# BabylonPiles project summary

BabylonPiles is an offline knowledge-server prototype: a React frontend, FastAPI backend, storage service, mirroring adapter, and Kiwix reader. It stores and serves information selected by its operator. It does not validate the medical, emergency, or other substantive accuracy of imported content.

## Run it

Docker Compose v2 with Linux containers is the supported application runtime. These instructions use the `security` branch; the default `main` branch does not yet include its administrator setup.

```sh
git clone --branch security --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker compose up --build -d --wait
docker compose exec backend python -m app.admin create --username admin
```

Choose and confirm a password of at least 12 characters at the hidden prompts, then sign in at [localhost:3000](http://localhost:3000). There is no default account. Existing deployments should read [Security setup and upgrades](docs/SECURITY_SETUP.md) before recreating containers.

The optional Unix `babylonpiles.sh` helper manages Compose and additional host storage. It preserves a separate storage mapping; deployments using it must run subsequent Compose operations through `bash ./babylonpiles.sh compose ...`. See [Installation](docs/INSTALL.md).

## Components

| Component | Responsibility |
| --- | --- |
| `frontend/src/` | Login, dashboard, file browsing, piles, and update controls |
| `backend/main.py` | FastAPI startup and manager lifecycle |
| `backend/app/api/v1/` | Authenticated management APIs and explicit public-share routes |
| `backend/app/core/` | Database, path/network controls, storage clients, and mirror scheduling |
| `backend/app/modules/` | HTTP, Kiwix, and Gutenberg source adapters and content updates |
| `storage/storage_service.py` | Drive discovery, allocation metadata, and chunk migration |
| `mirrorer/app.py` | Authenticated adapter for the supported vendored source commands |
| `vendor/EmergencyStorage/` | Pinned submodule containing standalone download workflows |
| `scripts/manage_storage.py` | Validated operator storage configuration and rollback |

## Current behavior and limits

- Administrators manage files, sources, piles, mirror jobs, and public shares. There is no automatic first account or public administrator registration.
- Explicit public shares identify the file that was approved. Upload-review requests do not grant write access.
- HTTP/Kiwix/Gutenberg retrieval is bounded and restricted to public network destinations. Direct torrent imports are disabled.
- Mirror schedules use fixed UTC presets and retain run history. Supported provider names do not imply that every upstream archive has been downloaded; consult the mirroring guide for the actual outputs.
- The standalone storage service and backend content stores have separate locations. Adding chunk-storage capacity does not automatically migrate backend files.
- Kiwix is a separate read-only reader bound to the host loopback interface. It does not implement BabylonPiles authorization.
- Host Wi-Fi configuration belongs to the operating system. Docker containers are not granted privileged host access by the supported deployment.
- The dashboard and system page refresh every 30 seconds. Storage capacity describes the backend content filesystem, with limitations for empty roots and separate mounts; it is not the sum of chunk-storage drives.
- Search/indexing, richer user-management UI, and broader content integrations remain development areas. See [Roadmap](RoadMap.md) and [TODO](TODO.md).

## Development

Use Docker for the application environment. Frontend source edits reload from its bind mount; dependency changes also require renewing its anonymous `node_modules` volume. Rebuild and recreate backend/storage/mirrorer images after changing their source. Run backend tests with the image's Python 3.11 environment; see [Contributing](CONTRIBUTING.md) and [tests/README.md](tests/README.md).

Documentation: [Installation](docs/INSTALL.md), [Security setup](docs/SECURITY_SETUP.md), [Storage](docs/STORAGE.md), [Mirroring](docs/MIRRORING.md), and [API reference](docs/API.md).
