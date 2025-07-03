"""
Main API router for BabylonPiles
"""

from fastapi import APIRouter
from app.api.v1.endpoints import piles, system, auth, updates, files

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(piles.router, prefix="/piles", tags=["piles"])
api_router.include_router(updates.router, prefix="/updates", tags=["updates"])
api_router.include_router(files.router, prefix="/files", tags=["files"]) 