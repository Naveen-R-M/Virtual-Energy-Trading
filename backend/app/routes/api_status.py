"""
API Status and Key Rotation Monitoring Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import datetime, timedelta
from typing import Optional
from ..database import get_session
from ..services.market_data import MarketDataService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["monitoring"])

@router.get("/keys")
async def get_api_key_status(session: Session = Depends(get_session)):
    """
    Get current API key rotation status and statistics
    
    Returns:
    - Total number of keys configured (5 keys)
    - Status of each key (requests, successes, failures, rate limit status)
    - Current rotation statistics
    """
    try:
        service = MarketDataService(session)
        status = service.get_api_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting API key status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keys/test")
async def test_api_keys(
    session: Session = Depends(get_session),
    node: str = Query(default="PJM_RTO", description="Node to test with")
):
    """
    Test all configured API keys and report their status
    
    This endpoint will:
    1. Try to fetch data using key rotation
    2. Report which keys are working
    3. Show current rate limit status
    """
    try:
        service = MarketDataService(session)
        
        # Get yesterday's date for testing (more likely to have data)
        test_date = datetime.utcnow() - timedelta(days=1)
        test_date = test_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Test DA fetch (this will rotate through keys as needed)
        test_results = {
            "test_node": node,
            "test_date": test_date.date().isoformat(),
            "da_test": {
                "success": False,
                "price_count": 0,
                "error": None
            },
            "rt_test": {
                "success": False,
                "price_count": 0,
                "error": None
            }
        }
        
        # Test DA prices
        try:
            logger.info(f"Testing DA price fetch for {node} on {test_date.date()}")
            da_prices = await service.fetch_day_ahead_prices(node, test_date)
            test_results["da_test"]["success"] = len(da_prices) > 0
            test_results["da_test"]["price_count"] = len(da_prices)
            logger.info(f"DA test result: {len(da_prices)} prices")
        except Exception as e:
            test_results["da_test"]["error"] = str(e)
            logger.error(f"DA test failed: {e}")
        
        # Test RT prices (smaller time range)
        rt_start = test_date.replace(hour=14, minute=0)
        rt_end = rt_start + timedelta(hours=1)
        
        try:
            logger.info(f"Testing RT price fetch for {node} from {rt_start} to {rt_end}")
            rt_prices = await service.fetch_real_time_prices(node, rt_start, rt_end)
            test_results["rt_test"]["success"] = len(rt_prices) > 0
            test_results["rt_test"]["price_count"] = len(rt_prices)
            logger.info(f"RT test result: {len(rt_prices)} prices")
        except Exception as e:
            test_results["rt_test"]["error"] = str(e)
            logger.error(f"RT test failed: {e}")
        
        # Get the status after tests
        api_status = service.get_api_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "test_results": test_results,
            "api_status": api_status,
            "summary": {
                "all_tests_passed": test_results["da_test"]["success"] and test_results["rt_test"]["success"],
                "active_keys": api_status.get("active_keys", 0),
                "total_keys": api_status.get("total_api_keys", 0),
                "success_rate": api_status.get("success_rate", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/reset")
async def reset_rate_limits(
    session: Session = Depends(get_session),
    confirm: bool = Query(default=False, description="Confirm reset action")
):
    """
    Reset rate limit tracking for all API keys
    
    WARNING: This only resets internal tracking. Actual API rate limits still apply!
    Use with caution - only when you're sure the rate limit window has passed.
    """
    if not confirm:
        return {
            "status": "error",
            "message": "Reset not confirmed. Add ?confirm=true to proceed.",
            "warning": "This will reset internal rate limit tracking but actual API limits still apply!"
        }
    
    try:
        service = MarketDataService(session)
        
        # Reset rate limit tracking
        if hasattr(service.api_service, 'key_rotator'):
            for key_status in service.api_service.key_rotator.keys:
                key_status.rate_limited_until = None
                key_status.request_count = 0
                key_status.success_count = 0
                key_status.failure_count = 0
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Rate limit tracking reset for all 5 API keys",
            "warning": "Actual GridStatus API rate limits still apply!"
        }
        
    except Exception as e:
        logger.error(f"Error resetting rate limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keys/health")
async def api_health_check(session: Session = Depends(get_session)):
    """
    Quick health check for API key rotation system
    
    Returns a simple health status indicating if the system is operational
    """
    try:
        service = MarketDataService(session)
        status = service.get_api_status()
        
        # Determine health
        total_keys = status.get("total_api_keys", 0)
        active_keys = status.get("active_keys", 0)
        success_rate = status.get("success_rate", 0)
        
        if active_keys == 0:
            health_status = "critical"
            health_message = "All API keys are rate-limited"
        elif active_keys < total_keys / 2:
            health_status = "degraded"
            health_message = f"Only {active_keys}/{total_keys} keys active"
        elif success_rate < 50:
            health_status = "warning"
            health_message = f"Low success rate: {success_rate}%"
        else:
            health_status = "healthy"
            health_message = f"{active_keys}/{total_keys} keys active, {success_rate}% success rate"
        
        return {
            "status": health_status,
            "message": health_message,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "success_rate": success_rate,
                "total_requests": status.get("total_requests", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/fetch/history")
async def fetch_historical_data(
    session: Session = Depends(get_session),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    days: int = Query(default=1, ge=1, le=7, description="Number of days to fetch"),
    market: str = Query(default="both", regex="^(da|rt|both)$", description="Market type")
):
    """
    Fetch historical market data for multiple days
    
    Uses key rotation to handle bulk data fetching efficiently
    Maximum 7 days to avoid overwhelming the system
    """
    try:
        service = MarketDataService(session)
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Fetching {days} days of {market} data for {node}")
        
        # Fetch data
        result = await service.bulk_fetch_historical_data(
            node=node,
            start_date=start_date,
            end_date=end_date,
            market_type=market
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "fetch_summary": result["fetch_summary"],
            "data": {
                "da_prices": result["da_prices"][:10] if result["da_prices"] else [],  # First 10 for preview
                "rt_prices": result["rt_prices"][:10] if result["rt_prices"] else [],  # First 10 for preview
                "total_da_prices": len(result["da_prices"]),
                "total_rt_prices": len(result["rt_prices"])
            },
            "api_status": result["fetch_summary"].get("api_status", {})
        }
        
    except Exception as e:
        logger.error(f"Historical fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
