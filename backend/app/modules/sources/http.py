"""HTTP imports through the shared public-network and managed-file policies."""
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse, unquote
import aiohttp

from app.core.config import settings
from app.core.paths import resolve_path, validate_name, validate_stored_path
from app.core.public_http import PublicSession
from app.core.transfers import save_chunks
from app.models.pile import Pile
from app.models.update_log import UpdateLog

logger = logging.getLogger(__name__)


async def progress_chunks(response, target: Path, callback=None):
    """Forward bounded chunks and support either sync or async callbacks."""
    total = int(response.headers.get("content-length", 0))
    received = 0
    async for chunk in response.content.iter_chunked(64 * 1024):
        received += len(chunk)
        yield chunk
        if callback and total > 0:
            result = callback(target.name, min(received / total, 1.0))
            if inspect.isawaitable(result):
                await result


class HTTPSource:
    def __init__(self):
        self.session = None
        self.last_error = None

    async def _get_session(self) -> PublicSession:
        if self.session is None or self.session.closed:
            self.session = PublicSession(timeout=aiohttp.ClientTimeout(total=3600))
        return self.session

    async def download(self, pile: Pile, update_log: UpdateLog,
                       progress_callback: Optional[Callable] = None) -> bool:
        try:
            validate_name(pile.name)
            if not pile.source_url:
                raise ValueError("No source URL provided")
            target = resolve_path(settings.piles_dir, self._get_filename(pile))
            if not await self._download_file(pile.source_url, target, progress_callback):
                raise ValueError(self.last_error or "HTTP download failed")
            pile.file_path = str(target)
            pile.file_size = target.stat().st_size
            pile.file_format = target.suffix.lstrip(".")
            return True
        except Exception as exc:
            logger.error("HTTP import failed: %s", exc)
            update_log.error_message = str(exc)
            return False

    def _get_filename(self, pile: Pile) -> str:
        name = validate_name(pile.name)
        if pile.source_url:
            # URL syntax is decoded once; filesystem paths are never re-decoded.
            candidate = unquote(urlparse(pile.source_url).path.rsplit("/", 1)[-1], errors="strict")
            if candidate and "." in candidate:
                return validate_name(candidate)
        if Path(name).suffix:
            return name
        return validate_name(f"{name}.bin")

    async def _download_file(self, url: str, target_path: Path,
                             progress_callback: Optional[Callable] = None) -> bool:
        try:
            target = validate_stored_path(settings.piles_dir, target_path)
            session = await self._get_session()
            async with session.get(url, max_bytes=settings.max_file_size) as response:
                if response.status != 200:
                    raise ValueError(f"Download failed with HTTP {response.status}")
                await save_chunks(progress_chunks(response, target, progress_callback),
                                  target, settings.max_file_size)
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.error("HTTP download failed: %s", exc)
            return False

    async def get_available_content(self) -> Dict[str, Any]:
        return {"total_count": 0, "categories": {},
                "note": "HTTP source requires manual URL configuration"}

    async def cleanup(self):
        if self.session and not self.session.closed:
            await self.session.close()
