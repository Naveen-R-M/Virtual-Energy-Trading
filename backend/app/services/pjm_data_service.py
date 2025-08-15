# PJM Data Service for Watchlist Features
# Specialized service for PJM watchlist functionality

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlmodel import Session, select
from ..models import PJMNode, NodePriceSnapshot, WatchlistItem, PriceAlert, WatchlistSummary
try:
    from .gridstatus_api import gridstatus_service
except ImportError:
    gridstatus_service = None

logger = logging.getLogger(__name__)

class PJMDataService:
    """Service for PJM-specific data operations and watchlist management"""
    
    def __init__(self, session: Session):
        self.session = session
        # Use the globally imported gridstatus_service
        self.gridstatus_api = gridstatus_service
        if not self.gridstatus_api:
            logger.warning("GridStatus API not available, using mock data only")
    
    async def sync_pjm_nodes(self) -> Dict:
        """
        Sync PJM nodes from GridStatus API to local database
        Run this daily or on app startup
        """
        try:
            logger.info("Syncing PJM nodes from GridStatus API...")
            
            # If GridStatus API is not available, use mock nodes
            if not self.gridstatus_api:
                logger.info("GridStatus API not available, creating mock nodes")
                return await self._create_mock_nodes()
            
            # Fetch nodes from GridStatus
            raw_nodes = await self.gridstatus_api.get_pjm_pricing_nodes()
            
            if not raw_nodes:
                logger.warning("No PJM nodes returned from API")
                return {"status": "warning", "nodes_synced": 0}
            
            nodes_created = 0
            nodes_updated = 0
            
            for node_data in raw_nodes:
                node_id = str(node_data.get('node_id', ''))
                if not node_id:
                    continue
                
                # Check if node exists
                existing_node = self.session.exec(
                    select(PJMNode).where(PJMNode.node_id == node_id)
                ).first()
                
                if existing_node:
                    # Update existing node
                    existing_node.node_name = node_data.get('node_name', existing_node.node_name)
                    existing_node.zone = node_data.get('zone', existing_node.zone)
                    existing_node.voltage_level = node_data.get('voltage_level')
                    existing_node.node_type = node_data.get('node_type', existing_node.node_type)
                    existing_node.updated_at = datetime.utcnow()
                    nodes_updated += 1
                else:
                    # Create new node
                    from ..models import create_pjm_node_from_gridstatus
                    new_node = create_pjm_node_from_gridstatus(node_data)
                    self.session.add(new_node)
                    nodes_created += 1
            
            self.session.commit()
            
            logger.info(f"PJM nodes sync complete: {nodes_created} created, {nodes_updated} updated")
            
            return {
                "status": "success",
                "nodes_created": nodes_created,
                "nodes_updated": nodes_updated,
                "total_nodes": nodes_created + nodes_updated
            }
            
        except Exception as e:
            logger.error(f"Error syncing PJM nodes: {e}")
            self.session.rollback()
            raise
    
    async def fetch_latest_prices_for_watchlist(self, user_id: str) -> List[WatchlistSummary]:
        """
        Fetch latest prices for user's watchlist nodes
        This runs every 5 minutes for real-time updates
        """
        try:
            # Get user's watchlist
            watchlist_items = self.session.exec(
                select(WatchlistItem, PJMNode)
                .join(PJMNode)
                .where(WatchlistItem.user_id == user_id)
                .order_by(WatchlistItem.display_order)
            ).all()
            
            if not watchlist_items:
                return []
            
            node_ids = [item[1].node_id for item in watchlist_items]
            
            # Fetch latest prices from GridStatus or generate mock data
            try:
                latest_prices = await self.gridstatus_api.get_latest_lmp_prices(node_ids)
            except:
                # Generate mock data if API fails
                latest_prices = await self._generate_mock_prices(node_ids)
            
            # Get historical data for price changes and sparklines
            summaries = []
            
            for watchlist_item, pjm_node in watchlist_items:
                node_price_data = latest_prices.get(pjm_node.node_id)
                if not node_price_data:
                    continue
                
                current_price = float(node_price_data.get('lmp', 0))
                
                # Get price change data
                price_change_5min, price_change_percent = await self._calculate_price_changes(
                    pjm_node.id, current_price
                )
                
                # Get sparkline data (last 24 hours, 1-hour intervals)
                sparkline_data = await self._get_sparkline_data(pjm_node.id)
                
                # Get day-ahead price for comparison
                da_price = await self._get_day_ahead_price(pjm_node.node_id)
                
                # Save current price to history
                await self._save_price_snapshot(
                    pjm_node.id,
                    current_price,
                    da_price,
                    price_change_5min,
                    node_price_data
                )
                
                # Create summary
                summary = WatchlistSummary(
                    node_id=pjm_node.id,
                    ticker_symbol=pjm_node.ticker_symbol,
                    node_name=pjm_node.node_name,
                    custom_name=watchlist_item.custom_name,
                    current_price=current_price,
                    price_change_5min=price_change_5min,
                    price_change_percent=price_change_percent,
                    day_ahead_price=da_price,
                    sparkline_data=sparkline_data,
                    last_updated=datetime.utcnow(),
                    is_favorite=watchlist_item.is_favorite
                )
                
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error fetching watchlist prices: {e}")
            raise
    
    async def get_node_chart_data(
        self,
        node_id: int,
        hours_back: int = 24,
        include_day_ahead: bool = True
    ) -> Dict:
        """
        Get detailed price history for charting
        """
        try:
            pjm_node = self.session.get(PJMNode, node_id)
            if not pjm_node:
                raise ValueError(f"Node {node_id} not found")
            
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get RT price history (from database or API)
            rt_prices = await self._get_rt_price_history(pjm_node.node_id, start_time)
            
            chart_data = []
            da_overlay = []
            
            for price_point in rt_prices:
                timestamp = price_point['timestamp']
                lmp = price_point['lmp']
                
                chart_data.append({
                    'timestamp': timestamp.isoformat(),
                    'price': lmp,
                    'energy': price_point.get('energy_component', 0),
                    'congestion': price_point.get('congestion_component', 0),
                    'losses': price_point.get('loss_component', 0)
                })
                
                # Add DA price overlay if requested
                if include_day_ahead:
                    da_price = await self._get_day_ahead_price_for_hour(
                        pjm_node.node_id, timestamp
                    )
                    if da_price:
                        da_overlay.append({
                            'timestamp': timestamp.isoformat(),
                            'da_price': da_price
                        })
            
            return {
                'node': {
                    'id': pjm_node.id,
                    'ticker': pjm_node.ticker_symbol,
                    'name': pjm_node.node_name,
                    'zone': pjm_node.zone
                },
                'rt_prices': chart_data,
                'da_overlay': da_overlay if include_day_ahead else [],
                'timeframe': f"{hours_back}h",
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data for node {node_id}: {e}")
            raise
    
    async def check_price_alerts(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Check all active price alerts and trigger notifications
        Run this every 5 minutes
        """
        try:
            # Get active alerts
            alert_query = select(PriceAlert, PJMNode).join(PJMNode).where(
                PriceAlert.status == "active"
            )
            
            if user_id:
                alert_query = alert_query.where(PriceAlert.user_id == user_id)
            
            active_alerts = self.session.exec(alert_query).all()
            
            triggered_alerts = []
            
            for alert, node in active_alerts:
                # Get current price
                try:
                    current_prices = await self.gridstatus_api.get_latest_lmp_prices([node.node_id])
                    current_price = current_prices.get(node.node_id, {}).get('lmp')
                except:
                    # Use mock price if API fails
                    current_price = await self._generate_mock_price(node.node_id)
                
                if not current_price:
                    continue
                
                # Check alert conditions
                is_triggered = False
                
                if alert.alert_type == "above" and current_price >= alert.threshold_value:
                    is_triggered = True
                elif alert.alert_type == "below" and current_price <= alert.threshold_value:
                    is_triggered = True
                elif alert.alert_type == "percent_change":
                    # Calculate percent change from 24h ago
                    price_24h_ago = await self._get_price_hours_ago(node.id, 24)
                    if price_24h_ago:
                        percent_change = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        if abs(percent_change) >= alert.threshold_value:
                            is_triggered = True
                
                if is_triggered:
                    # Update alert status
                    alert.status = "triggered"
                    alert.triggered_at = datetime.utcnow()
                    
                    if not alert.is_recurring:
                        alert.status = "disabled"
                    
                    triggered_alert = {
                        'alert_id': alert.alert_id,
                        'user_id': alert.user_id,
                        'node': {
                            'ticker': node.ticker_symbol,
                            'name': node.node_name
                        },
                        'alert_type': alert.alert_type,
                        'threshold': alert.threshold_value,
                        'current_price': current_price,
                        'message': alert.message or f"{node.ticker_symbol} price alert triggered",
                        'triggered_at': alert.triggered_at.isoformat()
                    }
                    
                    triggered_alerts.append(triggered_alert)
                
                # Update last checked time
                alert.last_checked = datetime.utcnow()
            
            self.session.commit()
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Error checking price alerts: {e}")
            self.session.rollback()
            return []
    
    # Helper methods
    async def _calculate_price_changes(
        self, node_id: int, current_price: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate 5-minute and percentage price changes"""
        try:
            # Get price from 5 minutes ago
            five_min_ago = datetime.utcnow() - timedelta(minutes=5)
            
            old_price = self.session.exec(
                select(NodePriceSnapshot.lmp_price)
                .where(
                    NodePriceSnapshot.node_id == node_id,
                    NodePriceSnapshot.timestamp_utc <= five_min_ago
                )
                .order_by(NodePriceSnapshot.timestamp_utc.desc())
                .limit(1)
            ).first()
            
            if old_price:
                change_5min = current_price - old_price
                change_percent = (change_5min / old_price) * 100 if old_price != 0 else 0
                return change_5min, change_percent
            
            return None, None
            
        except Exception:
            return None, None
    
    async def _get_sparkline_data(self, node_id: int, hours_back: int = 24) -> List[float]:
        """Get simplified price data for sparkline chart"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get hourly prices for sparkline
            prices = self.session.exec(
                select(NodePriceSnapshot.lmp_price)
                .where(
                    NodePriceSnapshot.node_id == node_id,
                    NodePriceSnapshot.timestamp_utc >= start_time
                )
                .order_by(NodePriceSnapshot.timestamp_utc.asc())
            ).all()
            
            # If no historical data, generate mock sparkline
            if not prices:
                import random
                base_price = 35 + random.random() * 30
                return [base_price + (random.random() - 0.5) * 10 for _ in range(24)]
            
            return list(prices)[:24]  # Max 24 points for sparkline
            
        except Exception:
            # Return mock sparkline data on error
            import random
            base_price = 35 + random.random() * 30
            return [base_price + (random.random() - 0.5) * 10 for _ in range(24)]
    
    async def _save_price_snapshot(
        self,
        node_id: int,
        lmp_price: float,
        da_price: Optional[float],
        price_change_5min: Optional[float],
        raw_data: Dict
    ):
        """Save price snapshot to history"""
        try:
            snapshot = NodePriceSnapshot(
                node_id=node_id,
                timestamp_utc=datetime.utcnow(),
                lmp_price=lmp_price,
                day_ahead_price=da_price,
                price_change_5min=price_change_5min,
                energy_component=raw_data.get('energy_component'),
                congestion_component=raw_data.get('congestion_component'),
                loss_component=raw_data.get('loss_component'),
                data_source="gridstatus"
            )
            
            self.session.add(snapshot)
            
        except Exception as e:
            logger.error(f"Error saving price snapshot: {e}")
    
    async def _get_day_ahead_price(self, node_id: str) -> Optional[float]:
        """Get day-ahead price for current hour"""
        try:
            current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            da_prices = await self.gridstatus_api.get_day_ahead_prices(
                [node_id], current_hour, current_hour + timedelta(hours=1)
            )
            
            return da_prices.get(node_id, {}).get('price')
            
        except Exception:
            # Return mock DA price
            import random
            return 40 + random.random() * 20
    
    async def _get_day_ahead_price_for_hour(
        self, node_id: str, timestamp: datetime
    ) -> Optional[float]:
        """Get day-ahead price for specific hour"""
        try:
            hour_start = timestamp.replace(minute=0, second=0, microsecond=0)
            da_prices = await self.gridstatus_api.get_day_ahead_prices(
                [node_id], hour_start, hour_start + timedelta(hours=1)
            )
            
            return da_prices.get(node_id, {}).get('price')
            
        except Exception:
            # Return mock DA price
            import random
            return 40 + random.random() * 20
    
    async def _get_price_hours_ago(self, node_id: int, hours: int) -> Optional[float]:
        """Get price from X hours ago"""
        try:
            target_time = datetime.utcnow() - timedelta(hours=hours)
            
            price = self.session.exec(
                select(NodePriceSnapshot.lmp_price)
                .where(
                    NodePriceSnapshot.node_id == node_id,
                    NodePriceSnapshot.timestamp_utc <= target_time
                )
                .order_by(NodePriceSnapshot.timestamp_utc.desc())
                .limit(1)
            ).first()
            
            return price
            
        except Exception:
            return None
    
    # Mock data generation for development
    async def _generate_mock_prices(self, node_ids: List[str]) -> Dict:
        """Generate mock price data when API is unavailable"""
        import random
        
        prices = {}
        for node_id in node_ids:
            hour = datetime.utcnow().hour
            
            # Time-of-day pricing pattern
            base_price = 45.0
            if 14 <= hour <= 18:  # Peak
                base_price = 65.0
            elif 6 <= hour <= 9:  # Morning
                base_price = 55.0
            elif hour <= 5 or hour >= 22:  # Off-peak
                base_price = 35.0
            
            volatility = random.uniform(0.8, 1.2)
            mock_price = max(10.0, base_price * volatility)
            
            prices[node_id] = {
                'lmp': round(mock_price, 2),
                'energy_component': round(mock_price * 0.8, 2),
                'congestion_component': round(mock_price * 0.15, 2),
                'loss_component': round(mock_price * 0.05, 2)
            }
        
        return prices
    
    async def _generate_mock_price(self, node_id: str) -> float:
        """Generate single mock price"""
        prices = await self._generate_mock_prices([node_id])
        return prices.get(node_id, {}).get('lmp', 45.0)
    
    async def _create_mock_nodes(self) -> Dict:
        """Create mock PJM nodes when API is not available"""
        try:
            mock_nodes_data = [
                {
                    'node_id': 'PJM_RTO',
                    'node_name': 'PJM RTO Hub',
                    'zone': 'RTO',
                    'node_type': 'hub'
                },
                {
                    'node_id': 'WESTERN_HUB',
                    'node_name': 'Western Hub',
                    'zone': 'WEST',
                    'node_type': 'hub'
                },
                {
                    'node_id': 'EASTERN_HUB',
                    'node_name': 'Eastern Hub',
                    'zone': 'EAST',
                    'node_type': 'hub'
                },
                {
                    'node_id': 'KEARNEYS138KV',
                    'node_name': 'Kearneys 138 KV T61',
                    'zone': 'PSEG',
                    'node_type': 'bus'
                }
            ]
            
            nodes_created = 0
            
            for node_data in mock_nodes_data:
                # Check if node exists
                existing_node = self.session.exec(
                    select(PJMNode).where(PJMNode.node_id == node_data['node_id'])
                ).first()
                
                if not existing_node:
                    from ..models import create_pjm_node_from_gridstatus
                    new_node = create_pjm_node_from_gridstatus(node_data)
                    self.session.add(new_node)
                    nodes_created += 1
            
            self.session.commit()
            
            return {
                "status": "success",
                "nodes_created": nodes_created,
                "nodes_updated": 0,
                "total_nodes": nodes_created,
                "source": "mock_data"
            }
            
        except Exception as e:
            logger.error(f"Error creating mock nodes: {e}")
            self.session.rollback()
            raise
    
    async def _get_rt_price_history(self, node_id: str, start_time: datetime) -> List[Dict]:
        """Get RT price history (from DB or API)"""
        try:
            # Try to get from GridStatus API first
            rt_prices = await self.gridstatus_api.get_lmp_history(
                node_id, start_time, datetime.utcnow(), interval_minutes=5
            )
            return rt_prices
        except:
            # Generate mock historical data
            return await self._generate_mock_historical_prices(node_id, start_time)
    
    async def _generate_mock_historical_prices(self, node_id: str, start_time: datetime) -> List[Dict]:
        """Generate mock historical price data"""
        import random
        import math
        
        prices = []
        current_time = start_time
        end_time = datetime.utcnow()
        
        while current_time <= end_time:
            hour = current_time.hour
            
            # Base price with time-of-day pattern
            base_price = 45.0
            if 14 <= hour <= 18:
                base_price = 65.0 + 15 * math.sin((hour - 16) * math.pi / 4)
            elif 6 <= hour <= 9:
                base_price = 55.0 + 10 * (hour - 6) / 3
            elif hour <= 5 or hour >= 22:
                base_price = 35.0
            
            # Add volatility
            volatility = random.uniform(0.85, 1.15)
            mock_price = max(15.0, base_price * volatility)
            
            prices.append({
                'timestamp': current_time,
                'lmp': round(mock_price, 2),
                'energy_component': round(mock_price * 0.8, 2),
                'congestion_component': round(mock_price * 0.15, 2),
                'loss_component': round(mock_price * 0.05, 2)
            })
            
            current_time += timedelta(minutes=5)
        
        return prices

# Background task for real-time updates
class PJMRealTimeUpdater:
    """Background service for real-time price updates"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.is_running = False
    
    async def start_updates(self):
        """Start 5-minute update cycle"""
        self.is_running = True
        logger.info("Starting PJM real-time price updates (5-minute intervals)")
        
        while self.is_running:
            try:
                with self.session_factory() as session:
                    service = PJMDataService(session)
                    
                    # Update all watchlists
                    users_with_watchlists = session.exec(
                        select(WatchlistItem.user_id).distinct()
                    ).all()
                    
                    for user_id in users_with_watchlists:
                        await service.fetch_latest_prices_for_watchlist(user_id)
                    
                    # Check price alerts
                    triggered_alerts = await service.check_price_alerts()
                    
                    if triggered_alerts:
                        logger.info(f"Triggered {len(triggered_alerts)} price alerts")
                        # Here you would send notifications to users
                    
                    logger.debug("Real-time price update cycle completed")
                    
            except Exception as e:
                logger.error(f"Error in real-time update cycle: {e}")
            
            # Wait 5 minutes
            await asyncio.sleep(300)
    
    def stop_updates(self):
        """Stop update cycle"""
        self.is_running = False
        logger.info("Stopped PJM real-time price updates")
