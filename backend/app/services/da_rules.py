# PJM Day-Ahead Rules Enforcement Service
# Server-side validation for DA order submission rules

from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlmodel import Session, select
from ..models import TradingOrder, MarketType, OrderStatus
from .trading_clock import trading_clock, TradingState
import logging
import os

logger = logging.getLogger(__name__)

class DAOrderValidationError(Exception):
    """Raised when DA order validation fails"""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class DAOrderRulesEngine:
    """
    PJM Day-Ahead order rules enforcement engine
    
    Rules enforced:
    1. DA orders only accepted before 11:00:00 ET
    2. Maximum 10 DA orders per hour per user
    3. DA orders for tomorrow's delivery only (after 11am)
    4. Proper timezone handling for edge cases
    """
    
    def __init__(self):
        self.max_da_orders_per_hour = int(os.getenv("MAX_ORDERS_PER_HOUR", "10"))
        self.feature_enabled = os.getenv("PJM_STATE_MACHINE_ENABLED", "true").lower() == "true"
    
    def validate_da_order_submission(
        self,
        session: Session,
        user_id: str,
        node: str,
        hour_start_utc: datetime,
        now_utc: Optional[datetime] = None
    ) -> Dict:
        """
        Comprehensive DA order validation
        
        Args:
            session: Database session
            user_id: User submitting the order
            node: PJM node for the order
            hour_start_utc: Delivery hour in UTC
            now_utc: Current time (for testing)
            
        Returns:
            Dict with validation result and details
            
        Raises:
            DAOrderValidationError: If validation fails
        """
        if now_utc is None:
            now_utc = datetime.utcnow()
        
        # Get trading state
        trading_info = trading_clock.get_trading_info(now_utc)
        state = TradingState(trading_info["state"])
        
        validation_result = {
            "valid": True,
            "trading_state": state.value,
            "permissions": trading_info["permissions"],
            "checks": [],
            "warnings": []
        }
        
        # Check 1: Feature flag (if disabled, use legacy behavior)
        if not self.feature_enabled:
            validation_result["checks"].append({
                "check": "feature_flag",
                "status": "pass",
                "message": "PJM state machine disabled, using legacy validation"
            })
            return self._legacy_validation(session, user_id, node, hour_start_utc, now_utc)
        
        # Check 2: Trading state allows DA orders
        da_allowed = trading_info["permissions"]["da_orders"]
        if not da_allowed:
            cutoff_message = trading_clock.get_da_cutoff_message(now_utc)
            validation_result["checks"].append({
                "check": "trading_state",
                "status": "fail",
                "message": cutoff_message or "DA orders not allowed in current state"
            })
            validation_result["valid"] = False
            
            raise DAOrderValidationError(
                f"DA orders are closed. {cutoff_message}",
                "DA_MARKET_CLOSED"
            )
        
        validation_result["checks"].append({
            "check": "trading_state", 
            "status": "pass",
            "message": f"DA orders allowed in {state.value} state"
        })
        
        # Check 3: Edge case timing validation (critical 11:00:00.000 boundary)
        edge_case_result = self._validate_edge_case_timing(now_utc)
        validation_result["checks"].append(edge_case_result)
        
        if edge_case_result["status"] == "fail":
            validation_result["valid"] = False
            raise DAOrderValidationError(
                edge_case_result["message"],
                "EDGE_CASE_TIMING"
            )
        
        # Check 4: Hour limit validation
        hour_limit_result = self._validate_hour_limits(
            session, user_id, node, hour_start_utc
        )
        validation_result["checks"].append(hour_limit_result)
        
        if hour_limit_result["status"] == "fail":
            validation_result["valid"] = False
            raise DAOrderValidationError(
                hour_limit_result["message"],
                "HOUR_LIMIT_EXCEEDED"
            )
        
        # Check 5: Delivery date validation (tomorrow's delivery after cutoff)
        delivery_validation = self._validate_delivery_date(hour_start_utc, now_utc)
        validation_result["checks"].append(delivery_validation)
        
        if delivery_validation["status"] == "warning":
            validation_result["warnings"].append(delivery_validation["message"])
        
        logger.info(f"DA order validation passed for user {user_id}, node {node}, hour {hour_start_utc}")
        return validation_result
    
    def _validate_edge_case_timing(self, now_utc: datetime) -> Dict:
        """
        Validate edge case timing around 11:00:00 ET boundary
        Critical for testing with microsecond precision
        """
        try:
            from zoneinfo import ZoneInfo
            now_et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
            
            # Get exact cutoff time
            cutoff_hour = int(os.getenv("ORDER_CUTOFF_HOUR", "11"))
            cutoff_time = now_et.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
            
            # Critical boundary check
            if now_et >= cutoff_time:
                # Calculate how late the submission is
                seconds_late = (now_et - cutoff_time).total_seconds()
                
                return {
                    "check": "edge_case_timing",
                    "status": "fail",
                    "message": f"DA cutoff passed by {seconds_late:.3f} seconds at {now_et.strftime('%H:%M:%S.%f')} ET"
                }
            
            # Calculate margin before cutoff
            seconds_remaining = (cutoff_time - now_et).total_seconds()
            
            # Warning if very close to cutoff (< 60 seconds)
            status = "warning" if seconds_remaining < 60 else "pass"
            message = f"{seconds_remaining:.3f} seconds before DA cutoff"
            
            return {
                "check": "edge_case_timing",
                "status": status,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Edge case timing validation error: {e}")
            return {
                "check": "edge_case_timing",
                "status": "fail",
                "message": f"Timing validation error: {e}"
            }
    
    def _validate_hour_limits(
        self,
        session: Session,
        user_id: str,
        node: str,
        hour_start_utc: datetime
    ) -> Dict:
        """Validate DA order limits per hour per user"""
        try:
            # Count existing DA orders for this hour
            existing_orders = session.exec(
                select(TradingOrder).where(
                    TradingOrder.user_id == user_id,
                    TradingOrder.node == node,
                    TradingOrder.market == MarketType.DAY_AHEAD,
                    TradingOrder.hour_start_utc == hour_start_utc,
                    TradingOrder.status.in_([OrderStatus.PENDING, OrderStatus.FILLED])
                )
            ).all()
            
            order_count = len(existing_orders)
            
            if order_count >= self.max_da_orders_per_hour:
                return {
                    "check": "hour_limits",
                    "status": "fail",
                    "message": f"Maximum {self.max_da_orders_per_hour} DA orders per hour exceeded. Current: {order_count}"
                }
            
            return {
                "check": "hour_limits",
                "status": "pass",
                "message": f"Order limit OK: {order_count}/{self.max_da_orders_per_hour} DA orders for this hour"
            }
            
        except Exception as e:
            logger.error(f"Hour limits validation error: {e}")
            return {
                "check": "hour_limits",
                "status": "fail", 
                "message": f"Hour limits validation error: {e}"
            }
    
    def _validate_delivery_date(self, hour_start_utc: datetime, now_utc: datetime) -> Dict:
        """Validate delivery date is for tomorrow (after cutoff)"""
        try:
            from zoneinfo import ZoneInfo
            
            # Convert times to ET
            now_et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
            delivery_et = hour_start_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
            
            # Check if delivery is for tomorrow
            now_date = now_et.date()
            delivery_date = delivery_et.date()
            
            # After 11am, DA orders should be for tomorrow
            state = trading_clock.get_trading_state(now_utc)
            if state == TradingState.POST_11AM:
                tomorrow = now_date + timedelta(days=1)
                if delivery_date < tomorrow:
                    return {
                        "check": "delivery_date",
                        "status": "fail",
                        "message": f"After 11am ET, DA orders must be for tomorrow. Delivery date: {delivery_date}, Tomorrow: {tomorrow}"
                    }
                elif delivery_date > tomorrow:
                    return {
                        "check": "delivery_date",
                        "status": "warning",
                        "message": f"DA order for {delivery_date} (more than 1 day ahead)"
                    }
            
            return {
                "check": "delivery_date",
                "status": "pass",
                "message": f"Delivery date {delivery_date} is valid for current time {now_date}"
            }
            
        except Exception as e:
            logger.error(f"Delivery date validation error: {e}")
            return {
                "check": "delivery_date",
                "status": "warning",
                "message": f"Delivery date validation error: {e}"
            }
    
    def _legacy_validation(
        self,
        session: Session,
        user_id: str,
        node: str,
        hour_start_utc: datetime,
        now_utc: datetime
    ) -> Dict:
        """Legacy validation logic (when feature flag is disabled)"""
        from ..models import validate_da_order_timing, validate_order_limits
        
        # Use existing validation functions
        timing_valid = validate_da_order_timing(hour_start_utc)
        limits_result = validate_order_limits(
            session, node, MarketType.DAY_AHEAD, hour_start_utc
        )
        
        if not timing_valid:
            raise DAOrderValidationError(
                "DA orders must be submitted before 11:00 AM ET",
                "LEGACY_TIMING_CUTOFF"
            )
        
        if not limits_result["valid"]:
            raise DAOrderValidationError(
                limits_result["message"],
                "LEGACY_LIMIT_EXCEEDED"
            )
        
        return {
            "valid": True,
            "trading_state": "LEGACY_MODE",
            "permissions": {"da_orders": timing_valid, "rt_orders": True},
            "checks": [
                {"check": "legacy_timing", "status": "pass" if timing_valid else "fail"},
                {"check": "legacy_limits", "status": "pass" if limits_result["valid"] else "fail"}
            ],
            "warnings": []
        }

# Global instance for use across the application  
da_rules_engine = DAOrderRulesEngine()

# Convenience functions
def validate_da_order(
    session: Session,
    user_id: str,
    node: str,
    hour_start_utc: datetime,
    now_utc: Optional[datetime] = None
) -> Dict:
    """Validate DA order submission"""
    return da_rules_engine.validate_da_order_submission(
        session, user_id, node, hour_start_utc, now_utc
    )

def is_da_submission_allowed(now_utc: Optional[datetime] = None) -> bool:
    """Quick check if DA submissions are currently allowed"""
    return trading_clock.is_da_allowed(now_utc)