"""
Storage API endpoints for BabylonPiles Backend
Provides interface to storage service for HDD management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import logging

from app.core.storage_client import get_storage_client, StorageClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/drives")
async def get_drives():
    """Get all available drives from storage service"""
    try:
        storage_client = get_storage_client()
        drives = await storage_client.get_drives()
        return {"drives": drives}
    except Exception as e:
        logger.error(f"Failed to get drives: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drives")


@router.get("/drives/{drive_id}")
async def get_drive(drive_id: str):
    """Get specific drive information"""
    try:
        storage_client = get_storage_client()
        drive = await storage_client.get_drive(drive_id)
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        return drive
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get drive {drive_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drive")


@router.post("/drives/scan")
async def scan_drives():
    """Manually trigger drive scan"""
    try:
        storage_client = get_storage_client()
        result = await storage_client.scan_drives()
        return result
    except Exception as e:
        logger.error(f"Failed to scan drives: {e}")
        raise HTTPException(status_code=500, detail="Failed to scan drives")


@router.post("/allocate")
async def allocate_storage(file_size: int, file_id: str):
    """Allocate storage for a file"""
    try:
        storage_client = get_storage_client()
        allocation = await storage_client.allocate_file(file_size, file_id)
        return allocation
    except Exception as e:
        logger.error(f"Failed to allocate storage for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to allocate storage")


@router.get("/chunks")
async def get_chunks(file_id: Optional[str] = None):
    """Get chunks, optionally filtered by file_id"""
    try:
        storage_client = get_storage_client()
        chunks = await storage_client.get_chunks(file_id)
        return {"chunks": chunks}
    except Exception as e:
        logger.error(f"Failed to get chunks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chunks")


@router.get("/chunks/{chunk_id}")
async def get_chunk(chunk_id: str):
    """Get specific chunk information"""
    try:
        storage_client = get_storage_client()
        chunk = await storage_client.get_chunk(chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return chunk
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunk {chunk_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chunk")


@router.post("/migrate")
async def migrate_chunk(chunk_id: str, target_drive: str):
    """Migrate chunk to different drive"""
    try:
        storage_client = get_storage_client()
        migration = await storage_client.migrate_chunk(chunk_id, target_drive)
        return migration
    except Exception as e:
        logger.error(f"Failed to migrate chunk {chunk_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to migrate chunk")


@router.get("/migrations")
async def get_migrations():
    """Get all migrations"""
    try:
        storage_client = get_storage_client()
        migrations = await storage_client.get_migrations()
        return {"migrations": migrations}
    except Exception as e:
        logger.error(f"Failed to get migrations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get migrations")


@router.get("/migrations/{migration_id}")
async def get_migration(migration_id: str):
    """Get specific migration"""
    try:
        storage_client = get_storage_client()
        migration = await storage_client.get_migration(migration_id)
        if not migration:
            raise HTTPException(status_code=404, detail="Migration not found")
        return migration
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get migration {migration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get migration")


@router.get("/status")
async def get_storage_status():
    """Get overall storage status"""
    try:
        storage_client = get_storage_client()
        status = await storage_client.get_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get storage status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage status")


@router.get("/files/{file_id}")
async def get_file_allocation(file_id: str):
    """Get file allocation information"""
    try:
        storage_client = get_storage_client()
        allocation = await storage_client.get_file_allocation(file_id)
        if not allocation:
            raise HTTPException(status_code=404, detail="File allocation not found")
        return allocation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file allocation {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file allocation")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete file and free allocated storage"""
    try:
        storage_client = get_storage_client()
        result = await storage_client.delete_file(file_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.get("/health")
async def storage_health_check():
    """Check storage service health"""
    try:
        storage_client = get_storage_client()
        is_healthy = await storage_client.health_check()
        return {"healthy": is_healthy}
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return {"healthy": False}
