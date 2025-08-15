#!/usr/bin/env python3
"""
Simple startup test for Docker environment
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, '/app')

def test_basic_imports():
    """Test basic imports work"""
    print("Testing basic imports...")
    
    try:
        # Test existing imports
        from app.models import TradingOrder, OrderStatus
        print("✅ Existing models work")
        
        # Test new imports
        from app.models import PJMNode, WatchlistItem, PriceAlert
        print("✅ New PJM models work")
        
        # Test routes
        from app.routes.pjm import router
        print("✅ PJM routes work")
        
        # Test main app
        from app.main import app
        print("✅ Main app works")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    print("\nTesting database...")
    
    try:
        from app.database import init_db, SessionLocal
        
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Test session
        with SessionLocal() as session:
            # Simple query
            from sqlmodel import text
            result = session.exec(text("SELECT 1")).first()
            print(f"✅ Database query works: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pjm_nodes():
    """Test PJM node creation"""
    print("\nTesting PJM nodes...")
    
    try:
        from app.models import insert_sample_pjm_nodes
        from app.database import SessionLocal
        
        with SessionLocal() as session:
            insert_sample_pjm_nodes(session)
        
        print("✅ PJM nodes created")
        
        # Check if they exist
        from app.models import PJMNode
        from sqlmodel import select
        
        with SessionLocal() as session:
            nodes = session.exec(select(PJMNode)).all()
            print(f"✅ Found {len(nodes)} PJM nodes")
            
            if nodes:
                sample = nodes[0]
                print(f"   Sample: {sample.ticker_symbol} - {sample.node_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ PJM nodes failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Quick Docker Integration Test")
    print("=" * 40)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Database", test_database),
        ("PJM Nodes", test_pjm_nodes)
    ]
    
    passed = 0
    
    for name, test_func in tests:
        if test_func():
            passed += 1
        else:
            break  # Stop on first failure
    
    print("\n" + "=" * 40)
    if passed == len(tests):
        print("🎉 All tests passed! Ready to start the API server.")
        print("\n✅ You can now:")
        print("1. Start API: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("2. Test endpoints: python test_api.py") 
        print("3. Start frontend and visit /watchlist")
    else:
        print(f"❌ {passed}/{len(tests)} tests passed")
        print("Check the errors above")

if __name__ == "__main__":
    main()
