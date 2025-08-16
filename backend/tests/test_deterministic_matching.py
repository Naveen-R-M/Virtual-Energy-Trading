"""
Unit Tests for Deterministic PJM Matching Engine
Tests the core matching logic with various scenarios
"""

import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, SQLModel, select
from unittest.mock import patch
import os
import asyncio

# Test imports
from app.models import (
    TradingOrder, OrderFill, DayAheadPrice, RealTimePrice,
    MarketType, OrderStatus, OrderSide, OrderType, TimeInForce, FillType
)
from app.services.deterministic_matching import (
    DeterministicMatchingService, trigger_rt_matching, trigger_da_matching
)
from app.database import get_session

# Test database setup
@pytest.fixture
def test_engine():
    """Create test database engine"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    with Session(test_engine) as session:
        yield session

@pytest.fixture
def matching_service(test_session):
    """Create deterministic matching service with test session"""
    with patch.dict(os.environ, {"DETERMINISTIC_MATCHING_ENABLED": "true"}):
        return DeterministicMatchingService(test_session)

class TestRTMatching:
    """Test Real-Time order matching"""

    @pytest.mark.asyncio
    async def test_rt_market_order_always_fills(self, matching_service, test_session):
        """RT market orders should always fill at LMP"""
        # Create market buy order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO", 
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            limit_price=None,  # No limit for market orders
            quantity_mwh=2.5,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Process RT tick
        lmp_price = 55.75
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        result = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        
        # Verify results
        assert result["status"] == "completed"
        assert result["metrics"]["filled"] == 1
        
        # Verify order was filled
        test_session.refresh(order)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == lmp_price
        assert order.filled_quantity == 2.5

    @pytest.mark.asyncio
    async def test_rt_limit_buy_fills_when_lmp_at_or_below_limit(self, matching_service, test_session):
        """RT limit BUY order fills when LMP <= limit"""
        # Create limit buy order at $50
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Test case 1: LMP below limit (should fill)
        lmp_price = 48.25
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        result = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        
        assert result["metrics"]["filled"] == 1
        test_session.refresh(order)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 48.25  # Fills at LMP, not limit

    @pytest.mark.asyncio
    async def test_rt_limit_buy_no_fill_when_lmp_above_limit(self, matching_service, test_session):
        """RT limit BUY order doesn't fill when LMP > limit"""
        # Create limit buy order at $50
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # LMP above limit (should not fill)
        lmp_price = 52.75
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        result = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        
        assert result["metrics"]["filled"] == 0
        test_session.refresh(order)
        assert order.status == OrderStatus.PENDING  # Still pending

    @pytest.mark.asyncio
    async def test_rt_limit_sell_fills_when_lmp_at_or_above_limit(self, matching_service, test_session):
        """RT limit SELL order fills when LMP >= limit"""
        # Create limit sell order at $45
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=45.00,
            quantity_mwh=3.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # LMP above limit (should fill)
        lmp_price = 47.50
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        result = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        
        assert result["metrics"]["filled"] == 1
        test_session.refresh(order)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 47.50  # Fills at LMP

class TestDAMatching:
    """Test Day-Ahead order matching"""

    @pytest.mark.asyncio
    async def test_da_limit_buy_fills_when_da_price_at_or_below_limit(self, matching_service, test_session):
        """DA limit BUY order fills when P_DA <= limit"""
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create limit buy order at $60
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=60.00,
            quantity_mwh=2.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # DA clearing price below limit (should fill)
        da_price = 58.25
        
        result = await matching_service.on_new_da_price("PJM_RTO", hour_start, da_price)
        
        assert result["metrics"]["filled"] == 1
        test_session.refresh(order)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 58.25

    @pytest.mark.asyncio
    async def test_da_limit_buy_rejected_when_da_price_above_limit(self, matching_service, test_session):
        """DA limit BUY order rejected when P_DA > limit"""
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create limit buy order at $50
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=2.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # DA clearing price above limit (should reject)
        da_price = 52.75
        
        result = await matching_service.on_new_da_price("PJM_RTO", hour_start, da_price)
        
        assert result["metrics"]["rejected"] == 1
        test_session.refresh(order)
        assert order.status == OrderStatus.REJECTED
        assert "Limit not met" in order.rejection_reason

    @pytest.mark.asyncio
    async def test_da_limit_sell_fills_when_da_price_at_or_above_limit(self, matching_service, test_session):
        """DA limit SELL order fills when P_DA >= limit"""
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create limit sell order at $40
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=40.00,
            quantity_mwh=1.5,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # DA clearing price above limit (should fill)
        da_price = 42.10
        
        result = await matching_service.on_new_da_price("PJM_RTO", hour_start, da_price)
        
        assert result["metrics"]["filled"] == 1
        test_session.refresh(order)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 42.10

class TestIdempotency:
    """Test idempotent processing (no duplicate fills)"""

    @pytest.mark.asyncio
    async def test_rt_idempotency_no_duplicate_fills(self, matching_service, test_session):
        """Processing same RT tick twice should not create duplicate fills"""
        # Create order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Process first time
        lmp_price = 45.00
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        result1 = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        assert result1["metrics"]["filled"] == 1
        
        # Process same tick again (should not create duplicate)
        result2 = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        assert result2["metrics"]["filled"] == 0  # No new fills
        
        # Verify only one fill record exists
        fills = test_session.exec(select(OrderFill).where(OrderFill.order_id == order.id)).all()
        assert len(fills) == 1

    @pytest.mark.asyncio
    async def test_da_idempotency_no_duplicate_processing(self, matching_service, test_session):
        """Processing same DA price twice should not create duplicate processing"""
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Process first time
        da_price = 48.00
        result1 = await matching_service.on_new_da_price("PJM_RTO", hour_start, da_price)
        assert result1["metrics"]["filled"] == 1
        
        # Process same price again (should not reprocess)
        result2 = await matching_service.on_new_da_price("PJM_RTO", hour_start, da_price)
        assert result2["metrics"]["filled"] == 0  # No new processing
        
        # Verify only one fill record exists
        fills = test_session.exec(select(OrderFill).where(OrderFill.order_id == order.id)).all()
        assert len(fills) == 1

class TestMultipleOrders:
    """Test deterministic ordering of multiple orders"""

    @pytest.mark.asyncio
    async def test_multiple_orders_deterministic_processing(self, matching_service, test_session):
        """Multiple orders on same tick should be processed deterministically by created_at"""
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create orders with different creation times
        order1 = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(seconds=10)  # Older
        )
        
        order2 = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity_mwh=2.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(seconds=5)  # Newer
        )
        
        test_session.add(order1)
        test_session.add(order2)
        test_session.commit()
        
        # Process RT tick
        lmp_price = 50.00
        result = await matching_service.on_new_rt_tick("PJM_RTO", ts_5m, lmp_price)
        
        assert result["metrics"]["filled"] == 2
        
        # Both orders should be filled at same price (deterministic)
        test_session.refresh(order1)
        test_session.refresh(order2)
        assert order1.status == OrderStatus.FILLED
        assert order2.status == OrderStatus.FILLED
        assert order1.filled_price == lmp_price
        assert order2.filled_price == lmp_price

class TestTimeInForce:
    """Test time-in-force and expiry logic"""

    def test_ioc_order_expires_immediately(self, matching_service, test_session):
        """IOC orders should expire if not filled immediately"""
        # Create IOC order that won't fill (limit too low for buy)
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=30.00,  # Very low limit
            quantity_mwh=1.0,
            time_in_force=TimeInForce.IOC,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Should be filtered out as expired (IOC logic)
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        eligible_orders = matching_service._get_eligible_rt_orders("PJM_RTO", ts_5m)
        
        # IOC orders expire immediately if not on first eligible tick
        assert len(eligible_orders) == 0 or not any(o.time_in_force == TimeInForce.IOC for o in eligible_orders)

class TestFeatureFlag:
    """Test feature flag behavior"""

    @pytest.mark.asyncio
    async def test_disabled_feature_flag_skips_processing(self, test_session):
        """When DETERMINISTIC_MATCHING_ENABLED=false, should skip processing"""
        with patch.dict(os.environ, {"DETERMINISTIC_MATCHING_ENABLED": "false"}):
            service = DeterministicMatchingService(test_session)
            assert not service.enabled
            
            result = await service.on_new_rt_tick("PJM_RTO", datetime.utcnow(), 50.0)
            
            assert result["status"] == "disabled"
            assert result["processed"] == 0

# Performance and Observability Tests
class TestObservability:
    """Test logging and metrics"""

    @pytest.mark.asyncio
    async def test_matching_latency_metrics(self, matching_service, test_session):
        """Should measure and report processing time"""
        # Create simple order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Process and check metrics
        result = await matching_service.on_new_rt_tick("PJM_RTO", datetime.utcnow(), 50.0)
        
        assert "processing_time_ms" in result["metrics"]
        assert result["metrics"]["processing_time_ms"] >= 0
        assert isinstance(result["metrics"]["processing_time_ms"], (int, float))

# Integration Tests with Price Ingestion
class TestPriceIngestionIntegration:
    """Test integration with price ingestion endpoints"""

    @pytest.mark.asyncio
    async def test_trigger_rt_matching_convenience_function(self, test_session):
        """Test trigger_rt_matching convenience function"""
        # Create order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=datetime.utcnow().replace(minute=0, second=0, microsecond=0),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Test convenience function
        with patch.dict(os.environ, {"DETERMINISTIC_MATCHING_ENABLED": "true"}):
            result = await trigger_rt_matching(
                test_session, "PJM_RTO", datetime.utcnow(), 45.0
            )
            
            assert result["status"] in ["completed", "disabled"]

    @pytest.mark.asyncio
    async def test_trigger_da_matching_convenience_function(self, test_session):
        """Test trigger_da_matching convenience function"""
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Create order
        order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING
        )
        test_session.add(order)
        test_session.commit()
        
        # Test convenience function  
        with patch.dict(os.environ, {"DETERMINISTIC_MATCHING_ENABLED": "true"}):
            result = await trigger_da_matching(
                test_session, "PJM_RTO", hour_start, 48.0
            )
            
            assert result["status"] in ["completed", "disabled"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
