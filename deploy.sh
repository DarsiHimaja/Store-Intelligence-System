#!/bin/bash

echo "========================================"
echo "Store Intelligence - Quick Deploy"
echo "========================================"
echo ""

echo "[1/4] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker is installed"

echo ""
echo "[2/4] Building containers..."
if ! docker compose build; then
    echo "ERROR: Build failed"
    exit 1
fi
echo "✓ Build complete"

echo ""
echo "[3/4] Starting services..."
if ! docker compose up -d; then
    echo "ERROR: Failed to start services"
    exit 1
fi
echo "✓ Services started"

echo ""
echo "[4/4] Waiting for services to be ready..."
sleep 5

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "Dashboard:         http://localhost:8501"
echo ""
echo "To load sample data, run:"
echo "  docker compose exec api python load_events.py"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To stop services:"
echo "  docker compose down"
echo ""
