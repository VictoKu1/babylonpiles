"""
Kiwix source handler for downloading ZIM files
"""

import asyncio
import logging
import os
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from urllib.parse import urljoin, urlparse
import json

from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog

logger = logging.getLogger(__name__)

class KiwixSource:
    """Handles downloads from Kiwix library"""
    
    def __init__(self):
        self.base_url = settings.kiwix_library_url
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def download(
        self, 
        pile: Pile, 
        update_log: UpdateLog, 
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download ZIM file from Kiwix"""
        try:
            logger.info(f"Starting Kiwix download for: {pile.name}")
            
            # Get download URL
            download_url = await self._get_download_url(pile)
            if not download_url:
                raise ValueError("Could not find download URL")
            
            # Create target directory
            piles_dir = Path(settings.piles_dir)
            piles_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate target filename
            filename = f"{pile.name}.zim"
            target_path = piles_dir / filename
            
            # Download file
            success = await self._download_file(
                download_url, 
                target_path, 
                progress_callback
            )
            
            if success:
                # Update pile with file path
                pile.file_path = str(target_path)
                pile.file_size = os.path.getsize(target_path)
                pile.file_format = "zim"
                
                logger.info(f"Successfully downloaded: {target_path}")
                return True
            else:
                logger.error(f"Failed to download: {download_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading from Kiwix: {e}")
            update_log.error_message = str(e)
            return False
    
    async def _get_download_url(self, pile: Pile) -> Optional[str]:
        """Get download URL for ZIM file"""
        try:
            # Parse source URL or use default Kiwix library
            if pile.source_url:
                # Direct URL provided
                return pile.source_url
            
            # Search Kiwix library for matching content
            content_list = await self._get_content_list()
            
            # Find matching content based on pile name/description
            for content in content_list:
                if self._matches_pile(pile, content):
                    return content.get("download_url")
            
            logger.warning(f"No matching Kiwix content found for: {pile.name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None
    
    async def _get_content_list(self) -> List[Dict[str, Any]]:
        """Get list of available Kiwix content"""
        try:
            session = await self._get_session()
            
            # Get content catalog
            catalog_url = urljoin(self.base_url, "/catalog/v2/entries.json")
            
            async with session.get(catalog_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to get Kiwix catalog: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting Kiwix content list: {e}")
            return []
    
    def _matches_pile(self, pile: Pile, content: Dict[str, Any]) -> bool:
        """Check if Kiwix content matches pile"""
        try:
            # Check by name
            content_name = content.get("name", "").lower()
            pile_name = pile.name.lower()
            
            if pile_name in content_name or content_name in pile_name:
                return True
            
            # Check by description
            content_description = content.get("description", "").lower()
            pile_description = (pile.description or "").lower()
            
            if pile_description and any(word in content_description for word in pile_description.split()):
                return True
            
            # Check by tags
            content_tags = content.get("tags", [])
            pile_tags = pile.tags or []
            
            if pile_tags and any(tag in content_tags for tag in pile_tags):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error matching pile: {e}")
            return False
    
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
        """Get available Kiwix content"""
        try:
            content_list = await self._get_content_list()
            
            # Group by category
            categories = {}
            for content in content_list:
                category = content.get("category", "other")
                if category not in categories:
                    categories[category] = []
                categories[category].append({
                    "name": content.get("name"),
                    "description": content.get("description"),
                    "size": content.get("size"),
                    "download_url": content.get("download_url"),
                    "tags": content.get("tags", [])
                })
            
            return {
                "total_count": len(content_list),
                "categories": categories
            }
            
        except Exception as e:
            logger.error(f"Error getting available content: {e}")
            return {"total_count": 0, "categories": {}}
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close() 