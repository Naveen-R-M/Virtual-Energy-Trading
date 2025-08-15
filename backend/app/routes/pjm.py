# PJM API Routes for Watchlist Features
# New API routes for PJM watchlist functionality

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from ..database import get_session
from ..models import (
    PJMNode, WatchlistItem, PriceAlert, NodePriceSnapshot, 
    WatchlistSummary, AlertType, AlertStatus
)
from ..services.pjm_data_service import PJMDataService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pjm", tags=["pjm"])

# Request/Response models
class WatchlistAddRequest(BaseModel):
    """Request to add node to watchlist"""
    node_id: int = Field(..., description="PJM node ID")
    custom_name: Optional[str] = Field(default=None, description="Custom display name")
    is_favorite: bool = Field(default=False, description="Mark as favorite")

class AlertCreateRequest(BaseModel):
    """Request to create price alert"""
    node_id: int = Field(..., description="PJM node ID")
    alert_type: AlertType = Field(..., description="Alert type")
    threshold_value: float = Field(..., description="Alert threshold")
    message: Optional[str] = Field(default=None, description="Custom message")
    is_recurring: bool = Field(default=False, description="Recurring alert")

class WatchlistUpdateRequest(BaseModel):
    """Request to update watchlist item"""
    custom_name: Optional[str] = None
    is_favorite: Optional[bool] = None
    display_order: Optional[int] = None

# ==================== NODE DISCOVERY ====================

@router.get("/nodes")
async def get_pjm_nodes(
    search: Optional[str] = Query(default=None, description="Search nodes by name"),
    node_type: Optional[str] = Query(default=None, description="Filter by node type"),
    zone: Optional[str] = Query(default=None, description="Filter by zone"),
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
    session: Session = Depends(get_session)
):
    """
    Get all available PJM nodes with optional filtering
    """
    try:
        # Build query
        statement = select(PJMNode).where(PJMNode.is_active == True)
        
        # Apply filters
        if search:
            statement = statement.where(
                PJMNode.node_name.contains(search.upper()) |
                PJMNode.ticker_symbol.contains(search.upper())
            )
        
        if node_type:
            statement = statement.where(PJMNode.node_type == node_type)
        
        if zone:
            statement = statement.where(PJMNode.zone == zone)
        
        # Order by watchlist eligibility, then name
        statement = statement.order_by(
            PJMNode.is_watchlist_eligible.desc(),
            PJMNode.node_name.asc()
        ).limit(limit)
        
        nodes = session.exec(statement).all()
        
        # Format response
        result = []
        for node in nodes:
            result.append({
                "id": node.id,
                "node_id": node.node_id,
                "ticker_symbol": node.ticker_symbol,
                "node_name": node.node_name,
                "zone": node.zone,
                "voltage_level": node.voltage_level,
                "node_type": node.node_type,
                "is_watchlist_eligible": node.is_watchlist_eligible
            })
        
        return {
            "nodes": result,
            "count": len(result),
            "filters": {
                "search": search,
                "node_type": node_type,
                "zone": zone,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting PJM nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching PJM nodes: {e}")

@router.post("/nodes/sync")
async def sync_pjm_nodes(
    session: Session = Depends(get_session)
):
    """
    Sync PJM nodes from GridStatus API
    Run this daily or when adding new nodes
    """
    try:
        service = PJMDataService(session)
        result = await service.sync_pjm_nodes()
        
        return {
            "message": "PJM nodes synced successfully",
            **result
        }
        
    except Exception as e:
        logger.error(f"Error syncing PJM nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing nodes: {e}")

# ==================== WATCHLIST MANAGEMENT ====================

@router.get("/watchlist")
async def get_watchlist(
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get user's watchlist with current prices
    """
    try:
        service = PJMDataService(session)
        watchlist_data = await service.fetch_latest_prices_for_watchlist(user_id)
        
        return {
            "watchlist": [item.dict() for item in watchlist_data],
            "count": len(watchlist_data),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching watchlist: {e}")

@router.post("/watchlist")
async def add_to_watchlist(
    request: WatchlistAddRequest = Body(...),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Add node to user's watchlist
    """
    try:
        # Check if node exists
        pjm_node = session.get(PJMNode, request.node_id)
        if not pjm_node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        if not pjm_node.is_watchlist_eligible:
            raise HTTPException(status_code=400, detail="Node is not eligible for watchlist")
        
        # Check if already in watchlist
        existing = session.exec(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.node_id == request.node_id
            )
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Node already in watchlist")
        
        # Get next display order
        max_order = session.exec(
            select(WatchlistItem.display_order)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.display_order.desc())
            .limit(1)
        ).first()
        
        next_order = (max_order + 1) if max_order is not None else 0
        
        # Create watchlist item
        watchlist_item = WatchlistItem(
            user_id=user_id,
            node_id=request.node_id,
            custom_name=request.custom_name,
            is_favorite=request.is_favorite,
            display_order=next_order
        )
        
        session.add(watchlist_item)
        session.commit()
        session.refresh(watchlist_item)
        
        return {
            "message": f"Added {pjm_node.ticker_symbol} to watchlist",
            "node": {
                "id": pjm_node.id,
                "ticker": pjm_node.ticker_symbol,
                "name": pjm_node.node_name,
                "custom_name": request.custom_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding to watchlist: {e}")

@router.put("/watchlist/{node_id}")
async def update_watchlist_item(
    node_id: int,
    request: WatchlistUpdateRequest = Body(...),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Update watchlist item settings
    """
    try:
        watchlist_item = session.exec(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.node_id == node_id
            )
        ).first()
        
        if not watchlist_item:
            raise HTTPException(status_code=404, detail="Node not in watchlist")
        
        # Update fields
        if request.custom_name is not None:
            watchlist_item.custom_name = request.custom_name
        
        if request.is_favorite is not None:
            watchlist_item.is_favorite = request.is_favorite
        
        if request.display_order is not None:
            watchlist_item.display_order = request.display_order
        
        session.add(watchlist_item)
        session.commit()
        
        return {
            "message": "Watchlist item updated successfully",
            "item": {
                "node_id": node_id,
                "custom_name": watchlist_item.custom_name,
                "is_favorite": watchlist_item.is_favorite,
                "display_order": watchlist_item.display_order
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating watchlist item: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating watchlist item: {e}")

@router.delete("/watchlist/{node_id}")
async def remove_from_watchlist(
    node_id: int,
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Remove node from user's watchlist
    """
    try:
        watchlist_item = session.exec(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.node_id == node_id
            )
        ).first()
        
        if not watchlist_item:
            raise HTTPException(status_code=404, detail="Node not in watchlist")
        
        session.delete(watchlist_item)
        session.commit()
        
        return {
            "message": "Node removed from watchlist successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing from watchlist: {e}")

# ==================== PRICE DATA ====================

@router.get("/prices/latest")
async def get_latest_prices(
    node_ids: Optional[str] = Query(default=None, description="Comma-separated node IDs"),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Get latest prices for specified nodes or user's watchlist
    """
    try:
        service = PJMDataService(session)
        
        if node_ids:
            # Get prices for specific nodes
            node_id_list = [int(id.strip()) for id in node_ids.split(',')]
            # Implementation for specific nodes would go here
            return {"message": "Specific node prices not yet implemented"}
        else:
            # Get watchlist prices
            watchlist_data = await service.fetch_latest_prices_for_watchlist(user_id)
            
            return {
                "prices": [item.dict() for item in watchlist_data],
                "count": len(watchlist_data),
                "last_updated": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error getting latest prices: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching latest prices: {e}")

@router.get("/prices/chart/{node_id}")
async def get_chart_data(
    node_id: int,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of data"),
    include_day_ahead: bool = Query(default=True, description="Include DA overlay"),
    session: Session = Depends(get_session)
):
    """
    Get detailed chart data for a specific node
    """
    try:
        service = PJMDataService(session)
        chart_data = await service.get_node_chart_data(node_id, hours, include_day_ahead)
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {e}")

# ==================== PRICE ALERTS ====================

@router.get("/alerts")
async def get_price_alerts(
    user_id: str = Query(default="demo_user", description="User ID"),
    status: Optional[AlertStatus] = Query(default=None, description="Filter by status"),
    session: Session = Depends(get_session)
):
    """
    Get user's price alerts
    """
    try:
        statement = select(PriceAlert, PJMNode).join(PJMNode).where(
            PriceAlert.user_id == user_id
        )
        
        if status:
            statement = statement.where(PriceAlert.status == status)
        
        statement = statement.order_by(PriceAlert.created_at.desc())
        
        alerts = session.exec(statement).all()
        
        result = []
        for alert, node in alerts:
            result.append({
                "alert_id": alert.alert_id,
                "node": {
                    "id": node.id,
                    "ticker": node.ticker_symbol,
                    "name": node.node_name
                },
                "alert_type": alert.alert_type,
                "threshold_value": alert.threshold_value,
                "status": alert.status,
                "message": alert.message,
                "is_recurring": alert.is_recurring,
                "created_at": alert.created_at.isoformat(),
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
            })
        
        return {
            "alerts": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting price alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching price alerts: {e}")

@router.post("/alerts")
async def create_price_alert(
    request: AlertCreateRequest = Body(...),
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Create new price alert
    """
    try:
        # Verify node exists
        pjm_node = session.get(PJMNode, request.node_id)
        if not pjm_node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Create alert
        alert = PriceAlert(
            user_id=user_id,
            node_id=request.node_id,
            alert_type=request.alert_type,
            threshold_value=request.threshold_value,
            message=request.message,
            is_recurring=request.is_recurring,
            status=AlertStatus.ACTIVE
        )
        
        session.add(alert)
        session.commit()
        session.refresh(alert)
        
        return {
            "message": f"Price alert created for {pjm_node.ticker_symbol}",
            "alert": {
                "alert_id": alert.alert_id,
                "node_ticker": pjm_node.ticker_symbol,
                "alert_type": alert.alert_type,
                "threshold": alert.threshold_value,
                "status": alert.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating price alert: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating price alert: {e}")

@router.delete("/alerts/{alert_id}")
async def delete_price_alert(
    alert_id: str,
    user_id: str = Query(default="demo_user", description="User ID"),
    session: Session = Depends(get_session)
):
    """
    Delete price alert
    """
    try:
        alert = session.exec(
            select(PriceAlert).where(
                PriceAlert.alert_id == alert_id,
                PriceAlert.user_id == user_id
            )
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        session.delete(alert)
        session.commit()
        
        return {
            "message": "Price alert deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting price alert: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting price alert: {e}")

# ==================== SYSTEM STATUS ====================

@router.get("/status")
async def get_pjm_system_status(
    session: Session = Depends(get_session)
):
    """
    Get PJM system status and statistics
    """
    try:
        # Count nodes
        total_nodes = len(session.exec(select(PJMNode)).all())
        active_nodes = len(session.exec(select(PJMNode).where(PJMNode.is_active == True)).all())
        
        # Count watchlists
        total_watchlist_items = len(session.exec(select(WatchlistItem)).all())
        unique_users = len(session.exec(select(WatchlistItem.user_id).distinct()).all())
        
        # Count alerts
        active_alerts = len(session.exec(
            select(PriceAlert).where(PriceAlert.status == AlertStatus.ACTIVE)
        ).all())
        
        # Recent price updates
        recent_updates = len(session.exec(
            select(NodePriceSnapshot).where(
                NodePriceSnapshot.timestamp_utc >= datetime.utcnow() - timedelta(minutes=10)
            )
        ).all())
        
        return {
            "system_status": "operational",
            "statistics": {
                "total_nodes": total_nodes,
                "active_nodes": active_nodes,
                "watchlist_items": total_watchlist_items,
                "unique_users": unique_users,
                "active_alerts": active_alerts,
                "recent_price_updates": recent_updates
            },
            "features": {
                "real_time_updates": True,
                "price_alerts": True,
                "watchlist_management": True,
                "chart_data": True
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting PJM status: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching system status: {e}")
