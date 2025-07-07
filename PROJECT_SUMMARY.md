# BabylonPiles Project Summary

BabylonPiles is a modular, offline-first, open-source knowledge server for Raspberry Pi, PC, and more. It lets you store, organize, and serve critical data—encyclopedias, books, guides, and more—anywhere, anytime.

---

## 🚀 Docker Quick Start (Docker-Only)

**BabylonPiles is a Docker-only application. The only supported way to run it is with Docker Compose.**

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, Mac, Linux)

### 1. Clone the repository
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

### 2. Storage Management
BabylonPiles uses Docker volumes for optimal performance:
- **Fast Docker builds** (no large files in build context)
- **Persistent data** (survives container restarts)
- **Easy access** via provided access script

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

### 3. Start everything with Docker Compose
```bash
docker-compose up --build -d
```

### 4. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000
- Kiwix-Serve: http://localhost:8081

---

## What is BabylonPiles?

- **Offline-first**: No internet required for access
- **Modular**: Download and update data in categories (encyclopedias, health, tech, books, videos, and more)
- **Multi-access**: Serve data via Wi-Fi, Ethernet, USB gadget, or direct web browser
- **Admin control**: Add, update, or remove information through a web UI or CLI
- **Auto-updates**: Sync content from trusted sources or repositories
- **Multi-user**: Share your knowledge base with family, teams, classrooms, or communities
- **Open & extensible**: Build plugins for new content categories or automate your own data fetchers

---

## Key Features
- FastAPI backend with async SQLAlchemy
- React frontend
- JWT authentication
- Kiwix, HTTP, and Torrent content sources
- System monitoring and metrics
- Docker-first deployment
- Mode switching (Learn/Store)
- Environment-based configuration
- Comprehensive logging and monitoring
- **Docker volume-based storage** for optimal performance
- **Access script** for easy data management
- **Drag-and-drop file management** in web UI

## 📁 Project Structure

```
babylonpiles/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # REST API endpoints
│   │   ├── core/              # Core system components
│   │   ├── models/            # Database models
│   │   ├── modules/           # Content source modules
│   │   └── schemas/           # Pydantic schemas
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React frontend
│   ├── src/                  # React components
│   ├── package.json          # Node.js dependencies
│   └── index.html           # Main HTML file
├── storage/                   # Storage service
│   ├── storage_service.py    # Storage management service
│   └── Dockerfile           # Storage service container
├── access_storage.sh         # Data access script
├── docs/                      # Documentation
│   ├── INSTALL.md           # Installation guide
│   ├── STORAGE.md           # Storage management guide
│   └── API.md               # API documentation
├── TODO.md                   # Development roadmap
└── README.md                 # Project overview
```

## 🚀 Current Status

### ✅ Completed Features
1. **Backend API**: Complete REST API with all core endpoints
2. **Database**: SQLAlchemy models with async support
3. **Mode Management**: Learn/Store mode switching
4. **Content Sources**: Kiwix, HTTP, and Torrent support
5. **System Monitoring**: Real-time system metrics
6. **Authentication**: JWT-based authentication
7. **Docker-first deployment**
8. **Docker volume-based storage** for optimal performance
9. **Access script** for easy data management
10. **Drag-and-drop file management** in web UI
11. **Kiwix-Serve integration** for .ZIM files

---

## Storage System

BabylonPiles uses Docker volumes for storage, which provides:
- **Fast access** without bind mount overhead
- **Persistent data** across container restarts
- **Easy management** via access script

### Volume Structure
- `babylonpiles_data`: Backend data (SQLite database, logs)
- `babylonpiles_piles`: ZIM files and other pile content
- `babylonpiles_storage`: Storage service data and metadata
- `babylonpiles_service_data`: Storage service internal data

### Data Access
Use the provided access script to manage your data:
- **Linux/macOS**: `./access_storage.sh`
- **Windows**: Use Git Bash, WSL, or PowerShell with Docker commands

---

## System Integration

- **Docker volumes**: Automatic volume management and persistence
- **Network Configuration**: WiFi hotspot and DHCP server setup (if supported by host, not managed by BabylonPiles)

---

## Roadmap
- [ ] Complete responsive web interface
- [ ] Admin portal for uploading, updating, deleting modules
- [ ] Multi-platform support (PC, Mac, Linux)
- [ ] Advanced user roles & permissions
- [ ] Content discovery and search

---

## Contributing

**We welcome contributions!**
- See [CONTRIBUTING.md](CONTRIBUTING.md) for Docker-based development instructions.
- Use Docker for development and testing for best results.

---

## License

Open source under the [License](LICENSE)

## 🏗️ What Has Been Built

**BabylonPiles** is now a fully scaffolded, modular offline knowledge NAS system with the following components:

### ✅ Backend (Python FastAPI)
- **Complete API structure** with FastAPI framework
- **Database models** for Piles, Users, UpdateLogs, and SystemStatus
- **Mode management** system for Learn/Store mode switching
- **Content updater** with support for multiple sources (Kiwix, HTTP, Torrent)
- **System monitoring** with real-time metrics collection
- **Authentication system** with JWT tokens
- **Version control** with backup/restore functionality

### ✅ Core Features Implemented
- **Learn Mode**: Internet-connected mode for content updates
- **Store Mode**: Offline mode with local network sharing
- **Content Management**: CRUD operations for knowledge piles
- **Update System**: Automated content downloading with progress tracking
- **System Monitoring**: CPU, memory, storage, and network monitoring
- **Network Management**: WiFi hotspot and network configuration

### ✅ Data Source Support
- **Kiwix Integration**: Wikipedia ZIM files and other Kiwix content
- **HTTP Downloads**: Direct file downloads from URLs
- **Torrent Support**: BitTorrent protocol for large files
- **Local Files**: Manual file upload and management

### ✅ Setup & Deployment
- **Docker Compose**: Complete containerized deployment
- **Mode Switch Script**: Command-line mode switching
- **Configuration Management**: Environment-based configuration
- **Logging System**: Comprehensive logging and monitoring

## 📁 Project Structure

```
babylonpiles/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # REST API endpoints
│   │   ├── core/              # Core system components
│   │   ├── models/            # Database models
│   │   ├── modules/           # Content source modules
│   │   └── schemas/           # Pydantic schemas
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React frontend
│   ├── src/                  # React components
│   ├── package.json          # Node.js dependencies
│   └── index.html           # Main HTML file
├── storage/                   # Storage service
│   ├── storage_service.py    # Storage management service
│   └── Dockerfile           # Storage service container
├── access_storage.sh         # Data access script
├── docs/                      # Documentation
│   ├── INSTALL.md           # Installation guide
│   ├── STORAGE.md           # Storage management guide
│   └── API.md               # API documentation
├── TODO.md                   # Development roadmap
└── README.md                 # Project overview
```

## 🚀 Current Status

### ✅ Completed Features
1. **Backend API**: Complete REST API with all core endpoints
2. **Database**: SQLAlchemy models with async support
3. **Mode Management**: Learn/Store mode switching
4. **Content Sources**: Kiwix, HTTP, and Torrent support
5. **System Monitoring**: Real-time system metrics
6. **Authentication**: JWT-based authentication
7. **Docker-first deployment**
8. **Docker volume-based storage** for optimal performance
9. **Access script** for easy data management
10. **Drag-and-drop file management** in web UI
11. **Kiwix-Serve integration** for .ZIM files

### 🔄 In Progress
1. **Frontend Development**: React UI components
2. **Testing**: Unit and integration tests
3. **Advanced Features**: Content indexing and search

### 📋 Next Steps
1. **Complete Frontend**: Build responsive web interface
2. **Add Testing**: Comprehensive test coverage
3. **Enhance Security**: Proper password hashing and HTTPS
4. **Content Discovery**: Automatic content source discovery
5. **User Documentation**: Complete user manual

## 🎯 Key Capabilities

### Learn Mode (Internet Sync)
- Downloads content from Kiwix, HTTP, and torrent sources
- Automatic version control and backup
- Progress tracking and error handling
- Scheduled updates support

### Store Mode (Offline Sharing)
- WiFi hotspot for local network access
- Offline content serving
- Local network file sharing
- USB gadget mode support

### Content Management
- Modular "piles" system for organizing content
- Support for Wikipedia, books, maps, videos, and more
- Version control with rollback capability
- Content verification and integrity checking

### System Features
- Real-time system monitoring
- Automatic HDD/SSD detection and mounting
- Network configuration and management
- Comprehensive logging and diagnostics

## 🔧 Technical Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Async Support**: Full async/await throughout
- **Content Sources**: Kiwix, HTTP, BitTorrent

### Frontend (Planned)
- **Framework**: React with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Query
- **UI Components**: Modern, responsive design

### Infrastructure
- **Platform**: Raspberry Pi (primary), Linux, Windows, macOS
- **Network**: WiFi hotspot, Ethernet, USB gadget
- **Storage**: External HDD/SSD with auto-mount
- **Service**: Systemd for process management

## 📊 Supported Content Sources

| Source            | Type            | Status     | Description                             |
| ----------------- | --------------- | ---------- | --------------------------------------- |
| Kiwix             | ZIM files       | ✅ Complete | Wikipedia, medical, educational content |
| HTTP/HTTPS        | Direct download | ✅ Complete | Any downloadable file                   |
| BitTorrent        | Torrent files   | ✅ Basic    | Large file downloads                    |
| Project Gutenberg | Books           | 🔄 Planned  | Public domain literature                |
| OpenStreetMap     | Maps            | 🔄 Planned  | Offline map data                        |
| Internet Archive  | Media           | 🔄 Planned  | Videos, documents, software             |

## 🎉 Success Metrics

### Core Functionality ✅
- [x] System can switch between Learn and Store modes
- [x] Content can be downloaded and managed
- [x] Basic authentication system works
- [x] System monitoring and metrics collection
- [x] Automated installation process
- [x] Network configuration and management

### Next Milestones 🎯
- [ ] Complete web interface
- [ ] Add comprehensive testing
- [ ] Implement advanced security features
- [ ] Create user documentation
- [ ] Add content discovery features

## 🚀 Getting Started

### Quick Start (Raspberry Pi)
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
sudo chmod +x scripts/setup.sh
sudo ./scripts/setup.sh
```

### Development Setup
```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## 📈 Project Impact

**BabylonPiles** addresses critical needs for:
- **Offline Education**: Bringing knowledge to areas without internet
- **Emergency Preparedness**: Reliable access to critical information
- **Digital Preservation**: Long-term storage of important content
- **Community Sharing**: Local knowledge networks
- **Sustainable Technology**: Low-power, long-lasting solutions

The system is designed to be **user-friendly**, **reliable**, and **extensible**, making it suitable for both technical and non-technical users in various environments.

## 🔮 Future Vision

BabylonPiles aims to become the **de facto standard** for offline knowledge management, supporting:
- **Global Deployment**: Multi-language and cultural adaptation
- **Community Networks**: Peer-to-peer content sharing
- **Advanced AI**: Content indexing and intelligent search
- **Mobile Integration**: Smartphone and tablet support
- **Cloud Integration**: Hybrid online/offline workflows

This project represents a significant step toward **democratizing access to knowledge** and building **resilient information infrastructure** for communities worldwide. 