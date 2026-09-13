"""Gutenberg metadata and book imports through bounded public HTTP requests."""
import logging
import re
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlencode, urlsplit

from app.core.config import settings
from app.core.paths import resolve_path, validate_name
from app.core.public_http import PublicSession, validate_url
from app.core.transfers import save_chunks
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.modules.sources.http import progress_chunks

logger = logging.getLogger(__name__)


class GutenbergSource:
    BASE_API = "https://gutendex.com/books"

    @staticmethod
    def _book_id(value) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("No Project Gutenberg book ID provided")
        if value.startswith(("http://", "https://")):
            validate_url(value)
            value = urlsplit(value).path.rstrip("/").rsplit("/", 1)[-1]
        if not re.fullmatch(r"[0-9]{1,20}", value):
            raise ValueError("Project Gutenberg book ID must contain only digits")
        return value

    async def download(self, pile: Pile, update_log: UpdateLog,
                       progress_callback: Optional[Callable] = None) -> bool:
        try:
            validate_name(pile.name)
            book_id = self._book_id(pile.source_url)
            async with PublicSession() as session:
                async with session.get(f"{self.BASE_API}/{book_id}",
                                       max_bytes=settings.max_catalog_size) as response:
                    if response.status != 200:
                        raise ValueError("Book not found in Project Gutenberg")
                    data = await response.json()
                formats = data.get("formats", {})
                preferred = [
                    ("application/epub+zip", "epub"),
                    ("application/pdf", "pdf"),
                    ("text/plain; charset=utf-8", "txt"),
                    ("text/plain", "txt"),
                    ("text/html; charset=utf-8", "html"),
                    ("text/html", "html"),
                ]
                download_url, extension = next(
                    ((formats[mime], ext) for mime, ext in preferred if formats.get(mime)),
                    (None, None),
                )
                if not download_url:
                    raise ValueError("No supported format found for this book")
                target = resolve_path(settings.piles_dir, f"{pile.name}.{extension}")
                async with session.get(download_url, max_bytes=settings.max_file_size) as response:
                    if response.status != 200:
                        raise ValueError("Failed to download file from Project Gutenberg")
                    await save_chunks(progress_chunks(response, target, progress_callback),
                                      target, settings.max_file_size)
                pile.file_path = str(target)
                pile.file_size = target.stat().st_size
                pile.file_format = extension
                return True
        except Exception as exc:
            logger.error("Gutenberg import failed: %s", exc)
            update_log.error_message = str(exc)
            return False

    async def get_available_content(self, query: str = "") -> Dict[str, Any]:
        try:
            async with PublicSession() as session:
                url = f"{self.BASE_API}?{urlencode({'search': query})}"
                async with session.get(url, max_bytes=settings.max_catalog_size) as response:
                    if response.status != 200:
                        return {"total_count": 0, "results": [], "error": "Failed to fetch results"}
                    data = await response.json()
                    return {"total_count": data.get("count", 0), "results": data.get("results", [])}
        except Exception as exc:
            logger.error("Error searching Project Gutenberg: %s", exc)
            return {"total_count": 0, "results": [], "error": str(exc)}
