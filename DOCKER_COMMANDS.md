# 🐳 Virtual Energy Trading - Docker Setup Commands

Your platform is ready to run! Here are the exact commands to use:

## 🚀 Quick Start

### Option 1: Use the Start Script (Easiest)
```bash
# Windows
start.bat

# macOS/Linux
chmod +x start.sh
./start.sh
```

### Option 2: Manual Commands

```bash
# Navigate to project directory
cd C:\Users\navee\Projects\Virtual-Energy-Trading

# Build and start all services
docker compose up -d --build

# Check if containers are running
docker compose ps

# View logs (optional)
docker compose logs -f
```

## 🌐 Access Your Platform

Once running, access your Virtual Energy Trading platform:

- **🖥️ Frontend UI**: http://localhost:5173
- **🌐 Backend API**: http://localhost:8000  
- **📚 API Documentation**: http://localhost:8000/docs

## 🗄️ Initialize Database (First Time Only)

After the containers are running:

```bash
# Initialize the database
docker compose exec backend python scripts/init_db.py

# Load sample market data
docker compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock
```

## 🛠️ Essential Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d --build` | Start all services in background |
| `docker compose down` | Stop all services |
| `docker compose ps` | Check service status |
| `docker compose logs -f` | View live logs |
| `docker compose restart` | Restart all services |
| `docker compose logs backend` | View backend logs only |
| `docker compose logs frontend` | View frontend logs only |

## 🔧 Debugging Commands

```bash
# Check if containers are healthy
docker compose ps

# View detailed logs
docker compose logs backend
docker compose logs frontend

# Access backend container shell
docker compose exec backend /bin/bash

# Access frontend container shell
docker compose exec frontend /bin/sh

# Rebuild specific service
docker compose build backend
docker compose build frontend
```

## 🚨 If Something Goes Wrong

### Complete Reset
```bash
# Stop everything
docker compose down

# Remove all containers and volumes
docker compose down --volumes --rmi all

# Start fresh
docker compose up -d --build
```

### Port Issues
If ports 5173 or 8000 are in use:

**Windows:**
```cmd
netstat -ano | findstr :5173
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

**macOS/Linux:**
```bash
lsof -ti:5173 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

## ✅ Success Check

After running `docker compose up -d --build`, verify:

1. **Check containers**: `docker compose ps`
2. **Backend health**: Visit http://localhost:8000/health
3. **Frontend**: Visit http://localhost:5173
4. **API docs**: Visit http://localhost:8000/docs

You should see:
- Backend: `{"status": "healthy"}`
- Frontend: React app with Virtual Energy Trader interface
- API Docs: FastAPI interactive documentation

## 🎯 Next Steps

Once everything is running:

1. **Initialize database**: `docker compose exec backend python scripts/init_db.py`
2. **Load sample data**: `docker compose exec backend python scripts/fetch_prices.py --mock`
3. **Start development**: Follow the TodoList.md for feature implementation
4. **Build trading features**: Implement day-ahead orders, real-time matching, P&L calculation

**Happy Virtual Energy Trading!** ⚡💰

---

**Need help?** Check the logs with `docker compose logs -f` or run `docker compose ps` to see container status.
