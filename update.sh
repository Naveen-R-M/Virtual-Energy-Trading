#!/bin/bash
echo "🔄 Rebuilding Virtual Energy Trading Platform..."
echo ""

echo "📦 Rebuilding frontend with new dependencies..."
docker-compose build frontend

echo "🚀 Starting updated services..."
docker-compose up -d

echo ""
echo "✅ Update complete! Your platform should be running with the new UI at:"
echo "🖥️ Frontend: http://localhost:5173"
echo "🌐 Backend: http://localhost:8000"
echo ""
echo "If you see any issues, check the logs with:"
echo "docker-compose logs -f"
