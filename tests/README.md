# BabylonPiles Test Suite

This directory contains standalone test scripts for the implemented backend, storage, file browser, hotspot, and dashboard behavior.

## Test Files

- `test_storage_api.py` checks the storage service through the backend API and direct `:8001` service URL.
- `test_storage_calculation.py` checks dashboard content-storage calculations.
- `test_download_functionality.py` checks pile creation, download start, duplicate-download prevention, progress polling, and cleanup.
- `test_permissions.py` checks file permission toggling and file listings.
- `test_metadata.py` checks file and folder metadata, permission updates, and cleanup.
- `test_hotspot.py` checks hotspot status, start/stop, public content, and upload request handling.
- `test_cross_platform.py` checks hotspot requirements and platform-dependent behavior.
- `test_user_config.py` checks user-name configuration and personalized hotspot SSIDs.
- `run_all_tests.py` discovers every `test_*.py` file and runs them sequentially.

## Running Tests

Run a single script:
```bash
python tests/test_storage_api.py
```

Run the whole suite:
```bash
python tests/run_all_tests.py
```

## Prerequisites

- A running BabylonPiles backend on `http://localhost:8080`.
- A running storage service on `http://localhost:8001` for `test_storage_api.py`.
- Python 3 with the dependencies used by the scripts, including `requests` and `aiohttp`.
- Network access for tests that call external URLs, such as the download test target in `test_download_functionality.py`.

## Notes

- The runner sets `PYTHONIOENCODING=utf-8` on Windows so the emoji output from the scripts is handled consistently.
- These are direct scripts, not a pytest suite. There is no repository-level requirement to start Docker containers before running them.
