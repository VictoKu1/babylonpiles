"""
Piles endpoints for managing content modules
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, List, Optional
import os
import tempfile
from pathlib import Path
import aiohttp
import asyncio
from urllib.parse import urljoin
import json
from fastapi import Response
from bs4 import BeautifulSoup
import re

from app.core.database import get_db
from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.schemas.pile import PileCreate, PileUpdate, PileResponse
from app.modules.sources.gutenberg import GutenbergSource
from app.core.public_http import PublicSession, validate_url as public_url
from app.core.paths import validate_name, resolve_path, validate_stored_path
from app.core.transfers import save_upload, save_chunks, TransferTooLarge

router = APIRouter()


def sources_catalog():
    path = Path(settings.state_dir) / "sources.json"
    seed = Path(__file__).resolve().parents[2] / "sources.json"
    with (path if path.exists() else seed).open(encoding="utf-8") as source:
        return json.load(source)


def managed_pile_path(value):
    # Older database rows must satisfy the same boundary as new uploads.
    for root in (settings.piles_dir, settings.data_dir):
        try:
            return validate_stored_path(root, value)
        except ValueError:
            pass
    raise HTTPException(status_code=400, detail="Invalid stored content path")

@router.get("/")
async def get_piles(
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get all piles with optional filtering"""
    try:
        query = select(Pile)
        
        if category:
            query = query.where(Pile.category == category)
        
        if status:
            if status == "active":
                query = query.where(Pile.is_active == True)
            elif status == "downloading":
                query = query.where(Pile.is_downloading == True)
            elif status == "ready":
                query = query.where(Pile.file_path.isnot(None))
        
        result = await db.execute(query)
        piles = result.scalars().all()
        
        return {
            "success": True,
            "data": [pile.to_dict() for pile in piles],
            "total": len(piles)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting piles: {str(e)}"
        )

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get all available categories"""
    try:
        from sqlalchemy import distinct
        
        result = await db.execute(select(distinct(Pile.category)))
        categories = result.scalars().all()
        
        return {
            "success": True,
            "data": categories
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting categories: {str(e)}"
        )

@router.get("/sources-list")
async def get_sources_list():
    """Serve the sources.json file for Quick Add dynamic source listing (new format)."""
    return sources_catalog()

@router.post("/add-source")
async def add_source(request: Request):
    """Add or update a source in sources.json. Accepts JSON: {name, repo_url, info_url (nullable)}. Returns updated sources list."""
    data = await request.json()
    name = data.get('name')
    repo_url = data.get('repo_url')
    info_url = data.get('info_url')
    if not isinstance(name, str) or not name.strip() or len(name) > 200 or not isinstance(repo_url, str):
        raise HTTPException(status_code=400, detail="Name and repo_url are required.")
    public_url(repo_url)
    if info_url not in (None, "None", ""):
        if not isinstance(info_url, str):
            raise HTTPException(status_code=400, detail="Invalid info_url")
        public_url(info_url)
    sources = sources_catalog()
    # Store info_url as 'None' string if None for frontend compatibility
    sources[name] = [repo_url, info_url if info_url is not None else 'None']
    sources_path = Path(settings.state_dir) / "sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=sources_path.parent, prefix="sources-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)
        os.replace(temporary, sources_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return sources

@router.get("/browse-source")
async def browse_source(url: str, description_url: str = None):
    """List the immediate children (files/folders) of a directory URL for any source. Optionally accept a description_url for future use."""
    public_url(url)
    skip_names = {"Name", "Last modified", "Size", "Description", "README"}
    async with PublicSession(max_bytes=settings.max_catalog_size) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            items = []
            pre = soup.find("pre")
            if pre:
                for line in pre.text.splitlines():
                    m = re.match(r"\s*(.+?)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+([\d\.]+[KMG]?)?", line)
                    if not m:
                        continue
                    name = m.group(1).strip()
                    last_modified = m.group(2).strip() if m.lastindex >= 2 else None
                    size_str = m.group(3).strip() if m.lastindex >= 3 else None
                    size = None
                    if size_str:
                        try:
                            if size_str.endswith("K"):
                                size = int(float(size_str[:-1]) * 1024)
                            elif size_str.endswith("M"):
                                size = int(float(size_str[:-1]) * 1024 * 1024)
                            elif size_str.endswith("G"):
                                size = int(float(size_str[:-1]) * 1024 * 1024 * 1024)
                            else:
                                size = int(size_str)
                        except Exception:
                            size = None
                    link = pre.find("a", string=name)
                    if not link:
                        continue
                    href = link.get("href")
                    if (
                        not href or
                        name == "Parent Directory" or
                        name.upper() == "README" or
                        name in skip_names or
                        href.startswith("?C=")
                    ):
                        continue
                    is_dir = href.endswith("/")
                    items.append({
                        "name": name,
                        "url": urljoin(url, href),
                        "is_dir": is_dir,
                        "size": size if not is_dir else None,
                        "last_modified": last_modified
                    })
            return {"items": items}

@router.get("/file-info")
async def file_info(filename: str, description_url: str):
    """Return selected metadata as JSON text, never executable source markup."""
    public_url(description_url)
    async with PublicSession(max_bytes=settings.max_catalog_size) as session:
        async with session.get(description_url) as resp:
            resp.raise_for_status()
            content = await resp.text()
            soup = BeautifulSoup(content, "html.parser")
            # Instead of matching any attribute containing the filename, match the 'name' attribute that starts with the base filename
            base_filename = filename.rstrip('_')
            entry = None
            # Try to match the base filename against the 'url' attribute as well as 'name'
            for tag in soup.find_all(True):
                url_attr = tag.attrs.get('url')
                if url_attr and re.search(rf'{re.escape(base_filename)}', url_attr):
                    entry = tag
                    break
            if not entry:
                for tag in soup.find_all(True):
                    name_attr = tag.attrs.get('name')
                    if name_attr and re.match(rf'^{re.escape(base_filename)}(_|$)', name_attr):
                        entry = tag
                        break
            if not entry:
                for tag in soup.find_all(True):
                    if any(filename in str(v) for v in tag.attrs.values()):
                        entry = tag
                        break
            if not entry:
                entry = soup.find(lambda tag: tag.string and filename in tag.string)
            if not entry:
                return {"found": False}
            return {"found": True, **{
                key: str(entry.attrs.get(key, ""))
                for key in ("title", "description", "language", "creator", "publisher")
            }}


@router.get("/gutenberg-search")
async def gutenberg_search(query: str):
    """Search the public Gutenberg catalogue before the dynamic pile route."""
    source = GutenbergSource()
    results = await source.get_available_content(query)
    return {"success": True, "data": results}

@router.get("/{pile_id}")
async def get_pile(
    pile_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific pile by ID"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        return {
            "success": True,
            "data": pile.to_dict()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pile: {str(e)}"
        )

@router.post("/")
async def create_pile(
    pile_data: PileCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new pile"""
    try:
        # Check if pile with same name already exists
        existing = await db.execute(
            select(Pile).where(Pile.name == pile_data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pile with this name already exists"
            )
        
        # Create new pile
        pile = Pile(
            name=pile_data.name,
            display_name=pile_data.display_name,
            description=pile_data.description,
            category=pile_data.category,
            source_type=pile_data.source_type,
            source_url=pile_data.source_url,
            source_config=pile_data.source_config,
            tags=pile_data.tags
        )
        
        db.add(pile)
        await db.commit()
        await db.refresh(pile)
        
        return {
            "success": True,
            "data": pile.to_dict(),
            "message": "Pile created successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating pile: {str(e)}"
        )

@router.put("/{pile_id}")
async def update_pile(
    pile_id: int,
    pile_data: PileUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update a pile"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Update fields
        update_data = pile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pile, field, value)
        
        await db.commit()
        await db.refresh(pile)
        
        return {
            "success": True,
            "data": pile.to_dict(),
            "message": "Pile updated successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating pile: {str(e)}"
        )

@router.delete("/{pile_id}")
async def delete_pile(
    pile_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a pile"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Delete associated file if it exists
        if pile.file_path:
            file_path = managed_pile_path(pile.file_path)
            file_path.unlink(missing_ok=True)
        
        # Delete pile from database
        await db.delete(pile)
        await db.commit()
        
        return {
            "success": True,
            "message": "Pile deleted successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting pile: {str(e)}"
        )

@router.post("/{pile_id}/upload")
async def upload_pile_file(
    pile_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Upload a file for a pile"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Create piles directory if it doesn't exist
        piles_dir = Path(settings.piles_dir)
        piles_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        validate_name(pile.name)
        original_name = validate_name(file.filename or "upload")
        file_extension = Path(original_name).suffix
        filename = f"{pile.name}{file_extension}"
        file_path = resolve_path(piles_dir, filename)
        
        # Save file
        await save_upload(file, file_path, settings.max_upload_size)
        
        # Update pile with file information
        pile.file_path = str(file_path)
        pile.file_size = os.path.getsize(file_path)
        pile.file_format = file_extension.lstrip(".")
        pile.is_active = True
        
        await db.commit()
        await db.refresh(pile)
        
        return {
            "success": True,
            "data": pile.to_dict(),
            "message": "File uploaded successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/{pile_id}/download")
async def download_pile_file(
    pile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download a pile file"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        file_path = managed_pile_path(pile.file_path) if pile.file_path else None
        if not file_path or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile file not found"
            )
        
        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )

@router.post("/{pile_id}/toggle")
async def toggle_pile_status(
    pile_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle pile active status"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Toggle status
        pile.is_active = not pile.is_active
        
        await db.commit()
        await db.refresh(pile)
        
        return {
            "success": True,
            "data": pile.to_dict(),
            "message": f"Pile {'activated' if pile.is_active else 'deactivated'} successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=413 if isinstance(e, TransferTooLarge) else 400, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling pile status: {str(e)}"
        )

@router.get("/{pile_id}/logs")
async def get_pile_logs(
    pile_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get update logs for a pile"""
    try:
        result = await db.execute(
            select(UpdateLog)
            .where(UpdateLog.pile_id == pile_id)
            .order_by(UpdateLog.started_at.desc())
            .limit(limit)
        )
        logs = result.scalars().all()
        
        return {
            "success": True,
            "data": [log.to_dict() for log in logs]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pile logs: {str(e)}"
        )

@router.post("/{pile_id}/download-source")
async def download_pile_source(pile_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Import content atomically, inside managed storage and the public network boundary."""
    pile = (await db.execute(select(Pile).where(Pile.id == pile_id))).scalar_one_or_none()
    if not pile:
        raise HTTPException(status_code=404, detail="Pile not found")
    if pile.is_downloading:
        raise HTTPException(status_code=409, detail="Pile is already being downloaded")
    if pile.source_type == "torrent":
        raise HTTPException(status_code=400, detail="Torrent imports are disabled. Download with a trusted local client and upload the resulting file.")
    try:
        validate_name(pile.name)
        if pile.source_type == "gutenberg":
            GutenbergSource._book_id(pile.source_url)
        else:
            url = public_url(pile.source_url)
            filename = validate_name(url.path.rsplit("/", 1)[-1] or f"{pile.name}.bin")
            target = resolve_path(settings.data_dir, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pile.is_downloading = True
    pile.download_progress = 0.0
    await db.commit()
    try:
        async def progress(name, fraction):
            pile.download_progress = fraction
            await db.commit()

        if pile.source_type == "gutenberg":
            log = UpdateLog(pile_id=pile.id, update_type="download", status="running")
            if not await GutenbergSource().download(pile, log, progress):
                raise ValueError(log.error_message or "Book import failed")
        else:
            from app.modules.sources.http import progress_chunks
            async with PublicSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    size = await save_chunks(progress_chunks(response, target, progress),
                                             target, settings.max_file_size)
            pile.file_path = str(target)
            pile.file_size = size
            pile.file_format = target.suffix.lstrip(".")
        pile.is_downloading = False
        pile.download_progress = 1.0
        pile.is_active = True
        await db.commit()
        await db.refresh(pile)
        return {"success": True, "data": pile.to_dict(), "message": "Content downloaded successfully"}
    except BaseException as exc:
        await db.rollback()
        # Use a SQL update rather than reading ORM state expired by rollback.
        await db.execute(update(Pile).where(Pile.id == pile_id).values(is_downloading=False, download_progress=0.0))
        await db.commit()
        if isinstance(exc, TransferTooLarge):
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError)):
            raise HTTPException(status_code=502, detail="Content source could not be downloaded") from exc
        raise


@router.post("/validate-url")
async def validate_url(url: str = Form(...)) -> Dict[str, Any]:
    """Check public source response headers without downloading its body."""
    try:
        async with PublicSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                content_length = response.headers.get("content-length")
                return {"success": True, "valid": response.status == 200,
                        "status_code": response.status,
                        "file_size": int(content_length) if content_length else None,
                        "message": "URL is accessible" if response.status == 200 else "URL returned an error"}
    except (ValueError, aiohttp.ClientError, asyncio.TimeoutError):
        return {"success": True, "valid": False, "message": "URL is unavailable or not an allowed public source"}
