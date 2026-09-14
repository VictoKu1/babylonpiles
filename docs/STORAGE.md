# Storage

BabylonPiles has separate backend content stores and a chunk-storage service. Adding storage-service drives does not move the backend's existing files, piles, database, or mirror jobs.

## Default Compose locations

| Resource | Container path | Persistent source | Consumers |
| --- | --- | --- | --- |
| File-browser content and file permissions | `/mnt/babylonpiles/data` (`DATA_DIR`) | `babylonpiles_data` named volume | Backend |
| Piles and mirrored datasets | `/mnt/babylonpiles/piles` (`PILES_DIR`) | Host `storage/piles` | Backend and mirrorer; Kiwix reads the host directory at `/data` |
| Mirror run logs | `/mnt/babylonpiles/data/mirror_logs` | `babylonpiles_data` named volume | Backend and mirrorer |
| Accounts, jobs, signing key, source catalog | `/app/state` (`STATE_DIR`) | `backend_state` named volume | Backend |
| Internal service credential | `/run/babylonpiles/secrets` | `service_secrets` named volume | Backend, storage, mirrorer |
| Storage-service drive 1 | `/mnt/hdd1` | Host `storage/info` | Storage |
| Chunk allocation/migration metadata | `/app/data/metadata` | `storage_data` named volume | Storage |

Compose normally prefixes named volumes with the project name. Preserve both content and metadata when backing up or relocating a deployment. `docker compose down` keeps named volumes; deleting volumes discards their state. See [Security setup and upgrades](SECURITY_SETUP.md) before replacing an older backend whose database was kept inside its container.

## File browser, piles, and mirrors

The file browser lists `DATA_DIR`. Its `.permissions.json` and `.metadata.json` files belong to that directory. Administrators can upload, create folders, move/delete files, preview/download supported files, and explicitly share files through the dedicated public routes. A file's public permission identifies the exact approved file; replacing or moving it requires sharing it again.

Standard pile downloads use `PILES_DIR`; direct torrent imports are disabled. HTTP, Kiwix, and Gutenberg source retrieval uses the configured transfer limits. Piles are managed from the Piles page and `/api/v1/piles`.

Mirror files use `PILES_DIR/mirrors/<provider>/<variant>/`, and the vendored scripts may add another dataset directory below that. With the default separate roots, these files **do not appear in the file browser rooted at `DATA_DIR`**. Access mirror files through the mounted host `storage/piles/mirrors` directory. See [Mirroring](MIRRORING.md) for the current provider outputs and limitations.

Kiwix reads top-level `.zim` files in host `storage/piles` and listens on the Docker host at `127.0.0.1:8081`. Restart Kiwix after adding a ZIM. Its reader does not implement BabylonPiles permissions; keep private content behind the authenticated application or open a downloaded copy locally.

## Dashboard storage figures

The dashboard reads `/api/v1/system/storage`. `content_size_bytes` counts file bytes across `DATA_DIR` and `PILES_DIR`, counting shared files once. Capacity and available space come from the filesystem containing `DATA_DIR`; they do not combine the capacities of the pile mount and storage-service drives. If `DATA_DIR` is absent, empty, or contains only hidden entries, the current API reports zero capacity and available space.

Use the authenticated `/api/v1/storage/drives` API or the helper's `status` command to inspect chunk-storage drives. Adding those drives does not increase the dashboard's backend-content capacity.

## Add or detach chunk-storage drives

The storage service discovers configured `/mnt/hddN` paths, allocates chunks, and exposes migration/status endpoints through the administrator-only backend `/api/v1/storage` routes. It is internal to the Compose network and has no published host port. Direct internal requests require the shared service credential.

For manual setup, mount a disk through the host operating system, create a dedicated directory, add a bind to the storage service, and set `MAX_DRIVES` to the highest configured drive number. Validate the Compose document and recreate storage to apply mount/environment changes. Keep the storage metadata and credential mounts. The complete example is in [Installation](INSTALL.md).

On Unix, the optional operator helper provides:

```sh
bash ./babylonpiles.sh add-drive
bash ./babylonpiles.sh scan-drives
bash ./babylonpiles.sh remove-drive
```

The helper uses administrator authentication, validates a generated Compose configuration, and allocates into a `babylonpiles` child of the selected directory. It binds that real directory into storage; it does not copy the disk onto the system filesystem or recursively change its ownership. It refuses removal when allocated chunks are reported, recreates storage after a change, and checks the resulting drive list. Failed operations restore the previous configuration and report rollback failures explicitly.

It keeps a small `.babylonpiles-storage.json` mapping. Subsequent commands must apply that mapping:

```sh
bash ./babylonpiles.sh compose up --build -d --wait
bash ./babylonpiles.sh compose logs storage
```

Direct `docker compose` ignores the mapping. Back up the map with the deployment configuration. Removal detaches the configured directory and preserves host files/mounts; migrate allocated chunks first and unmount with the OS only after verifying the detach. Device auto-mount is an explicit Linux operation; ordinary application startup never edits fstab or mounts drives.

## Tests

Run installer fixtures on a Unix test host with Bash and Python 3.11 or newer. They use temporary fixtures without changing real host mounts:

```sh
python3 -m unittest discover -s tests -p 'test_installer*.py' -v
```

The older scripts in `tests/` include live API exercises; read [the test guide](../tests/README.md) and configure a disposable deployment before running them. They are not evidence that every storage or host-network feature works on the current platform.
