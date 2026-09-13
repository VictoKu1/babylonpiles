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

## Isolated security regressions

The `test_security_*.py` scripts exercise authentication, file and backup containment, sharing lifecycle, source HTTP policy, upload limits, service credentials, and the public request form. They use temporary databases and storage. Run them in the backend image with the repository mounted read-only (from the repository root on Linux):

```sh
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/repo,readonly" \
  -e PYTHONPATH=/repo/backend -e STATE_DIR=/tmp/security-tests \
  -e PYTHONDONTWRITEBYTECODE=1 \
  babylonpiles-backend python -c 'import pathlib,subprocess,sys; tests=sorted(pathlib.Path("/repo/tests").glob("test_security_*.py")); tests=[p for p in tests if p.name != "test_security_stack.py"]; results=[subprocess.run([sys.executable,str(p)]).returncode for p in tests]; sys.exit(any(results))'
```

On Windows, substitute the absolute repository path for `$PWD` in the bind-mount argument. Frontend checks run with `docker run --rm --network none babylonpiles-frontend npm test` and `npm run build` in the same image.

After rebuilding the images, `python tests/test_security_stack.py --run` starts an isolated Compose project with no host ports, host directory mounts, or outbound network. It checks real service startup, administrator setup, login through the frontend proxy, private/public file access, uploads, service credentials, and restart persistence. It refuses existing test-project resources and removes only the resources it created. Without `--run`, it only prepares and validates the configuration.

The older live-server scripts above assume anonymous administration and a directly exposed storage port. Those contracts are intentionally removed. Do not use them against a real installation or interpret their unauthenticated 401 responses as regressions; use the isolated security suite and full-stack checks for these boundaries.
