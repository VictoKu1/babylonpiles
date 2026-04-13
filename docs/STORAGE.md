# Storage

## Scope

BabylonPiles has two storage-related layers:
- `storage/storage_service.py` runs the drive, chunk, allocation, and migration service directly.
- The backend exposes file, pile, and system routes under `/api/v1/storage`, `/api/v1/files`, `/api/v1/piles`, and `/api/v1/system`.
- Mirrored sources write into the shared piles volume through the internal `mirrorer` service while job state stays in the backend database.

## Storage Service

`storage/storage_service.py` manages:
- Drive discovery and status.
- File allocation across drives by chunk.
- Chunk migration between drives.
- Persistent metadata stored under `/app/data/metadata`.

Direct storage service routes:
- `GET /health`
- `GET /drives`
- `POST /drives/scan`
- `GET /drives/{drive_id}`
- `POST /allocate`
- `GET /chunks`
- `GET /chunks/{chunk_id}`
- `POST /migrate`
- `GET /migrations`
- `GET /migrations/{migration_id}`
- `GET /status`
- `GET /files/{file_id}`
- `DELETE /files/{file_id}`

`backend/app/core/storage_client.py` is the async client used by the backend storage API to call those routes.

## File Browser

`backend/app/api/v1/endpoints/files.py` and `frontend/src/pages/Browse.tsx` implement the file browser.

Implemented browser features:
- List files and folders under `/mnt/babylonpiles/data`.
- Upload files and create folders.
- Move and delete items.
- Download files with `GET /api/v1/files/download?path=...`.
- View file information with `GET /api/v1/files/view/{file_path}`.
- Preview supported file types with `GET /api/v1/files/preview/{file_path}`.
- Open ZIM files with `GET /api/v1/files/zim-viewer/{file_path}`.
- Toggle public/private access with `GET /api/v1/files/permission/{file_path}` and `POST /api/v1/files/permission/{file_path}/toggle`.
- Fetch detailed metadata with `GET /api/v1/files/metadata/{file_path}`.
- Show active downloads with `GET /api/v1/files/download-status`.

The browser stores permissions in `.permissions.json` and metadata in `.metadata.json` under `/mnt/babylonpiles/data`.

Mirrored datasets also appear in this browser because they are stored under `/mnt/babylonpiles/piles/mirrors/...`.

## Piles

`frontend/src/pages/Piles.tsx` manages pile creation and downloads.

Implemented pile behaviors:
- Add piles with `source_type` values of `kiwix`, `http`, `torrent`, or `gutenberg`.
- Validate source URLs before starting a download.
- Start a download with `POST /api/v1/piles/{pile_id}/download-source`.
- Show downloaded, downloading, and pending piles.
- Show download progress from `file_path`, `file_size`, `is_downloading`, and `download_progress`.
- Update `download_progress` every 512 KB during HTTP downloads.
- Use a 1 hour `aiohttp.ClientTimeout(total=3600)` for HTTP downloads.
- Show Project Gutenberg search results through `GET /api/v1/piles/gutenberg-search`.

The backend prevents starting a second download while a pile is already downloading.

## Mirrored Sources

`backend/app/api/v1/endpoints/mirrors.py`, `backend/app/core/mirror_scheduler.py`, and `mirrorer/app.py` implement mirrored-source management.

Implemented mirrored-source behavior:
- Create persisted mirror jobs for fixed provider and variant pairs.
- Schedule mirror runs with `daily`, `weekly`, or `monthly` UTC presets.
- Trigger manual runs through `POST /api/v1/mirrors/jobs/{job_id}/run`.
- Persist mirror run history, bytes written, and error details.
- Tail local or proxied logs through `GET /api/v1/mirrors/runs/{run_id}/logs`.
- Recover interrupted running jobs as failed after backend restart.

Mirrored content layout:
- `/mnt/babylonpiles/piles/mirrors/openstreetmap/planet/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/software/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/music/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/movies/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/texts/`

The vendored EmergencyStorage scripts may create another dataset-specific directory inside those variant folders. The mirror adapter only passes fixed server-side command templates and does not accept arbitrary shell arguments from the frontend.

## Hotspot And User Config

`backend/app/api/v1/endpoints/system.py` exposes the hotspot and user configuration routes used by the dashboard UI:
- `POST /api/v1/system/hotspot/start`
- `POST /api/v1/system/hotspot/stop`
- `GET /api/v1/system/hotspot/status`
- `GET /api/v1/system/hotspot/requirements`
- `GET /api/v1/system/hotspot/public-content`
- `GET /api/v1/system/hotspot/download/{file_path}`
- `POST /api/v1/system/hotspot/request-upload`
- `POST /api/v1/system/hotspot/approve-request/{request_id}`
- `POST /api/v1/system/hotspot/reject-request/{request_id}`
- `GET /api/v1/system/user/config`
- `POST /api/v1/system/user/config`

The hotspot configuration is built around `BabylonPiles`, `babylon123`, `192.168.4.0/24`, and `192.168.4.1`, with the SSID optionally personalized from the stored user name.

The hotspot requirements response also includes platform-specific installation instructions, including `brew install hostapd` and `brew install dnsmasq` for `Darwin`/macOS.

`frontend/src/pages/Dashboard.tsx` wires those hotspot and user-config endpoints into the UI. `frontend/src/pages/System.tsx` is currently only a static placeholder and does not implement those controls.

## Tests

The test scripts in `tests/*.py` cover the implemented behavior above:
- `test_storage_api.py` checks the storage service through the backend API and direct service URL.
- `test_storage_calculation.py` checks dashboard storage calculations.
- `test_download_functionality.py` checks pile download flow, duplicate-download prevention, and download status.
- `test_permissions.py` checks public/private file toggling.
- `test_metadata.py` checks file and folder metadata.
- `test_hotspot.py` checks hotspot start/stop, public content, and upload requests.
- `test_cross_platform.py` checks hotspot requirements and platform-dependent behavior.
- `test_user_config.py` checks user-name persistence and personalized hotspot SSIDs.

## What Is Not Documented Here

The inspected code does not confirm any of the following claims, so they are intentionally omitted:
- Automatic temporary-file cleanup behavior.
- Torrent-specific backend implementation details.
