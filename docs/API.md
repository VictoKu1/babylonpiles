# API Reference

## Base URLs
- Local backend: `http://localhost:8080`
- OpenAPI UI: `http://localhost:8080/docs`
- Versioned API root: `http://localhost:8080/api/v1`

## Request Shapes
- `POST /api/v1/auth/login` and `POST /api/v1/auth/register` read parameters from the query string, not a JSON body.
- `GET /api/v1/auth/me` is the only route in this surface that depends on bearer authentication in code.
- `POST /api/v1/files/upload`, `POST /api/v1/files/mkdir`, `POST /api/v1/files/move`, and `POST /api/v1/files/permission/{file_path:path}` use multipart form fields.
- `POST /api/v1/piles/add-source` expects JSON.
- `POST /api/v1/piles/validate-url` uses a form field.
- `POST /api/v1/system/user/config` expects JSON.
- `POST /api/v1/system/mode`, `POST /api/v1/system/restart`, `POST /api/v1/system/shutdown`, and the hotspot approval/request routes use query/path parameters as defined below.

## Authentication
- `POST /api/v1/auth/login?username=...&password=...`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/register?username=...&password=...&email=...&full_name=...`

`/auth/login` returns `access_token`, `token_type`, and `user`. `logout` is client-side token removal only.

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

`POST /api/v1/piles/add-source` stores `info_url` as the string `"None"` when it is omitted or null, matching the frontend compatibility path.

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

`POST /api/v1/files/move` uses `src_path` and `dest_path` form fields, not JSON.

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

`POST /api/v1/system/user/config` accepts JSON like `{"user_name": "Alice"}` and stores a cleaned version. `GET /api/v1/system/gitinfo` returns a version string and build date.

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

## Updates
- `GET /api/v1/updates/`
- `GET /api/v1/updates/{log_id}`
- `POST /api/v1/updates/pile/{pile_id}`
- `POST /api/v1/updates/pile/{pile_id}/rollback`
- `POST /api/v1/updates/bulk?category=...`
- `GET /api/v1/updates/status`

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

## Other Backend Routes
- `GET /health`
- `GET /`

`/health` returns the backend health status and current mode. `/` serves the frontend build when present, otherwise it returns a simple status message.

## Notes
- The old claims about rate limiting, WebSocket support, and standardized success/error envelopes were removed because they are not implemented in the current backend routes.
- Some system endpoints are described as admin-only in code comments, but the routes themselves do not currently enforce an auth dependency.
