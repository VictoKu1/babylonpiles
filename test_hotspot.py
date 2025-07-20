#!/usr/bin/env python3
"""
Test script to verify WiFi hotspot functionality
"""

import asyncio
import aiohttp
import json
import time

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_hotspot():
    """Test the WiFi hotspot functionality"""
    print("🧪 Testing WiFi Hotspot Functionality")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Check initial hotspot status
        print("1. Checking initial hotspot status...")
        status_response = await session.get(f"{BASE_URL}/api/v1/hotspot/status")
        
        if status_response.status == 200:
            status_data = await status_response.json()
            initial_status = status_data["data"]
            print(f"   - Is running: {initial_status['is_running']}")
            print(f"   - SSID: {initial_status['ssid']}")
            print(f"   - Connected devices: {len(initial_status['connected_devices'])}")
            print(f"   - Pending requests: {len(initial_status['pending_requests'])}")
        else:
            print(f"❌ Failed to get hotspot status: {status_response.status}")
            return
        
        # 2. Test starting hotspot
        print("\n2. Testing hotspot start...")
        start_response = await session.post(f"{BASE_URL}/api/v1/hotspot/start")
        
        if start_response.status == 200:
            start_data = await start_response.json()
            print(f"   - Message: {start_data['message']}")
            if 'data' in start_data:
                print(f"   - SSID: {start_data['data']['ssid']}")
                print(f"   - Password: {start_data['data']['password']}")
                print(f"   - IP Range: {start_data['data']['ip_range']}")
            print("✅ Hotspot start test completed")
        else:
            error_data = await start_response.json()
            print(f"❌ Failed to start hotspot: {error_data['detail']}")
        
        # 3. Check hotspot status after start
        print("\n3. Checking hotspot status after start...")
        status_response = await session.get(f"{BASE_URL}/api/v1/hotspot/status")
        
        if status_response.status == 200:
            status_data = await status_response.json()
            status = status_data["data"]
            print(f"   - Is running: {status['is_running']}")
            print(f"   - Started at: {status['started_at']}")
            print(f"   - Connected devices: {len(status['connected_devices'])}")
        else:
            print(f"❌ Failed to get updated status: {status_response.status}")
        
        # 4. Test public content endpoint
        print("\n4. Testing public content endpoint...")
        content_response = await session.get(f"{BASE_URL}/api/v1/hotspot/public-content")
        
        if content_response.status == 200:
            content_data = await content_response.json()
            files = content_data["data"]["files"]
            print(f"   - Total public files: {len(files)}")
            print(f"   - Total files: {content_data['data']['total_files']}")
            print(f"   - Total folders: {content_data['data']['total_folders']}")
            
            if files:
                print("   - Sample files:")
                for file in files[:3]:  # Show first 3 files
                    print(f"     * {file['name']} ({file['size_formatted']})")
            else:
                print("   - No public files found")
            print("✅ Public content endpoint test completed")
        else:
            error_data = await content_response.json()
            print(f"❌ Failed to get public content: {error_data['detail']}")
        
        # 5. Test upload request
        print("\n5. Testing upload request...")
        request_data = {
            "filename": "test_upload.txt",
            "editor_name": "Test User",
            "client_ip": "192.168.4.100",
            "client_mac": "00:11:22:33:44:55"
        }
        
        request_response = await session.post(
            f"{BASE_URL}/api/v1/hotspot/request-upload",
            json=request_data
        )
        
        if request_response.status == 200:
            request_result = await request_response.json()
            print(f"   - Message: {request_result['message']}")
            print(f"   - Request ID: {request_result['data']['request_id']}")
            print(f"   - Status: {request_result['data']['status']}")
            print("✅ Upload request test completed")
        else:
            error_data = await request_response.json()
            print(f"❌ Failed to submit upload request: {error_data['detail']}")
        
        # 6. Check pending requests
        print("\n6. Checking pending requests...")
        status_response = await session.get(f"{BASE_URL}/api/v1/hotspot/status")
        
        if status_response.status == 200:
            status_data = await status_response.json()
            pending_requests = status_data["data"]["pending_requests"]
            print(f"   - Pending requests: {len(pending_requests)}")
            
            for req in pending_requests:
                if req["status"] == "pending":
                    print(f"     * {req['filename']} by {req['editor_name']}")
                    print(f"       Request ID: {req['id']}")
                    print(f"       IP: {req['client_ip']}")
                    print(f"       MAC: {req['client_mac']}")
        else:
            print(f"❌ Failed to get updated status: {status_response.status}")
        
        # 7. Test approving request
        print("\n7. Testing request approval...")
        if pending_requests:
            first_request = pending_requests[0]
            approve_response = await session.post(
                f"{BASE_URL}/api/v1/hotspot/approve-request/{first_request['id']}"
            )
            
            if approve_response.status == 200:
                approve_result = await approve_response.json()
                print(f"   - Message: {approve_result['message']}")
                print(f"   - Status: {approve_result['data']['status']}")
                print("✅ Request approval test completed")
            else:
                error_data = await approve_response.json()
                print(f"❌ Failed to approve request: {error_data['detail']}")
        else:
            print("   - No pending requests to approve")
        
        # 8. Test rejecting request
        print("\n8. Testing request rejection...")
        # Create another test request
        request_data2 = {
            "filename": "test_reject.txt",
            "editor_name": "Reject User",
            "client_ip": "192.168.4.101",
            "client_mac": "00:11:22:33:44:66"
        }
        
        request_response2 = await session.post(
            f"{BASE_URL}/api/v1/hotspot/request-upload",
            json=request_data2
        )
        
        if request_response2.status == 200:
            request_result2 = await request_response2.json()
            request_id = request_result2['data']['request_id']
            
            # Reject the request
            reject_response = await session.post(
                f"{BASE_URL}/api/v1/hotspot/reject-request/{request_id}",
                json={"reason": "Test rejection"}
            )
            
            if reject_response.status == 200:
                reject_result = await reject_response.json()
                print(f"   - Message: {reject_result['message']}")
                print(f"   - Status: {reject_result['data']['status']}")
                print(f"   - Reason: {reject_result['data']['rejection_reason']}")
                print("✅ Request rejection test completed")
            else:
                error_data = await reject_response.json()
                print(f"❌ Failed to reject request: {error_data['detail']}")
        else:
            print("❌ Failed to create test request for rejection")
        
        # 9. Test stopping hotspot
        print("\n9. Testing hotspot stop...")
        stop_response = await session.post(f"{BASE_URL}/api/v1/hotspot/stop")
        
        if stop_response.status == 200:
            stop_data = await stop_response.json()
            print(f"   - Message: {stop_data['message']}")
            print("✅ Hotspot stop test completed")
        else:
            error_data = await stop_response.json()
            print(f"❌ Failed to stop hotspot: {error_data['detail']}")
        
        # 10. Final status check
        print("\n10. Final status check...")
        final_status_response = await session.get(f"{BASE_URL}/api/v1/hotspot/status")
        
        if final_status_response.status == 200:
            final_status_data = await final_status_response.json()
            final_status = final_status_data["data"]
            print(f"   - Is running: {final_status['is_running']}")
            print(f"   - Connected devices: {len(final_status['connected_devices'])}")
            print(f"   - Total requests: {len(final_status['pending_requests'])}")
        else:
            print(f"❌ Failed to get final status: {final_status_response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 WiFi hotspot functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_hotspot()) 