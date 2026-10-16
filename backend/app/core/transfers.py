"""Bounded content transfers with atomic publication and failure cleanup."""
import os
import tempfile
from pathlib import Path
from app.core.paths import _reject_symlinks, validate_name

CHUNK_SIZE = 64 * 1024


class TransferTooLarge(ValueError):
    """The actual received bytes exceed the configured limit."""


async def save_chunks(chunks_async_iter, target: Path, max_size: int) -> int:
    """Stage a bounded async byte stream and replace target only on success."""
    target = Path(target)
    validate_name(target.name)
    _reject_symlinks(target)
    if max_size <= 0:
        raise ValueError("Transfer limit must be positive")
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlinks(target)
    descriptor, temporary = tempfile.mkstemp(prefix=".transfer-", dir=target.parent)
    received = 0
    try:
        with os.fdopen(descriptor, "wb") as output:
            async for chunk in chunks_async_iter:
                received += len(chunk)
                if received > max_size:
                    raise TransferTooLarge("File exceeds the configured size limit")
                output.write(chunk)
        _reject_symlinks(target)
        os.replace(temporary, target)
        return received
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


async def save_upload(upload, target: Path, max_size: int) -> int:
    async def chunks():
        while chunk := await upload.read(CHUNK_SIZE):
            yield chunk
    return await save_chunks(chunks(), target, max_size)
