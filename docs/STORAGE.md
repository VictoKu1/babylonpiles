# Storage

## Overview

BabylonPiles uses a distributed storage system that can manage multiple drives. Files are automatically chunked and distributed across available drives.

## Configuration

### Default Setup

BabylonPiles uses `./storage/info` in the current directory by default:

```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1
  environment:
    - MAX_DRIVES=1
```

### Add More Drives

Edit `docker-compose.yml` and add your drives:

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

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Management

### Web Interface

Access storage management at http://localhost:3000 → Storage

### API Endpoints

- **Status**: `GET /api/v1/storage/status`
- **Drives**: `GET /api/v1/storage/drives`
- **Scan**: `POST /api/v1/storage/drives/scan`

### Logs

```bash
docker-compose logs storage
```

## Troubleshooting

- **Drives not detected**: Check mount paths and permissions
- **MAX_DRIVES mismatch**: Ensure it matches the number of volume mounts
- **Permission errors**: Ensure Docker has access to the drives 