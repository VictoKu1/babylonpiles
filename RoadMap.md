# BabylonPiles Roadmap

BabylonPiles is now a Docker-only, cross-platform, modular offline knowledge server. All development and deployment are focused on Docker Compose and web/API-first features.

---

## ✅ Completed

### Core Infrastructure
- Docker Compose as the only supported deployment method
- FastAPI backend with async SQLAlchemy
- React frontend with TypeScript
- JWT authentication and security
- Docker-only, OS-agnostic documentation

### Content Management
- Modular content sources (Kiwix, HTTP, Torrent)
- Pile management (CRUD operations)
- Content update system with progress tracking
- Kiwix-Serve integration for .ZIM files
- Content validation and error handling

### File Management
- Drag-and-drop file move and parent folder navigation
- Backend move API for files/folders
- Seamless drag and drop file uploads from desktop to browser
- Visual upload feedback with progress indicators
- File permission management with public/private toggles
- Enhanced error handling and user notifications

### Storage & Analytics
- Multi-location storage allocation during startup
- Storage analysis with detailed space usage
- Connect/disconnect drives functionality
- Safe reallocation with data migration
- Accurate dashboard storage metrics (content vs system storage)
- Real-time storage updates after file operations

### System Management
- System monitoring and metrics
- Mode switching (Learn/Store)
- CPU, memory, and disk usage monitoring
- System health tracking
- Performance optimization

### User Experience
- Custom notification system replacing browser alerts
- Visual feedback for all operations
- Error recovery and retry mechanisms
- Responsive design and accessibility
- Real-time progress tracking

### Testing & Quality
- Comprehensive test suite organization
- Automated test runner with cross-platform support
- Test categories: API, System, and Functionality tests
- Detailed test documentation and execution guide
- Error handling and validation testing

### Documentation
- CONTRIBUTING.md and code style guidelines
- Comprehensive API documentation
- Storage management guides
- Installation and setup instructions
- Troubleshooting guides

## Recent Features

- Manual repository entry from the frontend (Quick Add): Users can now add custom repositories, which are stored in sources.json via the backend. If no Info URL is provided, the system adapts and hides the info button for those sources.

---

## 🛠️ In Progress / Planned

### Performance & Optimization
- Streamline Docker images for size and performance
- Automated Docker image builds and releases (CI/CD)
- Performance optimization for large file operations
- Memory usage optimization
- Startup time improvements

### User Management & Security
- User roles and permissions system
- Advanced authentication options
- Security auditing and logging
- Vulnerability scanning in Docker images
- Multi-user support with isolation

### Content & Discovery
- Content indexing and search functionality
- Content discovery and recommendations
- Content versioning and rollback
- More content sources (Project Gutenberg, OpenStreetMap, Internet Archive)
- Content categorization and tagging

### Admin & Management
- Admin portal for uploading, updating, deleting modules
- Advanced storage analytics and reporting
- System configuration management
- Backup and restore functionality
- Monitoring and alerting system

### User Interface
- Responsive web interface improvements
- Advanced file management features
- Multi-select and batch file operations
- Undo/redo for file moves
- Enhanced drag-and-drop with visual cues
- Accessibility improvements

### Development & Testing
- Automated tests (unit, integration, end-to-end)
- UI component testing
- Performance testing suite
- Security testing framework
- Continuous integration pipeline

### Community & Ecosystem
- Community chat (Discord/Matrix)
- Plugin system for custom content sources
- API client libraries
- More example content piles
- Community documentation and guides

### Advanced Features
- WebSocket support for real-time updates
- Advanced search and filtering
- Content compression and optimization
- Offline synchronization
- Mobile app support

---

## 🎯 Development Priorities

### High Priority
1. **Performance Optimization**: Improve startup times and resource usage
2. **User Management**: Implement proper user roles and permissions
3. **Content Search**: Add indexing and search functionality
4. **Security Hardening**: Implement comprehensive security measures

### Medium Priority
1. **UI/UX Improvements**: Enhanced drag-and-drop and visual feedback
2. **Testing Infrastructure**: Comprehensive automated testing
3. **Documentation**: Expand guides and tutorials
4. **Community Features**: Chat and collaboration tools

### Low Priority
1. **Mobile Support**: Native mobile applications
2. **Advanced Analytics**: Detailed usage and performance metrics
3. **Plugin System**: Extensible architecture for custom features
4. **Cloud Integration**: Optional cloud backup and sync

---

## 🚀 Release Strategy

### Version 1.0 (Current)
- ✅ Core functionality complete
- ✅ File management and storage
- ✅ Basic user interface
- ✅ Docker deployment

### Version 1.1 (Next)
- 🔄 Performance optimizations
- 🔄 Enhanced user experience
- 🔄 Improved testing coverage
- 🔄 Better documentation

### Version 1.2 (Future)
- 🔄 User management system
- 🔄 Content search and discovery
- 🔄 Advanced admin features
- 🔄 Community features

### Version 2.0 (Long-term)
- 🔄 Plugin architecture
- 🔄 Mobile applications
- 🔄 Cloud integration
- 🔄 Advanced analytics

---

> All future development will focus on Docker-based deployment and features accessible via the web UI and API. Native/manual/OS-specific installation is no longer supported.
