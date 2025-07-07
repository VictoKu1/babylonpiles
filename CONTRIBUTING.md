# 🤝 Contributing to BabylonPiles

Thank you for your interest in contributing! We welcome all contributions—code, documentation, bug reports, and feature requests.

## 🚀 Quick Start for Contributors (Docker-Only)

The only supported way to develop and test BabylonPiles is with Docker. This ensures your environment matches production and other contributors.

### 1. Prerequisites
- Docker (with Docker Compose support)

### 2. Clone the repository
```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

### 3. Storage Management
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

### 4. Start the development environment
```bash
docker-compose up --build -d
```

### 5. Access the app
- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000
- Kiwix-Serve: http://localhost:8081

### 6. Making changes
- Edit code in your local repo as usual.
- Docker volumes ensure your changes are reflected in the running containers.
- Use `docker-compose restart` to restart services if needed.

### 7. Running tests
- (Add test instructions here if available)

### 8. Troubleshooting
If you experience slow startup times:
```bash
# Clean up Docker system (removes unused images, containers, volumes, and build cache)
docker system prune -a --volumes
```

---

## Code Style & Guidelines
- Follow PEP8 for Python code.
- Use clear, descriptive commit messages.
- Write docstrings and comments for complex logic.
- Use Prettier/ESLint for frontend code (if configured).

## Submitting Pull Requests
- Fork the repo and create your branch from `main`.
- Ensure your code builds and passes tests in Docker.
- Test with the access script to ensure data management works correctly.

## Reporting Issues
- Use [GitHub Issues](https://github.com/VictoKu1/babylonpiles/issues) for bugs, feature requests, and questions.

## Community
- Join discussions in the Discussions tab or (coming soon) Discord/Matrix.

---

Thank you for helping make BabylonPiles better!

## How Can I Contribute?

**Here are some great ways to help:**

- 🐛 **Report Bugs:** If you spot a bug or something broken, [open an Issue](https://github.com/VictoKu1/babylonpiles/issues).
- ✨ **Suggest Features:** Have an idea to make babylonpiles more powerful or useful? Suggest it in [Discussions](https://github.com/VictoKu1/babylonpiles/discussions) or as a feature request Issue.
- 💻 **Code Contributions:** Submit bugfixes, improvements, new features, or plugins via Pull Request (PR).
- 📝 **Improve Documentation:** Better docs, guides, or translations are always appreciated.
- 🌍 **Localization:** Help translate the UI or documentation.

## Development Areas

**Current focus areas for contributions:**
- **Frontend improvements**: React UI components and user experience
- **Storage system**: Docker volume management and access script
- **Performance optimization**: Docker builds and startup times
- **Testing**: Unit and integration tests
- **Documentation**: API docs, user guides, and examples

## Need Help?

- [Open an Issue](https://github.com/VictoKu1/babylonpiles/issues)
- Join our (coming soon) chat/Discord/Matrix
- Email the maintainers (see README)

---

Thank you for helping build the offline library of civilization!  
**The Babylonpiles Maintainers**
