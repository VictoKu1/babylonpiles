"""
Content Updater for managing downloads and updates from various sources
"""

import asyncio
import logging
import os
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import aiofiles

from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.modules.sources.kiwix import KiwixSource
from app.modules.sources.torrent import TorrentSource
from app.modules.sources.http import HTTPSource
from app.modules.sources.gutenberg import GutenbergSource

logger = logging.getLogger(__name__)

class ContentUpdater:
    """Manages content updates from various sources"""
    
    def __init__(self):
        self.sources = {
            "kiwix": KiwixSource(),
            "torrent": TorrentSource(),
            "http": HTTPSource(),
            "gutenberg": GutenbergSource(),
            "local": None  # Local files don't need a source handler
        }
        self._active_downloads = {}
    
    async def update_pile(self, pile: Pile, update_log: UpdateLog) -> bool:
        """Update a pile from its source"""
        try:
            logger.info(f"Starting update for pile: {pile.name}")
            
            # Get source handler
            source_handler = self.sources.get(pile.source_type)
            if not source_handler and pile.source_type != "local":
                raise ValueError(f"Unsupported source type: {pile.source_type}")
            
            # Create backup of current file if it exists
            backup_path = None
            if pile.file_path and os.path.exists(pile.file_path):
                backup_path = await self._create_backup(pile)
            
            # Download/update file
            success = False
            if pile.source_type == "local":
                success = True  # Local files don't need updating
            elif source_handler:
                success = await source_handler.download(
                    pile, update_log, self._progress_callback
                )
            
            if success:
                # Update pile metadata
                await self._update_pile_metadata(pile, update_log)
                logger.info(f"Successfully updated pile: {pile.name}")
                return True
            else:
                # Restore backup if update failed
                if backup_path and os.path.exists(backup_path):
                    await self._restore_backup(pile, backup_path)
                logger.error(f"Failed to update pile: {pile.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating pile {pile.name}: {e}")
            update_log.error_message = str(e)
            return False
    
    async def rollback_pile(self, pile: Pile, version: Optional[str] = None) -> bool:
        """Rollback pile to previous version"""
        try:
            logger.info(f"Rolling back pile: {pile.name}")
            
            # Find backup file
            backup_dir = Path(settings.data_dir) / "backups" / pile.name
            if not backup_dir.exists():
                logger.error(f"No backups found for pile: {pile.name}")
                return False
            
            # Get latest backup or specific version
            if version:
                backup_file = backup_dir / f"{version}.backup"
            else:
                backup_files = list(backup_dir.glob("*.backup"))
                if not backup_files:
                    logger.error(f"No backup files found for pile: {pile.name}")
                    return False
                backup_file = max(backup_files, key=lambda f: f.stat().st_mtime)
            
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Restore from backup
            success = await self._restore_backup(pile, str(backup_file))
            
            if success:
                logger.info(f"Successfully rolled back pile: {pile.name}")
                return True
            else:
                logger.error(f"Failed to rollback pile: {pile.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error rolling back pile {pile.name}: {e}")
            return False
    
    async def _create_backup(self, pile: Pile) -> Optional[str]:
        """Create backup of current pile file"""
        try:
            if not pile.file_path or not os.path.exists(pile.file_path):
                return None
            
            # Create backup directory
            backup_dir = Path(settings.data_dir) / "backups" / pile.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{timestamp}.backup"
            backup_path = backup_dir / backup_filename
            
            # Copy file
            shutil.copy2(pile.file_path, backup_path)
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating backup for {pile.name}: {e}")
            return None
    
    async def _restore_backup(self, pile: Pile, backup_path: str) -> bool:
        """Restore pile from backup"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Ensure piles directory exists
            piles_dir = Path(settings.piles_dir)
            piles_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore file
            target_path = piles_dir / f"{pile.name}{Path(backup_path).suffix}"
            shutil.copy2(backup_path, target_path)
            
            # Update pile metadata
            pile.file_path = str(target_path)
            pile.file_size = os.path.getsize(target_path)
            pile.file_format = target_path.suffix.lstrip(".")
            
            logger.info(f"Restored pile from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup for {pile.name}: {e}")
            return False
    
    async def _update_pile_metadata(self, pile: Pile, update_log: UpdateLog):
        """Update pile metadata after successful update"""
        try:
            if pile.file_path and os.path.exists(pile.file_path):
                # Calculate checksum
                checksum = await self._calculate_checksum(pile.file_path)
                
                # Update pile metadata
                pile.file_size = os.path.getsize(pile.file_path)
                pile.file_format = Path(pile.file_path).suffix.lstrip(".")
                pile.checksum = checksum
                pile.version = datetime.now().strftime("%Y%m%d_%H%M%S")
                pile.last_updated = datetime.utcnow()
                
                # Update log metadata
                update_log.file_path = pile.file_path
                update_log.file_size = pile.file_size
                update_log.checksum = checksum
                update_log.version = pile.version
                update_log.completed_at = datetime.utcnow()
                
                if update_log.started_at:
                    duration = (update_log.completed_at - update_log.started_at).total_seconds()
                    update_log.duration_seconds = int(duration)
                
        except Exception as e:
            logger.error(f"Error updating pile metadata: {e}")
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            hash_sha256 = hashlib.sha256()
            async with aiofiles.open(file_path, "rb") as f:
                while chunk := await f.read(8192):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""
    
    def _progress_callback(self, pile_id: int, progress: float):
        """Callback for download progress updates"""
        try:
            # This would typically update the pile's download progress
            # For now, we'll just log it
            logger.debug(f"Download progress for pile {pile_id}: {progress:.2%}")
        except Exception as e:
            logger.error(f"Error in progress callback: {e}")
    
    async def get_available_sources(self) -> Dict[str, Any]:
        """Get available content sources"""
        try:
            sources = {}
            
            # Kiwix sources
            kiwix_handler = self.sources.get("kiwix")
            if kiwix_handler:
                sources["kiwix"] = await kiwix_handler.get_available_content()
            
            # Torrent sources
            torrent_handler = self.sources.get("torrent")
            if torrent_handler:
                sources["torrent"] = await torrent_handler.get_available_content()
            
            return sources
            
        except Exception as e:
            logger.error(f"Error getting available sources: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up ContentUpdater...")
        
        # Cancel active downloads
        for task in self._active_downloads.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._active_downloads:
            await asyncio.gather(*self._active_downloads.values(), return_exceptions=True)
        
        self._active_downloads.clear() 