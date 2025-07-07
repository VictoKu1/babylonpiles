"""
Storage Client for BabylonPiles Backend
Communicates with the storage service for HDD management
"""

import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class StorageClient:
    def __init__(self, storage_url: str):
        self.storage_url = storage_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def health_check(self) -> bool:
        """Check if storage service is healthy"""
        try:
            response = await self.client.get(f"{self.storage_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Storage service health check failed: {e}")
            return False

    async def get_drives(self) -> List[Dict]:
        """Get available drives from storage service"""
        try:
            response = await self.client.get(f"{self.storage_url}/drives")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get drives: {e}")
            return []

    async def get_drive(self, drive_id: str) -> Optional[Dict]:
        """Get specific drive information"""
        try:
            response = await self.client.get(f"{self.storage_url}/drives/{drive_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get drive {drive_id}: {e}")
            return None

    async def scan_drives(self) -> Dict:
        """Manually trigger drive scan"""
        try:
            response = await self.client.post(f"{self.storage_url}/drives/scan")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to scan drives: {e}")
            return {"message": "Scan failed", "drives": []}

    async def allocate_file(self, file_size: int, file_id: str) -> Dict:
        """Allocate storage for file"""
        try:
            response = await self.client.post(
                f"{self.storage_url}/allocate",
                json={"file_size": file_size, "file_id": file_id},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to allocate file {file_id}: {e}")
            raise

    async def get_chunks(self, file_id: Optional[str] = None) -> List[Dict]:
        """Get chunks, optionally filtered by file_id"""
        try:
            params = {"file_id": file_id} if file_id else {}
            response = await self.client.get(
                f"{self.storage_url}/chunks", params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get chunks: {e}")
            return []

    async def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """Get specific chunk information"""
        try:
            response = await self.client.get(f"{self.storage_url}/chunks/{chunk_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None

    async def migrate_chunk(self, chunk_id: str, target_drive: str) -> Dict:
        """Migrate chunk to different drive"""
        try:
            response = await self.client.post(
                f"{self.storage_url}/migrate",
                json={"chunk_id": chunk_id, "target_drive": target_drive},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to migrate chunk {chunk_id}: {e}")
            raise

    async def get_migrations(self) -> List[Dict]:
        """Get all migrations"""
        try:
            response = await self.client.get(f"{self.storage_url}/migrations")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get migrations: {e}")
            return []

    async def get_migration(self, migration_id: str) -> Optional[Dict]:
        """Get specific migration"""
        try:
            response = await self.client.get(
                f"{self.storage_url}/migrations/{migration_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get migration {migration_id}: {e}")
            return None

    async def get_status(self) -> Dict:
        """Get overall storage status"""
        try:
            response = await self.client.get(f"{self.storage_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {}

    async def get_file_allocation(self, file_id: str) -> Optional[Dict]:
        """Get file allocation information"""
        try:
            response = await self.client.get(f"{self.storage_url}/files/{file_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get file allocation {file_id}: {e}")
            return None

    async def delete_file(self, file_id: str) -> Dict:
        """Delete file and free allocated storage"""
        try:
            response = await self.client.delete(f"{self.storage_url}/files/{file_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global storage client instance
storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """Get the global storage client instance"""
    global storage_client
    if storage_client is None:
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        storage_client = StorageClient(storage_url)
    return storage_client


async def close_storage_client():
    """Close the global storage client"""
    global storage_client
    if storage_client:
        await storage_client.close()
        storage_client = None
