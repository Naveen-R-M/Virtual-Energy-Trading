#!/usr/bin/env python3
"""
Create orders using the existing database schema (without new fields)
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def create_simple_orders():
    """Create orders using the original schema (no order_type, time_in_force, expires_at)"""
    
    # Simple orders that should work with existing schema
    simple_orders = [
        {
            "hour_start": "2025-08-14T14:00:00Z",
            "market": "real-time", 
            "side": "buy",
            "limit_price": 50.00,
            "quantity_mwh": 2.5,
            "time_slot": "2025-08-14T14:05:00Z"
        },
        {
            "hour_start": "2025-08-14T15:00:00Z",
            "market": "real-time",
            "side": "sell", 
            "limit_price": 75.00,
            "quantity_mwh": 1.8,
            "time_slot": "2025-08-14T15:10:00Z"
        }
    ]
    
    print("🔧 Creating simple orders with existing schema...")
    created_orders = []
    
    for i, order_data in enumerate(simple_orders):
        try:
            print(f"\n📝 Creating order {i+1}...")
            print(f"   {order_data['side'].upper()} {order_data['quantity_mwh']} MWh @ ${order_data['limit_price']:.2f}")
            
            response = requests.post(
                f"{BASE_URL}/api/orders",
                json=order_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Order created: {result['order_id']}")
                created_orders.append(result)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"   ❌ Order failed: {error_detail}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return created_orders

def check_orders():
    """Check orders in database"""
    try:
        print("\n📋 Checking orders in database...")
        response = requests.get(f"{BASE_URL}/api/orders?user_id=demo_user&date=2025-08-14")
        
        if response.status_code == 200:
            result = response.json()
            orders = result.get("orders", [])
            print(f"✅ Found {len(orders)} orders:")
            
            for order in orders:
                print(f"  📋 {order['order_id']}: {order['side']} {order['quantity_mwh']} MWh @ ${order['limit_price']:.2f} [{order['status']}]")
            
            return orders
        else:
            print(f"❌ Error checking orders: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    print("🚀 Creating Test Orders for Frontend Integration")
    print("=" * 60)
    
    # Create simple orders
    created = create_simple_orders()
    
    # Check what was created
    orders = check_orders()
    
    print(f"\n✅ Successfully created {len(created)} orders")
    print(f"📊 Database now contains {len(orders)} orders")
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS TO SEE REAL DATA:")
    print("1. Hard refresh browser (Ctrl+Shift+R)")
    print("2. Select date: August 14, 2025") 
    print("3. Real orders should now appear in table!")
    print("4. Look for 'LIVE DATA' tag in dashboard")
    print("=" * 60)

if __name__ == "__main__":
    main()
