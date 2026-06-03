@echo off
echo ========================================
echo Store Intelligence - Quick Deploy
echo ========================================
echo.

echo [1/4] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✓ Docker is installed

echo.
echo [2/4] Building containers...
docker compose build
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
echo ✓ Build complete

echo.
echo [3/4] Starting services...
docker compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start services
    pause
    exit /b 1
)
echo ✓ Services started

echo.
echo [4/4] Waiting for services to be ready...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo API Documentation: http://localhost:8000/docs
echo Dashboard:         http://localhost:8501
echo.
echo To load sample data, run:
echo   docker compose exec api python load_events.py
echo.
echo To view logs:
echo   docker compose logs -f
echo.
echo To stop services:
echo   docker compose down
echo.
pause
