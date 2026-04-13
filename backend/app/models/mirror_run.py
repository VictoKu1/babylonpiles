"""
Mirror run model for tracking execution history of mirror jobs.
"""

from typing import Any, Dict

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MirrorRun(Base):
    """Execution history for a single mirror job run."""

    __tablename__ = "mirror_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("mirror_jobs.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued")
    started_at = Column(DateTime, default=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)
    bytes_downloaded = Column(BigInteger, nullable=False, default=0)
    log_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    job = relationship("MirrorJob", back_populates="runs")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the mirror run to an API dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "exit_code": self.exit_code,
            "bytes_downloaded": int(self.bytes_downloaded or 0),
            "log_path": self.log_path,
            "error_message": self.error_message,
        }
