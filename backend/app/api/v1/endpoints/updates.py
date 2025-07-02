"""
Updates endpoints for managing content updates and version control
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, List, Optional
import asyncio
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.modules.updater import ContentUpdater

router = APIRouter()
logger = logging.getLogger(__name__)

# Global updater instance
content_updater: ContentUpdater = None

def get_content_updater() -> ContentUpdater:
    """Get content updater instance"""
    if content_updater is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content updater not initialized"
        )
    return content_updater

@router.get("/")
async def get_update_logs(
    pile_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get update logs with optional filtering"""
    try:
        query = select(UpdateLog).order_by(UpdateLog.started_at.desc())
        
        if pile_id:
            query = query.where(UpdateLog.pile_id == pile_id)
        
        if status:
            query = query.where(UpdateLog.status == status)
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return {
            "success": True,
            "data": [log.to_dict() for log in logs],
            "total": len(logs)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting update logs: {str(e)}"
        )

@router.get("/{log_id}")
async def get_update_log(
    log_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific update log"""
    try:
        result = await db.execute(select(UpdateLog).where(UpdateLog.id == log_id))
        log = result.scalar_one_or_none()
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Update log not found"
            )
        
        return {
            "success": True,
            "data": log.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting update log: {str(e)}"
        )

@router.post("/pile/{pile_id}")
async def update_pile(
    pile_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger update for a specific pile"""
    try:
        # Get pile
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Check if pile is already downloading
        if pile.is_downloading:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pile is already being updated"
            )
        
        # Create update log
        update_log = UpdateLog(
            pile_id=pile_id,
            update_type="update",
            status="pending",
            source_url=pile.source_url
        )
        
        db.add(update_log)
        await db.commit()
        await db.refresh(update_log)
        
        # Start update in background
        background_tasks.add_task(
            run_pile_update,
            pile_id,
            update_log.id,
            db
        )
        
        return {
            "success": True,
            "data": {
                "update_log_id": update_log.id,
                "message": "Update started"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting update: {str(e)}"
        )

@router.post("/pile/{pile_id}/rollback")
async def rollback_pile(
    pile_id: int,
    version: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Rollback pile to previous version"""
    try:
        # Get pile
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        if not pile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pile not found"
            )
        
        # Create rollback log
        update_log = UpdateLog(
            pile_id=pile_id,
            update_type="rollback",
            status="pending",
            version=version
        )
        
        db.add(update_log)
        await db.commit()
        await db.refresh(update_log)
        
        # Perform rollback
        updater = get_content_updater()
        success = await updater.rollback_pile(pile, version)
        
        if success:
            update_log.status = "completed"
        else:
            update_log.status = "failed"
            update_log.error_message = "Rollback failed"
        
        await db.commit()
        
        return {
            "success": success,
            "data": update_log.to_dict(),
            "message": "Rollback completed" if success else "Rollback failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rolling back pile: {str(e)}"
        )

@router.post("/bulk")
async def bulk_update(
    category: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger bulk update for multiple piles"""
    try:
        # Get piles to update
        query = select(Pile).where(Pile.is_active == True)
        if category:
            query = query.where(Pile.category == category)
        
        result = await db.execute(query)
        piles = result.scalars().all()
        
        if not piles:
            return {
                "success": True,
                "data": {
                    "message": "No piles to update",
                    "updated_count": 0
                }
            }
        
        # Create update logs for each pile
        update_logs = []
        for pile in piles:
            if not pile.is_downloading:  # Skip if already downloading
                update_log = UpdateLog(
                    pile_id=pile.id,
                    update_type="update",
                    status="pending",
                    source_url=pile.source_url
                )
                db.add(update_log)
                update_logs.append(update_log)
        
        await db.commit()
        
        # Start updates in background
        if background_tasks:
            for update_log in update_logs:
                background_tasks.add_task(
                    run_pile_update,
                    update_log.pile_id,
                    update_log.id,
                    db
                )
        
        return {
            "success": True,
            "data": {
                "message": f"Started updates for {len(update_logs)} piles",
                "updated_count": len(update_logs),
                "update_logs": [log.id for log in update_logs]
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting bulk update: {str(e)}"
        )

@router.get("/status")
async def get_update_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get overall update status"""
    try:
        # Get recent update logs
        result = await db.execute(
            select(UpdateLog)
            .order_by(UpdateLog.started_at.desc())
            .limit(10)
        )
        recent_logs = result.scalars().all()
        
        # Count by status
        result = await db.execute(
            select(UpdateLog.status, UpdateLog.id)
        )
        status_counts = {}
        for log in result.all():
            status_counts[log[0]] = status_counts.get(log[0], 0) + 1
        
        # Get currently downloading piles
        result = await db.execute(
            select(Pile).where(Pile.is_downloading == True)
        )
        downloading_piles = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "recent_logs": [log.to_dict() for log in recent_logs],
                "status_counts": status_counts,
                "downloading_piles": [pile.to_dict() for pile in downloading_piles],
                "total_downloading": len(downloading_piles)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting update status: {str(e)}"
        )

async def run_pile_update(pile_id: int, log_id: int, db: AsyncSession):
    """Background task to run pile update"""
    try:
        # Get pile and log
        result = await db.execute(select(Pile).where(Pile.id == pile_id))
        pile = result.scalar_one_or_none()
        
        result = await db.execute(select(UpdateLog).where(UpdateLog.id == log_id))
        update_log = result.scalar_one_or_none()
        
        if not pile or not update_log:
            logger.error(f"Pile or update log not found: pile_id={pile_id}, log_id={log_id}")
            return
        
        # Update log status
        update_log.status = "running"
        await db.commit()
        
        # Mark pile as downloading
        pile.is_downloading = True
        pile.download_progress = 0.0
        await db.commit()
        
        # Run update
        updater = get_content_updater()
        success = await updater.update_pile(pile, update_log)
        
        # Update final status
        if success:
            update_log.status = "completed"
            pile.is_downloading = False
            pile.download_progress = 1.0
        else:
            update_log.status = "failed"
            pile.is_downloading = False
            pile.download_progress = 0.0
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error in background update: {e}")
        try:
            # Update status to failed
            result = await db.execute(select(UpdateLog).where(UpdateLog.id == log_id))
            update_log = result.scalar_one_or_none()
            if update_log:
                update_log.status = "failed"
                update_log.error_message = str(e)
                await db.commit()
            
            # Reset pile status
            result = await db.execute(select(Pile).where(Pile.id == pile_id))
            pile = result.scalar_one_or_none()
            if pile:
                pile.is_downloading = False
                pile.download_progress = 0.0
                await db.commit()
        except Exception as cleanup_error:
            logger.error(f"Error in cleanup: {cleanup_error}") 