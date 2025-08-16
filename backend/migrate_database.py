#!/usr/bin/env python3
"""
Database migration script to add new columns for enhanced order management
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add new columns to existing database"""
    
    # Connect to the database
    db_path = Path("data/energy_trader.db")
    
    if not db_path.exists():
        print("❌ Database file not found. Creating new database...")
        db_path.parent.mkdir(exist_ok=True)
        # The database will be created by SQLModel when the app starts
        return
    
    print(f"🔧 Migrating database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(trading_orders)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add missing columns if they don't exist
        migrations = [
            ("order_type", "VARCHAR DEFAULT 'LMT'", "Order type (MARKET/LIMIT)"),
            ("time_in_force", "VARCHAR DEFAULT 'GTC'", "Time in force (GTC/IOC/DAY)"), 
            ("expires_at", "DATETIME", "Explicit expiry timestamp")
        ]
        
        for column_name, column_def, description in migrations:
            if column_name not in columns:
                sql = f"ALTER TABLE trading_orders ADD COLUMN {column_name} {column_def}"
                print(f"   ➕ Adding column: {column_name} ({description})")
                cursor.execute(sql)
            else:
                print(f"   ✅ Column exists: {column_name}")
        
        # Commit changes
        conn.commit()
        
        # Verify new schema
        cursor.execute("PRAGMA table_info(trading_orders)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"✅ Updated columns: {new_columns}")
        
        conn.close()
        
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.close()

def test_migration():
    """Test that the migration worked"""
    try:
        from app.database import get_engine
        from app.models import TradingOrder
        from sqlmodel import Session, select
        
        print("\n🧪 Testing migration...")
        
        engine = get_engine()
        with Session(engine) as session:
            # Try to query with new columns
            statement = select(TradingOrder).limit(1)
            result = session.exec(statement).first()
            print("✅ New schema query successful")
            
    except Exception as e:
        print(f"❌ Migration test failed: {e}")

if __name__ == "__main__":
    print("🚀 Database Migration for Enhanced Order Management")
    print("=" * 60)
    
    migrate_database()
    
    # Test the migration
    test_migration()
    
    print("\n" + "=" * 60)
    print("🎯 Migration complete! Restart backend to use new schema.")
    print("=" * 60)
