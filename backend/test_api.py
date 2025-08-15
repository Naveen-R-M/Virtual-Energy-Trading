#!/usr/bin/env python3
"""
API Testing Script for PJM Watchlist Features
Tests all new endpoints to ensure they work correctly
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, params=None):
    """Test a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, params=params)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code < 400:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, f"Request error: {str(e)}"

def run_pjm_api_tests():
    """Run comprehensive API tests for PJM features"""
    
    print("🧪 PJM API Testing Suite")
    print("=" * 50)
    
    tests = []
    
    # Test 1: Health check
    print("\n1. Testing system status...")
    success, result = test_endpoint("GET", "/api/pjm/status")
    tests.append(("PJM Status", success, result))
    
    if success:
        print(f"✅ System operational - {result.get('statistics', {}).get('total_nodes', 0)} nodes")
    else:
        print(f"❌ Status check failed: {result}")
    
    # Test 2: Get nodes
    print("\n2. Testing node discovery...")
    success, result = test_endpoint("GET", "/api/pjm/nodes", params={"limit": 10})
    tests.append(("Get Nodes", success, result))
    
    if success:
        nodes = result.get('nodes', [])
        print(f"✅ Found {len(nodes)} nodes")
        if nodes:
            print(f"   Sample: {nodes[0].get('ticker_symbol')} - {nodes[0].get('node_name')}")
    else:
        print(f"❌ Node discovery failed: {result}")
    
    # Test 3: Get empty watchlist
    print("\n3. Testing empty watchlist...")
    success, result = test_endpoint("GET", "/api/pjm/watchlist")
    tests.append(("Empty Watchlist", success, result))
    
    if success:
        watchlist = result.get('watchlist', [])
        print(f"✅ Watchlist loaded - {len(watchlist)} items")
    else:
        print(f"❌ Watchlist failed: {result}")
    
    # Test 4: Add to watchlist (if we have nodes)
    if tests[1][1]:  # If get nodes succeeded
        print("\n4. Testing add to watchlist...")
        add_data = {
            "node_id": 1,  # Assuming first sample node has ID 1
            "custom_name": "Test Node",
            "is_favorite": True
        }
        success, result = test_endpoint("POST", "/api/pjm/watchlist", data=add_data)
        tests.append(("Add to Watchlist", success, result))
        
        if success:
            print(f"✅ Node added to watchlist")
        else:
            print(f"❌ Add to watchlist failed: {result}")
    
    # Test 5: Get populated watchlist
    print("\n5. Testing populated watchlist...")
    success, result = test_endpoint("GET", "/api/pjm/watchlist")
    tests.append(("Populated Watchlist", success, result))
    
    if success:
        watchlist = result.get('watchlist', [])
        print(f"✅ Watchlist now has {len(watchlist)} items")
        if watchlist:
            item = watchlist[0]
            print(f"   Item: {item.get('ticker_symbol')} @ ${item.get('current_price', 0):.2f}")
    else:
        print(f"❌ Populated watchlist failed: {result}")
    
    # Test 6: Create price alert
    print("\n6. Testing price alerts...")
    alert_data = {
        "node_id": 1,
        "alert_type": "above",
        "threshold_value": 50.0,
        "message": "Test alert",
        "is_recurring": False
    }
    success, result = test_endpoint("POST", "/api/pjm/alerts", data=alert_data)
    tests.append(("Create Alert", success, result))
    
    if success:
        print(f"✅ Price alert created")
    else:
        print(f"❌ Price alert failed: {result}")
    
    # Test 7: Get alerts
    print("\n7. Testing get alerts...")
    success, result = test_endpoint("GET", "/api/pjm/alerts")
    tests.append(("Get Alerts", success, result))
    
    if success:
        alerts = result.get('alerts', [])
        print(f"✅ Found {len(alerts)} alerts")
    else:
        print(f"❌ Get alerts failed: {result}")
    
    # Test 8: Chart data
    print("\n8. Testing chart data...")
    success, result = test_endpoint("GET", "/api/pjm/prices/chart/1", params={"hours": 24})
    tests.append(("Chart Data", success, result))
    
    if success:
        rt_prices = result.get('rt_prices', [])
        print(f"✅ Chart data loaded - {len(rt_prices)} price points")
    else:
        print(f"❌ Chart data failed: {result}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, success, _ in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All API tests passed! PJM features are working correctly.")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed. Check the errors above.")
        return False

def test_frontend_connectivity():
    """Test that frontend can reach backend"""
    print("\n🌐 Testing frontend connectivity...")
    
    try:
        # Test CORS and basic connectivity
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Backend is accessible from frontend")
            return True
        else:
            print(f"❌ Backend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure backend is running: uvicorn app.main:app --reload")
        return False

def main():
    """Main test runner"""
    print("⚡ Virtual Energy Trading - API Test Suite")
    print(f"Testing backend at: {BASE_URL}")
    print("=" * 60)
    
    # First check if backend is running
    if not test_frontend_connectivity():
        print("\n🔧 To start the backend:")
        print("   cd backend && uvicorn app.main:app --reload")
        return
    
    # Run the full test suite
    if run_pjm_api_tests():
        print("\n🎯 Ready for frontend testing!")
        print("   1. Start frontend: cd frontend && npm run dev")
        print("   2. Open: http://localhost:5173/watchlist")
        print("   3. Test the Robinhood-style interface!")
    else:
        print("\n🔧 Some APIs need attention. Check the backend logs.")

if __name__ == "__main__":
    main()
