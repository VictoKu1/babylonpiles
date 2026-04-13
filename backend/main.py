#!/usr/bin/env python3
"""
BabylonPiles Backend API
Main FastAPI application for the offline knowledge NAS system
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.system import SystemManager
from app.core.mode_manager import ModeManager
from app.core.mirror_scheduler import MirrorScheduler
from app.modules.updater import ContentUpdater

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global system managers
system_manager = None
mode_manager = None
content_updater = None
mirror_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global system_manager, mode_manager, content_updater, mirror_scheduler
    
    # Startup
    logger.info("Starting BabylonPiles backend...")
    
    # Initialize database
    await init_db()
    
    # Initialize system managers
    system_manager = SystemManager()
    mode_manager = ModeManager()
    content_updater = ContentUpdater()
    mirror_scheduler = MirrorScheduler()
    
    # Set global managers in endpoints
    from app.api.v1.endpoints.system import set_managers
    from app.api.v1.endpoints.updates import set_content_updater
    from app.api.v1.endpoints.mirrors import set_mirror_scheduler
    set_managers(mode_manager, system_manager)
    set_content_updater(content_updater)
    set_mirror_scheduler(mirror_scheduler)
    
    # Start in Store mode by default (offline)
    await mode_manager.set_mode("store")
    await mirror_scheduler.start()
    
    logger.info("BabylonPiles backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down BabylonPiles backend...")
    if mirror_scheduler:
        await mirror_scheduler.stop()
    if content_updater:
        await content_updater.cleanup()
    if system_manager:
        await system_manager.cleanup()
    if mode_manager:
        await mode_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="BabylonPiles API",
    description="Offline Knowledge NAS API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for frontend
if os.path.exists("../frontend/dist"):
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mode": mode_manager.current_mode if mode_manager else "unknown",
        "version": "1.0.0"
    }

# Root endpoint redirects to frontend
@app.get("/")
async def root():
    """Root endpoint - serves frontend"""
    if os.path.exists("../frontend/dist/index.html"):
        return FileResponse("../frontend/dist/index.html")
    return {"message": "BabylonPiles API is running. Frontend not found."}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    ) 
