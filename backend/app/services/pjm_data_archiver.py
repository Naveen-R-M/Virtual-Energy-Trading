# PJM Data Archiver - Persistent Storage for Free-Tier 3-Day History
# Idempotent upserts by (pnode_id, timestamp, interval_5m)

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select, or_
from ..models import DayAheadPrice, RealTimePrice, PJMSettlementData
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

class PJMDataArchiver:
    """
    PJM data archiver for persistent local storage
    
    Features:
    - Idempotent upserts prevent duplicate data
    - 3-day rolling history for free-tier preservation
    - Batch processing for efficiency
    - Data quality validation and gap detection
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.retention_days = int(os.getenv("PJM_DATA_RETENTION_DAYS", "3"))
        self.batch_size = int(os.getenv("PJM_ARCHIVER_BATCH_SIZE", "100"))
        self.feature_enabled = os.getenv("PJM_STATE_MACHINE_ENABLED", "true").lower() == "true"
    
    async def archive_da_prices(
        self, 
        pnode_id: str,
        price_data: List[Dict],
        source: str = "gridstatus_api"
    ) -> Dict:
        """
        Archive day-ahead hourly prices with idempotent upserts
        
        Args:
            pnode_id: PJM Pnode ID
            price_data: List of price records from API
            source: Data source identifier
            
        Returns:
            Archive result summary
        """
        try:
            if not self.feature_enabled:
                return {"status": "disabled", "records_processed": 0}
            
            archive_result = {
                "pnode_id": pnode_id,
                "source": source,
                "records_received": len(price_data),
                "records_inserted": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "errors": [],
                "data_quality": {}
            }
            
            for batch_start in range(0, len(price_data), self.batch_size):
                batch = price_data[batch_start:batch_start + self.batch_size]
                batch_result = await self._process_da_batch(pnode_id, batch, source)
                
                archive_result["records_inserted"] += batch_result["inserted"]
                archive_result["records_updated"] += batch_result["updated"]
                archive_result["records_skipped"] += batch_result["skipped"]
                archive_result["errors"].extend(batch_result["errors"])
            
            # Data quality assessment
            archive_result["data_quality"] = await self._assess_da_data_quality(
                pnode_id, price_data
            )
            
            # Cleanup old data
            cleanup_result = await self._cleanup_old_da_data()
            archive_result["cleanup"] = cleanup_result
            
            logger.info(
                f"Archived DA prices for {pnode_id}: "
                f"{archive_result['records_inserted']} new, "
                f"{archive_result['records_updated']} updated"
            )
            
            return archive_result
            
        except Exception as e:
            logger.error(f"Error archiving DA prices for {pnode_id}: {e}")
            return {"error": str(e), "records_processed": 0}
    
    async def archive_rt_prices(
        self,
        pnode_id: str,
        price_data: List[Dict],
        source: str = "gridstatus_api",
        is_verified: bool = False
    ) -> Dict:
        """
        Archive real-time 5-minute prices with provisional/verified handling
        
        Args:
            pnode_id: PJM Pnode ID
            price_data: List of 5-minute price records
            source: Data source identifier
            is_verified: Whether this is verified settlement data
            
        Returns:
            Archive result summary
        """
        try:
            if not self.feature_enabled:
                return {"status": "disabled", "records_processed": 0}
            
            archive_result = {
                "pnode_id": pnode_id,
                "source": source,
                "is_verified": is_verified,
                "records_received": len(price_data),
                "records_inserted": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "data_gaps_detected": 0,
                "errors": [],
                "interval_coverage": {}
            }
            
            for batch_start in range(0, len(price_data), self.batch_size):
                batch = price_data[batch_start:batch_start + self.batch_size]
                batch_result = await self._process_rt_batch(
                    pnode_id, batch, source, is_verified
                )
                
                archive_result["records_inserted"] += batch_result["inserted"]
                archive_result["records_updated"] += batch_result["updated"]
                archive_result["records_skipped"] += batch_result["skipped"]
                archive_result["errors"].extend(batch_result["errors"])
            
            # Gap detection for RT data
            gap_analysis = await self._detect_rt_data_gaps(pnode_id, price_data)
            archive_result["interval_coverage"] = gap_analysis
            archive_result["data_gaps_detected"] = len(gap_analysis.get("gaps", []))
            
            # Cleanup old data
            cleanup_result = await self._cleanup_old_rt_data()
            archive_result["cleanup"] = cleanup_result
            
            logger.info(
                f"Archived RT prices for {pnode_id}: "
                f"{archive_result['records_inserted']} new, "
                f"{archive_result['data_gaps_detected']} gaps detected"
            )
            
            return archive_result
            
        except Exception as e:
            logger.error(f"Error archiving RT prices for {pnode_id}: {e}")
            return {"error": str(e), "records_processed": 0}
    
    async def _process_da_batch(
        self, 
        pnode_id: str, 
        batch: List[Dict], 
        source: str
    ) -> Dict:
        """Process batch of DA price records with idempotent upserts"""
        batch_result = {"inserted": 0, "updated": 0, "skipped": 0, "errors": []}
        
        for record in batch:
            try:
                # Extract required fields
                timestamp_utc = self._parse_timestamp(record.get("timestamp"))
                price = float(record.get("lmp", record.get("price", 0)))
                
                if not timestamp_utc or price is None:
                    batch_result["skipped"] += 1
                    continue
                
                # Check if record exists
                existing = self.session.exec(
                    select(DayAheadPrice).where(
                        DayAheadPrice.node == pnode_id,
                        DayAheadPrice.timestamp_utc == timestamp_utc
                    )
                ).first()
                
                if existing:
                    # Update if price differs (data correction)
                    if abs(existing.price - price) > 0.01:  # $0.01/MWh threshold
                        existing.price = price
                        existing.updated_at = datetime.utcnow()
                        batch_result["updated"] += 1
                    else:
                        batch_result["skipped"] += 1
                else:
                    # Insert new record
                    new_record = DayAheadPrice(
                        node=pnode_id,
                        timestamp_utc=timestamp_utc,
                        price=price,
                        created_at=datetime.utcnow()
                    )
                    self.session.add(new_record)
                    batch_result["inserted"] += 1
                    
            except Exception as e:
                batch_result["errors"].append(f"Record error: {str(e)}")
        
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            batch_result["errors"].append(f"Batch commit error: {str(e)}")
        
        return batch_result
    
    async def _process_rt_batch(
        self,
        pnode_id: str,
        batch: List[Dict],
        source: str,
        is_verified: bool
    ) -> Dict:
        """Process batch of RT 5-minute price records"""
        batch_result = {"inserted": 0, "updated": 0, "skipped": 0, "errors": []}
        
        for record in batch:
            try:
                timestamp_utc = self._parse_timestamp(record.get("timestamp"))
                price = float(record.get("lmp", record.get("price", 0)))
                
                # Extract LMP components if available
                energy_component = record.get("energy_component")
                congestion_component = record.get("congestion_component") 
                loss_component = record.get("loss_component")
                
                if not timestamp_utc or price is None:
                    batch_result["skipped"] += 1
                    continue
                
                # Check if record exists
                existing = self.session.exec(
                    select(RealTimePrice).where(
                        RealTimePrice.node == pnode_id,
                        RealTimePrice.timestamp_utc == timestamp_utc
                    )
                ).first()
                
                if existing:
                    # Update if price differs or verification status changes
                    needs_update = (
                        abs(existing.price - price) > 0.01 or
                        (is_verified and not getattr(existing, 'is_verified', False))
                    )
                    
                    if needs_update:
                        existing.price = price
                        existing.updated_at = datetime.utcnow()
                        # Update verification status if applicable
                        if hasattr(existing, 'is_verified'):
                            existing.is_verified = is_verified
                        batch_result["updated"] += 1
                    else:
                        batch_result["skipped"] += 1
                else:
                    # Insert new record
                    new_record = RealTimePrice(
                        node=pnode_id,
                        timestamp_utc=timestamp_utc,
                        price=price,
                        created_at=datetime.utcnow()
                    )
                    # Add verification status if field exists
                    if hasattr(new_record, 'is_verified'):
                        new_record.is_verified = is_verified
                    
                    self.session.add(new_record)
                    batch_result["inserted"] += 1
                
                # Also create PJMSettlementData record if components available
                if any([energy_component, congestion_component, loss_component]):
                    await self._upsert_settlement_data(
                        pnode_id, timestamp_utc, price, 
                        energy_component, congestion_component, loss_component,
                        is_verified
                    )
                    
            except Exception as e:
                batch_result["errors"].append(f"RT record error: {str(e)}")
        
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            batch_result["errors"].append(f"RT batch commit error: {str(e)}")
        
        return batch_result
    
    async def _upsert_settlement_data(
        self,
        pnode_id: str,
        timestamp_utc: datetime,
        lmp: float,
        energy_component: Optional[float],
        congestion_component: Optional[float], 
        loss_component: Optional[float],
        is_verified: bool
    ):
        """Upsert PJM settlement data with LMP components"""
        try:
            existing = self.session.exec(
                select(PJMSettlementData).where(
                    PJMSettlementData.pnode_id == pnode_id,
                    PJMSettlementData.timestamp_utc == timestamp_utc
                )
            ).first()
            
            if existing:
                # Update with verified data if available
                if is_verified:
                    existing.verified_lmp = lmp
                    existing.is_verified = True
                    existing.verified_at = datetime.utcnow()
                else:
                    existing.provisional_lmp = lmp
                
                # Update components
                if energy_component is not None:
                    existing.energy_component = energy_component
                if congestion_component is not None:
                    existing.congestion_component = congestion_component
                if loss_component is not None:
                    existing.loss_component = loss_component
                    
            else:
                # Create new settlement record
                settlement_data = PJMSettlementData(
                    pnode_id=pnode_id,
                    timestamp_utc=timestamp_utc,
                    provisional_lmp=lmp if not is_verified else None,
                    verified_lmp=lmp if is_verified else None,
                    is_verified=is_verified,
                    data_source="settlements_verified" if is_verified else "real_time_5min",
                    energy_component=energy_component,
                    congestion_component=congestion_component,
                    loss_component=loss_component,
                    verified_at=datetime.utcnow() if is_verified else None
                )
                self.session.add(settlement_data)
                
        except Exception as e:
            logger.warning(f"Error upserting settlement data: {e}")
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats to datetime"""
        if not timestamp_str:
            return None
            
        try:
            # Handle ISO format
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=None)
            # Handle other formats as needed
            else:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse timestamp {timestamp_str}: {e}")
            return None
    
    async def _detect_rt_data_gaps(
        self, 
        pnode_id: str, 
        recent_data: List[Dict]
    ) -> Dict:
        """Detect gaps in 5-minute RT data coverage"""
        try:
            if not recent_data:
                return {"gaps": [], "coverage_percent": 0}
            
            # Sort data by timestamp
            sorted_data = sorted(
                recent_data, 
                key=lambda x: self._parse_timestamp(x.get("timestamp", ""))
            )
            
            gaps = []
            expected_interval = timedelta(minutes=5)
            
            for i in range(1, len(sorted_data)):
                prev_time = self._parse_timestamp(sorted_data[i-1].get("timestamp"))
                curr_time = self._parse_timestamp(sorted_data[i].get("timestamp"))
                
                if prev_time and curr_time:
                    gap = curr_time - prev_time
                    if gap > expected_interval * 1.5:  # Allow some tolerance
                        gaps.append({
                            "start": prev_time.isoformat(),
                            "end": curr_time.isoformat(),
                            "duration_minutes": gap.total_seconds() / 60,
                            "missing_intervals": int(gap.total_seconds() / 300) - 1
                        })
            
            # Calculate coverage percentage
            if sorted_data:
                start_time = self._parse_timestamp(sorted_data[0].get("timestamp"))
                end_time = self._parse_timestamp(sorted_data[-1].get("timestamp"))
                if start_time and end_time:
                    total_duration = (end_time - start_time).total_seconds()
                    gap_duration = sum(gap["duration_minutes"] * 60 for gap in gaps)
                    coverage_percent = (1 - gap_duration / total_duration) * 100 if total_duration > 0 else 100
                else:
                    coverage_percent = 0
            else:
                coverage_percent = 0
            
            return {
                "gaps": gaps,
                "coverage_percent": round(coverage_percent, 2),
                "total_intervals": len(sorted_data),
                "missing_intervals": sum(gap["missing_intervals"] for gap in gaps)
            }
            
        except Exception as e:
            logger.error(f"Error detecting RT data gaps: {e}")
            return {"error": str(e), "gaps": []}
    
    async def _assess_da_data_quality(
        self,
        pnode_id: str,
        price_data: List[Dict]
    ) -> Dict:
        """Assess data quality for DA prices"""
        try:
            quality_metrics = {
                "total_records": len(price_data),
                "price_range": {"min": 0, "max": 0, "avg": 0},
                "negative_prices": 0,
                "extreme_prices": 0,  # >$1000/MWh
                "data_quality_score": 100
            }
            
            if not price_data:
                return quality_metrics
            
            prices = []
            for record in price_data:
                price = float(record.get("lmp", record.get("price", 0)))
                prices.append(price)
                
                if price < 0:
                    quality_metrics["negative_prices"] += 1
                if price > 1000:
                    quality_metrics["extreme_prices"] += 1
            
            if prices:
                quality_metrics["price_range"] = {
                    "min": min(prices),
                    "max": max(prices), 
                    "avg": sum(prices) / len(prices)
                }
            
            # Calculate quality score (deduct for anomalies)
            anomaly_rate = (quality_metrics["extreme_prices"] / len(prices)) * 100
            quality_metrics["data_quality_score"] = max(0, 100 - anomaly_rate * 10)
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error assessing DA data quality: {e}")
            return {"error": str(e)}
    
    async def _cleanup_old_da_data(self) -> Dict:
        """Clean up DA data older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            old_records = self.session.exec(
                select(DayAheadPrice).where(
                    DayAheadPrice.timestamp_utc < cutoff_date
                )
            )
            
            deleted_count = 0
            for record in old_records:
                self.session.delete(record)
                deleted_count += 1
            
            self.session.commit()
            
            return {"deleted_da_records": deleted_count, "cutoff_date": cutoff_date.isoformat()}
            
        except Exception as e:
            logger.error(f"Error cleaning up old DA data: {e}")
            self.session.rollback()
            return {"error": str(e), "deleted_da_records": 0}
    
    async def _cleanup_old_rt_data(self) -> Dict:
        """Clean up RT data older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            old_rt_records = self.session.exec(
                select(RealTimePrice).where(
                    RealTimePrice.timestamp_utc < cutoff_date
                )
            )
            
            old_settlement_records = self.session.exec(
                select(PJMSettlementData).where(
                    PJMSettlementData.timestamp_utc < cutoff_date
                )
            )
            
            deleted_rt = 0
            for record in old_rt_records:
                self.session.delete(record)
                deleted_rt += 1
            
            deleted_settlement = 0
            for record in old_settlement_records:
                self.session.delete(record)
                deleted_settlement += 1
            
            self.session.commit()
            
            return {
                "deleted_rt_records": deleted_rt,
                "deleted_settlement_records": deleted_settlement,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old RT data: {e}")
            self.session.rollback()
            return {"error": str(e), "deleted_rt_records": 0}

# Global archiver instance
pjm_archiver = None

def get_pjm_archiver(session: Session) -> PJMDataArchiver:
    """Get or create PJM data archiver instance"""
    global pjm_archiver
    if pjm_archiver is None:
        pjm_archiver = PJMDataArchiver(session)
    return pjm_archiver