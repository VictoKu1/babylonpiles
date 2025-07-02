"""
Pydantic schemas for pile data validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class PileBase(BaseModel):
    """Base pile schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique pile name")
    display_name: str = Field(..., min_length=1, max_length=255, description="Human readable name")
    description: Optional[str] = Field(None, description="Pile description")
    category: str = Field(..., min_length=1, max_length=100, description="Pile category")
    source_type: str = Field(..., description="Source type (kiwix, torrent, http, local)")
    source_url: Optional[str] = Field(None, description="Source URL")
    source_config: Optional[Dict[str, Any]] = Field(None, description="Additional source configuration")
    tags: Optional[List[str]] = Field(None, description="List of tags")

class PileCreate(PileBase):
    """Schema for creating a new pile"""
    pass

class PileUpdate(BaseModel):
    """Schema for updating a pile"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class PileResponse(PileBase):
    """Schema for pile response"""
    id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    version: Optional[str] = None
    checksum: Optional[str] = None
    last_updated: Optional[datetime] = None
    is_active: bool
    is_downloading: bool
    download_progress: float
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PileStatus(BaseModel):
    """Schema for pile status"""
    id: int
    name: str
    display_name: str
    status: str  # ready, downloading, pending, inactive
    progress: float
    file_size: Optional[int] = None
    last_updated: Optional[datetime] = None

class PileSummary(BaseModel):
    """Schema for pile summary"""
    total_piles: int
    active_piles: int
    downloading_piles: int
    total_size_bytes: int
    categories: List[str] 