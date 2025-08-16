#!/usr/bin/env python3
"""
Script to create real orders for testing the frontend integration
"""

import requests
import json
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://localhost:8000"

def test_connection():
    """Test backend connection"""
    try:
        response = requests.get(f"{BASE_URL}/api/test/connection")
        result = response.json()
        print("✅ Backend connection:", result["message"])
        return True
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def create_sample_orders():
    """Create sample orders that will show up in the dashboard"""
    
    orders_to_create = [
        {
            "hour_start": "2025-08-14T14:00:00Z",
            "market": "real-time",
            "side": "buy",
            "order_type": "LMT",
            "limit_price": 50.00,
            "quantity_mwh": 2.5,
            "time_slot": "2025-08-14T14:05:00Z",
            "time_in_force": "GTC"
        },
        {
            "hour_start": "2025-08-14T15:00:00Z", 
            "market": "real-time",
            "side": "sell",
            "order_type": "LMT",
            "limit_price": 60.00,
            "quantity_mwh": 1.8,
            "time_slot": "2025-08-14T15:10:00Z",
            "time_in_force": "GTC"
        },
        {
            "hour_start": "2025-08-14T16:00:00Z",
            "market": "day-ahead", 
            "side": "buy",
            "order_type": "LMT",
            "limit_price": 55.00,
            "quantity_mwh": 3.0,
            "time_in_force": "GTC"
        }
    ]
    
    created_orders = []
    
    for i, order_data in enumerate(orders_to_create):
        try:
            print(f"\n📝 Creating order {i+1}/3...")
            print(f"   Market: {order_data['market']}")
            print(f"   Side: {order_data['side']}")
            print(f"   Quantity: {order_data['quantity_mwh']} MWh")
            print(f"   Limit: ${order_data['limit_price']:.2f}")
            
            response = requests.post(
                f"{BASE_URL}/api/orders",
                json=order_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Order created: {result['order_id']}")
                print(f"   Status: {result['message']}")
                created_orders.append(result)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"   ❌ Order failed: {error_detail}")
                
        except Exception as e:
            print(f"   ❌ Error creating order: {e}")
    
    return created_orders

def check_orders():
    """Check what orders exist in the database"""
    try:
        print("\n📋 Checking existing orders...")
        response = requests.get(f"{BASE_URL}/api/orders?user_id=demo_user&date=2025-08-14")
        result = response.json()
        
        orders = result.get("orders", [])
        print(f"Found {len(orders)} orders in database:")
        
        for order in orders:
            print(f"  - {order['order_id']}: {order['side']} {order['quantity_mwh']} MWh @ ${order['limit_price']:.2f} [{order['status']}]")
        
        return orders
        
    except Exception as e:
        print(f"❌ Error checking orders: {e}")
        return []

def test_market_data():
    """Test real market data"""
    try:
        print("\n📈 Testing real market data...")
        response = requests.get(f"{BASE_URL}/api/market/da?date=2025-08-14&node=PJM_RTO")
        result = response.json()
        
        prices = result.get("prices", [])
        if prices:
            print(f"✅ Got {len(prices)} real DA prices")
            print(f"   First price: ${prices[0]['close_price']:.2f} at {prices[0]['hour_start']}")
            print(f"   Peak price: ${max(p['close_price'] for p in prices):.2f}")
            print(f"   Off-peak price: ${min(p['close_price'] for p in prices):.2f}")
        else:
            print("❌ No price data found")
            
    except Exception as e:
        print(f"❌ Error testing market data: {e}")

def main():
    """Main test function"""
    print("🚀 Testing Virtual Energy Trading Platform")
    print("=" * 50)
    
    # Test connection
    if not test_connection():
        return
    
    # Test market data
    test_market_data()
    
    # Check existing orders
    existing_orders = check_orders()
    
    # Create new orders if none exist
    if len(existing_orders) == 0:
        print("\n🔧 No orders found. Creating sample orders...")
        created = create_sample_orders()
        print(f"\n✅ Created {len(created)} orders successfully!")
        
        # Check orders again
        check_orders()
    else:
        print(f"\n✅ Found {len(existing_orders)} existing orders")
    
    print("\n" + "=" * 50)
    print("🎯 NEXT STEPS:")
    print("1. Hard refresh your browser (Ctrl+Shift+R)")
    print("2. Select date: August 14, 2025")
    print("3. Look for 'LIVE DATA' green tag")
    print("4. Orders should now show real data!")
    print("=" * 50)

if __name__ == "__main__":
    main()
