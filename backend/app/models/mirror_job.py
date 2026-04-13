"""
Mirror job model for vendored EmergencyStorage mirror tasks.
"""

from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MirrorJob(Base):
    """Persisted mirror job configuration."""

    __tablename__ = "mirror_jobs"
    __table_args__ = (
        UniqueConstraint("provider", "variant", name="uq_mirror_jobs_provider_variant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    variant = Column(String(50), nullable=False, index=True)
    destination_subpath = Column(String(255), nullable=False)

    enabled = Column(Boolean, default=True, nullable=False)
    schedule_enabled = Column(Boolean, default=False, nullable=False)
    schedule_frequency = Column(String(20), default="disabled", nullable=False)
    schedule_time_utc = Column(String(5), default="02:00", nullable=False)
    schedule_day = Column(Integer, nullable=True)

    status = Column(String(20), default="idle", nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    runs = relationship("MirrorRun", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self, latest_run: Optional["MirrorRun"] = None) -> Dict[str, Any]:
        """Convert the mirror job to an API dictionary."""
        return {
            "id": self.id,
            "provider": self.provider,
            "variant": self.variant,
            "destination_subpath": self.destination_subpath,
            "enabled": self.enabled,
            "schedule_enabled": self.schedule_enabled,
            "schedule_frequency": self.schedule_frequency,
            "schedule_time_utc": self.schedule_time_utc,
            "schedule_day": self.schedule_day,
            "status": self.status,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "latest_run": latest_run.to_dict() if latest_run else None,
        }
