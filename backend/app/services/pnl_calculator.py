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
    
    async def calculate_order_pnl(self, order_id: str) -> Optional[Dict]:
        """
        Calculate P&L for a specific order
        """
        try:
            statement = select(TradingOrder).where(TradingOrder.order_id == order_id)
            order = self.session.exec(statement).first()
            
            if not order or order.status != OrderStatus.FILLED:
                return None
            
            if order.market == MarketType.DAY_AHEAD:
                # For DA orders, calculate offset against RT prices
                hour_start = order.hour_start_utc
                hour_end = hour_start + timedelta(hours=1)
                rt_prices = await self._get_rt_prices_for_hour(order.node, hour_start, hour_end)
                
                if not rt_prices:
                    rt_avg = self._generate_mock_rt_avg_for_hour(hour_start.hour)
                else:
                    rt_avg = sum(rt_prices) / len(rt_prices)
                
                if order.side == OrderSide.BUY:
                    pnl = (rt_avg - order.filled_price) * order.filled_quantity
                else:
                    pnl = (order.filled_price - rt_avg) * order.filled_quantity
                
                return {
                    "order_id": order.order_id,
                    "market": "day-ahead",
                    "side": order.side.value,
                    "quantity_mwh": order.filled_quantity,
                    "da_fill_price": order.filled_price,
                    "rt_avg_price": round(rt_avg, 2),
                    "pnl": round(pnl, 2),
                    "hour_start": hour_start.isoformat()
                }
            
            else:  # Real-Time order
                # For RT orders, P&L is immediate
                fills = self.session.exec(
                    select(OrderFill).where(OrderFill.order_id == order.id)
                ).all()
                
                pnl = sum(fill.gross_pnl or 0 for fill in fills)
                
                return {
                    "order_id": order.order_id,
                    "market": "real-time",
                    "side": order.side.value,
                    "quantity_mwh": order.filled_quantity,
                    "execution_price": order.filled_price,
                    "pnl": round(pnl, 2),
                    "time_slot": order.time_slot_utc.isoformat() if order.time_slot_utc else None
                }
                
        except Exception as e:
            logger.error(f"Error calculating order P&L: {e}")
            return None
    
    async def get_performance_analytics(self, node: str, days: int) -> Dict:
        """
        Get comprehensive performance analytics for the specified period
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get all P&L records for the period
            pnl_records = self.session.exec(
                select(PnLRecord).where(
                    PnLRecord.node == node,
                    PnLRecord.date >= start_date,
                    PnLRecord.date <= end_date
                )
            ).all()
            
            if not pnl_records:
                # Generate analytics from orders
                return await self._generate_analytics_from_orders(node, start_date, end_date)
            
            # Calculate metrics
            total_pnl = sum(r.total_pnl for r in pnl_records)
            winning_days = len([r for r in pnl_records if r.total_pnl > 0])
            losing_days = len([r for r in pnl_records if r.total_pnl < 0])
            
            # Calculate max drawdown
            cumulative_pnl = 0
            peak_pnl = 0
            max_drawdown = 0
            
            for record in sorted(pnl_records, key=lambda x: x.date):
                cumulative_pnl += record.total_pnl
                if cumulative_pnl > peak_pnl:
                    peak_pnl = cumulative_pnl
                drawdown = peak_pnl - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return {
                "node": node,
                "period_days": days,
                "total_pnl": round(total_pnl, 2),
                "winning_days": winning_days,
                "losing_days": losing_days,
                "win_rate": round(winning_days / (winning_days + losing_days), 3) if (winning_days + losing_days) > 0 else 0,
                "max_drawdown": round(max_drawdown, 2),
                "avg_daily_pnl": round(total_pnl / len(pnl_records), 2) if pnl_records else 0,
                "total_da_volume": sum(r.da_volume_mwh for r in pnl_records),
                "total_rt_volume": sum(r.rt_volume_mwh for r in pnl_records)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            raise
    
    async def _generate_analytics_from_orders(self, node: str, start_date: datetime, end_date: datetime) -> Dict:
        """
        Generate analytics directly from orders when P&L records don't exist
        """
        # This is a simplified version - in production, you'd calculate from actual orders
        return {
            "node": node,
            "period_days": (end_date - start_date).days,
            "total_pnl": 0.0,
            "winning_days": 0,
            "losing_days": 0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "avg_daily_pnl": 0.0,
            "total_da_volume": 0.0,
            "total_rt_volume": 0.0,
            "message": "No historical data available"
        }
    
    async def save_pnl_record(self, date: datetime, node: str, user_id: str):
        """
        Save calculated P&L to database for historical tracking
        """
        try:
            # Calculate P&L for both markets
            portfolio_data = await self.calculate_portfolio_pnl(date, node)
            
            # Check if record already exists
            existing = self.session.exec(
                select(PnLRecord).where(
                    PnLRecord.user_id == user_id,
                    PnLRecord.node == node,
                    PnLRecord.date == date
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.da_pnl = portfolio_data["market_breakdown"]["day_ahead_pnl"]
                existing.rt_pnl = portfolio_data["market_breakdown"]["real_time_pnl"]
                existing.total_pnl = portfolio_data["portfolio_pnl"]
                existing.updated_at = datetime.utcnow()
            else:
                # Create new record
                new_record = PnLRecord(
                    user_id=user_id,
                    node=node,
                    date=date,
                    da_pnl=portfolio_data["market_breakdown"]["day_ahead_pnl"],
                    rt_pnl=portfolio_data["market_breakdown"]["real_time_pnl"],
                    total_pnl=portfolio_data["portfolio_pnl"],
                    winning_trades=portfolio_data["performance_metrics"]["profitable_trades"],
                    total_trades=portfolio_data["performance_metrics"]["total_trades"]
                )
                self.session.add(new_record)
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving P&L record: {e}")
            raise
    
    async def calculate_multi_day_pnl(self, start_date: datetime, end_date: datetime, node: str) -> Dict:
        """
        Calculate P&L for multiple days
        """
        try:
            daily_pnl = []
            total_pnl = 0.0
            
            current_date = start_date
            while current_date <= end_date:
                day_pnl = await self.calculate_portfolio_pnl(current_date, node)
                daily_pnl.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "pnl": day_pnl["portfolio_pnl"],
                    "da_pnl": day_pnl["market_breakdown"]["day_ahead_pnl"],
                    "rt_pnl": day_pnl["market_breakdown"]["real_time_pnl"]
                })
                total_pnl += day_pnl["portfolio_pnl"]
                current_date += timedelta(days=1)
            
            return {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "node": node,
                "total_pnl": round(total_pnl, 2),
                "daily_breakdown": daily_pnl,
                "summary": {
                    "days_analyzed": len(daily_pnl),
                    "profitable_days": len([d for d in daily_pnl if d["pnl"] > 0]),
                    "loss_days": len([d for d in daily_pnl if d["pnl"] < 0]),
                    "avg_daily_pnl": round(total_pnl / len(daily_pnl), 2) if daily_pnl else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating multi-day P&L: {e}")
            raise
