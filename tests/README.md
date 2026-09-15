# BabylonPiles tests

Run the isolated checks below for current behavior. The older live-server scripts at the end of this guide predate administrator authentication and private service ports.

## Prepare the test images

Run commands from the repository root. Use Docker with Compose v2; the host-side scripts also need Python 3.11 or newer. On systems where Python is named `python3`, substitute it for `python` below.

```bash
git submodule update --init --recursive
docker compose -p babylonpiles build backend frontend storage mirrorer
```

The explicit project name produces the `babylonpiles-backend`, `babylonpiles-frontend`, `babylonpiles-storage`, and `babylonpiles-mirrorer` image names used by these commands and the stack harness. Building images does not start the application. Rebuild after source or dependency changes; frontend image-based tests do not use the running development container's source bind mount.

## Isolated backend regressions

These checks need no running application or real administrator account:

| Files | Coverage |
| --- | --- |
| `test_security_*.py`, excluding `test_security_stack.py` | Authentication, file and backup containment, sharing lifecycle, source HTTP policy, request limits, service credentials, and the public request form. |
| `test_dashboard_storage.py` | Authenticated dashboard storage response and content byte accounting, including nested roots, hard links, and symlinks. |
| `test_mirror_scheduling.py` | Daily, weekly, and monthly schedule calculations. |
| `test_installer.py` | Storage helper configuration, rollback, and shell entry points using temporary fixtures and stubbed host operations. |
| `test_privacy_guard.py` | Publication guards exercised against temporary Git repositories, including staged content and outgoing history. |

Run them in the backend image with the current repository mounted read-only. This example uses a POSIX shell on the Docker host:

```sh
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/repo,readonly" \
  -e PYTHONPATH=/repo/backend -e STATE_DIR=/tmp/security-tests \
  -e PYTHONDONTWRITEBYTECODE=1 \
  babylonpiles-backend python -c 'import pathlib,subprocess,sys; root=pathlib.Path("/repo/tests"); tests=sorted(p for p in root.glob("test_security_*.py") if p.name != "test_security_stack.py"); tests += [root/name for name in ("test_dashboard_storage.py", "test_mirror_scheduling.py", "test_installer.py", "test_privacy_guard.py")]; results=[subprocess.run([sys.executable,str(p)]).returncode for p in tests]; sys.exit(any(results))'
```

On Windows, use the absolute repository path for the bind source and PowerShell's backtick for line continuation, or place the command on one line. To run one regression script, keep the mount and environment options and replace `python -c '...'` with, for example, `python /repo/tests/test_dashboard_storage.py`.

The container has no external network or application data mounts. Each script runs in a separate Python process so its settings and database fixtures do not leak into the next script.

## Frontend checks

After rebuilding the frontend image, run:

```bash
docker run --rm --network none babylonpiles-frontend npm test
docker run --rm --network none babylonpiles-frontend npm run typecheck
docker run --rm --network none babylonpiles-frontend npm run lint
docker run --rm --network none babylonpiles-frontend npm run build
```

`npm test` runs `frontend/tests/*.test.cjs` with Node's test runner. These tests cover client authentication, rendering safety, and component workflows with mocked browser/network boundaries. They do not replace a browser check against the running application. `npm run build` runs Vite; type checking and linting are separate commands.

## Compose parser check

Run this on the Docker host:

```bash
python tests/test_installer_compose.py
```

It checks generated storage configuration through `docker compose config` using temporary files. It creates no containers and skips if the Docker CLI or Compose v2 is unavailable.

## Isolated stack integration

With the four images built above, run on the Docker host:

```bash
python tests/test_security_stack.py --run
```

The harness starts a separate `babylonpiles-security-check` Compose project with temporary volumes, no host ports or host directory mounts, and an internal network. It creates its own administrator and checks service startup, login through the frontend proxy, private/public file access, uploads, service credentials, and restart persistence. It does not start Kiwix or exercise physical Wi-Fi hotspot setup.

The harness refuses existing test-project resources and removes only resources it created. Without `--run`, it prepares and validates the configuration without starting containers. It writes generated configuration to the ignored `tmp/security-compose.json` file and prints results to the terminal.

## Legacy live-server scripts and runner

The following scripts need updates before they can validate the current authenticated deployment:

- `test_storage_api.py`
- `test_storage_calculation.py`
- `test_download_functionality.py`
- `test_permissions.py`
- `test_metadata.py`
- `test_hotspot.py`
- `test_cross_platform.py`
- `test_user_config.py`

They assume anonymous administrator requests; some also expect the storage service at host port `8001` or routes that no longer exist. Several create, download, change, or delete content and settings. Do not run them against an installation containing data you need, disable authentication, or expose service ports to make them pass. Use a disposable environment when updating them to the current API.

`run_all_tests.py` discovers `test_*.py` scripts and runs each with a 60-second timeout. It probes an authenticated backend route without credentials and probes the removed host storage port, so it may skip legacy integration tests even when the application is healthy. It also runs `test_security_stack.py` without `--run`, which validates configuration only, and does not run frontend checks. A successful runner summary is therefore not evidence that all application workflows passed.
