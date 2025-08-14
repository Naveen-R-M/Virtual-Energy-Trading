#!/usr/bin/env python3
"""
Fetch market prices script for Virtual Energy Trading Platform.
Supports both real GridStatus API and mock data generation.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

def generate_mock_da_prices(node: str, date: str) -> list:
    """Generate mock day-ahead hourly prices."""
    base_price = 45.0
    prices = []
    
    for hour in range(24):
        # Create realistic price curve
        time_factor = 1.0
        if 6 <= hour <= 9:  # Morning ramp
            time_factor = 1.2
        elif 14 <= hour <= 19:  # Afternoon peak
            time_factor = 1.5
        elif 20 <= hour <= 23:  # Evening decline
            time_factor = 0.8
        else:  # Off-peak
            time_factor = 0.7
        
        # Add some random volatility
        volatility = random.uniform(0.9, 1.1)
        price = base_price * time_factor * volatility
        
        prices.append({
            "node": node,
            "hour_start": f"{date}T{hour:02d}:00:00Z",
            "close_price": round(price, 2)
        })
    
    return prices

def generate_mock_rt_prices(node: str, date: str) -> list:
    """Generate mock real-time 5-minute prices."""
    base_price = 45.0
    prices = []
    
    start_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
    
    for minute in range(0, 24 * 60, 5):  # Every 5 minutes for 24 hours
        current_time = start_time + timedelta(minutes=minute)
        hour = current_time.hour
        
        # Create realistic price curve similar to DA
        time_factor = 1.0
        if 6 <= hour <= 9:  # Morning ramp
            time_factor = 1.2
        elif 14 <= hour <= 19:  # Afternoon peak
            time_factor = 1.5
        elif 20 <= hour <= 23:  # Evening decline
            time_factor = 0.8
        else:  # Off-peak
            time_factor = 0.7
        
        # Add higher volatility for RT prices
        volatility = random.uniform(0.8, 1.2)
        price = base_price * time_factor * volatility
        
        prices.append({
            "node": node,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "price": round(price, 2)
        })
    
    return prices

def save_mock_data(data: list, filename: str):
    """Save mock data to JSON file."""
    data_dir = Path("/app/data")
    data_dir.mkdir(exist_ok=True)
    
    file_path = data_dir / filename
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Mock data saved: {file_path} ({len(data)} records)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fetch or generate market price data")
    parser.add_argument("--node", default="PJM_RTO", help="Grid node (default: PJM_RTO)")
    parser.add_argument("--date", default="yesterday", help="Date (YYYY-MM-DD or 'yesterday')")
    parser.add_argument("--da", action="store_true", help="Fetch day-ahead prices")
    parser.add_argument("--rt", action="store_true", help="Fetch real-time prices")
    parser.add_argument("--mock", action="store_true", help="Generate mock data")
    
    args = parser.parse_args()
    
    # Handle date
    if args.date == "yesterday":
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        date = args.date
    
    print(f"🔄 Processing market data for {args.node} on {date}")
    
    # For now, always generate mock data since we don't have GridStatus integration yet
    if args.da or (not args.da and not args.rt):
        print("📊 Generating day-ahead mock prices...")
        da_prices = generate_mock_da_prices(args.node, date)
        save_mock_data(da_prices, f"mock_da_{date}.json")
    
    if args.rt or (not args.da and not args.rt):
        print("⚡ Generating real-time mock prices...")
        rt_prices = generate_mock_rt_prices(args.node, date)
        save_mock_data(rt_prices, f"mock_rt_{date}.json")
    
    print("✅ Data generation completed successfully!")

if __name__ == "__main__":
    main()
