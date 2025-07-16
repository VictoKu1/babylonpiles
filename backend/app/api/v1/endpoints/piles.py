"""
Piles endpoints for managing content modules
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, List, Optional
import os
import shutil
from pathlib import Path
import aiohttp
import asyncio
from urllib.parse import urlparse

from app.core.database import get_db
from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.schemas.pile import PileCreate, PileUpdate, PileResponse

router = APIRouter()

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
        if pile.file_path and os.path.exists(pile.file_path):
            try:
                os.remove(pile.file_path)
            except Exception as e:
                logger.warning(f"Could not delete file {pile.file_path}: {e}")
        
        # Delete pile from database
        await db.delete(pile)
        await db.commit()
        
        return {
            "success": True,
            "message": "Pile deleted successfully"
        }
    except HTTPException:
        raise
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
        file_extension = Path(file.filename).suffix if file.filename else ""
        filename = f"{pile.name}{file_extension}"
        file_path = piles_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
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
        
        if not pile.file_path or not os.path.exists(pile.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile file not found"
            )
        
        return FileResponse(
            pile.file_path,
            filename=os.path.basename(pile.file_path),
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
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
async def download_pile_source(
    pile_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Download content from the pile's source URL"""
    try:
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        if not pile.source_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pile has no source URL"
            )
        
        # Set downloading status
        pile.is_downloading = True
        pile.download_progress = 0.0
        await db.commit()
        
        try:
            # Create data directory if it doesn't exist
            data_dir = Path(settings.data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename from URL
            parsed_url = urlparse(pile.source_url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = f"{pile.name}.{pile.source_type}"
            
            file_path = data_dir / filename
            
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(pile.source_url) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to download from source: HTTP {response.status}"
                        )
                    
                    # Get content length for progress tracking
                    content_length = response.headers.get('content-length')
                    total_size = int(content_length) if content_length else None
                    downloaded_size = 0
                    
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # Update progress (but don't commit too frequently)
                            if total_size and downloaded_size % (1024 * 1024) == 0:  # Every 1MB
                                pile.download_progress = downloaded_size / total_size
                                await db.commit()
            
            # Update pile with file information
            pile.file_path = str(file_path)
            pile.file_size = os.path.getsize(file_path)
            pile.file_format = Path(filename).suffix.lstrip(".")
            pile.is_downloading = False
            pile.download_progress = 1.0
            pile.is_active = True
            
            await db.commit()
            await db.refresh(pile)
            
            return {
                "success": True,
                "data": pile.to_dict(),
                "message": f"Successfully downloaded {filename}"
            }
            
        except Exception as e:
            # Reset downloading status on error
            try:
                pile.is_downloading = False
                pile.download_progress = 0.0
                await db.commit()
            except:
                # If commit fails, rollback and try again
                await db.rollback()
                pile.is_downloading = False
                pile.download_progress = 0.0
                await db.commit()
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        try:
            await db.rollback()
        except:
            pass  # Ignore rollback errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading pile source: {str(e)}"
        )

@router.post("/validate-url")
async def validate_url(url: str = Form(...)) -> Dict[str, Any]:
    """Validate if a URL is accessible"""
    allowed_domains = {"example.com", "another-allowed-domain.com"}
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                "success": False,
                "valid": False,
                "message": "Invalid URL format"
            }
        # Resolve the hostname to an IP address
        hostname = parsed_url.hostname
        resolved_ip = (await asyncio.get_event_loop().getaddrinfo(hostname, None))[0][4][0]
        # Check if the domain is in the allowed list
        if hostname not in allowed_domains:
            return {
                "success": False,
                "valid": False,
                "message": "Domain not allowed"
            }
        # Check if the resolved IP is private or loopback
        if resolved_ip.startswith("10.") or resolved_ip.startswith("192.168.") or resolved_ip.startswith("172.") or resolved_ip == "127.0.0.1":
            return {
                "success": False,
                "valid": False,
                "message": "Access to private or loopback IPs is not allowed"
            }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as response:
                if response.status == 200:
                    # Get content length if available
                    content_length = response.headers.get('content-length')
                    file_size = int(content_length) if content_length else None
                    # Don't read the body, just close
                    await response.release()
                    return {
                        "success": True,
                        "valid": True,
                        "status_code": response.status,
                        "file_size": file_size,
                        "message": "URL is accessible"
                    }
                else:
                    return {
                        "success": True,
                        "valid": False,
                        "status_code": response.status,
                        "message": f"URL returned status code {response.status}"
                    }
    except asyncio.TimeoutError:
        return {
            "success": True,
            "valid": False,
            "message": "URL validation timed out"
        }
    except Exception as e:
        return {
            "success": True,
            "valid": False,
            "message": f"Error validating URL: {str(e)}"
        } 