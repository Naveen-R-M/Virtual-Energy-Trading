#!/bin/bash
echo "========================================"
echo "Virtual Energy Trading Platform Setup"
echo "========================================"
echo

echo "Checking Docker..."
docker --version
echo

echo "Building and starting services..."
docker compose up -d --build
echo

echo "Waiting for services to start..."
sleep 10
echo

echo "Checking container status..."
docker compose ps
echo

echo "Services should be available at:"
echo "- Frontend: http://localhost:5173"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo

echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
echo
