#!/usr/bin/env python3
"""
Test script to verify download functionality improvements
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8080"
TEST_PILE_DATA = {
    "name": "test-download-pile",
    "display_name": "Test Download Pile",
    "description": "A test pile for download functionality",
    "category": "test",
    "source_type": "http",
    "source_url": "https://httpbin.org/bytes/1024",  # Small test file
    "tags": ["test", "download"]
}

async def test_download_functionality():
    """Test the improved download functionality"""
    print("🧪 Testing Download Functionality Improvements")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Create a test pile
        print("1. Creating test pile...")
        create_response = await session.post(
            f"{BASE_URL}/api/v1/piles/",
            json=TEST_PILE_DATA
        )
        
        if create_response.status != 200:
            print(f"❌ Failed to create test pile: {create_response.status}")
            return
        
        pile_data = await create_response.json()
        pile_id = pile_data["data"]["id"]
        print(f"✅ Created test pile with ID: {pile_id}")
        
        # 2. Check initial status
        print("\n2. Checking initial pile status...")
        status_response = await session.get(f"{BASE_URL}/api/v1/piles/{pile_id}")
        if status_response.status == 200:
            status_data = await status_response.json()
            pile = status_data["data"]
            print(f"   - is_downloading: {pile['is_downloading']}")
            print(f"   - download_progress: {pile['download_progress']}")
            print(f"   - file_path: {pile['file_path']}")
        
        # 3. Start download
        print("\n3. Starting download...")
        download_response = await session.post(
            f"{BASE_URL}/api/v1/piles/{pile_id}/download-source"
        )
        
        if download_response.status == 200:
            download_data = await download_response.json()
            print(f"✅ Download started: {download_data['message']}")
        else:
            error_data = await download_response.json()
            print(f"❌ Download failed: {error_data['detail']}")
            return
        
        # 4. Monitor download progress
        print("\n4. Monitoring download progress...")
        for i in range(10):  # Monitor for up to 10 seconds
            await asyncio.sleep(1)
            
            progress_response = await session.get(f"{BASE_URL}/api/v1/piles/{pile_id}")
            if progress_response.status == 200:
                progress_data = await progress_response.json()
                pile = progress_data["data"]
                
                print(f"   Progress: {pile['download_progress']:.1%} - is_downloading: {pile['is_downloading']}")
                
                if not pile['is_downloading'] and pile['file_path']:
                    print("✅ Download completed successfully!")
                    break
            else:
                print(f"❌ Failed to get progress: {progress_response.status}")
                break
        
        # 5. Check final status
        print("\n5. Checking final status...")
        final_response = await session.get(f"{BASE_URL}/api/v1/piles/{pile_id}")
        if final_response.status == 200:
            final_data = await final_response.json()
            pile = final_data["data"]
            
            print(f"   - is_downloading: {pile['is_downloading']}")
            print(f"   - download_progress: {pile['download_progress']}")
            print(f"   - file_path: {pile['file_path']}")
            print(f"   - file_size: {pile['file_size']}")
            
            if pile['file_path'] and pile['file_size']:
                print("✅ File downloaded successfully!")
            else:
                print("❌ File download failed or incomplete")
        
        # 6. Test duplicate download prevention
        print("\n6. Testing duplicate download prevention...")
        duplicate_response = await session.post(
            f"{BASE_URL}/api/v1/piles/{pile_id}/download-source"
        )
        
        if duplicate_response.status == 400:
            error_data = await duplicate_response.json()
            print(f"✅ Duplicate download correctly prevented: {error_data['detail']}")
        else:
            print(f"❌ Duplicate download prevention failed: {duplicate_response.status}")
        
        # 7. Test download status endpoint
        print("\n7. Testing download status endpoint...")
        status_response = await session.get(f"{BASE_URL}/api/v1/files/download-status")
        if status_response.status == 200:
            status_data = await status_response.json()
            print(f"✅ Download status endpoint working: {len(status_data['data'])} active downloads")
        else:
            print(f"❌ Download status endpoint failed: {status_response.status}")
        
        # 8. Cleanup
        print("\n8. Cleaning up test pile...")
        cleanup_response = await session.delete(f"{BASE_URL}/api/v1/piles/{pile_id}")
        if cleanup_response.status == 200:
            print("✅ Test pile cleaned up successfully")
        else:
            print(f"❌ Failed to cleanup test pile: {cleanup_response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 Download functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_download_functionality()) 