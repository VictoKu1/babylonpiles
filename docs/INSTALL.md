# Installation Guide

## Prerequisites

- Docker (with Docker Compose support)

## Quick Start

### 1. Clone and Start
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
docker-compose up --build -d
```

### 2. Access Services
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Kiwix-Serve**: http://localhost:8081

## Management Commands

```bash
docker-compose down           # Stop services
docker-compose restart        # Restart services
docker-compose logs -f        # View logs
docker-compose up --build -d  # Rebuild and start
```

## Storage Configuration

### Docker Volumes

BabylonPiles uses Docker volumes for optimal performance:

- **`babylonpiles_data`**: Backend data (SQLite database, logs, etc.)
- **`babylonpiles_piles`**: ZIM files and other pile content
- **`babylonpiles_storage`**: Storage service data and metadata
- **`babylonpiles_service_data`**: Storage service internal data

### Data Access

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

### Adding ZIM Files

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

## Performance Optimizations

The system includes several performance optimizations:

- **Docker volumes**: Fast access without bind mount overhead
- **Optimized Docker builds** with reduced image sizes
- **Faster startup** with disabled SMART checks by default
- **Reduced background scanning** (every 5 minutes)
- **Better health checks** with reasonable timeouts

### Environment Variables

```yaml
environment:
  - ENABLE_SMART_CHECKS=false      # Disable SMART checks for faster startup
  - BACKGROUND_SCAN_INTERVAL=300   # Scan every 5 minutes
  - MAX_DRIVES=1                   # Number of storage drives
  - CHUNK_SIZE=104857600           # 100MB chunk size
```

## Troubleshooting

### Port Conflicts
- Ensure ports 8080, 3000, and 8081 are free
- Check for other services using these ports

### Permission Issues
- **Windows**: Run Docker Desktop as administrator
- **Linux**: Add your user to the docker group: `sudo usermod -aG docker $USER`

### Services Not Starting
- Check logs: `docker-compose logs -f`
- Verify Docker has enough resources (2GB RAM minimum)
- Ensure Docker has permission to create volumes

### Slow Startup
- Clean Docker system: `docker system prune -a --volumes`
- Ensure `ENABLE_SMART_CHECKS=false` is set
- Check Docker has enough resources (2GB RAM minimum)

### Build Issues
- Clean Docker cache: `docker system prune -f`
- Rebuild from scratch: `docker-compose build --no-cache`

### "Exporting to Image" Messages
If you see slow startup with "exporting to image" or "exporting layers" messages:
```bash
# Clean up Docker system (removes unused images, containers, volumes, and build cache)
docker system prune -a --volumes
```

---

## FAQ

**Q: Can I run BabylonPiles without Docker?**
A: No. Docker Compose is the only supported way to run BabylonPiles. This ensures a consistent, cross-platform experience.

**Q: How do I update the app?**
A: Pull the latest code and re-run `docker-compose up --build -d`.

**Q: Where are my files stored?**
A: All files are stored in Docker volumes. Use the access script (`access_storage.sh`) to easily manage your data.

**Q: How do I add ZIM files?**
A: Use the access script to copy files from your local directory to the Docker volumes, or upload directly through the web interface.

**Q: How do I backup my data?**
A: Use the access script to copy data from Docker volumes to local directories, or use Docker volume backup commands.

**Q: How do I access data on Windows?**
A: Use Git Bash to run the access script, or use PowerShell with Docker commands directly.

---

For more details, see the [README.md](../README.md), [Storage Guide](STORAGE.md), or [API documentation](API.md). 