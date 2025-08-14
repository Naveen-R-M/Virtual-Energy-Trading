"""
P&L Calculator Service for Virtual Energy Trading Platform
Calculates profit/loss for both Day-Ahead and Real-Time markets
"""

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from ..models import (
    TradingOrder, OrderFill, DayAheadPrice, RealTimePrice, PnLRecord,
    MarketType, OrderStatus, OrderSide, FillType
)

logger = logging.getLogger(__name__)

class PnLCalculator:
    """
    P&L calculation engine for energy trading
    
    Key concepts:
    - Day-Ahead orders: Filled at DA closing price, offset against RT prices during delivery
    - Real-Time orders: Immediate settlement, no offset needed
    - Portfolio P&L: Combined performance across both markets
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    async def calculate_da_pnl(self, date: datetime, node: str) -> Dict:
        """
        Calculate P&L for Day-Ahead orders offset against Real-Time prices
        
        Logic:
        - BUY DA at $50, RT avg $55 during delivery hour → Profit = ($55 - $50) × quantity
        - SELL DA at $50, RT avg $45 during delivery hour → Profit = ($50 - $45) × quantity
        """
        try:
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            # Get all filled DA orders for the date
            filled_da_orders = self.session.exec(
                select(TradingOrder).where(
                    TradingOrder.node == node,
                    TradingOrder.market == MarketType.DAY_AHEAD,
                    TradingOrder.status == OrderStatus.FILLED,
                    TradingOrder.hour_start_utc >= start_time,
                    TradingOrder.hour_start_utc < end_time
                )
            ).all()
            
            hourly_pnl = []
            total_pnl = 0.0
            
            for hour in range(24):
                hour_start = start_time + timedelta(hours=hour)
                hour_end = hour_start + timedelta(hours=1)
                
                # Get DA orders for this hour
                hour_orders = [
                    order for order in filled_da_orders 
                    if order.hour_start_utc == hour_start
                ]
                
                if not hour_orders:
                    hourly_pnl.append({
                        "hour_start": hour_start.isoformat(),
                        "da_orders": [],
                        "rt_avg_price": None,
                        "hour_pnl": 0.0
                    })
                    continue
                
                # Get RT prices for this hour (5-minute intervals)
                rt_prices = await self._get_rt_prices_for_hour(node, hour_start, hour_end)
                
                if not rt_prices:
                    # Use mock RT price if no data
                    rt_avg = self._generate_mock_rt_avg_for_hour(hour)
                    logger.warning(f"Using mock RT price for hour {hour}: ${rt_avg:.2f}")
                else:
                    rt_avg = sum(rt_prices) / len(rt_prices)
                
                # Calculate P&L for each order in this hour
                hour_pnl_value = 0.0
                order_pnls = []
                
                for order in hour_orders:
                    da_fill_price = order.filled_price
                    quantity = order.filled_quantity
                    
                    if order.side == OrderSide.BUY:
                        # BUY: profit if RT > DA
                        order_pnl = (rt_avg - da_fill_price) * quantity
                    else:  # SELL
                        # SELL: profit if DA > RT
                        order_pnl = (da_fill_price - rt_avg) * quantity
                    
                    hour_pnl_value += order_pnl
                    order_pnls.append({
                        "order_id": order.order_id,
                        "side": order.side.value,
                        "quantity_mwh": quantity,
                        "da_fill_price": da_fill_price,
                        "rt_avg_price": rt_avg,
                        "order_pnl": round(order_pnl, 2)
                    })
                
                total_pnl += hour_pnl_value
                
                hourly_pnl.append({
                    "hour_start": hour_start.isoformat(),
                    "da_orders": order_pnls,
                    "rt_avg_price": round(rt_avg, 2),
                    "hour_pnl": round(hour_pnl_value, 2)
                })
            
            return {
                "date": date.strftime("%Y-%m-%d"),
                "node": node,
                "market": "day-ahead",
                "total_pnl": round(total_pnl, 2),
                "hourly_breakdown": hourly_pnl,
                "summary": {
                    "total_orders": len(filled_da_orders),
                    "profitable_hours": len([h for h in hourly_pnl if h["hour_pnl"] > 0]),
                    "loss_hours": len([h for h in hourly_pnl if h["hour_pnl"] < 0])
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating DA P&L: {e}")
            raise
    
    async def calculate_rt_pnl(self, date: datetime, node: str) -> Dict:
        """
        Calculate P&L for Real-Time orders (immediate settlement)
        
        Logic:
        - RT orders are settled immediately at execution price
        - P&L is realized instantly, no offset calculation needed
        """
        try:
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            # Get all filled RT orders for the date
            filled_rt_orders = self.session.exec(
                select(TradingOrder).where(
                    TradingOrder.node == node,
                    TradingOrder.market == MarketType.REAL_TIME,
                    TradingOrder.status == OrderStatus.FILLED,
                    TradingOrder.created_at >= start_time,
                    TradingOrder.created_at < end_time
                )
            ).all()
            
            # Get associated fills
            total_pnl = 0.0
            order_details = []
            
            for order in filled_rt_orders:
                # Get fills for this order
                fills = self.session.exec(
                    select(OrderFill).where(OrderFill.order_id == order.id)
                ).all()
                
                order_pnl = sum(fill.gross_pnl or 0 for fill in fills)
                total_pnl += order_pnl
                
                order_details.append({
                    "order_id": order.order_id,
                    "time_slot": order.time_slot_utc.isoformat() if order.time_slot_utc else None,
                    "side": order.side.value,
                    "quantity_mwh": order.filled_quantity,
                    "execution_price": order.filled_price,
                    "order_pnl": round(order_pnl, 2),
                    "filled_at": order.filled_at.isoformat() if order.filled_at else None
                })
            
            return {
                "date": date.strftime("%Y-%m-%d"),
                "node": node,
                "market": "real-time",
                "total_pnl": round(total_pnl, 2),
                "order_details": order_details,
                "summary": {
                    "total_orders": len(filled_rt_orders),
                    "profitable_orders": len([o for o in order_details if o["order_pnl"] > 0]),
                    "loss_orders": len([o for o in order_details if o["order_pnl"] < 0])
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating RT P&L: {e}")
            raise
    
    async def calculate_portfolio_pnl(self, date: datetime, node: str) -> Dict:
        """
        Calculate combined portfolio P&L for both Day-Ahead and Real-Time markets
        """
        try:
            # Get P&L for both markets
            da_pnl_data = await self.calculate_da_pnl(date, node)
            rt_pnl_data = await self.calculate_rt_pnl(date, node)
            
            # Combine results
            total_pnl = da_pnl_data["total_pnl"] + rt_pnl_data["total_pnl"]
            
            # Calculate performance metrics
            all_orders = da_pnl_data["summary"]["total_orders"] + rt_pnl_data["summary"]["total_orders"]
            profitable_trades = (
                da_pnl_data["summary"]["profitable_hours"] + 
                rt_pnl_data["summary"]["profitable_orders"]
            )
            
            win_rate = profitable_trades / all_orders if all_orders > 0 else 0.0
            
            return {
                "date": date.strftime("%Y-%m-%d"),
                "node": node,
                "portfolio_pnl": round(total_pnl, 2),
                "market_breakdown": {
                    "day_ahead_pnl": da_pnl_data["total_pnl"],
                    "real_time_pnl": rt_pnl_data["total_pnl"]
                },
                "performance_metrics": {
                    "total_trades": all_orders,
                    "profitable_trades": profitable_trades,
                    "win_rate": round(win_rate, 3),
                    "avg_pnl_per_trade": round(total_pnl / all_orders, 2) if all_orders > 0 else 0.0
                },
                "detailed_breakdown": {
                    "day_ahead": da_pnl_data,
                    "real_time": rt_pnl_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio P&L: {e}")
            raise
    
    async def _get_rt_prices_for_hour(self, node: str, hour_start: datetime, hour_end: datetime) -> List[float]:
        """
        Get all 5-minute RT prices for a specific hour
        """
        statement = select(RealTimePrice).where(
            RealTimePrice.node == node,
            RealTimePrice.timestamp_utc >= hour_start,
            RealTimePrice.timestamp_utc < hour_end
        ).order_by(RealTimePrice.timestamp_utc)
        
        rt_records = self.session.exec(statement).all()
        return [record.price for record in rt_records]
    
    def _generate_mock_rt_avg_for_hour(self, hour: int) -> float:
        """
        Generate a mock RT average price for a specific hour
        Used when no real RT data is available
        """
        import random
        import math
        
        # Base price pattern similar to DA but more volatile
        base_price = 45.0
        
        if 6 <= hour <= 9:  # Morning ramp
            base_price = 42.0 + (hour - 6) * 6
        elif 14 <= hour <= 19:  # Peak hours
            base_price = 50.0 + 15 * (1 + math.sin((hour - 16) * math.pi / 3)) / 2
        elif 20 <= hour <= 23:  # Evening decline
            base_price = 48.0 - (hour - 20) * 3
        else:  # Off-peak
            base_price = 35.0
        
        # Add higher volatility for RT
        volatility = random.uniform(0.8, 1.2)
        mock_price = max(10.0, base_price * volatility)
        
        return round(mock_price, 2)
