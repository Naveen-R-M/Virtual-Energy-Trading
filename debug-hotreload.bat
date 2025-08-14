@echo off
echo 🔧 Hot Reload Troubleshooting for Virtual Energy Trader
echo ==================================================
echo.

echo 1️⃣ Checking container status...
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo 2️⃣ Checking frontend container logs...
docker logs energy-trader-frontend --tail 10
echo.

echo 3️⃣ Testing volume mount...
echo Files in container /app/src:
docker exec energy-trader-frontend ls -la /app/src/
echo.

echo 4️⃣ Frontend process info...
docker exec energy-trader-frontend ps aux
echo.

echo 🔥 If hot reload still doesn't work, try:
echo 1. Edit a file in frontend/src/
echo 2. Check browser console for WebSocket connection errors
echo 3. Try hard refresh (Ctrl+Shift+R)
echo 4. Check if http://localhost:5173 works directly
echo.

echo 📝 Manual restart command if needed:
echo docker-compose restart frontend
echo.
pause
