"""
Main API router for BabylonPiles
"""

from fastapi import APIRouter, Depends
from app.api.v1.endpoints import piles, system, auth, updates, files, storage, mirrors

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(system.public_router, prefix="/system", tags=["public-content"])
for route, prefix, tag in [
    (system.router, "/system", "system"), (piles.router, "/piles", "piles"),
    (updates.router, "/updates", "updates"), (mirrors.router, "/mirrors", "mirrors"),
    (files.router, "/files", "files"), (storage.router, "/storage", "storage"),
]:
    api_router.include_router(route, prefix=prefix, tags=[tag], dependencies=[Depends(auth.require_admin)])
