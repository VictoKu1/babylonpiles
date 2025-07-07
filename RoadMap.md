# BabylonPiles Roadmap

BabylonPiles is now a Docker-only, cross-platform, modular offline knowledge server. All development and deployment are focused on Docker Compose and web/API-first features.

---

## ✅ Completed
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
- Drag-and-drop file move and parent folder navigation in the file browser
- Backend move API for files/folders
- Kiwix-Serve integration for .ZIM files
- Docker volume-based storage for optimal performance
- Access script for easy data management (cross-platform)
- Optimized Docker builds with reduced image sizes and faster startup
- Performance optimizations (disabled SMART checks, reduced background scanning)

---

## 🛠️ In Progress / Planned
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
- UI polish for drag-and-drop (visual cues, accessibility)
- Multi-select and batch file operations
- Undo/redo for file moves
- Enhanced access script with backup/restore functionality
- Volume migration tools for moving data between systems
- Storage analytics and usage reporting

---

> All future development will focus on Docker-based deployment and features accessible via the web UI and API. Native/manual/OS-specific installation is no longer supported.
