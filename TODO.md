# BabylonPiles work items

These items describe the current source tree. Unchecked items need implementation or verification; they are not available features. The [roadmap](RoadMap.md) provides the broader direction.

## Current capabilities

- [x] Run application services with Docker Compose and initialize the pinned EmergencyStorage submodule.
- [x] Enforce administrator access to management APIs and private files.
- [x] Hash passwords, migrate legacy plaintext rows, and provide local administrator creation/password reset.
- [x] Share explicitly approved files through public endpoints.
- [x] Bound backend uploads, downloads, and catalog retrieval; restrict source fetches to public network destinations.
- [x] Implement HTTP, Kiwix, and Gutenberg source adapters, pile CRUD, and custom source entries.
- [x] Provide manual pile updates, update history, and basic per-pile backup/rollback.
- [x] Schedule supported mirror jobs in UTC and retain run history/logs.
- [x] Provide OpenStreetMap planet retrieval and Internet Archive catalog/instruction generation.
- [x] Support file uploads, moves, downloads, deletes, metadata, and supported-format previews.
- [x] Measure content bytes across data and pile roots without counting overlapping files twice.
- [x] Manage configured chunk-storage locations and migration through the storage service.
- [x] Validate helper-managed Compose storage mappings, with rollback on failed changes.
- [x] Add isolated backend, frontend component, installer, and Docker integration checks.

## Correctness and integration

- [ ] Report usable capacity for empty content roots and define aggregate capacity when content roots span filesystems.
- [ ] Fix the `GET /api/v1/updates/status` route being captured by the earlier `/{log_id}` route.
- [ ] Replace or retire legacy live-server tests that assume anonymous administration, exposed port 8001, or a nonexistent dashboard endpoint.
- [ ] Expand Docker integration coverage for actual mirrorer commands and scheduled runs, including failures and restart recovery.
- [ ] Test simultaneous uploads, downloads, moves, and directory scans against realistic data sizes.
- [ ] Verify current helper and application behavior across supported Docker host platforms.
- [ ] Implement host-network controls before describing Store mode as internet isolation or advertising container-managed Wi-Fi.

## Accounts and security

- [ ] Add an administrator user-management interface.
- [ ] Add login/API rate limits and security audit events.
- [ ] Review session expiry and recovery UX; refresh tokens and 2FA would be separate additions.
- [ ] Automate dependency and container-image vulnerability checks in CI.
- [ ] Test and document an HTTPS reverse-proxy deployment with certificate renewal; the current app already supports origin/secure-cookie settings.
- [ ] Add backup encryption and verify recovery from encrypted backups.
- [ ] Keep direct torrent imports disabled until peer destinations, paths, and transfer sizes can be constrained and tested.

## Content and storage

- [ ] Add application-wide indexing and content search.
- [ ] Extend automatic scheduling to standard pile updates.
- [ ] Add bounded Internet Archive collection downloads beyond catalog generation.
- [ ] Define a custom source-plugin interface; adding a repository URL is not a plugin system.
- [ ] Evaluate additional adapters such as RSS and CD3WD against a concrete content need.
- [ ] Add backup retention, integrity verification, and full-instance restore tooling.
- [ ] Improve chunk migration diagnostics, monitoring, and operator recovery.
- [ ] Clarify content-versus-chunk-storage capacity in the UI.
- [ ] Add instance-to-instance content sharing and export/import workflows if required.

## Interface

- [ ] Improve keyboard navigation, accessibility, and mobile layouts, with browser-based verification.
- [ ] Add multi-select/batch operations and undo for file moves.
- [ ] Expand preview coverage where the browser can render a format safely.
- [ ] Consider push-based progress updates; current dashboard/system refresh uses 30-second polling.
- [ ] Improve error messages, retry behavior, and expired-session handling.
- [ ] Evaluate offline browser caching/PWA support. Reading stored files from the local server already works without internet access.

## Performance and delivery

- [ ] Establish performance baselines for large directories and transfers.
- [ ] Reduce image and frontend bundle size where measurements justify changes.
- [ ] Add frontend code splitting or list virtualization when profiling identifies a need.
- [ ] Add CI for isolated backend tests, frontend tests/typecheck/lint/build, installer fixtures, and Docker builds.
- [ ] Add browser end-to-end tests for the main user workflows.
- [ ] Add reproducible backup/restore exercises and load tests.
- [ ] Define and automate a release process before assigning features to version numbers.

Keep completed work and implementation limits in the [README](README.md) and [project summary](PROJECT_SUMMARY.md) aligned with the code. See [Contributing](CONTRIBUTING.md) and [test instructions](tests/README.md) before running checks.
