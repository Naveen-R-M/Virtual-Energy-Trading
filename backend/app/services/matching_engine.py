"""
Matching Engine for Virtual Energy Trading Platform
Handles order matching for both Day-Ahead and Real-Time markets
"""

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from ..models import (
    TradingOrder, OrderFill, DayAheadPrice, RealTimePrice,
    MarketType, OrderStatus, OrderSide, FillType
)

logger = logging.getLogger(__name__)

class MatchingResult:
    """Result of order matching operation"""
    def __init__(self, order_id: str, status: str, filled_price: Optional[float] = None,
                 filled_quantity: Optional[float] = None, reason: Optional[str] = None):
        self.order_id = order_id
        self.status = status
        self.filled_price = filled_price
        self.filled_quantity = filled_quantity
        self.reason = reason

class MatchingEngine:
    """
    Order matching engine supporting both Day-Ahead and Real-Time markets
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    async def match_day_ahead_orders(self, trading_date: datetime, node: str) -> List[MatchingResult]:
        """
        Match all pending Day-Ahead orders for a specific date against DA closing prices
        """
        results = []
        
        try:
            start_time = trading_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            pending_orders = self.session.exec(
                select(TradingOrder).where(
                    TradingOrder.node == node,
                    TradingOrder.market == MarketType.DAY_AHEAD,
                    TradingOrder.status == OrderStatus.PENDING,
                    TradingOrder.hour_start_utc >= start_time,
                    TradingOrder.hour_start_utc < end_time
                )
            ).all()
            
            logger.info(f"Found {len(pending_orders)} pending DA orders for {trading_date.date()}")
            
            for order in pending_orders:
                da_price_record = self.session.exec(
                    select(DayAheadPrice).where(
                        DayAheadPrice.node == node,
                        DayAheadPrice.hour_start_utc == order.hour_start_utc
                    )
                ).first()
                
                if not da_price_record:
                    result = await self._reject_order(
                        order, 
                        "No Day-Ahead closing price available"
                    )
                    results.append(result)
                    continue
                
                da_closing_price = da_price_record.close_price
                should_fill = self._should_fill_da_order(order, da_closing_price)
                
                if should_fill:
                    result = await self._fill_da_order(order, da_closing_price)
                    results.append(result)
                else:
                    result = await self._reject_order(
                        order,
                        f"Limit not met: ${order.limit_price:.2f} vs DA close ${da_closing_price:.2f}"
                    )
                    results.append(result)
            
            self.session.commit()
            logger.info(f"DA matching completed: {len(results)} orders processed")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in DA matching: {e}")
            raise
        
        return results
    
    async def execute_real_time_order(self, order_id: int) -> MatchingResult:
        """Execute a Real-Time order immediately against current RT price"""
        try:
            order = self.session.get(TradingOrder, order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.market != MarketType.REAL_TIME:
                raise ValueError("Order is not a Real-Time order")
            
            if order.status != OrderStatus.PENDING:
                raise ValueError(f"Order status is {order.status}, not pending")
            
            current_rt_price = await self._get_current_rt_price(order.node)
            
            if current_rt_price is None:
                result = await self._reject_order(order, "No Real-Time price available")
                return result
            
            should_fill = self._should_fill_rt_order(order, current_rt_price)
            
            if should_fill:
                result = await self._fill_rt_order(order, current_rt_price)
                self.session.commit()
                logger.info(f"RT order {order.order_id} filled at ${current_rt_price:.2f}")
                return result
            else:
                result = await self._reject_order(
                    order,
                    f"RT limit not met: ${order.limit_price:.2f} vs RT price ${current_rt_price:.2f}"
                )
                self.session.commit()
                return result
                
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error executing RT order {order_id}: {e}")
            raise
    
    def _should_fill_da_order(self, order: TradingOrder, da_closing_price: float) -> bool:
        """Determine if a DA order should be filled"""
        if order.side == OrderSide.BUY:
            return order.limit_price >= da_closing_price
        else:  # SELL
            return order.limit_price <= da_closing_price
    
    def _should_fill_rt_order(self, order: TradingOrder, rt_price: float) -> bool:
        """Determine if an RT order should be filled"""
        if order.side == OrderSide.BUY:
            return order.limit_price >= rt_price
        else:  # SELL
            return order.limit_price <= rt_price
    
    async def _fill_da_order(self, order: TradingOrder, da_closing_price: float) -> MatchingResult:
        """Fill a Day-Ahead order at DA closing price"""
        order.status = OrderStatus.FILLED
        order.filled_price = da_closing_price
        order.filled_quantity = order.quantity_mwh
        order.filled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        fill = OrderFill(
            order_id=order.id,
            fill_type=FillType.DA_CLOSING,
            filled_price=da_closing_price,
            filled_quantity=order.quantity_mwh,
            market_price_at_fill=da_closing_price,
            timestamp_utc=datetime.utcnow()
        )
        
        self.session.add(order)
        self.session.add(fill)
        
        return MatchingResult(
            order_id=order.order_id,
            status="filled",
            filled_price=da_closing_price,
            filled_quantity=order.quantity_mwh,
            reason="Filled at DA closing price"
        )
    
    async def _fill_rt_order(self, order: TradingOrder, rt_price: float) -> MatchingResult:
        """Fill a Real-Time order at current RT price"""
        order.status = OrderStatus.FILLED
        order.filled_price = rt_price
        order.filled_quantity = order.quantity_mwh
        order.filled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        fill = OrderFill(
            order_id=order.id,
            fill_type=FillType.RT_IMMEDIATE,
            filled_price=rt_price,
            filled_quantity=order.quantity_mwh,
            market_price_at_fill=rt_price,
            timestamp_utc=datetime.utcnow(),
            gross_pnl=0.0  # RT orders have immediate settlement
        )
        
        self.session.add(order)
        self.session.add(fill)
        
        return MatchingResult(
            order_id=order.order_id,
            status="filled",
            filled_price=rt_price,
            filled_quantity=order.quantity_mwh,
            reason="Filled at current RT price"
        )
    
    async def _reject_order(self, order: TradingOrder, reason: str) -> MatchingResult:
        """Reject an order with reason"""
        order.status = OrderStatus.REJECTED
        order.rejection_reason = reason
        order.updated_at = datetime.utcnow()
        
        self.session.add(order)
        
        return MatchingResult(
            order_id=order.order_id,
            status="rejected",
            reason=reason
        )
    
    async def _get_current_rt_price(self, node: str) -> Optional[float]:
        """Get current Real-Time price for a node"""
        statement = select(RealTimePrice).where(
            RealTimePrice.node == node
        ).order_by(RealTimePrice.timestamp_utc.desc()).limit(1)
        
        latest_price = self.session.exec(statement).first()
        
        if latest_price:
            return latest_price.price
        
        # Generate mock current price
        import random
        import math
        current_hour = datetime.utcnow().hour
        
        base_price = 45.0
        if 14 <= current_hour <= 18:  # Peak hours
            base_price = 65.0
        elif 6 <= current_hour <= 9:   # Morning ramp
            base_price = 55.0
        elif 20 <= current_hour <= 23: # Evening
            base_price = 48.0
        else:  # Off-peak
            base_price = 35.0
        
        volatility = (random.random() - 0.5) * 15
        mock_price = max(10.0, base_price + volatility)
        
        logger.info(f"Using mock RT price for {node}: ${mock_price:.2f}")
        return round(mock_price, 2)
