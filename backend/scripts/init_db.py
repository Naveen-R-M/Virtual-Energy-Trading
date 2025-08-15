#!/usr/bin/env python3
"""
Database initialization script for Virtual Energy Trading Platform.
Creates all necessary tables and initial data for both Day-Ahead and Real-Time markets.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add app directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

def create_database():
    """Create database and tables with enhanced two-market support."""
    try:
        print("🗄️ Initializing database...")
        
        # Import and initialize database
        from app.database import init_db
        init_db()
        
        print("✅ Database initialized successfully!")
        
        # Create data directory for mock data files
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Check database health
        from app.database import check_database_health
        health = check_database_health()
        
        print()
        print("📊 Database Status:")
        print(f"   - Connection: {health['connection']}")
        if 'statistics' in health:
            print(f"   - Grid Nodes: {health['statistics']['grid_nodes']}")
            print(f"   - Trading Orders: {health['statistics']['trading_orders']}")
            print(f"   - DA Prices: {health['statistics']['day_ahead_prices']}")
            print(f"   - RT Prices: {health['statistics']['real_time_prices']}")
        
        print()
        print("🏪 Markets Configured:")
        print("   📅 Day-Ahead: Hourly slots, 11AM cutoff, 10 orders/hour")
        print("   ⚡ Real-Time: 5-min slots, continuous, 50 orders/slot")
        print("   📊 PJM Watchlist: Robinhood-style price tracking")
        
        # Initialize PJM features
        initialize_pjm_features()
        
        print()
        print("✅ Database is ready for trading!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("🔧 Troubleshooting:")
        print("   - Check if all dependencies are installed")
        print("   - Verify Python path and imports")
        print("   - Run from backend directory")
        sys.exit(1)

def initialize_pjm_features():
    """Initialize PJM-specific watchlist features"""
    try:
        print("\n📊 Initializing PJM Watchlist Features...")
        
        from app.models import insert_sample_pjm_nodes
        from app.database import SessionLocal
        
        with SessionLocal() as session:
            insert_sample_pjm_nodes(session)
        
        print("✅ PJM sample nodes created")
        print("   - PJM RTO Hub (PJMRTO)")
        print("   - Western Hub (WEST)")
        print("   - Kearneys 138kV (KNY138KV)")
        
    except Exception as e:
        print(f"⚠️ PJM initialization warning: {e}")
        print("   PJM features may have limited functionality")

def main():
    """Main initialization function."""
    print("⚡ Virtual Energy Trading Platform")
    print("=====================================")
    print("🗄️ Database Initialization")
    print()
    
    create_database()

if __name__ == "__main__":
    main()
