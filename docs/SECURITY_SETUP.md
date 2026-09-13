# Security setup and upgrades

## First administrator

Start the services with `docker compose up --build -d`, then run:

```sh
docker compose exec backend python -m app.admin create --username admin
```

The command prompts for a password and confirmation. Use at least 12 characters. It creates an active administrator locally; public registration cannot create an administrator. Sign in through [the frontend](http://localhost:3000). To reset an existing account's password, use `reset-password` in place of `create`. Resetting a password does not change that account's role.

Management APIs require an active administrator. Login accepts a JSON body, such as `{"username":"admin","password":"your password"}`, at `POST /api/v1/auth/login`; credentials in query strings are no longer accepted. The browser receives an HttpOnly, SameSite=Strict session cookie. API clients can use the returned Bearer token. Cookie-authenticated mutations must send an `Origin` matching the deployment; the frontend handles this through its same-origin API proxy.

Only health checks, login, the explicitly public hotspot content/download routes, and hotspot upload-request submission are available without administrator access. An upload request is a request for review, not permission to write files.

## Persistent state and service credentials

Compose keeps the account database, JWT signing key, and source catalog in `backend_state`, mounted at `/app/state`. Storage and mirrorer requests require a shared credential generated on first startup in `service_secrets`, mounted at `/run/babylonpiles/secrets` in all three services. These mounts are writable so concurrent first startup can initialize the credential safely. Keep both volumes when recreating containers, and include them in protected backups.

The backend root filesystem is read-only. Content volumes remain writable; `/tmp` is temporary storage. The storage service has no published host port. Access it through the authenticated backend API.

## Preserve an existing installation before upgrading

Earlier versions stored SQLite inside the backend container at `/app/babylonpiles.db`. Recreating that container can discard the database. Before rebuilding or replacing the old backend, save a consistent snapshot while the old container still exists:

```sh
docker compose exec backend python -c "import pathlib, sqlite3; p=pathlib.Path('/app/babylonpiles.db'); assert p.is_file(), 'Locate your configured database before continuing'; source=sqlite3.connect(str(p)); target=sqlite3.connect('/tmp/babylonpiles-upgrade.db'); source.backup(target); target.close(); source.close()"
docker compose cp backend:/tmp/babylonpiles-upgrade.db ./babylonpiles-upgrade.db
```

If the old deployment uses a different `DATABASE_URL`, back up that database instead. Protect the snapshot: older account rows contain plaintext passwords. Also preserve existing content volumes, `storage/piles`, and any customized source catalog. Stop the old services after the snapshot to avoid accepting changes that are absent from the backup.

Build the new backend image and restore the snapshot into a **new, empty** state volume before starting the new backend. One method uses an auxiliary container configured with the new Compose service:

```sh
docker compose build backend
docker compose run --rm --no-deps --entrypoint python --volume "${PWD}/babylonpiles-upgrade.db:/restore.db:ro" backend -c "import pathlib, shutil; destination=pathlib.Path('/app/state/babylonpiles.db'); assert not destination.exists(), 'State already contains a database; stop and reconcile it first'; shutil.copyfile('/restore.db', destination)"
docker compose up --build -d
```

Use an absolute host path for the snapshot if your shell does not expand `${PWD}`. The restore command refuses to overwrite an existing state database. Keep the original snapshot until you have checked the account list and content records; do not remove existing Docker volumes as part of this upgrade.

Startup hashes legacy plaintext account passwords before accepting requests. Existing passwords remain usable. If no administrator exists, create one with the local command above; choose an unused username if an old non-admin account already has the desired name. Existing sessions must sign in again because the previous default signing key is replaced.

## HTTPS and reverse proxies

For an HTTPS deployment, put these values in the Compose project's `.env` file, substituting your actual external origin:

```dotenv
PUBLIC_ORIGIN=https://knowledge.example.org
COOKIE_SECURE=true
```

The origin includes the scheme and any non-default port, without a path. Route the frontend and `/api` under that same origin, and preserve the browser's original `Host` and `Origin` headers through proxies. Recreate the backend after configuration changes. Secure cookies require HTTPS; the default local HTTP setup leaves `COOKIE_SECURE=false`. Restrict direct access to backend port 8080 when exposing the deployment through a TLS proxy so credentials cannot bypass HTTPS.

## Transfer limits and private content

These optional `.env` settings are byte counts:

| Setting | Default | Applies to |
| --- | ---: | --- |
| `MAX_UPLOAD_SIZE` | 104857600 (100 MiB) | Uploaded file size |
| `MAX_FILE_SIZE` | 1073741824 (1 GiB) | Backend source downloads and storage allocations |
| `MAX_CATALOG_SIZE` | 8388608 (8 MiB) | Downloaded source/catalog metadata |

Increase limits deliberately for larger archives, with sufficient free disk space, then recreate the affected services. Limits are enforced during transfer, including responses without a trustworthy Content-Length. Direct torrent imports are disabled because torrent peers and paths cannot yet be constrained by the download policy. Download through a trusted local client and upload the resulting files instead.

Kiwix-Serve listens only on `127.0.0.1:8081` on the Docker host and mounts its ZIM content read-only. It does not enforce BabylonPiles permissions, so do not republish that port as a private-content gateway. On another device, authenticate to BabylonPiles, download a private ZIM file, and open it locally with Kiwix. Explicit public hotspot files remain available through the dedicated public download route.

## Reconfirm public shares after upgrading

Public permissions now identify the exact file that was shared. Legacy boolean permissions cannot prove which content was approved, so those files start private after the upgrade. Review and explicitly share the intended files again in Browse. Replacing a file, moving it, or restoring it from a backup requires a new sharing decision; a reused filename no longer inherits an older file's public access. Downloads already authorized stream the opened file rather than reopening a path that could have changed.

Incoming request bodies are also limited before multipart parsing: file uploads allow the configured file cap plus 64 KiB of form overhead, and other bodies are limited to 1 MiB. Each backend worker stages at most four incoming bodies, with a five-minute receiving deadline. Extra requests receive 503 and can be retried. The public upload-request form accepts bounded JSON and keeps at most 1,000 pending requests; submitting a request does not authorize a file upload.
