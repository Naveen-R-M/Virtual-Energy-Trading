"""
Simple test endpoint to verify frontend-backend connection
"""

from fastapi import APIRouter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])

@router.get("/connection")
async def test_connection():
    """Simple test endpoint to verify frontend can reach backend"""
    return {
        "status": "success",
        "message": "Frontend-backend connection working!",
        "timestamp": datetime.utcnow().isoformat(),
        "backend_version": "0.2.0",
        "real_data_enabled": True
    }

@router.get("/sample-data")
async def get_sample_data():
    """Get sample data to test frontend integration"""
    
    # Real-looking price data (this could be real GridStatus data)
    sample_prices = []
    for hour in range(24):
        # Create realistic price pattern
        if 0 <= hour <= 5:      # Off-peak
            base_price = 25 + hour * 2
        elif 6 <= hour <= 9:    # Morning ramp
            base_price = 35 + (hour - 6) * 8
        elif 10 <= hour <= 13:  # Mid-day
            base_price = 45 + (hour - 10) * 2
        elif 14 <= hour <= 19:  # Peak
            base_price = 70 + (hour - 14) * 6
        else:                   # Evening decline
            base_price = 90 - (hour - 20) * 8
            
        import random
        da_price = base_price + random.uniform(-5, 5)
        rt_price = da_price + random.uniform(-8, 8)
        
        sample_prices.append({
            "hour": f"{hour:02d}:00",
            "daPrice": round(da_price, 2),
            "rtPrice": round(rt_price, 2),
            "spread": round(rt_price - da_price, 2)
        })
    
    # Sample orders data
    sample_orders = [
        {
            "id": "REAL-001",
            "time": "09:15",
            "hour": "14:00", 
            "side": "Buy",
            "quantity": 2.5,
            "price": 48.50,
            "fillPrice": 47.25,
            "status": "Filled",
            "pnl": 156.25
        },
        {
            "id": "REAL-002",
            "time": "10:30",
            "hour": "16:00",
            "side": "Sell", 
            "quantity": 3.0,
            "price": 55.00,
            "fillPrice": 56.80,
            "status": "Filled",
            "pnl": 540.00
        }
    ]
    
    # Sample P&L data
    sample_pnl = []
    cumulative = 0
    for i in range(7):
        daily_pnl = [250, 180, -120, 420, -80, 310, -60][i]
        cumulative += daily_pnl
        day = datetime.now().date()
        from datetime import timedelta
        day = day - timedelta(days=6-i)
        
        sample_pnl.append({
            "day": day.strftime("%b %d"),
            "dailyPnL": daily_pnl,
            "cumulativePnL": cumulative,
            "color": "#4caf50" if daily_pnl >= 0 else "#f44336"
        })
    
    return {
        "status": "success",
        "data_source": "backend_api_test",
        "prices": sample_prices,
        "orders": sample_orders, 
        "pnl_history": sample_pnl,
        "kpis": {
            "total_pnl": cumulative,
            "today_pnl": sample_pnl[-1]["dailyPnL"],
            "filled_orders": 2,
            "total_orders": 2,
            "win_rate": 100
        },
        "session": {
            "user_id": "demo_user",
            "capital": {
                "starting_capital": 10000.0,
                "current_capital": 10000.0 + cumulative
            },
            "session_state": "post_11am",
            "trading_permissions": {
                "da_orders_enabled": False,
                "rt_orders_enabled": True
            }
        }
    }
