"""
SystemStatus model for tracking system state and metrics
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from typing import Optional, Dict, Any

class SystemStatus(Base):
    """SystemStatus model for tracking system state"""
    
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # System mode
    current_mode = Column(String(20), nullable=False)  # learn, store
    mode_changed_at = Column(DateTime, default=func.now())
    
    # Network status
    internet_available = Column(Boolean, default=False)
    wifi_enabled = Column(Boolean, default=False)
    ethernet_enabled = Column(Boolean, default=False)
    hotspot_enabled = Column(Boolean, default=False)
    
    # Storage information
    total_storage_bytes = Column(Integer, nullable=True)
    used_storage_bytes = Column(Integer, nullable=True)
    available_storage_bytes = Column(Integer, nullable=True)
    
    # System metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    
    # Content statistics
    total_piles = Column(Integer, default=0)
    active_piles = Column(Integer, default=0)
    downloading_piles = Column(Integer, default=0)
    total_content_size_bytes = Column(Integer, default=0)
    
    # Update status
    last_update_check = Column(DateTime, nullable=True)
    updates_available = Column(Integer, default=0)
    auto_update_enabled = Column(Boolean, default=False)
    
    # System information
    system_info = Column(JSON, nullable=True)  # OS, version, etc.
    network_info = Column(JSON, nullable=True)  # IP addresses, interfaces
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemStatus(mode='{self.current_mode}', internet={self.internet_available})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system status to dictionary"""
        return {
            "id": self.id,
            "current_mode": self.current_mode,
            "mode_changed_at": self.mode_changed_at.isoformat() if self.mode_changed_at else None,
            "internet_available": self.internet_available,
            "wifi_enabled": self.wifi_enabled,
            "ethernet_enabled": self.ethernet_enabled,
            "hotspot_enabled": self.hotspot_enabled,
            "total_storage_bytes": self.total_storage_bytes,
            "used_storage_bytes": self.used_storage_bytes,
            "available_storage_bytes": self.available_storage_bytes,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "temperature_celsius": self.temperature_celsius,
            "total_piles": self.total_piles,
            "active_piles": self.active_piles,
            "downloading_piles": self.downloading_piles,
            "total_content_size_bytes": self.total_content_size_bytes,
            "last_update_check": self.last_update_check.isoformat() if self.last_update_check else None,
            "updates_available": self.updates_available,
            "auto_update_enabled": self.auto_update_enabled,
            "system_info": self.system_info,
            "network_info": self.network_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def storage_usage_percent(self) -> Optional[float]:
        """Calculate storage usage percentage"""
        if self.total_storage_bytes and self.used_storage_bytes:
            return (self.used_storage_bytes / self.total_storage_bytes) * 100
        return None
    
    @property
    def storage_human(self) -> Dict[str, str]:
        """Get human readable storage information"""
        def format_bytes(bytes_value: Optional[int]) -> str:
            if not bytes_value:
                return "Unknown"
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        
        return {
            "total": format_bytes(self.total_storage_bytes),
            "used": format_bytes(self.used_storage_bytes),
            "available": format_bytes(self.available_storage_bytes),
            "usage_percent": f"{self.storage_usage_percent:.1f}%" if self.storage_usage_percent else "Unknown"
        }
    
    @property
    def content_size_human(self) -> str:
        """Get human readable content size"""
        if not self.total_content_size_bytes:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.total_content_size_bytes < 1024.0:
                return f"{self.total_content_size_bytes:.1f} {unit}"
            self.total_content_size_bytes /= 1024.0
        return f"{self.total_content_size_bytes:.1f} PB" 