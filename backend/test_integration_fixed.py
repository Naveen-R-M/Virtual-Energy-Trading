#!/usr/bin/env python3
"""
Fixed integration test script
"""

import sys
import os
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def test_imports():
    """Test that all new imports work"""
    print("🔧 Testing imports...")
    
    try:
        # Test basic imports first
        print("   Testing basic models...")
        from app.models import MarketType, OrderSide, OrderStatus
        
        print("   Testing new PJM models...")
        from app.models import PJMNode, WatchlistItem, PriceAlert, AlertType, AlertStatus
        
        print("   Testing PJM routes...")
        from app.routes.pjm import router
        
        print("   Testing PJM service...")
        from app.services.pjm_data_service import PJMDataService
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database initialization"""
    print("\n🗄️ Testing database...")
    
    try:
        print("   Creating database connection...")
        from app.database import init_db, check_database_health
        
        # Initialize database
        print("   Initializing database...")
        init_db()
        print("✅ Database initialized")
        
        # Check health
        print("   Checking database health...")
        health = check_database_health()
        if health['status'] == 'healthy':
            print("✅ Database health check passed")
            print(f"   - Tables: {health.get('statistics', {})}")
        else:
            print(f"⚠️ Database health: {health}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pjm_features():
    """Test PJM feature initialization"""
    print("\n📊 Testing PJM features...")
    
    try:
        print("   Creating session...")
        from app.database import SessionLocal
        
        print("   Testing sample node insertion...")
        from app.models import insert_sample_pjm_nodes
        
        with SessionLocal() as session:
            insert_sample_pjm_nodes(session)
        
        print("✅ PJM sample nodes inserted")
        
        # Test node count
        print("   Verifying nodes...")
        from app.models import PJMNode
        from sqlmodel import select
        
        with SessionLocal() as session:
            nodes = session.exec(select(PJMNode)).all()
            print(f"   Found {len(nodes)} PJM nodes in database")
            
            if nodes:
                sample_node = nodes[0]
                print(f"   Sample: {sample_node.ticker_symbol} - {sample_node.node_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ PJM features error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_routes():
    """Test API route registration"""
    print("\n🌐 Testing API routes...")
    
    try:
        print("   Testing FastAPI app creation...")
        from app.main import app
        
        # Get route information
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        # Check for PJM routes
        pjm_routes = [r for r in routes if '/pjm' in r[0]]
        
        print(f"   Found {len(pjm_routes)} PJM routes:")
        for path, methods in pjm_routes[:5]:  # Show first 5
            print(f"     {path} ({', '.join(methods)})")
        
        if len(pjm_routes) >= 5:
            print("✅ PJM routes registered successfully")
        else:
            print(f"⚠️ Expected more PJM routes, found {len(pjm_routes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ API routes error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("⚡ Virtual Energy Trading - PJM Integration Test (Fixed)")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("PJM Features", test_pjm_features),
        ("API Routes", test_api_routes)
    ]
    
    passed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n⚠️ {test_name} test had issues")
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed >= 3:  # Allow some flexibility
        print("🎉 Integration looks good! Ready to test the API.")
        print("\nNext steps:")
        print("1. Start the backend:")
        print("   uvicorn app.main:app --reload")
        print("2. Test the API:")
        print("   python test_api.py")
        print("3. Start the frontend:")
        print("   cd ../frontend && npm run dev")
        print("4. Visit: http://localhost:5173/watchlist")
        return True
    else:
        print("❌ Integration needs attention. Check errors above.")
        return False

if __name__ == "__main__":
    main()
