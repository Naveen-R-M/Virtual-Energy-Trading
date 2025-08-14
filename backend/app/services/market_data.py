"""
Market Data Service for Virtual Energy Trading Platform
Handles data fetching and mock data generation for both markets
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for fetching and managing market data"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
    
    def generate_mock_da_prices(self, node: str, date: str) -> List[Dict]:
        """Generate realistic mock Day-Ahead hourly prices"""
        prices = []
        base_date = datetime.strptime(date, "%Y-%m-%d")
        
        for hour in range(24):
            hour_start = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Create realistic intraday price curve
            base_price = 45.0
            
            # Morning ramp (6-9 AM): increasing prices
            if 6 <= hour <= 9:
                time_factor = 1.0 + (hour - 6) * 0.15  # 1.0 to 1.45
                base_price = 42.0
            
            # Peak demand (2-7 PM): highest prices
            elif 14 <= hour <= 19:
                time_factor = 1.4 + 0.2 * (1 + math.sin((hour - 16) * math.pi / 3))  # 1.4 to 1.8
                base_price = 50.0
            
            # Evening decline (8-11 PM): decreasing prices
            elif 20 <= hour <= 23:
                time_factor = 1.2 - (hour - 20) * 0.1  # 1.2 to 0.9
                base_price = 48.0
            
            # Off-peak (midnight-5 AM, 10 AM-1 PM): low prices
            else:
                time_factor = 0.7 + 0.1 * random.random()  # 0.7 to 0.8
                base_price = 35.0
            
            # Add daily volatility
            daily_volatility = random.uniform(0.9, 1.1)
            
            # Calculate final price
            price = base_price * time_factor * daily_volatility
            price = max(15.0, price)  # Floor price
            
            prices.append({
                "node": node,
                "hour_start": hour_start.isoformat() + "Z",
                "close_price": round(price, 2),
                "created_at": datetime.utcnow().isoformat() + "Z"
            })
        
        return prices
    
    def generate_mock_rt_prices(self, node: str, date: str) -> List[Dict]:
        """Generate realistic mock Real-Time 5-minute prices"""
        prices = []
        base_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Generate prices for every 5 minutes (288 intervals per day)
        for interval in range(288):
            timestamp = base_date + timedelta(minutes=interval * 5)
            hour = timestamp.hour
            minute = timestamp.minute
            
            # Base price similar to DA but with higher volatility
            base_price = 45.0
            
            # Time-of-day factors (similar to DA but more volatile)
            if 6 <= hour <= 9:
                time_factor = 1.0 + (hour - 6) * 0.15
                base_price = 42.0
            elif 14 <= hour <= 19:
                time_factor = 1.4 + 0.3 * (1 + math.sin((hour - 16) * math.pi / 3))
                base_price = 50.0
            elif 20 <= hour <= 23:
                time_factor = 1.2 - (hour - 20) * 0.1
                base_price = 48.0
            else:
                time_factor = 0.7 + 0.15 * random.random()
                base_price = 35.0
            
            # Add 5-minute volatility (higher than DA)
            short_term_volatility = random.uniform(0.85, 1.15)
            
            # Add some correlation to previous price (momentum)
            if interval > 0:
                prev_price = prices[-1]["price"]
                momentum = 0.1 * (prev_price / base_price - 1)
                time_factor += momentum
            
            # Calculate final price
            price = base_price * time_factor * short_term_volatility
            price = max(10.0, price)  # Floor price
            
            prices.append({
                "node": node,
                "timestamp": timestamp.isoformat() + "Z",
                "price": round(price, 2),
                "created_at": datetime.utcnow().isoformat() + "Z"
            })
        
        return prices
    
    def save_mock_data(self, data: List[Dict], filename: str):
        """Save mock data to JSON file"""
        file_path = self.data_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Mock data saved: {file_path} ({len(data)} records)")
    
    def load_mock_data(self, filename: str) -> Optional[List[Dict]]:
        """Load mock data from JSON file"""
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Mock data loaded: {file_path} ({len(data)} records)")
            return data
            
        except Exception as e:
            logger.error(f"Error loading mock data from {file_path}: {e}")
            return None
    
    async def fetch_real_market_data(self, node: str, date: str, market_type: str) -> Optional[List[Dict]]:
        """
        Fetch real market data from GridStatus API
        Falls back to mock data if API is unavailable
        """
        try:
            # TODO: Implement real GridStatus API integration
            # For now, return mock data
            logger.warning(f"GridStatus API not implemented, using mock data for {market_type}")
            
            if market_type == "day-ahead":
                return self.generate_mock_da_prices(node, date)
            else:
                return self.generate_mock_rt_prices(node, date)
                
        except Exception as e:
            logger.error(f"Error fetching real market data: {e}")
            # Fall back to mock data
            if market_type == "day-ahead":
                return self.generate_mock_da_prices(node, date)
            else:
                return self.generate_mock_rt_prices(node, date)

# Import math for sin function
import math