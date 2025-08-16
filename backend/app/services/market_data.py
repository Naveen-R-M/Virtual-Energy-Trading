"""
Market Data Service with Enhanced API Key Rotation
NO MOCK DATA - Real GridStatus data only
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlmodel import Session
from ..services.gridstatus_api_enhanced import GridStatusAPIServiceEnhanced

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Service for fetching market data using enhanced API with key rotation
    Uses 5 API keys in round-robin fashion to avoid rate limits
    """
    
    def __init__(self, session: Session = None):
        self.session = session
        
        # Initialize enhanced API service with key rotation
        try:
            self.api_service = GridStatusAPIServiceEnhanced()
            logger.info(f"Market Data Service initialized with {len(self.api_service.api_keys)} API key(s) for rotation")
        except Exception as e:
            logger.error(f"Failed to initialize GridStatus API service: {e}")
            raise RuntimeError(f"GridStatus API initialization failed: {e}")
    
    async def fetch_day_ahead_prices(
        self, 
        node: str, 
        date: datetime
    ) -> List[Dict]:
        """
        Fetch day-ahead prices with automatic key rotation
        
        Args:
            node: Grid node identifier (e.g., 'PJM_RTO')
            date: Date to fetch prices for
            
        Returns:
            List of price dictionaries with hour_start, node, price, close_price
        """
        try:
            logger.info(f"Fetching DA prices for {node} on {date.date()}")
            prices = await self.api_service.fetch_day_ahead_prices(node, date)
            
            if prices:
                logger.info(f"Successfully fetched {len(prices)} DA prices")
                return prices
            else:
                logger.warning(f"No DA prices available for {node} on {date.date()}")
                # Return empty list - no mock fallback
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch DA prices: {e}")
            # Log rotation status for debugging
            status = self.get_api_status()
            logger.info(f"API Key Status: {status}")
            raise  # Propagate error - no mock fallback
    
    async def fetch_real_time_prices(
        self, 
        node: str, 
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        Fetch real-time prices with automatic key rotation
        
        Args:
            node: Grid node identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of price dictionaries with timestamp, node, price
        """
        try:
            logger.info(f"Fetching RT prices for {node} from {start_time} to {end_time}")
            prices = await self.api_service.fetch_real_time_prices(
                node, start_time, end_time
            )
            
            if prices:
                logger.info(f"Successfully fetched {len(prices)} RT prices")
                return prices
            else:
                logger.warning(f"No RT prices available for {node}")
                # Return empty list - no mock fallback
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch RT prices: {e}")
            # Log rotation status for debugging
            status = self.get_api_status()
            logger.info(f"API Key Status: {status}")
            raise  # Propagate error - no mock fallback
    
    async def fetch_latest_prices(self, node: str) -> Dict:
        """
        Fetch latest available prices for both DA and RT markets
        """
        result = {
            "day_ahead": None,
            "real_time": None
        }
        
        try:
            # Get latest DA (today)
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            da_prices = await self.fetch_day_ahead_prices(node, today)
            
            if da_prices:
                # Get current hour's price
                current_hour = datetime.utcnow().hour
                for price in da_prices:
                    hour_start = datetime.fromisoformat(price["hour_start"].replace("Z", "+00:00"))
                    if hour_start.hour == current_hour:
                        result["day_ahead"] = price
                        break
                
                if not result["day_ahead"] and da_prices:
                    # Use first available if current hour not found
                    result["day_ahead"] = da_prices[0]
            
            # Get latest RT (last hour)
            now = datetime.utcnow()
            start_time = now - timedelta(hours=1)
            rt_prices = await self.fetch_real_time_prices(node, start_time, now)
            
            if rt_prices:
                # Use most recent
                result["real_time"] = rt_prices[-1]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch latest prices: {e}")
            return result
    
    def get_api_status(self) -> Dict:
        """
        Get current API service status including key rotation info
        """
        try:
            rotation_status = self.api_service.get_rotation_status()
            
            # Calculate aggregate stats
            total_requests = sum(k["requests"] for k in rotation_status["keys_status"])
            total_successes = sum(k["successes"] for k in rotation_status["keys_status"])
            total_failures = sum(k["failures"] for k in rotation_status["keys_status"])
            active_keys = sum(1 for k in rotation_status["keys_status"] if not k["rate_limited"])
            
            return {
                "mode": "real_data_only",
                "total_api_keys": rotation_status["total_keys"],
                "active_keys": active_keys,
                "total_requests": total_requests,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "success_rate": round(total_successes / total_requests * 100, 2) if total_requests > 0 else 0,
                "key_rotation": rotation_status
            }
        except Exception as e:
            logger.error(f"Failed to get API status: {e}")
            return {
                "mode": "real_data_only",
                "error": str(e)
            }
    
    async def bulk_fetch_historical_data(
        self,
        node: str,
        start_date: datetime,
        end_date: datetime,
        market_type: str = "both"
    ) -> Dict:
        """
        Bulk fetch historical data for a date range
        Uses key rotation to handle large data requests
        
        Args:
            node: Grid node identifier
            start_date: Start date
            end_date: End date
            market_type: 'da', 'rt', or 'both'
            
        Returns:
            Dictionary with da_prices and/or rt_prices
        """
        result = {
            "da_prices": [],
            "rt_prices": [],
            "fetch_summary": {
                "node": node,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "da_count": 0,
                "rt_count": 0
            }
        }
        
        try:
            # Fetch DA prices day by day
            if market_type in ["da", "both"]:
                current_date = start_date
                while current_date <= end_date:
                    logger.info(f"Fetching DA prices for {current_date.date()}")
                    
                    try:
                        da_prices = await self.fetch_day_ahead_prices(node, current_date)
                        result["da_prices"].extend(da_prices)
                        result["fetch_summary"]["da_count"] += len(da_prices)
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch DA for {current_date.date()}: {e}")
                    
                    current_date += timedelta(days=1)
            
            # Fetch RT prices in chunks
            if market_type in ["rt", "both"]:
                # RT data in 6-hour chunks to avoid large queries
                chunk_hours = 6
                current_start = start_date
                
                while current_start < end_date:
                    current_end = min(
                        current_start + timedelta(hours=chunk_hours),
                        end_date
                    )
                    
                    logger.info(f"Fetching RT prices from {current_start} to {current_end}")
                    
                    try:
                        rt_prices = await self.fetch_real_time_prices(
                            node, current_start, current_end
                        )
                        result["rt_prices"].extend(rt_prices)
                        result["fetch_summary"]["rt_count"] += len(rt_prices)
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(1.5)
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch RT for {current_start}: {e}")
                    
                    current_start = current_end
            
            # Log final API status
            status = self.get_api_status()
            result["fetch_summary"]["api_status"] = status
            
            logger.info(f"Bulk fetch complete: {result['fetch_summary']}")
            return result
            
        except Exception as e:
            logger.error(f"Bulk fetch failed: {e}")
            result["fetch_summary"]["error"] = str(e)
            return result

# For backward compatibility
import asyncio

# Singleton instance (lazy loaded)
_service_instance = None

def get_market_data_service(session: Session = None) -> MarketDataService:
    """Get or create market data service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = MarketDataService(session)
    return _service_instance
