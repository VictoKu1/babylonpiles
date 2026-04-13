"""
Mirror job endpoints for the vendored EmergencyStorage adapter.
"""

from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.mirror_catalog import get_destination_subpath, get_provider_catalog
from app.core.mirror_scheduler import MirrorQueueError, MirrorScheduler
from app.core.mirror_schedules import compute_next_run_at
from app.models.mirror_job import MirrorJob
from app.models.mirror_run import MirrorRun
from app.schemas.mirror import MirrorJobCreate, MirrorJobUpdate

router = APIRouter()

mirror_scheduler: Optional[MirrorScheduler] = None


def set_mirror_scheduler(scheduler: MirrorScheduler):
    """Register the global mirror scheduler instance."""
    global mirror_scheduler
    mirror_scheduler = scheduler


def get_mirror_scheduler() -> MirrorScheduler:
    if mirror_scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mirror scheduler not initialized",
        )
    return mirror_scheduler


async def _get_latest_run(db: AsyncSession, job_id: int) -> Optional[MirrorRun]:
    result = await db.execute(
        select(MirrorRun)
        .where(MirrorRun.job_id == job_id)
        .order_by(desc(MirrorRun.started_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


def _tail_file(path: Path, tail: int) -> str:
    lines = deque(maxlen=tail)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


async def _job_to_dict(db: AsyncSession, job: MirrorJob) -> Dict[str, Any]:
    latest_run = await _get_latest_run(db, job.id)
    return job.to_dict(latest_run=latest_run)


@router.get("/providers")
async def get_mirror_providers() -> Dict[str, Any]:
    """Return the fixed v1 mirrored provider catalog."""
    return {"success": True, "data": get_provider_catalog()}


@router.get("/jobs")
async def list_mirror_jobs(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """List mirror jobs and their latest run state."""
    result = await db.execute(select(MirrorJob).order_by(MirrorJob.provider.asc(), MirrorJob.variant.asc()))
    jobs = result.scalars().all()
    return {
        "success": True,
        "data": [await _job_to_dict(db, job) for job in jobs],
    }


@router.post("/jobs")
async def create_mirror_job(
    payload: MirrorJobCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new persisted mirror job."""
    existing = await db.execute(
        select(MirrorJob).where(
            MirrorJob.provider == payload.provider.value,
            MirrorJob.variant == payload.variant.value,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A mirror job for this provider/variant already exists",
        )

    job = MirrorJob(
        provider=payload.provider.value,
        variant=payload.variant.value,
        destination_subpath=get_destination_subpath(payload.provider.value, payload.variant.value),
        enabled=payload.enabled,
        schedule_enabled=payload.schedule_enabled,
        schedule_frequency=payload.schedule_frequency.value,
        schedule_time_utc=payload.schedule_time_utc,
        schedule_day=payload.schedule_day,
        status="idle",
        next_run_at=compute_next_run_at(
            schedule_enabled=payload.enabled and payload.schedule_enabled,
            schedule_frequency=payload.schedule_frequency.value,
            schedule_time_utc=payload.schedule_time_utc,
            schedule_day=payload.schedule_day,
        ),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"success": True, "data": await _job_to_dict(db, job)}


@router.put("/jobs/{job_id}")
async def update_mirror_job(
    job_id: int,
    payload: MirrorJobUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update a mirror job configuration."""
    job = await db.get(MirrorJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mirror job not found")
    if job.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mirror job is running")

    merged = {
        "provider": payload.provider.value if payload.provider else job.provider,
        "variant": payload.variant.value if payload.variant else job.variant,
        "enabled": payload.enabled if payload.enabled is not None else job.enabled,
        "schedule_enabled": payload.schedule_enabled if payload.schedule_enabled is not None else job.schedule_enabled,
        "schedule_frequency": payload.schedule_frequency.value if payload.schedule_frequency else job.schedule_frequency,
        "schedule_time_utc": payload.schedule_time_utc if payload.schedule_time_utc is not None else job.schedule_time_utc,
        "schedule_day": payload.schedule_day if payload.schedule_day is not None else job.schedule_day,
    }

    validated = MirrorJobCreate.model_validate(merged)

    duplicate = await db.execute(
        select(MirrorJob).where(
            MirrorJob.provider == validated.provider.value,
            MirrorJob.variant == validated.variant.value,
            MirrorJob.id != job_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another mirror job already uses this provider/variant",
        )

    job.provider = validated.provider.value
    job.variant = validated.variant.value
    job.enabled = validated.enabled
    job.schedule_enabled = validated.schedule_enabled
    job.schedule_frequency = validated.schedule_frequency.value
    job.schedule_time_utc = validated.schedule_time_utc
    job.schedule_day = validated.schedule_day
    job.destination_subpath = get_destination_subpath(job.provider, job.variant)
    job.next_run_at = compute_next_run_at(
        schedule_enabled=job.enabled and job.schedule_enabled,
        schedule_frequency=job.schedule_frequency,
        schedule_time_utc=job.schedule_time_utc,
        schedule_day=job.schedule_day,
    )

    await db.commit()
    await db.refresh(job)
    return {"success": True, "data": await _job_to_dict(db, job)}


@router.post("/jobs/{job_id}/run")
async def run_mirror_job(
    job_id: int,
    scheduler: MirrorScheduler = Depends(get_mirror_scheduler),
) -> Dict[str, Any]:
    """Queue a manual mirror run."""
    try:
        run = await scheduler.queue_job(job_id)
    except MirrorQueueError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return {"success": True, "data": run}


@router.get("/jobs/{job_id}/runs")
async def list_mirror_runs(
    job_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return recent runs for a mirror job."""
    job = await db.get(MirrorJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mirror job not found")

    result = await db.execute(
        select(MirrorRun)
        .where(MirrorRun.job_id == job_id)
        .order_by(desc(MirrorRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    return {"success": True, "data": [run.to_dict() for run in runs]}


@router.get("/runs/{run_id}/logs")
async def get_mirror_run_logs(
    run_id: int,
    tail: int = Query(default=40, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the local or proxied log tail for a mirror run."""
    run = await db.get(MirrorRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mirror run not found")

    content = ""
    if run.log_path:
        log_path = Path(run.log_path)
        if log_path.exists():
            content = _tail_file(log_path, tail)

    if not content:
        scheduler = get_mirror_scheduler()
        try:
            remote = await scheduler.client.get_logs(run_id, tail)
            content = remote.get("content", "")
        except Exception:
            content = ""

    return {
        "success": True,
        "data": {
            "run_id": run_id,
            "log_path": run.log_path,
            "content": content,
        },
    }
