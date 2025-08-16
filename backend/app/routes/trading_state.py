# Trading State API Routes
# Provides trading clock state and market permissions

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from typing import Optional, Dict
from ..services.trading_clock import trading_clock, TradingState
from ..services.da_rules import da_rules_engine
from ..services.settlement_engine import get_settlement_engine
from ..database import get_session
from sqlmodel import Session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading-state", tags=["trading-state"])

@router.get("/current")
async def get_current_trading_state(
    now_utc: Optional[str] = Query(default=None, description="Override current time for testing (ISO format)")
):
    """
    Get current trading state with market permissions and transition info
    """
    try:
        # Parse override time if provided (for testing)
        current_time = None
        if now_utc:
            try:
                current_time = datetime.fromisoformat(now_utc.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")
        
        # Get comprehensive trading info
        trading_info = trading_clock.get_trading_info(current_time)
        
        return {
            **trading_info,
            "api_version": "1.0",
            "description": "PJM-compliant trading day state machine"
        }
        
    except Exception as e:
        logger.error(f"Error getting trading state: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting trading state: {e}")

@router.get("/permissions")
async def get_market_permissions(
    now_utc: Optional[str] = Query(default=None, description="Override current time for testing")
):
    """
    Get current market permissions (DA and RT)
    """
    try:
        current_time = None
        if now_utc:
            current_time = datetime.fromisoformat(now_utc.replace('Z', '+00:00')).replace(tzinfo=None)
        
        state = trading_clock.get_trading_state(current_time)
        permissions = trading_clock._get_permissions(state)
        
        return {
            "state": state.value,
            "permissions": permissions,
            "da_allowed": permissions["da_orders"],
            "rt_allowed": permissions["rt_orders"],
            "da_cutoff_message": trading_clock.get_da_cutoff_message(current_time)
        }
        
    except Exception as e:
        logger.error(f"Error getting market permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting permissions: {e}")

@router.post("/validate-da-order")
async def validate_da_order_submission(
    user_id: str = Query(default="demo_user", description="User ID"),
    node: str = Query(..., description="PJM node for the order"),
    hour_start_utc: str = Query(..., description="Delivery hour in UTC (ISO format)"),
    now_utc: Optional[str] = Query(default=None, description="Override current time for testing"),
    session: Session = Depends(get_session)
):
    """
    Validate DA order submission against PJM rules
    """
    try:
        # Parse times
        hour_delivery = datetime.fromisoformat(hour_start_utc.replace('Z', '+00:00')).replace(tzinfo=None)
        current_time = None
        if now_utc:
            current_time = datetime.fromisoformat(now_utc.replace('Z', '+00:00')).replace(tzinfo=None)
        
        # Validate DA order
        validation_result = da_rules_engine.validate_da_order_submission(
            session, user_id, node, hour_delivery, current_time
        )
        
        return validation_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
    except Exception as e:
        logger.error(f"Error validating DA order: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {e}")

@router.get("/settlement-status/{date}")
async def get_settlement_status(
    date: str,
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get settlement status for a specific trading date
    """
    try:
        from datetime import date as date_type
        target_date = date_type.fromisoformat(date)
        
        settlement_engine = get_settlement_engine(session)
        settlement_result = await settlement_engine.process_trading_day_settlement(
            target_date, user_id
        )
        
        return settlement_result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        logger.error(f"Error getting settlement status: {e}")
        raise HTTPException(status_code=500, detail=f"Settlement error: {e}")

@router.get("/market-status-banner")
async def get_market_status_banner_data(
    now_utc: Optional[str] = Query(default=None, description="Override current time for testing")
):
    """
    Get data for market status banner component
    """
    try:
        current_time = None
        if now_utc:
            current_time = datetime.fromisoformat(now_utc.replace('Z', '+00:00')).replace(tzinfo=None)
        
        trading_info = trading_clock.get_trading_info(current_time)
        
        # Additional banner-specific info
        banner_data = {
            **trading_info,
            "banner_type": None,
            "banner_message": None,
            "banner_severity": "info"
        }
        
        # Determine banner type based on state
        state = TradingState(trading_info["state"])
        
        if state == TradingState.POST_11AM:
            banner_data["banner_type"] = "da_closed"
            banner_data["banner_message"] = "Day-ahead market closed until tomorrow 11:00 AM ET"
            banner_data["banner_severity"] = "warning"
        
        elif state == TradingState.PRE_11AM:
            seconds_until = trading_info["next_transition"]["seconds_until"]
            if seconds_until < 3600:  # Less than 1 hour
                banner_data["banner_type"] = "da_closing_soon"
                banner_data["banner_message"] = f"DA market closes in {trading_info['next_transition']['human_readable']}"
                banner_data["banner_severity"] = "warning"
        
        elif state == TradingState.END_OF_DAY:
            banner_data["banner_type"] = "market_closed"
            banner_data["banner_message"] = "Trading day ended - settlement in progress"
            banner_data["banner_severity"] = "error"
        
        return banner_data
        
    except Exception as e:
        logger.error(f"Error getting banner data: {e}")
        raise HTTPException(status_code=500, detail=f"Banner error: {e}")

@router.get("/feature-status")
async def get_feature_status():
    """
    Get PJM state machine feature status
    """
    try:
        return {
            "pjm_state_machine_enabled": trading_clock.feature_enabled,
            "da_cutoff_hour": trading_clock.da_cutoff_hour,
            "da_cutoff_minute": trading_clock.da_cutoff_minute,
            "timezone": str(trading_clock.timezone),
            "current_state": trading_clock.get_trading_state().value if trading_clock.feature_enabled else "LEGACY_MODE",
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Error getting feature status: {e}")
        raise HTTPException(status_code=500, detail=f"Feature status error: {e}")

@router.post("/test-edge-cases")
async def test_edge_case_scenarios(
    session: Session = Depends(get_session)
):
    """
    Test critical edge cases for DA cutoff timing
    """
    try:
        from zoneinfo import ZoneInfo
        
        test_cases = []
        
        # Test case 1: 10:59:59.999 ET (should allow)
        test_time_1 = datetime.now(ZoneInfo("America/New_York")).replace(
            hour=10, minute=59, second=59, microsecond=999000
        ).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        
        result_1 = da_rules_engine.validate_da_order_submission(
            session, "test_user", "TEST_NODE", 
            test_time_1 + timedelta(days=1), test_time_1
        )
        
        test_cases.append({
            "scenario": "10:59:59.999 ET",
            "time_et": test_time_1.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York")).isoformat(),
            "should_allow": True,
            "result": result_1["valid"]
        })
        
        # Test case 2: 11:00:00.000 ET (should reject)
        test_time_2 = datetime.now(ZoneInfo("America/New_York")).replace(
            hour=11, minute=0, second=0, microsecond=0
        ).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        
        try:
            result_2 = da_rules_engine.validate_da_order_submission(
                session, "test_user", "TEST_NODE",
                test_time_2 + timedelta(days=1), test_time_2
            )
            test_cases.append({
                "scenario": "11:00:00.000 ET",
                "time_et": test_time_2.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York")).isoformat(),
                "should_allow": False,
                "result": result_2["valid"]
            })
        except Exception as e:
            test_cases.append({
                "scenario": "11:00:00.000 ET",
                "time_et": test_time_2.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York")).isoformat(),
                "should_allow": False,
                "result": False,
                "error": str(e)
            })
        
        return {
            "test_cases": test_cases,
            "summary": {
                "passed": sum(1 for tc in test_cases if tc.get("result") == tc["should_allow"]),
                "failed": sum(1 for tc in test_cases if tc.get("result") != tc["should_allow"]),
                "total": len(test_cases)
            }
        }
        
    except Exception as e:
        logger.error(f"Error running edge case tests: {e}")
        raise HTTPException(status_code=500, detail=f"Test error: {e}")