"""
P&L API Routes for Virtual Energy Trading Platform
Handles P&L calculation and simulation for both markets
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import datetime, timedelta
from typing import Optional
from ..database import get_session
from ..services.pnl_calculator import PnLCalculator

router = APIRouter(prefix="/api/pnl", tags=["pnl"])

@router.post("/simulate/day-ahead/{date}")
async def simulate_day_ahead_pnl(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Simulate P&L for Day-Ahead orders offset against Real-Time prices
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        calculator = PnLCalculator(session)
        
        pnl_data = await calculator.calculate_da_pnl(target_date, node)
        
        return pnl_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating DA P&L: {e}")

@router.post("/simulate/real-time/{date}")
async def simulate_real_time_pnl(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Calculate P&L for Real-Time orders (immediate settlement)
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        calculator = PnLCalculator(session)
        
        pnl_data = await calculator.calculate_rt_pnl(target_date, node)
        
        return pnl_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating RT P&L: {e}")

@router.get("/portfolio/{date}")
async def get_portfolio_pnl(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Get combined portfolio P&L for both Day-Ahead and Real-Time markets
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        calculator = PnLCalculator(session)
        
        portfolio_pnl = await calculator.calculate_portfolio_pnl(target_date, node)
        
        return portfolio_pnl
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting portfolio P&L: {e}")

@router.get("/analytics")
async def get_performance_analytics(
    node: str = Query(default="PJM_RTO", description="Grid node"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    session: Session = Depends(get_session)
):
    """
    Get comprehensive performance analytics and metrics
    """
    try:
        calculator = PnLCalculator(session)
        analytics = await calculator.get_performance_analytics(node, days)
        
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance analytics: {e}")

@router.get("/order/{order_id}")
async def get_order_pnl(
    order_id: str,
    session: Session = Depends(get_session)
):
    """
    Get detailed P&L calculation for a specific order
    """
    try:
        calculator = PnLCalculator(session)
        order_pnl = await calculator.calculate_order_pnl(order_id)
        
        if not order_pnl:
            raise HTTPException(status_code=404, detail="Order not found or not filled")
        
        return order_pnl
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating order P&L: {e}")

@router.post("/save/{date}")
async def save_daily_pnl(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Save calculated P&L to database for historical tracking
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        calculator = PnLCalculator(session)
        
        await calculator.save_pnl_record(target_date, node, user_id)
        
        return {
            "message": "P&L record saved successfully",
            "date": date,
            "node": node,
            "user_id": user_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving P&L record: {e}")

@router.get("/history")
async def get_pnl_history(
    node: str = Query(default="PJM_RTO", description="Grid node"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get historical P&L records for trend analysis
    """
    try:
        # Set default date range if not provided
        if not end_date:
            end_dt = datetime.utcnow()
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if not start_date:
            start_dt = end_dt - timedelta(days=30)
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        
        calculator = PnLCalculator(session)
        history_data = await calculator.calculate_multi_day_pnl(start_dt, end_dt, node)
        
        return history_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting P&L history: {e}")
