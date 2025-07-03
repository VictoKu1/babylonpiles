# Installation Guide (Docker-Only)

BabylonPiles is now **Docker-only**. The only supported way to run the app is with Docker Compose. All previous OS-specific instructions have been removed for simplicity and reliability.

---

## Prerequisites

- Docker (with Docker Compose support)

---

## 1. Clone the repository

```bash
git clone https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

---

## 2. Start with Docker Compose

```bash
docker-compose up --build -d
```

---

## 3. Access the app

- Backend API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Frontend: http://localhost:3000

---

## 4. Stopping and restarting

```bash
docker-compose down  # Stop everything
docker-compose restart  # Restart services
docker-compose logs -f  # View logs
```

---

## Troubleshooting

- **Docker not found**: Install Docker from [docker.com](https://www.docker.com/products/docker-desktop/).
- **Port already in use**: Make sure nothing else is running on ports 8080 (backend) or 3000 (frontend).
- **File permission issues**: Use `sudo` if needed, or ensure your user is in the `docker` group.
- **Frontend not loading**: Wait a minute for the frontend to build, then refresh http://localhost:3000.
- **Backend not loading**: Check logs with `docker-compose logs -f`.

---

## FAQ

**Q: Can I run BabylonPiles without Docker?**
A: No. Docker Compose is now the only supported way to run BabylonPiles. This ensures a consistent, cross-platform experience.

**Q: How do I update the app?**
A: Pull the latest code and re-run `docker-compose up --build -d`.

---

For more details, see the [README.md](../README.md) or [API documentation](API.md). 