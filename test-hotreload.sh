#!/bin/bash
echo "🔥 Testing Hot Reload for Virtual Energy Trader"
echo "=============================================="
echo ""

echo "1️⃣ Checking container status..."
docker ps --filter "name=energy-trader" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2️⃣ Checking if frontend is responding..."
curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend responding at :5173" || echo "❌ Frontend not responding"
curl -s http://localhost:8000/health > /dev/null && echo "✅ Backend responding at :8000" || echo "❌ Backend not responding"
echo ""

echo "3️⃣ Testing file change detection..."
echo "Making a test change to HotReloadTest component..."

# Make a temporary change to test hot reload
sed -i.bak 's/Hot Reload Test Component/🔥 HOT RELOAD WORKING!/g' frontend/src/components/HotReloadTest.tsx

echo "✅ Test change made!"
echo ""
echo "🌐 Check your browser at http://localhost:5173"
echo "   You should see the component title change to '🔥 HOT RELOAD WORKING!'"
echo ""
echo "⏰ Waiting 3 seconds for hot reload..."
sleep 3
echo ""

# Restore original
mv frontend/src/components/HotReloadTest.tsx.bak frontend/src/components/HotReloadTest.tsx 2>/dev/null

echo "🔄 Original text restored"
echo ""
echo "If you saw the text change and then revert, HOT RELOAD IS WORKING! 🎉"
echo ""
echo "📝 Now you can edit any file and see instant changes!"
