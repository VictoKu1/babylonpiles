# 🏛️ BabylonPiles

**Your offline, modular, open source vault of civilization's knowledge accessible anywhere, anytime, on any device.**

---

## �� Docker Quick Start

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

## What is babylonpiles?

**babylonpiles** is an open-source, cross-platform, self-hosted knowledge server inspired by the legendary libraries of history. It lets you store, organize, and serve critical data—from offline Wikipedia and medical guides to books, survival manuals, technical documentation, and more.

**Key Features:**
- 📚 **Modular content**: Download and update data in categories (encyclopedias, health, tech, books, videos, and more)
- 💡 **Offline-first**: No internet required for access—ideal for emergencies, remote work, or prepping
- 🌐 **Multiple interfaces**: Access via Wi-Fi hotspot, Ethernet, USB gadget, or direct web browser
- 🛠️ **Admin control**: Easily add, update, or remove information through a web UI or CLI
- 🔄 **Auto-updates**: Sync content from trusted sources or repositories, with git-like versioning
- 👥 **Multi-user**: Share your knowledge base with family, teams, classrooms, or communities
- 🕹️ **Open & extensible**: Build plugins for new content categories or automate your own data fetchers

---

## System Requirements

- **Docker**
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB+ for system, additional for content
- **Network**: Ethernet or WiFi

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
