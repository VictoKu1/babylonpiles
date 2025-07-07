#!/usr/bin/env python3
"""
BabylonPiles Storage Service
Manages HDD storage, file chunking, and migration
"""

import os
import shutil
import threading
import time
import uuid
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import subprocess

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/data/logs/storage.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BabylonPiles Storage Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class DriveInfo(BaseModel):
    id: str
    path: str
    total_space: int
    free_space: int
    used_space: int
    status: str
    health: str
    mount_point: str
    file_system: str


class ChunkInfo(BaseModel):
    id: str
    file_id: str
    drive_id: str
    path: str
    size: int
    checksum: str
    created_at: str
    status: str


class MigrationTask(BaseModel):
    id: str
    chunk_id: str
    source_drive: str
    target_drive: str
    status: str
    progress: float
    started_at: str
    completed_at: Optional[str]


class StorageAllocation(BaseModel):
    file_id: str
    file_size: int
    chunks: List[Dict]
    status: str


class StorageManager:
    def __init__(self):
        self.drives: Dict[str, DriveInfo] = {}
        self.chunks: Dict[str, ChunkInfo] = {}
        self.migrations: Dict[str, MigrationTask] = {}
        self.file_allocations: Dict[str, StorageAllocation] = {}
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "104857600"))  # 100MB default
        self.max_drives = int(os.getenv("MAX_DRIVES", "10"))

        # Load existing data
        self.load_metadata()

        # Start background tasks
        self.start_background_tasks()

    def load_metadata(self):
        """Load metadata from disk"""
        try:
            metadata_dir = Path("/app/data/metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)

            # Load drives
            drives_file = metadata_dir / "drives.json"
            if drives_file.exists():
                with open(drives_file, "r") as f:
                    drives_data = json.load(f)
                    for drive_id, data in drives_data.items():
                        self.drives[drive_id] = DriveInfo(**data)

            # Load chunks
            chunks_file = metadata_dir / "chunks.json"
            if chunks_file.exists():
                with open(chunks_file, "r") as f:
                    chunks_data = json.load(f)
                    for chunk_id, data in chunks_data.items():
                        self.chunks[chunk_id] = ChunkInfo(**data)

            # Load migrations
            migrations_file = metadata_dir / "migrations.json"
            if migrations_file.exists():
                with open(migrations_file, "r") as f:
                    migrations_data = json.load(f)
                    for migration_id, data in migrations_data.items():
                        self.migrations[migration_id] = MigrationTask(**data)

            logger.info(
                f"Loaded {len(self.drives)} drives, {len(self.chunks)} chunks, {len(self.migrations)} migrations"
            )
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")

    def save_metadata(self):
        """Save metadata to disk"""
        try:
            metadata_dir = Path("/app/data/metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)

            # Save drives
            with open(metadata_dir / "drives.json", "w") as f:
                json.dump({k: v.dict() for k, v in self.drives.items()}, f, indent=2)

            # Save chunks
            with open(metadata_dir / "chunks.json", "w") as f:
                json.dump({k: v.dict() for k, v in self.chunks.items()}, f, indent=2)

            # Save migrations
            with open(metadata_dir / "migrations.json", "w") as f:
                json.dump(
                    {k: v.dict() for k, v in self.migrations.items()}, f, indent=2
                )

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def scan_drives(self):
        """Scan for available drives"""
        logger.info("Scanning for drives...")

        for i in range(1, self.max_drives + 1):
            drive_id = f"hdd{i}"
            mount_path = f"/mnt/{drive_id}"

            if os.path.exists(mount_path):
                try:
                    # Get disk usage
                    total, used, free = shutil.disk_usage(mount_path)

                    # Get mount info
                    mount_info = self.get_mount_info(mount_path)

                    # Check drive health
                    health = self.check_drive_health(mount_path)

                    drive_info = DriveInfo(
                        id=drive_id,
                        path=mount_path,
                        total_space=total,
                        free_space=free,
                        used_space=used,
                        status=(
                            "active" if os.access(mount_path, os.W_OK) else "readonly"
                        ),
                        health=health,
                        mount_point=mount_info.get("mount_point", mount_path),
                        file_system=mount_info.get("file_system", "unknown"),
                    )

                    self.drives[drive_id] = drive_info
                    logger.info(
                        f"Found drive {drive_id}: {total // (1024**3)}GB total, {free // (1024**3)}GB free"
                    )

                except Exception as e:
                    logger.error(f"Error scanning drive {drive_id}: {e}")

        self.save_metadata()
        return list(self.drives.values())

    def get_mount_info(self, path: str) -> Dict[str, str]:
        """Get mount information for a path"""
        try:
            result = subprocess.run(["df", "-T", path], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 7:
                    return {"mount_point": parts[6], "file_system": parts[1]}
        except Exception as e:
            logger.error(f"Error getting mount info for {path}: {e}")

        return {"mount_point": path, "file_system": "unknown"}

    def check_drive_health(self, path: str) -> str:
        """Check drive health using smartctl"""
        try:
            # Try to get device name from mount point
            result = subprocess.run(
                ["findmnt", "-n", "-o", "SOURCE", path], capture_output=True, text=True
            )
            device = result.stdout.strip()

            if device and os.path.exists(device):
                # Check SMART status
                smart_result = subprocess.run(
                    ["smartctl", "-H", device], capture_output=True, text=True
                )

                if (
                    "SMART overall-health self-assessment test result: PASSED"
                    in smart_result.stdout
                ):
                    return "healthy"
                elif (
                    "SMART overall-health self-assessment test result: FAILED"
                    in smart_result.stdout
                ):
                    return "failed"
                else:
                    return "unknown"
        except Exception as e:
            logger.error(f"Error checking drive health for {path}: {e}")

        return "unknown"

    def find_best_drive_for_chunk(self, chunk_size: int) -> Optional[str]:
        """Find the best drive for a chunk based on available space and load"""
        candidates = []

        for drive_id, drive in self.drives.items():
            if drive.status == "active" and drive.free_space >= chunk_size:
                # Calculate score based on free space ratio and current load
                free_ratio = drive.free_space / drive.total_space
                load_score = 1.0 - (drive.used_space / drive.total_space)

                # Count chunks on this drive
                chunk_count = sum(
                    1 for chunk in self.chunks.values() if chunk.drive_id == drive_id
                )
                chunk_penalty = min(chunk_count * 0.01, 0.3)  # Max 30% penalty

                score = (free_ratio * 0.6) + (load_score * 0.3) - chunk_penalty
                candidates.append((drive_id, score))

        if candidates:
            # Sort by score (higher is better)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def allocate_file(self, file_size: int, file_id: str) -> StorageAllocation:
        """Allocate storage for a file across multiple drives"""
        logger.info(f"Allocating {file_size} bytes for file {file_id}")

        # Split file into chunks
        chunks = []
        remaining_size = file_size
        chunk_number = 0

        while remaining_size > 0:
            chunk_size = min(self.chunk_size, remaining_size)

            # Find best drive for this chunk
            drive_id = self.find_best_drive_for_chunk(chunk_size)
            if not drive_id:
                raise HTTPException(
                    status_code=507, detail="Insufficient storage space"
                )

            chunk_id = f"{file_id}_chunk_{chunk_number}"
            chunk_path = f"{self.drives[drive_id].path}/chunks/{chunk_id}"

            # Create chunk directory
            os.makedirs(os.path.dirname(chunk_path), exist_ok=True)

            chunk_info = ChunkInfo(
                id=chunk_id,
                file_id=file_id,
                drive_id=drive_id,
                path=chunk_path,
                size=chunk_size,
                checksum="",  # Will be calculated when file is written
                created_at=datetime.now().isoformat(),
                status="allocated",
            )

            self.chunks[chunk_id] = chunk_info
            chunks.append(
                {
                    "id": chunk_id,
                    "drive_id": drive_id,
                    "path": chunk_path,
                    "size": chunk_size,
                }
            )

            # Update drive usage
            self.drives[drive_id].free_space -= chunk_size
            self.drives[drive_id].used_space += chunk_size

            remaining_size -= chunk_size
            chunk_number += 1

        allocation = StorageAllocation(
            file_id=file_id, file_size=file_size, chunks=chunks, status="allocated"
        )

        self.file_allocations[file_id] = allocation
        self.save_metadata()

        logger.info(f"Allocated {len(chunks)} chunks for file {file_id}")
        return allocation

    def migrate_chunk(self, chunk_id: str, target_drive: str) -> MigrationTask:
        """Migrate a chunk to a different drive"""
        if chunk_id not in self.chunks:
            raise HTTPException(status_code=404, detail="Chunk not found")

        if target_drive not in self.drives:
            raise HTTPException(status_code=404, detail="Target drive not found")

        chunk = self.chunks[chunk_id]
        source_drive = chunk.drive_id

        if source_drive == target_drive:
            raise HTTPException(
                status_code=400, detail="Source and target drives are the same"
            )

        # Check if target drive has enough space
        if self.drives[target_drive].free_space < chunk.size:
            raise HTTPException(
                status_code=507, detail="Target drive has insufficient space"
            )

        migration_id = str(uuid.uuid4())
        migration = MigrationTask(
            id=migration_id,
            chunk_id=chunk_id,
            source_drive=source_drive,
            target_drive=target_drive,
            status="queued",
            progress=0.0,
            started_at=datetime.now().isoformat(),
            completed_at=None,
        )

        self.migrations[migration_id] = migration
        self.save_metadata()

        # Start migration in background
        threading.Thread(target=self._perform_migration, args=(migration_id,)).start()

        logger.info(
            f"Started migration {migration_id}: {chunk_id} from {source_drive} to {target_drive}"
        )
        return migration

    def _perform_migration(self, migration_id: str):
        """Perform chunk migration in background"""
        migration = self.migrations[migration_id]
        chunk = self.chunks[migration.chunk_id]

        try:
            migration.status = "migrating"
            migration.started_at = datetime.now().isoformat()
            self.save_metadata()

            # Create target path
            target_path = (
                f"{self.drives[migration.target_drive].path}/chunks/{chunk.id}"
            )
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Copy file using rsync for efficiency
            if os.path.exists(chunk.path):
                result = subprocess.run(
                    ["rsync", "-av", "--progress", chunk.path, target_path],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    # Update chunk information
                    chunk.drive_id = migration.target_drive
                    chunk.path = target_path

                    # Update drive usage
                    self.drives[migration.source_drive].free_space += chunk.size
                    self.drives[migration.source_drive].used_space -= chunk.size
                    self.drives[migration.target_drive].free_space -= chunk.size
                    self.drives[migration.target_drive].used_space += chunk.size

                    # Remove original file
                    os.remove(chunk.path)

                    migration.status = "completed"
                    migration.progress = 100.0
                    migration.completed_at = datetime.now().isoformat()

                    logger.info(f"Migration {migration_id} completed successfully")
                else:
                    raise Exception(f"rsync failed: {result.stderr}")
            else:
                raise Exception(f"Source file {chunk.path} not found")

        except Exception as e:
            migration.status = "failed"
            migration.completed_at = datetime.now().isoformat()
            logger.error(f"Migration {migration_id} failed: {e}")

        self.save_metadata()

    def get_status(self) -> Dict:
        """Get overall storage status"""
        total_space = sum(drive.total_space for drive in self.drives.values())
        free_space = sum(drive.free_space for drive in self.drives.values())
        used_space = sum(drive.used_space for drive in self.drives.values())

        active_migrations = sum(
            1 for m in self.migrations.values() if m.status == "migrating"
        )
        queued_migrations = sum(
            1 for m in self.migrations.values() if m.status == "queued"
        )

        return {
            "total_drives": len(self.drives),
            "active_drives": sum(
                1 for d in self.drives.values() if d.status == "active"
            ),
            "total_space": total_space,
            "free_space": free_space,
            "used_space": used_space,
            "utilization_percent": (
                (used_space / total_space * 100) if total_space > 0 else 0
            ),
            "total_chunks": len(self.chunks),
            "active_migrations": active_migrations,
            "queued_migrations": queued_migrations,
            "total_files": len(self.file_allocations),
        }

    def start_background_tasks(self):
        """Start background tasks"""

        def background_scanner():
            while True:
                try:
                    self.scan_drives()
                    time.sleep(60)  # Scan every minute
                except Exception as e:
                    logger.error(f"Error in background scanner: {e}")
                    time.sleep(60)

        threading.Thread(target=background_scanner, daemon=True).start()
        logger.info("Started background tasks")


# Initialize storage manager
storage_manager = StorageManager()


# API endpoints
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/drives", response_model=List[DriveInfo])
def get_drives():
    """Get all available drives"""
    return list(storage_manager.drives.values())


@app.post("/drives/scan")
def scan_drives():
    """Manually trigger drive scan"""
    drives = storage_manager.scan_drives()
    return {"message": f"Scanned {len(drives)} drives", "drives": drives}


@app.get("/drives/{drive_id}", response_model=DriveInfo)
def get_drive(drive_id: str):
    """Get specific drive information"""
    if drive_id not in storage_manager.drives:
        raise HTTPException(status_code=404, detail="Drive not found")
    return storage_manager.drives[drive_id]


@app.post("/allocate", response_model=StorageAllocation)
def allocate_file(file_size: int, file_id: str):
    """Allocate storage for a file"""
    return storage_manager.allocate_file(file_size, file_id)


@app.get("/chunks", response_model=List[ChunkInfo])
def get_chunks(file_id: Optional[str] = None):
    """Get chunks, optionally filtered by file_id"""
    chunks = list(storage_manager.chunks.values())
    if file_id:
        chunks = [c for c in chunks if c.file_id == file_id]
    return chunks


@app.get("/chunks/{chunk_id}", response_model=ChunkInfo)
def get_chunk(chunk_id: str):
    """Get specific chunk information"""
    if chunk_id not in storage_manager.chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return storage_manager.chunks[chunk_id]


@app.post("/migrate", response_model=MigrationTask)
def migrate_chunk(chunk_id: str, target_drive: str):
    """Migrate chunk to different drive"""
    return storage_manager.migrate_chunk(chunk_id, target_drive)


@app.get("/migrations", response_model=List[MigrationTask])
def get_migrations():
    """Get all migrations"""
    return list(storage_manager.migrations.values())


@app.get("/migrations/{migration_id}", response_model=MigrationTask)
def get_migration(migration_id: str):
    """Get specific migration"""
    if migration_id not in storage_manager.migrations:
        raise HTTPException(status_code=404, detail="Migration not found")
    return storage_manager.migrations[migration_id]


@app.get("/status")
def get_status():
    """Get overall storage status"""
    return storage_manager.get_status()


@app.get("/files/{file_id}", response_model=StorageAllocation)
def get_file_allocation(file_id: str):
    """Get file allocation information"""
    if file_id not in storage_manager.file_allocations:
        raise HTTPException(status_code=404, detail="File allocation not found")
    return storage_manager.file_allocations[file_id]


@app.delete("/files/{file_id}")
def delete_file(file_id: str):
    """Delete file and free allocated storage"""
    if file_id not in storage_manager.file_allocations:
        raise HTTPException(status_code=404, detail="File allocation not found")

    allocation = storage_manager.file_allocations[file_id]

    # Delete chunks
    for chunk_info in allocation.chunks:
        chunk_id = chunk_info["id"]
        if chunk_id in storage_manager.chunks:
            chunk = storage_manager.chunks[chunk_id]

            # Remove file if it exists
            if os.path.exists(chunk.path):
                os.remove(chunk.path)

            # Update drive usage
            drive = storage_manager.drives[chunk.drive_id]
            drive.free_space += chunk.size
            drive.used_space -= chunk.size

            # Remove chunk record
            del storage_manager.chunks[chunk_id]

    # Remove file allocation
    del storage_manager.file_allocations[file_id]
    storage_manager.save_metadata()

    return {"message": f"Deleted file {file_id} and freed storage"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
