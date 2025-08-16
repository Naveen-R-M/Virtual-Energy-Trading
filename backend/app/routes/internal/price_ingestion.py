"""
Internal Price Ingestion API Routes
Handles price data ingestion and triggers deterministic matching
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from ...database import get_session
from ...models import DayAheadPrice, RealTimePrice
from ...services.deterministic_matching import trigger_rt_matching, trigger_da_matching
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal/prices", tags=["internal"])

class RealTimePriceIngest(BaseModel):
    """RT price ingestion model"""
    node_id: str = Field(..., description="PJM node identifier")
    timestamp: str = Field(..., description="5-minute timestamp in ISO format")
    lmp: float = Field(..., description="Locational Marginal Price in $/MWh")
    energy_component: Optional[float] = Field(None, description="Energy component")
    congestion_component: Optional[float] = Field(None, description="Congestion component")
    loss_component: Optional[float] = Field(None, description="Loss component")

class DayAheadPriceIngest(BaseModel):
    """DA price ingestion model"""
    node_id: str = Field(..., description="PJM node identifier")
    hour_start: str = Field(..., description="Hour start timestamp in ISO format")
    clearing_price: float = Field(..., description="DA clearing price in $/MWh")

class PriceIngestResponse(BaseModel):
    """Price ingestion response"""
    status: str
    message: str
    matching_triggered: bool
    matching_results: Optional[Dict] = None

@router.post("/ingest/rt")
async def ingest_rt_price(
    price_data: RealTimePriceIngest = Body(...),
    session: Session = Depends(get_session)
) -> PriceIngestResponse:
    """
    Ingest RT 5-minute price and trigger deterministic matching
    """
    try:
        # Parse timestamp
        ts_5m = datetime.fromisoformat(price_data.timestamp.replace("Z", "+00:00"))
        
        # Upsert RT price record (idempotent)
        existing_price = session.exec(
            select(RealTimePrice).where(
                RealTimePrice.node == price_data.node_id,
                RealTimePrice.timestamp_utc == ts_5m
            )
        ).first()
        
        if existing_price:
            # Update existing record
            existing_price.price = price_data.lmp
            session.add(existing_price)
            logger.info(f"Updated existing RT price: {price_data.node_id} at {ts_5m}")
        else:
            # Create new record
            rt_price = RealTimePrice(
                node=price_data.node_id,
                timestamp_utc=ts_5m,
                price=price_data.lmp
            )
            session.add(rt_price)
            logger.info(f"Created new RT price: {price_data.node_id} at {ts_5m}")
        
        session.commit()
        
        # Trigger deterministic matching
        matching_results = await trigger_rt_matching(
            session, price_data.node_id, ts_5m, price_data.lmp
        )
        
        matching_triggered = matching_results.get("status") == "completed"
        
        return PriceIngestResponse(
            status="success",
            message=f"RT price ingested and matching {'completed' if matching_triggered else 'skipped'}",
            matching_triggered=matching_triggered,
            matching_results=matching_results
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error ingesting RT price: {e}")
        raise HTTPException(status_code=500, detail=f"Error ingesting RT price: {e}")

@router.post("/ingest/da")
async def ingest_da_price(
    price_data: DayAheadPriceIngest = Body(...),
    session: Session = Depends(get_session)
) -> PriceIngestResponse:
    """
    Ingest DA hourly clearing price and trigger deterministic matching
    """
    try:
        # Parse timestamp
        hour_start = datetime.fromisoformat(price_data.hour_start.replace("Z", "+00:00"))
        
        # Upsert DA price record (idempotent)
        existing_price = session.exec(
            select(DayAheadPrice).where(
                DayAheadPrice.node == price_data.node_id,
                DayAheadPrice.hour_start_utc == hour_start
            )
        ).first()
        
        if existing_price:
            # Update existing record
            existing_price.close_price = price_data.clearing_price
            existing_price.price = price_data.clearing_price
            session.add(existing_price)
            logger.info(f"Updated existing DA price: {price_data.node_id} hour {hour_start}")
        else:
            # Create new record
            da_price = DayAheadPrice(
                node=price_data.node_id,
                hour_start_utc=hour_start,
                close_price=price_data.clearing_price,
                price=price_data.clearing_price
            )
            session.add(da_price)
            logger.info(f"Created new DA price: {price_data.node_id} hour {hour_start}")
        
        session.commit()
        
        # Trigger deterministic matching
        matching_results = await trigger_da_matching(
            session, price_data.node_id, hour_start, price_data.clearing_price
        )
        
        matching_triggered = matching_results.get("status") == "completed"
        
        return PriceIngestResponse(
            status="success",
            message=f"DA price ingested and matching {'completed' if matching_triggered else 'skipped'}",
            matching_triggered=matching_triggered,
            matching_results=matching_results
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error ingesting DA price: {e}")
        raise HTTPException(status_code=500, detail=f"Error ingesting DA price: {e}")

@router.post("/ingest/batch/rt")
async def ingest_rt_prices_batch(
    prices: List[RealTimePriceIngest] = Body(...),
    session: Session = Depends(get_session)
) -> Dict:
    """
    Ingest multiple RT prices and trigger matching for each
    """
    results = []
    processed_count = 0
    matching_triggered_count = 0
    
    try:
        for price_data in prices:
            try:
                result = await ingest_rt_price(price_data, session)
                results.append(result)
                processed_count += 1
                
                if result.matching_triggered:
                    matching_triggered_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing RT price for {price_data.node_id}: {e}")
                results.append({
                    "node_id": price_data.node_id,
                    "timestamp": price_data.timestamp,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "status": "completed",
            "total_prices": len(prices),
            "processed": processed_count,
            "matching_triggered": matching_triggered_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch RT ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Error in batch ingestion: {e}")

@router.post("/ingest/batch/da")
async def ingest_da_prices_batch(
    prices: List[DayAheadPriceIngest] = Body(...),
    session: Session = Depends(get_session)
) -> Dict:
    """
    Ingest multiple DA prices and trigger matching for each
    """
    results = []
    processed_count = 0
    matching_triggered_count = 0
    
    try:
        for price_data in prices:
            try:
                result = await ingest_da_price(price_data, session)
                results.append(result)
                processed_count += 1
                
                if result.matching_triggered:
                    matching_triggered_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing DA price for {price_data.node_id}: {e}")
                results.append({
                    "node_id": price_data.node_id,
                    "hour_start": price_data.hour_start,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "status": "completed",
            "total_prices": len(prices),
            "processed": processed_count,
            "matching_triggered": matching_triggered_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch DA ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Error in batch ingestion: {e}")

@router.get("/matching/status")
async def get_matching_status() -> Dict:
    """
    Get current deterministic matching configuration status
    """
    import os
    
    return {
        "deterministic_matching_enabled": os.getenv("DETERMINISTIC_MATCHING_ENABLED", "false").lower() == "true",
        "feature_status": "ready",
        "supported_markets": ["real-time", "day-ahead"],
        "matching_triggers": [
            "RT 5-minute price ingestion",
            "DA hourly price ingestion"
        ],
        "order_types_supported": ["MKT", "LMT"],
        "time_in_force_supported": ["GTC", "IOC", "DAY"]
    }
