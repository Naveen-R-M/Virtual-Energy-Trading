"""
Market Data Service for Virtual Energy Trading Platform
Strictly follows USE_REAL_DATA flag with no fallback
"""

import random
import json
import math
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import logging
import asyncio

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for fetching and managing market data"""
    
    def __init__(self, session=None):
        self.session = session
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Check if we should use real data - STRICT MODE
        self.use_real_data = os.getenv("USE_REAL_DATA", "true").lower() == "true"
        self.gridstatus_api = None
        
        logger.info(f"Market Data Service initialized with USE_REAL_DATA={self.use_real_data}")
        
        if self.use_real_data:
            try:
                from .gridstatus_api import gridstatus_service
                self.gridstatus_api = gridstatus_service
                logger.info("GridStatus API service initialized for REAL data mode")
            except Exception as e:
                logger.error(f"FAILED to initialize GridStatus API in REAL data mode: {e}")
                raise RuntimeError(
                    f"USE_REAL_DATA=true but GridStatus API initialization failed: {e}"
                )
        else:
            logger.info("Running in MOCK data mode")
    
    async def fetch_day_ahead_prices(self, node: str, date: datetime) -> List[Dict]:
        """
        Fetch Day-Ahead prices - STRICT mode based on USE_REAL_DATA flag
        """
        if self.use_real_data:
            # REAL DATA MODE - No fallback
            if not self.gridstatus_api:
                raise RuntimeError("GridStatus API not available in REAL data mode")
                
            try:
                logger.info(f"Fetching real DA prices for {node} on {date}")
                real_prices = await self.gridstatus_api.fetch_day_ahead_prices(node, date)
                
                if not real_prices:
                    raise ValueError(f"No real DA prices available for {node} on {date}")
                    
                logger.info(f"Successfully fetched {len(real_prices)} real DA prices")
                return real_prices
                    
            except Exception as e:
                logger.error(f"Error fetching real DA prices: {e}")
                raise  # Re-raise - NO FALLBACK in real data mode
        else:
            # MOCK DATA MODE
            logger.info(f"Generating mock DA prices for {node} on {date}")
            return await self.generate_mock_da_prices(node, date)
    
    async def fetch_real_time_prices(
        self, 
        node: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """
        Fetch Real-Time prices - STRICT mode based on USE_REAL_DATA flag
        """
        if self.use_real_data:
            # REAL DATA MODE - No fallback
            if not self.gridstatus_api:
                raise RuntimeError("GridStatus API not available in REAL data mode")
                
            try:
                logger.info(f"Fetching real RT prices for {node}")
                real_prices = await self.gridstatus_api.fetch_real_time_prices(
                    node, start_time, end_time
                )
                
                if not real_prices:
                    raise ValueError(
                        f"No real RT prices available for {node} between {start_time} and {end_time}"
                    )
                    
                logger.info(f"Successfully fetched {len(real_prices)} real RT prices")
                return real_prices
                    
            except Exception as e:
                logger.error(f"Error fetching real RT prices: {e}")
                raise  # Re-raise - NO FALLBACK in real data mode
        else:
            # MOCK DATA MODE
            logger.info(f"Generating mock RT prices for {node}")
            return await self.generate_mock_rt_prices(node, start_time, end_time)
    
    async def get_latest_prices(self, node: str) -> Dict:
        """
        Get latest prices - STRICT mode based on USE_REAL_DATA flag
        """
        if self.use_real_data:
            # REAL DATA MODE - No fallback
            if not self.gridstatus_api:
                raise RuntimeError("GridStatus API not available in REAL data mode")
                
            try:
                logger.info(f"Fetching latest real prices for {node}")
                latest = await self.gridstatus_api.get_latest_prices(node)
                
                if not latest or (not latest.get("day_ahead") and not latest.get("real_time")):
                    raise ValueError(f"No latest prices available for {node}")
                    
                return latest
                    
            except Exception as e:
                logger.error(f"Error fetching latest real prices: {e}")
                raise  # Re-raise - NO FALLBACK in real data mode
        else:
            # MOCK DATA MODE
            current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            
            da_price = await self.generate_single_da_price(node, current_hour)
            rt_price = await self.generate_single_rt_price(node)
            
            return {
                "node": node,
                "day_ahead": da_price,
                "real_time": rt_price,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def test_gridstatus_connection(self) -> Dict:
        """Test connection to GridStatus API"""
        result = {
            "use_real_data_flag": self.use_real_data,
            "mode": "REAL" if self.use_real_data else "MOCK"
        }
        
        if self.use_real_data:
            if not self.gridstatus_api:
                result.update({
                    "connected": False,
                    "api_configured": False,
                    "error": "GridStatus API not initialized in REAL data mode"
                })
            else:
                is_connected = await self.gridstatus_api.test_connection()
                result.update({
                    "connected": is_connected,
                    "api_configured": True,
                    "api_key_present": bool(os.getenv("GRIDSTATUS_API_KEY"))
                })
        else:
            result.update({
                "connected": False,
                "api_configured": False,
                "message": "Running in MOCK data mode - GridStatus API not used"
            })
        
        return result
    
    # ==================== MOCK DATA GENERATION METHODS ====================
    # These are ONLY used when USE_REAL_DATA=false
    
    async def generate_mock_da_prices(self, node: str, date: datetime) -> List[Dict]:
        """Generate realistic mock Day-Ahead hourly prices"""
        if self.use_real_data:
            raise RuntimeError("Mock data generation called in REAL data mode")
            
        prices = []
        base_date = date if isinstance(date, datetime) else datetime.strptime(date, "%Y-%m-%d")
        
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
    
    async def generate_mock_rt_prices(self, node: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate realistic mock Real-Time 5-minute prices"""
        if self.use_real_data:
            raise RuntimeError("Mock data generation called in REAL data mode")
            
        prices = []
        # Generate prices for every 5 minutes in the range
        current_time = start_time
        while current_time < end_time:
            timestamp = current_time
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
            if prices:
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
            
            current_time += timedelta(minutes=5)
        
        return prices
    
    async def generate_single_da_price(self, node: str, hour_start: datetime) -> Dict:
        """Generate a single DA price for a specific hour"""
        if self.use_real_data:
            raise RuntimeError("Mock data generation called in REAL data mode")
            
        hour = hour_start.hour
        
        # Create realistic price based on hour
        base_price = 45.0
        
        if 6 <= hour <= 9:
            time_factor = 1.0 + (hour - 6) * 0.15
            base_price = 42.0
        elif 14 <= hour <= 19:
            time_factor = 1.4 + 0.2 * (1 + math.sin((hour - 16) * math.pi / 3))
            base_price = 50.0
        elif 20 <= hour <= 23:
            time_factor = 1.2 - (hour - 20) * 0.1
            base_price = 48.0
        else:
            time_factor = 0.7 + 0.1 * random.random()
            base_price = 35.0
        
        daily_volatility = random.uniform(0.9, 1.1)
        price = max(15.0, base_price * time_factor * daily_volatility)
        
        return {
            "node": node,
            "hour_start": hour_start.isoformat() + "Z",
            "price": round(price, 2)
        }
    
    async def generate_single_rt_price(self, node: str) -> Dict:
        """Generate a single RT price for current time"""
        if self.use_real_data:
            raise RuntimeError("Mock data generation called in REAL data mode")
            
        current_time = datetime.utcnow()
        hour = current_time.hour
        
        # Create realistic price based on hour
        base_price = 45.0
        
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
        
        short_term_volatility = random.uniform(0.85, 1.15)
        price = max(10.0, base_price * time_factor * short_term_volatility)
        
        return {
            "node": node,
            "timestamp": current_time.isoformat() + "Z",
            "price": round(price, 2)
        }
    
    def save_mock_data(self, data: List[Dict], filename: str):
        """Save mock data to JSON file - ONLY in mock mode"""
        if self.use_real_data:
            raise RuntimeError("Cannot save mock data in REAL data mode")
            
        file_path = self.data_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Mock data saved: {file_path} ({len(data)} records)")
    
    def load_mock_data(self, filename: str) -> Optional[List[Dict]]:
        """Load mock data from JSON file - ONLY in mock mode"""
        if self.use_real_data:
            raise RuntimeError("Cannot load mock data in REAL data mode")
            
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


# Create a singleton instance
market_data_service = MarketDataService()
