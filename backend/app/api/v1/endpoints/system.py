"""
System endpoints for mode switching and status monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List
from app.core.database import get_db
from app.models.system_status import SystemStatus
from app.models.update_log import UpdateLog
from app.core.system import SystemManager
from app.core.mode_manager import ModeManager
import psutil
import os
import json
from datetime import datetime
import time
import subprocess
import platform
from fastapi.responses import JSONResponse
import logging

router = APIRouter()

# Hotspot configuration
HOTSPOT_CONFIG = {
    "ssid": "BabylonPiles",
    "password": "babylon123",
    "interface": "wlan0",  # Default WiFi interface
    "channel": "6",
    "ip_range": "192.168.4.0/24",
    "gateway_ip": "192.168.4.1"
}

# User configuration
USER_CONFIG_FILE = "/tmp/babylonpiles_user_config.json"

# Store hotspot status and connected devices
hotspot_status = {
    "is_running": False,
    "started_at": None,
    "connected_devices": [],
    "pending_requests": []
}

def load_user_config():
    """Load user configuration from file"""
    try:
        if os.path.exists(USER_CONFIG_FILE):
            with open(USER_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {"user_name": "", "hotspot_name": "BabylonPiles"}
    except Exception:
        return {"user_name": "", "hotspot_name": "BabylonPiles"}

def save_user_config(config):
    """Save user configuration to file"""
    try:
        with open(USER_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving user config: {e}")

def get_hotspot_ssid():
    """Get the current hotspot SSID based on user configuration"""
    config = load_user_config()
    if config.get("user_name"):
        return f"{config['user_name']}BabylonPiles"
    return "BabylonPiles"

def detect_wifi_interface():
    """Detect available WiFi interface on the system"""
    try:
        # Common WiFi interface names
        possible_interfaces = ["wlan0", "wlan1", "wifi0", "wifi1", "wlp2s0", "wlp3s0"]
        
        # Check which interfaces exist
        import subprocess
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        
        for interface in possible_interfaces:
            if interface in result.stdout:
                return interface
        
        # If no common interface found, try to detect any wireless interface
        result = subprocess.run(["iwconfig"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'IEEE' in line and 'ESSID' in line:
                    # Extract interface name
                    interface = line.split()[0]
                    return interface
        
        return "wlan0"  # Default fallback
    except Exception:
        return "wlan0"  # Default fallback

def check_system_requirements():
    """Check if system meets requirements for hotspot"""
    requirements = {
        "hostapd": False,
        "dnsmasq": False,
        "wifi_interface": False,
        "root_privileges": False
    }
    
    try:
        # Check for hostapd
        result = subprocess.run(["which", "hostapd"], capture_output=True)
        requirements["hostapd"] = result.returncode == 0
        
        # Check for dnsmasq
        result = subprocess.run(["which", "dnsmasq"], capture_output=True)
        requirements["dnsmasq"] = result.returncode == 0
        
        # Check for WiFi interface
        interface = detect_wifi_interface()
        requirements["wifi_interface"] = interface != "wlan0" or subprocess.run(["ip", "link", "show", "wlan0"], capture_output=True).returncode == 0
        
        # Check for root privileges (simplified)
        requirements["root_privileges"] = os.geteuid() == 0
        
        return requirements
    except Exception:
        return requirements

def create_hostapd_config(interface, ssid, password, channel):
    """Create hostapd configuration file"""
    config = f"""# BabylonPiles Hotspot Configuration
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
    return config

def create_dnsmasq_config(interface, ip_range, gateway_ip):
    """Create dnsmasq configuration file"""
    config = f"""# BabylonPiles DHCP Configuration
interface={interface}
dhcp-range={ip_range.replace('/24', '.2')},{ip_range.replace('/24', '.20')},255.255.255.0,24h
dhcp-option=3,{gateway_ip}
dhcp-option=6,{gateway_ip}
log-queries
log-dhcp
"""
    return config

# Global managers (will be set by main.py)
mode_manager: ModeManager = None
system_manager: SystemManager = None

DATA_ROOT = "/mnt/babylonpiles/data"

# Add these global variables after the router definition


def set_managers(mode_mgr: ModeManager, sys_mgr: SystemManager):
    """Set global managers"""
    global mode_manager, system_manager
    mode_manager = mode_mgr
    system_manager = sys_mgr


def get_mode_manager() -> ModeManager:
    """Get mode manager instance"""
    if mode_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mode manager not initialized",
        )
    return mode_manager


def get_system_manager() -> SystemManager:
    """Get system manager instance"""
    if system_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System manager not initialized",
        )
    return system_manager


@router.get("/status")
async def get_system_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get system status"""
    try:
        # Get latest system status from database
        result = await db.execute(
            select(SystemStatus).order_by(SystemStatus.id.desc()).limit(1)
        )
        status_record = result.scalar_one_or_none()

        if status_record:
            return {"success": True, "data": status_record.to_dict()}
        else:
            return {
                "success": True,
                "data": {
                    "current_mode": "store",
                    "internet_available": False,
                    "total_piles": 0,
                    "active_piles": 0,
                },
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system status: {str(e)}",
        )


@router.get("/mode")
async def get_current_mode() -> Dict[str, Any]:
    """Get current system mode"""
    try:
        mode_mgr = get_mode_manager()
        status = await mode_mgr.get_status()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting mode status: {str(e)}",
        )


@router.post("/mode")
async def switch_mode(mode: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Switch system mode"""
    if mode not in ["learn", "store"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'learn' or 'store'",
        )

    try:
        mode_mgr = get_mode_manager()
        result = await mode_mgr.set_mode(mode)

        return {"success": result["success"], "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching mode: {str(e)}",
        )


@router.get("/storage")
async def get_storage_info() -> Dict[str, Any]:
    """Get storage information"""
    try:
        sys_mgr = get_system_manager()
        storage_info = await sys_mgr.get_storage_usage()

        return {"success": True, "data": storage_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting storage info: {str(e)}",
        )


@router.get("/network")
async def get_network_info() -> Dict[str, Any]:
    """Get network information"""
    try:
        network_info = {}

        # Get network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            network_info[interface] = {"addresses": [], "mac": None}

            for addr in addrs:
                if addr.family == 2:  # AF_INET
                    network_info[interface]["addresses"].append(addr.address)
                elif addr.family == 17:  # AF_LINK
                    network_info[interface]["mac"] = addr.address

        # Get network connections
        connections = psutil.net_connections()
        network_info["total_connections"] = len(connections)

        return {"success": True, "data": network_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting network info: {str(e)}",
        )


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage
        disk = psutil.disk_usage("/")

        # Temperature (if available)
        try:
            temperature = psutil.sensors_temperatures()
        except:
            temperature = None

        metrics = {
            "cpu": {"usage_percent": cpu_usage, "count": cpu_count},
            "memory": {
                "total_bytes": memory.total,
                "used_bytes": memory.used,
                "available_bytes": memory.available,
                "usage_percent": memory.percent,
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "usage_percent": (disk.used / disk.total) * 100,
            },
            "temperature": temperature,
        }

        return {"success": True, "data": metrics}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system metrics: {str(e)}",
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
            "sudo",
            "reboot",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        return {"success": True, "message": "System restart initiated"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restarting system: {str(e)}",
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
            "sudo",
            "shutdown",
            "-h",
            "now",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        return {"success": True, "message": "System shutdown initiated"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error shutting down system: {str(e)}",
        )


@router.get("/drives")
async def get_available_drives() -> Dict[str, Any]:
    """Get available drives and their storage information"""
    try:
        drives = []

        # Get all disk partitions
        partitions = psutil.disk_partitions()

        for partition in partitions:
            try:
                # Get disk usage for this partition
                usage = psutil.disk_usage(partition.mountpoint)

                drive_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "usage_percent": (
                        (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    ),
                }

                # Format sizes for display
                drive_info["total_formatted"] = _format_bytes(usage.total)
                drive_info["used_formatted"] = _format_bytes(usage.used)
                drive_info["free_formatted"] = _format_bytes(usage.free)

                drives.append(drive_info)

            except (PermissionError, OSError):
                # Skip drives we can't access
                continue

        return {
            "success": True,
            "data": {"drives": drives, "current_data_dir": DATA_ROOT},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting available drives: {str(e)}",
        )


@router.post("/hotspot/start")
async def start_hotspot() -> Dict[str, Any]:
    """Start the WiFi hotspot"""
    try:
        if hotspot_status["is_running"]:
            return {
                "success": True,
                "message": "Hotspot is already running",
                "data": {
                    "ssid": HOTSPOT_CONFIG["ssid"],
                    "password": HOTSPOT_CONFIG["password"],
                    "ip_range": HOTSPOT_CONFIG["ip_range"],
                    "started_at": hotspot_status["started_at"]
                }
            }
        
        # Check system requirements
        requirements = check_system_requirements()
        missing_requirements = []
        
        if not requirements["hostapd"]:
            missing_requirements.append("hostapd")
        if not requirements["dnsmasq"]:
            missing_requirements.append("dnsmasq")
        if not requirements["wifi_interface"]:
            missing_requirements.append("WiFi interface")
        if not requirements["root_privileges"]:
            missing_requirements.append("root privileges")
        
        if missing_requirements:
            return {
                "success": False,
                "message": f"System requirements not met. Missing: {', '.join(missing_requirements)}",
                "data": {
                    "requirements": requirements,
                    "missing": missing_requirements
                }
            }
        
        # Detect WiFi interface
        interface = detect_wifi_interface()
        if interface != HOTSPOT_CONFIG["interface"]:
            # Update config with detected interface
            HOTSPOT_CONFIG["interface"] = interface
        
        # Get personalized SSID
        personalized_ssid = get_hotspot_ssid()
        
        try:
            # Create hostapd configuration
            hostapd_config = create_hostapd_config(
                interface,
                personalized_ssid,  # Use personalized SSID
                HOTSPOT_CONFIG["password"],
                HOTSPOT_CONFIG["channel"]
            )
            
            with open("/tmp/babylonpiles_hostapd.conf", "w") as f:
                f.write(hostapd_config)
            
            # Create dnsmasq configuration
            dnsmasq_config = create_dnsmasq_config(
                interface,
                HOTSPOT_CONFIG["ip_range"],
                HOTSPOT_CONFIG["gateway_ip"]
            )
            
            with open("/tmp/babylonpiles_dnsmasq.conf", "w") as f:
                f.write(dnsmasq_config)
            
            # Configure network interface
            try:
                # Bring interface up
                subprocess.run([
                    "ip", "link", "set", interface, "up"
                ], check=True)
                
                # Configure IP address
                subprocess.run([
                    "ip", "addr", "add", f"{HOTSPOT_CONFIG['gateway_ip']}/24", "dev", interface
                ], check=True)
                
                # Enable IP forwarding
                subprocess.run([
                    "echo", "1", ">", "/proc/sys/net/ipv4/ip_forward"
                ], check=True)
                
                # Configure NAT (optional, for internet sharing)
                subprocess.run([
                    "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"
                ], check=False)  # Don't fail if eth0 doesn't exist
                
            except subprocess.CalledProcessError as e:
                raise Exception(f"Network configuration failed: {str(e)}")
            
            # Start hostapd
            hostapd_process = subprocess.Popen([
                "hostapd", "/tmp/babylonpiles_hostapd.conf"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait a moment for hostapd to start
            time.sleep(2)
            
            # Check if hostapd is running
            if hostapd_process.poll() is not None:
                raise Exception("hostapd failed to start")
            
            # Start dnsmasq
            dnsmasq_process = subprocess.Popen([
                "dnsmasq", "-C", "/tmp/babylonpiles_dnsmasq.conf"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait a moment for dnsmasq to start
            time.sleep(1)
            
            # Check if dnsmasq is running
            if dnsmasq_process.poll() is not None:
                # Kill hostapd if dnsmasq failed
                hostapd_process.terminate()
                raise Exception("dnsmasq failed to start")
            
            hotspot_status["is_running"] = True
            hotspot_status["started_at"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "message": "Hotspot started successfully",
                "data": {
                    "ssid": HOTSPOT_CONFIG["ssid"],
                    "password": HOTSPOT_CONFIG["password"],
                    "ip_range": HOTSPOT_CONFIG["ip_range"],
                    "gateway_ip": HOTSPOT_CONFIG["gateway_ip"],
                    "interface": interface,
                    "started_at": hotspot_status["started_at"],
                    "requirements": requirements
                }
            }
            
        except Exception as e:
            # Cleanup on failure
            subprocess.run(["pkill", "hostapd"], check=False)
            subprocess.run(["pkill", "dnsmasq"], check=False)
            raise Exception(f"Failed to start hotspot: {str(e)}")
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting hotspot: {str(e)}"
        )

@router.post("/hotspot/stop")
async def stop_hotspot() -> Dict[str, Any]:
    """Stop the WiFi hotspot"""
    try:
        if not hotspot_status["is_running"]:
            return {
                "success": True,
                "message": "Hotspot is not running"
            }
        
        # Stop hostapd and dnsmasq
        subprocess.run(["pkill", "-f", "hostapd"], check=False)
        subprocess.run(["pkill", "-f", "dnsmasq"], check=False)
        
        # Wait a moment for processes to stop
        time.sleep(2)
        
        # Clean up network configuration
        try:
            interface = HOTSPOT_CONFIG["interface"]
            
            # Remove IP address
            subprocess.run([
                "ip", "addr", "del", f"{HOTSPOT_CONFIG['gateway_ip']}/24", "dev", interface
            ], check=False)
            
            # Remove NAT rules (if they exist)
            subprocess.run([
                "iptables", "-t", "nat", "-D", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"
            ], check=False)
            
            # Disable IP forwarding
            subprocess.run([
                "echo", "0", ">", "/proc/sys/net/ipv4/ip_forward"
            ], check=False)
            
        except Exception as e:
            print(f"Warning: Network cleanup failed: {e}")
        
        # Clean up configuration files
        try:
            os.remove("/tmp/babylonpiles_hostapd.conf")
        except FileNotFoundError:
            pass
        
        try:
            os.remove("/tmp/babylonpiles_dnsmasq.conf")
        except FileNotFoundError:
            pass
        
        hotspot_status["is_running"] = False
        hotspot_status["started_at"] = None
        hotspot_status["connected_devices"] = []
        
        return {
            "success": True,
            "message": "Hotspot stopped successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping hotspot: {str(e)}"
        )

@router.get("/hotspot/status")
async def get_hotspot_status() -> Dict[str, Any]:
    """Get current hotspot status"""
    try:
        # Check if processes are running
        hostapd_running = False
        dnsmasq_running = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'hostapd' or (proc.info['cmdline'] and 'hostapd' in ' '.join(proc.info['cmdline'])):
                    hostapd_running = True
                elif proc.info['name'] == 'dnsmasq' or (proc.info['cmdline'] and 'dnsmasq' in ' '.join(proc.info['cmdline'])):
                    dnsmasq_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Get connected devices (multiple methods)
        connected_devices = []
        
        # Method 1: Parse DHCP leases
        lease_files = [
            "/var/lib/misc/dnsmasq.leases",
            "/var/lib/dhcp/dnsmasq.leases",
            "/tmp/babylonpiles_dnsmasq.leases"
        ]
        
        for lease_file in lease_files:
            try:
                if os.path.exists(lease_file):
                    with open(lease_file, "r") as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 4:
                                connected_devices.append({
                                    "mac": parts[1],
                                    "ip": parts[2],
                                    "hostname": parts[3] if len(parts) > 3 else "Unknown",
                                    "connected_at": datetime.fromtimestamp(int(parts[0])).isoformat(),
                                    "lease_expires": datetime.fromtimestamp(int(parts[0]) + 86400).isoformat()  # 24h lease
                                })
                    break
            except Exception:
                continue
        
        # Method 2: Check ARP table for connected devices
        if not connected_devices:
            try:
                result = subprocess.run(["arp", "-n"], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n')[1:]:  # Skip header
                        if line.strip() and HOTSPOT_CONFIG["gateway_ip"].split('.')[:-1] in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                connected_devices.append({
                                    "mac": parts[2],
                                    "ip": parts[0],
                                    "hostname": "Unknown",
                                    "connected_at": datetime.now().isoformat(),
                                    "source": "arp"
                                })
            except Exception:
                pass
        
        # Get system information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "wifi_interface": detect_wifi_interface(),
            "requirements": check_system_requirements()
        }
        
        # Get user configuration
        user_config = load_user_config()
        personalized_ssid = get_hotspot_ssid()
        
        return {
            "success": True,
            "data": {
                "is_running": hotspot_status["is_running"] and hostapd_running and dnsmasq_running,
                "ssid": personalized_ssid,  # Use personalized SSID
                "password": HOTSPOT_CONFIG["password"],
                "ip_range": HOTSPOT_CONFIG["ip_range"],
                "gateway_ip": HOTSPOT_CONFIG["gateway_ip"],
                "interface": HOTSPOT_CONFIG["interface"],
                "started_at": hotspot_status["started_at"],
                "connected_devices": connected_devices,
                "pending_requests": hotspot_status["pending_requests"],
                "system_info": system_info,
                "process_status": {
                    "hostapd": hostapd_running,
                    "dnsmasq": dnsmasq_running
                },
                "user_config": user_config
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting hotspot status: {str(e)}"
        )

@router.get("/hotspot/public-content")
async def get_public_content() -> Dict[str, Any]:
    """Get list of public content for hotspot users"""
    try:
        from app.api.v1.endpoints.files import DATA_ROOT, get_file_permission, get_file_metadata
        
        public_files = []
        
        def scan_directory(path: str, relative_path: str = ""):
            try:
                for entry in os.scandir(os.path.join(DATA_ROOT, path)):
                    if entry.name in [".permissions.json", ".metadata.json"]:
                        continue
                    
                    item_path = os.path.join(relative_path, entry.name) if relative_path else entry.name
                    
                    # Check if item is public
                    if get_file_permission(item_path):
                        metadata = get_file_metadata(item_path)
                        stat = entry.stat()
                        
                        public_files.append({
                            "name": entry.name,
                            "path": item_path,
                            "is_dir": entry.is_dir(),
                            "size": stat.st_size if not entry.is_dir() else 0,
                            "size_formatted": format_file_size(stat.st_size) if not entry.is_dir() else "0 B",
                            "creator": metadata.get("creator", "admin"),
                            "created_at": metadata.get("created_at", datetime.fromtimestamp(stat.st_ctime).isoformat()),
                            "download_url": f"/api/v1/hotspot/download/{item_path}" if not entry.is_dir() else None
                        })
                    
                    # Recursively scan subdirectories
                    if entry.is_dir():
                        scan_directory(os.path.join(path, entry.name), item_path)
                        
            except Exception as e:
                print(f"Error scanning directory {path}: {e}")
        
        scan_directory("")
        
        return {
            "success": True,
            "data": {
                "files": public_files,
                "total_files": len([f for f in public_files if not f["is_dir"]]),
                "total_folders": len([f for f in public_files if f["is_dir"]])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting public content: {str(e)}"
        )

@router.get("/hotspot/download/{file_path:path}")
async def download_public_file(file_path: str):
    """Download a public file (for hotspot users)"""
    try:
        from app.api.v1.endpoints.files import DATA_ROOT, get_file_permission
        
        # Check if file is public
        if not get_file_permission(file_path):
            raise HTTPException(
                status_code=403,
                detail="File is not public"
            )
        
        full_path = os.path.join(DATA_ROOT, file_path)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )
        
        return FileResponse(
            full_path,
            filename=os.path.basename(full_path),
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading file: {str(e)}"
        )

@router.post("/hotspot/request-upload")
async def request_content_upload(
    filename: str,
    editor_name: str,
    client_ip: str = None,
    client_mac: str = None
) -> Dict[str, Any]:
    """Request content upload (for hotspot users)"""
    try:
        request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        request_data = {
            "id": request_id,
            "filename": filename,
            "editor_name": editor_name,
            "client_ip": client_ip,
            "client_mac": client_mac,
            "requested_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        hotspot_status["pending_requests"].append(request_data)
        
        return {
            "success": True,
            "message": "Upload request submitted successfully",
            "data": {
                "request_id": request_id,
                "status": "pending",
                "message": "Your request has been submitted and is awaiting administrator approval."
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting upload request: {str(e)}"
        )

@router.post("/hotspot/approve-request/{request_id}")
async def approve_upload_request(request_id: str) -> Dict[str, Any]:
    """Approve an upload request (admin only)"""
    try:
        # Find the request
        request = None
        for req in hotspot_status["pending_requests"]:
            if req["id"] == request_id:
                request = req
                break
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )
        
        if request["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="Request is not pending"
            )
        
        # Update request status
        request["status"] = "approved"
        request["approved_at"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "Upload request approved",
            "data": request
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error approving request: {str(e)}"
        )

@router.post("/hotspot/reject-request/{request_id}")
async def reject_upload_request(request_id: str, reason: str = "") -> Dict[str, Any]:
    """Reject an upload request (admin only)"""
    try:
        # Find the request
        request = None
        for req in hotspot_status["pending_requests"]:
            if req["id"] == request_id:
                request = req
                break
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )
        
        if request["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="Request is not pending"
            )
        
        # Update request status
        request["status"] = "rejected"
        request["rejected_at"] = datetime.now().isoformat()
        request["rejection_reason"] = reason
        
        return {
            "success": True,
            "message": "Upload request rejected",
            "data": request
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error rejecting request: {str(e)}"
        )

@router.get("/hotspot/requirements")
async def get_hotspot_requirements() -> Dict[str, Any]:
    """Get system requirements for hotspot functionality"""
    try:
        requirements = check_system_requirements()
        interface = detect_wifi_interface()
        
        # Get detailed system information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "wifi_interface": interface,
            "root_privileges": os.geteuid() == 0
        }
        
        # Installation instructions based on platform
        installation_instructions = {
            "Linux": {
                "hostapd": "sudo apt-get install hostapd",
                "dnsmasq": "sudo apt-get install dnsmasq",
                "raspberry_pi": "sudo apt-get install hostapd dnsmasq"
            },
            "Darwin": {  # macOS
                "hostapd": "brew install hostapd",
                "dnsmasq": "brew install dnsmasq"
            }
        }
        
        platform_instructions = installation_instructions.get(system_info["platform"], {})
        
        # Get personalized hotspot configuration
        personalized_config = HOTSPOT_CONFIG.copy()
        personalized_config["ssid"] = get_hotspot_ssid()
        
        return {
            "success": True,
            "data": {
                "requirements": requirements,
                "system_info": system_info,
                "installation_instructions": platform_instructions,
                "hotspot_config": personalized_config,
                "recommendations": {
                    "raspberry_pi": "Raspberry Pi is well-suited for hotspot functionality",
                    "linux": "Most Linux distributions support hotspot functionality",
                    "other": "Check system compatibility and install required packages"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting requirements: {str(e)}"
        )

@router.get("/user/config")
async def get_user_config() -> Dict[str, Any]:
    """Get current user configuration"""
    try:
        config = load_user_config()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting user config: {str(e)}"
        )

@router.post("/user/config")
async def update_user_config(request: dict = Body(...)) -> Dict[str, Any]:
    """Update user configuration"""
    try:
        # Extract user_name from request body
        user_name = request.get("user_name", "")
        
        # Validate user name
        if not user_name or len(user_name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="User name cannot be empty"
            )
        
        # Clean user name (remove special characters, limit length)
        clean_name = "".join(c for c in user_name.strip() if c.isalnum() or c.isspace())
        clean_name = clean_name.replace(" ", "")[:20]  # Remove spaces and limit length
        
        if not clean_name:
            raise HTTPException(
                status_code=400,
                detail="User name must contain alphanumeric characters"
            )
        
        # Update configuration
        config = load_user_config()
        config["user_name"] = clean_name
        config["hotspot_name"] = f"{clean_name}BabylonPiles"
        
        save_user_config(config)
        
        return {
            "success": True,
            "message": f"User name updated to: {clean_name}",
            "data": {
                "user_name": clean_name,
                "hotspot_name": config["hotspot_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating user config: {str(e)}"
        )

@router.get("/gitinfo")
def get_git_info():
    import os
    import datetime
    import logging
    version = "1.0.0"
    build = "2024.01.15"
    try:
        root = os.getcwd()
        git_dir = os.path.join(root, '.git')
        head_path = os.path.join(git_dir, 'HEAD')
        print(f"[GITINFO] head_path: {head_path}")
        if os.path.exists(head_path):
            with open(head_path, 'r') as f:
                ref = f.read().strip()
            print(f"[GITINFO] ref: {ref}")
            if ref.startswith('ref:'):
                ref_rel = ref.split(':', 1)[1].strip()
                ref_path = os.path.join(git_dir, *ref_rel.split('/'))
                print(f"[GITINFO] ref_path: {ref_path}")
                if os.path.exists(ref_path):
                    with open(ref_path, 'r') as rf:
                        version = rf.read().strip()[:7]
                    log_path = os.path.join(git_dir, 'logs', *ref_rel.split('/'))
                    print(f"[GITINFO] log_path: {log_path}")
                    if os.path.exists(log_path):
                        with open(log_path, 'r') as lf:
                            lines = lf.readlines()
                        print(f"[GITINFO] log lines: {lines[-2:]}")
                        if lines:
                            last = lines[-1]
                            parts = last.split()
                            print(f"[GITINFO] last log line: {last}")
                            print(f"[GITINFO] parts: {parts}")
                            if len(parts) > 4:
                                timestamp = int(parts[4])
                                build = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y.%m.%d')
    except Exception as e:
        print(f"[GITINFO] Exception: {e}")
    return JSONResponse({"version": version, "build": build})

def _calculate_directory_size(path: str) -> tuple[int, int]:
    """Calculate total size and file count of a directory"""
    total_size = 0
    file_count = 0

    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                file_count += 1
            except (OSError, PermissionError):
                continue

    return total_size, file_count


def _format_bytes(bytes_value: int) -> str:
    """Format bytes in human readable format"""
    if bytes_value == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_value >= 1024 and i < len(size_names) - 1:
        bytes_value /= 1024.0
        i += 1

    return f"{bytes_value:.1f} {size_names[i]}"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
