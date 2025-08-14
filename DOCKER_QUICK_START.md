# 🐳 Docker Quick Start Guide

## Step-by-Step Instructions to Run with Docker

### 1️⃣ Prerequisites
Make sure you have:
- ✅ Docker Desktop installed
- ✅ Docker Desktop is running (check system tray)

### 2️⃣ Open Terminal/Command Prompt
Navigate to project directory:
```bash
cd C:\Users\navee\Projects\Virtual-Energy-Trading
```

### 3️⃣ Run the Setup Script

#### Option A: Use the automated script (Recommended)

**Windows (Command Prompt or PowerShell):**
```bash
docker-start.bat
```

**Linux/Mac/Git Bash:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

#### Option B: Manual commands

If the scripts don't work, run these commands one by one:

```bash
# 1. Stop any existing containers
docker-compose down -v

# 2. Build the images
docker-compose build

# 3. Initialize the database
docker-compose run --rm backend python scripts/init_db.py

# 4. Generate mock data (Windows)
docker-compose run --rm backend python scripts/fetch_prices.py --node PJM_RTO --date 2025-01-15 --mock --da --rt

# 5. Start the application
docker-compose up -d
```

### 4️⃣ Wait for Services to Start
The application needs about 10-30 seconds to fully start. You can check the status:

```bash
docker-compose ps
```

You should see:
```
NAME                        STATUS              PORTS
energy-trader-backend       Up                  0.0.0.0:8000->8000/tcp
energy-trader-frontend      Up                  0.0.0.0:5173->5173/tcp
```

### 5️⃣ Access the Application

Open your web browser and go to:
- 🌐 **Application**: http://localhost:5173
- 📡 **API Docs**: http://localhost:8000/docs

### 6️⃣ Test the Application

1. **Dashboard**: View current market prices
2. **Orders Page**: Create a test order
   - Select "Day-Ahead" market
   - Choose tomorrow's date and any hour
   - Set Buy/Sell, price, and quantity
   - Submit order
3. **View Orders**: See your order in the table
4. **Match Orders**: Click "Match Day" button
5. **View P&L**: Click "Simulate Day" to see profit/loss

### 7️⃣ Troubleshooting

#### If you see "Docker is not running":
1. Open Docker Desktop application
2. Wait for it to start (whale icon in system tray)
3. Try the script again

#### If ports are already in use:
```bash
# Check what's using the ports
netstat -an | findstr :8000
netstat -an | findstr :5173

# Force stop everything
docker-compose down
docker stop $(docker ps -q)
```

#### If build fails:
```bash
# Clean rebuild
docker-compose build --no-cache
```

#### To view logs if something isn't working:
```bash
# View all logs
docker-compose logs

# View backend logs only
docker-compose logs backend

# View frontend logs only
docker-compose logs frontend
```

### 8️⃣ Stopping the Application

When you're done:
```bash
docker-compose down
```

To completely remove everything (including data):
```bash
docker-compose down -v
```

## 📊 Quick Test Commands

Once running, you can test the API:

```bash
# Check if backend is healthy
curl http://localhost:8000/health

# Get market prices
curl "http://localhost:8000/api/market/da?date=2025-01-15&node=PJM_RTO"
```

## 🎯 Success Checklist

✅ Docker Desktop is running  
✅ Both containers show "Up" status  
✅ Frontend loads at http://localhost:5173  
✅ API docs load at http://localhost:8000/docs  
✅ No error messages in logs  
✅ Can create and view orders  

## 💡 Tips

- The first build might take 2-5 minutes
- Data persists between restarts (unless you use `-v` flag)
- Frontend changes auto-reload
- Backend changes auto-reload
- Check Docker Desktop for resource usage

## 🆘 Need Help?

If you encounter issues:
1. Check Docker Desktop is running
2. Run `docker-compose logs` to see errors
3. Try `docker-compose down -v` and start fresh
4. Ensure ports 8000 and 5173 are free
