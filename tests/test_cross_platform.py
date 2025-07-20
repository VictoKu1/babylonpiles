#!/usr/bin/env python3
"""
Test script to verify cross-platform WiFi hotspot compatibility
"""

import asyncio
import aiohttp
import json
import platform
import subprocess
import os
import sys

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_cross_platform_compatibility():
    """Test cross-platform compatibility of WiFi hotspot functionality"""
    print("🧪 Testing Cross-Platform WiFi Hotspot Compatibility")
    print("=" * 60)
    
    # System information
    print("System Information:")
    print(f"  Platform: {platform.system()}")
    print(f"  Platform Version: {platform.version()}")
    print(f"  Machine: {platform.machine()}")
    print(f"  Processor: {platform.processor()}")
    print(f"  Python Version: {platform.python_version()}")
    print()
    
    async with aiohttp.ClientSession() as session:
        # 1. Test system requirements endpoint
        print("1. Testing System Requirements Detection...")
        requirements_response = await session.get(f"{BASE_URL}/api/v1/hotspot/requirements")
        
        if requirements_response.status == 200:
            requirements_data = await requirements_response.json()
            data = requirements_data["data"]
            
            print(f"   - Platform: {data['system_info']['platform']}")
            print(f"   - WiFi Interface: {data['system_info']['wifi_interface']}")
            print(f"   - Root Privileges: {data['system_info']['root_privileges']}")
            
            requirements = data['requirements']
            print("   - Requirements Status:")
            print(f"     * hostapd: {'✅' if requirements['hostapd'] else '❌'}")
            print(f"     * dnsmasq: {'✅' if requirements['dnsmasq'] else '❌'}")
            print(f"     * WiFi Interface: {'✅' if requirements['wifi_interface'] else '❌'}")
            print(f"     * Root Privileges: {'✅' if requirements['root_privileges'] else '❌'}")
            
            # Check if all requirements are met
            all_met = all(requirements.values())
            if all_met:
                print("   ✅ All system requirements are met")
            else:
                print("   ⚠️  Some system requirements are missing")
                missing = [k for k, v in requirements.items() if not v]
                print(f"      Missing: {', '.join(missing)}")
                
                # Show installation instructions
                if 'installation_instructions' in data:
                    print("   - Installation Instructions:")
                    for package, command in data['installation_instructions'].items():
                        print(f"     * {package}: {command}")
            
            print("✅ System requirements test completed")
        else:
            print(f"❌ Failed to get system requirements: {requirements_response.status}")
            return
        
        # 2. Test hotspot status endpoint
        print("\n2. Testing Hotspot Status Endpoint...")
        status_response = await session.get(f"{BASE_URL}/api/v1/hotspot/status")
        
        if status_response.status == 200:
            status_data = await status_response.json()
            data = status_data["data"]
            
            print(f"   - Is Running: {data['is_running']}")
            print(f"   - SSID: {data['ssid']}")
            print(f"   - Interface: {data['interface']}")
            print(f"   - Gateway IP: {data['gateway_ip']}")
            print(f"   - Connected Devices: {len(data['connected_devices'])}")
            print(f"   - Pending Requests: {len(data['pending_requests'])}")
            
            # Show system info if available
            if 'system_info' in data:
                sys_info = data['system_info']
                print("   - System Information:")
                print(f"     * Platform: {sys_info['platform']}")
                print(f"     * Machine: {sys_info['machine']}")
                print(f"     * WiFi Interface: {sys_info['wifi_interface']}")
            
            print("✅ Hotspot status test completed")
        else:
            print(f"❌ Failed to get hotspot status: {status_response.status}")
        
        # 3. Test platform-specific functionality
        print("\n3. Testing Platform-Specific Features...")
        
        # Check if we can detect WiFi interfaces
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            if result.returncode == 0:
                wifi_interfaces = []
                for line in result.stdout.split('\n'):
                    if any(iface in line for iface in ['wlan', 'wifi', 'wlp']):
                        wifi_interfaces.append(line.strip())
                
                if wifi_interfaces:
                    print(f"   - Detected WiFi interfaces: {len(wifi_interfaces)}")
                    for iface in wifi_interfaces[:3]:  # Show first 3
                        print(f"     * {iface}")
                else:
                    print("   - No WiFi interfaces detected")
            else:
                print("   - Could not check WiFi interfaces")
        except Exception as e:
            print(f"   - Error checking WiFi interfaces: {e}")
        
        # Check for required packages
        packages = ['hostapd', 'dnsmasq']
        for package in packages:
            try:
                result = subprocess.run(["which", package], capture_output=True)
                if result.returncode == 0:
                    print(f"   - {package}: ✅ Available")
                else:
                    print(f"   - {package}: ❌ Not found")
            except Exception as e:
                print(f"   - {package}: ⚠️  Error checking ({e})")
        
        # 4. Test hotspot start (if requirements are met)
        print("\n4. Testing Hotspot Start...")
        if all_met:
            start_response = await session.post(f"{BASE_URL}/api/v1/hotspot/start")
            
            if start_response.status == 200:
                start_data = await start_response.json()
                if start_data['success']:
                    print(f"   - Message: {start_data['message']}")
                    if 'data' in start_data:
                        data = start_data['data']
                        print(f"   - SSID: {data['ssid']}")
                        print(f"   - Interface: {data['interface']}")
                        print(f"   - Gateway IP: {data['gateway_ip']}")
                    print("✅ Hotspot start test completed")
                    
                    # Stop the hotspot
                    print("\n5. Testing Hotspot Stop...")
                    stop_response = await session.post(f"{BASE_URL}/api/v1/hotspot/stop")
                    
                    if stop_response.status == 200:
                        stop_data = await stop_response.json()
                        print(f"   - Message: {stop_data['message']}")
                        print("✅ Hotspot stop test completed")
                    else:
                        print(f"❌ Failed to stop hotspot: {stop_response.status}")
                else:
                    print(f"   - Error: {start_data['message']}")
                    if 'data' in start_data and 'missing' in start_data['data']:
                        print(f"   - Missing requirements: {', '.join(start_data['data']['missing'])}")
            else:
                error_data = await start_response.json()
                print(f"❌ Failed to start hotspot: {error_data['detail']}")
        else:
            print("   ⚠️  Skipping hotspot start test (requirements not met)")
        
        # 6. Test content endpoints
        print("\n6. Testing Content Endpoints...")
        
        # Test public content endpoint
        content_response = await session.get(f"{BASE_URL}/api/v1/hotspot/public-content")
        
        if content_response.status == 200:
            content_data = await content_response.json()
            files = content_data["data"]["files"]
            print(f"   - Public files available: {len(files)}")
            print(f"   - Total files: {content_data['data']['total_files']}")
            print(f"   - Total folders: {content_data['data']['total_folders']}")
            print("✅ Content endpoints test completed")
        else:
            print(f"❌ Failed to get public content: {content_response.status}")
        
        # 7. Platform-specific recommendations
        print("\n7. Platform-Specific Analysis...")
        
        platform_name = platform.system()
        if platform_name == "Linux":
            print("   - Linux system detected")
            print("   - Full hotspot support available")
            print("   - Recommended for production use")
        elif platform_name == "Darwin":  # macOS
            print("   - macOS system detected")
            print("   - Limited hotspot support")
            print("   - Requires additional configuration")
        elif platform_name == "Windows":
            print("   - Windows system detected")
            print("   - Limited hotspot support")
            print("   - Requires WSL or virtualization")
        else:
            print(f"   - Unknown platform: {platform_name}")
            print("   - Compatibility unknown")
        
        # Check if it's a Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'Raspberry Pi' in cpuinfo or 'BCM2708' in cpuinfo or 'BCM2835' in cpuinfo:
                    print("   - Raspberry Pi detected")
                    print("   - Excellent platform for hotspot functionality")
                    print("   - Low power consumption, good performance")
        except FileNotFoundError:
            pass  # Not a Linux system
    
    print("\n" + "=" * 60)
    print("🎉 Cross-platform compatibility test completed!")
    print("\nSummary:")
    print("- The WiFi hotspot functionality is designed to work on any system")
    print("- Raspberry Pi is the primary target platform")
    print("- Linux systems provide full support")
    print("- Other platforms may require additional setup")
    print("- System requirements are automatically detected and validated")

if __name__ == "__main__":
    asyncio.run(test_cross_platform_compatibility()) 