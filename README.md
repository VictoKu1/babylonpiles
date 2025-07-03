# 🏛️ BabylonPiles

**Your offline, modular, open source vault of civilization's knowledge accessible anywhere, anytime, on any device.**

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

### 2. Start everything with Docker Compose
```bash
docker-compose up --build -d
```

### 3. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000

### 4. Stopping and restarting
```bash
docker-compose down  # Stop everything
docker-compose restart  # Restart services
docker-compose logs -f  # View logs
```

---

## What is BabylonPiles?

BabylonPiles is an open-source, modular, offline-first knowledge server. It lets you store, organize, and serve critical data—from offline Wikipedia and medical guides to books, survival manuals, technical documentation, and more. All features are accessible via a web interface and API, and the system is designed to be cross-platform via Docker.

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
