# BabylonPiles

BabylonPiles is an offline knowledge-server prototype. Use its web interface to manage downloaded archives, books, and other files, then access stored content over your local network. Docker Compose runs the React frontend, FastAPI backend, storage service, mirroring adapter, and Kiwix reader.

## Current capabilities

- Browse, upload, download, move, and delete files and folders; mark selected content public.
- Create and download piles from HTTP, Kiwix, and Project Gutenberg sources. Quick Add supports repository browsing and manual source entries.
- Configure OpenStreetMap and Internet Archive mirror jobs with UTC schedules and run logs.
- View content totals, download status, and system metrics. The dashboard refreshes every 30 seconds.
- Protect management operations and private files with administrator login. Public readers use the `/hotspot` page for explicitly shared content.

Initial builds and content downloads need internet access. You can read stored files over the local network without internet access. Direct torrent imports are disabled. Internet Archive mirror jobs currently generate catalogs and download instructions; they do not download entire collections.

The default Docker setup does not configure the host's Wi-Fi or enforce network isolation when you switch modes. See [Installation](docs/INSTALL.md) and [Mirroring](docs/MIRRORING.md) for deployment limits.

## Docker quick start

Use Docker with Linux-container support, the Compose v2 plugin (`docker compose`), and Git. Allow disk space for the images and your chosen content; large archives can require substantial additional storage.

### 1. Clone the repository

These instructions describe the `security` branch, which contains administrator authentication. The default `main` branch does not yet contain that setup.

```sh
git clone --branch security --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

If you already cloned this branch without submodules, initialize the mirrorer dependency:

```sh
git submodule update --init --recursive
```

Existing deployments should read [Security setup and upgrades](docs/SECURITY_SETUP.md) before recreating the backend. That guide covers preserving account data and configuring HTTPS.

### 2. Start the services

```sh
docker compose up --build -d --wait
```

### 3. Create an administrator and sign in

**A fresh installation has no administrator account or default password.** Create the first account from a terminal on the Docker host; the browser login screen cannot create it.

```sh
docker compose exec backend python -m app.admin create --username admin
```

At `Password:`, choose a password of at least **12 characters**, then repeat it at `Confirm password:`. The terminal hides typed characters. After `Account updated successfully.`, open [localhost:3000](http://localhost:3000) and sign in as **admin** with the password you chose.

If that account already exists, use its password or follow the [password reset instructions](docs/SECURITY_SETUP.md#reset-an-existing-administrators-password).

### 4. Manage the services

Run the command for the operation you need:

| Operation | Command |
| --- | --- |
| View logs | `docker compose logs -f` |
| Stop services and preserve named volumes | `docker compose down` |
| Rebuild and apply application changes | `docker compose up --build -d --wait` |
| Rebuild the frontend after dependency changes | `docker compose up --build -d --no-deps --renew-anon-volumes frontend` |

The frontend keeps dependencies in an anonymous volume, so an image rebuild alone can retain an old `node_modules`. Do not add `--volumes` to `docker compose down` unless you intend to delete named-volume data.

On Unix, the optional `bash ./babylonpiles.sh` helper can manage Compose and dedicated host storage directories. After saving a storage mapping with the helper, use `bash ./babylonpiles.sh compose ...` for subsequent Compose commands so those mounts remain configured. See [Installation](docs/INSTALL.md).

## Using the application

### Files and piles

The file browser supports file uploads, directory creation, downloads, previews for supported formats, and public/private sharing. Drag files or folders onto a folder or the `..` entry to move them. Drop files from your desktop into the browser to upload them.

On the Piles page, add a source manually or use Quick Add to browse repositories. `Manual Entry...` accepts a source name, repository URL, and optional Info URL. The backend saves custom sources in the persistent state volume. An omitted Info URL disables that source's metadata-info button.

### Storage and dashboard

The dashboard reports bytes in the configured content and piles directories, counting overlapping files once. It refreshes every 30 seconds; it does not update instantly in response to operations on another page. System metrics describe the environment visible inside the backend container.

Chunk-storage drives use separate locations from the browser's content root. Adding a chunk-storage drive does not move existing browser files or expand the dashboard's content filesystem. Dashboard capacity has limitations for empty content roots and separate filesystems; see [Storage](docs/STORAGE.md) for the volume map, measurements, migration, and backups.

### Mirrored sources

Use the Updates page to create and run mirror jobs. Supported variants are the OpenStreetMap planet file and Internet Archive `software`, `music`, `movies`, and `texts`.

Schedules use UTC daily, weekly, or monthly presets. Mirror output goes to host `storage/piles/mirrors/<provider>/<variant>/` in the default Compose setup. The file browser uses a separate root. Review [Mirroring](docs/MIRRORING.md) for actual outputs and space requirements before starting a job.

### ZIM files and Kiwix

Kiwix-Serve reads top-level `.zim` files in host `storage/piles` and binds to [localhost:8081](http://localhost:8081) on the Docker host. With no archives, it serves an empty library. After adding an archive, restart it:

```sh
docker compose restart kiwix-serve
```

Use the helper's Compose wrapper for this command if you configured managed storage. Kiwix reads the archive mount without write access and does not enforce BabylonPiles file permissions. It is not exposed to other LAN devices by default. For private ZIM content on another device, sign in to BabylonPiles, download the file, and open it with a local Kiwix reader.

## Development and project status

See [Contributing](CONTRIBUTING.md) for source changes and frontend checks, and [tests/README.md](tests/README.md) for isolated backend, frontend, installer, and Docker integration checks. Older live-server test scripts assume anonymous administration and are not the supported validation path.

[RoadMap.md](RoadMap.md) distinguishes implemented features from planned work. [TODO.md](TODO.md) tracks remaining tasks. Planned work includes content indexing, a user-management interface, host-network integration, and continuous integration.

## Documentation

- [Installation](docs/INSTALL.md): Docker setup and troubleshooting
- [Security setup and upgrades](docs/SECURITY_SETUP.md): administrator accounts, persistent state, HTTPS, and transfer limits
- [Storage](docs/STORAGE.md): volumes, drive management, and backups
- [Mirroring](docs/MIRRORING.md): providers, schedules, and output
- [API reference](docs/API.md): authentication, endpoints, and request examples
- [Project summary](PROJECT_SUMMARY.md): components and implementation limits
- [Test suite](tests/README.md): checks and execution instructions
- [Security policy](SECURITY.md): vulnerability reporting
- [Publication privacy checks](docs/PRIVACY.md): local-file exclusions and commit/push checks

## License

See the [GNU General Public License v3 text](LICENSE).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution instructions.
