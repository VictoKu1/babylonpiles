"""
HTTP source handler for downloading files from HTTP/HTTPS URLs
"""

import asyncio
import logging
import os
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse

from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog

logger = logging.getLogger(__name__)

class HTTPSource:
    """Handles downloads from HTTP/HTTPS URLs"""
    
    def __init__(self):
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def download(
        self, 
        pile: Pile, 
        update_log: UpdateLog, 
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download file from HTTP/HTTPS URL"""
        try:
            logger.info(f"Starting HTTP download for: {pile.name}")
            
            if not pile.source_url:
                raise ValueError("No source URL provided")
            
            # Create target directory
            piles_dir = Path(settings.piles_dir)
            piles_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate target filename
            filename = self._get_filename(pile)
            target_path = piles_dir / filename
            
            # Download file
            success = await self._download_file(
                pile.source_url, 
                target_path, 
                progress_callback
            )
            
            if success:
                # Update pile with file path
                pile.file_path = str(target_path)
                pile.file_size = os.path.getsize(target_path)
                pile.file_format = target_path.suffix.lstrip(".")
                
                logger.info(f"Successfully downloaded: {target_path}")
                return True
            else:
                logger.error(f"Failed to download: {pile.source_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading from HTTP: {e}")
            update_log.error_message = str(e)
            return False
    
    def _get_filename(self, pile: Pile) -> str:
        """Generate filename for downloaded file"""
        try:
            if pile.source_url:
                # Try to get filename from URL
                parsed_url = urlparse(pile.source_url)
                path = parsed_url.path
                if path and "/" in path:
                    filename = path.split("/")[-1]
                    if filename and "." in filename:
                        return filename
            
            # Fallback to pile name with common extensions
            extensions = [".pdf", ".zip", ".tar.gz", ".iso", ".mp4", ".avi"]
            for ext in extensions:
                if pile.name.lower().endswith(ext):
                    return f"{pile.name}{ext}"
            
            # Default to pile name with .bin extension
            return f"{pile.name}.bin"
            
        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            return f"{pile.name}.bin"
    
    async def _download_file(
        self, 
        url: str, 
        target_path: Path, 
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download file with progress tracking"""
        try:
            session = await self._get_session()
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Download failed: {response.status}")
                    return False
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                async with aiofiles.open(target_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Update progress
                        if total_size > 0 and progress_callback:
                            progress = downloaded_size / total_size
                            progress_callback(target_path.name, progress)
                
                return True
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    async def get_available_content(self) -> Dict[str, Any]:
        """Get available HTTP content (placeholder)"""
        return {
            "total_count": 0,
            "categories": {},
            "note": "HTTP source requires manual URL configuration"
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close() 