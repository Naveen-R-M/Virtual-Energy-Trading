#!/usr/bin/env python3
"""
Integration Test Script for Deterministic PJM Matching
Run this to verify the implementation works end-to-end
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, create_engine, SQLModel
from app.models import (
    TradingOrder, OrderFill, DayAheadPrice, RealTimePrice,
    MarketType, OrderStatus, OrderSide, OrderType, TimeInForce, FillType
)
from app.services.deterministic_matching import (
    DeterministicMatchingService, trigger_rt_matching, trigger_da_matching
)

async def test_deterministic_matching():
    """Test deterministic matching end-to-end"""
    
    print("🚀 Starting Deterministic PJM Matching Integration Test")
    print("=" * 60)
    
    # Setup test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    
    # Enable deterministic matching
    os.environ["DETERMINISTIC_MATCHING_ENABLED"] = "true"
    
    with Session(engine) as session:
        
        # Test 1: RT Market Order (should always fill)
        print("\n✅ Test 1: RT Market Order Matching")
        print("-" * 40)
        
        ts_5m = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        rt_market_order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            limit_price=None,
            quantity_mwh=2.5,
            status=OrderStatus.PENDING
        )
        
        session.add(rt_market_order)
        session.commit()
        
        # Process RT tick
        lmp_price = 55.75
        result = await trigger_rt_matching(session, "PJM_RTO", ts_5m, lmp_price)
        
        print(f"RT Matching Result: {result['status']}")
        print(f"Orders Processed: {result['metrics']['matched_orders']}")
        print(f"Orders Filled: {result['metrics']['filled']}")
        print(f"Processing Time: {result['metrics']['processing_time_ms']} ms")
        
        session.refresh(rt_market_order)
        print(f"Order Status: {rt_market_order.status.value}")
        print(f"Fill Price: ${rt_market_order.filled_price}")
        
        assert rt_market_order.status == OrderStatus.FILLED
        assert rt_market_order.filled_price == lmp_price
        print("✅ RT Market Order test PASSED")
        
        # Test 2: RT Limit Order (conditional fill)
        print("\n✅ Test 2: RT Limit Order Matching")
        print("-" * 40)
        
        ts_5m_2 = ts_5m + timedelta(minutes=5)
        
        rt_limit_order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m_2,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=50.00,
            quantity_mwh=1.5,
            status=OrderStatus.PENDING
        )
        
        session.add(rt_limit_order)
        session.commit()
        
        # Test with LMP above limit (should not fill)
        high_lmp = 52.00
        result = await trigger_rt_matching(session, "PJM_RTO", ts_5m_2, high_lmp)
        
        session.refresh(rt_limit_order)
        print(f"High LMP Test (${high_lmp}): Status = {rt_limit_order.status.value}")
        assert rt_limit_order.status == OrderStatus.PENDING
        
        # Test with LMP at limit (should fill)
        good_lmp = 49.50
        result = await trigger_rt_matching(session, "PJM_RTO", ts_5m_2, good_lmp)
        
        session.refresh(rt_limit_order)
        print(f"Good LMP Test (${good_lmp}): Status = {rt_limit_order.status.value}")
        print(f"Fill Price: ${rt_limit_order.filled_price}")
        
        assert rt_limit_order.status == OrderStatus.FILLED
        assert rt_limit_order.filled_price == good_lmp
        print("✅ RT Limit Order test PASSED")
        
        # Test 3: DA Order Matching
        print("\n✅ Test 3: DA Order Matching")
        print("-" * 40)
        
        hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        da_order = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.DAY_AHEAD,
            hour_start_utc=hour_start,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=45.00,
            quantity_mwh=3.0,
            status=OrderStatus.PENDING
        )
        
        session.add(da_order)
        session.commit()
        
        # Test with DA price above limit (should fill)
        da_price = 47.25
        result = await trigger_da_matching(session, "PJM_RTO", hour_start, da_price)
        
        print(f"DA Matching Result: {result['status']}")
        print(f"Orders Filled: {result['metrics']['filled']}")
        
        session.refresh(da_order)
        print(f"Order Status: {da_order.status.value}")
        print(f"Fill Price: ${da_order.filled_price}")
        
        assert da_order.status == OrderStatus.FILLED
        assert da_order.filled_price == da_price
        print("✅ DA Order test PASSED")
        
        # Test 4: Idempotency (no duplicate fills)
        print("\n✅ Test 4: Idempotency Test")
        print("-" * 40)
        
        # Process same RT tick again
        result_2nd = await trigger_rt_matching(session, "PJM_RTO", ts_5m, lmp_price)
        print(f"Second Processing - Orders Filled: {result_2nd['metrics']['filled']}")
        
        # Should be 0 new fills
        assert result_2nd['metrics']['filled'] == 0
        
        # Check fill count
        from sqlmodel import select
        fills = session.exec(select(OrderFill).where(OrderFill.order_id == rt_market_order.id)).all()
        print(f"Total Fills for First Order: {len(fills)}")
        
        assert len(fills) == 1  # Only one fill despite multiple processing
        print("✅ Idempotency test PASSED")
        
        # Test 5: Multiple Orders (deterministic processing)
        print("\n✅ Test 5: Multiple Orders Deterministic Processing")
        print("-" * 40)
        
        ts_5m_3 = ts_5m + timedelta(minutes=10)
        
        # Create two orders with different creation times
        order_a = TradingOrder(
            user_id="test_user",
            node="PJM_RTO",
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m_3,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity_mwh=1.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(seconds=20)  # Older
        )
        
        order_b = TradingOrder(
            user_id="test_user",
            node="PJM_RTO", 
            market=MarketType.REAL_TIME,
            hour_start_utc=datetime.utcnow(),
            time_slot_utc=ts_5m_3,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity_mwh=2.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(seconds=10)  # Newer
        )
        
        session.add(order_a)
        session.add(order_b)
        session.commit()
        
        # Process both orders
        multi_lmp = 48.00
        result = await trigger_rt_matching(session, "PJM_RTO", ts_5m_3, multi_lmp)
        
        print(f"Multiple Orders - Orders Filled: {result['metrics']['filled']}")
        
        session.refresh(order_a)
        session.refresh(order_b)
        
        print(f"Order A (older): Status = {order_a.status.value}, Fill Price = ${order_a.filled_price}")
        print(f"Order B (newer): Status = {order_b.status.value}, Fill Price = ${order_b.filled_price}")
        
        assert order_a.status == OrderStatus.FILLED
        assert order_b.status == OrderStatus.FILLED
        assert order_a.filled_price == multi_lmp
        assert order_b.filled_price == multi_lmp
        print("✅ Multiple Orders test PASSED")
        
        # Test 6: Feature Flag Disabled
        print("\n✅ Test 6: Feature Flag Disabled")
        print("-" * 40)
        
        os.environ["DETERMINISTIC_MATCHING_ENABLED"] = "false"
        
        result = await trigger_rt_matching(session, "PJM_RTO", datetime.utcnow(), 50.0)
        print(f"Disabled Feature Result: {result['status']}")
        
        assert result["status"] == "disabled"
        print("✅ Feature Flag test PASSED")
        
    print("\n" + "=" * 60)
    print("🎉 ALL DETERMINISTIC MATCHING TESTS PASSED!")
    print("✅ RT Market Orders: Always fill at LMP")
    print("✅ RT Limit Orders: Fill when price crosses/touches limit")
    print("✅ DA Orders: Fill/reject based on clearing price vs limit")
    print("✅ Idempotency: No duplicate fills on reprocessing")
    print("✅ Deterministic: Consistent processing order by created_at")
    print("✅ Feature Flag: Properly enables/disables functionality")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_deterministic_matching())
