# 📚 Virtual Energy Trading Platform - API Documentation

## Overview

The Virtual Energy Trading Platform provides a comprehensive REST API for simulating energy trading in Day-Ahead (DA) and Real-Time (RT) electricity markets. The API supports professional trading session management, deterministic order matching, and real-time market data integration.

**Base URL**: `http://localhost:8000`  
**API Version**: `v0.2.0`  
**Documentation**: `http://localhost:8000/docs` (Swagger UI)

---

## 🏗️ API Categories

- [**Session Management**](#session-management) - Trading sessions, capital tracking, daily resets
- [**Market Data**](#market-data) - Day-Ahead and Real-Time price data
- [**Order Management**](#order-management) - Order creation, listing, and lifecycle
- [**Position & P&L**](#position--pnl) - Portfolio tracking and profit/loss calculation
- [**Deterministic Matching**](#deterministic-matching) - Price ingestion and order matching
- [**PJM Watchlist**](#pjm-watchlist) - Node monitoring and alerts
- [**System Status**](#system-status) - Health checks and configuration

---

## 🏦 Session Management

### Initialize Trading Session
**`POST /api/session/initialize`**

Initialize or resume a trading session for a user. This is the main entry point when the simulator starts.

**Parameters:**
- `user_id` (query, optional): User identifier (default: "demo_user")
- `trading_date` (query, optional): Trading date in YYYY-MM-DD format (default: today)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/session/initialize?user_id=trader_001" \
     -H "Content-Type: application/json"
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Trading session initialized successfully",
  "data": {
    "user_id": "trader_001",
    "trading_date": "2025-08-15",
    "session_state": "post_11am",
    "capital": {
      "starting_capital": 10000.0,
      "current_capital": 10000.0,
      "daily_starting_capital": 10000.0,
      "daily_current_capital": 10000.0
    },
    "pnl": {
      "total_realized_pnl": 0.0,
      "total_unrealized_pnl": 0.0,
      "daily_realized_pnl": 0.0,
      "daily_unrealized_pnl": 0.0,
      "daily_gross_pnl": 0.0
    },
    "trading_permissions": {
      "da_orders_enabled": false,
      "rt_orders_enabled": true
    },
    "positions": {
      "open_da_positions": 0,
      "open_rt_positions": 0,
      "carryover_da_positions": 0
    }
  }
}
```

### Get Session Summary
**`GET /api/session/summary`**

Get comprehensive session summary for a user.

**Parameters:**
- `user_id` (query, optional): User identifier
- `trading_date` (query, optional): Trading date in YYYY-MM-DD format

**Example Request:**
```bash
curl "http://localhost:8000/api/session/summary?user_id=trader_001"
```

### Get Market State
**`GET /api/session/market-state`**

Get current market state and trading permissions.

**Example Request:**
```bash
curl "http://localhost:8000/api/session/market-state"
```

**Example Response:**
```json
{
  "status": "success",
  "market_state": {
    "current_time": "2025-08-15T17:09:51.449915",
    "current_time_et": "2025-08-15 13:09:51 EDT",
    "session_state": "post_11am",
    "trading_permissions": {
      "da_orders_enabled": false,
      "rt_orders_enabled": true
    },
    "market_timing": {
      "da_cutoff_time": "11:00 EDT",
      "time_until_da_cutoff_minutes": 0,
      "is_pre_11am": false,
      "is_post_11am": true
    }
  }
}
```

### Check Trading Permissions
**`GET /api/session/trading-permissions`**

Check if trading is allowed for a user in a specific market.

**Parameters:**
- `market` (query, required): Market type ("day-ahead" or "real-time")
- `user_id` (query, optional): User identifier
- `trading_date` (query, optional): Trading date

**Example Request:**
```bash
curl "http://localhost:8000/api/session/trading-permissions?market=day-ahead&user_id=trader_001"
```

**Example Response:**
```json
{
  "status": "success",
  "trading_allowed": false,
  "reason": "Day-Ahead orders are not allowed after 11:00 AM ET",
  "market": "day-ahead",
  "user_id": "trader_001"
}
```

### Get Capital Summary
**`GET /api/session/capital`**

Get detailed capital and P&L summary for a user.

**Example Request:**
```bash
curl "http://localhost:8000/api/session/capital?user_id=trader_001"
```

**Example Response:**
```json
{
  "status": "success",
  "capital": {
    "starting_capital": 10000.0,
    "current_capital": 10000.0,
    "total_realized_pnl": 0.0,
    "total_unrealized_pnl": 0.0,
    "net_pnl": 0.0
  },
  "performance": {
    "total_trades": 0,
    "winning_trades": 0,
    "win_rate": 0,
    "max_drawdown": 0.0,
    "sharpe_ratio": null
  },
  "session_info": {
    "session_count": 1,
    "last_trading_date": "2025-08-15"
  }
}
```

---

## 📊 Market Data

### Get Day-Ahead Prices
**`GET /api/market/da`**

Get Day-Ahead hourly prices for a specific date and node.

**Parameters:**
- `date` (query, required): Date in YYYY-MM-DD format
- `node` (query, optional): Grid node identifier (default: "PJM_RTO")

**Example Request:**
```bash
curl "http://localhost:8000/api/market/da?date=2025-08-15&node=PJM_RTO"
```

**Example Response:**
```json
{
  "date": "2025-08-15",
  "node": "PJM_RTO",
  "market": "day-ahead",
  "prices": [
    {
      "hour_start": "2025-08-15T00:00:00",
      "node": "PJM_RTO",
      "close_price": 32.45,
      "price": 32.45
    },
    {
      "hour_start": "2025-08-15T01:00:00",
      "node": "PJM_RTO",
      "close_price": 28.90,
      "price": 28.90
    }
  ],
  "count": 24
}
```

### Get Real-Time Prices
**`GET /api/market/rt`**

Get Real-Time 5-minute prices for a specific time range and node.

**Parameters:**
- `start` (query, required): Start datetime in ISO format
- `end` (query, required): End datetime in ISO format  
- `node` (query, optional): Grid node identifier

**Example Request:**
```bash
curl "http://localhost:8000/api/market/rt?start=2025-08-15T14:00:00Z&end=2025-08-15T15:00:00Z&node=PJM_RTO"
```

### Get Latest Prices
**`GET /api/market/latest`**

Get latest available prices for both Day-Ahead and Real-Time markets.

**Example Request:**
```bash
curl "http://localhost:8000/api/market/latest?node=PJM_RTO"
```

### Get Market Summary
**`GET /api/market/summary/{date}`**

Get market summary statistics for a specific date.

**Example Request:**
```bash
curl "http://localhost:8000/api/market/summary/2025-08-15?node=PJM_RTO"
```

---

## 📝 Order Management

### Create Trading Order
**`POST /api/orders`**

Create a new trading order for Day-Ahead or Real-Time market with enhanced order types and time-in-force options.

**Request Body:**
```json
{
  "hour_start": "2025-08-15T14:00:00Z",
  "node": "PJM_RTO",
  "market": "real-time",
  "side": "buy",
  "order_type": "LMT",
  "limit_price": 50.00,
  "quantity_mwh": 2.5,
  "time_slot": "2025-08-15T14:05:00Z",
  "time_in_force": "GTC",
  "expires_at": "2025-08-15T18:00:00Z"
}
```

**Field Descriptions:**
- `market`: "day-ahead" or "real-time"
- `side`: "buy" or "sell"
- `order_type`: "MKT" (market) or "LMT" (limit)
- `time_in_force`: "GTC" (good till cancelled), "IOC" (immediate or cancel), "DAY" (good for day)

**Example - Market Order:**
```bash
curl -X POST "http://localhost:8000/api/orders" \
     -H "Content-Type: application/json" \
     -d '{
       "hour_start": "2025-08-15T14:00:00Z",
       "market": "real-time",
       "side": "buy",
       "order_type": "MKT",
       "quantity_mwh": 2.5,
       "time_slot": "2025-08-15T14:05:00Z"
     }'
```

**Example - Limit Order:**
```bash
curl -X POST "http://localhost:8000/api/orders" \
     -H "Content-Type: application/json" \
     -d '{
       "hour_start": "2025-08-15T15:00:00Z",
       "market": "day-ahead", 
       "side": "sell",
       "order_type": "LMT",
       "limit_price": 55.00,
       "quantity_mwh": 3.0,
       "time_in_force": "GTC"
     }'
```

**Example Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "message": "Real-Time order filled: Filled at current RT price",
  "details": {
    "filled_price": 48.75,
    "filled_quantity": 2.5,
    "order_status": "filled"
  }
}
```

### List Orders
**`GET /api/orders`**

List trading orders with optional filters.

**Parameters:**
- `date` (query, optional): Filter by date (YYYY-MM-DD)
- `node` (query, optional): Grid node (default: "PJM_RTO")
- `market` (query, optional): Market type filter
- `status` (query, optional): Order status filter
- `user_id` (query, optional): User identifier
- `limit` (query, optional): Maximum number of orders (default: 100)

**Example Request:**
```bash
curl "http://localhost:8000/api/orders?date=2025-08-15&status=filled&user_id=trader_001"
```

### Get Order Details
**`GET /api/orders/{order_id}`**

Get detailed information about a specific order.

**Example Request:**
```bash
curl "http://localhost:8000/api/orders/550e8400-e29b-41d4-a716-446655440000"
```

### Cancel Order
**`PUT /api/orders/{order_id}/cancel`**

Cancel a pending order.

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/api/orders/550e8400-e29b-41d4-a716-446655440000/cancel"
```

---

## 💰 Position & P&L

### Simulate Day P&L
**`POST /api/pnl/simulate/day/{date}`**

Calculate profit and loss for all positions on a specific date.

**Parameters:**
- `date` (path, required): Trading date in YYYY-MM-DD format
- `node` (query, optional): Grid node (default: "PJM_RTO")

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/pnl/simulate/day/2025-08-15?node=PJM_RTO"
```

**Example Response:**
```json
{
  "date": "2025-08-15",
  "node": "PJM_RTO",
  "total_pnl": 342.50,
  "data_quality": "complete_provisional",
  "hourly_breakdown": [
    {
      "hour_start": "2025-08-15T14:00:00Z",
      "da_orders": [
        {
          "order_id": "ORDER_123",
          "side": "buy",
          "quantity_mwh": 2.5,
          "da_fill_price": 48.00,
          "rt_avg_price": 52.30,
          "order_pnl": 10.75,
          "pnl_method": "bucket_by_bucket_settlement"
        }
      ],
      "hour_pnl": 10.75,
      "rt_intervals_available": 12
    }
  ],
  "pjm_compliance": {
    "formula_used": "P&L_H = Σ(P_DA - P_RT,t) × q/12",
    "settlement_method": "individual_5min_buckets"
  }
}
```

### Get Position Summary
**`GET /api/orders/position/summary`**

Get portfolio position summary for a user.

**Example Request:**
```bash
curl "http://localhost:8000/api/orders/position/summary?user_id=trader_001&node=PJM_RTO"
```

### Get Hourly Positions
**`GET /api/orders/position/hourly`**

Get hour-by-hour position breakdown.

**Example Request:**
```bash
curl "http://localhost:8000/api/orders/position/hourly?date=2025-08-15&user_id=trader_001"
```

---

## ⚡ Deterministic Matching

### RT Price Ingestion
**`POST /api/internal/prices/ingest/rt`**

Ingest Real-Time 5-minute price and trigger deterministic matching.

**Request Body:**
```json
{
  "node_id": "PJM_RTO",
  "timestamp": "2025-08-15T14:05:00Z",
  "lmp": 52.75,
  "energy_component": 48.20,
  "congestion_component": 3.55,
  "loss_component": 1.00
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/internal/prices/ingest/rt" \
     -H "Content-Type: application/json" \
     -d '{
       "node_id": "PJM_RTO",
       "timestamp": "2025-08-15T14:05:00Z",
       "lmp": 52.75
     }'
```

**Example Response:**
```json
{
  "status": "success",
  "message": "RT price ingested and matching completed",
  "matching_triggered": true,
  "matching_results": {
    "status": "completed",
    "node_id": "PJM_RTO",
    "timestamp": "2025-08-15T14:05:00Z",
    "lmp_price": 52.75,
    "metrics": {
      "matched_orders": 3,
      "filled": 2,
      "rejected": 0,
      "processing_time_ms": 12.5
    },
    "results": [
      {
        "order_id": "ORDER_123",
        "status": "filled",
        "filled_price": 52.75,
        "filled_quantity": 2.5,
        "execution_time": "2025-08-15T14:05:00Z",
        "exec_ref": "RT_5M"
      }
    ]
  }
}
```

### DA Price Ingestion
**`POST /api/internal/prices/ingest/da`**

Ingest Day-Ahead hourly clearing price and trigger deterministic matching.

**Request Body:**
```json
{
  "node_id": "PJM_RTO",
  "hour_start": "2025-08-16T14:00:00Z",
  "clearing_price": 48.50
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/internal/prices/ingest/da" \
     -H "Content-Type: application/json" \
     -d '{
       "node_id": "PJM_RTO",
       "hour_start": "2025-08-16T14:00:00Z",
       "clearing_price": 48.50
     }'
```

### Batch Price Ingestion
**`POST /api/internal/prices/ingest/batch/rt`**
**`POST /api/internal/prices/ingest/batch/da`**

Ingest multiple prices and trigger matching for each.

**Example Request (RT Batch):**
```bash
curl -X POST "http://localhost:8000/api/internal/prices/ingest/batch/rt" \
     -H "Content-Type: application/json" \
     -d '[
       {
         "node_id": "PJM_RTO",
         "timestamp": "2025-08-15T14:00:00Z",
         "lmp": 50.25
       },
       {
         "node_id": "PJM_RTO", 
         "timestamp": "2025-08-15T14:05:00Z",
         "lmp": 52.75
       }
     ]'
```

### Get Matching Status
**`GET /api/internal/prices/matching/status`**

Get deterministic matching configuration and status.

**Example Request:**
```bash
curl "http://localhost:8000/api/internal/prices/matching/status"
```

**Example Response:**
```json
{
  "deterministic_matching_enabled": true,
  "feature_status": "ready",
  "supported_markets": ["real-time", "day-ahead"],
  "matching_triggers": [
    "RT 5-minute price ingestion",
    "DA hourly price ingestion"
  ],
  "order_types_supported": ["MKT", "LMT"],
  "time_in_force_supported": ["GTC", "IOC", "DAY"]
}
```

---

## 🎯 Complete Trading Workflow Examples

### Example 1: First-Time Trader Setup

```bash
# 1. Initialize new trader
curl -X POST "http://localhost:8000/api/session/initialize?user_id=new_trader"

# 2. Check current market state
curl "http://localhost:8000/api/session/market-state"

# 3. Check trading permissions
curl "http://localhost:8000/api/session/trading-permissions?market=real-time&user_id=new_trader"
```

### Example 2: Place Real-Time Market Order

```bash
# 1. Create RT market order (fills immediately at current price)
curl -X POST "http://localhost:8000/api/orders" \
     -H "Content-Type: application/json" \
     -d '{
       "hour_start": "2025-08-15T14:00:00Z",
       "market": "real-time",
       "side": "buy",
       "order_type": "MKT",
       "quantity_mwh": 2.5,
       "time_slot": "2025-08-15T14:05:00Z",
       "time_in_force": "IOC"
     }'

# 2. Check order status
curl "http://localhost:8000/api/orders?user_id=demo_user&status=filled"

# 3. Check updated capital
curl "http://localhost:8000/api/session/capital?user_id=demo_user"
```

### Example 3: Place Day-Ahead Limit Order (Before 11 AM)

```bash
# 1. Check if DA orders are allowed
curl "http://localhost:8000/api/session/trading-permissions?market=day-ahead"

# 2. Create DA limit order for tomorrow's delivery
curl -X POST "http://localhost:8000/api/orders" \
     -H "Content-Type: application/json" \
     -d '{
       "hour_start": "2025-08-16T16:00:00Z",
       "market": "day-ahead",
       "side": "sell",
       "order_type": "LMT", 
       "limit_price": 60.00,
       "quantity_mwh": 3.0,
       "time_in_force": "GTC"
     }'

# 3. List pending DA orders
curl "http://localhost:8000/api/orders?market=day-ahead&status=pending"
```

### Example 4: Simulate Price Event and Matching

```bash
# 1. Ingest new RT price (triggers matching)
curl -X POST "http://localhost:8000/api/internal/prices/ingest/rt" \
     -H "Content-Type: application/json" \
     -d '{
       "node_id": "PJM_RTO",
       "timestamp": "2025-08-15T14:10:00Z",
       "lmp": 48.25
     }'

# 2. Check matching results in response
# 3. Verify orders were filled
curl "http://localhost:8000/api/orders?status=filled"

# 4. Calculate P&L
curl -X POST "http://localhost:8000/api/pnl/simulate/day/2025-08-15"
```

### Example 5: Daily Reset for New Trading Day

```bash
# 1. Perform daily reset
curl -X POST "http://localhost:8000/api/session/daily-reset?user_id=trader_001&trading_date=2025-08-16"

# 2. Check carryover positions from yesterday
curl "http://localhost:8000/api/session/carryover-positions?user_id=trader_001&trading_date=2025-08-16"

# 3. Verify daily counters are reset
curl "http://localhost:8000/api/session/summary?user_id=trader_001&trading_date=2025-08-16"
```

---

## 📈 PJM Watchlist

### Get Watchlist
**`GET /api/pjm/watchlist`**

Get user's PJM node watchlist with real-time prices.

### Add to Watchlist  
**`POST /api/pjm/watchlist`**

Add PJM nodes to user's watchlist.

### Set Price Alert
**`POST /api/pjm/alerts`**

Create price threshold alerts for nodes.

---

## 🔍 System Status

### Health Check
**`GET /health`**

Enhanced health check with market status.

**Example Request:**
```bash
curl "http://localhost:8000/health"
```

**Example Response:**
```json
{
  "status": "healthy",
  "service": "virtual-energy-trader-backend",
  "version": "0.2.0",
  "timestamp": "2025-08-15T17:09:51.123456",
  "components": {
    "api": "operational",
    "database": "operational",
    "markets": {
      "day_ahead": "closed",
      "real_time": "open"
    }
  },
  "market_status": {
    "day_ahead_cutoff": "11:00 EST",
    "time_until_da_cutoff": 0
  }
}
```

### API Status
**`GET /api/status`**

Detailed API status with market information.

### Session System Status
**`GET /api/session/status`**

Get trading session system status and configuration.

**Example Response:**
```json
{
  "status": "operational",
  "configuration": {
    "starting_capital": 10000.0,
    "daily_reset_enabled": true,
    "capital_persistence": true
  },
  "features": [
    "Starting capital management",
    "Daily P&L tracking",
    "Session state management", 
    "DA order cutoff enforcement",
    "Carryover position handling",
    "Real-time capital updates"
  ]
}
```

---

## 🚨 Error Handling

### Common Error Responses

**422 Unprocessable Entity - Trading Not Allowed:**
```json
{
  "detail": "Day-Ahead orders are not allowed after 11:00 AM ET"
}
```

**422 Unprocessable Entity - Order Validation:**
```json
{
  "detail": "Limit price is required for limit orders"
}
```

**422 Unprocessable Entity - Position Limits:**
```json
{
  "detail": "Order limit exceeded: 10/10 orders already placed for this Day-Ahead hour"
}
```

**503 Service Unavailable - Data Issues:**
```json
{
  "detail": "Real data unavailable: GridStatus API connection failed"
}
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
DATABASE_URL=sqlite:///./data/energy_trader.db
USE_REAL_DATA=true
DEFAULT_NODE=PJM_RTO

# GridStatus API
GRIDSTATUS_API_KEY=your_api_key_here
GRIDSTATUS_BASE_URL=https://api.gridstatus.io

# Market Rules
MARKET_TIMEZONE=America/New_York
ORDER_CUTOFF_HOUR=11
MAX_ORDERS_PER_HOUR=10

# Trading Session Management
SIM_STARTING_CAPITAL=10000.0
SIM_DAILY_RESET_ENABLED=true
SIM_CAPITAL_PERSISTENCE=true

# Deterministic Matching
DETERMINISTIC_MATCHING_ENABLED=true
MATCHING_LATENCY_THRESHOLD_MS=100
```

---

## 🎯 Best Practices

### **Order Management**
1. **Check permissions** before creating orders using `/api/session/trading-permissions`
2. **Use appropriate order types**: MKT for immediate execution, LMT for price control
3. **Set time-in-force** based on strategy: GTC for persistent, IOC for immediate
4. **Monitor fills** via order status endpoints

### **Session Management**  
1. **Initialize session** on app startup with `/api/session/initialize`
2. **Check market state** regularly with `/api/session/market-state`
3. **Perform daily reset** at start of new trading day
4. **Monitor capital** changes with `/api/session/capital`

### **Price Ingestion & Matching**
1. **Use batch endpoints** for high-volume price ingestion
2. **Monitor matching latency** via response metrics
3. **Verify idempotency** by checking duplicate ingestion behavior
4. **Review matching logs** for debugging and performance tuning

### **P&L Calculation**
1. **Use PJM-compliant calculation** for accurate settlement simulation
2. **Check data quality badges** to understand P&L reliability
3. **Wait for verified data** (T+2 days) for final settlement accuracy
4. **Monitor unrealized P&L** for open positions

---

## 📞 Support & Resources

- **API Documentation**: http://localhost:8000/docs (Interactive Swagger UI)
- **Health Endpoint**: http://localhost:8000/health
- **System Status**: http://localhost:8000/api/status
- **Session Status**: http://localhost:8000/api/session/status

The Virtual Energy Trading Platform API provides enterprise-grade functionality for energy market simulation with proper market mechanics, session management, and deterministic order execution. 🚀