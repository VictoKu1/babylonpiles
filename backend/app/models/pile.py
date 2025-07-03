"""
Pile model for content modules
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from typing import Optional, Dict, Any

class Pile(Base):
    """Pile model representing a content module"""
    
    __tablename__ = "piles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    
    # Source information
    source_type = Column(String(50), nullable=False)  # kiwix, torrent, http, local
    source_url = Column(String(500), nullable=True)
    source_config = Column(JSON, nullable=True)  # Additional source configuration
    
    # File information
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    file_format = Column(String(50), nullable=True)  # zim, pdf, zip, etc.
    
    # Version control
    version = Column(String(50), nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA256 hash
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Status
    is_active = Column(Boolean, default=True)
    is_downloading = Column(Boolean, default=False)
    download_progress = Column(Float, default=0.0)  # 0.0 to 1.0
    
    # Metadata
    pile_metadata = Column(JSON, nullable=True)  # Additional metadata
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Pile(name='{self.name}', category='{self.category}', version='{self.version}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pile to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_format": self.file_format,
            "version": self.version,
            "checksum": self.checksum,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active,
            "is_downloading": self.is_downloading,
            "download_progress": self.download_progress,
            "metadata": self.pile_metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def size_human(self) -> str:
        """Human readable file size"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} PB"
    
    @property
    def status(self) -> str:
        """Get pile status"""
        if self.is_downloading:
            return "downloading"
        elif not self.is_active:
            return "inactive"
        elif self.file_path and self.file_size:
            return "ready"
        else:
            return "pending" 