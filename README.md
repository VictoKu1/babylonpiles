# 🏛️ BabylonPiles

**Your offline, modular, open source vault of civilization's knowledge accessible anywhere, anytime, on any device.**

---

## What is babylonpiles?

**babylonpiles** is an open-source, cross-platform, self-hosted knowledge server inspired by the legendary libraries of history. Designed for **Raspberry Pi + HDD/SSD**, PC, and mobile devices, it lets you store, organize, and serve critical data—from offline Wikipedia and medical guides to books, survival manuals, technical documentation, and more.

**Key Features:**
- 📚 **Modular content**: Download and update data in categories (encyclopedias, health, tech, books, videos, and more)
- 💡 **Offline-first**: No internet required for access—ideal for emergencies, remote work, or prepping
- 🌐 **Multiple interfaces**: Access via Wi-Fi hotspot, Ethernet, USB gadget, or direct web browser
- 🛠️ **Admin control**: Easily add, update, or remove information through a web UI or CLI
- 🔄 **Auto-updates**: Sync content from trusted sources or repositories, with git-like versioning
- 👥 **Multi-user**: Share your knowledge base with family, teams, classrooms, or communities
- 🕹️ **Open & extensible**: Build plugins for new content categories or automate your own data fetchers

---

## Use Cases

- 🏕️ **Disaster & emergency readiness**: Instant access to survival guides, medical references, maps, and more when the grid goes down
- 🌍 **Education everywhere**: Bring a digital library to classrooms, camps, field hospitals, and rural sites—no connection needed
- 🚐 **Travel & expeditions**: Carry a whole library on your Raspberry Pi or external HDD
- 🔒 **Personal knowledge archiving**: Preserve your essential docs, research, and how-tos offline

---

## Quickstart

### On Raspberry Pi (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles

# 2. Run the automated setup script
sudo chmod +x scripts/setup.sh
sudo ./scripts/setup.sh

# 3. Access your vault!
# - Web interface: http://raspberrypi.local:8080
# - WiFi hotspot: Connect to "BabylonPiles" (password: babylonpiles123)
```

### Development Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

---

## Core Concepts

* **Piles** = Modular, category-based content blocks (e.g. Wikipedia, Medical, Survival, Books)
* **Learn Mode** = Internet-connected mode for downloading and updating content
* **Store Mode** = Offline mode with local network sharing and WiFi hotspot
* **Auto-sync** = Admins can pull fresh content or schedule updates from trusted sources (like Wikipedia ZIMs, Project Gutenberg, etc.)
* **Multi-access** = Serve data via local Wi-Fi, direct ethernet, USB gadget mode, or even as a hotspot

---

## Current Status

### ✅ Completed Features
- **Backend API**: Complete FastAPI backend with all core endpoints
- **Database**: SQLAlchemy models with async support
- **Mode Management**: Learn/Store mode switching
- **Content Sources**: Kiwix, HTTP, and Torrent support
- **System Monitoring**: Real-time system metrics
- **Authentication**: JWT-based authentication
- **Setup Scripts**: Automated Raspberry Pi installation
- **Documentation**: Installation and setup guides

### 🔄 In Progress
- **Frontend Development**: React UI components
- **Testing**: Unit and integration tests
- **Advanced Features**: Content indexing and search

### 📋 Next Steps
- Complete responsive web interface
- Add comprehensive testing
- Enhance security features
- Add content discovery
- Create user documentation

---

## Supported Content Sources

| Source | Type | Status | Description |
|--------|------|--------|-------------|
| Kiwix | ZIM files | ✅ Complete | Wikipedia, medical, educational content |
| HTTP/HTTPS | Direct download | ✅ Complete | Any downloadable file |
| BitTorrent | Torrent files | ✅ Basic | Large file downloads |
| Project Gutenberg | Books | 🔄 Planned | Public domain literature |
| OpenStreetMap | Maps | 🔄 Planned | Offline map data |
| Internet Archive | Media | 🔄 Planned | Videos, documents, software |

---

## System Requirements

- **OS**: Linux (Raspberry Pi OS, Ubuntu, Debian)
- **Python**: 3.8+
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB+ for system, additional for content
- **Network**: Ethernet or WiFi

---

## Roadmap

See [RoadMap.md](RoadMap.md) for full milestones and feature plans!

* [x] Initial project bootstrap
* [x] Backend API with FastAPI
* [x] Database models and migrations
* [x] Mode switching (Learn/Store)
* [x] Content source integrations
* [x] System monitoring
* [x] Automated setup scripts
* [ ] Web interface for file/category navigation
* [ ] Admin portal for uploading, updating, deleting modules
* [ ] Multi-platform support (PC, Mac, Linux)
* [ ] Advanced user roles & permissions

---

## Documentation

- [Installation Guide](docs/INSTALL.md) - Complete setup instructions
- [Project Summary](PROJECT_SUMMARY.md) - Detailed project overview
- [TODO List](TODO.md) - Development roadmap and priorities
- [API Documentation](docs/API.md) - Backend API reference (coming soon)

---

## License

Open source under the [License](LICENSE)

---

## Contributing

**We welcome contributions!**
Please check our [CONTRIBUTING.md](CONTRIBUTING.md) for code style, issue reporting, and roadmap planning.

---

## Credits & Inspiration

* [Kiwix](https://kiwix.org) for ZIM format and offline content delivery
* [Syncthing](https://syncthing.net) for sync ideas
* [Nextcloud](https://nextcloud.com), [RACHEL](https://rachelfriends.org), [Internet-in-a-Box](https://internet-in-a-box.org)
* The prepping, humanitarian, open-education, and FOSS communities

---

## Contact & Community

* [GitHub Issues](https://github.com/VictoKu1/babylonpiles/issues)
* Discussions tab coming soon!
* Interested in collaborating? Open a PR or join our Discord/Matrix (link soon).

---

> *Build your own library of civilization—offline, open, forever.*
