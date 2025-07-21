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
- 📤 **Seamless file uploads**: Drag files directly from desktop to browser for instant upload
- 📊 **Accurate storage metrics**: Dashboard shows actual content storage vs system disk usage
- 🔐 **Enhanced permissions**: Improved file permission management with better error handling
- 🧪 **Comprehensive testing**: Organized test suite with automated test runner

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

### 2. Manual Docker commands
```bash
docker-compose up --build -d  # Start everything
docker-compose down           # Stop everything
docker-compose restart        # Restart services
docker-compose logs -f        # View logs
```

### 3. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000

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
- **Seamless desktop uploads**: Drag files directly from your desktop to the browser window for instant upload
- '..' entry lets you move items up to the parent folder
- All file operations are reflected instantly in the UI
- **Visual upload feedback** with progress indicators and overlays

### Storage Management
- **Multi-location storage allocation** during system startup
- **Browse storage locations** with file system navigation
- **Storage analysis** with detailed space usage and drive information
- **Connect/Disconnect drives** to add or remove storage from the system
- **Reallocate storage** with data migration between drives
- **Real-time progress tracking** during data transfers
- **Automatic validation** of storage space requirements
- **Safe reallocation** that prevents data loss during transfers

### Dashboard & Analytics
- **Accurate storage metrics**: Dashboard shows actual content storage instead of system disk usage
- **Real-time updates**: Storage information updates immediately after file operations
- **Content vs System storage**: Clear distinction between user content and system storage
- **Visual progress indicators**: Upload and download progress tracking
- **System health monitoring**: CPU, memory, and disk usage monitoring

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

### Testing
- Comprehensive test suite for all functionality
- Run individual tests: `python tests/test_storage_api.py`
- Run all tests: `python tests/run_all_tests.py`
- Test categories: API, System, and Functionality tests
- See [Test Suite Documentation](tests/README.md) for detailed information

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
- **Seamless drag and drop file uploads from desktop**
- **Accurate dashboard storage metrics (content vs system storage)**
- **Enhanced file permission management with improved error handling**
- **Real-time storage updates and visual feedback**
- **Comprehensive test suite organization and documentation**

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
- [Test Suite](tests/README.md) - Comprehensive test documentation and execution guide

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
3. **Enter repository**
4. **Start the services:**
   ```sh
   docker-compose up -d
   ```
5. **Access the UI:**
   - Open [http://localhost:3000](http://localhost:3000) in your browser.

## Quick Add & Custom Content Sources

You can now add custom content repositories directly from the frontend interface using the 'Manual Entry...' option in the repository dropdown. This allows you to:
- Enter a repository name
- Enter a repository URL (required)
- Optionally provide an Info URL for file metadata

If you do not provide an Info URL, file info (the 'i' button) will not be available for files from that source. The backend will store your custom source in `sources.json` automatically.

For API users, you can add or update sources using the `/api/v1/piles/add-source` endpoint. See [API.md](docs/API.md) for details.
