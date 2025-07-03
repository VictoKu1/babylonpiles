@echo off
echo 🐳 Starting BabylonPiles with Docker...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Stop any existing containers
echo 🛑 Stopping any existing containers...
docker-compose down

REM Build and start the services
echo 🔨 Building and starting services...
docker-compose up --build -d

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service status...
docker-compose ps

REM Show logs
echo 📋 Recent logs:
docker-compose logs --tail=20

echo.
echo ✅ BabylonPiles is now running!
echo 🌐 Backend API: http://localhost:8080
echo 📚 API Documentation: http://localhost:8080/docs
echo 🎨 Frontend: http://localhost:3000
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo To restart: docker-compose restart
pause 