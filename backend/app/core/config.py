"""
Configuration management for BabylonPiles
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "BabylonPiles"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")

    # Database
    database_url: str = Field(default="sqlite:///./babylonpiles.db", env="DATABASE_URL")

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production", env="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Storage
    data_dir: str = Field(default="/mnt/babylonpiles/data", env="DATA_DIR")
    piles_dir: str = Field(default="/mnt/babylonpiles/piles", env="PILES_DIR")
    temp_dir: str = Field(default="/tmp/babylonpiles", env="TEMP_DIR")

    # Network
    wifi_ssid: str = Field(default="BabylonPiles", env="WIFI_SSID")
    wifi_password: str = Field(default="babylonpiles123", env="WIFI_PASSWORD")

    # Mode settings
    default_mode: str = Field(default="store", env="DEFAULT_MODE")

    # Update settings
    auto_update_enabled: bool = Field(default=False, env="AUTO_UPDATE_ENABLED")
    update_schedule: str = Field(
        default="0 2 * * *", env="UPDATE_SCHEDULE"
    )  # Daily at 2 AM

    # Content sources
    kiwix_library_url: str = Field(
        default="https://library.kiwix.org", env="KIWIX_LIBRARY_URL"
    )
    osm_planet_url: str = Field(
        default="https://planet.openstreetmap.org", env="OSM_PLANET_URL"
    )

    # File size limits
    max_file_size: int = Field(default=1024 * 1024 * 1024, env="MAX_FILE_SIZE")  # 1GB
    max_upload_size: int = Field(
        default=100 * 1024 * 1024, env="MAX_UPLOAD_SIZE"
    )  # 100MB

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Ensure directories exist - DISABLED to prevent automatic storage allocation
# Users must manually add storage through the UI
def ensure_directories():
    """Ensure all required directories exist - DISABLED for manual control"""
    # This function is disabled to prevent automatic storage allocation
    # Users must manually add storage through the storage management UI
    pass


# Initialize directories on import - DISABLED
# ensure_directories()
