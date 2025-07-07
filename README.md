# 🏛️ BabylonPiles

**Your offline, modular, open source vault of civilization's knowledge accessible anywhere, anytime, on any device.**

---

## What is BabylonPiles?

BabylonPiles is an open-source, modular, offline-first knowledge server. It lets you store, organize, and serve critical data from offline Wikipedia and medical guides to books, survival manuals, technical documentation, and more. All features are accessible via a web interface and API, and the system is designed to be cross-platform via Docker.

**Key Features:**
- 📚 **Modular content**: Download and update data in categories (encyclopedias, health, tech, books, videos, and more)
- 💡 **Offline-first**: No internet required for access—ideal for emergencies, remote work, or prepping
- 🌐 **Multiple interfaces**: Access via web browser, local network, or Wi-Fi hotspot (if supported by host)
- 🛠️ **Admin control**: Easily add, update, or remove information through a web UI or API
- 🔄 **Auto-updates**: Sync content from trusted sources or repositories
- 👥 **Multi-user**: Share your knowledge base with family, teams, classrooms, or communities
- 🕹️ **Open & extensible**: Build plugins for new content categories or automate your own data fetchers
- 🖱️ **Drag-and-drop file management**: Move files and folders in the web UI with native drag-and-drop
- 📁 **Parent folder navigation**: Move files up a level using the '..' entry in every folder
- 🗂️ **Kiwix-Serve integration**: Serve and browse .ZIM files (offline Wikipedia, etc.) over your network

---

## 🚀 Docker Quick Start

**BabylonPiles is a Docker-only application. The only supported way to run it is with Docker Compose.**

### Prerequisites
- Docker (with Docker Compose support)

### 1. Clone the repository
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

### 2. Storage Management
BabylonPiles uses Docker volumes for storage, which provides:
- **Fast Docker builds** (no large files in build context)
- **Persistent data** (survives container restarts)
- **Easy access** via the provided access script

**Access your data:**
```bash
# Linux/macOS
chmod +x access_storage.sh
./access_storage.sh

# Windows (using Git Bash, WSL, or PowerShell)
# Option 1: Use Git Bash (recommended)
./access_storage.sh

# Option 2: Use PowerShell
docker run --rm -v babylonpiles_piles:/data -v ${PWD}/your_zim_files:/source alpine sh -c "cp /source/*.zim /data/"
```

This script allows you to:
- Copy data between Docker volumes and local directories
- View volume information and sizes
- Open volumes in your file manager

### 3. Adding ZIM Files
To add ZIM files to your BabylonPiles system:

**Option 1: Use the access script (recommended)**
```bash
./access_storage.sh
# Choose option 2 to copy from local directory to Docker volumes
```

**Option 2: Direct volume access**
```bash
# Copy files directly to the Docker volume
docker run --rm -v babylonpiles_piles:/data -v $(pwd)/your_zim_files:/source alpine sh -c "cp /source/*.zim /data/"
```

**Option 3: Through the web interface**
- Upload files via the web UI at http://localhost:3000

### 4. Start everything with Docker Compose
```bash
docker-compose up --build -d
```

### 5. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000
- Kiwix-Serve: http://localhost:8081

### 6. Alternative: Manual Docker commands
```bash
docker-compose up --build -d  # Start everything
docker-compose down           # Stop everything
docker-compose restart        # Restart services
docker-compose logs -f        # View logs
```

---

## System Requirements

- **Docker**
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB+ for system, additional for content
- **Network**: Ethernet or WiFi

---

## Usage Highlights

### File Browser
- Browse, upload, download, and delete files and folders from the web UI
- **Drag and drop** files/folders onto folders or the '..' entry to move them
- '..' entry lets you move items up to the parent folder
- All file operations are reflected instantly in the UI

### Storage Management
- **Docker volume-based storage** for optimal performance
- **Browse storage locations** with file system navigation
- **Storage analysis** with detailed space usage and drive information
- **Easy data access** via provided access script
- **Real-time progress tracking** during data transfers
- **Automatic validation** of storage space requirements

### Quick Add & Pile Management
- Add new content sources (piles) manually or with one click from popular repositories
- Validate URLs before adding
- Download and delete piles with progress tracking

### ZIM File Viewing & Kiwix-Serve
- View .ZIM files (offline Wikipedia, etc.) in-browser or via Kiwix-Serve
- Kiwix-Serve runs in Docker and is accessible at http://localhost:8081/
- Share ZIM content on your local network

### Backend Move API
- Move or rename files/folders via POST `/api/v1/files/move` (used by the frontend drag-and-drop)

---

## Project Status & Roadmap

BabylonPiles is now a Docker-only, cross-platform, modular offline knowledge server. All future development will focus on Docker-based deployment and features accessible via the web UI and API.

### Completed
- Docker Compose as the only supported deployment method
- FastAPI backend with async SQLAlchemy
- React frontend
- JWT authentication
- Modular content sources (Kiwix, HTTP, Torrent)
- System monitoring and metrics
- Mode switching (Learn/Store)
- Pile management (CRUD)
- Content update system
- Security best practices (JWT, password hashing, etc.)
- Docker-only, OS-agnostic documentation
- CONTRIBUTING.md and code style guidelines
- **Drag-and-drop file move and parent folder navigation**
- **Kiwix-Serve integration for .ZIM files**
- **Backend move API**
- **Optimized Docker builds and startup**
- **Docker volume-based storage for fast builds**
- **Access script for easy data management**

### In Progress / Planned
- Streamline Docker images for size and performance
- Automated Docker image builds and releases (CI/CD)
- User roles and permissions
- Content indexing and search
- Admin portal for uploading, updating, deleting modules
- Responsive web interface
- Comprehensive API documentation
- More content sources (Project Gutenberg, OpenStreetMap, Internet Archive)
- Content versioning and rollback
- Content discovery and recommendations
- Automated tests (unit, integration)
- Vulnerability scanning in Docker images
- Community chat (Discord/Matrix)
- More example content piles

See [RoadMap.md](RoadMap.md) and [TODO.md](TODO.md) for details.

---

## Documentation

- [Installation Guide](docs/INSTALL.md) - Complete Docker setup instructions
- [Storage Guide](docs/STORAGE.md) - Comprehensive storage management guide
- [Project Summary](PROJECT_SUMMARY.md) - Detailed project overview
- [TODO List](TODO.md) - Development roadmap and priorities
- [API Documentation](docs/API.md) - Backend API reference

---

## License

Open source under the [License](LICENSE)

---

## Contributing

**We welcome contributions!**

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and setup instructions.

---

## Troubleshooting

### Slow Docker Startup
If you experience slow startup times with "exporting to image" or "exporting layers" messages:
```bash
# Clean up Docker system (removes unused images, containers, volumes, and build cache)
docker system prune -a --volumes
```

### Build Issues
```bash
# Clean build cache and rebuild
docker system prune -f
docker-compose build --no-cache
```

### Access Storage Data
Use the provided access script to easily manage your data:
- **Linux/macOS**: `./access_storage.sh`
- **Windows**: Use Git Bash, WSL, or PowerShell with Docker commands

For more troubleshooting, see the [Installation Guide](docs/INSTALL.md).

---

> *Build your own library of civilization—offline, open, forever.*

## Quick Start

1. **Install Docker and Docker Compose**
2. **Clone this repository**
3. **Configure storage locations (optional):**
   - Edit `storage/Dockerfile` and `backend/Dockerfile` to set your desired paths
   - Update `docker-compose.yml` volume mappings to match
4. **Add ZIM files to the system**
   - Use the access script: `./access_storage.sh`
   - Or upload via the web interface at http://localhost:3000
   - Or copy directly to Docker volumes using Docker commands
5. **Start the services:**
   ```sh
   docker-compose up --build -d
   ```
6. **Access the UI:**
   - Open [http://localhost:3000](http://localhost:3000) in your browser.


