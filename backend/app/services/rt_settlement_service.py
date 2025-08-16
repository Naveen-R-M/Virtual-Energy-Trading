"""
Real-Time Settlement Service
Handles settlement of RT orders based on published 5-minute interval prices
"""

from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from ..models import (
    TradingOrder, OrderStatus, MarketType, OrderSide,
    RealTimePrice, OrderFill, FillType
)
from ..services.rt_interval_manager import RTIntervalManager
from ..services.market_data import MarketDataService

logger = logging.getLogger(__name__)

class RTSettlementService:
    """
    Service for settling RT orders when interval prices become available
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.interval_manager = RTIntervalManager()
        self.market_data_service = MarketDataService(session)
    
    async def check_and_settle_pending_orders(
        self,
        node: str = "PJM_RTO",
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Check for pending RT orders and settle those with available price data
        
        Args:
            node: Grid node to check
            user_id: Optional user filter
            
        Returns:
            Summary of settlement results
        """
        results = {
            'checked': 0,
            'settled': 0,
            'filled': 0,
            'rejected': 0,
            'waiting': 0,
            'errors': 0,
            'details': []
        }
        
        try:
            # Get all pending RT orders
            query = select(TradingOrder).where(
                TradingOrder.market == MarketType.REAL_TIME,
                TradingOrder.status == OrderStatus.PENDING,
                TradingOrder.node == node
            )
            
            if user_id:
                query = query.where(TradingOrder.user_id == user_id)
            
            pending_orders = self.session.exec(query).all()
            results['checked'] = len(pending_orders)
            
            logger.info(f"Found {len(pending_orders)} pending RT orders to check")
            
            for order in pending_orders:
                try:
                    # Determine the interval for this order
                    interval_start = order.time_slot_utc or order.hour_start_utc
                    
                    # Check settlement status
                    settlement_status = self.interval_manager.get_settlement_status(
                        interval_start,
                        datetime.utcnow()
                    )
                    
                    order_detail = {
                        'order_id': order.order_id,
                        'interval': self.interval_manager.format_interval_display(interval_start),
                        'status': None,
                        'message': None
                    }
                    
                    if not settlement_status['can_settle']:
                        # Can't settle yet
                        results['waiting'] += 1
                        order_detail['status'] = 'waiting'
                        order_detail['message'] = settlement_status['message']
                        logger.debug(f"Order {order.order_id}: {settlement_status['message']}")
                    else:
                        # Try to settle
                        settlement_result = await self._settle_order(order, interval_start)
                        
                        if settlement_result['settled']:
                            results['settled'] += 1
                            if settlement_result['status'] == 'filled':
                                results['filled'] += 1
                            else:
                                results['rejected'] += 1
                            
                            order_detail['status'] = settlement_result['status']
                            order_detail['message'] = settlement_result['message']
                            order_detail['filled_price'] = settlement_result.get('filled_price')
                        else:
                            results['waiting'] += 1
                            order_detail['status'] = 'waiting'
                            order_detail['message'] = settlement_result['message']
                    
                    results['details'].append(order_detail)
                    
                except Exception as e:
                    logger.error(f"Error processing order {order.order_id}: {e}")
                    results['errors'] += 1
                    results['details'].append({
                        'order_id': order.order_id,
                        'status': 'error',
                        'message': str(e)
                    })
            
            # Commit all changes
            self.session.commit()
            
            logger.info(
                f"Settlement complete: {results['settled']} settled "
                f"({results['filled']} filled, {results['rejected']} rejected), "
                f"{results['waiting']} waiting"
            )
            
        except Exception as e:
            logger.error(f"Error in settlement check: {e}")
            self.session.rollback()
            results['errors'] += 1
            results['message'] = str(e)
        
        return results
    
    async def _settle_order(
        self,
        order: TradingOrder,
        interval_start: datetime
    ) -> Dict:
        """
        Attempt to settle a single RT order
        
        Args:
            order: The order to settle
            interval_start: Start of the 5-minute interval
            
        Returns:
            Dict with settlement results
        """
        result = {
            'settled': False,
            'status': None,
            'message': None,
            'filled_price': None
        }
        
        try:
            # Try to get the RT price for this interval
            interval_end = interval_start + timedelta(minutes=5)
            
            # Check database first
            rt_price_record = self.session.exec(
                select(RealTimePrice).where(
                    RealTimePrice.node == order.node,
                    RealTimePrice.timestamp_utc >= interval_start,
                    RealTimePrice.timestamp_utc < interval_end
                )
            ).first()
            
            if not rt_price_record:
                # Try to fetch from API
                logger.info(f"Fetching RT price for {order.node} interval {interval_start}")
                
                try:
                    prices = await self.market_data_service.fetch_real_time_prices(
                        order.node,
                        interval_start,
                        interval_end
                    )
                    
                    if prices:
                        # Use the first price in the interval
                        rt_price = prices[0]['price']
                        
                        # Save to database
                        rt_price_record = RealTimePrice(
                            node=order.node,
                            timestamp_utc=interval_start,
                            price=rt_price
                        )
                        self.session.add(rt_price_record)
                    else:
                        # No price available yet
                        result['message'] = f"RT price not yet available for interval {interval_start.strftime('%H:%M')}"
                        return result
                        
                except Exception as e:
                    logger.warning(f"Could not fetch RT price: {e}")
                    result['message'] = f"Waiting for RT price data: {str(e)}"
                    return result
            
            # We have a price, now settle the order
            rt_price = rt_price_record.price
            
            # Check if order should be filled based on limit price
            should_fill = self._should_fill_order(order, rt_price)
            
            if should_fill:
                # Fill the order
                order.status = OrderStatus.FILLED
                order.filled_price = rt_price
                order.filled_quantity = order.quantity_mwh
                order.filled_at = datetime.utcnow()
                order.updated_at = datetime.utcnow()
                
                # Create fill record
                fill = OrderFill(
                    order_id=order.id,
                    fill_type=FillType.RT_IMMEDIATE,
                    filled_price=rt_price,
                    filled_quantity=order.quantity_mwh,
                    market_price_at_fill=rt_price,
                    timestamp_utc=datetime.utcnow()
                )
                self.session.add(fill)
                
                result['settled'] = True
                result['status'] = 'filled'
                result['filled_price'] = rt_price
                result['message'] = f"Filled at ${rt_price:.2f}/MWh (interval {interval_start.strftime('%H:%M')})"
                
                logger.info(f"Order {order.order_id} FILLED at ${rt_price:.2f}")
                
            else:
                # Reject the order
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Limit not met: ${order.limit_price:.2f} vs RT ${rt_price:.2f}"
                order.updated_at = datetime.utcnow()
                
                result['settled'] = True
                result['status'] = 'rejected'
                result['message'] = order.rejection_reason
                
                logger.info(f"Order {order.order_id} REJECTED: {order.rejection_reason}")
            
            self.session.add(order)
            
        except Exception as e:
            logger.error(f"Error settling order {order.order_id}: {e}")
            result['message'] = f"Settlement error: {str(e)}"
        
        return result
    
    def _should_fill_order(self, order: TradingOrder, rt_price: float) -> bool:
        """
        Determine if an order should be filled at the given RT price
        
        Args:
            order: The order to check
            rt_price: The real-time price
            
        Returns:
            True if order should be filled, False otherwise
        """
        if order.side == OrderSide.BUY:
            # Buy order fills if limit >= market price
            return order.limit_price >= rt_price
        else:
            # Sell order fills if limit <= market price
            return order.limit_price <= rt_price
    
    async def get_pending_orders_status(
        self,
        node: str = "PJM_RTO",
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get status of all pending RT orders
        
        Returns:
            List of order status dictionaries
        """
        status_list = []
        
        # Get pending orders
        query = select(TradingOrder).where(
            TradingOrder.market == MarketType.REAL_TIME,
            TradingOrder.status == OrderStatus.PENDING,
            TradingOrder.node == node
        )
        
        if user_id:
            query = query.where(TradingOrder.user_id == user_id)
        
        pending_orders = self.session.exec(query).all()
        
        for order in pending_orders:
            interval_start = order.time_slot_utc or order.hour_start_utc
            settlement_status = self.interval_manager.get_settlement_status(
                interval_start,
                datetime.utcnow()
            )
            
            status_list.append({
                'order_id': order.order_id,
                'interval': self.interval_manager.format_interval_display(interval_start),
                'side': order.side.value,
                'quantity': order.quantity_mwh,
                'limit_price': order.limit_price,
                'can_settle': settlement_status['can_settle'],
                'is_complete': settlement_status['is_complete'],
                'expected_settlement': settlement_status['expected_settlement_time'].isoformat(),
                'message': settlement_status['message']
            })
        
        return status_list
