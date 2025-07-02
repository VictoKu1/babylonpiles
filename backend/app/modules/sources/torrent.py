"""
Torrent source handler for downloading files via BitTorrent
"""

import asyncio
import logging
import os
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import subprocess
import tempfile

from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog

logger = logging.getLogger(__name__)

class TorrentSource:
    """Handles downloads via BitTorrent protocol"""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_dir) / "torrents"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def download(
        self, 
        pile: Pile, 
        update_log: UpdateLog, 
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download file via BitTorrent"""
        try:
            logger.info(f"Starting torrent download for: {pile.name}")
            
            if not pile.source_url:
                raise ValueError("No torrent URL provided")
            
            # Create target directory
            piles_dir = Path(settings.piles_dir)
            piles_dir.mkdir(parents=True, exist_ok=True)
            
            # Download torrent file
            torrent_file = await self._download_torrent_file(pile.source_url)
            if not torrent_file:
                raise ValueError("Failed to download torrent file")
            
            # Download content via torrent
            success = await self._download_via_torrent(
                torrent_file, 
                piles_dir, 
                pile.name,
                progress_callback
            )
            
            if success:
                # Find downloaded file
                downloaded_file = self._find_downloaded_file(piles_dir, pile.name)
                if downloaded_file:
                    pile.file_path = str(downloaded_file)
                    pile.file_size = os.path.getsize(downloaded_file)
                    pile.file_format = downloaded_file.suffix.lstrip(".")
                    
                    logger.info(f"Successfully downloaded: {downloaded_file}")
                    return True
            
            logger.error(f"Failed to download torrent: {pile.source_url}")
            return False
                
        except Exception as e:
            logger.error(f"Error downloading torrent: {e}")
            update_log.error_message = str(e)
            return False
    
    async def _download_torrent_file(self, url: str) -> Optional[Path]:
        """Download torrent file from URL"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download torrent file: {response.status}")
                        return None
                    
                    # Save torrent file
                    torrent_file = self.temp_dir / f"temp_{hash(url)}.torrent"
                    async with aiofiles.open(torrent_file, 'wb') as f:
                        await f.write(await response.read())
                    
                    return torrent_file
                    
        except Exception as e:
            logger.error(f"Error downloading torrent file: {e}")
            return None
    
    async def _download_via_torrent(
        self, 
        torrent_file: Path, 
        target_dir: Path, 
        pile_name: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download content via torrent client"""
        try:
            # Use transmission-cli or similar torrent client
            # This is a simplified implementation
            cmd = [
                "transmission-cli",
                "--download-dir", str(target_dir),
                "--no-portmap",
                str(torrent_file)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Torrent download completed")
                return True
            else:
                logger.error(f"Torrent download failed: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            logger.error("transmission-cli not found. Please install transmission-cli.")
            return False
        except Exception as e:
            logger.error(f"Error downloading via torrent: {e}")
            return False
    
    def _find_downloaded_file(self, target_dir: Path, pile_name: str) -> Optional[Path]:
        """Find downloaded file in target directory"""
        try:
            # Look for files that might match the pile name
            for file_path in target_dir.iterdir():
                if file_path.is_file():
                    # Check if filename contains pile name
                    if pile_name.lower() in file_path.name.lower():
                        return file_path
                    
                    # Check common file extensions
                    if file_path.suffix in ['.pdf', '.zip', '.iso', '.mp4', '.avi', '.mkv']:
                        return file_path
            
            # If no match found, return the largest file
            files = [f for f in target_dir.iterdir() if f.is_file()]
            if files:
                return max(files, key=lambda f: f.stat().st_size)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding downloaded file: {e}")
            return None
    
    async def get_available_content(self) -> Dict[str, Any]:
        """Get available torrent content (placeholder)"""
        return {
            "total_count": 0,
            "categories": {},
            "note": "Torrent source requires manual torrent URL configuration"
        }
    
    async def cleanup(self):
        """Cleanup temporary files"""
        try:
            # Remove temporary torrent files
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up torrent files: {e}") 