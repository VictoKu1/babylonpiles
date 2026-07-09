#!/usr/bin/env python3
"""
Test runner for BabylonPiles test suite
Runs all tests in the tests directory
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


SERVICE_HEALTH_ENDPOINTS = {
    "backend": "http://localhost:8080/api/v1/storage/health",
    "storage": "http://localhost:8001/health",
}

TEST_SERVICE_REQUIREMENTS = {
    "test_cross_platform.py": {"backend"},
    "test_download_functionality.py": {"backend"},
    "test_hotspot.py": {"backend"},
    "test_metadata.py": {"backend"},
    "test_permissions.py": {"backend"},
    "test_storage_api.py": {"backend", "storage"},
    "test_storage_calculation.py": {"backend"},
    "test_user_config.py": {"backend"},
}


def is_service_available(health_url):
    """Check whether a service health endpoint is reachable."""
    try:
        with urlopen(health_url, timeout=2) as response:
            return 200 <= response.status < 300
    except (URLError, TimeoutError, OSError):
        return False


def get_available_services():
    """Probe required integration services and return availability map."""
    return {
        name: is_service_available(url)
        for name, url in SERVICE_HEALTH_ENDPOINTS.items()
    }


def should_skip_test(test_name, service_status):
    """Return missing services for this test, if any."""
    required = TEST_SERVICE_REQUIREMENTS.get(test_name, set())
    missing = [service for service in required if not service_status.get(service, False)]
    return missing

def run_test(test_file):
    """Run a single test file"""
    try:
        print(f"Running {test_file}...")
        
        # Set environment variables for proper encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=60,
                              env=env, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"PASSED: {test_file}")
            return True
        else:
            print(f"FAILED: {test_file}")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {test_file}")
        return False
    except Exception as e:
        print(f"ERROR: {test_file} - {e}")
        return False

def run_all_tests():
    """Run all test files in the tests directory"""
    print("BabylonPiles Test Suite Runner")
    print("=" * 50)
    
    # Get all test files
    test_dir = Path(__file__).parent
    test_files = [f for f in test_dir.glob("test_*.py") if f.name != "run_all_tests.py"]
    
    if not test_files:
        print("No test files found in tests directory")
        return
    
    print(f"Found {len(test_files)} test files")
    print()
    
    service_status = get_available_services()
    unavailable = [name for name, available in service_status.items() if not available]

    if unavailable:
        print("Integration service check:")
        for service_name in unavailable:
            print(f"  - {service_name}: unavailable")
        print("Integration tests that require unavailable services will be skipped.")
        print()

    # Run tests
    passed = 0
    failed = 0
    skipped = 0
    
    for test_file in sorted(test_files):
        missing_services = should_skip_test(test_file.name, service_status)
        if missing_services:
            print(f"SKIPPED: {test_file} (missing services: {', '.join(missing_services)})")
            skipped += 1
        elif run_test(test_file):
            passed += 1
        else:
            failed += 1
        print()
    
    # Summary
    print("=" * 50)
    print("Test Results Summary")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows compatibility
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    sys.exit(run_all_tests()) 