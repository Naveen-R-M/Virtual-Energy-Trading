#!/usr/bin/env python3
"""
Diagnostic script to identify import issues
"""

import sys
import traceback

def test_imports():
    """Test imports step by step to identify the issue"""
    
    print("🔍 Testing imports step by step...")
    
    try:
        print("1. Testing basic imports...")
        from sqlmodel import SQLModel
        print("   ✅ SQLModel imported")
        
        from datetime import datetime
        print("   ✅ datetime imported")
        
        from typing import Optional, List, Dict
        print("   ✅ typing imported")
        
    except Exception as e:
        print(f"   ❌ Basic imports failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("2. Testing models...")
        from app.models import MarketType, OrderSide, OrderStatus
        print("   ✅ Basic enums imported")
        
        from app.models import TradingOrder, DayAheadPrice, RealTimePrice
        print("   ✅ Basic models imported")
        
    except Exception as e:
        print(f"   ❌ Basic models failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("3. Testing new enums...")
        from app.models import SessionState
        print("   ✅ SessionState imported")
        
        # from app.models import OrderType, TimeInForce
        # print("   ✅ OrderType and TimeInForce imported")
        
    except Exception as e:
        print(f"   ❌ New enums failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("4. Testing new models...")
        from app.models import UserCapital, TradingSession
        print("   ✅ Session models imported")
        
    except Exception as e:
        print(f"   ❌ Session models failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("5. Testing helper functions...")
        from app.models import calculate_session_state
        print("   ✅ Helper functions imported")
        
    except Exception as e:
        print(f"   ❌ Helper functions failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("6. Testing services...")
        from app.services.matching_engine import MatchingEngine
        print("   ✅ MatchingEngine imported")
        
        from app.services.deterministic_matching import DeterministicMatchingService
        print("   ✅ DeterministicMatchingService imported")
        
    except Exception as e:
        print(f"   ❌ Services failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("7. Testing routes...")
        from app.routes.market import router as market_router
        print("   ✅ Market routes imported")
        
        from app.routes.orders import router as orders_router
        print("   ✅ Orders routes imported")
        
    except Exception as e:
        print(f"   ❌ Routes failed: {e}")
        traceback.print_exc()
        return
    
    try:
        print("8. Testing main app...")
        from app.main import app
        print("   ✅ Main app imported")
        
    except Exception as e:
        print(f"   ❌ Main app failed: {e}")
        traceback.print_exc()
        return
    
    print("\n🎉 All imports successful!")

if __name__ == "__main__":
    test_imports()
