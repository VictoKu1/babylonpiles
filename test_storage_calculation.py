#!/usr/bin/env python3
"""
Test script to verify storage calculation shows 0 when no files are downloaded
"""

import asyncio
import aiohttp
import json

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_storage_calculation():
    """Test that storage calculation shows 0 when no files are downloaded"""
    print("🧪 Testing Storage Calculation")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        # 1. Get dashboard data
        print("1. Fetching dashboard data...")
        dashboard_response = await session.get(f"{BASE_URL}/api/v1/dashboard")
        
        if dashboard_response.status != 200:
            print(f"❌ Failed to get dashboard data: {dashboard_response.status}")
            return
        
        dashboard_data = await dashboard_response.json()
        print(f"✅ Dashboard data retrieved")
        
        # 2. Check storage calculations
        print("\n2. Checking storage calculations...")
        
        # Get piles data
        piles_response = await session.get(f"{BASE_URL}/api/v1/piles/")
        if piles_response.status == 200:
            piles_data = await piles_response.json()
            piles = piles_data.get("data", [])
            
            # Calculate downloaded piles
            downloaded_piles = [p for p in piles if p.get("file_path")]
            total_downloaded_size = sum(p.get("file_size", 0) for p in downloaded_piles)
            
            print(f"   - Total piles: {len(piles)}")
            print(f"   - Downloaded piles: {len(downloaded_piles)}")
            print(f"   - Total downloaded size: {total_downloaded_size} bytes")
            
            if len(downloaded_piles) == 0:
                print("✅ No downloaded piles found - storage should show 0")
            else:
                print(f"⚠️  Found {len(downloaded_piles)} downloaded piles")
                for pile in downloaded_piles:
                    print(f"     - {pile['name']}: {pile.get('file_size', 0)} bytes")
        
        # 3. Check system metrics
        print("\n3. Checking system metrics...")
        metrics_response = await session.get(f"{BASE_URL}/api/v1/system/metrics")
        if metrics_response.status == 200:
            metrics_data = await metrics_response.json()
            disk_info = metrics_data.get("data", {}).get("disk", {})
            
            print(f"   - Total disk: {disk_info.get('total_bytes', 0)} bytes")
            print(f"   - Used disk: {disk_info.get('used_bytes', 0)} bytes")
            print(f"   - Free disk: {disk_info.get('free_bytes', 0)} bytes")
        
        # 4. Verify dashboard storage display
        print("\n4. Verifying dashboard storage display...")
        if "storageUsed" in dashboard_data:
            storage_used = dashboard_data["storageUsed"]
            print(f"   - Dashboard shows storage used: {storage_used}")
            
            if storage_used == "0 B" or storage_used == "0.0 B":
                print("✅ Dashboard correctly shows 0 storage when no files downloaded")
            else:
                print(f"⚠️  Dashboard shows {storage_used} - check if this is correct")
        
        # 5. Check downloaded piles count
        if "downloadedPiles" in dashboard_data:
            downloaded_count = dashboard_data["downloadedPiles"]
            print(f"   - Dashboard shows {downloaded_count} downloaded piles")
            
            if downloaded_count == 0:
                print("✅ Dashboard correctly shows 0 downloaded piles")
            else:
                print(f"⚠️  Dashboard shows {downloaded_count} downloaded piles")
    
    print("\n" + "=" * 40)
    print("🎉 Storage calculation test completed!")

if __name__ == "__main__":
    asyncio.run(test_storage_calculation()) 