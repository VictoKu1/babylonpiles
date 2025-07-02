"""
UpdateLog model for tracking content updates and version history
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from typing import Optional, Dict, Any

class UpdateLog(Base):
    """UpdateLog model for tracking content updates"""
    
    __tablename__ = "update_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    pile_id = Column(Integer, ForeignKey("piles.id"), nullable=False)
    
    # Update information
    update_type = Column(String(50), nullable=False)  # download, update, rollback, delete
    status = Column(String(20), nullable=False)  # pending, running, completed, failed
    source_url = Column(String(500), nullable=True)
    
    # File information
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)
    version = Column(String(50), nullable=True)
    
    # Progress and timing
    progress = Column(Integer, default=0)  # 0-100
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    pile = relationship("Pile", backref="update_logs")
    
    def __repr__(self):
        return f"<UpdateLog(pile_id={self.pile_id}, type='{self.update_type}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert update log to dictionary"""
        return {
            "id": self.id,
            "pile_id": self.pile_id,
            "update_type": self.update_type,
            "status": self.status,
            "source_url": self.source_url,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "version": self.version,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "metadata": self.metadata,
        }
    
    @property
    def is_completed(self) -> bool:
        """Check if update is completed"""
        return self.status in ["completed", "failed"]
    
    @property
    def is_running(self) -> bool:
        """Check if update is running"""
        return self.status == "running"
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration"""
        if not self.duration_seconds:
            return "Unknown"
        
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s" 