# Recruiter Brief: BabylonPiles

## One-minute summary

BabylonPiles is a Docker-first offline knowledge server that combines a FastAPI backend, React frontend, storage service, mirroring service, Kiwix/ZIM support, and modular content sources. It demonstrates full-stack engineering, backend API design, DevOps/containerization, storage workflows, and product thinking around resilient access to information.

## What it demonstrates

- Backend engineering with FastAPI services, async APIs, SQLAlchemy models, JWT auth, and service-to-service clients.
- Frontend engineering with React, TypeScript, Tailwind, dashboard views, file browsing, upload flows, and system/status pages.
- DevOps and platform work with Docker Compose, multiple services, persistent volumes, internal networking, and Kiwix integration.
- Data/storage design with pile metadata, file allocation, drive scanning, migrations, mirroring jobs, and content update logs.
- Product design for offline-first use cases: classrooms, remote teams, emergency kits, field work, and local network knowledge access.

## Architecture at a glance

```text
React frontend
  -> FastAPI backend
  -> SQLite/SQLAlchemy metadata
  -> Storage service for drive/file allocation
  -> Mirrorer service for scheduled external dataset syncs
  -> Kiwix service for ZIM browsing
  -> Docker volumes for persistent content
```

Important files:

- `docker-compose.yml` - multi-service local deployment.
- `backend/main.py` - FastAPI application entry point.
- `backend/app/api/v1/endpoints/` - API surface for piles, storage, system, updates, and mirrors.
- `backend/app/core/` - database, scheduler, storage, mirroring, and mode-management logic.
- `frontend/src/` - React UI.
- `storage/storage_service.py` - drive scanning, allocation, chunk tracking, and migration APIs.
- `mirrorer/app.py` - internal mirror-run API and log access.

## How to verify locally

```bash
git clone --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker-compose up --build -d
```

Open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`
- Kiwix service: `http://localhost:8081`

## Role positioning

Best aligned roles:

- Backend Developer
- Full Stack Developer
- Software Engineer
- DevOps / Platform Engineer
- Python Developer
- React Frontend Developer

Suggested portfolio phrasing:

> Built a Dockerized offline knowledge platform with FastAPI, React, storage services, content mirroring, scheduled update jobs, local-network access, and Kiwix/ZIM browsing.

## Responsible claims

Present this as an offline-first knowledge infrastructure prototype. Avoid implying that emergency, medical, or survival content is validated by the software itself; the project focuses on storage, access, mirroring, and management workflows.
