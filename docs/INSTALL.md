# Installation

## Prerequisites

- Docker (with Docker Compose support)

## Quick Start

### 1. Clone and Start
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker-compose up -d
```

### 2. Access Services
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## Management Commands

```bash
docker-compose down           # Stop services
docker-compose restart        # Restart services
docker-compose logs -f        # View logs
docker-compose up --build -d  # Rebuild and start
```

## Storage Configuration

By default, BabylonPiles uses `./storage/info` in the current directory.

To add more drives, edit `docker-compose.yml`:

**Windows:**
```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1  # Default
    - D:\:/mnt/hdd2
    - E:\:/mnt/hdd3
  environment:
    - MAX_DRIVES=3  # Match number of drives
```

**Linux:**
```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1  # Default
    - /media/hdd1:/mnt/hdd2
    - /mnt/storage:/mnt/hdd3
  environment:
    - MAX_DRIVES=3  # Match number of drives
```

Then restart: `docker-compose down && docker-compose up -d`

## Troubleshooting

- **Port conflicts**: Ensure ports 8080 and 3000 are free
- **Permission issues**: Run Docker as administrator (Windows) or add user to docker group (Linux)
- **Services not starting**: Check logs with `docker-compose logs -f`

---

## FAQ

**Q: Can I run BabylonPiles without Docker?**
A: No. Docker Compose is now the only supported way to run BabylonPiles. This ensures a consistent, cross-platform experience.

**Q: How do I update the app?**
A: Pull the latest code and re-run `docker-compose up --build -d`.

---

For more details, see the [README.md](../README.md), [Storage Guide](STORAGE.md), or [API documentation](API.md). 