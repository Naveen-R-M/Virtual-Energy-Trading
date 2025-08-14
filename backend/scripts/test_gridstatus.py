#!/usr/bin/env python3
"""
Test script to verify GridStatus API connection and data fetching with rate limiting
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add app directory to path (adjust depth if your project structure differs)
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Load environment variables
load_dotenv()

PJM_NODE = "PJM-RTO ZONE"  # Exact string GridStatus expects

# Helpful spacing for the GridStatus free tier:
PAUSE = 2.5          # base pause between individual calls
PAUSE_BEFORE_LATEST = 4.0  # bigger pause before "latest" snapshots


async def test_gridstatus_api():
    """Test GridStatus API connection and data fetching"""

    print("=" * 60)
    print("GridStatus API Connection Test")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("GRIDSTATUS_API_KEY")
    if not api_key:
        print("❌ No API key found in environment")
        print("   Please set GRIDSTATUS_API_KEY in your .env file")
        return

    print(f"✅ API Key found: {api_key[:10]}...")

    # Import service
    from app.services.gridstatus_api import gridstatus_service

    # Test connection
    print("\n📡 Testing API connection...")
    is_connected = await gridstatus_service.test_connection()

    if not is_connected:
        print("❌ Failed to connect to GridStatus API")
        print("   Check your API key and internet connection")
        return

    print("✅ Successfully connected to GridStatus API")

    # Add delay to respect rate limits
    print(f"\n⏳ Implementing rate limiting (~1 req/{PAUSE:.1f}s)...")
    await asyncio.sleep(PAUSE)

    # Test fetching nodes for PJM (kept minimal to avoid rate limits)
    print("\n📍 Testing node fetching for PJM...")
    nodes = await gridstatus_service.get_available_nodes("PJM")
    if nodes:
        print(f"    Found {len(nodes)} nodes")
        for node in nodes[:3]:
            print(f"    - {node.get('node_code', 'N/A')}: {node.get('node_name', 'N/A')}")
    else:
        print("    No nodes found (normal if metadata endpoint is unavailable; sampling may return none)")

    await asyncio.sleep(PAUSE)

    # Test fetching Day-Ahead prices with proper node name
    print("\n📊 Testing Day-Ahead price fetching...")
    test_node = PJM_NODE
    test_date = datetime.utcnow() - timedelta(days=1)  # Yesterday (UTC)

    print(f"  Fetching DA prices for {test_node} on {test_date.date()}...")
    print("  (Note: GridStatus may not have data for all dates)")
    da_prices = await gridstatus_service.fetch_day_ahead_prices(test_node, test_date)

    if da_prices:
        print(f"✅ Retrieved {len(da_prices)} DA prices for {test_node} on {test_date.date()}")

        print("\n  Sample DA prices (first 5 hours):")
        for price in da_prices[:5]:
            hour = price.get("hour_start", "N/A")
            lmp = price.get("close_price", price.get("price", "N/A"))
            if isinstance(lmp, (int, float)):
                print(f"    {hour}: ${lmp:.2f}/MWh")
            else:
                print(f"    {hour}: ${lmp}/MWh")

        prices = [p.get("close_price", p.get("price", 0.0)) for p in da_prices if isinstance(p.get("close_price", p.get("price", None)), (int, float))]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            print(f"\n  Statistics:")
            print(f"    Average: ${avg_price:.2f}/MWh")
            print(f"    Min: ${min_price:.2f}/MWh")
            print(f"    Max: ${max_price:.2f}/MWh")
    else:
        print(f"⚠️  No DA prices retrieved for {test_node}")
        print("     Possible reasons:")
        print("     - No data available for this date")
        print("     - Rate limiting")
        print("     - Node name mismatch")

    await asyncio.sleep(PAUSE)

    # Test fetching Real-Time prices
    print("\n⚡ Testing Real-Time price fetching...")

    # Get last full hour of data (UTC)
    end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)

    print(f"  Fetching RT prices for {test_node}")
    print(f"  Time range (UTC): {start_time.isoformat()} to {end_time.isoformat()}")

    rt_prices = await gridstatus_service.fetch_real_time_prices(
        test_node, start_time, end_time
    )

    if rt_prices:
        print(f"✅ Retrieved {len(rt_prices)} RT prices for {test_node}")

        print("\n  Sample RT prices (first 5 intervals):")
        for price in rt_prices[:5]:
            timestamp = price.get("timestamp", "N/A")
            lmp = price.get("price", "N/A")
            if isinstance(lmp, (int, float)):
                print(f"    {timestamp}: ${lmp:.2f}/MWh")
            else:
                print(f"    {timestamp}: ${lmp}/MWh")

        prices = [p.get("price", 0.0) for p in rt_prices if isinstance(p.get("price", None), (int, float))]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            volatility = (sum((p - avg_price) ** 2 for p in prices) / len(prices)) ** 0.5

            print(f"\n  Statistics:")
            print(f"    Average: ${avg_price:.2f}/MWh")
            print(f"    Min: ${min_price:.2f}/MWh")
            print(f"    Max: ${max_price:.2f}/MWh")
            print(f"    Volatility (stdev): ${volatility:.2f}")
    else:
        print(f"⚠️  No RT prices retrieved for {test_node}")
        print("     This is normal if data is not available for the selected time range")

    # Extra wait before the “latest” snapshot to avoid 30/min limit
    await asyncio.sleep(PAUSE_BEFORE_LATEST)

    # Test getting latest prices
    print("\n📈 Testing latest price fetching...")
    latest = await gridstatus_service.get_latest_prices(test_node)

    if latest:
        print(f"✅ Retrieved latest prices for {test_node}")

        da = latest.get("day_ahead")
        if da:
            lmp = da.get("close_price", da.get("price"))
            if isinstance(lmp, (int, float)):
                print(f"  Day-Ahead: ${lmp:.2f}/MWh at {da.get('hour_start', 'N/A')}")
            else:
                print(f"  Day-Ahead: ${lmp}/MWh at {da.get('hour_start', 'N/A')}")
        else:
            print("  Day-Ahead: No data available")

        rt = latest.get("real_time")
        if rt:
            lmp = rt.get("price", "N/A")
            if isinstance(lmp, (int, float)):
                print(f"  Real-Time: ${lmp:.2f}/MWh at {rt.get('timestamp', 'N/A')}")
            else:
                print(f"  Real-Time: ${lmp}/MWh at {rt.get('timestamp', 'N/A')}")
        else:
            print("  Real-Time: No data available")
    else:
        print("⚠️  Could not retrieve latest prices")

    print("\n" + "=" * 60)
    print("✅ GridStatus API test completed!")
    print("=" * 60)
    print("\nNote: If some data is missing, it's normal — GridStatus may not")
    print("have data for all dates/times. Your app can fall back to mock data.")


async def test_market_data_service():
    """Test the MarketDataService with real/mock fallback"""

    print("\n" + "=" * 60)
    print("Market Data Service Test (with fallback)")
    print("=" * 60)

    from app.services.market_data import MarketDataService
    from app.database import engine, Session

    with Session(engine) as session:
        service = MarketDataService(session)

        # Test connection status
        print("\n🔌 Checking data source...")
        conn_info = await service.test_gridstatus_connection()

        if conn_info.get("connected"):
            print("✅ Using REAL data from GridStatus API")
        else:
            print("⚠️  Using MOCK data (GridStatus unavailable)")

        # Test fetching data (will use real if available, mock if not)
        test_node = PJM_NODE
        test_date = datetime.utcnow() - timedelta(days=1)

        print(f"\n📊 Fetching data for {test_node} on {test_date.date()}...")

        await asyncio.sleep(PAUSE)

        # Fetch DA prices
        da_prices = await service.fetch_day_ahead_prices(test_node, test_date)
        print(f"  Day-Ahead: {len(da_prices)} prices")

        await asyncio.sleep(PAUSE)

        # Fetch RT prices (first hour to avoid too many requests)
        start_time = test_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        rt_prices = await service.fetch_real_time_prices(test_node, start_time, end_time)
        print(f"  Real-Time: {len(rt_prices)} prices")

        # Extra pause before “latest” to stay under 30/min
        await asyncio.sleep(PAUSE_BEFORE_LATEST)

        # Get latest
        latest = await service.get_latest_prices(test_node)
        if latest.get("day_ahead"):
            val = latest["day_ahead"].get("close_price", latest["day_ahead"].get("price", "N/A"))
            if isinstance(val, (int, float)):
                print(f"  Latest DA: ${val:.2f}/MWh")
            else:
                print(f"  Latest DA: ${val}/MWh")
        if latest.get("real_time"):
            val = latest["real_time"].get("price", "N/A")
            if isinstance(val, (int, float)):
                print(f"  Latest RT: ${val:.2f}/MWh")
            else:
                print(f"  Latest RT: ${val}/MWh")


def main():
    """Run all tests"""

    print("\n🚀 Starting GridStatus API Integration Tests\n")
    print(f"⚠️  Note: This test respects API rate limits (~1 req/{PAUSE:.1f}s; ≤ 30/min)\n")

    try:
        # Run async tests sequentially
        asyncio.run(test_gridstatus_api())
        asyncio.run(test_market_data_service())

        print("\n✅ All tests completed!")
        print("\n💡 Tips:")
        print("  - If no real data was retrieved, your app can use mock data")
        print("  - Rate limits handled with spacing and an extra pause before 'latest'")
        print("  - Ensure exact node names (e.g., 'PJM-RTO ZONE')")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
