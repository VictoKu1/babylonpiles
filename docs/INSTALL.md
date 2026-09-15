# Installation

Run the application with Docker Compose v2 and Linux containers. On Windows or macOS, use a Docker engine configured for Linux containers. Check `docker compose version` before starting. The optional Unix operator helper also requires Bash and Python 3.11 or newer; it does not run in native PowerShell.

## First installation

A fresh installation has no default administrator or password. The browser login form expects an account that already exists in the database; it cannot create the first administrator.

On the computer running Docker, open a terminal and clone the `security` branch. These instructions require its administrator setup, which is not yet on the default `main` branch. Run the setup commands from the project folder:

```sh
git clone --branch security --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker compose up --build -d --wait
docker compose exec backend python -m app.admin create --username admin
```

Enter and confirm a password of at least 12 characters. The terminal hides your password input. Then open [the frontend](http://localhost:3000) and sign in with username `admin` and the password you chose. The [backend](http://localhost:8080) and [API documentation](http://localhost:8080/docs) are also available locally.

If the command reports `Account already exists`, sign in with that administrator's credentials or [reset its password](SECURITY_SETUP.md#reset-an-existing-administrators-password). A password reset does not promote an ordinary user to administrator.

If you already use helper-managed storage, run Compose commands through `bash ./babylonpiles.sh compose`, as shown under [Optional Unix operator helper](#optional-unix-operator-helper).

If you already cloned without submodules, run `git submodule update --init --recursive` before building. The mirrorer image requires the vendored EmergencyStorage scripts.

Existing installations must follow [Security setup and upgrades](SECURITY_SETUP.md) to preserve account state before replacing an older backend. That guide also explains HTTPS and public shares.

## Manage the application

```sh
docker compose logs --tail=50
docker compose down                 # Preserve named volumes
docker compose up --build -d --wait # Apply image/configuration changes
```

To update the checkout, pull the desired version, refresh submodules, and rebuild:

```sh
git pull
git submodule update --init --recursive
docker compose up --build -d --wait
```

Only frontend source is bind-mounted for development. Backend, storage, and mirrorer edits require rebuilding their images; restarting an existing container does not apply new mounts or environment variables.

After changing `frontend/package.json` or `frontend/package-lock.json`, rebuild the frontend and replace its anonymous dependency volume:

```sh
docker compose up --build -d --no-deps --renew-anon-volumes frontend
```

The existing `/app/node_modules` volume otherwise retains the previous dependencies. This command replaces only the frontend's anonymous volume; the application's named content and account volumes remain in place. Use the helper's `compose` command here too if you use managed storage.

## Storage configuration

Backend content, account state, service credentials, and storage-service chunks use different locations. See [Storage](STORAGE.md) before moving or backing up any of them.

To add a drive manually, mount it with your operating system and create a dedicated `babylonpiles` directory on it. Add that directory to the existing `storage.volumes` list in `docker-compose.yml`, keeping its other volume entries:

```yaml
      - type: bind
        source: /media/external/babylonpiles
        target: /mnt/hdd2
        bind:
          create_host_path: false
```

On Windows, use an absolute Docker-accessible path such as `D:/babylonpiles`. Set the storage service's `MAX_DRIVES` to the highest configured drive number, then validate and recreate storage:

```sh
docker compose config --quiet
docker compose up -d --force-recreate storage
```

Mounting a new chunk-storage location does not migrate existing backend content or database files. Preserve the original locations until a deliberate migration and readback have completed. Do not recursively change the ownership of an existing disk.

## Optional Unix operator helper

```sh
bash ./babylonpiles.sh start
bash ./babylonpiles.sh add-drive
bash ./babylonpiles.sh scan-drives
bash ./babylonpiles.sh remove-drive
```

Storage administration commands prompt for an administrator username/password; the helper sends credentials in JSON and keeps them in memory. Create the first administrator before using those commands. Automation can provide `BABYLONPILES_TOKEN` through its environment. The default API is `http://127.0.0.1:8080/api/v1`; `BABYLONPILES_API_URL` can select your deployment's trusted HTTPS endpoint.

Choose an existing directory or, on Linux, a full block-device path. Content is allocated in a dedicated `babylonpiles` child directory. The helper validates effective Compose configuration before changing storage, recreates the storage service, checks its authenticated drive list, and restores the previous configuration on failure. It refuses to detach a drive with allocated chunks. Detaching preserves the disk's files and host mount; unmount through the operating system after you have verified the detach.

The saved mapping is `.babylonpiles-storage.json` in the project root. **Once you use this mapping, run subsequent Compose commands through the helper** so it is applied to the current base configuration:

```sh
bash ./babylonpiles.sh compose up --build -d --wait
bash ./babylonpiles.sh compose exec backend python -m app.admin create --username admin
bash ./babylonpiles.sh compose logs --tail=50
bash ./babylonpiles.sh stop
```

Direct `docker compose` does not read the helper's mapping. Back up that mapping alongside your deployment configuration; it contains host paths, not file contents or credentials.

For a Linux device that should mount after reboot, use `bash ./babylonpiles.sh auto-mount`. This uses its actual filesystem type and UUID, a dedicated `/media/babylonpiles/<uuid>` mountpoint, and a validated fstab entry. It preserves unrelated fstab entries and rolls back its own entry on failure. Existing conflicting mount entries must be managed through the OS. These host operations require `sudo`, `blkid`, `findmnt`, and `mount`; they are never run merely by starting the application.

## Host Wi-Fi access

Keep account/content volumes on reliable storage, and allow sufficient disk space for the chosen datasets. For an ARM computer such as a Raspberry Pi, check that every image in the Compose deployment provides a compatible architecture; the repository has no separate Raspberry Pi deployment configuration.

Configure Wi-Fi access with the host operating system's supported hotspot tools. Clients connect to the host and open `http://<host-address>:3000`; use HTTPS if the network is not trusted. Docker application containers remain on their normal bridge network.

The default backend container cannot configure the host's Wi-Fi interface: it has neither the required hotspot utilities nor host network access. Installing packages on the host does not add them to the container. Manage the access point through the host OS; the application's hotspot controls do not provision it in this Compose deployment.

## Mirrors and Kiwix

The Updates page manages supported mirror jobs, schedules, and run logs. See [Mirroring](MIRRORING.md) for actual dataset behavior and limits.

Kiwix is available at [localhost:8081](http://localhost:8081) on the Docker host. It has a read-only ZIM mount and does not enforce BabylonPiles permissions. For private content on another device, authenticate to BabylonPiles, download the file, and open it locally in Kiwix.

## Troubleshooting

- Inspect `docker compose ps` and service logs; use the helper equivalents when managed storage is configured.
- Initialize submodules before rebuilding mirrorer.
- Recreate a service after changing its mounts or environment.
- Check that a removable disk is mounted at its expected host path before starting storage.
- For login, HTTPS, transfer limits, and state upgrades, use [Security setup](SECURITY_SETUP.md).
- Test the helper without host mutations using `python3 -m unittest discover -s tests -p 'test_installer*.py' -v` on a Unix test environment. The extra parser test uses the installed Compose CLI to validate a fixture; it never creates containers and skips when the CLI is unavailable.
