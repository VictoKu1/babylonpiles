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

### 2. Place your ZIM files (and other pile files) in the `./storage/piles` directory
- This directory is shared between the backend, kiwix-serve, and the UI.
- Any `.zim` file you want to serve or view must be placed here.

### 3. Start everything with the unified script
**Linux/macOS:**
```bash
./babylonpiles.sh
```

**Windows:**
```cmd
babylonpiles.bat
```

```powershell
.\babylonpiles.bat
```


The script provides an interactive menu for:
- Starting/stopping services
- **Multi-location storage allocation** during startup
- Managing storage drives
- Viewing logs
- System status

### 4. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000

### 5. Alternative: Manual Docker commands
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
- **Multi-location storage allocation** during system startup
- **Browse storage locations** with file system navigation
- **Storage analysis** with detailed space usage and drive information
- **Connect/Disconnect drives** to add or remove storage from the system
- **Reallocate storage** with data migration between drives
- **Real-time progress tracking** during data transfers
- **Automatic validation** of storage space requirements
- **Safe reallocation** that prevents data loss during transfers

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
- [Storage Guide](docs/STORAGE.md) - Comprehensive storage management guide including multi-location allocation
- [Project Summary](PROJECT_SUMMARY.md) - Detailed project overview
- [TODO List](TODO.md) - Development roadmap and priorities
- [API Documentation](docs/API.md) - Backend API reference

---

## License

Open source under the [License](LICENSE)

---

## Contributing

**We welcome contributions!**
Please check our [CONTRIBUTING.md](CONTRIBUTING.md) for Docker-based development instructions.

---

> *Build your own library of civilization—offline, open, forever.*

## Quick Start

1. **Install Docker and Docker Compose**
2. **Clone this repository**
3. **Place your ZIM files (and other pile files) in the `./storage/piles` directory**
   - This directory is shared between the backend, kiwix-serve, and the UI.
   - Any `.zim` file you want to serve or view must be placed here.
4. **Start the services:**
   ```sh
   docker-compose up -d
   ```
5. **Access the UI:**
   - Open [http://localhost:3000](http://localhost:3000) in your browser.
6. **Browse, download, and view ZIM files**
   - Use the UI to browse files in `./storage/piles`.
   - To view a ZIM file with Kiwix, use the "Open ZIM" action in the UI.

## Adding Content
- To add new ZIM files, simply copy them into the `./storage/piles` directory.
- The backend and Kiwix-Serve will automatically detect new files after a restart.
- To remove content, delete the file from `./storage/piles` and restart the services if needed.

## Troubleshooting
- If a ZIM file does not appear in the UI or is not served by Kiwix:
  1. Make sure it is in the `./storage/piles` directory.
  2. Restart the services:
     ```sh
     docker-compose down
     docker-compose up -d
     ```
- If you see connection errors on `localhost:8081`, ensure at least one `.zim` file is present in `./storage/piles`.

## Directory Structure
- `./storage/piles` — Place all your ZIM and pile files here.
- This directory is shared by all relevant services via Docker Compose.

## No More Docker Volumes for Piles
- The system now uses a host directory for piles, making file management easy from your OS.

---
For more details, see the comments in `docker-compose.yml`.

## Storage Configuration

BabylonPiles uses `./storage/info` in the current directory by default.

### Default Configuration
```yaml
storage:
  volumes:
    - ./storage/info:/mnt/hdd1  # Default location
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

## Management Commands

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### View Storage Logs
```bash
docker-compose logs storage
```

### Rebuild Services
```bash
docker-compose up --build -d
```

## Troubleshooting

### Check Service Health
```bash
docker-compose ps
```

### View Recent Logs
```bash
docker-compose logs --tail=50
```

### Check Storage Status
```bash
curl http://localhost:8001/status
```

### Verify Storage Setup
- Web interface: http://localhost:3000 → Storage
- API docs: http://localhost:8080/docs
- Logs: `docker-compose logs storage`

### Reset Everything
```bash
docker-compose down -v
docker-compose up --build -d
```
