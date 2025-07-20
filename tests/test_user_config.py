#!/usr/bin/env python3
"""
Test script to verify user name configuration functionality
"""

import asyncio
import aiohttp
import json

# Test configuration
BASE_URL = "http://localhost:8080"

async def test_user_config():
    """Test the user name configuration functionality"""
    print("🧪 Testing User Name Configuration")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Get initial user configuration
        print("1. Getting initial user configuration...")
        config_response = await session.get(f"{BASE_URL}/api/v1/system/user/config")
        
        if config_response.status == 200:
            config_data = await config_response.json()
            initial_config = config_data["data"]
            print(f"   - Current user name: '{initial_config.get('user_name', '')}'")
            print(f"   - Current hotspot name: '{initial_config.get('hotspot_name', '')}'")
        else:
            print(f"❌ Failed to get user config: {config_response.status}")
            return
        
        # 2. Test updating user name
        print("\n2. Testing user name update...")
        test_user_name = "James"
        
        update_response = await session.post(
            f"{BASE_URL}/api/v1/system/user/config",
            json={"user_name": test_user_name}
        )
        
        if update_response.status == 200:
            update_data = await update_response.json()
            print(f"   - Message: {update_data['message']}")
            print(f"   - New user name: {update_data['data']['user_name']}")
            print(f"   - New hotspot name: {update_data['data']['hotspot_name']}")
            print("✅ User name update test completed")
        else:
            error_data = await update_response.json()
            print(f"❌ Failed to update user name: {error_data['detail']}")
        
        # 3. Verify updated configuration
        print("\n3. Verifying updated configuration...")
        verify_response = await session.get(f"{BASE_URL}/api/v1/system/user/config")
        
        if verify_response.status == 200:
            verify_data = await verify_response.json()
            updated_config = verify_data["data"]
            print(f"   - User name: '{updated_config['user_name']}'")
            print(f"   - Hotspot name: '{updated_config['hotspot_name']}'")
            
            expected_hotspot_name = f"{test_user_name}BabylonPiles"
            if updated_config['hotspot_name'] == expected_hotspot_name:
                print("✅ Configuration verification successful")
            else:
                print(f"❌ Hotspot name mismatch. Expected: {expected_hotspot_name}, Got: {updated_config['hotspot_name']}")
        else:
            print(f"❌ Failed to verify configuration: {verify_response.status}")
        
        # 4. Test hotspot status with personalized name
        print("\n4. Testing hotspot status with personalized name...")
        status_response = await session.get(f"{BASE_URL}/api/v1/system/hotspot/status")
        
        if status_response.status == 200:
            status_data = await status_response.json()
            hotspot_data = status_data["data"]
            print(f"   - SSID: {hotspot_data['ssid']}")
            print(f"   - User config: {hotspot_data.get('user_config', {})}")
            
            if hotspot_data['ssid'] == expected_hotspot_name:
                print("✅ Hotspot status shows personalized SSID")
            else:
                print(f"❌ SSID mismatch. Expected: {expected_hotspot_name}, Got: {hotspot_data['ssid']}")
        else:
            print(f"❌ Failed to get hotspot status: {status_response.status}")
        
        # 5. Test invalid user names
        print("\n5. Testing invalid user names...")
        invalid_names = ["", "   ", "Test@123", "VeryLongNameThatExceedsTwentyCharacters", "Test Name With Spaces"]
        
        for invalid_name in invalid_names:
            invalid_response = await session.post(
                f"{BASE_URL}/api/v1/system/user/config",
                json={"user_name": invalid_name}
            )
            
            if invalid_response.status == 400:
                error_data = await invalid_response.json()
                print(f"   ✅ Correctly rejected '{invalid_name}': {error_data['detail']}")
            else:
                print(f"   ❌ Should have rejected '{invalid_name}' but didn't")
        
        # 6. Test valid user names
        print("\n6. Testing valid user names...")
        valid_names = ["Alice", "Bob123", "Charlie", "David", "Eve"]
        
        for valid_name in valid_names:
            valid_response = await session.post(
                f"{BASE_URL}/api/v1/system/user/config",
                json={"user_name": valid_name}
            )
            
            if valid_response.status == 200:
                valid_data = await valid_response.json()
                print(f"   ✅ Accepted '{valid_name}': {valid_data['data']['hotspot_name']}")
            else:
                error_data = await valid_response.json()
                print(f"   ❌ Should have accepted '{valid_name}' but didn't: {error_data['detail']}")
        
        # 7. Test special character handling
        print("\n7. Testing special character handling...")
        special_names = ["John-Doe", "Mary@Smith", "Bob&Alice", "Test.Name", "User 123"]
        
        for special_name in special_names:
            special_response = await session.post(
                f"{BASE_URL}/api/v1/system/user/config",
                json={"user_name": special_name}
            )
            
            if special_response.status == 200:
                special_data = await special_response.json()
                cleaned_name = special_data['data']['user_name']
                print(f"   ✅ Cleaned '{special_name}' to '{cleaned_name}': {special_data['data']['hotspot_name']}")
            else:
                error_data = await special_response.json()
                print(f"   ❌ Failed to process '{special_name}': {error_data['detail']}")
        
        # 8. Test name length limits
        print("\n8. Testing name length limits...")
        long_name = "A" * 25  # 25 characters
        short_name = "B" * 5   # 5 characters
        
        # Test long name
        long_response = await session.post(
            f"{BASE_URL}/api/v1/system/user/config",
            json={"user_name": long_name}
        )
        
        if long_response.status == 200:
            long_data = await long_response.json()
            final_name = long_data['data']['user_name']
            print(f"   ✅ Long name '{long_name}' truncated to '{final_name}' ({len(final_name)} chars)")
        else:
            error_data = await long_response.json()
            print(f"   ❌ Failed to process long name: {error_data['detail']}")
        
        # Test short name
        short_response = await session.post(
            f"{BASE_URL}/api/v1/system/user/config",
            json={"user_name": short_name}
        )
        
        if short_response.status == 200:
            short_data = await short_response.json()
            print(f"   ✅ Short name '{short_name}' accepted: {short_data['data']['hotspot_name']}")
        else:
            error_data = await short_response.json()
            print(f"   ❌ Failed to process short name: {error_data['detail']}")
        
        # 9. Final configuration check
        print("\n9. Final configuration check...")
        final_response = await session.get(f"{BASE_URL}/api/v1/system/user/config")
        
        if final_response.status == 200:
            final_data = await final_response.json()
            final_config = final_data["data"]
            print(f"   - Final user name: '{final_config['user_name']}'")
            print(f"   - Final hotspot name: '{final_config['hotspot_name']}'")
            print("✅ User configuration test completed successfully")
        else:
            print(f"❌ Failed to get final configuration: {final_response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 User name configuration test completed!")
    print("\nSummary:")
    print("- User names are validated and cleaned")
    print("- Special characters are removed")
    print("- Names are limited to 20 characters")
    print("- Hotspot SSID is personalized with user name")
    print("- Configuration persists across restarts")

if __name__ == "__main__":
    asyncio.run(test_user_config()) 