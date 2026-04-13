"""
Schedule utilities for mirrored EmergencyStorage jobs.
"""

import calendar
from datetime import datetime, timedelta
from typing import Optional, Tuple


def utc_now() -> datetime:
    """Return a naive UTC timestamp for consistent storage in SQLite."""
    return datetime.utcnow().replace(microsecond=0)


def parse_schedule_time(schedule_time_utc: str) -> Tuple[int, int]:
    """Parse an HH:MM UTC string into hour/minute integers."""
    hour_text, minute_text = schedule_time_utc.split(":", maxsplit=1)
    return int(hour_text), int(minute_text)


def compute_next_run_at(
    schedule_enabled: bool,
    schedule_frequency: str,
    schedule_time_utc: str,
    schedule_day: Optional[int],
    reference_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """Compute the next UTC run time for the fixed v1 schedules."""
    if not schedule_enabled or schedule_frequency == "disabled":
        return None

    now = reference_time or utc_now()
    hour, minute = parse_schedule_time(schedule_time_utc)

    if schedule_frequency == "daily":
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if schedule_frequency == "weekly":
        if schedule_day is None:
            return None
        current_day = (now.weekday() + 1) % 7  # Sunday = 0 ... Saturday = 6
        days_until = (schedule_day - current_day) % 7
        candidate = (now + timedelta(days=days_until)).replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    if schedule_frequency == "monthly":
        if schedule_day is None:
            return None
        year = now.year
        month = now.month
        while True:
            last_day = calendar.monthrange(year, month)[1]
            target_day = min(schedule_day, last_day)
            candidate = datetime(year, month, target_day, hour, minute, 0)
            if candidate > now:
                return candidate

            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

    return None
