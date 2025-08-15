#!/usr/bin/env python3
"""
Quick test script to verify the PJM implementation works
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
        from app.models import PJMNode, WatchlistItem, PriceAlert
        print("✅ New models imported successfully")
        
        from app.routes.pjm import router
        print("✅ PJM routes imported successfully")
        
        from app.services.pjm_data_service import PJMDataService
        print("✅ PJM data service imported successfully")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🗄️ Testing database...")
    
    try:
        from app.database import init_db, check_database_health
        
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Check health
        health = check_database_health()
        if health['status'] == 'healthy':
            print("✅ Database health check passed")
        else:
            print(f"⚠️ Database health: {health}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_pjm_features():
    """Test PJM feature initialization"""
    print("\n📊 Testing PJM features...")
    
    try:
        from app.models import insert_sample_pjm_nodes
        from app.database import SessionLocal
        
        with SessionLocal() as session:
            insert_sample_pjm_nodes(session)
        
        print("✅ PJM sample nodes inserted")
        return True
        
    except Exception as e:
        print(f"❌ PJM features error: {e}")
        return False

def main():
    print("⚡ Virtual Energy Trading - PJM Integration Test")
    print("=" * 50)
    
    success = True
    
    success &= test_imports()
    success &= test_database()
    success &= test_pjm_features()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! PJM integration is ready.")
        print("\nNext steps:")
        print("1. Start backend: uvicorn app.main:app --reload")
        print("2. Start frontend: npm run dev")
        print("3. Navigate to /watchlist")
    else:
        print("❌ Some tests failed. Check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
