"""
Schemas for mirrored EmergencyStorage jobs.
"""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.mirror_catalog import is_valid_provider_variant


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class MirrorProvider(str, Enum):
    openstreetmap = "openstreetmap"
    internet_archive = "internet_archive"


class MirrorVariant(str, Enum):
    planet = "planet"
    software = "software"
    music = "music"
    movies = "movies"
    texts = "texts"


class MirrorScheduleFrequency(str, Enum):
    disabled = "disabled"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class MirrorRunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class MirrorJobConfig(BaseModel):
    """Full mirror job configuration used for create/merged update validation."""

    provider: MirrorProvider
    variant: MirrorVariant
    enabled: bool = True
    schedule_enabled: bool = False
    schedule_frequency: MirrorScheduleFrequency = MirrorScheduleFrequency.disabled
    schedule_time_utc: str = Field(default="02:00")
    schedule_day: Optional[int] = None

    @field_validator("schedule_time_utc")
    @classmethod
    def validate_schedule_time(cls, value: str) -> str:
        if not TIME_PATTERN.match(value):
            raise ValueError("schedule_time_utc must be in HH:MM 24-hour UTC format")
        return value

    @model_validator(mode="after")
    def validate_job(self) -> "MirrorJobConfig":
        if not is_valid_provider_variant(self.provider.value, self.variant.value):
            raise ValueError("Invalid provider/variant combination")

        if not self.schedule_enabled:
            self.schedule_frequency = MirrorScheduleFrequency.disabled
            self.schedule_day = None
            return self

        if self.schedule_frequency == MirrorScheduleFrequency.disabled:
            raise ValueError("schedule_frequency cannot be disabled when schedule_enabled is true")

        if self.schedule_frequency == MirrorScheduleFrequency.daily:
            self.schedule_day = None
            return self

        if self.schedule_frequency == MirrorScheduleFrequency.weekly:
            if self.schedule_day is None or self.schedule_day < 0 or self.schedule_day > 6:
                raise ValueError("Weekly schedules require schedule_day between 0 (Sunday) and 6 (Saturday)")
            return self

        if self.schedule_frequency == MirrorScheduleFrequency.monthly:
            if self.schedule_day is None or self.schedule_day < 1 or self.schedule_day > 31:
                raise ValueError("Monthly schedules require schedule_day between 1 and 31")
            return self

        return self


class MirrorJobCreate(MirrorJobConfig):
    """Create payload for a mirror job."""


class MirrorJobUpdate(BaseModel):
    """Partial update payload for a mirror job."""

    provider: Optional[MirrorProvider] = None
    variant: Optional[MirrorVariant] = None
    enabled: Optional[bool] = None
    schedule_enabled: Optional[bool] = None
    schedule_frequency: Optional[MirrorScheduleFrequency] = None
    schedule_time_utc: Optional[str] = None
    schedule_day: Optional[int] = None

    @field_validator("schedule_time_utc")
    @classmethod
    def validate_schedule_time(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not TIME_PATTERN.match(value):
            raise ValueError("schedule_time_utc must be in HH:MM 24-hour UTC format")
        return value
