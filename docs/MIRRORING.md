# Mirrored Sources

## Overview

BabylonPiles includes an EmergencyStorage-backed mirroring subsystem for large preserved datasets that do not fit the normal pile download flow.

The implementation is split across three layers:

- `vendor/EmergencyStorage` is a pinned Git submodule.
- `mirrorer/` is an internal adapter service that wraps fixed EmergencyStorage commands.
- The backend owns mirror job persistence, scheduling, run history, and log access.

The vendored repo is not used as a general-purpose runtime or scheduler. BabylonPiles remains Docker-first and treats EmergencyStorage as a controlled internal dependency.

## Supported Providers

The current integration supports these fixed provider and variant combinations:

- `openstreetmap / planet`
- `internet_archive / software`
- `internet_archive / music`
- `internet_archive / movies`
- `internet_archive / texts`

Unknown provider or variant combinations are rejected by the backend and the mirrorer adapter.

The current vendored Internet Archive scripts prepare catalogs, collection descriptions, manifests, and download links. They do not download the advertised collection payloads. A successful script exit therefore means preparation completed; it does not establish that books, music, movies, or software are available offline. OpenStreetMap invokes a planet-file download. Check the actual output before relying on a collection, and plan capacity for the selected dataset. The backend's ordinary pile-download size limits do not automatically constrain these shell workflows.

## Storage Layout

Mirrored content is written into the shared piles directory:

- Files: `/mnt/babylonpiles/piles/mirrors/<provider>/<variant>/`
- Logs: `/mnt/babylonpiles/data/mirror_logs/<run_id>.log`

Examples:

- `/mnt/babylonpiles/piles/mirrors/openstreetmap/planet/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/software/`

The underlying EmergencyStorage scripts may create one more nested directory inside the variant directory. For example, the OpenStreetMap script writes into `.../planet/openstreetmap/`.

The default Compose deployment binds host `storage/piles` at `/mnt/babylonpiles/piles` in backend and mirrorer. Browse is rooted at the separate `/mnt/babylonpiles/data` volume, so mirror files do not appear there under the default configuration. They remain accessible in host `storage/piles/mirrors`. Back up that host directory, the `babylonpiles_data` volume containing logs, and the `backend_state` volume containing the job database. See [Storage](STORAGE.md) for layouts selected by the operator helper.

## How To Use

1. Clone the `security` branch with submodules to match the authenticated setup in this guide:

```bash
git clone --branch security --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

2. For an existing clone, initialize or update the pinned submodule:

```bash
git submodule update --init --recursive
```

3. Start the stack:

```bash
docker compose up --build -d --wait
```

4. On a fresh installation, create the first administrator:

```sh
docker compose exec backend python -m app.admin create --username admin
```

Enter a password of at least 12 characters at the hidden prompts. For an existing administrator, use its credentials instead of creating it again. Open `http://localhost:3000`, sign in, go to `Updates`, and use the `Add Mirrored Source` form. Existing installations should follow [Security setup](SECURITY_SETUP.md) before replacing containers. When the operator helper manages storage, replace `docker compose` with `bash ./babylonpiles.sh compose` in this guide so its storage mapping remains applied.

5. Configure:

- provider and variant
- enabled or disabled state
- optional schedule in UTC
- manual `Run Now` execution

Only one job per provider/variant pair can exist. A disabled job cannot run manually, and a running job cannot be edited or started again.

## Scheduling

Mirror jobs use fixed preset scheduling, not free-form cron:

- disabled
- daily at `HH:MM` UTC
- weekly on day `0-6` (Sunday–Saturday) at `HH:MM` UTC
- monthly on day `1-31` at `HH:MM` UTC

New jobs are enabled with scheduling off. Enable scheduling explicitly and select a frequency to run automatically; the default time is `02:00` UTC. If a monthly day does not exist in a particular month, the run falls on that month's last day.

The backend scheduler polls for due jobs every 60 seconds by default. To change this, pass `MIRROR_SCHEDULER_POLL_SECONDS` into the backend container environment in a Compose override; adding it to the host `.env` alone does not pass it through the default Compose file.

Mirror scheduling is independent of Learn/Store mode. Switching to Store mode does not stop scheduled jobs or block their network access in the default deployment.

If the backend restarts while a mirror run is active, the scheduler marks the interrupted run and job as failed on startup and recomputes the next scheduled execution.

## API Surface

Mirror routes live under `/api/v1/mirrors`:

- `GET /api/v1/mirrors/providers`
- `GET /api/v1/mirrors/jobs`
- `POST /api/v1/mirrors/jobs`
- `PUT /api/v1/mirrors/jobs/{job_id}`
- `POST /api/v1/mirrors/jobs/{job_id}/run`
- `GET /api/v1/mirrors/jobs/{job_id}/runs`
- `GET /api/v1/mirrors/runs/{run_id}/logs`

See [API.md](API.md) for the backend route summary.

## Docker Services

The mirroring subsystem adds one internal Compose service:

- `mirrorer`

It is not exposed on a host port by default. The backend talks to it over the internal Docker network using `MIRRORER_URL=http://mirrorer:8002` and the shared service credential. Mirror management and log access require an active administrator.

## Updating The Vendored Submodule

When pulling future changes, keep the pinned submodule in sync:

```bash
git pull
git submodule update --init --recursive
docker compose up --build -d --wait
```

Do not edit `vendor/EmergencyStorage` directly for BabylonPiles-specific behavior. Keep integration glue in BabylonPiles code and Docker files.

## What This Does Not Cover

The current mirroring subsystem does not:

- create normal `Pile` records for mirrored datasets
- expose arbitrary EmergencyStorage features
- use EmergencyStorage's own scheduler or `systemd` setup
- support arbitrary command arguments from the UI
