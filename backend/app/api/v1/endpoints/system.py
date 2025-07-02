"""
System endpoints for mode switching and status monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from app.core.database import get_db
from app.core.mode_manager import ModeManager
from app.core.system import SystemManager
from app.models.system_status import SystemStatus
from sqlalchemy import select

router = APIRouter()

# Global managers (will be set by main.py)
mode_manager: ModeManager = None
system_manager: SystemManager = None

def get_mode_manager() -> ModeManager:
    """Get mode manager instance"""
    if mode_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mode manager not initialized"
        )
    return mode_manager

def get_system_manager() -> SystemManager:
    """Get system manager instance"""
    if system_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System manager not initialized"
        )
    return system_manager

@router.get("/status")
async def get_system_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get system status"""
    try:
        # Get latest system status from database
        result = await db.execute(select(SystemStatus).order_by(SystemStatus.id.desc()).limit(1))
        status_record = result.scalar_one_or_none()
        
        if status_record:
            return {
                "success": True,
                "data": status_record.to_dict()
            }
        else:
            return {
                "success": True,
                "data": {
                    "current_mode": "store",
                    "internet_available": False,
                    "total_piles": 0,
                    "active_piles": 0
                }
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system status: {str(e)}"
        )

@router.get("/mode")
async def get_current_mode() -> Dict[str, Any]:
    """Get current system mode"""
    try:
        mode_mgr = get_mode_manager()
        status = await mode_mgr.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting mode status: {str(e)}"
        )

@router.post("/mode")
async def switch_mode(
    mode: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Switch system mode"""
    if mode not in ["learn", "store"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'learn' or 'store'"
        )
    
    try:
        mode_mgr = get_mode_manager()
        result = await mode_mgr.set_mode(mode)
        
        return {
            "success": result["success"],
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching mode: {str(e)}"
        )

@router.get("/storage")
async def get_storage_info() -> Dict[str, Any]:
    """Get storage information"""
    try:
        sys_mgr = get_system_manager()
        storage_info = await sys_mgr.get_storage_usage()
        
        return {
            "success": True,
            "data": storage_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting storage info: {str(e)}"
        )

@router.get("/network")
async def get_network_info() -> Dict[str, Any]:
    """Get network information"""
    try:
        import psutil
        
        network_info = {}
        
        # Get network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            network_info[interface] = {
                "addresses": [],
                "mac": None
            }
            
            for addr in addrs:
                if addr.family == psutil.AF_INET:
                    network_info[interface]["addresses"].append(addr.address)
                elif addr.family == psutil.AF_LINK:
                    network_info[interface]["mac"] = addr.address
        
        # Get network connections
        connections = psutil.net_connections()
        network_info["total_connections"] = len(connections)
        
        return {
            "success": True,
            "data": network_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting network info: {str(e)}"
        )

@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        import psutil
        
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Temperature (if available)
        try:
            temperature = psutil.sensors_temperatures()
        except:
            temperature = None
        
        metrics = {
            "cpu": {
                "usage_percent": cpu_usage,
                "count": cpu_count
            },
            "memory": {
                "total_bytes": memory.total,
                "used_bytes": memory.used,
                "available_bytes": memory.available,
                "usage_percent": memory.percent
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "usage_percent": (disk.used / disk.total) * 100
            },
            "temperature": temperature
        }
        
        return {
            "success": True,
            "data": metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system metrics: {str(e)}"
        )

@router.post("/restart")
async def restart_system() -> Dict[str, Any]:
    """Restart the system (admin only)"""
    try:
        # This is a placeholder - in production you'd want proper authentication
        import subprocess
        import asyncio
        
        # Schedule restart
        process = await asyncio.create_subprocess_exec(
            "sudo", "reboot",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        return {
            "success": True,
            "message": "System restart initiated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restarting system: {str(e)}"
        )

@router.post("/shutdown")
async def shutdown_system() -> Dict[str, Any]:
    """Shutdown the system (admin only)"""
    try:
        # This is a placeholder - in production you'd want proper authentication
        import subprocess
        import asyncio
        
        # Schedule shutdown
        process = await asyncio.create_subprocess_exec(
            "sudo", "shutdown", "-h", "now",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        return {
            "success": True,
            "message": "System shutdown initiated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error shutting down system: {str(e)}"
        ) 