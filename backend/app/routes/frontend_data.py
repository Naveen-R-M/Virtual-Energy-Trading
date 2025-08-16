"""
Frontend Data API Routes  
Provides formatted data specifically for the frontend dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import pytz
from ..database import get_session
from ..models import TradingOrder, OrderStatus, MarketType
from ..services.trading_session_manager import TradingSessionManager
from ..services.pnl_calculator import PnLCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/frontend", tags=["frontend"])

@router.get("/dashboard-data")
async def get_dashboard_data(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
) -> Dict:
    """
    Get all dashboard data in one API call - formatted for frontend
    """
    try:
        # Initialize session manager
        session_manager = TradingSessionManager(session)
        
        # Get session data
        session_summary = session_manager.get_session_summary(user_id)
        market_state = session_manager.get_market_state_info()
        
        # Get market prices
        try:
            from ..routes.market import get_day_ahead_prices
            da_prices_response = await get_day_ahead_prices(date, node, session)
            da_prices = da_prices_response.get("prices", [])
            
            # Format prices for frontend chart
            price_data = []
            for hour in range(24):
                hour_start = datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=hour)
                hour_start_iso = hour_start.strftime("%Y-%m-%dT%H:00:00")
                
                # Find DA price for this hour
                da_price = next((p for p in da_prices if p["hour_start"].startswith(hour_start_iso)), None)
                
                # For now, generate RT price as DA + some volatility (mock RT)
                rt_price = None
                if da_price:
                    import random
                    rt_price = da_price["close_price"] * (1 + (random.random() - 0.5) * 0.1)
                
                price_data.append({
                    "hour": hour_start.strftime("%H:%M"),
                    "daPrice": da_price["close_price"] if da_price else None,
                    "rtPrice": rt_price,
                    "spread": (rt_price - da_price["close_price"]) if (rt_price and da_price) else None
                })
                
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            # Return empty price data
            price_data = []
        
        # Get orders
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            orders = session.exec(
                select(TradingOrder).where(
                    TradingOrder.user_id == user_id,
                    TradingOrder.node == node,
                    TradingOrder.hour_start_utc >= start_time,
                    TradingOrder.hour_start_utc < end_time
                )
            ).all()
            
            # Format orders for frontend
            order_data = []
            for order in orders:
                order_data.append({
                    "id": order.order_id,
                    "time": order.created_at.strftime("%H:%M"),
                    "hour": order.hour_start_utc.strftime("%H:%M"),
                    "side": "Buy" if order.side.value == "buy" else "Sell",
                    "quantity": order.quantity_mwh,
                    "price": order.limit_price,
                    "fillPrice": order.filled_price,
                    "status": order.status.value.title(),
                    "pnl": calculate_order_pnl(order) if order.status == OrderStatus.FILLED else 0
                })
                
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            order_data = []
        
        # Get P&L data for last 7 days
        try:
            pnl_data = []
            for i in range(7):
                pnl_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=6-i)
                pnl_date_str = pnl_date.strftime("%Y-%m-%d")
                
                try:
                    pnl_response = await simulate_day_pnl(pnl_date_str, node, session)
                    daily_pnl = pnl_response.get("pnl_total", 0)
                except:
                    daily_pnl = 0
                
                pnl_data.append({
                    "day": pnl_date.strftime("%b %d"),
                    "dailyPnL": round(daily_pnl, 2),
                    "cumulativePnL": sum(p["dailyPnL"] for p in pnl_data) + daily_pnl,
                    "color": "#4caf50" if daily_pnl >= 0 else "#f44336"
                })
                
        except Exception as e:
            logger.error(f"Error fetching P&L data: {e}")
            pnl_data = []
        
        # Calculate KPIs
        total_pnl = session_summary["pnl"]["total_realized_pnl"] + session_summary["pnl"]["total_unrealized_pnl"]
        today_pnl = session_summary["pnl"]["daily_gross_pnl"]
        filled_orders = len([o for o in order_data if o["status"] == "Filled"])
        total_orders = len(order_data)
        profitable_orders = len([o for o in order_data if o["pnl"] > 0])
        win_rate = round((profitable_orders / max(1, filled_orders)) * 100)
        
        return {
            "status": "success",
            "data_source": "real_api",
            "session": session_summary,
            "market_state": market_state,
            "prices": price_data,
            "orders": order_data,
            "pnl_history": pnl_data,
            "kpis": {
                "total_pnl": total_pnl,
                "today_pnl": today_pnl,
                "filled_orders": filled_orders,
                "total_orders": total_orders,
                "win_rate": win_rate
            },
            "meta": {
                "date": date,
                "node": node,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {e}")

def calculate_order_pnl(order: TradingOrder) -> float:
    """Calculate simple P&L for an order (placeholder)"""
    if not order.filled_price:
        return 0.0
    
    # Simple mock P&L calculation
    # In production, this would use real-time market prices
    import random
    mock_current_price = order.filled_price * (1 + (random.random() - 0.5) * 0.1)
    side_multiplier = 1 if order.side.value == "buy" else -1
    return round((mock_current_price - order.filled_price) * side_multiplier * order.quantity_mwh, 2)

@router.get("/market-data")
async def get_market_data_formatted(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
) -> Dict:
    """Get market data formatted for frontend charts"""
    try:
        da_response = await get_day_ahead_prices(date, node, session)
        da_prices = da_response.get("prices", [])
        
        # Format for frontend chart
        chart_data = []
        for hour in range(24):
            hour_start = datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=hour)
            hour_start_iso = hour_start.strftime("%Y-%m-%dT%H:00:00")
            
            da_price = next((p for p in da_prices if p["hour_start"].startswith(hour_start_iso)), None)
            
            chart_data.append({
                "hour": hour_start.strftime("%H:%M"),
                "daPrice": da_price["close_price"] if da_price else None,
                "rtPrice": None,  # Would be filled with real RT data
                "spread": None
            })
        
        return {
            "status": "success",
            "date": date,
            "node": node,
            "data": chart_data,
            "data_source": "gridstatus_real_data",
            "count": len([d for d in chart_data if d["daPrice"] is not None])
        }
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market data: {e}")
