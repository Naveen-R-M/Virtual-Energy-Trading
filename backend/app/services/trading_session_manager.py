"""
Trading Session Manager Service
Handles trading session lifecycle, capital tracking, and daily resets
"""

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os
import pytz
from ..models import (
    TradingSession, UserCapital, DailyPnLSummary, TradingOrder, OrderFill,
    SessionState, OrderStatus, MarketType,
    get_or_create_user_capital, get_or_create_trading_session, calculate_session_state
)

logger = logging.getLogger(__name__)

class TradingSessionManager:
    """
    Manages trading sessions, capital tracking, and daily resets
    
    Key Features:
    1. Initialize new traders with starting capital
    2. Handle daily session lifecycle and state transitions
    3. Manage DA order cutoffs and carryover positions
    4. Track daily P&L and reset counters
    5. Update capital based on realized/unrealized P&L
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.starting_capital = float(os.getenv("SIM_STARTING_CAPITAL", "10000.0"))
        
    def initialize_trader_session(self, user_id: str, trading_date: Optional[datetime] = None) -> Dict:
        """
        Initialize or get existing trader session for the day
        This is called when trader first launches the simulator
        """
        try:
            if trading_date is None:
                trading_date = datetime.utcnow()
            
            # Get or create user capital record
            user_capital = get_or_create_user_capital(
                self.session, user_id, self.starting_capital
            )
            
            # Get or create today's trading session
            trading_session = get_or_create_trading_session(
                self.session, user_id, trading_date, self.starting_capital
            )
            
            # Update session state based on current time
            self.update_session_state(trading_session)
            
            # Handle carryover DA positions from previous trading day
            carryover_positions = self.load_carryover_da_positions(user_id, trading_date)
            
            # Calculate current unrealized P&L
            unrealized_pnl = self.calculate_current_unrealized_pnl(user_id, trading_date)
            
            # Update session with current data
            trading_session.daily_unrealized_pnl = unrealized_pnl
            trading_session.carryover_da_positions = len(carryover_positions)
            trading_session.updated_at = datetime.utcnow()
            
            self.session.add(trading_session)
            self.session.commit()
            
            logger.info(
                f"Trader session initialized: user_id={user_id}, "
                f"capital=${user_capital.current_capital:.2f}, "
                f"session_state={trading_session.session_state.value}, "
                f"carryover_positions={len(carryover_positions)}"
            )
            
            return {
                "user_id": user_id,
                "trading_date": trading_date.strftime("%Y-%m-%d"),
                "session_state": trading_session.session_state.value,
                "capital": {
                    "starting_capital": user_capital.starting_capital,
                    "current_capital": user_capital.current_capital,
                    "daily_starting_capital": trading_session.starting_daily_capital,
                    "daily_current_capital": trading_session.current_daily_capital
                },
                "pnl": {
                    "total_realized_pnl": user_capital.total_realized_pnl,
                    "total_unrealized_pnl": unrealized_pnl,
                    "daily_realized_pnl": trading_session.daily_realized_pnl,
                    "daily_unrealized_pnl": trading_session.daily_unrealized_pnl,
                    "daily_gross_pnl": trading_session.daily_realized_pnl + unrealized_pnl
                },
                "trading_permissions": {
                    "da_orders_enabled": trading_session.da_orders_enabled,
                    "rt_orders_enabled": trading_session.rt_orders_enabled
                },
                "positions": {
                    "open_da_positions": trading_session.open_da_positions,
                    "open_rt_positions": trading_session.open_rt_positions,
                    "carryover_da_positions": len(carryover_positions)
                },
                "session_info": {
                    "da_cutoff_time": trading_session.da_cutoff_time.isoformat() if trading_session.da_cutoff_time else None,
                    "market_open_time": trading_session.market_open_time.isoformat() if trading_session.market_open_time else None,
                    "daily_trades": trading_session.daily_trades,
                    "daily_volume_mwh": trading_session.daily_volume_mwh
                }
            }
            
        except Exception as e:
            logger.error(f"Error initializing trader session for {user_id}: {e}")
            self.session.rollback()
            raise
    
    def update_session_state(self, trading_session: TradingSession) -> None:
        """Update session state based on current time"""
        current_time = datetime.utcnow()
        session_state, da_enabled, rt_enabled = calculate_session_state(current_time)
        
        # Update session state
        old_state = trading_session.session_state
        trading_session.session_state = session_state
        trading_session.da_orders_enabled = da_enabled
        trading_session.rt_orders_enabled = rt_enabled
        
        # Set timing markers when state changes
        if old_state != session_state:
            et = pytz.timezone('US/Eastern')
            et_time = current_time.astimezone(et)
            
            if session_state == SessionState.PRE_11AM and old_state == SessionState.PRE_MARKET:
                trading_session.market_open_time = current_time
                
            elif session_state == SessionState.POST_11AM and old_state == SessionState.PRE_11AM:
                trading_session.da_cutoff_time = current_time
                
            elif session_state == SessionState.MARKET_CLOSE:
                trading_session.market_close_time = current_time
                
            logger.info(
                f"Session state changed: {old_state.value} -> {session_state.value} "
                f"at {et_time.strftime('%H:%M %Z')}"
            )
    
    def load_carryover_da_positions(self, user_id: str, trading_date: datetime) -> List[Dict]:
        """Load DA positions from previous day that are delivering today"""
        try:
            # Yesterday's date
            yesterday = trading_date - timedelta(days=1)
            yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Today's delivery window
            today_start = trading_date.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # Find filled DA orders from yesterday that deliver today
            carryover_orders = self.session.exec(
                select(TradingOrder).where(
                    TradingOrder.user_id == user_id,
                    TradingOrder.market == MarketType.DAY_AHEAD,
                    TradingOrder.status == OrderStatus.FILLED,
                    TradingOrder.hour_start_utc >= today_start,
                    TradingOrder.hour_start_utc < today_end,
                    TradingOrder.created_at >= yesterday_start,
                    TradingOrder.created_at < today_start
                )
            ).all()
            
            carryover_positions = []
            for order in carryover_orders:
                position = {
                    "order_id": order.order_id,
                    "hour_start": order.hour_start_utc.isoformat(),
                    "side": order.side.value,
                    "quantity_mwh": order.quantity_mwh,
                    "da_fill_price": order.filled_price,
                    "node": order.node,
                    "created_at": order.created_at.isoformat()
                }
                carryover_positions.append(position)
            
            if carryover_positions:
                logger.info(
                    f"Loaded {len(carryover_positions)} carryover DA positions for {user_id} "
                    f"on {trading_date.date()}"
                )
            
            return carryover_positions
            
        except Exception as e:
            logger.error(f"Error loading carryover DA positions: {e}")
            return []
    
    def calculate_current_unrealized_pnl(self, user_id: str, trading_date: datetime) -> float:
        """Calculate current unrealized P&L for all open positions"""
        try:
            # This would integrate with your existing P&L calculation service
            # For now, return 0.0 as placeholder
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating unrealized P&L: {e}")
            return 0.0
    
    def update_daily_pnl(self, user_id: str, trading_date: datetime, realized_pnl: float, 
                         unrealized_pnl: float) -> None:
        """Update daily P&L tracking"""
        try:
            normalized_date = trading_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get trading session
            trading_session = self.session.exec(
                select(TradingSession).where(
                    TradingSession.user_id == user_id,
                    TradingSession.trading_date == normalized_date
                )
            ).first()
            
            if not trading_session:
                logger.warning(f"No trading session found for {user_id} on {normalized_date.date()}")
                return
            
            # Update daily P&L
            trading_session.daily_realized_pnl += realized_pnl
            trading_session.daily_unrealized_pnl = unrealized_pnl
            trading_session.daily_gross_pnl = trading_session.daily_realized_pnl + unrealized_pnl
            trading_session.updated_at = datetime.utcnow()
            
            self.session.add(trading_session)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating daily P&L: {e}")
            self.session.rollback()
    
    def update_trade_metrics(self, user_id: str, trading_date: datetime, trade_volume: float) -> None:
        """Update daily trading metrics when new trades occur"""
        try:
            normalized_date = trading_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get trading session
            trading_session = self.session.exec(
                select(TradingSession).where(
                    TradingSession.user_id == user_id,
                    TradingSession.trading_date == normalized_date
                )
            ).first()
            
            if trading_session:
                trading_session.daily_trades += 1
                trading_session.daily_volume_mwh += trade_volume
                trading_session.updated_at = datetime.utcnow()
                
                self.session.add(trading_session)
                self.session.commit()
                
        except Exception as e:
            logger.error(f"Error updating trade metrics: {e}")
    
    def get_session_summary(self, user_id: str, trading_date: Optional[datetime] = None) -> Dict:
        """Get comprehensive session summary"""
        try:
            if trading_date is None:
                trading_date = datetime.utcnow()
                
            normalized_date = trading_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get user capital
            user_capital = self.session.exec(
                select(UserCapital).where(UserCapital.user_id == user_id)
            ).first()
            
            # Get trading session
            trading_session = self.session.exec(
                select(TradingSession).where(
                    TradingSession.user_id == user_id,
                    TradingSession.trading_date == normalized_date
                )
            ).first()
            
            if not user_capital or not trading_session:
                # Initialize if doesn't exist
                return self.initialize_trader_session(user_id, trading_date)
            
            # Update session state
            self.update_session_state(trading_session)
            self.session.add(trading_session)
            self.session.commit()
            
            return {
                "user_id": user_id,
                "trading_date": normalized_date.strftime("%Y-%m-%d"),
                "session_state": trading_session.session_state.value,
                "capital": {
                    "starting_capital": user_capital.starting_capital,
                    "current_capital": user_capital.current_capital,
                    "daily_starting_capital": trading_session.starting_daily_capital,
                    "daily_current_capital": trading_session.current_daily_capital
                },
                "pnl": {
                    "total_realized_pnl": user_capital.total_realized_pnl,
                    "total_unrealized_pnl": user_capital.total_unrealized_pnl,
                    "daily_realized_pnl": trading_session.daily_realized_pnl,
                    "daily_unrealized_pnl": trading_session.daily_unrealized_pnl,
                    "daily_gross_pnl": trading_session.daily_gross_pnl
                },
                "trading_permissions": {
                    "da_orders_enabled": trading_session.da_orders_enabled,
                    "rt_orders_enabled": trading_session.rt_orders_enabled
                },
                "positions": {
                    "open_da_positions": trading_session.open_da_positions,
                    "open_rt_positions": trading_session.open_rt_positions,
                    "carryover_da_positions": trading_session.carryover_da_positions
                },
                "metrics": {
                    "daily_trades": trading_session.daily_trades,
                    "daily_volume_mwh": trading_session.daily_volume_mwh,
                    "total_trades": user_capital.total_trades,
                    "winning_trades": user_capital.winning_trades,
                    "max_drawdown": user_capital.max_drawdown
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary for {user_id}: {e}")
            raise
    
    def is_trading_allowed(self, user_id: str, market_type: MarketType, 
                          trading_date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if trading is allowed for the user in the specified market"""
        try:
            if trading_date is None:
                trading_date = datetime.utcnow()
                
            session_summary = self.get_session_summary(user_id, trading_date)
            permissions = session_summary["trading_permissions"]
            
            if market_type == MarketType.DAY_AHEAD:
                if not permissions["da_orders_enabled"]:
                    return False, "Day-Ahead orders are not allowed after 11:00 AM ET"
                    
            elif market_type == MarketType.REAL_TIME:
                if not permissions["rt_orders_enabled"]:
                    return False, "Real-Time orders are not allowed outside market hours"
            
            return True, "Trading is allowed"
            
        except Exception as e:
            logger.error(f"Error checking trading permissions: {e}")
            return False, f"Error checking permissions: {e}"
    
    def get_market_state_info(self, trading_date: Optional[datetime] = None) -> Dict:
        """Get current market state information"""
        try:
            if trading_date is None:
                trading_date = datetime.utcnow()
                
            session_state, da_enabled, rt_enabled = calculate_session_state(trading_date)
            
            et = pytz.timezone('US/Eastern')
            et_time = trading_date.astimezone(et)
            
            # Calculate time until DA cutoff
            da_cutoff = et_time.replace(hour=11, minute=0, second=0, microsecond=0)
            if et_time < da_cutoff:
                time_until_cutoff = (da_cutoff - et_time).total_seconds() / 60  # minutes
            else:
                time_until_cutoff = 0
                
            return {
                "current_time": trading_date.isoformat(),
                "current_time_et": et_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "session_state": session_state.value,
                "trading_permissions": {
                    "da_orders_enabled": da_enabled,
                    "rt_orders_enabled": rt_enabled
                },
                "market_timing": {
                    "da_cutoff_time": da_cutoff.strftime("%H:%M %Z"),
                    "time_until_da_cutoff_minutes": max(0, time_until_cutoff),
                    "is_pre_11am": session_state == SessionState.PRE_11AM,
                    "is_post_11am": session_state == SessionState.POST_11AM
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting market state info: {e}")
            raise
