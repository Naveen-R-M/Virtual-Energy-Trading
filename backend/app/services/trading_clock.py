# PJM Trading Clock Service - DST-Safe Trading Day State Management
# Implements PJM-accurate trading-day logic with proper Eastern Time handling

from datetime import datetime, time
from enum import Enum
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo
import logging
import os

logger = logging.getLogger(__name__)

class TradingState(Enum):
    """PJM Trading Day States"""
    PRE_MARKET = "PRE_MARKET"      # Midnight to market open
    PRE_11AM = "PRE_11AM"          # Market open, DA orders allowed
    POST_11AM = "POST_11AM"        # DA closed, RT only
    END_OF_DAY = "END_OF_DAY"      # Market closing, settle positions

class TradingClock:
    """
    PJM-compliant trading clock with DST-safe timezone handling
    
    State transitions:
    - 00:00:00 ET → PRE_MARKET
    - Market open < 11:00 ET → PRE_11AM (DA + RT allowed)
    - 11:00:00 ET → POST_11AM (DA disabled, RT only)
    - 23:59:59 ET → END_OF_DAY (close RT, persist ledgers)
    """
    
    def __init__(self):
        self.timezone = ZoneInfo("America/New_York")
        self.feature_enabled = self._get_feature_flag()
        
        # Configurable cutoff times
        self.da_cutoff_hour = int(os.getenv("ORDER_CUTOFF_HOUR", "11"))
        self.da_cutoff_minute = int(os.getenv("ORDER_CUTOFF_MINUTE", "0"))
        self.da_cutoff_second = int(os.getenv("ORDER_CUTOFF_SECOND", "0"))
        
        # Market session times
        self.market_open_hour = int(os.getenv("MARKET_OPEN_HOUR", "0"))  # Midnight
        self.market_close_hour = int(os.getenv("MARKET_CLOSE_HOUR", "23"))
        self.market_close_minute = int(os.getenv("MARKET_CLOSE_MINUTE", "59"))
        
    def _get_feature_flag(self) -> bool:
        """Get PJM state machine feature flag"""
        return os.getenv("PJM_STATE_MACHINE_ENABLED", "true").lower() == "true"
    
    def get_trading_state(self, now_utc: Optional[datetime] = None) -> TradingState:
        """
        Get current trading state (DST-safe)
        
        Args:
            now_utc: Optional current time in UTC (for testing)
            
        Returns:
            TradingState enum value
        """
        if not self.feature_enabled:
            # Legacy behavior - always allow trading
            return TradingState.PRE_11AM
        
        if now_utc is None:
            now_utc = datetime.utcnow()
        
        # Convert to Eastern Time (handles DST automatically)
        now_et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
        current_time = now_et.time()
        
        # Define cutoff times
        da_cutoff = time(self.da_cutoff_hour, self.da_cutoff_minute, self.da_cutoff_second)
        market_close = time(self.market_close_hour, self.market_close_minute, 59)
        market_open = time(self.market_open_hour, 0, 0)
        
        # State machine logic
        if current_time >= market_open and current_time < da_cutoff:
            return TradingState.PRE_11AM
        elif current_time >= da_cutoff and current_time <= market_close:
            return TradingState.POST_11AM
        else:
            return TradingState.END_OF_DAY
    
    def get_trading_info(self, now_utc: Optional[datetime] = None) -> Dict:
        """
        Get comprehensive trading state information
        
        Returns:
            Dictionary with trading state, permissions, and timing info
        """
        if now_utc is None:
            now_utc = datetime.utcnow()
            
        now_et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
        state = self.get_trading_state(now_utc)
        
        # Calculate time to next state transition
        next_transition = self._get_next_transition_time(now_et)
        
        return {
            "state": state.value,
            "timestamp_utc": now_utc.isoformat(),
            "timestamp_et": now_et.isoformat(), 
            "timezone": str(self.timezone),
            "permissions": self._get_permissions(state),
            "next_transition": next_transition,
            "feature_enabled": self.feature_enabled,
            "cutoff_config": {
                "da_cutoff_hour": self.da_cutoff_hour,
                "da_cutoff_minute": self.da_cutoff_minute,
                "market_close_hour": self.market_close_hour,
                "market_close_minute": self.market_close_minute
            }
        }
    
    def _get_permissions(self, state: TradingState) -> Dict[str, bool]:
        """Get trading permissions for current state"""
        if not self.feature_enabled:
            return {"da_orders": True, "rt_orders": True}
            
        permissions = {
            TradingState.PRE_MARKET: {"da_orders": False, "rt_orders": False},
            TradingState.PRE_11AM: {"da_orders": True, "rt_orders": True},
            TradingState.POST_11AM: {"da_orders": False, "rt_orders": True},
            TradingState.END_OF_DAY: {"da_orders": False, "rt_orders": False}
        }
        
        return permissions.get(state, {"da_orders": False, "rt_orders": False})
    
    def _get_next_transition_time(self, now_et: datetime) -> Dict:
        """Calculate time until next state transition"""
        current_time = now_et.time()
        current_date = now_et.date()
        
        # Define transition times
        da_cutoff = time(self.da_cutoff_hour, self.da_cutoff_minute, self.da_cutoff_second)
        market_close = time(self.market_close_hour, self.market_close_minute, 59)
        market_open = time(0, 0, 0)
        
        # Find next transition
        next_transition_time = None
        next_state = None
        
        if current_time < da_cutoff:
            next_transition_time = datetime.combine(current_date, da_cutoff).replace(tzinfo=self.timezone)
            next_state = TradingState.POST_11AM
        elif current_time < market_close:
            next_transition_time = datetime.combine(current_date, market_close).replace(tzinfo=self.timezone)
            next_state = TradingState.END_OF_DAY
        else:
            # Next day market open
            from datetime import timedelta
            next_date = current_date + timedelta(days=1)
            next_transition_time = datetime.combine(next_date, market_open).replace(tzinfo=self.timezone)
            next_state = TradingState.PRE_11AM
        
        # Calculate seconds until transition
        seconds_until = (next_transition_time - now_et).total_seconds()
        
        return {
            "next_state": next_state.value if next_state else None,
            "next_transition_et": next_transition_time.isoformat(),
            "seconds_until": int(seconds_until),
            "human_readable": self._format_duration(seconds_until)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 0:
            return "Past due"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def is_da_allowed(self, now_utc: Optional[datetime] = None) -> bool:
        """Check if DA orders are currently allowed"""
        state = self.get_trading_state(now_utc)
        permissions = self._get_permissions(state)
        return permissions["da_orders"]
    
    def is_rt_allowed(self, now_utc: Optional[datetime] = None) -> bool:
        """Check if RT orders are currently allowed"""
        state = self.get_trading_state(now_utc)
        permissions = self._get_permissions(state)
        return permissions["rt_orders"]
    
    def get_da_cutoff_message(self, now_utc: Optional[datetime] = None) -> Optional[str]:
        """Get user-friendly message about DA cutoff status"""
        if not self.feature_enabled:
            return None
            
        state = self.get_trading_state(now_utc)
        
        if state == TradingState.PRE_11AM:
            info = self.get_trading_info(now_utc)
            duration = info["next_transition"]["human_readable"]
            return f"DA orders close in {duration}"
        elif state == TradingState.POST_11AM:
            return f"DA orders closed until tomorrow {self.da_cutoff_hour:02d}:00 ET"
        else:
            return "Market closed - DA orders unavailable"

# Global instance for use across the application
trading_clock = TradingClock()

# Convenience functions for backward compatibility
def get_trading_state(now_utc: Optional[datetime] = None) -> TradingState:
    """Get current trading state - DST safe"""
    return trading_clock.get_trading_state(now_utc)

def is_da_cutoff_passed(now_utc: Optional[datetime] = None) -> bool:
    """Check if DA cutoff has passed (legacy compatibility)"""
    return not trading_clock.is_da_allowed(now_utc)

def get_market_permissions(now_utc: Optional[datetime] = None) -> Dict[str, bool]:
    """Get current market permissions"""
    state = trading_clock.get_trading_state(now_utc)
    return trading_clock._get_permissions(state)