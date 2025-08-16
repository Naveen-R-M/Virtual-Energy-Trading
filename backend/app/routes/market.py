"""
Market Data API Routes for Virtual Energy Trading Platform
Handles Day-Ahead and Real-Time market price endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, List
from ..database import get_session
from ..models import DayAheadPrice, RealTimePrice
from ..services.market_data import MarketDataService
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/da")
async def get_day_ahead_prices(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    node: str = Query(default="PJM_RTO", description="Grid node identifier"),
    session: Session = Depends(get_session)
):
    """
    Get Day-Ahead hourly prices for a specific date and node
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        # Query database for DA prices
        statement = select(DayAheadPrice).where(
            DayAheadPrice.node == node,
            DayAheadPrice.hour_start_utc >= start_time,
            DayAheadPrice.hour_start_utc < end_time
        ).order_by(DayAheadPrice.hour_start_utc)
        
        prices = session.exec(statement).all()
        
        # If no prices found, fetch from service (real or mock based on flag)
        if not prices:
            logger.info(f"No DA prices in database for {node} on {date}, fetching...")
            service = MarketDataService(session)
            
            try:
                price_data = await service.fetch_day_ahead_prices(node, target_date)
                
                # Save to database for future use
                for price_dict in price_data:
                    da_price = DayAheadPrice(
                        node=price_dict["node"],
                        hour_start_utc=datetime.fromisoformat(price_dict["hour_start"].replace("Z", "+00:00")),
                        price=price_dict.get("close_price", price_dict.get("price", 0)),
                        close_price=price_dict.get("close_price", price_dict.get("price", 0))
                    )
                    session.add(da_price)
                
                session.commit()
                
                # Re-query to get the saved prices
                prices = session.exec(statement).all()
                
            except Exception as fetch_error:
                # In REAL data mode, propagate the error
                if os.getenv("USE_REAL_DATA", "true").lower() == "true":
                    logger.error(f"Failed to fetch real DA prices: {fetch_error}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"Real data unavailable: {str(fetch_error)}"
                    )
                else:
                    # This shouldn't happen in mock mode, but handle it
                    raise fetch_error
        
        # Format response
        result = []
        for price in prices:
            result.append({
                "hour_start": price.hour_start_utc.isoformat(),
                "node": price.node,
                "close_price": price.close_price,
                "price": price.price
            })
        
        return {
            "date": date,
            "node": node,
            "market": "day-ahead",
            "prices": result,
            "count": len(result)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error fetching DA prices: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching Day-Ahead prices: {e}")

@router.get("/rt")
async def get_real_time_prices(
    start: str = Query(..., description="Start datetime in ISO format"),
    end: str = Query(..., description="End datetime in ISO format"),
    node: str = Query(default="PJM_RTO", description="Grid node identifier"),
    session: Session = Depends(get_session)
):
    """
    Get Real-Time 5-minute prices for a specific time range and node
    """
    try:
        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
        
        # If start and end are the same (single point query), expand to 5-minute window
        if start_time == end_time:
            # Round down to nearest 5-minute interval
            minutes = start_time.minute
            rounded_minutes = (minutes // 5) * 5
            start_time = start_time.replace(minute=rounded_minutes, second=0, microsecond=0)
            end_time = start_time + timedelta(minutes=5)
        
        # Validate time range (max 24 hours)
        if (end_time - start_time) > timedelta(hours=24):
            raise HTTPException(status_code=400, detail="Time range cannot exceed 24 hours")
        
        # Query database for RT prices
        statement = select(RealTimePrice).where(
            RealTimePrice.node == node,
            RealTimePrice.timestamp_utc >= start_time,
            RealTimePrice.timestamp_utc < end_time
        ).order_by(RealTimePrice.timestamp_utc)
        
        prices = session.exec(statement).all()
        
        # If no prices found, fetch from service (real or mock based on flag)
        if not prices:
            logger.info(f"No RT prices in database for {node} from {start} to {end}, fetching...")
            service = MarketDataService(session)
            
            try:
                price_data = await service.fetch_real_time_prices(node, start_time, end_time)
                
                # Save to database for future use
                for price_dict in price_data:
                    rt_price = RealTimePrice(
                        node=price_dict["node"],
                        timestamp_utc=datetime.fromisoformat(price_dict["timestamp"].replace("Z", "+00:00")),
                        price=price_dict["price"]
                    )
                    session.add(rt_price)
                
                session.commit()
                
                # Re-query to get the saved prices
                prices = session.exec(statement).all()
                
            except Exception as fetch_error:
                # In REAL data mode, propagate the error
                if os.getenv("USE_REAL_DATA", "true").lower() == "true":
                    logger.error(f"Failed to fetch real RT prices: {fetch_error}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"Real data unavailable: {str(fetch_error)}"
                    )
                else:
                    # This shouldn't happen in mock mode, but handle it
                    raise fetch_error
        
        # Format response
        result = []
        for price in prices:
            result.append({
                "timestamp": price.timestamp_utc.isoformat(),
                "node": price.node,
                "price": price.price
            })
        
        return {
            "start": start,
            "end": end,
            "node": node,
            "market": "real-time",
            "prices": result,
            "count": len(result),
            "interval": "5-minute"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching RT prices: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching Real-Time prices: {e}")

@router.get("/latest")
async def get_latest_prices(
    node: str = Query(default="PJM_RTO", description="Grid node identifier"),
    session: Session = Depends(get_session)
):
    """
    Get latest available prices for both Day-Ahead and Real-Time markets
    """
    try:
        # Get latest DA price
        da_statement = select(DayAheadPrice).where(
            DayAheadPrice.node == node
        ).order_by(DayAheadPrice.hour_start_utc.desc()).limit(1)
        
        latest_da = session.exec(da_statement).first()
        
        # Get latest RT price
        rt_statement = select(RealTimePrice).where(
            RealTimePrice.node == node
        ).order_by(RealTimePrice.timestamp_utc.desc()).limit(1)
        
        latest_rt = session.exec(rt_statement).first()
        
        # If no data, fetch latest from service
        if not latest_da or not latest_rt:
            service = MarketDataService(session)
            
            try:
                latest_data = await service.get_latest_prices(node)
                
                if not latest_da and latest_data.get("day_ahead"):
                    latest_da_data = latest_data["day_ahead"]
                else:
                    latest_da_data = {
                        "hour_start": latest_da.hour_start_utc.isoformat() if latest_da else None,
                        "price": latest_da.close_price if latest_da else None
                    }
                
                if not latest_rt and latest_data.get("real_time"):
                    latest_rt_data = latest_data["real_time"]
                else:
                    latest_rt_data = {
                        "timestamp": latest_rt.timestamp_utc.isoformat() if latest_rt else None,
                        "price": latest_rt.price if latest_rt else None
                    }
                    
            except Exception as fetch_error:
                # In REAL data mode, provide partial data or error
                if os.getenv("USE_REAL_DATA", "true").lower() == "true":
                    logger.error(f"Failed to fetch latest real prices: {fetch_error}")
                    # Return partial data if available
                    latest_da_data = {
                        "hour_start": latest_da.hour_start_utc.isoformat() if latest_da else None,
                        "price": latest_da.close_price if latest_da else None,
                        "error": "Real data unavailable"
                    }
                    latest_rt_data = {
                        "timestamp": latest_rt.timestamp_utc.isoformat() if latest_rt else None,
                        "price": latest_rt.price if latest_rt else None,
                        "error": "Real data unavailable"
                    }
                else:
                    raise fetch_error
        else:
            latest_da_data = {
                "hour_start": latest_da.hour_start_utc.isoformat(),
                "price": latest_da.close_price
            }
            latest_rt_data = {
                "timestamp": latest_rt.timestamp_utc.isoformat(),
                "price": latest_rt.price
            }
        
        return {
            "node": node,
            "day_ahead": latest_da_data,
            "real_time": latest_rt_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching latest prices: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching latest prices: {e}")

@router.get("/data-source")
async def get_data_source_info(session: Session = Depends(get_session)):
    """
    Get information about the current data source (real or mock)
    """
    try:
        service = MarketDataService(session)
        connection_info = await service.test_gridstatus_connection()
        
        use_real_data = os.getenv("USE_REAL_DATA", "true").lower() == "true"
        
        return {
            "USE_REAL_DATA": use_real_data,
            "mode": connection_info.get("mode", "UNKNOWN"),
            "strict_mode": True,  # Always strict mode - no fallback
            "gridstatus_connected": connection_info.get("connected", False),
            "api_configured": connection_info.get("api_configured", False),
            "api_key_configured": connection_info.get("api_key_present", False),
            "message": (
                f"STRICT MODE: {connection_info.get('mode', 'UNKNOWN')} data only - "
                f"{'GridStatus connected' if connection_info.get('connected') else 'Using mock data'}"
            ),
            "available_isos": ["PJM", "CAISO", "ERCOT", "NYISO", "MISO"],
            "details": connection_info
        }
        
    except Exception as e:
        logger.error(f"Error getting data source info: {e}")
        return {
            "using_real_data": False,
            "gridstatus_connected": False,
            "api_configured": False,
            "message": "Using mock data (error checking real data source)",
            "error": str(e)
        }

@router.get("/nodes")
async def get_available_nodes(
    iso: str = Query(default="PJM", description="ISO name"),
    session: Session = Depends(get_session)
):
    """
    Get list of available nodes/locations for an ISO
    """
    try:
        # Try to get real nodes from GridStatus
        if os.getenv("USE_REAL_DATA", "true").lower() == "true":
            try:
                from ..services.gridstatus_api import gridstatus_service
                nodes = await gridstatus_service.get_available_nodes(iso)
                
                if nodes:
                    return {
                        "iso": iso,
                        "nodes": nodes,
                        "count": len(nodes),
                        "source": "gridstatus"
                    }
            except Exception as e:
                logger.warning(f"Could not fetch real nodes: {e}")
        
        # Fall back to predefined nodes
        default_nodes = {
            "PJM": [
                {"node_code": "PJM_RTO", "node_name": "PJM RTO Hub", "type": "hub"},
                {"node_code": "WESTERN_HUB", "node_name": "Western Hub", "type": "hub"},
                {"node_code": "EASTERN_HUB", "node_name": "Eastern Hub", "type": "hub"}
            ],
            "CAISO": [
                {"node_code": "TH_NP15_GEN_APND", "node_name": "NP15 Trading Hub", "type": "hub"},
                {"node_code": "TH_SP15_GEN_APND", "node_name": "SP15 Trading Hub", "type": "hub"},
                {"node_code": "TH_ZP26_GEN_APND", "node_name": "ZP26 Trading Hub", "type": "hub"}
            ],
            "ERCOT": [
                {"node_code": "HB_HOUSTON", "node_name": "Houston Hub", "type": "hub"},
                {"node_code": "HB_NORTH", "node_name": "North Hub", "type": "hub"},
                {"node_code": "HB_SOUTH", "node_name": "South Hub", "type": "hub"}
            ],
            "NYISO": [
                {"node_code": "N.Y.C.", "node_name": "New York City", "type": "zone"},
                {"node_code": "CAPITL", "node_name": "Capital Zone", "type": "zone"},
                {"node_code": "CENTRL", "node_name": "Central Zone", "type": "zone"}
            ],
            "MISO": [
                {"node_code": "HUB", "node_name": "MISO Hub", "type": "hub"},
                {"node_code": "ILLINOIS.HUB", "node_name": "Illinois Hub", "type": "hub"},
                {"node_code": "MICHIGAN.HUB", "node_name": "Michigan Hub", "type": "hub"}
            ]
        }
        
        nodes = default_nodes.get(iso, [])
        
        return {
            "iso": iso,
            "nodes": nodes,
            "count": len(nodes),
            "source": "default"
        }
        
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting available nodes: {e}")

@router.get("/summary/{date}")
async def get_market_summary(
    date: str,
    node: str = Query(default="PJM_RTO", description="Grid node identifier"),
    session: Session = Depends(get_session)
):
    """
    Get market summary statistics for a specific date
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        # Get DA prices for the date
        da_statement = select(DayAheadPrice).where(
            DayAheadPrice.node == node,
            DayAheadPrice.hour_start_utc >= start_time,
            DayAheadPrice.hour_start_utc < end_time
        )
        
        da_prices = session.exec(da_statement).all()
        
        # Get RT prices for the date
        rt_statement = select(RealTimePrice).where(
            RealTimePrice.node == node,
            RealTimePrice.timestamp_utc >= start_time,
            RealTimePrice.timestamp_utc < end_time
        )
        
        rt_prices = session.exec(rt_statement).all()
        
        # Calculate statistics
        da_values = [p.close_price for p in da_prices] if da_prices else []
        rt_values = [p.price for p in rt_prices] if rt_prices else []
        
        summary = {
            "date": date,
            "node": node,
            "day_ahead": {
                "count": len(da_values),
                "min": min(da_values) if da_values else None,
                "max": max(da_values) if da_values else None,
                "avg": sum(da_values) / len(da_values) if da_values else None,
                "peak_hour": None,
                "off_peak_avg": None
            },
            "real_time": {
                "count": len(rt_values),
                "min": min(rt_values) if rt_values else None,
                "max": max(rt_values) if rt_values else None,
                "avg": sum(rt_values) / len(rt_values) if rt_values else None,
                "volatility": None
            },
            "spread": {
                "avg_da_rt_spread": None
            }
        }
        
        # Calculate peak/off-peak for DA
        if da_prices:
            peak_hours = [p for p in da_prices if 14 <= p.hour_start_utc.hour <= 18]
            off_peak_hours = [p for p in da_prices if p.hour_start_utc.hour < 6 or p.hour_start_utc.hour >= 22]
            
            if peak_hours:
                peak_hour_max = max(peak_hours, key=lambda x: x.close_price)
                summary["day_ahead"]["peak_hour"] = {
                    "hour": peak_hour_max.hour_start_utc.hour,
                    "price": peak_hour_max.close_price
                }
            
            if off_peak_hours:
                summary["day_ahead"]["off_peak_avg"] = sum(p.close_price for p in off_peak_hours) / len(off_peak_hours)
        
        # Calculate volatility for RT
        if len(rt_values) > 1:
            mean = sum(rt_values) / len(rt_values)
            variance = sum((x - mean) ** 2 for x in rt_values) / len(rt_values)
            summary["real_time"]["volatility"] = variance ** 0.5
        
        # Calculate average spread
        if da_values and rt_values:
            da_avg = sum(da_values) / len(da_values)
            rt_avg = sum(rt_values) / len(rt_values)
            summary["spread"]["avg_da_rt_spread"] = rt_avg - da_avg
        
        return summary
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market summary: {e}")
