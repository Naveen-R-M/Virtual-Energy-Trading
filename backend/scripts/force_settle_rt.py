#!/usr/bin/env python3
"""
Force settle pending RT orders for testing purposes.
This script will settle all pending RT orders whose execution time has passed.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select, and_

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_session
from app.models import Order
from app.services.market_service import MarketService
from app.services.order_service import OrderService

async def force_settle_rt_orders():
    """Force settlement of pending RT orders."""
    
    async with get_session() as session:
        market_service = MarketService(session)
        order_service = OrderService(session)
        
        # Get current time
        now = datetime.now(timezone.utc)
        print(f"🕐 Current time (UTC): {now}")
        print(f"🕐 Current time (EDT): {now.astimezone()}")
        print("-" * 50)
        
        # Find all pending RT orders
        stmt = select(Order).where(
            and_(
                Order.status == 'pending',
                Order.market == 'real-time'
            )
        )
        
        result = await session.execute(stmt)
        pending_orders = result.scalars().all()
        
        if not pending_orders:
            print("ℹ️ No pending RT orders found.")
            return
        
        print(f"📋 Found {len(pending_orders)} pending RT orders")
        print("-" * 50)
        
        settled_count = 0
        for order in pending_orders:
            # Check if order's execution time has passed
            order_time = order.time_slot_utc if order.time_slot_utc else order.hour_start
            
            print(f"\n🔍 Order {order.order_id[:8]}...")
            print(f"   Time Slot: {order_time}")
            print(f"   Status: {order.status}")
            print(f"   Side: {order.side}, Limit: ${order.limit_price}")
            
            # For testing, we'll settle orders that should have executed
            # Add 5 minutes to account for the interval duration
            from datetime import timedelta
            execution_end = order_time + timedelta(minutes=5)
            
            if execution_end <= now:
                print(f"   ⏰ Execution time has passed, settling...")
                
                # Generate a realistic RT price for this time
                # This is mock data - in production, you'd fetch real RT prices
                hour = order_time.hour
                if 6 <= hour < 9 or 17 <= hour < 21:
                    # Peak hours
                    rt_price = 42.50 + (hash(str(order_time)) % 100) / 50
                else:
                    # Off-peak
                    rt_price = 40.00 + (hash(str(order_time)) % 100) / 100
                
                # Determine if order fills based on limit price
                fills = False
                if order.side == 'buy':
                    fills = order.limit_price >= rt_price
                else:  # sell
                    fills = order.limit_price <= rt_price
                
                if fills:
                    order.status = 'filled'
                    order.filled_price = rt_price
                    order.filled_at = now
                    print(f"   ✅ FILLED at ${rt_price:.2f}")
                    
                    # Calculate P&L
                    if order.side == 'buy':
                        # For buy: profit if we can sell at higher price later
                        # This is simplified - actual P&L depends on future RT prices
                        order.pnl = (rt_price * 1.02 - rt_price) * order.quantity_mwh
                    else:
                        # For sell: profit if we sold above market
                        order.pnl = (rt_price - rt_price * 0.98) * order.quantity_mwh
                    
                    print(f"   💰 P&L: ${order.pnl:.2f}")
                else:
                    order.status = 'rejected'
                    order.rejected_reason = f"Limit not met. RT price: ${rt_price:.2f}"
                    print(f"   ❌ REJECTED - Limit not met (RT: ${rt_price:.2f})")
                
                order.updated_at = now
                settled_count += 1
            else:
                time_until = (execution_end - now).total_seconds()
                print(f"   ⏳ Not ready yet. Executes in {time_until/60:.1f} minutes")
        
        # Commit changes
        await session.commit()
        
        print("\n" + "=" * 50)
        print(f"✅ Settled {settled_count} RT orders")
        print("=" * 50)

async def main():
    """Main entry point."""
    print("=" * 50)
    print("🚀 RT Order Settlement Tool")
    print("=" * 50)
    
    await force_settle_rt_orders()

if __name__ == "__main__":
    asyncio.run(main())
