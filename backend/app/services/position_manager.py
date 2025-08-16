"""
Position Manager Service for Virtual Energy Trading Platform
Tracks net positions and validates trading logic
"""

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging
import os  # Add os import for environment variables
from ..models import (
    TradingOrder, OrderStatus, OrderSide, MarketType
)

logger = logging.getLogger(__name__)

class PositionManager:
    """
    Manages trading positions and validates order logic
    
    Key Rules:
    1. Cannot sell energy you haven't bought (no naked short selling)
    2. Day-Ahead positions are per hour slot
    3. Real-Time positions are per 5-minute slot
    4. Positions net out: Buy 10 MWh, Sell 6 MWh = Net Long 4 MWh
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def calculate_net_position(
        self, 
        user_id: str, 
        node: str, 
        market: MarketType,
        time_slot: datetime
    ) -> Dict:
        """
        Calculate net position for validation
        
        For RT orders: Calculate DAILY net position (not per-slot)
        For DA orders: Calculate per-hour position
        
        Returns:
            Dict with position details:
            - net_position: Net MWh position (positive = long, negative = short)
            - buy_volume: Total buy volume
            - sell_volume: Total sell volume
            - filled_orders: List of filled orders
        """
        if market == MarketType.REAL_TIME:
            # For RT: Use DAILY net position to allow intraday trading
            today_start = time_slot.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            statement = select(TradingOrder).where(
                TradingOrder.user_id == user_id,
                TradingOrder.node == node,
                TradingOrder.market == MarketType.REAL_TIME,
                TradingOrder.status == OrderStatus.FILLED,
                TradingOrder.hour_start_utc >= today_start,
                TradingOrder.hour_start_utc < today_end
            )
        else:
            # For DA: Use per-hour position (original logic)
            slot_start = time_slot.replace(minute=0, second=0, microsecond=0)
            slot_end = slot_start + timedelta(hours=1)
            
            statement = select(TradingOrder).where(
                TradingOrder.user_id == user_id,
                TradingOrder.node == node,
                TradingOrder.market == MarketType.DAY_AHEAD,
                TradingOrder.status == OrderStatus.FILLED,
                TradingOrder.hour_start_utc >= slot_start,
                TradingOrder.hour_start_utc < slot_end
            )
        
        filled_orders = self.session.exec(statement).all()
        
        # Calculate volumes
        buy_volume = Decimal('0')
        sell_volume = Decimal('0')
        
        for order in filled_orders:
            quantity = Decimal(str(order.filled_quantity or order.quantity_mwh))
            if order.side == OrderSide.BUY:
                buy_volume += quantity
            else:
                sell_volume += quantity
        
        net_position = buy_volume - sell_volume
        
        return {
            'net_position': float(net_position),
            'buy_volume': float(buy_volume),
            'sell_volume': float(sell_volume),
            'filled_orders': filled_orders,
            'time_slot': time_slot.isoformat()
        }
    
    def calculate_pending_position(
        self,
        user_id: str,
        node: str,
        market: MarketType,
        time_slot: datetime,
        include_pending: bool = True
    ) -> Dict:
        """
        Calculate position including pending orders
        
        This helps prevent over-selling before orders are matched
        """
        # Get current filled position
        current_position = self.calculate_net_position(user_id, node, market, time_slot)
        
        if not include_pending:
            return current_position
        
        # Determine time window based on market type
        if market == MarketType.DAY_AHEAD:
            slot_start = time_slot.replace(minute=0, second=0, microsecond=0)
            slot_end = slot_start + timedelta(hours=1)
            time_field = TradingOrder.hour_start_utc
        else:
            slot_start = time_slot
            slot_end = slot_start + timedelta(minutes=5)
            time_field = TradingOrder.time_slot_utc
        
        # Query pending orders
        statement = select(TradingOrder).where(
            TradingOrder.user_id == user_id,
            TradingOrder.node == node,
            TradingOrder.market == market,
            TradingOrder.status == OrderStatus.PENDING,
            time_field >= slot_start,
            time_field < slot_end
        )
        
        pending_orders = self.session.exec(statement).all()
        
        # Calculate pending volumes
        pending_buy = Decimal('0')
        pending_sell = Decimal('0')
        
        for order in pending_orders:
            quantity = Decimal(str(order.quantity_mwh))
            if order.side == OrderSide.BUY:
                pending_buy += quantity
            else:
                pending_sell += quantity
        
        # Calculate projected position
        projected_buy = Decimal(str(current_position['buy_volume'])) + pending_buy
        projected_sell = Decimal(str(current_position['sell_volume'])) + pending_sell
        projected_net = projected_buy - projected_sell
        
        return {
            'current_net_position': current_position['net_position'],
            'pending_buy_volume': float(pending_buy),
            'pending_sell_volume': float(pending_sell),
            'projected_net_position': float(projected_net),
            'projected_buy_volume': float(projected_buy),
            'projected_sell_volume': float(projected_sell),
            'time_slot': time_slot.isoformat()
        }
    
    def validate_order(
        self,
        user_id: str,
        node: str,
        market: MarketType,
        time_slot: datetime,
        side: OrderSide,
        quantity: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if an order can be placed based on position limits
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get current position including pending orders
        position = self.calculate_pending_position(user_id, node, market, time_slot)
        
        # Calculate what position would be after this order
        order_quantity = Decimal(str(quantity))
        
        if side == OrderSide.BUY:
            new_net_position = Decimal(str(position['projected_net_position'])) + order_quantity
        else:  # SELL
            new_net_position = Decimal(str(position['projected_net_position'])) - order_quantity
        
        # Check if sell order would result in negative position (short selling)
        if new_net_position < 0:
            max_sell = Decimal(str(position['projected_net_position']))
            if max_sell <= 0:
                return False, (
                    f"Cannot sell energy without buying first. "
                    f"Current net position: {position['current_net_position']:.1f} MWh"
                )
            else:
                return False, (
                    f"Cannot sell {quantity:.1f} MWh. "
                    f"Maximum sellable quantity: {float(max_sell):.1f} MWh "
                    f"(Current: {position['current_net_position']:.1f} MWh + "
                    f"Pending buys: {position['pending_buy_volume']:.1f} MWh - "
                    f"Pending sells: {position['pending_sell_volume']:.1f} MWh)"
                )
        
        # Additional checks can be added here (e.g., max position limits)
        max_position_limit = 100.0  # Maximum net position allowed
        
        if abs(float(new_net_position)) > max_position_limit:
            return False, (
                f"Order would exceed maximum position limit of {max_position_limit} MWh. "
                f"Projected position: {float(new_net_position):.1f} MWh"
            )
        
        return True, None
    
    def get_portfolio_summary(
        self,
        user_id: str,
        node: str,
        date: Optional[datetime] = None
    ) -> Dict:
        """
        Get a summary of all positions for a user
        """
        if date is None:
            date = datetime.utcnow()
        
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        # Get all orders for the day
        statement = select(TradingOrder).where(
            TradingOrder.user_id == user_id,
            TradingOrder.node == node,
            TradingOrder.hour_start_utc >= start_time,
            TradingOrder.hour_start_utc < end_time
        )
        
        all_orders = self.session.exec(statement).all()
        
        # Separate by market and status
        da_filled = [o for o in all_orders if o.market == MarketType.DAY_AHEAD and o.status == OrderStatus.FILLED]
        da_pending = [o for o in all_orders if o.market == MarketType.DAY_AHEAD and o.status == OrderStatus.PENDING]
        rt_filled = [o for o in all_orders if o.market == MarketType.REAL_TIME and o.status == OrderStatus.FILLED]
        rt_pending = [o for o in all_orders if o.market == MarketType.REAL_TIME and o.status == OrderStatus.PENDING]
        
        # Calculate totals
        def sum_volumes(orders):
            buy_vol = sum(o.filled_quantity or o.quantity_mwh for o in orders if o.side == OrderSide.BUY)
            sell_vol = sum(o.filled_quantity or o.quantity_mwh for o in orders if o.side == OrderSide.SELL)
            return buy_vol, sell_vol
        
        da_filled_buy, da_filled_sell = sum_volumes(da_filled)
        da_pending_buy, da_pending_sell = sum_volumes(da_pending)
        rt_filled_buy, rt_filled_sell = sum_volumes(rt_filled)
        rt_pending_buy, rt_pending_sell = sum_volumes(rt_pending)
        
        return {
            'user_id': user_id,
            'node': node,
            'date': date.strftime('%Y-%m-%d'),
            'day_ahead': {
                'filled': {
                    'buy_volume': da_filled_buy,
                    'sell_volume': da_filled_sell,
                    'net_position': da_filled_buy - da_filled_sell,
                    'order_count': len(da_filled)
                },
                'pending': {
                    'buy_volume': da_pending_buy,
                    'sell_volume': da_pending_sell,
                    'net_position': da_pending_buy - da_pending_sell,
                    'order_count': len(da_pending)
                }
            },
            'real_time': {
                'filled': {
                    'buy_volume': rt_filled_buy,
                    'sell_volume': rt_filled_sell,
                    'net_position': rt_filled_buy - rt_filled_sell,
                    'order_count': len(rt_filled)
                },
                'pending': {
                    'buy_volume': rt_pending_buy,
                    'sell_volume': rt_pending_sell,
                    'net_position': rt_pending_buy - rt_pending_sell,
                    'order_count': len(rt_pending)
                }
            },
            'total': {
                'buy_volume': da_filled_buy + da_pending_buy + rt_filled_buy + rt_pending_buy,
                'sell_volume': da_filled_sell + da_pending_sell + rt_filled_sell + rt_pending_sell,
                'net_exposure': (da_filled_buy + rt_filled_buy) - (da_filled_sell + rt_filled_sell)
            }
        }
    
    def get_hourly_positions(
        self,
        user_id: str,
        node: str,
        date: datetime
    ) -> List[Dict]:
        """
        Get hour-by-hour position breakdown for a specific date
        """
        positions = []
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for hour in range(24):
            hour_start = start_date + timedelta(hours=hour)
            
            # Get DA position
            da_position = self.calculate_pending_position(
                user_id, node, MarketType.DAY_AHEAD, hour_start
            )
            
            # Get RT positions (12 5-minute slots per hour)
            rt_net_position = 0
            rt_slots = []
            
            for minute in range(0, 60, 5):
                slot_time = hour_start + timedelta(minutes=minute)
                rt_position = self.calculate_net_position(
                    user_id, node, MarketType.REAL_TIME, slot_time
                )
                rt_net_position += rt_position['net_position']
                
                if rt_position['net_position'] != 0:
                    rt_slots.append({
                        'time': slot_time.strftime('%H:%M'),
                        'net_position': rt_position['net_position']
                    })
            
            positions.append({
                'hour': hour_start.strftime('%H:00'),
                'day_ahead': {
                    'net_position': da_position['current_net_position'],
                    'pending_position': da_position['projected_net_position'] - da_position['current_net_position']
                },
                'real_time': {
                    'net_position': rt_net_position,
                    'active_slots': rt_slots
                },
                'total_exposure': da_position['current_net_position'] + rt_net_position
            })
        
        return positions
