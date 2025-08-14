# 🐳 Docker Setup Guide - Virtual Energy Trading Platform

## Prerequisites
- Docker Desktop installed and running
- Docker Compose installed (comes with Docker Desktop)
- At least 4GB of free RAM allocated to Docker

## 📋 Step-by-Step Instructions

### Step 1: Clone or Navigate to Project
```bash
cd C:\Users\navee\Projects\Virtual-Energy-Trading
```

### Step 2: Create Docker Environment File
Create a `.env.docker` file in the root directory with the following content:

```env
# Backend Configuration
DATABASE_URL=sqlite:///./data/trading.db
DEFAULT_NODE=PJM_RTO
MARKET_TIMEZONE=America/New_York
ORDER_CUTOFF_HOUR=11
MAX_ORDERS_PER_HOUR=10
DEBUG=True
LOG_LEVEL=INFO

# Frontend Configuration
VITE_API_URL=http://localhost:8000

# Docker Configuration
COMPOSE_PROJECT_NAME=energy-trader
```

### Step 3: Build Docker Images
```bash
# Build both backend and frontend images
docker-compose build

# Or build individually
docker-compose build backend
docker-compose build frontend
```

### Step 4: Initialize Database and Generate Mock Data
```bash
# Run database initialization
docker-compose run --rm backend python scripts/init_db.py

# Generate mock market data for today
docker-compose run --rm backend python scripts/fetch_prices.py --node PJM_RTO --date $(date +%Y-%m-%d) --mock --da --rt
```

### Step 5: Start the Application
```bash
# Start both services in detached mode
docker-compose up -d

# Or start with logs visible
docker-compose up
```

### Step 6: Verify Services are Running
```bash
# Check container status
docker-compose ps

# Check backend logs
docker-compose logs backend

# Check frontend logs
docker-compose logs frontend
```

### Step 7: Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Common Docker Commands

### Starting and Stopping
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (careful - this deletes data!)
docker-compose down -v

# Restart a specific service
docker-compose restart backend
docker-compose restart frontend
```

### Viewing Logs
```bash
# View all logs
docker-compose logs

# View backend logs (follow mode)
docker-compose logs -f backend

# View frontend logs (follow mode)
docker-compose logs -f frontend

# View last 100 lines
docker-compose logs --tail=100
```

### Executing Commands in Containers
```bash
# Access backend shell
docker-compose exec backend bash

# Access frontend shell
docker-compose exec frontend sh

# Run Python commands in backend
docker-compose exec backend python scripts/fetch_prices.py --help

# Check database
docker-compose exec backend python -c "from app.database import check_database_health; print(check_database_health())"
```

### Database Operations
```bash
# Initialize/Reset database
docker-compose exec backend python scripts/init_db.py

# Generate mock data for specific date
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date 2025-01-15 --mock --da --rt

# Access SQLite database directly
docker-compose exec backend sqlite3 data/trading.db
```

## 🚀 Quick Start Script

For convenience, here's a one-line command to set everything up:

```bash
# Windows PowerShell
docker-compose down -v; docker-compose build; docker-compose run --rm backend sh -c "python scripts/init_db.py && python scripts/fetch_prices.py --node PJM_RTO --date $(Get-Date -Format yyyy-MM-dd) --mock --da --rt"; docker-compose up -d

# Linux/Mac/Git Bash
docker-compose down -v && docker-compose build && docker-compose run --rm backend sh -c "python scripts/init_db.py && python scripts/fetch_prices.py --node PJM_RTO --date $(date +%Y-%m-%d) --mock --da --rt" && docker-compose up -d
```

## 🧪 Testing the Application

### 1. Test Backend Health
```bash
curl http://localhost:8000/health
```

### 2. Test Market Data API
```bash
# Get Day-Ahead prices
curl "http://localhost:8000/api/market/da?date=2025-01-15&node=PJM_RTO"

# Get Real-Time prices
curl "http://localhost:8000/api/market/rt?start=2025-01-15T00:00:00Z&end=2025-01-15T01:00:00Z&node=PJM_RTO"
```

### 3. Create a Test Order
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "market": "day-ahead",
    "node": "PJM_RTO",
    "hour_start": "2025-01-16T14:00:00Z",
    "side": "buy",
    "limit_price": 50.0,
    "quantity_mwh": 2.0
  }'
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using the ports
netstat -an | findstr :8000
netstat -an | findstr :5173

# Or use different ports in docker-compose.yml
# Change "8000:8000" to "8001:8000" for backend
# Change "5173:5173" to "5174:5173" for frontend
```

### Container Won't Start
```bash
# Check logs for errors
docker-compose logs backend
docker-compose logs frontend

# Rebuild without cache
docker-compose build --no-cache

# Remove everything and start fresh
docker-compose down -v
docker system prune -a
docker-compose up --build
```

### Database Issues
```bash
# Reset database
docker-compose exec backend rm -f data/trading.db
docker-compose exec backend python scripts/init_db.py
```

### Frontend Can't Connect to Backend
```bash
# Ensure backend is running
docker-compose ps

# Check backend is accessible
curl http://localhost:8000/health

# Verify VITE_API_URL in frontend container
docker-compose exec frontend printenv | grep VITE_API_URL
```

## 📊 Monitoring Performance

```bash
# Check resource usage
docker stats

# Check container details
docker-compose ps
docker inspect energy-trader-backend
docker inspect energy-trader-frontend
```

## 🔄 Development Workflow

The Docker setup includes hot-reloading for both frontend and backend:

1. **Backend Changes**: Python files are automatically reloaded
2. **Frontend Changes**: Vite dev server automatically refreshes

To see changes immediately:
```bash
# Watch backend logs
docker-compose logs -f backend

# Watch frontend logs
docker-compose logs -f frontend
```

## 🛑 Stopping Everything

```bash
# Stop containers but keep data
docker-compose down

# Stop containers and remove data volumes
docker-compose down -v

# Complete cleanup (remove images too)
docker-compose down -v --rmi all
```

## 📝 Notes

- Data is persisted in Docker volumes (`backend_data` and `backend_logs`)
- Source code is mounted for hot-reloading during development
- The frontend runs on port 5173, backend on port 8000
- Database is SQLite stored in `/app/data/trading.db` inside the backend container

## 🎯 Success Indicators

You'll know everything is working when:
1. ✅ Both containers show as "Up" in `docker-compose ps`
2. ✅ http://localhost:5173 shows the frontend
3. ✅ http://localhost:8000/docs shows the API documentation
4. ✅ No error messages in `docker-compose logs`
5. ✅ You can create orders and see market data in the UI
