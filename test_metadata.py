#!/usr/bin/env python3
"""
Test script to verify metadata functionality
"""

import asyncio
import aiohttp
import json
import time

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_metadata():
    """Test the metadata functionality"""
    print("🧪 Testing File Metadata Functionality")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Create a test file
        print("1. Creating test file...")
        test_file_content = "This is a test file for metadata"
        test_file_path = "test_metadata.txt"
        
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
        
        # 2. Create a test folder
        print("\n2. Creating test folder...")
        folder_form_data = aiohttp.FormData()
        folder_form_data.add_field('folder_name', 'test_metadata_folder')
        folder_form_data.add_field('path', '')
        
        folder_response = await session.post(
            f"{BASE_URL}/api/v1/files/mkdir",
            data=folder_form_data
        )
        
        if folder_response.status != 200:
            print(f"❌ Failed to create test folder: {folder_response.status}")
            return
        
        print("✅ Test folder created successfully")
        
        # 3. Check file listing includes metadata
        print("\n3. Checking file listing includes metadata...")
        list_response = await session.get(f"{BASE_URL}/api/v1/files")
        
        if list_response.status == 200:
            list_data = await list_response.json()
            files = list_data["items"]
            
            test_file = None
            test_folder = None
            for file in files:
                if file["name"] == test_file_path:
                    test_file = file
                elif file["name"] == "test_metadata_folder":
                    test_folder = file
            
            if test_file and "metadata" in test_file:
                print(f"   - File metadata found: {test_file['metadata']}")
                print("✅ File listing correctly includes metadata")
            else:
                print("❌ File listing missing metadata information")
                
            if test_folder and "metadata" in test_folder:
                print(f"   - Folder metadata found: {test_folder['metadata']}")
                print("✅ Folder listing correctly includes metadata")
            else:
                print("❌ Folder listing missing metadata information")
        else:
            print(f"❌ Failed to get file listing: {list_response.status}")
        
        # 4. Get detailed metadata for file
        print("\n4. Getting detailed metadata for file...")
        metadata_response = await session.get(
            f"{BASE_URL}/api/v1/files/metadata/{test_file_path}"
        )
        
        if metadata_response.status == 200:
            metadata_data = await metadata_response.json()
            file_metadata = metadata_data["data"]
            
            print(f"   - File name: {file_metadata['name']}")
            print(f"   - Creator: {file_metadata['creator']}")
            print(f"   - Created: {file_metadata['created_at']}")
            print(f"   - Created ago: {file_metadata['created_ago']}")
            print(f"   - Modified: {file_metadata['modified_at']}")
            print(f"   - Modified ago: {file_metadata['modified_ago']}")
            print(f"   - Size: {file_metadata['size_formatted']}")
            print(f"   - Is public: {file_metadata['is_public']}")
            
            if file_metadata['creator'] == 'admin':
                print("✅ File metadata correctly shows admin as creator")
            else:
                print("⚠️  File metadata shows unexpected creator")
        else:
            error_data = await metadata_response.json()
            print(f"❌ Failed to get file metadata: {error_data['detail']}")
        
        # 5. Get detailed metadata for folder
        print("\n5. Getting detailed metadata for folder...")
        folder_metadata_response = await session.get(
            f"{BASE_URL}/api/v1/files/metadata/test_metadata_folder"
        )
        
        if folder_metadata_response.status == 200:
            folder_metadata_data = await folder_metadata_response.json()
            folder_metadata = folder_metadata_data["data"]
            
            print(f"   - Folder name: {folder_metadata['name']}")
            print(f"   - Creator: {folder_metadata['creator']}")
            print(f"   - Created: {folder_metadata['created_at']}")
            print(f"   - Created ago: {folder_metadata['created_ago']}")
            print(f"   - Is directory: {folder_metadata['is_dir']}")
            
            if folder_metadata['is_dir']:
                print("✅ Folder metadata correctly shows as directory")
            else:
                print("❌ Folder metadata incorrectly shows as file")
        else:
            error_data = await folder_metadata_response.json()
            print(f"❌ Failed to get folder metadata: {error_data['detail']}")
        
        # 6. Test metadata with permissions
        print("\n6. Testing metadata with permissions...")
        
        # Make file public
        permission_response = await session.post(
            f"{BASE_URL}/api/v1/files/permission/{test_file_path}/toggle"
        )
        
        if permission_response.status == 200:
            print("✅ Made file public")
            
            # Check metadata again
            updated_metadata_response = await session.get(
                f"{BASE_URL}/api/v1/files/metadata/{test_file_path}"
            )
            
            if updated_metadata_response.status == 200:
                updated_metadata_data = await updated_metadata_response.json()
                updated_metadata = updated_metadata_data["data"]
                
                print(f"   - Updated is_public: {updated_metadata['is_public']}")
                print(f"   - Public read permission: {updated_metadata['permissions']['public_read']}")
                
                if updated_metadata['is_public'] and updated_metadata['permissions']['public_read']:
                    print("✅ Metadata correctly reflects public permission")
                else:
                    print("❌ Metadata incorrectly reflects permission")
            else:
                print("❌ Failed to get updated metadata")
        else:
            print("❌ Failed to toggle file permission")
        
        # 7. Cleanup test files
        print("\n7. Cleaning up test files...")
        
        # Delete test file
        delete_file_response = await session.delete(
            f"{BASE_URL}/api/v1/files/delete?path={test_file_path}"
        )
        
        if delete_file_response.status == 200:
            print("✅ Test file cleaned up successfully")
        else:
            print(f"❌ Failed to cleanup test file: {delete_file_response.status}")
        
        # Delete test folder
        delete_folder_response = await session.delete(
            f"{BASE_URL}/api/v1/files/delete?path=test_metadata_folder"
        )
        
        if delete_folder_response.status == 200:
            print("✅ Test folder cleaned up successfully")
        else:
            print(f"❌ Failed to cleanup test folder: {delete_folder_response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 Metadata functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_metadata()) 