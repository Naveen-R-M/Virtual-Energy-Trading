"""
Trading Session API Routes
Handles session management, capital tracking, and daily resets
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, Dict
from pydantic import BaseModel
from ..database import get_session
from ..services.trading_session_manager import TradingSessionManager
from ..models import MarketType, UserCapital
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])

class SessionResponse(BaseModel):
    """Trading session response model"""
    status: str
    message: str
    data: Optional[Dict] = None

@router.post("/initialize")
async def initialize_session(
    user_id: str = Query(default="demo_user", description="User ID"),
    trading_date: Optional[str] = Query(default=None, description="Trading date (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
) -> SessionResponse:
    """
    Initialize or resume trading session for a user
    This is the main entry point when simulator starts
    """
    try:
        session_manager = TradingSessionManager(session)
        
        # Parse trading date if provided
        parsed_date = None
        if trading_date:
            parsed_date = datetime.strptime(trading_date, "%Y-%m-%d")
        
        # Initialize trader session
        session_data = session_manager.initialize_trader_session(user_id, parsed_date)
        
        return SessionResponse(
            status="success",
            message="Trading session initialized successfully",
            data=session_data
        )
        
    except Exception as e:
        logger.error(f"Error initializing session for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing session: {e}")

@router.get("/summary")
async def get_session_summary(
    user_id: str = Query(default="demo_user", description="User ID"),
    trading_date: Optional[str] = Query(default=None, description="Trading date (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
) -> SessionResponse:
    """
    Get comprehensive session summary for a user
    """
    try:
        session_manager = TradingSessionManager(session)
        
        # Parse trading date if provided
        parsed_date = None
        if trading_date:
            parsed_date = datetime.strptime(trading_date, "%Y-%m-%d")
        
        summary = session_manager.get_session_summary(user_id, parsed_date)
        
        return SessionResponse(
            status="success",
            message="Session summary retrieved successfully",
            data=summary
        )
        
    except Exception as e:
        logger.error(f"Error getting session summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting session summary: {e}")

@router.get("/market-state")
async def get_market_state(
    session: Session = Depends(get_session)
) -> Dict:
    """
    Get current market state and trading permissions
    """
    try:
        session_manager = TradingSessionManager(session)
        market_state = session_manager.get_market_state_info()
        
        return {
            "status": "success",
            "market_state": market_state
        }
        
    except Exception as e:
        logger.error(f"Error getting market state: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market state: {e}")

@router.get("/trading-permissions")
async def check_trading_permissions(
    market: MarketType = Query(..., description="Market type to check"),
    user_id: str = Query(default="demo_user", description="User ID"),
    trading_date: Optional[str] = Query(default=None, description="Trading date (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
) -> Dict:
    """
    Check if trading is allowed for user in specified market
    """
    try:
        session_manager = TradingSessionManager(session)
        
        # Parse trading date if provided
        parsed_date = None
        if trading_date:
            parsed_date = datetime.strptime(trading_date, "%Y-%m-%d")
        
        is_allowed, reason = session_manager.is_trading_allowed(user_id, market, parsed_date)
        
        return {
            "status": "success",
            "trading_allowed": is_allowed,
            "reason": reason,
            "market": market.value,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error checking trading permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking permissions: {e}")

@router.get("/capital")
async def get_capital_summary(
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
) -> Dict:
    """
    Get detailed capital and P&L summary for user
    """
    try:
        user_capital = session.exec(
            select(UserCapital).where(UserCapital.user_id == user_id)
        ).first()
        
        if not user_capital:
            # Initialize user if doesn't exist
            session_manager = TradingSessionManager(session)
            session_data = session_manager.initialize_trader_session(user_id)
            return {
                "status": "initialized",
                "message": "User capital initialized",
                "capital": session_data["capital"]
            }
        
        return {
            "status": "success",
            "capital": {
                "starting_capital": user_capital.starting_capital,
                "current_capital": user_capital.current_capital,
                "total_realized_pnl": user_capital.total_realized_pnl,
                "total_unrealized_pnl": user_capital.total_unrealized_pnl,
                "net_pnl": user_capital.total_realized_pnl + user_capital.total_unrealized_pnl
            },
            "performance": {
                "total_trades": user_capital.total_trades,
                "winning_trades": user_capital.winning_trades,
                "win_rate": (user_capital.winning_trades / max(1, user_capital.total_trades)) * 100,
                "max_drawdown": user_capital.max_drawdown,
                "sharpe_ratio": user_capital.sharpe_ratio
            },
            "session_info": {
                "session_count": user_capital.session_count,
                "last_trading_date": user_capital.last_trading_date.strftime("%Y-%m-%d")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting capital summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting capital summary: {e}")

@router.get("/status")
async def get_session_status() -> Dict:
    """Get trading session system status and configuration"""
    import os
    
    return {
        "status": "operational",
        "configuration": {
            "starting_capital": float(os.getenv("SIM_STARTING_CAPITAL", "10000.0")),
            "daily_reset_enabled": os.getenv("SIM_DAILY_RESET_ENABLED", "true").lower() == "true",
            "capital_persistence": os.getenv("SIM_CAPITAL_PERSISTENCE", "true").lower() == "true"
        },
        "features": [
            "Starting capital management",
            "Daily P&L tracking", 
            "Session state management",
            "DA order cutoff enforcement",
            "Carryover position handling",
            "Real-time capital updates"
        ],
        "session_states": [
            "pre_market", "pre_11am", "post_11am", 
            "market_close", "settlement"
        ]
    }
