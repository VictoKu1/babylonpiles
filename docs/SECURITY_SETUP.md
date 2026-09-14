# Security setup and upgrades

This guide describes the `security` branch. The default `main` branch does not yet include its authentication and state-volume changes. Follow [Installation](INSTALL.md) for a new checkout; preserve the old database as described below before upgrading an existing one.

## First administrator

**There is no default administrator account or password.** The login screen expects an account that already exists in the database. On a fresh installation, create that account in a terminal before signing in; the browser has no first-account setup form. Authentication protects administration and private files from unauthenticated access.

Run these commands from the project folder on the computer running Docker. If you have configured storage through the Unix helper, use `bash ./babylonpiles.sh compose ...` in place of `docker compose ...` to retain its saved mapping. Start the services and wait for readiness:

```sh
docker compose up --build -d --wait
```

Then create your first administrator:

```sh
docker compose exec backend python -m app.admin create --username admin
```

At `Password:`, enter a password of at least **12 characters**. Enter the same password at `Confirm password:`. The terminal hides your typing. When the command prints `Account updated successfully.`, open [the frontend](http://localhost:3000) and sign in with username **admin** and the password you chose. If you use a different value for `--username`, sign in with that value instead.

This command creates an active administrator locally. The registration API requires an existing administrator and creates ordinary user accounts; it cannot bootstrap or create an administrator. The account persists in the state volume, so you do not need to recreate it after a normal container restart.

Management APIs require an active administrator. Login accepts a JSON body, such as `{"username":"admin","password":"your password"}`, at `POST /api/v1/auth/login`; credentials in query strings are no longer accepted. The browser receives an HttpOnly, SameSite=Strict session cookie. API clients can use the returned Bearer token. Cookie-authenticated mutations must send an `Origin` matching the deployment; the frontend handles this through its same-origin API proxy.

Public endpoints include health checks, login/logout, API documentation, and the explicitly public hotspot content/download and upload-request routes. `/api/v1/auth/me` requires an active signed-in account. Management APIs and private file access require an administrator. An upload request is a request for review, not permission to write files.

The optional Unix storage helper also requires an administrator. It prompts for credentials and uses JSON login plus a Bearer header, or reads `BABYLONPILES_TOKEN` from its environment. Do not put credentials in command-line URLs. Once the helper has configured storage, use `bash ./babylonpiles.sh compose ...` for the Compose commands in this guide so its saved drive mapping remains applied. See [Installation](INSTALL.md) for details.

## Reset an existing administrator's password

If the creation command reports `Account already exists; use reset-password`, the username is already registered. Sign in with its existing password, or set a new password for your administrator:

```sh
docker compose exec backend python -m app.admin reset-password --username admin
```

Enter and confirm a new password of at least 12 characters, then sign in as **admin** with that password. Substitute your administrator's username if it differs. The reset command changes only the password; it does not grant an ordinary account administrator access or reactivate a disabled account. If the existing username belongs to an ordinary account, create the administrator with an unused username instead.

If Docker reports that the backend service is not running, start it with the Compose command above and check `docker compose logs --tail=50 backend` if startup fails. Keep the state volume when troubleshooting so account data remains available.

## Persistent state and service credentials

Compose keeps the account database, JWT signing key, and source catalog in `backend_state`, mounted at `/app/state`. Storage and mirrorer management requests require a shared credential generated on first startup in `service_secrets`, mounted at `/run/babylonpiles/secrets` in all three services. These mounts are writable so concurrent first startup can initialize the credential safely. Keep both volumes when recreating containers, and include them in protected backups.

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

Increase limits for larger archives only with sufficient free disk space, then recreate the affected services. The backend enforces download limits during transfer, including responses without a trustworthy Content-Length. These settings do not limit downloads performed by the vendored mirror scripts; see [Mirroring](MIRRORING.md). Direct torrent imports are disabled because torrent peers and paths cannot yet be constrained by the download policy. Download through a trusted local client and upload the resulting files instead.

Kiwix-Serve listens only on `127.0.0.1:8081` on the Docker host and mounts its ZIM content read-only. It does not enforce BabylonPiles permissions, so do not republish that port as a private-content gateway. On another device, authenticate to BabylonPiles, download a private ZIM file, and open it locally with Kiwix. Explicit public hotspot files remain available through the dedicated public download route.

## Reconfirm public shares after upgrading

Public permissions now identify the exact file that was shared. Legacy boolean permissions cannot prove which content was approved, so those files start private after the upgrade. Review and explicitly share the intended files again in Browse. Replacing a file, moving it, or restoring it from a backup requires a new sharing decision; a reused filename no longer inherits an older file's public access. Downloads already authorized stream the opened file rather than reopening a path that could have changed.

Incoming request bodies are also limited before multipart parsing: file uploads allow the configured file cap plus 64 KiB of form overhead, and other bodies are limited to 1 MiB. Each backend worker stages at most four incoming bodies, with a five-minute receiving deadline. Extra requests receive 503 and can be retried. The public upload-request form accepts bounded JSON and keeps at most 1,000 pending requests; submitting a request does not authorize a file upload.
