#!/usr/bin/env python3
"""
Test script to verify public/private permission functionality
"""

import asyncio
import aiohttp
import json

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_permissions():
    """Test the public/private permission functionality"""
    print("🧪 Testing Public/Private Permissions")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Create a test file
        print("1. Creating test file...")
        test_file_content = "This is a test file for permissions"
        test_file_path = "test_permissions.txt"
        
        # Upload test file
        form_data = aiohttp.FormData()
        form_data.add_field('file', test_file_content, filename=test_file_path)
        form_data.add_field('path', '')
        
        upload_response = await session.post(
            f"{BASE_URL}/api/v1/files/upload",
            data=form_data
        )
        
        if upload_response.status != 200:
            print(f"❌ Failed to create test file: {upload_response.status}")
            return
        
        print("✅ Test file created successfully")
        
        # 2. Check initial permission (should be private by default)
        print("\n2. Checking initial permission...")
        permission_response = await session.get(
            f"{BASE_URL}/api/v1/files/permission/{test_file_path}"
        )
        
        if permission_response.status == 200:
            permission_data = await permission_response.json()
            initial_permission = permission_data["data"]["is_public"]
            print(f"   - Initial permission: {'Public' if initial_permission else 'Private'}")
            
            if not initial_permission:
                print("✅ File correctly starts as private")
            else:
                print("⚠️  File started as public (unexpected)")
        else:
            print(f"❌ Failed to get permission: {permission_response.status}")
            return
        
        # 3. Toggle permission to public
        print("\n3. Toggling permission to public...")
        toggle_response = await session.post(
            f"{BASE_URL}/api/v1/files/permission/{test_file_path}/toggle"
        )
        
        if toggle_response.status == 200:
            toggle_data = await toggle_response.json()
            new_permission = toggle_data["data"]["is_public"]
            print(f"   - New permission: {'Public' if new_permission else 'Private'}")
            print(f"   - Message: {toggle_data['message']}")
            
            if new_permission:
                print("✅ Successfully made file public")
            else:
                print("❌ Failed to make file public")
        else:
            error_data = await toggle_response.json()
            print(f"❌ Failed to toggle permission: {error_data['detail']}")
            return
        
        # 4. Toggle permission back to private
        print("\n4. Toggling permission back to private...")
        toggle_response2 = await session.post(
            f"{BASE_URL}/api/v1/files/permission/{test_file_path}/toggle"
        )
        
        if toggle_response2.status == 200:
            toggle_data2 = await toggle_response2.json()
            final_permission = toggle_data2["data"]["is_public"]
            print(f"   - Final permission: {'Public' if final_permission else 'Private'}")
            print(f"   - Message: {toggle_data2['message']}")
            
            if not final_permission:
                print("✅ Successfully made file private")
            else:
                print("❌ Failed to make file private")
        else:
            error_data = await toggle_response2.json()
            print(f"❌ Failed to toggle permission: {error_data['detail']}")
            return
        
        # 5. Check file listing includes permissions
        print("\n5. Checking file listing includes permissions...")
        list_response = await session.get(f"{BASE_URL}/api/v1/files")
        
        if list_response.status == 200:
            list_data = await list_response.json()
            files = list_data["items"]
            
            test_file = None
            for file in files:
                if file["name"] == test_file_path:
                    test_file = file
                    break
            
            if test_file and "is_public" in test_file:
                print(f"   - File permission in listing: {'Public' if test_file['is_public'] else 'Private'}")
                print("✅ File listing correctly includes permission information")
            else:
                print("❌ File listing missing permission information")
        else:
            print(f"❌ Failed to get file listing: {list_response.status}")
        
        # 6. Cleanup test file
        print("\n6. Cleaning up test file...")
        delete_response = await session.delete(
            f"{BASE_URL}/api/v1/files/delete?path={test_file_path}"
        )
        
        if delete_response.status == 200:
            print("✅ Test file cleaned up successfully")
        else:
            print(f"❌ Failed to cleanup test file: {delete_response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 Permission functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_permissions()) 