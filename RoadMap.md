# BabylonPiles roadmap

This roadmap describes the current source tree. Planned items are development goals, not released features or dated commitments. Use [TODO.md](TODO.md) for actionable follow-up work and [README.md](README.md) for setup.

## Implemented

| Area | Current behavior |
| --- | --- |
| Deployment | Docker Compose runs the frontend, backend, storage service, mirrorer, and Kiwix. The optional Unix helper manages Compose and storage mappings. |
| Authentication | Administrator-only management APIs, hashed passwords, browser session cookies, and local account creation/password reset. |
| Files | Browse, upload, download, move, delete, preview supported formats, and publish selected files. |
| Piles | HTTP, Kiwix, and Gutenberg adapters; pile CRUD and download controls; custom repository entries in persistent state. |
| Updates | Manual pile update endpoints, update logs, and basic per-pile backup/rollback. |
| Mirrors | UTC scheduling, run history, and logs for supported OpenStreetMap and Internet Archive workflows. |
| Storage | Configured content roots, chunk allocation/migration, and helper-managed host directories or devices. |
| Monitoring | Dashboard and system metrics polled every 30 seconds; separate content totals and container-visible disk usage. |
| Tests | Isolated backend regressions, frontend component/auth checks, installer fixtures, and a disposable Docker integration harness. |

Internet Archive jobs currently prepare catalogs and download instructions. Direct torrent imports are disabled. The default Docker deployment does not provide working host Wi-Fi management or enforce Store-mode network isolation. Consult the [mirroring](docs/MIRRORING.md), [storage](docs/STORAGE.md), and [installation](docs/INSTALL.md) guides before relying on those workflows.

## Near-term work

- Improve storage reporting for empty content roots and deployments where content, piles, and chunk drives use different filesystems.
- Correct remaining endpoint/consumer mismatches, including the update-status route described in [API limitations](docs/API.md).
- Add continuous integration for the existing tests, frontend checks, dependency review, and Docker builds.
- Expand browser and cross-service tests for login, file operations, scheduled mirroring, and failure recovery.
- Measure large-directory, transfer, memory, and image-build performance before setting optimization targets.
- Improve keyboard access, mobile layouts, and error recovery in the existing interface.
- Add an account-management interface on top of the existing administrator authorization.

## Content and operations

- Index stored content and provide cross-content search. Kiwix's archive reader is separate from application-wide search.
- Extend scheduling to standard pile updates.
- Expand Internet Archive downloads beyond the current catalog workflow.
- Add backup verification, retention, and full-instance recovery tools beyond basic per-pile rollback.
- Implement and test host-network integration for Store/Learn mode and Wi-Fi controls.
- Improve storage migration diagnostics and failure recovery.
- Add API rate limiting and security audit events.

## Longer-term ideas

Additional source adapters, a plugin interface, batch file operations, push-based progress updates, offline browser caching, instance-to-instance sharing, and optional remote backups remain possible extensions. Native mobile apps, client libraries, and community infrastructure need their own designs and maintainers before becoming release commitments.

There is no checked-in automated release pipeline or version-by-version delivery schedule. Application version strings do not establish that all planned functionality is complete.
