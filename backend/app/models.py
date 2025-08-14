"""
Enhanced Database Models for Virtual Energy Trading Platform
Supports both Day-Ahead and Real-Time markets with proper constraints
"""

from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

class MarketType(str, Enum):
    """Market type enumeration"""
    DAY_AHEAD = "day-ahead"
    REAL_TIME = "real-time"

class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class FillType(str, Enum):
    """Fill type for different settlement methods"""
    DA_CLOSING = "da_closing"  # Day-ahead closing price
    RT_IMMEDIATE = "rt_immediate"  # Real-time immediate settlement
    RT_OFFSET = "rt_offset"  # RT offset against DA position

# Base model for market prices
class MarketPriceBase(SQLModel):
    """Base class for market prices"""
    node: str = Field(index=True, description="Grid node identifier (e.g., PJM_RTO)")
    price: float = Field(description="Price in $/MWh")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Day-Ahead Market Prices (hourly)
class DayAheadPrice(MarketPriceBase, table=True):
    """Day-ahead market hourly prices"""
    __tablename__ = "market_da_prices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hour_start_utc: datetime = Field(index=True, description="Hour starting time in UTC")
    close_price: float = Field(description="DA closing price in $/MWh")

# Real-Time Market Prices (5-minute intervals)
class RealTimePrice(MarketPriceBase, table=True):
    """Real-time market 5-minute prices"""
    __tablename__ = "market_rt_prices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp_utc: datetime = Field(index=True, description="5-minute timestamp in UTC")
    price: float = Field(description="RT price in $/MWh")

# Enhanced Trading Orders supporting both markets
class TradingOrder(SQLModel, table=True):
    """Trading orders for both Day-Ahead and Real-Time markets"""
    __tablename__ = "trading_orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str = Field(unique=True, index=True, default_factory=lambda: str(uuid.uuid4()))
    
    # User and market identification
    user_id: str = Field(default="demo_user", index=True)
    node: str = Field(index=True, description="Grid node identifier")
    market: MarketType = Field(index=True, description="Market type: day-ahead or real-time")
    
    # Timing fields
    hour_start_utc: datetime = Field(index=True, description="Hour starting time in UTC")
    time_slot_utc: Optional[datetime] = Field(
        default=None, 
        index=True, 
        description="5-minute time slot for RT market"
    )
    
    # Order details
    side: OrderSide = Field(description="Buy or sell")
    limit_price: float = Field(description="Limit price in $/MWh")
    quantity_mwh: float = Field(description="Quantity in MWh")
    
    # Status and execution
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    filled_price: Optional[float] = Field(default=None, description="Actual filled price")
    filled_quantity: Optional[float] = Field(default=None, description="Actual filled quantity")
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = Field(default=None)
    filled_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    fills: List["OrderFill"] = Relationship(back_populates="order")

# Order fills/executions
class OrderFill(SQLModel, table=True):
    """Order fills and executions for both markets"""
    __tablename__ = "order_fills"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="trading_orders.id", index=True)
    
    # Fill details
    fill_type: FillType = Field(description="Type of fill settlement")
    filled_price: float = Field(description="Actual execution price")
    filled_quantity: float = Field(description="Actual execution quantity")
    
    # Market context
    market_price_at_fill: float = Field(description="Market price at time of fill")
    timestamp_utc: datetime = Field(description="Fill execution time")
    
    # P&L tracking
    gross_pnl: Optional[float] = Field(default=None, description="Gross P&L for this fill")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: TradingOrder = Relationship(back_populates="fills")

# P&L calculations and tracking
class PnLRecord(SQLModel, table=True):
    """P&L records for tracking performance"""
    __tablename__ = "pnl_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    node: str = Field(index=True)
    
    # Time period
    date: datetime = Field(index=True, description="Trading date")
    hour_start_utc: Optional[datetime] = Field(default=None, description="Specific hour for DA trades")
    
    # Market breakdown
    da_pnl: float = Field(default=0.0, description="Day-ahead market P&L")
    rt_pnl: float = Field(default=0.0, description="Real-time market P&L") 
    offset_pnl: float = Field(default=0.0, description="DA-RT offset P&L")
    total_pnl: float = Field(description="Total P&L for the period")
    
    # Volume tracking
    da_volume_mwh: float = Field(default=0.0, description="DA market volume")
    rt_volume_mwh: float = Field(default=0.0, description="RT market volume")
    
    # Performance metrics
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    total_trades: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

# Grid node configuration
class GridNode(SQLModel, table=True):
    """Grid node configuration and metadata"""
    __tablename__ = "grid_nodes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    node_code: str = Field(unique=True, index=True, description="Node code (e.g., PJM_RTO)")
    node_name: str = Field(description="Human-readable node name")
    iso_name: str = Field(description="ISO/RTO name")
    timezone: str = Field(description="Local timezone")
    
    # Market support
    supports_da_market: bool = Field(default=True)
    supports_rt_market: bool = Field(default=True)
    
    # Trading limits
    da_max_orders_per_hour: int = Field(default=10)
    rt_max_orders_per_slot: int = Field(default=50)
    min_quantity_mwh: float = Field(default=0.1)
    max_quantity_mwh: float = Field(default=100.0)
    
    # Status
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Create all tables
def create_tables(engine):
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)

# Sample data insertion functions
def insert_sample_nodes(session):
    """Insert sample grid nodes"""
    nodes = [
        GridNode(
            node_code="PJM_RTO",
            node_name="PJM Regional Transmission Organization",
            iso_name="PJM",
            timezone="America/New_York",
            supports_da_market=True,
            supports_rt_market=True
        ),
        GridNode(
            node_code="CAISO",
            node_name="California Independent System Operator",
            iso_name="CAISO",
            timezone="America/Los_Angeles",
            supports_da_market=True,
            supports_rt_market=True
        ),
        GridNode(
            node_code="ERCOT",
            node_name="Electric Reliability Council of Texas",
            iso_name="ERCOT",
            timezone="America/Chicago",
            supports_da_market=True,
            supports_rt_market=True
        )
    ]
    
    for node in nodes:
        session.add(node)
    session.commit()

# Validation functions
def validate_da_order_timing(hour_start_utc: datetime) -> bool:
    """Validate Day-Ahead order timing (before 11 AM cutoff)"""
    from pytz import timezone
    et = timezone('US/Eastern')
    local_time = datetime.now(et)
    cutoff_time = local_time.replace(hour=11, minute=0, second=0, microsecond=0)
    
    return local_time < cutoff_time

def validate_order_limits(
    session,
    node: str,
    market: MarketType,
    hour_start_utc: datetime,
    time_slot_utc: Optional[datetime] = None
) -> dict:
    """Validate order limits for the specified time slot"""
    
    if market == MarketType.DAY_AHEAD:
        # Count DA orders for this hour
        from sqlmodel import select
        existing_orders = session.exec(
            select(TradingOrder).where(
                TradingOrder.node == node,
                TradingOrder.market == MarketType.DAY_AHEAD,
                TradingOrder.hour_start_utc == hour_start_utc,
                TradingOrder.status != OrderStatus.CANCELLED
            )
        ).all()
        max_orders = 10
    else:
        # Count RT orders for this 5-minute slot
        from sqlmodel import select
        existing_orders = session.exec(
            select(TradingOrder).where(
                TradingOrder.node == node,
                TradingOrder.market == MarketType.REAL_TIME,
                TradingOrder.time_slot_utc == time_slot_utc,
                TradingOrder.status != OrderStatus.CANCELLED
            )
        ).all()
        max_orders = 50
    
    current_count = len(existing_orders)
    
    return {
        'is_valid': current_count < max_orders,
        'current_count': current_count,
        'max_count': max_orders,
        'remaining': max_orders - current_count
    }
