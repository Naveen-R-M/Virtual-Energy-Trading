"""
Trading Orders API Routes for Virtual Energy Trading Platform
Handles order creation, listing, and management for both markets
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from ..database import get_session
from ..models import (
    TradingOrder, OrderStatus, OrderSide, MarketType, OrderType, TimeInForce,
    validate_da_order_timing, validate_order_limits
)
from ..services.matching_engine import MatchingEngine
from ..services.position_manager import PositionManager
from ..services.trading_session_manager import TradingSessionManager
from ..services.rt_interval_manager import RTIntervalManager
from ..services.rt_settlement_service import RTSettlementService
import logging
import pytz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Request/Response models
class OrderRequest(BaseModel):
    """Order creation request model"""
    hour_start: str = Field(..., description="Hour start time in ISO format")
    node: str = Field(default="PJM_RTO", description="Grid node")
    market: MarketType = Field(..., description="Market type: day-ahead or real-time")
    side: OrderSide = Field(..., description="Order side: buy or sell")
    order_type: OrderType = Field(default=OrderType.LIMIT, description="Order type: MKT or LMT")
    limit_price: Optional[float] = Field(default=None, gt=0, description="Limit price in $/MWh (required for LMT orders)")
    quantity_mwh: float = Field(..., gt=0, le=100, description="Quantity in MWh")
    time_slot: Optional[str] = Field(default=None, description="5-minute slot for RT orders")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time in force: GTC, IOC, or DAY")
    expires_at: Optional[str] = Field(default=None, description="Explicit expiry time (ISO format)")
    
    def validate_order_data(self):
        """Validate order data consistency"""
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit price is required for limit orders")
        if self.order_type == OrderType.MARKET and self.limit_price is not None:
            raise ValueError("Limit price should not be specified for market orders")

class OrderResponse(BaseModel):
    """Order response model"""
    order_id: str
    status: str
    message: str
    details: Optional[dict] = None

@router.post("/")
async def create_order(
    order_data: OrderRequest = Body(...),
    user_id: str = Query(default="demo_user", description="User ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session)
) -> OrderResponse:
    """
    Create a new trading order for Day-Ahead or Real-Time market
    """
    try:
        # Validate order data consistency
        order_data.validate_order_data()
        
        # Parse timestamps and handle RT interval assignment
        hour_start_utc = datetime.fromisoformat(order_data.hour_start.replace("Z", "+00:00"))
        time_slot_utc = None
        expires_at_utc = None
        
        # For RT orders, determine the appropriate 5-minute interval
        if order_data.market == MarketType.REAL_TIME:
            interval_manager = RTIntervalManager()
            current_time = datetime.utcnow()
            
            # If time_slot is specified, validate it
            if order_data.time_slot:
                requested_slot = datetime.fromisoformat(order_data.time_slot.replace("Z", "+00:00"))
                
                # Align to 5-minute boundary if needed
                is_aligned, aligned_slot = interval_manager.validate_interval_alignment(requested_slot)
                if not is_aligned:
                    logger.info(f"Aligning requested slot {requested_slot} to {aligned_slot}")
                    time_slot_utc = aligned_slot
                else:
                    time_slot_utc = requested_slot
                
                # Check if we can place order for this interval
                can_place, reason = interval_manager.can_place_order_for_interval(
                    current_time, time_slot_utc
                )
                
                logger.info(
                    f"RT interval check: current_time={current_time}, "
                    f"requested_slot={time_slot_utc}, can_place={can_place}, reason={reason}"
                )
                
                if not can_place:
                    raise HTTPException(status_code=422, detail=reason)
            else:
                # Auto-assign to appropriate interval based on current time
                interval_start, interval_end, interval_type = interval_manager.get_interval_for_order(
                    current_time
                )
                time_slot_utc = interval_start
                
                logger.info(
                    f"Auto-assigned RT order to {interval_type} interval: "
                    f"{interval_manager.format_interval_display(interval_start)}"
                )
            
        if order_data.expires_at:
            expires_at_utc = datetime.fromisoformat(order_data.expires_at.replace("Z", "+00:00"))
        
        # NOW check trading permissions with parsed timestamp
        session_manager = TradingSessionManager(session)
        is_allowed, permission_reason = session_manager.is_trading_allowed(
            user_id, order_data.market, hour_start_utc
        )
        
        if not is_allowed:
            raise HTTPException(status_code=422, detail=permission_reason)
        
        # Validate Day-Ahead cutoff time
        if order_data.market == MarketType.DAY_AHEAD:
            if not validate_da_order_timing(hour_start_utc):
                et = pytz.timezone('US/Eastern')
                current_time = datetime.now(et)
                cutoff_time = current_time.replace(hour=11, minute=0, second=0, microsecond=0)
                
                raise HTTPException(
                    status_code=422,
                    detail=f"Day-Ahead orders must be submitted before {cutoff_time.strftime('%I:%M %p %Z')}. Current time: {current_time.strftime('%I:%M %p %Z')}"
                )
        
        # Validate order limits
        limit_check = validate_order_limits(
            session,
            order_data.node,
            order_data.market,
            hour_start_utc,
            time_slot_utc
        )
        
        if not limit_check['is_valid']:
            max_orders = limit_check['max_count']
            current_count = limit_check['current_count']
            market_name = "Day-Ahead hour" if order_data.market == MarketType.DAY_AHEAD else "Real-Time slot"
            
            raise HTTPException(
                status_code=422,
                detail=f"Order limit exceeded: {current_count}/{max_orders} orders already placed for this {market_name}"
            )
        
        # Validate position logic (no naked short selling)
        position_manager = PositionManager(session)
        
        # Determine the time slot to check
        check_time = time_slot_utc if order_data.market == MarketType.REAL_TIME else hour_start_utc
        
        is_valid, error_message = position_manager.validate_order(
            user_id=user_id,
            node=order_data.node,
            market=order_data.market,
            time_slot=check_time,
            side=order_data.side,
            quantity=order_data.quantity_mwh
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail=error_message
            )
        
        # Create the order
        new_order = TradingOrder(
            user_id=user_id,
            node=order_data.node,
            market=order_data.market,
            hour_start_utc=hour_start_utc,
            time_slot_utc=time_slot_utc,
            side=order_data.side,
            order_type=order_data.order_type,
            limit_price=order_data.limit_price,
            quantity_mwh=order_data.quantity_mwh,
            time_in_force=order_data.time_in_force,
            expires_at=expires_at_utc,
            status=OrderStatus.PENDING  # ALL orders start as PENDING
        )
        
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
        
        # Update trade metrics in session (for pending orders)
        session_manager.update_trade_metrics(
            user_id, hour_start_utc, order_data.quantity_mwh
        )
        
        # RT orders - show interval assignment and settlement info
        if order_data.market == MarketType.REAL_TIME:
            interval_manager = RTIntervalManager()
            interval_display = interval_manager.format_interval_display(time_slot_utc)
            settlement_status = interval_manager.get_settlement_status(time_slot_utc)
            
            logger.info(
                f"RT order {new_order.order_id} created for interval {interval_display}"
            )
            
            # Check if we can settle immediately (rare, but possible if price is already available)
            if settlement_status['can_settle']:
                try:
                    settlement_service = RTSettlementService(session)
                    settlement_results = await settlement_service.check_and_settle_pending_orders(
                        node=order_data.node,
                        user_id=user_id
                    )
                    
                    # Check if our order was settled
                    session.refresh(new_order)
                    
                    if new_order.status == OrderStatus.FILLED:
                        return OrderResponse(
                            order_id=new_order.order_id,
                            status="success",
                            message=f"RT order filled at ${new_order.filled_price:.2f}/MWh for {interval_display}",
                            details={
                                "order_status": "filled",
                                "filled_price": new_order.filled_price,
                                "filled_quantity": new_order.filled_quantity,
                                "interval": interval_display,
                                "settlement_time": datetime.utcnow().isoformat()
                            }
                        )
                    elif new_order.status == OrderStatus.REJECTED:
                        return OrderResponse(
                            order_id=new_order.order_id,
                            status="success",
                            message=f"RT order rejected: {new_order.rejection_reason}",
                            details={
                                "order_status": "rejected",
                                "rejection_reason": new_order.rejection_reason,
                                "interval": interval_display
                            }
                        )
                except Exception as e:
                    logger.warning(f"Could not settle RT order immediately: {e}")
            
            # Order remains pending until settlement
            return OrderResponse(
                order_id=new_order.order_id,
                status="success",
                message=f"RT order placed for {interval_display} - {settlement_status['message']}",
                details={
                    "order_status": "pending",
                    "interval": interval_display,
                    "interval_start_utc": time_slot_utc.isoformat(),
                    "interval_end_utc": (time_slot_utc + timedelta(minutes=5)).isoformat(),
                    "expected_settlement_time": settlement_status['expected_settlement_time'].isoformat(),
                    "settlement_message": settlement_status['message']
                }
            )
        
        # DA orders also remain pending until DA close/matching
        return OrderResponse(
            order_id=new_order.order_id,
            status="success",
            message=f"{order_data.market.value.title()} order created successfully",
            details={
                "order_status": new_order.status.value,
                "remaining_slots": limit_check['remaining'] - 1,
                "market": order_data.market.value,
                "hour": hour_start_utc.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating order: {e}")

@router.post("/execute-rt/{order_id}")
async def execute_rt_order(
    order_id: int,
    session: Session = Depends(get_session)
):
    """
    Manually execute a pending RT order
    """
    try:
        # Get the order
        order = session.get(TradingOrder, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.market != MarketType.REAL_TIME:
            raise HTTPException(status_code=400, detail="Not a Real-Time order")
        
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400, 
                detail=f"Order status is {order.status.value}, not pending"
            )
        
        # Execute the order
        matching_engine = MatchingEngine(session)
        result = await matching_engine.execute_real_time_order(order_id)
        
        # Refresh order to get updated values
        session.refresh(order)
        
        return {
            "status": "success",
            "order_id": order.order_id,
            "execution_status": result.status,
            "filled_price": result.filled_price,
            "filled_quantity": result.filled_quantity,
            "reason": result.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing RT order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing order: {e}")

@router.post("/settle-rt")
async def settle_pending_rt_orders(
    user_id: str = Query(default="demo_user", description="User ID"),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Check and settle pending RT orders with published interval prices
    
    This endpoint:
    1. Finds all pending RT orders
    2. Checks if their intervals have completed
    3. Fetches the published RT prices for those intervals
    4. Settles orders based on limit price vs actual price
    """
    try:
        settlement_service = RTSettlementService(session)
        result = await settlement_service.check_and_settle_pending_orders(node, user_id)
        
        return {
            "status": "success",
            "summary": {
                "checked": result['checked'],
                "settled": result['settled'],
                "filled": result['filled'],
                "rejected": result['rejected'],
                "waiting": result['waiting'],
                "errors": result['errors']
            },
            "details": result['details']
        }
        
    except Exception as e:
        logger.error(f"Error in RT settlement: {e}")
        raise HTTPException(status_code=500, detail=f"Error settling RT orders: {e}")

@router.get("/rt-status")
async def get_rt_orders_status(
    user_id: str = Query(default="demo_user", description="User ID"),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Get status of all pending RT orders with settlement information
    """
    try:
        settlement_service = RTSettlementService(session)
        status_list = await settlement_service.get_pending_orders_status(node, user_id)
        
        return {
            "status": "success",
            "pending_orders": status_list,
            "count": len(status_list),
            "current_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting RT order status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {e}")

@router.get("/")
async def list_orders(
    date: Optional[str] = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
    node: str = Query(default="PJM_RTO", description="Grid node"),
    market: Optional[MarketType] = Query(default=None, description="Filter by market type"),
    status: Optional[OrderStatus] = Query(default=None, description="Filter by order status"),
    user_id: str = Query(default="demo_user", description="User ID"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of orders to return"),
    session: Session = Depends(get_session)
):
    """
    List trading orders with optional filters
    """
    try:
        # Build query
        statement = select(TradingOrder).where(
            TradingOrder.user_id == user_id,
            TradingOrder.node == node
        )
        
        # Apply filters
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            statement = statement.where(
                TradingOrder.hour_start_utc >= start_time,
                TradingOrder.hour_start_utc < end_time
            )
        
        if market:
            statement = statement.where(TradingOrder.market == market)
        
        if status:
            statement = statement.where(TradingOrder.status == status)
        
        # Order by creation time descending
        statement = statement.order_by(TradingOrder.created_at.desc()).limit(limit)
        
        # Execute query
        orders = session.exec(statement).all()
        
        # Format response
        result = []
        for order in orders:
            order_dict = {
                "id": order.id,
                "order_id": order.order_id,
                "market": order.market.value,
                "hour_start": order.hour_start_utc.isoformat(),
                "time_slot": order.time_slot_utc.isoformat() if order.time_slot_utc else None,
                "side": order.side.value,
                "limit_price": order.limit_price,
                "quantity_mwh": order.quantity_mwh,
                "status": order.status.value,
                "filled_price": order.filled_price,
                "filled_quantity": order.filled_quantity,
                "rejection_reason": order.rejection_reason,
                "created_at": order.created_at.isoformat(),
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            }
            result.append(order_dict)
        
        return {
            "orders": result,
            "count": len(result),
            "filters": {
                "date": date,
                "node": node,
                "market": market.value if market else None,
                "status": status.value if status else None,
                "user_id": user_id
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing orders: {e}")

@router.get("/{order_id}")
async def get_order(
    order_id: str,
    session: Session = Depends(get_session)
):
    """
    Get details of a specific order
    """
    try:
        statement = select(TradingOrder).where(TradingOrder.order_id == order_id)
        order = session.exec(statement).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Include fill information if available
        fills_data = []
        if order.fills:
            for fill in order.fills:
                fills_data.append({
                    "fill_type": fill.fill_type.value,
                    "filled_price": fill.filled_price,
                    "filled_quantity": fill.filled_quantity,
                    "market_price_at_fill": fill.market_price_at_fill,
                    "timestamp": fill.timestamp_utc.isoformat(),
                    "gross_pnl": fill.gross_pnl
                })
        
        return {
            "id": order.id,
            "order_id": order.order_id,
            "user_id": order.user_id,
            "node": order.node,
            "market": order.market.value,
            "hour_start": order.hour_start_utc.isoformat(),
            "time_slot": order.time_slot_utc.isoformat() if order.time_slot_utc else None,
            "side": order.side.value,
            "limit_price": order.limit_price,
            "quantity_mwh": order.quantity_mwh,
            "status": order.status.value,
            "filled_price": order.filled_price,
            "filled_quantity": order.filled_quantity,
            "rejection_reason": order.rejection_reason,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            "fills": fills_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting order: {e}")

@router.put("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    session: Session = Depends(get_session)
) -> OrderResponse:
    """
    Cancel a pending order
    """
    try:
        statement = select(TradingOrder).where(TradingOrder.order_id == order_id)
        order = session.exec(statement).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel order with status: {order.status.value}"
            )
        
        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        session.add(order)
        session.commit()
        
        return OrderResponse(
            order_id=order.order_id,
            status="success",
            message="Order cancelled successfully",
            details={"order_status": order.status.value}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling order: {e}")

@router.post("/match/day/{date}")
async def match_day_ahead_orders(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    session: Session = Depends(get_session)
):
    """
    Match all pending Day-Ahead orders for a specific date
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        
        engine = MatchingEngine(session)
        results = await engine.match_day_ahead_orders(target_date, node)
        
        # Summarize results
        filled_count = sum(1 for r in results if r.status == "filled")
        rejected_count = sum(1 for r in results if r.status == "rejected")
        
        return {
            "date": date,
            "node": node,
            "total_processed": len(results),
            "filled": filled_count,
            "rejected": rejected_count,
            "results": [
                {
                    "order_id": r.order_id,
                    "status": r.status,
                    "filled_price": r.filled_price,
                    "filled_quantity": r.filled_quantity,
                    "reason": r.reason
                }
                for r in results
            ]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error matching DA orders: {e}")
        raise HTTPException(status_code=500, detail=f"Error matching Day-Ahead orders: {e}")

@router.get("/position/summary")
async def get_position_summary(
    node: str = Query(default="PJM_RTO", description="Grid node"),
    date: Optional[str] = Query(default=None, description="Date (YYYY-MM-DD)"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get portfolio position summary
    """
    try:
        position_manager = PositionManager(session)
        
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.utcnow()
        
        summary = position_manager.get_portfolio_summary(user_id, node, target_date)
        return summary
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting position summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting position summary: {e}")

@router.get("/position/hourly")
async def get_hourly_positions(
    node: str = Query(default="PJM_RTO", description="Grid node"),
    date: Optional[str] = Query(default=None, description="Date (YYYY-MM-DD)"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get hour-by-hour position breakdown
    """
    try:
        position_manager = PositionManager(session)
        
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.utcnow()
        
        positions = position_manager.get_hourly_positions(user_id, node, target_date)
        
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "node": node,
            "user_id": user_id,
            "hourly_positions": positions
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting hourly positions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting hourly positions: {e}")

@router.get("/limits/{hour}")
async def get_order_limits(
    hour: str,
    node: str = Query(default="PJM_RTO", description="Grid node"),
    market: MarketType = Query(..., description="Market type"),
    time_slot: Optional[str] = Query(default=None, description="5-minute slot for RT"),
    session: Session = Depends(get_session)
):
    """
    Get current order count and limits for a specific time slot
    """
    try:
        hour_start_utc = datetime.fromisoformat(hour.replace("Z", "+00:00"))
        time_slot_utc = None
        
        if market == MarketType.REAL_TIME and time_slot:
            time_slot_utc = datetime.fromisoformat(time_slot.replace("Z", "+00:00"))
        
        limit_info = validate_order_limits(
            session,
            node,
            market,
            hour_start_utc,
            time_slot_utc
        )
        
        # Also get position info
        position_manager = PositionManager(session)
        check_time = time_slot_utc if market == MarketType.REAL_TIME else hour_start_utc
        position = position_manager.calculate_pending_position(
            "demo_user", node, market, check_time
        )
        
        return {
            "node": node,
            "market": market.value,
            "hour": hour,
            "time_slot": time_slot,
            "current_orders": limit_info['current_count'],
            "max_orders": limit_info['max_count'],
            "remaining_slots": limit_info['remaining'],
            "can_place_order": limit_info['is_valid'],
            "position": {
                "current_net": position['current_net_position'],
                "projected_net": position['projected_net_position'],
                "max_sell_quantity": max(0, position['projected_net_position'])
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
    except Exception as e:
        logger.error(f"Error getting order limits: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting order limits: {e}")

@router.post("/position/validate")
async def validate_position(
    order_data: OrderRequest = Body(...),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Validate if an order can be placed based on position limits
    """
    try:
        position_manager = PositionManager(session)
        
        # Parse timestamps
        hour_start_utc = datetime.fromisoformat(order_data.hour_start.replace("Z", "+00:00"))
        time_slot_utc = None
        
        if order_data.market == MarketType.REAL_TIME and order_data.time_slot:
            time_slot_utc = datetime.fromisoformat(order_data.time_slot.replace("Z", "+00:00"))
        
        check_time = time_slot_utc if order_data.market == MarketType.REAL_TIME else hour_start_utc
        
        is_valid, error_message = position_manager.validate_order(
            user_id=user_id,
            node=order_data.node,
            market=order_data.market,
            time_slot=check_time,
            side=order_data.side,
            quantity=order_data.quantity_mwh
        )
        
        # Get current position for context
        position = position_manager.calculate_pending_position(
            user_id, order_data.node, order_data.market, check_time
        )
        
        return {
            "is_valid": is_valid,
            "error_message": error_message,
            "current_position": position
        }
        
    except Exception as e:
        logger.error(f"Error validating position: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating position: {e}")

@router.post("/settle-rt")
async def settle_rt_orders(
    user_id: str = Query(default="demo_user", description="User ID"),
    node: str = Query(default="PJM_RTO", description="Node ID"),
    force: bool = Query(default=False, description="Force settlement even if time hasn't passed"),
    session: Session = Depends(get_session)
):
    """
    Settle pending RT orders whose execution time has passed.
    This endpoint is called periodically by the frontend to process RT settlements.
    """
    try:
        from datetime import timedelta
        import random
        
        now = datetime.now(timezone.utc)
        settled_orders = []
        
        # Query pending RT orders for the user and node
        stmt = select(Order).where(
            Order.user_id == user_id,
            Order.node == node,
            Order.market == MarketType.REAL_TIME,
            Order.status == OrderStatus.PENDING
        )
        
        result = session.execute(stmt)
        pending_orders = result.scalars().all()
        
        logger.info(f"Found {len(pending_orders)} pending RT orders for settlement check")
        
        for order in pending_orders:
            # Determine execution time
            exec_time = order.time_slot_utc if order.time_slot_utc else order.hour_start
            exec_end_time = exec_time + timedelta(minutes=5)  # RT intervals are 5 minutes
            
            # Check if execution time has passed (or force flag is set)
            if exec_end_time <= now or force:
                # Generate mock RT price (in production, fetch from market data)
                hour = exec_time.hour
                base_price = 42.0 if 6 <= hour < 21 else 40.0  # Higher during day
                rt_price = base_price + random.uniform(-2, 3)  # Add some variation
                
                # Determine if order fills
                fills = False
                if order.side == OrderSide.BUY:
                    fills = order.limit_price >= rt_price
                else:  # SELL
                    fills = order.limit_price <= rt_price
                
                if fills:
                    order.status = OrderStatus.FILLED
                    order.filled_price = rt_price
                    order.filled_at = now
                    
                    # Simple P&L calculation (in production, would be more complex)
                    if order.side == OrderSide.BUY:
                        # Assume we can sell at a small premium
                        order.pnl = (rt_price * 1.01 - rt_price) * order.quantity_mwh
                    else:
                        # Assume we avoided buying at a small discount  
                        order.pnl = (rt_price - rt_price * 0.99) * order.quantity_mwh
                    
                    logger.info(f"Order {order.order_id[:8]} FILLED at ${rt_price:.2f}")
                else:
                    order.status = OrderStatus.REJECTED
                    order.rejected_reason = f"Limit not met. RT price: ${rt_price:.2f}"
                    logger.info(f"Order {order.order_id[:8]} REJECTED - limit not met")
                
                order.updated_at = now
                settled_orders.append({
                    "order_id": order.order_id,
                    "status": order.status.value,
                    "filled_price": order.filled_price,
                    "rt_price": rt_price,
                    "pnl": order.pnl
                })
        
        session.commit()
        
        return {
            "status": "success",
            "settled_count": len(settled_orders),
            "settled_orders": settled_orders,
            "message": f"Settled {len(settled_orders)} RT orders"
        }
        
    except Exception as e:
        logger.error(f"Error settling RT orders: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error settling RT orders: {e}")
