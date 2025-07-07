# Storage Management

## Overview

BabylonPiles uses Docker volumes for storage, which provides optimal performance and easy data management. All data is stored in Docker volumes that persist across container restarts and can be easily accessed using the provided access script.

## Storage Architecture

### Docker Volumes

BabylonPiles uses four main Docker volumes:

- **`babylonpiles_data`**: Backend data (SQLite database, logs, etc.)
- **`babylonpiles_piles`**: ZIM files and other pile content
- **`babylonpiles_storage`**: Storage service data and metadata
- **`babylonpiles_service_data`**: Storage service internal data

### Volume Configuration

Volumes are defined in `docker-compose.yml`:

```yaml
volumes:
  babylonpiles_data:
    driver: local
  babylonpiles_piles:
    driver: local
  babylonpiles_storage:
    driver: local
  babylonpiles_service_data:
    driver: local
```

### Service Mappings

Each service maps to specific volumes:

```yaml
backend:
  volumes:
    - babylonpiles_data:/mnt/babylonpiles/data
    - babylonpiles_piles:/mnt/babylonpiles/piles

storage:
  volumes:
    - babylonpiles_storage:/mnt/hdd1
    - babylonpiles_service_data:/app/data

kiwix-serve:
  volumes:
    - babylonpiles_piles:/data
```

## Data Access

### Access Script

Use the provided access script to manage your data:

**Linux/macOS:**
```bash
chmod +x access_storage.sh
./access_storage.sh
```

**Windows:**
```bash
# Option 1: Use Git Bash (recommended)
./access_storage.sh

# Option 2: Use PowerShell
docker run --rm -v babylonpiles_piles:/data -v ${PWD}/your_zim_files:/source alpine sh -c "cp /source/*.zim /data/"
```

### Script Features

The access script provides:
- **Volume information**: View volume names, sizes, and mount points
- **Copy data**: Copy files between Docker volumes and local directories
- **Open volumes**: Open volumes in your file manager
- **Backup/restore**: Easy data backup and restoration

### Manual Volume Access

You can also access volumes directly:

```bash
# View volume information
docker volume ls
docker volume inspect babylonpiles_piles

# Copy files to/from volumes
docker run --rm -v babylonpiles_piles:/data -v $(pwd)/local_files:/source alpine sh -c "cp /source/*.zim /data/"

# Browse volume contents
docker run --rm -it -v babylonpiles_piles:/data alpine sh
```

## Adding Content

### ZIM Files

To add ZIM files to your BabylonPiles system:

1. **Use the access script (recommended):**
   ```bash
   ./access_storage.sh
   # Choose option 2 to copy from local directory to Docker volumes
   ```

2. **Direct volume access:**
   ```bash
   docker run --rm -v babylonpiles_piles:/data -v $(pwd)/your_zim_files:/source alpine sh -c "cp /source/*.zim /data/"
   ```

3. **Web interface:**
   - Upload files via the web UI at http://localhost:3000

### Other Content

- **Piles**: Add via the web interface or API
- **Files**: Upload through the file browser
- **Data**: Automatically managed by the backend

## Performance Optimizations

The storage system includes several performance optimizations:

- **Docker volumes**: Fast access without bind mount overhead
- **SMART checks disabled**: Faster startup by default
- **Reduced background scanning**: Every 5 minutes instead of every minute
- **Optimized mount information**: Python-based instead of subprocess calls
- **Timeouts**: Prevent hanging on subprocess calls

### Environment Variables

```yaml
environment:
  - ENABLE_SMART_CHECKS=false      # Disable SMART checks for faster startup
  - BACKGROUND_SCAN_INTERVAL=300   # Scan every 5 minutes
  - MAX_DRIVES=1                   # Number of storage drives
  - CHUNK_SIZE=104857600           # 100MB chunk size
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

## Backup and Migration

### Backup Data

```bash
# Backup all volumes
docker run --rm -v babylonpiles_data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/data_backup.tar.gz -C /data .
docker run --rm -v babylonpiles_piles:/data -v $(pwd)/backup:/backup alpine tar czf /backup/piles_backup.tar.gz -C /data .
```

### Restore Data

```bash
# Restore from backup
docker run --rm -v babylonpiles_data:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/data_backup.tar.gz -C /data
docker run --rm -v babylonpiles_piles:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/piles_backup.tar.gz -C /data
```

### Volume Migration

To move volumes to a different location:

1. **Stop services:**
   ```bash
   docker-compose down
   ```

2. **Export volumes:**
   ```bash
   docker run --rm -v babylonpiles_piles:/data alpine tar czf - -C /data . > piles_backup.tar.gz
   ```

3. **Create new volumes and restore:**
   ```bash
   docker volume create babylonpiles_piles_new
   docker run --rm -v babylonpiles_piles_new:/data -v $(pwd):/backup alpine tar xzf /backup/piles_backup.tar.gz -C /data
   ```

4. **Update docker-compose.yml** to use the new volume names

## Troubleshooting

### Slow Startup
- Ensure `ENABLE_SMART_CHECKS=false` is set
- Clean Docker system: `docker system prune -a --volumes`
- Check Docker has enough resources (2GB RAM minimum)

### Volume Not Found
- Check volume exists: `docker volume ls`
- Recreate if needed: `docker volume create babylonpiles_piles`
- Verify volume mappings in `docker-compose.yml`

### Permission Errors
- Ensure Docker has access to create and manage volumes
- On Windows, run Docker Desktop as administrator if needed
- On Linux, add your user to the docker group

### Data Loss Prevention
- **Always backup before major changes**
- **Use the access script** for safe data operations
- **Test volume operations** on non-critical data first
- **Keep backups** of important content

### Performance Issues
- Monitor volume usage: `docker system df`
- Clean unused volumes: `docker volume prune`
- Check available disk space on the Docker host 