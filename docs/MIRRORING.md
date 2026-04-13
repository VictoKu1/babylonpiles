# Mirrored Sources

## Overview

BabylonPiles includes an EmergencyStorage-backed mirroring subsystem for large preserved datasets that do not fit the normal pile download flow.

The implementation is split across three layers:
- `vendor/EmergencyStorage` is a pinned Git submodule.
- `mirrorer/` is an internal adapter service that wraps fixed EmergencyStorage commands.
- The backend owns mirror job persistence, scheduling, run history, and log access.

The vendored repo is not used as a general-purpose runtime or scheduler. BabylonPiles remains Docker-first and treats EmergencyStorage as a controlled internal dependency.

## Supported Providers

Version 1 supports these fixed provider and variant combinations:
- `openstreetmap / planet`
- `internet_archive / software`
- `internet_archive / music`
- `internet_archive / movies`
- `internet_archive / texts`

Unknown provider or variant combinations are rejected by the backend and the mirrorer adapter.

## Storage Layout

Mirrored content is written into the shared piles volume so it is immediately visible in the existing file browser:
- Files: `/mnt/babylonpiles/piles/mirrors/<provider>/<variant>/`
- Logs: `/mnt/babylonpiles/data/mirror_logs/<run_id>.log`

Examples:
- `/mnt/babylonpiles/piles/mirrors/openstreetmap/planet/`
- `/mnt/babylonpiles/piles/mirrors/internet_archive/software/`

The underlying EmergencyStorage scripts may create one more nested directory inside the variant directory. For example, the OpenStreetMap script writes into `.../planet/openstreetmap/`.

## How To Use

1. Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

2. If you already cloned the repo before mirrored sources were added, initialize the submodule:

```bash
git submodule update --init --recursive
```

3. Start the stack:

```bash
docker-compose up --build -d
```

4. Open the frontend at `http://localhost:3000`, go to `Updates`, and use the `Add Mirrored Source` form.

5. Configure:
- provider and variant
- enabled or disabled state
- optional schedule in UTC
- manual `Run Now` execution

## Scheduling

Mirror jobs use fixed preset scheduling, not free-form cron:
- disabled
- daily at `HH:MM` UTC
- weekly on day `0-6` at `HH:MM` UTC
- monthly on day `1-31` at `HH:MM` UTC

The backend scheduler polls for due jobs every `MIRROR_SCHEDULER_POLL_SECONDS` seconds. The default is `60`.

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

It is not exposed on a host port by default. The backend talks to it over the internal Docker network using `MIRRORER_URL=http://mirrorer:8002`.

## Updating The Vendored Submodule

When pulling future changes, keep the pinned submodule in sync:

```bash
git pull
git submodule update --init --recursive
docker-compose up --build -d
```

Do not edit `vendor/EmergencyStorage` directly for BabylonPiles-specific behavior. Keep integration glue in BabylonPiles code and Docker files.

## What This Does Not Cover

The current mirroring subsystem does not:
- create normal `Pile` records for mirrored datasets
- expose arbitrary EmergencyStorage features
- use EmergencyStorage's own scheduler or `systemd` setup
- support arbitrary command arguments from the UI
