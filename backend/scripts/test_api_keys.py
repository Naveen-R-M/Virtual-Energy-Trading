#!/usr/bin/env python3
"""
Test script for API key rotation
Run: python scripts/test_api_keys.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.services.gridstatus_api_enhanced import GridStatusAPIServiceEnhanced

async def test_keys():
    """Test all configured API keys"""
    
    print("=" * 70)
    print("🔄 GridStatus API Key Rotation Tester")
    print("=" * 70)
    
    # Check environment
    keys_str = os.getenv("GRIDSTATUS_API_KEYS", "")
    if not keys_str:
        keys_str = os.getenv("GRIDSTATUS_API_KEY", "")
    
    if not keys_str:
        print("❌ No API keys found in environment variables")
        print("   Set GRIDSTATUS_API_KEYS in your .env file")
        return
    
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    print(f"✅ Found {len(keys)} API key(s) to test")
    print(f"   Keys: {', '.join(['...' + k[-4:] for k in keys])}")
    print()
    
    # Initialize service
    try:
        service = GridStatusAPIServiceEnhanced()
        print(f"✅ Service initialized with {len(service.api_keys)} keys")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return
    
    print()
    
    # Test configuration
    test_date = datetime.utcnow() - timedelta(days=1)
    test_node = "PJM_RTO"
    
    print(f"📊 Test Configuration:")
    print(f"   Node: {test_node}")
    print(f"   Date: {test_date.date()}")
    print()
    
    # Test 1: Day-Ahead prices
    print("Test 1: Fetching Day-Ahead Prices")
    print("-" * 40)
    try:
        da_prices = await service.fetch_day_ahead_prices(test_node, test_date)
        if da_prices:
            print(f"✅ Successfully fetched {len(da_prices)} DA prices")
            print(f"   Sample: Hour {da_prices[0]['hour_start'][:13]}, Price: ${da_prices[0]['price']:.2f}")
        else:
            print("⚠️ No DA prices returned")
    except Exception as e:
        print(f"❌ DA fetch failed: {e}")
    
    print()
    
    # Test 2: Real-Time prices
    print("Test 2: Fetching Real-Time Prices")
    print("-" * 40)
    rt_start = test_date.replace(hour=14, minute=0, second=0, microsecond=0)
    rt_end = rt_start + timedelta(hours=1)
    
    try:
        rt_prices = await service.fetch_real_time_prices(test_node, rt_start, rt_end)
        if rt_prices:
            print(f"✅ Successfully fetched {len(rt_prices)} RT prices")
            print(f"   Sample: Time {rt_prices[0]['timestamp'][:16]}, Price: ${rt_prices[0]['price']:.2f}")
        else:
            print("⚠️ No RT prices returned")
    except Exception as e:
        print(f"❌ RT fetch failed: {e}")
    
    print()
    
    # Test 3: Multiple rapid requests to test rotation
    print("Test 3: Rapid Requests (Testing Rotation)")
    print("-" * 40)
    
    success_count = 0
    fail_count = 0
    
    for i in range(5):
        try:
            # Fetch different hours to avoid cache
            test_hour = test_date.replace(hour=i*4 % 24)
            rt_start = test_hour
            rt_end = rt_start + timedelta(minutes=30)
            
            print(f"   Request {i+1}: Fetching RT for hour {test_hour.hour}:00...", end="")
            rt_prices = await service.fetch_real_time_prices(test_node, rt_start, rt_end)
            
            if rt_prices:
                print(f" ✅ ({len(rt_prices)} prices)")
                success_count += 1
            else:
                print(f" ⚠️ (no data)")
                
        except Exception as e:
            print(f" ❌ (error: {str(e)[:30]}...)")
            fail_count += 1
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    print(f"\n   Results: {success_count} successful, {fail_count} failed")
    
    print()
    
    # Show final key status
    print("📈 API Key Status After Tests:")
    print("-" * 40)
    status = service.get_rotation_status()
    
    for i, key_info in enumerate(status["keys_status"], 1):
        status_emoji = "🟢" if not key_info['rate_limited'] else "🔴"
        print(f"{status_emoji} Key {i} ({key_info['key_suffix']}):")
        print(f"     Requests: {key_info['requests']}")
        print(f"     Successes: {key_info['successes']}")
        print(f"     Failures: {key_info['failures']}")
        if key_info['rate_limited']:
            print(f"     ⏰ Rate limited for {key_info['seconds_until_available']:.0f} more seconds")
    
    # Summary
    total_requests = sum(k["requests"] for k in status["keys_status"])
    total_successes = sum(k["successes"] for k in status["keys_status"])
    active_keys = sum(1 for k in status["keys_status"] if not k["rate_limited"])
    
    print()
    print("📊 Summary:")
    print("-" * 40)
    print(f"   Total Requests: {total_requests}")
    print(f"   Total Successes: {total_successes}")
    print(f"   Success Rate: {(total_successes/total_requests*100):.1f}%" if total_requests > 0 else "N/A")
    print(f"   Active Keys: {active_keys}/{len(status['keys_status'])}")
    
    print()
    print("=" * 70)
    print("✅ Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    print("\n🚀 Starting API Key Rotation Test...\n")
    asyncio.run(test_keys())
