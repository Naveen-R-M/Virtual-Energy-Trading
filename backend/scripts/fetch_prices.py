#!/usr/bin/env python3
"""
Fetch market prices script for Virtual Energy Trading Platform.
Supports both GridStatus API real data and mock data generation.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

async def fetch_prices(node: str, date: str, use_mock: bool = False):
    """Fetch or generate market price data."""
    
    # Parse date
    if date == "yesterday":
        target_date = datetime.now() - timedelta(days=1)
    elif date == "today":
        target_date = datetime.now()
    else:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    
    print(f"🔄 Fetching market data for {node} on {target_date.date()}")
    
    # Import services
    from app.services.market_data import MarketDataService
    from app.database import engine, Session
    from app.models import DayAheadPrice, RealTimePrice
    
    # Create service
    with Session(engine) as session:
        service = MarketDataService(session)
        
        # Check if we're using real data
        if not use_mock:
            connection_info = await service.test_gridstatus_connection()
            if connection_info.get("connected"):
                print("✅ Connected to GridStatus API - fetching real data")
            else:
                print("⚠️  GridStatus API not available - using mock data")
                use_mock = True
        
        # Fetch Day-Ahead prices
        print("📊 Fetching day-ahead prices...")
        if use_mock:
            da_prices = await service.generate_mock_da_prices(node, target_date)
        else:
            da_prices = await service.fetch_day_ahead_prices(node, target_date)
        
        if da_prices:
            print(f"  Retrieved {len(da_prices)} DA prices")
            
            # Save to database
            for price_data in da_prices:
                try:
                    hour_start = datetime.fromisoformat(
                        price_data["hour_start"].replace("Z", "+00:00")
                    )
                    
                    # Check if already exists
                    existing = session.query(DayAheadPrice).filter(
                        DayAheadPrice.node == node,
                        DayAheadPrice.hour_start_utc == hour_start
                    ).first()
                    
                    if not existing:
                        da_price = DayAheadPrice(
                            node=node,
                            hour_start_utc=hour_start,
                            price=price_data.get("close_price", price_data.get("price", 0)),
                            close_price=price_data.get("close_price", price_data.get("price", 0))
                        )
                        session.add(da_price)
                
                except Exception as e:
                    print(f"  Warning: Could not save DA price: {e}")
            
            session.commit()
            print(f"  ✅ Saved DA prices to database")
        else:
            print("  ⚠️  No DA prices retrieved")
        
        # Fetch Real-Time prices
        print("⚡ Fetching real-time prices...")
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        if use_mock:
            rt_prices = await service.generate_mock_rt_prices(node, start_time, end_time)
        else:
            rt_prices = await service.fetch_real_time_prices(node, start_time, end_time)
        
        if rt_prices:
            print(f"  Retrieved {len(rt_prices)} RT prices")
            
            # Save to database (sample to avoid too many records)
            saved_count = 0
            for price_data in rt_prices:
                try:
                    timestamp = datetime.fromisoformat(
                        price_data["timestamp"].replace("Z", "+00:00")
                    )
                    
                    # Check if already exists
                    existing = session.query(RealTimePrice).filter(
                        RealTimePrice.node == node,
                        RealTimePrice.timestamp_utc == timestamp
                    ).first()
                    
                    if not existing:
                        rt_price = RealTimePrice(
                            node=node,
                            timestamp_utc=timestamp,
                            price=price_data["price"]
                        )
                        session.add(rt_price)
                        saved_count += 1
                
                except Exception as e:
                    print(f"  Warning: Could not save RT price: {e}")
            
            session.commit()
            print(f"  ✅ Saved {saved_count} new RT prices to database")
        else:
            print("  ⚠️  No RT prices retrieved")
        
        # Save to JSON files for reference
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        if da_prices:
            da_file = data_dir / f"da_{node}_{target_date.strftime('%Y%m%d')}.json"
            with open(da_file, 'w') as f:
                json.dump(da_prices, f, indent=2)
            print(f"  💾 Saved DA data to {da_file}")
        
        if rt_prices:
            rt_file = data_dir / f"rt_{node}_{target_date.strftime('%Y%m%d')}.json"
            with open(rt_file, 'w') as f:
                json.dump(rt_prices[:100], f, indent=2)  # Save sample for file size
            print(f"  💾 Saved RT data sample to {rt_file}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch market price data from GridStatus API or generate mock data"
    )
    parser.add_argument(
        "--node", 
        default="PJM_RTO", 
        help="Grid node (default: PJM_RTO)"
    )
    parser.add_argument(
        "--date", 
        default="yesterday", 
        help="Date (YYYY-MM-DD, 'yesterday', or 'today')"
    )
    parser.add_argument(
        "--mock", 
        action="store_true", 
        help="Force use of mock data instead of real API"
    )
    parser.add_argument(
        "--da", 
        action="store_true", 
        help="Fetch only day-ahead prices"
    )
    parser.add_argument(
        "--rt", 
        action="store_true", 
        help="Fetch only real-time prices"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    if not args.mock and not os.getenv("GRIDSTATUS_API_KEY"):
        print("⚠️  No GRIDSTATUS_API_KEY found in environment")
        print("   Set it in .env file or use --mock flag for mock data")
        args.mock = True
    
    # Run async function
    asyncio.run(fetch_prices(args.node, args.date, args.mock))
    
    print("✅ Data fetching completed successfully!")

if __name__ == "__main__":
    main()
