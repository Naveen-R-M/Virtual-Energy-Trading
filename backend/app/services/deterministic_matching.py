# Deterministic PJM Matching Engine - ISO Counterparty Model
# Event-driven, idempotent order matching against published LMPs

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import logging
import os
from ..models import (
    TradingOrder, OrderFill, DayAheadPrice, RealTimePrice, 
    MarketType, OrderStatus, OrderSide, OrderType, TimeInForce, FillType
)

logger = logging.getLogger(__name__)

class DeterministicMatchingService:
    """
    ISO-counterparty deterministic matching engine
    - Triggers on new price events only (no randomness)
    - Idempotent processing (no duplicate fills)
    - Price-taker model (no market impact)
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.enabled = self._is_feature_enabled()
    
    def _is_feature_enabled(self) -> bool:
        """Check if deterministic matching is enabled"""
        return os.getenv("DETERMINISTIC_MATCHING_ENABLED", "false").lower() == "true"
    
    async def on_new_rt_tick(self, node_id: str, ts_5m: datetime, lmp: float) -> Dict:
        """
        Process new RT 5-minute tick - match all eligible RT orders
        
        Args:
            node_id: PJM node identifier
            ts_5m: 5-minute timestamp (must be exactly on 5-min boundary)
            lmp: Locational Marginal Price in $/MWh
        
        Returns:
            Dict with matching results and metrics
        """
        if not self.enabled:
            logger.info("Deterministic matching disabled, skipping RT tick processing")
            return {"status": "disabled", "processed": 0}
        
        start_time = datetime.utcnow()
        
        try:
            # Get all eligible open RT orders for this node
            eligible_orders = self._get_eligible_rt_orders(node_id, ts_5m)
            
            matched_orders = 0
            filled_orders = 0
            rejected_orders = 0
            results = []
            
            # Process orders deterministically (ordered by created_at for consistency)
            for order in sorted(eligible_orders, key=lambda o: o.created_at):
                
                # Check if order should fill based on limit price
                should_fill = self._should_fill_rt_order(order, lmp)
                
                if should_fill:
                    # Execute fill idempotently
                    fill_result = await self._execute_rt_fill_idempotent(order, lmp, ts_5m)
                    if fill_result["status"] == "filled":
                        filled_orders += 1
                    results.append(fill_result)
                else:
                    # Order doesn't meet limit - keep open for future ticks
                    results.append({
                        "order_id": order.order_id,
                        "status": "no_fill",
                        "reason": f"Limit not met: ${order.limit_price:.2f} vs LMP ${lmp:.2f}",
                        "lmp_price": lmp
                    })
                
                matched_orders += 1
            
            # Commit all changes atomically
            self.session.commit()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log metrics
            logger.info(
                f"RT matching completed: node={node_id}, timestamp={ts_5m}, "
                f"lmp=${lmp:.2f}, matched_orders={matched_orders}, "
                f"filled={filled_orders}, rejected={rejected_orders}, "
                f"processing_time={processing_time:.1f}ms"
            )
            
            return {
                "status": "completed",
                "node_id": node_id,
                "timestamp": ts_5m.isoformat(),
                "lmp_price": lmp,
                "metrics": {
                    "matched_orders": matched_orders,
                    "filled": filled_orders,
                    "rejected": rejected_orders,
                    "processing_time_ms": round(processing_time, 1)
                },
                "results": results
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in RT matching for {node_id} at {ts_5m}: {e}")
            raise
    
    async def on_new_da_price(self, node_id: str, hour_start: datetime, p_da: float) -> Dict:
        """
        Process new DA hourly clearing price - match all eligible DA orders
        
        Args:
            node_id: PJM node identifier  
            hour_start: Hour starting datetime (delivery hour)
            p_da: Day-ahead clearing price in $/MWh
        
        Returns:
            Dict with matching results and metrics
        """
        if not self.enabled:
            logger.info("Deterministic matching disabled, skipping DA price processing")
            return {"status": "disabled", "processed": 0}
        
        start_time = datetime.utcnow()
        
        try:
            # Get all eligible open DA orders for this node and hour
            eligible_orders = self._get_eligible_da_orders(node_id, hour_start)
            
            matched_orders = 0
            filled_orders = 0  
            rejected_orders = 0
            results = []
            
            # Process orders deterministically (ordered by created_at)
            for order in sorted(eligible_orders, key=lambda o: o.created_at):
                
                # Check if order should fill based on limit price
                should_fill = self._should_fill_da_order(order, p_da)
                
                if should_fill:
                    # Execute fill idempotently
                    fill_result = await self._execute_da_fill_idempotent(order, p_da, hour_start)
                    if fill_result["status"] == "filled":
                        filled_orders += 1
                    else:
                        rejected_orders += 1
                    results.append(fill_result)
                else:
                    # Reject order - limit not met
                    reject_result = await self._reject_order_idempotent(
                        order, f"Limit not met: ${order.limit_price:.2f} vs DA ${p_da:.2f}"
                    )
                    rejected_orders += 1
                    results.append(reject_result)
                
                matched_orders += 1
            
            # Commit all changes atomically
            self.session.commit()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log metrics
            logger.info(
                f"DA matching completed: node={node_id}, hour={hour_start}, "
                f"da_price=${p_da:.2f}, matched_orders={matched_orders}, "
                f"filled={filled_orders}, rejected={rejected_orders}, "
                f"processing_time={processing_time:.1f}ms"
            )
            
            return {
                "status": "completed",
                "node_id": node_id,
                "hour_start": hour_start.isoformat(),
                "da_price": p_da,
                "metrics": {
                    "matched_orders": matched_orders,
                    "filled": filled_orders,
                    "rejected": rejected_orders,
                    "processing_time_ms": round(processing_time, 1)
                },
                "results": results
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in DA matching for {node_id} hour {hour_start}: {e}")
            raise
    
    def _get_eligible_rt_orders(self, node_id: str, ts_5m: datetime) -> List[TradingOrder]:
        """Get all eligible RT orders for matching against this tick"""
        
        # RT orders are eligible if:
        # 1. Status = OPEN/PENDING
        # 2. Market = REAL_TIME  
        # 3. Node matches
        # 4. time_slot_utc <= ts_5m (order time slot has arrived)
        # 5. Not already filled (idempotency check)
        
        statement = select(TradingOrder).where(
            TradingOrder.node == node_id,
            TradingOrder.market == MarketType.REAL_TIME,
            TradingOrder.status == OrderStatus.PENDING,
            TradingOrder.time_slot_utc <= ts_5m
        ).order_by(TradingOrder.created_at)
        
        orders = self.session.exec(statement).all()
        
        # Additional filtering for time-in-force and expiry
        eligible = []
        for order in orders:
            # Check if order has expired (default: expires end of trading day)
            if self._is_order_expired(order, ts_5m):
                continue
                
            # Check if already processed for this exact timestamp (idempotency)
            if self._already_processed_at_timestamp(order, ts_5m):
                continue
                
            eligible.append(order)
        
        return eligible
    
    def _get_eligible_da_orders(self, node_id: str, hour_start: datetime) -> List[TradingOrder]:
        """Get all eligible DA orders for matching against this clearing price"""
        
        # DA orders are eligible if:
        # 1. Status = OPEN/PENDING
        # 2. Market = DAY_AHEAD
        # 3. Node matches  
        # 4. hour_start_utc matches exactly
        # 5. Not already filled (idempotency check)
        
        statement = select(TradingOrder).where(
            TradingOrder.node == node_id,
            TradingOrder.market == MarketType.DAY_AHEAD,
            TradingOrder.status == OrderStatus.PENDING,
            TradingOrder.hour_start_utc == hour_start
        ).order_by(TradingOrder.created_at)
        
        orders = self.session.exec(statement).all()
        
        # Filter out already processed orders (idempotency)
        eligible = []
        for order in orders:
            if not self._already_processed_for_da_hour(order, hour_start):
                eligible.append(order)
        
        return eligible
    
    def _should_fill_rt_order(self, order: TradingOrder, lmp: float) -> bool:
        """Determine if RT order should fill based on order type and limit price"""
        # Market orders always fill at current LMP
        if order.order_type == OrderType.MARKET:
            return True
            
        # Limit orders fill based on limit price
        if order.side == OrderSide.BUY:
            # BUY: fill if LMP <= limit (can buy at or below limit)
            return lmp <= order.limit_price
        else:  # SELL
            # SELL: fill if LMP >= limit (can sell at or above limit)  
            return lmp >= order.limit_price
    
    def _should_fill_da_order(self, order: TradingOrder, p_da: float) -> bool:
        """Determine if DA order should fill based on order type and limit price"""
        # Market orders always fill at clearing price (rare for DA but supported)
        if order.order_type == OrderType.MARKET:
            return True
            
        # Limit orders fill based on limit price
        if order.side == OrderSide.BUY:
            # BUY: fill if P_DA <= limit
            return p_da <= order.limit_price
        else:  # SELL
            # SELL: fill if P_DA >= limit
            return p_da >= order.limit_price
    
    async def _execute_rt_fill_idempotent(self, order: TradingOrder, lmp: float, ts_5m: datetime) -> Dict:
        """Execute RT fill with idempotency protection"""
        
        try:
            # Double-check order hasn't been filled already (race condition protection)
            self.session.refresh(order)
            if order.status != OrderStatus.PENDING:
                return {
                    "order_id": order.order_id,
                    "status": "already_processed",
                    "reason": f"Order status is {order.status.value}",
                    "filled_price": order.filled_price
                }
            
            # Update order status
            order.status = OrderStatus.FILLED
            order.filled_price = lmp
            order.filled_quantity = order.quantity_mwh  # Full fill
            order.filled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            # Create fill record
            fill = OrderFill(
                order_id=order.id,
                fill_type=FillType.RT_IMMEDIATE,
                filled_price=lmp,
                filled_quantity=order.quantity_mwh,
                market_price_at_fill=lmp,
                timestamp_utc=ts_5m,  # Use market timestamp, not system time
                gross_pnl=0.0  # RT has immediate settlement, no carry P&L
            )
            
            self.session.add(order)
            self.session.add(fill)
            
            # Update trading session metrics
            try:
                from .trading_session_manager import TradingSessionManager
                session_manager = TradingSessionManager(self.session)
                
                # Update trade metrics
                session_manager.update_trade_metrics(
                    order.user_id, hour_start, order.quantity_mwh
                )
                
                # For DA trades, P&L will be calculated during RT settlement
                # For now, just track the fill
                realized_pnl = 0.0  # Will be updated during RT settlement
                session_manager.update_daily_pnl(
                    order.user_id, hour_start, realized_pnl, 0.0
                )
                
            except Exception as session_error:
                logger.warning(f"Failed to update session metrics: {session_error}")
            
            logger.debug(
                f"RT fill executed: order_id={order.order_id}, "
                f"side={order.side.value}, qty={order.quantity_mwh}, "
                f"fill_price=${lmp:.2f}, market_ts={ts_5m}"
            )
            
            return {
                "order_id": order.order_id,
                "status": "filled",
                "filled_price": lmp,
                "filled_quantity": order.quantity_mwh,
                "execution_time": ts_5m.isoformat(),
                "exec_ref": "RT_5M"
            }
            
        except Exception as e:
            logger.error(f"Error executing RT fill for order {order.order_id}: {e}")
            return {
                "order_id": order.order_id,
                "status": "error",
                "reason": str(e)
            }
    
    async def _execute_da_fill_idempotent(self, order: TradingOrder, p_da: float, hour_start: datetime) -> Dict:
        """Execute DA fill with idempotency protection"""
        
        try:
            # Double-check order hasn't been processed already
            self.session.refresh(order)
            if order.status != OrderStatus.PENDING:
                return {
                    "order_id": order.order_id,
                    "status": "already_processed", 
                    "reason": f"Order status is {order.status.value}",
                    "filled_price": order.filled_price
                }
            
            # Update order status
            order.status = OrderStatus.FILLED
            order.filled_price = p_da
            order.filled_quantity = order.quantity_mwh  # Full fill
            order.filled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            # Create fill record
            fill = OrderFill(
                order_id=order.id,
                fill_type=FillType.DA_CLOSING,
                filled_price=p_da,
                filled_quantity=order.quantity_mwh,
                market_price_at_fill=p_da,
                timestamp_utc=hour_start,  # Use delivery hour timestamp
                gross_pnl=0.0  # P&L calculated later during RT settlement
            )
            
            self.session.add(order)
            self.session.add(fill)
            
            logger.debug(
                f"DA fill executed: order_id={order.order_id}, "
                f"side={order.side.value}, qty={order.quantity_mwh}, "
                f"fill_price=${p_da:.2f}, delivery_hour={hour_start}"
            )
            
            return {
                "order_id": order.order_id,
                "status": "filled",
                "filled_price": p_da,
                "filled_quantity": order.quantity_mwh,
                "delivery_hour": hour_start.isoformat(),
                "exec_ref": "DA_HOURLY"
            }
            
        except Exception as e:
            logger.error(f"Error executing DA fill for order {order.order_id}: {e}")
            return {
                "order_id": order.order_id,
                "status": "error", 
                "reason": str(e)
            }
    
    async def _reject_order_idempotent(self, order: TradingOrder, reason: str) -> Dict:
        """Reject order with idempotency protection"""
        
        try:
            # Double-check order status
            self.session.refresh(order)
            if order.status != OrderStatus.PENDING:
                return {
                    "order_id": order.order_id,
                    "status": "already_processed",
                    "reason": f"Order status is {order.status.value}"
                }
            
            # Update order status  
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            order.updated_at = datetime.utcnow()
            
            self.session.add(order)
            
            logger.debug(f"Order rejected: order_id={order.order_id}, reason={reason}")
            
            return {
                "order_id": order.order_id,
                "status": "rejected",
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error rejecting order {order.order_id}: {e}")
            return {
                "order_id": order.order_id,
                "status": "error",
                "reason": str(e)
            }
    
    def _is_order_expired(self, order: TradingOrder, current_time: datetime) -> bool:
        """Check if order has expired based on time-in-force and expiry settings"""
        
        # Check explicit expiry time first
        if order.expires_at and current_time > order.expires_at:
            return True
            
        # Time-in-force specific logic
        if order.time_in_force == TimeInForce.IOC:
            # IOC orders expire immediately if not filled on first tick
            return True
            
        elif order.time_in_force == TimeInForce.DAY:
            # DAY orders expire at end of trading day (midnight ET)
            from pytz import timezone
            et = timezone('US/Eastern')
            trading_day_end = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return current_time > trading_day_end
            
        elif order.time_in_force == TimeInForce.GTC:
            # GTC with market-specific defaults
            if order.market == MarketType.REAL_TIME:
                # RT orders expire after 4 hours if no explicit expiry
                default_expiry = order.created_at + timedelta(hours=4)
                return current_time > default_expiry
                
            elif order.market == MarketType.DAY_AHEAD:
                # DA orders expire after delivery hour has passed
                delivery_end = order.hour_start_utc + timedelta(hours=1)
                return current_time > delivery_end
        
        return False
    
    def _already_processed_at_timestamp(self, order: TradingOrder, ts_5m: datetime) -> bool:
        """Check if order was already processed at this exact RT timestamp (idempotency)"""
        
        # Check if there's already a fill record for this order at this timestamp
        existing_fill = self.session.exec(
            select(OrderFill).where(
                OrderFill.order_id == order.id,
                OrderFill.timestamp_utc == ts_5m,
                OrderFill.fill_type == FillType.RT_IMMEDIATE
            )
        ).first()
        
        return existing_fill is not None
    
    def _already_processed_for_da_hour(self, order: TradingOrder, hour_start: datetime) -> bool:
        """Check if order was already processed for this DA hour (idempotency)"""
        
        # Check if there's already a fill record for this order for this hour
        existing_fill = self.session.exec(
            select(OrderFill).where(
                OrderFill.order_id == order.id,
                OrderFill.timestamp_utc == hour_start,
                OrderFill.fill_type == FillType.DA_CLOSING
            )
        ).first()
        
        return existing_fill is not None

# Convenience functions for external triggering
async def trigger_rt_matching(session: Session, node_id: str, ts_5m: datetime, lmp: float) -> Dict:
    """Convenience function to trigger RT matching from external services"""
    matcher = DeterministicMatchingService(session)
    return await matcher.on_new_rt_tick(node_id, ts_5m, lmp)

async def trigger_da_matching(session: Session, node_id: str, hour_start: datetime, p_da: float) -> Dict:
    """Convenience function to trigger DA matching from external services"""
    matcher = DeterministicMatchingService(session)
    return await matcher.on_new_da_price(node_id, hour_start, p_da)