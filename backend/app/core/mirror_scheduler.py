"""
Background scheduler and executor for mirrored EmergencyStorage jobs.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.mirror_schedules import compute_next_run_at, utc_now
from app.core.mirrorer_client import MirrorerClient
from app.models.mirror_job import MirrorJob
from app.models.mirror_run import MirrorRun

logger = logging.getLogger(__name__)


class MirrorQueueError(Exception):
    """Raised when a mirror job cannot be queued."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class MirrorExecutionSnapshot:
    """Immutable execution arguments captured before the async run starts."""

    job_id: int
    run_id: int
    provider: str
    variant: str
    destination_subpath: str
    schedule_enabled: bool
    schedule_frequency: str
    schedule_time_utc: str
    schedule_day: Optional[int]
    enabled: bool


class MirrorScheduler:
    """Poll due mirror jobs and dispatch them through the adapter service."""

    def __init__(self):
        self.poll_interval_seconds = settings.mirror_scheduler_poll_seconds
        self.client = MirrorerClient(settings.mirrorer_url)
        self._poll_task: Optional[asyncio.Task] = None
        self._run_tasks: Dict[int, asyncio.Task] = {}

    async def start(self):
        """Start scheduler polling and reconcile stale state."""
        if self._poll_task is not None and not self._poll_task.done():
            return

        await self._recover_stale_state()
        self._poll_task = asyncio.create_task(self._poll_loop(), name="mirror-scheduler")
        logger.info("Mirror scheduler started")

    async def stop(self):
        """Stop scheduler polling and active run tasks."""
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        for task in list(self._run_tasks.values()):
            task.cancel()
        if self._run_tasks:
            await asyncio.gather(*self._run_tasks.values(), return_exceptions=True)
        self._run_tasks.clear()

        await self.client.close()
        logger.info("Mirror scheduler stopped")

    async def queue_job(self, job_id: int) -> Dict[str, object]:
        """Queue a manual mirror run for execution."""
        snapshot, run_dict = await self._claim_and_create_run(job_id)
        task = asyncio.create_task(
            self._execute_run(snapshot),
            name=f"mirror-run-{snapshot.run_id}",
        )
        self._run_tasks[snapshot.run_id] = task
        task.add_done_callback(lambda _: self._run_tasks.pop(snapshot.run_id, None))
        return run_dict

    async def _poll_loop(self):
        """Poll due jobs forever until cancelled."""
        while True:
            try:
                due_job_ids = await self._get_due_job_ids()
                for job_id in due_job_ids:
                    try:
                        await self.queue_job(job_id)
                    except MirrorQueueError:
                        continue
                    except Exception as exc:
                        logger.error("Failed to queue due mirror job %s: %s", job_id, exc)
            except Exception as exc:
                logger.error("Mirror scheduler poll failed: %s", exc)

            await asyncio.sleep(self.poll_interval_seconds)

    async def _get_due_job_ids(self) -> List[int]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MirrorJob.id)
                .where(MirrorJob.enabled == True)
                .where(MirrorJob.schedule_enabled == True)
                .where(MirrorJob.schedule_frequency != "disabled")
                .where(MirrorJob.next_run_at.is_not(None))
                .where(MirrorJob.next_run_at <= utc_now())
                .where(MirrorJob.status != "running")
                .order_by(MirrorJob.next_run_at.asc())
            )
            return list(result.scalars().all())

    async def _claim_and_create_run(self, job_id: int) -> Tuple[MirrorExecutionSnapshot, Dict[str, object]]:
        async with AsyncSessionLocal() as session:
            job = await session.get(MirrorJob, job_id)
            if job is None:
                raise MirrorQueueError(404, "Mirror job not found")
            if not job.enabled:
                raise MirrorQueueError(400, "Mirror job is disabled")

            claim_result = await session.execute(
                update(MirrorJob)
                .where(MirrorJob.id == job_id)
                .where(MirrorJob.status != "running")
                .values(status="running", last_error=None)
            )
            if claim_result.rowcount != 1:
                await session.rollback()
                raise MirrorQueueError(409, "Mirror job is already running")

            started_at = utc_now()
            run = MirrorRun(
                job_id=job_id,
                status="running",
                started_at=started_at,
            )
            session.add(run)
            await session.flush()

            job = await session.get(MirrorJob, job_id)
            job.last_run_at = started_at

            await session.commit()
            await session.refresh(job)
            await session.refresh(run)

            snapshot = MirrorExecutionSnapshot(
                job_id=job.id,
                run_id=run.id,
                provider=job.provider,
                variant=job.variant,
                destination_subpath=job.destination_subpath,
                schedule_enabled=job.schedule_enabled,
                schedule_frequency=job.schedule_frequency,
                schedule_time_utc=job.schedule_time_utc,
                schedule_day=job.schedule_day,
                enabled=job.enabled,
            )
            return snapshot, run.to_dict()

    async def _execute_run(self, snapshot: MirrorExecutionSnapshot):
        """Run a claimed mirror job against the mirrorer adapter."""
        try:
            adapter_response = await self.client.run_job(
                run_id=snapshot.run_id,
                provider=snapshot.provider,
                variant=snapshot.variant,
                destination_subpath=snapshot.destination_subpath,
            )
            exit_code = int(adapter_response.get("exit_code", -1))
            run_status = "completed" if exit_code == 0 else "failed"
            error_message = adapter_response.get("error_message")
            await self._finalize_run(
                snapshot=snapshot,
                run_status=run_status,
                exit_code=exit_code,
                bytes_downloaded=int(adapter_response.get("bytes_downloaded", 0)),
                log_path=adapter_response.get("log_path"),
                error_message=error_message,
            )
        except httpx.HTTPError as exc:
            await self._finalize_run(
                snapshot=snapshot,
                run_status="failed",
                exit_code=-1,
                bytes_downloaded=0,
                log_path=None,
                error_message=f"Mirrorer request failed: {exc}",
            )
        except asyncio.CancelledError:
            await self._finalize_run(
                snapshot=snapshot,
                run_status="failed",
                exit_code=-1,
                bytes_downloaded=0,
                log_path=None,
                error_message="Mirror run was cancelled",
            )
            raise
        except Exception as exc:
            await self._finalize_run(
                snapshot=snapshot,
                run_status="failed",
                exit_code=-1,
                bytes_downloaded=0,
                log_path=None,
                error_message=str(exc),
            )

    async def _finalize_run(
        self,
        snapshot: MirrorExecutionSnapshot,
        run_status: str,
        exit_code: int,
        bytes_downloaded: int,
        log_path: Optional[str],
        error_message: Optional[str],
    ):
        finished_at = utc_now()
        async with AsyncSessionLocal() as session:
            job = await session.get(MirrorJob, snapshot.job_id)
            run = await session.get(MirrorRun, snapshot.run_id)
            if job is None or run is None:
                return

            run.status = run_status
            run.finished_at = finished_at
            run.exit_code = exit_code
            run.bytes_downloaded = bytes_downloaded
            run.log_path = log_path
            run.error_message = error_message

            job.status = run_status
            job.last_run_at = finished_at
            job.last_error = error_message if run_status == "failed" else None
            job.next_run_at = compute_next_run_at(
                schedule_enabled=job.enabled and job.schedule_enabled,
                schedule_frequency=job.schedule_frequency,
                schedule_time_utc=job.schedule_time_utc,
                schedule_day=job.schedule_day,
                reference_time=finished_at,
            )

            await session.commit()

    async def _recover_stale_state(self):
        """Mark interrupted running jobs as failed after a backend restart."""
        recovery_time = utc_now()
        async with AsyncSessionLocal() as session:
            run_result = await session.execute(select(MirrorRun).where(MirrorRun.status == "running"))
            stale_runs = run_result.scalars().all()
            for run in stale_runs:
                run.status = "failed"
                run.finished_at = recovery_time
                run.exit_code = -1
                run.error_message = run.error_message or "Mirror run interrupted by backend restart"

            job_result = await session.execute(select(MirrorJob).where(MirrorJob.status == "running"))
            stale_jobs = job_result.scalars().all()
            for job in stale_jobs:
                job.status = "failed"
                job.last_error = "Mirror job interrupted by backend restart"
                job.next_run_at = compute_next_run_at(
                    schedule_enabled=job.enabled and job.schedule_enabled,
                    schedule_frequency=job.schedule_frequency,
                    schedule_time_utc=job.schedule_time_utc,
                    schedule_day=job.schedule_day,
                    reference_time=recovery_time,
                )

            await session.commit()
