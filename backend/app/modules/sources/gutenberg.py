import aiohttp
import aiofiles
from pathlib import Path
import logging
from typing import Dict, Any, Optional, Callable
from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog

logger = logging.getLogger(__name__)

class GutenbergSource:
    BASE_API = "https://gutendex.com/books"

    async def download(
        self,
        pile: Pile,
        update_log: UpdateLog,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        try:
            # Assume pile.source_url is a Gutendex book ID or full URL
            book_id = pile.source_url
            if not book_id:
                raise Exception("No Project Gutenberg book ID provided")
            # If a full URL is provided, extract the ID
            if isinstance(book_id, str) and book_id.startswith("http"):
                # e.g. https://www.gutenberg.org/ebooks/1342
                book_id = book_id.rstrip("/").split("/")[-1]
            async with aiohttp.ClientSession() as session:
                # Get book metadata
                async with session.get(f"{self.BASE_API}/{book_id}") as resp:
                    if resp.status != 200:
                        raise Exception("Book not found in Project Gutenberg")
                    data = await resp.json()
                # Pick a preferred format (EPUB, plain text, etc.)
                formats = data.get("formats", {})
                preferred = [
                    ("application/epub+zip", "epub"),
                    ("application/pdf", "pdf"),
                    ("text/plain; charset=utf-8", "txt"),
                    ("text/plain", "txt"),
                    ("text/html; charset=utf-8", "html"),
                    ("text/html", "html"),
                ]
                download_url = None
                ext = None
                for mime, extension in preferred:
                    if mime in formats:
                        download_url = formats[mime]
                        ext = extension
                        break
                if not download_url:
                    raise Exception("No supported format found for this book")
                # Download the file
                piles_dir = Path(settings.piles_dir)
                piles_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{pile.name}.{ext}"
                target_path = piles_dir / filename
                async with session.get(download_url) as resp:
                    if resp.status != 200:
                        raise Exception("Failed to download file from Project Gutenberg")
                    async with aiofiles.open(target_path, "wb") as f:
                        while True:
                            chunk = await resp.content.read(8192)
                            if not chunk:
                                break
                            await f.write(chunk)
                pile.file_path = str(target_path)
                pile.file_size = target_path.stat().st_size
                pile.file_format = ext
                logger.info(f"Successfully downloaded Project Gutenberg book: {target_path}")
                return True
        except Exception as e:
            logger.error(f"Gutenberg download failed: {e}")
            update_log.error_message = str(e)
            return False

    async def get_available_content(self, query: str = "") -> Dict[str, Any]:
        """Search for books on Project Gutenberg using Gutendex API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_API}?search={query}") as resp:
                    if resp.status != 200:
                        return {"total_count": 0, "results": [], "error": "Failed to fetch results"}
                    data = await resp.json()
                    return {
                        "total_count": data.get("count", 0),
                        "results": data.get("results", [])
                    }
        except Exception as e:
            logger.error(f"Error searching Project Gutenberg: {e}")
            return {"total_count": 0, "results": [], "error": str(e)} 