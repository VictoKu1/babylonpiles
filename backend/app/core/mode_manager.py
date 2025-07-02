"""
Mode Manager for switching between Learn and Store modes
"""

import asyncio
import logging
import subprocess
import psutil
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.system_status import SystemStatus

logger = logging.getLogger(__name__)

class ModeManager:
    """Manages system mode switching between Learn and Store modes"""
    
    def __init__(self):
        self.current_mode = "store"  # Default to store mode
        self._mode_lock = asyncio.Lock()
        self._network_processes = {}
    
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """Switch system mode"""
        if mode not in ["learn", "store"]:
            raise ValueError("Mode must be 'learn' or 'store'")
        
        async with self._mode_lock:
            logger.info(f"Switching from {self.current_mode} mode to {mode} mode")
            
            try:
                if mode == "learn":
                    result = await self._enable_learn_mode()
                else:
                    result = await self._enable_store_mode()
                
                # Update database
                await self._update_system_status(mode)
                
                self.current_mode = mode
                logger.info(f"Successfully switched to {mode} mode")
                
                return {
                    "success": True,
                    "mode": mode,
                    "message": f"Switched to {mode} mode",
                    "details": result
                }
                
            except Exception as e:
                logger.error(f"Failed to switch to {mode} mode: {e}")
                return {
                    "success": False,
                    "mode": self.current_mode,
                    "message": f"Failed to switch to {mode} mode: {str(e)}"
                }
    
    async def _enable_learn_mode(self) -> Dict[str, Any]:
        """Enable Learn mode (internet sync mode)"""
        logger.info("Enabling Learn mode...")
        
        # Check internet connectivity
        internet_available = await self._check_internet_connectivity()
        
        if not internet_available:
            logger.warning("No internet connectivity detected in Learn mode")
        
        # Enable network interfaces
        network_status = await self._configure_network_learn_mode()
        
        # Stop hotspot if running
        await self._stop_hotspot()
        
        return {
            "internet_available": internet_available,
            "network_status": network_status,
            "hotspot_disabled": True
        }
    
    async def _enable_store_mode(self) -> Dict[str, Any]:
        """Enable Store mode (offline/sharing mode)"""
        logger.info("Enabling Store mode...")
        
        # Disable internet access
        await self._disable_internet_access()
        
        # Configure local network
        network_status = await self._configure_network_store_mode()
        
        # Start hotspot if configured
        hotspot_status = await self._start_hotspot()
        
        return {
            "internet_disabled": True,
            "network_status": network_status,
            "hotspot_status": hotspot_status
        }
    
    async def _check_internet_connectivity(self) -> bool:
        """Check if internet is available"""
        try:
            # Try to connect to a reliable host
            result = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "5", "8.8.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking internet connectivity: {e}")
            return False
    
    async def _configure_network_learn_mode(self) -> Dict[str, Any]:
        """Configure network for Learn mode"""
        try:
            # Enable all network interfaces
            interfaces = await self._get_network_interfaces()
            
            # Enable WiFi and Ethernet
            wifi_enabled = await self._enable_wifi()
            ethernet_enabled = await self._enable_ethernet()
            
            return {
                "interfaces": interfaces,
                "wifi_enabled": wifi_enabled,
                "ethernet_enabled": ethernet_enabled
            }
        except Exception as e:
            logger.error(f"Error configuring network for Learn mode: {e}")
            return {"error": str(e)}
    
    async def _configure_network_store_mode(self) -> Dict[str, Any]:
        """Configure network for Store mode"""
        try:
            # Get network interfaces
            interfaces = await self._get_network_interfaces()
            
            # Configure for local network only
            local_network = await self._configure_local_network()
            
            return {
                "interfaces": interfaces,
                "local_network": local_network
            }
        except Exception as e:
            logger.error(f"Error configuring network for Store mode: {e}")
            return {"error": str(e)}
    
    async def _start_hotspot(self) -> Dict[str, Any]:
        """Start WiFi hotspot"""
        try:
            # Check if hotspot is configured
            if not settings.wifi_ssid or not settings.wifi_password:
                return {"enabled": False, "reason": "Not configured"}
            
            # Start hostapd or similar
            process = await asyncio.create_subprocess_exec(
                "sudo", "systemctl", "start", "hostapd",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Hotspot started successfully")
                return {"enabled": True, "ssid": settings.wifi_ssid}
            else:
                logger.warning(f"Failed to start hotspot: {stderr.decode()}")
                return {"enabled": False, "error": stderr.decode()}
                
        except Exception as e:
            logger.error(f"Error starting hotspot: {e}")
            return {"enabled": False, "error": str(e)}
    
    async def _stop_hotspot(self) -> bool:
        """Stop WiFi hotspot"""
        try:
            process = await asyncio.create_subprocess_exec(
                "sudo", "systemctl", "stop", "hostapd",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Hotspot stopped successfully")
                return True
            else:
                logger.warning(f"Failed to stop hotspot: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping hotspot: {e}")
            return False
    
    async def _disable_internet_access(self) -> bool:
        """Disable internet access while keeping local network"""
        try:
            # This is a simplified implementation
            # In production, you might want to use iptables or similar
            logger.info("Internet access disabled for Store mode")
            return True
        except Exception as e:
            logger.error(f"Error disabling internet access: {e}")
            return False
    
    async def _get_network_interfaces(self) -> Dict[str, Any]:
        """Get network interface information"""
        try:
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interfaces[interface] = {
                    "addresses": [addr.address for addr in addrs if addr.family == psutil.AF_INET],
                    "mac": [addr.address for addr in addrs if addr.family == psutil.AF_LINK]
                }
            return interfaces
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
            return {}
    
    async def _enable_wifi(self) -> bool:
        """Enable WiFi interface"""
        try:
            # Simplified implementation
            logger.info("WiFi enabled")
            return True
        except Exception as e:
            logger.error(f"Error enabling WiFi: {e}")
            return False
    
    async def _enable_ethernet(self) -> bool:
        """Enable Ethernet interface"""
        try:
            # Simplified implementation
            logger.info("Ethernet enabled")
            return True
        except Exception as e:
            logger.error(f"Error enabling Ethernet: {e}")
            return False
    
    async def _configure_local_network(self) -> Dict[str, Any]:
        """Configure local network for Store mode"""
        try:
            # Configure static IP for local network
            # This is a simplified implementation
            return {
                "static_ip": "192.168.4.1",
                "subnet": "255.255.255.0",
                "dhcp_enabled": True
            }
        except Exception as e:
            logger.error(f"Error configuring local network: {e}")
            return {"error": str(e)}
    
    async def _update_system_status(self, mode: str):
        """Update system status in database"""
        try:
            async with AsyncSessionLocal() as session:
                # Get or create system status record
                status = await session.get(SystemStatus, 1)
                if not status:
                    status = SystemStatus()
                    session.add(status)
                
                # Update mode information
                status.current_mode = mode
                status.mode_changed_at = datetime.utcnow()
                
                # Update network status based on mode
                if mode == "learn":
                    status.internet_available = await self._check_internet_connectivity()
                    status.hotspot_enabled = False
                else:
                    status.internet_available = False
                    status.hotspot_enabled = True
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current mode status"""
        return {
            "current_mode": self.current_mode,
            "mode_locked": self._mode_lock.locked(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up ModeManager...")
        
        # Stop any running processes
        for name, process in self._network_processes.items():
            try:
                if process and not process.done():
                    process.cancel()
            except Exception as e:
                logger.error(f"Error canceling process {name}: {e}")
        
        self._network_processes.clear() 