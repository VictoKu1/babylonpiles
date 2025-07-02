"""
System Manager for monitoring and managing system resources
"""

import asyncio
import logging
import psutil
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.system_status import SystemStatus

logger = logging.getLogger(__name__)

class SystemManager:
    """Manages system monitoring and resources"""
    
    def __init__(self):
        self._monitoring_task = None
        self._monitoring_interval = 30  # seconds
        self._running = False
    
    async def start_monitoring(self):
        """Start system monitoring"""
        if self._running:
            logger.warning("System monitoring already running")
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_system())
        logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")
    
    async def _monitor_system(self):
        """System monitoring loop"""
        while self._running:
            try:
                await self._update_system_status()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(self._monitoring_interval)
    
    async def _update_system_status(self):
        """Update system status in database"""
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(settings.data_dir)
            
            # Get storage information
            storage_info = await self._get_storage_info()
            
            # Get content statistics
            content_stats = await self._get_content_statistics()
            
            # Get network information
            network_info = await self._get_network_info()
            
            # Get system information
            system_info = await self._get_system_info()
            
            # Update database
            async with AsyncSessionLocal() as session:
                status = await session.get(SystemStatus, 1)
                if not status:
                    status = SystemStatus()
                    session.add(status)
                
                # Update metrics
                status.cpu_usage_percent = cpu_usage
                status.memory_usage_percent = memory.percent
                status.disk_usage_percent = (disk.used / disk.total) * 100
                
                # Update storage
                status.total_storage_bytes = storage_info.get("total_bytes")
                status.used_storage_bytes = storage_info.get("used_bytes")
                status.available_storage_bytes = storage_info.get("available_bytes")
                
                # Update content statistics
                status.total_piles = content_stats.get("total_piles", 0)
                status.active_piles = content_stats.get("active_piles", 0)
                status.downloading_piles = content_stats.get("downloading_piles", 0)
                status.total_content_size_bytes = content_stats.get("total_size_bytes", 0)
                
                # Update system info
                status.system_info = system_info
                status.network_info = network_info
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
    
    async def _get_storage_info(self) -> Dict[str, Any]:
        """Get storage information"""
        try:
            # Check main data directory
            data_path = Path(settings.data_dir)
            if not data_path.exists():
                return {"error": "Data directory does not exist"}
            
            # Get disk usage
            disk_usage = psutil.disk_usage(str(data_path))
            
            return {
                "total_bytes": disk_usage.total,
                "used_bytes": disk_usage.used,
                "available_bytes": disk_usage.free,
                "usage_percent": (disk_usage.used / disk_usage.total) * 100
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}
    
    async def _get_content_statistics(self) -> Dict[str, Any]:
        """Get content statistics"""
        try:
            from app.models.pile import Pile
            from sqlalchemy import select, func
            
            async with AsyncSessionLocal() as session:
                # Get pile counts
                result = await session.execute(
                    select(func.count(Pile.id))
                )
                total_piles = result.scalar() or 0
                
                result = await session.execute(
                    select(func.count(Pile.id)).where(Pile.is_active == True)
                )
                active_piles = result.scalar() or 0
                
                result = await session.execute(
                    select(func.count(Pile.id)).where(Pile.is_downloading == True)
                )
                downloading_piles = result.scalar() or 0
                
                # Get total content size
                result = await session.execute(
                    select(func.sum(Pile.file_size)).where(Pile.file_size.isnot(None))
                )
                total_size_bytes = result.scalar() or 0
                
                return {
                    "total_piles": total_piles,
                    "active_piles": active_piles,
                    "downloading_piles": downloading_piles,
                    "total_size_bytes": total_size_bytes
                }
                
        except Exception as e:
            logger.error(f"Error getting content statistics: {e}")
            return {
                "total_piles": 0,
                "active_piles": 0,
                "downloading_piles": 0,
                "total_size_bytes": 0
            }
    
    async def _get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
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
            network_info["connections"] = len(connections)
            
            return network_info
            
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            return {"error": str(e)}
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": psutil.sys.platform,
                "python_version": psutil.sys.version,
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "memory_total": psutil.virtual_memory().total,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "hostname": psutil.sys.gethostname(),
                "pid": os.getpid()
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            async with AsyncSessionLocal() as session:
                status = await session.get(SystemStatus, 1)
                if status:
                    return status.to_dict()
                else:
                    return {"error": "No system status found"}
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get detailed storage usage"""
        try:
            storage_info = await self._get_storage_info()
            
            # Get directory sizes
            piles_dir = Path(settings.piles_dir)
            if piles_dir.exists():
                piles_size = sum(f.stat().st_size for f in piles_dir.rglob('*') if f.is_file())
                storage_info["piles_size_bytes"] = piles_size
            
            return storage_info
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup system manager"""
        logger.info("Cleaning up SystemManager...")
        await self.stop_monitoring() 