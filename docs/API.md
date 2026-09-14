# API Reference

## Base URLs

- Local backend: `http://localhost:8080`
- OpenAPI UI: `http://localhost:8080/docs`
- Versioned API root: `http://localhost:8080/api/v1`

The frontend at `http://localhost:3000` proxies `/api` to the backend. Browser clients should use that same-origin path; the backend does not grant cross-origin API access. Paths below are relative to the deployment host.

## Request Shapes

- `POST /api/v1/auth/login` and `POST /api/v1/auth/register` require JSON bodies. Never put credentials in a URL.
- Management routes require an active administrator, including `/api/v1/storage/health`. `/api/v1/auth/me` accepts any active authenticated account. `/health` and the three public hotspot routes listed below do not require login.
- `POST /api/v1/files/upload` and `POST /api/v1/piles/{pile_id}/upload` require multipart form data with a `file` field. The files endpoint also accepts a `path` field relative to the data directory.
- `POST /api/v1/files/mkdir`, `POST /api/v1/files/move`, and `POST /api/v1/files/permission/{file_path:path}` use form fields.
- `POST /api/v1/mirrors/jobs` and `PUT /api/v1/mirrors/jobs/{job_id}` expect JSON.
- `POST /api/v1/piles/add-source` expects JSON.
- `POST /api/v1/piles/validate-url` uses a form field.
- `POST /api/v1/system/user/config` expects JSON.
- `POST /api/v1/system/mode` uses a `mode` query parameter. Restart/shutdown take no body. Hotspot approval/rejection use the request ID in the path; public upload-request submission requires bounded JSON (`filename`, `editor_name`, optional `client_ip` and `client_mac`). A review request grants no file-upload permission.

## Authentication

- `POST /api/v1/auth/login` with JSON `{"username":"admin","password":"your password"}`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/register` with JSON fields `username`, `password`, optional `email` and `full_name`; requires an administrator and creates a regular user.

There is no default account or password. Create the first administrator using the CLI in [Security setup](SECURITY_SETUP.md). `/auth/register` is not a first-account setup endpoint, and the regular users it creates cannot access the management dashboard. Registration passwords must be 12–1024 characters.

`/auth/login` returns `access_token`, `token_type`, and `user` inside `data`, and sets an HttpOnly, SameSite=Strict cookie named `babylonpiles_session`, scoped to `/api`. Sessions expire after 30 minutes by default. API clients can send `Authorization: Bearer <access_token>`.

Cookie-authenticated mutations must send the deployment's matching `Origin`; the frontend supplies this through the same-origin proxy. Login accepts requests without an `Origin` header, but rejects a supplied origin that does not match. `/auth/logout` clears the cookie; it does not revoke a copied bearer token before its expiry. See [Security setup](SECURITY_SETUP.md) for origin and HTTPS configuration.

## Transfer Limits

Default limits are:

| Setting | Default | Applies to |
| --- | --- | --- |
| `MAX_UPLOAD_SIZE` | 100 MiB | Uploaded file bytes |
| `MAX_FILE_SIZE` | 1 GiB | Ordinary source downloads and storage-service files |
| `MAX_CATALOG_SIZE` | 8 MiB | Catalog and metadata responses fetched by backend source handlers |

Other incoming request bodies are limited to 1 MiB. Upload requests allow 64 KiB of multipart overhead in addition to the file limit. Oversized requests or transfers can return HTTP 413. These limits do not constrain the separate EmergencyStorage shell workflows; see [Mirrored sources](MIRRORING.md).

Backend content imports accept public HTTP(S) URLs without embedded credentials. Localhost, private network addresses, and redirects to those addresses are rejected. Torrent imports are disabled; upload files downloaded with a trusted local client instead.

## Piles

- `GET /api/v1/piles/` lists piles. Optional query params: `category`, `status` (`active`, `downloading`, `ready`).
- `GET /api/v1/piles/categories`
- `GET /api/v1/piles/sources-list`
- `POST /api/v1/piles/add-source`
- `GET /api/v1/piles/browse-source?url=...&description_url=...`
- `GET /api/v1/piles/file-info?filename=...&description_url=...`
- `GET /api/v1/piles/{pile_id}`
- `POST /api/v1/piles/`
- `PUT /api/v1/piles/{pile_id}`
- `DELETE /api/v1/piles/{pile_id}`
- `POST /api/v1/piles/{pile_id}/upload`
- `GET /api/v1/piles/{pile_id}/download`
- `POST /api/v1/piles/{pile_id}/toggle`
- `GET /api/v1/piles/{pile_id}/logs?limit=...`
- `POST /api/v1/piles/{pile_id}/download-source`
- `POST /api/v1/piles/validate-url`
- `GET /api/v1/piles/gutenberg-search?query=...`

`POST /api/v1/piles/add-source` accepts `{"name":"My source","repo_url":"https://example.org/files/","info_url":null}` and returns the updated source catalog. `name` is required and limited to 200 characters; `repo_url` is required, and `info_url` is optional. Both URLs must satisfy the public-source rules above. An omitted or null `info_url` is returned as the string `"None"` in the catalog.

## Files

- `GET /api/v1/files?path=...`
- `GET /api/v1/files/download?path=...`
- `POST /api/v1/files/upload`
- `POST /api/v1/files/mkdir`
- `DELETE /api/v1/files/delete?path=...`
- `GET /api/v1/files/view/{file_path:path}`
- `GET /api/v1/files/preview/{file_path:path}`
- `GET /api/v1/files/zim-viewer/{file_path:path}`
- `GET /api/v1/files/download-status`
- `GET /api/v1/files/permission/{file_path:path}`
- `POST /api/v1/files/permission/{file_path:path}/toggle`
- `POST /api/v1/files/permission/{file_path:path}`
- `GET /api/v1/files/metadata/{file_path:path}`
- `POST /api/v1/files/move`

File paths are relative to `DATA_DIR` (default `/mnt/babylonpiles/data`), not arbitrary host paths. `POST /api/v1/files/mkdir` accepts `folder_name` and an optional parent `path`. `POST /api/v1/files/move` accepts `src_path` and `dest_path`. Permission updates accept the Boolean form field `is_public`.

Publishing a file makes it available through the public hotspot download route. Replacing or changing that file invalidates the existing publication grant; publish it again to share the new content.

## System

- `GET /api/v1/system/status`
- `GET /api/v1/system/mode`
- `POST /api/v1/system/mode?mode=learn|store`
- `GET /api/v1/system/storage`
- `GET /api/v1/system/network`
- `GET /api/v1/system/metrics`
- `POST /api/v1/system/restart`
- `POST /api/v1/system/shutdown`
- `GET /api/v1/system/drives`
- `POST /api/v1/system/hotspot/start`
- `POST /api/v1/system/hotspot/stop`
- `GET /api/v1/system/hotspot/status`
- `GET /api/v1/system/hotspot/public-content`
- `GET /api/v1/system/hotspot/download/{file_path:path}`
- `POST /api/v1/system/hotspot/request-upload`
- `POST /api/v1/system/hotspot/approve-request/{request_id}`
- `POST /api/v1/system/hotspot/reject-request/{request_id}`
- `GET /api/v1/system/hotspot/requirements`
- `GET /api/v1/system/user/config`
- `POST /api/v1/system/user/config`
- `GET /api/v1/system/gitinfo`

`POST /api/v1/system/user/config` accepts JSON like `{"user_name":"Alice"}` to change the displayed operator/hotspot name. It does not change the login account. `GET /api/v1/system/gitinfo` returns `version` and `build`; these are best-effort Git values with hard-coded fallbacks, not a reliable image build timestamp.

`GET /api/v1/system/storage` returns storage measurements inside `data`:

| Field | Meaning |
| --- | --- |
| `content_size_bytes` | Regular-file bytes under `PILES_DIR` and `DATA_DIR`, excluding symbolic links and counting hard links or overlapping roots once |
| `piles_size_bytes` | The portion measured under `PILES_DIR` |
| `total_bytes`, `available_bytes` | Capacity and free space for the filesystem containing `DATA_DIR`; may be zero when no data storage is detected |
| `used_bytes`, `usage_percent` | Data-directory file usage and its share of that filesystem's capacity |
| `no_storage_allocated` | `true` when the data-directory check finds no usable content storage |

The content total includes files such as backups and mirror logs within those roots. It is not the sum of pile database records. Capacity fields do not add together all mounted drives. `/system/metrics` instead reports CPU, memory, and the backend's root filesystem usage.

Hotspot start/stop, restart, and shutdown routes depend on Linux networking tools and host privileges that the default Compose services do not provide. Their presence in the API does not make them host controls in the default deployment.

The public routes are `GET /api/v1/system/hotspot/public-content`, `GET /api/v1/system/hotspot/download/{file_path:path}`, and `POST /api/v1/system/hotspot/request-upload`. The upload-request body requires `filename` (1–255 characters) and `editor_name` (1–200); optional `client_ip` and `client_mac` are each limited to 64 characters. Requests are kept in memory and lost on backend restart. The queue returns HTTP 429 at 1,000 entries. Approval only changes the review status; file upload remains administrator-only. Rejection accepts an optional `reason` query parameter.

## Storage

- `GET /api/v1/storage/drives`
- `GET /api/v1/storage/drives/{drive_id}`
- `POST /api/v1/storage/drives/scan`
- `POST /api/v1/storage/allocate?file_size=...&file_id=...`
- `GET /api/v1/storage/chunks?file_id=...`
- `GET /api/v1/storage/chunks/{chunk_id}`
- `POST /api/v1/storage/migrate?chunk_id=...&target_drive=...`
- `GET /api/v1/storage/migrations`
- `GET /api/v1/storage/migrations/{migration_id}`
- `GET /api/v1/storage/status`
- `GET /api/v1/storage/files/{file_id}`
- `DELETE /api/v1/storage/files/{file_id}`
- `GET /api/v1/storage/health`

These routes are thin proxies to the storage client/service and return service-shaped payloads rather than a uniform local schema.

## Mirrors

- `GET /api/v1/mirrors/providers`
- `GET /api/v1/mirrors/jobs`
- `POST /api/v1/mirrors/jobs`
- `PUT /api/v1/mirrors/jobs/{job_id}`
- `POST /api/v1/mirrors/jobs/{job_id}/run`
- `GET /api/v1/mirrors/jobs/{job_id}/runs?limit=...`
- `GET /api/v1/mirrors/runs/{run_id}/logs?tail=...`

Mirror job payloads use fixed enums rather than arbitrary source strings:

- `provider`: `openstreetmap` or `internet_archive`
- `variant`: `planet`, `software`, `music`, `movies`, or `texts`
- `schedule_frequency`: `disabled`, `daily`, `weekly`, or `monthly`

Valid pairs are `openstreetmap/planet` and `internet_archive` with `software`, `music`, `movies`, or `texts`. Each pair can have only one job; duplicates return HTTP 409.

Jobs default to `enabled: true` and `schedule_enabled: false`. To enable scheduling, send `schedule_enabled: true` and a frequency other than `disabled`. `schedule_time_utc` must use `HH:MM` 24-hour UTC format and defaults to `02:00`. `PUT` accepts partial updates.

`schedule_day` rules:

- omit for `disabled` and `daily`
- `0-6` for `weekly` where Sunday is `0`
- `1-31` for `monthly`

Monthly days beyond the end of a month run on that month's last day. Disabled jobs cannot run manually. An already-running job cannot be edited or started again (HTTP 409).

The run-history `limit` defaults to 20 (range 1–100); log `tail` defaults to 40 lines (range 1–500). Mirror jobs write into the shared piles directory under `mirrors/<provider>/<variant>/`. Execution happens in the internal `mirrorer` service. A completed Internet Archive run currently prepares catalogs and download links, not the collection payloads; see [Mirrored sources](MIRRORING.md).

## Updates

- `GET /api/v1/updates/`
- `GET /api/v1/updates/{log_id}`
- `POST /api/v1/updates/pile/{pile_id}`
- `POST /api/v1/updates/pile/{pile_id}/rollback?version=...`
- `POST /api/v1/updates/bulk?category=...`
- `GET /api/v1/updates/status`

The log list accepts optional `pile_id`, `status`, and `limit` query parameters; `limit` defaults to 50. Rollback requires an existing backup; omit `version` for the latest backup or supply its `YYYYMMDD_HHMMSS` identifier.

Current limitation: `/updates/status` is declared after `/updates/{log_id}`, so authenticated requests are handled as an invalid integer log ID and return HTTP 422. Use `/updates/` for logs and `/piles/?status=downloading` for active downloads until that routing issue is corrected.

## Pile Schemas

`PileCreate` requires:

- `name`
- `display_name`
- `category`
- `source_type`

`PileCreate` also accepts:

- `description`
- `source_url`
- `source_config`
- `tags`

`PileUpdate` accepts optional updates for:

- `display_name`
- `description`
- `category`
- `source_type`
- `source_url`
- `source_config`
- `tags`
- `is_active`

`name` must be a safe single path component and cannot be changed through `PileUpdate`. Use `kiwix`, `http`, or `gutenberg` for supported remote source handlers, or `local` for uploaded files. The schema accepts a source-type string, but this does not enable unsupported handlers or the disabled torrent importer.

## Other Backend Routes

- `GET /health`
- `GET /`

In the default Compose deployment, `/health` returns the backend health status, current mode, and version; `/` returns an API status message. The frontend is served separately on port 3000.

## Notes

- Response formats differ by endpoint. Many return `success` and `data`, while source catalogs, file responses, and storage proxies use other shapes. Check HTTP status before parsing or relying on `success`.
- The mirrored-source scheduler is separate from the older pile update routes under `/api/v1/updates`.
