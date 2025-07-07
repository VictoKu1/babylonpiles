#!/usr/bin/env python3
"""
Test script for BabylonPiles Storage API
Verifies that the storage service endpoints are working correctly
"""

import requests
import json
import time
import sys
from typing import Dict, List, Optional

# Configuration
API_BASE_URL = "http://localhost:8080/api/v1"
STORAGE_BASE_URL = "http://localhost:8001"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_success(message: str):
    """Print a success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"✗ {message}")


def print_info(message: str):
    """Print an info message"""
    print(f"ℹ {message}")


def test_api_health() -> bool:
    """Test if the API is accessible"""
    print_section("Testing API Health")

    try:
        # Test backend API
        response = requests.get(f"{API_BASE_URL}/storage/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend API is healthy")
            backend_healthy = True
        else:
            print_error(f"Backend API returned status {response.status_code}")
            backend_healthy = False
    except Exception as e:
        print_error(f"Backend API not accessible: {e}")
        backend_healthy = False

    try:
        # Test storage service directly
        response = requests.get(f"{STORAGE_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Storage service is healthy")
            storage_healthy = True
        else:
            print_error(f"Storage service returned status {response.status_code}")
            storage_healthy = False
    except Exception as e:
        print_error(f"Storage service not accessible: {e}")
        storage_healthy = False

    return backend_healthy and storage_healthy


def test_get_drives() -> List[Dict]:
    """Test getting current drives"""
    print_section("Testing Get Drives")

    try:
        response = requests.get(f"{API_BASE_URL}/storage/drives", timeout=10)
        if response.status_code == 200:
            data = response.json()
            drives = data.get("drives", [])
            print_success(f"Successfully retrieved {len(drives)} drives")

            if drives:
                print_info("Current drives:")
                for drive in drives:
                    total_gb = drive.get("total_space", 0) / (1024**3)
                    free_gb = drive.get("free_space", 0) / (1024**3)
                    print(
                        f"  - {drive['id']}: {drive['path']} ({total_gb:.1f}GB total, {free_gb:.1f}GB free)"
                    )
            else:
                print_info("No drives currently configured")

            return drives
        else:
            print_error(f"Failed to get drives: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error getting drives: {e}")
        return []


def test_scan_drives() -> bool:
    """Test scanning for new drives"""
    print_section("Testing Drive Scan")

    try:
        response = requests.post(f"{API_BASE_URL}/storage/drives/scan", timeout=15)
        if response.status_code == 200:
            data = response.json()
            print_success("Drive scan completed successfully")
            print_info(f"Scan result: {json.dumps(data, indent=2)}")
            return True
        else:
            print_error(f"Drive scan failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error scanning drives: {e}")
        return False


def test_storage_status() -> Optional[Dict]:
    """Test getting storage status"""
    print_section("Testing Storage Status")

    try:
        response = requests.get(f"{API_BASE_URL}/storage/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully retrieved storage status")
            print_info(f"Status: {json.dumps(data, indent=2)}")
            return data
        else:
            print_error(f"Failed to get storage status: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Error getting storage status: {e}")
        return None


def test_allocate_storage() -> bool:
    """Test allocating storage for a file"""
    print_section("Testing Storage Allocation")

    try:
        # Test with a 1GB file
        file_size = 1024 * 1024 * 1024  # 1GB
        file_id = f"test_file_{int(time.time())}"

        response = requests.post(
            f"{API_BASE_URL}/storage/allocate",
            params={"file_size": file_size, "file_id": file_id},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Successfully allocated storage")
            print_info(f"Allocation: {json.dumps(data, indent=2)}")
            return True
        else:
            print_error(f"Failed to allocate storage: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error allocating storage: {e}")
        return False


def test_get_chunks() -> List[Dict]:
    """Test getting chunks"""
    print_section("Testing Get Chunks")

    try:
        response = requests.get(f"{API_BASE_URL}/storage/chunks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            chunks = data.get("chunks", [])
            print_success(f"Successfully retrieved {len(chunks)} chunks")

            if chunks:
                print_info("Sample chunks:")
                for chunk in chunks[:3]:  # Show first 3 chunks
                    size_mb = chunk.get("size", 0) / (1024**2)
                    print(f"  - {chunk['id']}: {size_mb:.1f}MB on {chunk['drive_id']}")

            return chunks
        else:
            print_error(f"Failed to get chunks: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error getting chunks: {e}")
        return []


def test_get_migrations() -> List[Dict]:
    """Test getting migrations"""
    print_section("Testing Get Migrations")

    try:
        response = requests.get(f"{API_BASE_URL}/storage/migrations", timeout=10)
        if response.status_code == 200:
            data = response.json()
            migrations = data.get("migrations", [])
            print_success(f"Successfully retrieved {len(migrations)} migrations")

            if migrations:
                print_info("Sample migrations:")
                for migration in migrations[:3]:  # Show first 3 migrations
                    print(
                        f"  - {migration['id']}: {migration['status']} ({migration['progress']:.1f}%)"
                    )

            return migrations
        else:
            print_error(f"Failed to get migrations: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error getting migrations: {e}")
        return []


def main():
    """Main test function"""
    print_section("BabylonPiles Storage API Test")
    print_info("Testing storage service endpoints...")

    # Test API health first
    if not test_api_health():
        print_error("API health check failed. Make sure BabylonPiles is running.")
        sys.exit(1)

    # Test getting current drives
    drives = test_get_drives()

    # Test scanning for new drives
    scan_success = test_scan_drives()

    # Test storage status
    status = test_storage_status()

    # Test storage allocation
    allocation_success = test_allocate_storage()

    # Test getting chunks
    chunks = test_get_chunks()

    # Test getting migrations
    migrations = test_get_migrations()

    # Summary
    print_section("Test Summary")
    print_info(f"Current drives: {len(drives)}")
    print_info(f"Drive scan: {'✓' if scan_success else '✗'}")
    print_info(f"Storage status: {'✓' if status else '✗'}")
    print_info(f"Storage allocation: {'✓' if allocation_success else '✗'}")
    print_info(f"Chunks: {len(chunks)}")
    print_info(f"Migrations: {len(migrations)}")

    if drives:
        print_success("Storage API is working correctly!")
        print_info("You can now use the babylonpiles script to manage drives.")
    else:
        print_info(
            "No drives configured yet. Use the babylonpiles script to add drives."
        )


if __name__ == "__main__":
    main()
