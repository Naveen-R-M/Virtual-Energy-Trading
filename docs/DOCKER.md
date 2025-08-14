# 🐳 Docker Quick Start Guide

**No installation needed!** Just Docker and you're ready to go.

## Prerequisites

Only **Docker Desktop** is required:
- **Windows**: [Download Docker Desktop](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
- **macOS**: [Download Docker Desktop](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
- **Linux**: [Install Docker Engine](https://docs.docker.com/engine/install/)

## 🚀 Quick Start Commands

### Production Mode (Recommended)
```bash
cd C:\Users\navee\Projects\Virtual-Energy-Trading

# Build and start all services
docker-compose up -d --build

# Initialize database
docker-compose exec backend python scripts/init_db.py

# Load sample data
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock
```

**Access your platform:**
- 🖥️ **Frontend**: http://localhost
- 🌐 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

### Development Mode (with hot reloading)
```bash
cd C:\Users\navee\Projects\Virtual-Energy-Trading

# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Initialize database
docker-compose exec backend python scripts/init_db.py

# Load sample data
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock
```

**Access your platform:**
- 🖥️ **Frontend**: http://localhost:5173 (with hot reloading)
- 🌐 **Backend API**: http://localhost:8000 (with hot reloading)
- 📚 **API Docs**: http://localhost:8000/docs

---

## 📋 Essential Commands

### Starting Services
```bash
# Production mode
docker-compose up -d --build

# Development mode (hot reloading)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Foreground mode (see logs in terminal)
docker-compose up --build
```

### Stopping Services
```bash
# Stop containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (containers, networks, volumes)
docker-compose down --volumes
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100
```

### Container Management
```bash
# Check status
docker-compose ps

# Restart services
docker-compose restart

# Rebuild specific service
docker-compose build backend
docker-compose build frontend
```

---

## 🗄️ Database Management

### Initialize Database
```bash
docker-compose exec backend python scripts/init_db.py
```

### Load Sample Data
```bash
# Load mock data for yesterday
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock

# Load for specific date
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date 2025-08-15 --mock

# Load both DA and RT data
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --da --rt --mock
```

### Reset Database
```bash
# Stop services
docker-compose down

# Remove database volume
docker volume rm virtual-energy-trading_backend_data

# Start and reinitialize
docker-compose up -d --build
docker-compose exec backend python scripts/init_db.py
```

---

## 🧪 Development & Debugging

### Access Container Shells
```bash
# Backend container
docker-compose exec backend /bin/bash

# Frontend container
docker-compose exec frontend /bin/sh
```

### Run Tests
```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

### Check Service Health
```bash
# Backend health check
curl http://localhost:8000/health

# Frontend health check (production)
curl http://localhost/health

# Frontend health check (development)
curl http://localhost:5173
```

---

## 🔧 Configuration

### Environment Variables
Create `.env` file in project root:
```bash
# Copy from template
cp .env.docker .env

# Edit with your settings
GRIDSTATUS_API_KEY=your_api_key_here
COMPOSE_PROJECT_NAME=energy-trader
```

### Custom Ports
Edit `docker-compose.yml` to change ports:
```yaml
services:
  frontend:
    ports:
      - "3000:80"  # Change from 80 to 3000
  backend:
    ports:
      - "8001:8000"  # Change from 8000 to 8001
```

---

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Find and kill process using port
netstat -ano | findstr :8000  # Windows
lsof -ti:8000 | xargs kill -9  # macOS/Linux

# Or change ports in docker-compose.yml
```

### Container Won't Start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild from scratch
docker-compose down --rmi all
docker-compose up --build
```

### Permission Issues (Linux/macOS)
```bash
# Run with sudo
sudo docker-compose up -d

# Or add user to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

### Database Connection Issues
```bash
# Check if backend is running
docker-compose ps

# Check backend logs
docker-compose logs backend

# Reset database
docker-compose down --volumes
docker-compose up -d --build
```

### Clean Slate Reset
```bash
# Nuclear option - removes everything
docker-compose down --volumes --rmi all
docker system prune -af
docker volume prune -f

# Then start fresh
docker-compose up -d --build
```

---

## 📊 Service Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │
│   (React)       │◄──►│   (FastAPI)     │
│   Port: 80/5173 │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │    Database     │
                       │    (SQLite)     │
                       │   in Volume     │
                       └─────────────────┘
```

---

## ✅ Complete Setup Example

Here's the complete sequence to get everything running:

```bash
# Navigate to project
cd C:\Users\navee\Projects\Virtual-Energy-Trading

# Start services (choose production OR development)

# PRODUCTION:
docker-compose up -d --build

# OR DEVELOPMENT:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Wait for services to start (30-60 seconds)
docker-compose ps

# Initialize database
docker-compose exec backend python scripts/init_db.py

# Load sample data
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock

# Verify everything is working
curl http://localhost:8000/health
```

**Success!** Your platform is now running. Visit:
- **Frontend**: http://localhost (production) or http://localhost:5173 (development)
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🎉 You're Ready!

Your Virtual Energy Trading platform is running in Docker containers with:
- ✅ FastAPI backend with health checks
- ✅ React frontend with Arco Design
- ✅ SQLite database with persistence
- ✅ Mock data for testing
- ✅ Hot reloading (in development mode)

**Next Steps:**
1. Explore the API at http://localhost:8000/docs
2. Check out the UI at http://localhost
3. Follow TodoList.md to implement trading features
4. Start building your energy trading algorithms!

**Happy Trading!** ⚡💰
