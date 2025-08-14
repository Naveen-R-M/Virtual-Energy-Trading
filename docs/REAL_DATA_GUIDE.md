# 📊 Real Market Data Integration Guide

## Overview

The Virtual Energy Trading Platform now supports **real market data** from GridStatus.io API in addition to mock data. The system automatically attempts to fetch real data and falls back to mock data if the API is unavailable.

## 🔑 API Configuration

### GridStatus API Key

The application uses the GridStatus.io API for real market data. The API key is already configured in the `.env` files:

```env
GRIDSTATUS_API_KEY=6574119a04954abd93469f85194e07a0
GRIDSTATUS_BASE_URL=https://api.gridstatus.io
USE_REAL_DATA=true
```

### Supported ISOs

The platform supports real data from the following Independent System Operators (ISOs):

- **PJM** - PJM Interconnection (Mid-Atlantic region)
- **CAISO** - California Independent System Operator
- **ERCOT** - Electric Reliability Council of Texas
- **NYISO** - New York Independent System Operator
- **MISO** - Midcontinent Independent System Operator

## 🚀 Using Real Data

### Automatic Detection

The system automatically detects and uses real data when:
1. `USE_REAL_DATA=true` in environment
2. Valid API key is configured
3. GridStatus API is accessible
4. Data is available for the requested node/date

### Manual Control

You can control data source using these methods:

#### 1. Environment Variable
```bash
# Use real data (default)
USE_REAL_DATA=true

# Force mock data only
USE_REAL_DATA=false
```

#### 2. Command Line (fetch_prices.py)
```bash
# Force real data
python scripts/fetch_prices.py --node PJM_RTO --date 2025-01-14

# Force mock data
python scripts/fetch_prices.py --node PJM_RTO --date 2025-01-14 --mock
```

#### 3. Docker Environment
```yaml
environment:
  - USE_REAL_DATA=true  # or false
```

## 📡 API Endpoints

### Check Data Source
```bash
GET /api/market/data-source
```

Returns current data source status:
```json
{
  "using_real_data": true,
  "gridstatus_connected": true,
  "api_configured": true,
  "api_key_configured": true,
  "message": "Using GridStatus real data",
  "available_isos": ["PJM", "CAISO", "ERCOT", "NYISO", "MISO"]
}
```

### Get Available Nodes
```bash
GET /api/market/nodes?iso=PJM
```

Returns available trading nodes for an ISO:
```json
{
  "iso": "PJM",
  "nodes": [
    {
      "node_code": "PJM_RTO",
      "node_name": "PJM RTO Hub",
      "type": "hub"
    }
  ],
  "count": 3,
  "source": "gridstatus"  // or "default" for fallback
}
```

## 🧪 Testing Real Data

### 1. Test GridStatus Connection
```bash
cd backend
python scripts/test_gridstatus.py
```

This will:
- Verify API connection
- Fetch sample data from each ISO
- Display statistics
- Test fallback to mock data

### 2. Fetch Real Prices
```bash
# Fetch yesterday's data for PJM
python scripts/fetch_prices.py --node PJM_RTO --date yesterday

# Fetch specific date
python scripts/fetch_prices.py --node CAISO_NORTH --date 2025-01-14

# Force mock data
python scripts/fetch_prices.py --node ERCOT_HOUSTON --date today --mock
```

### 3. Via API
```bash
# Check data source
curl http://localhost:8000/api/market/data-source

# Get Day-Ahead prices (real if available)
curl "http://localhost:8000/api/market/da?date=2025-01-14&node=PJM_RTO"

# Get Real-Time prices
curl "http://localhost:8000/api/market/rt?start=2025-01-14T00:00:00Z&end=2025-01-14T01:00:00Z&node=PJM_RTO"
```

## 📈 Data Structure

### Day-Ahead Prices
Real data includes:
- `hour_start`: Hour beginning timestamp (UTC)
- `close_price`: Day-ahead LMP ($/MWh)
- `congestion`: Congestion component
- `loss`: Loss component

### Real-Time Prices
Real data includes:
- `timestamp`: 5-minute interval timestamp (UTC)
- `price`: Real-time LMP ($/MWh)
- `congestion`: Congestion component
- `loss`: Loss component

## 🔄 Fallback Behavior

The system uses intelligent fallback:

1. **Try Real Data First**
   - Connects to GridStatus API
   - Fetches requested data
   - Validates response

2. **Fallback to Mock if:**
   - API key not configured
   - API connection fails
   - No data available for node/date
   - API rate limit exceeded
   - Network timeout

3. **Mock Data Quality**
   - Realistic price curves
   - Peak/off-peak patterns
   - Appropriate volatility
   - Consistent with market behavior

## 🐳 Docker Configuration

### With Real Data
```yaml
# docker-compose.yml
environment:
  - GRIDSTATUS_API_KEY=6574119a04954abd93469f85194e07a0
  - USE_REAL_DATA=true
```

### Force Mock Data
```yaml
environment:
  - USE_REAL_DATA=false
```

## 📊 Performance Considerations

### API Rate Limits
- GridStatus API has rate limits
- Cached data in database to minimize API calls
- Automatic retry with exponential backoff

### Data Caching
- Fetched data stored in SQLite database
- Subsequent requests use cached data
- Cache invalidation after 24 hours

### Response Times
- Real data: 1-3 seconds (API call)
- Cached data: <100ms (database)
- Mock data: <50ms (generated)

## 🛠 Troubleshooting

### API Connection Issues

**Problem**: "GridStatus API not available"
```bash
# Check API key
echo $GRIDSTATUS_API_KEY

# Test connection
python scripts/test_gridstatus.py

# Check logs
docker-compose logs backend | grep GridStatus
```

### No Data Available

**Problem**: "No data found for node/date"
- GridStatus may not have historical data for all dates
- Try a more recent date (within last 30 days)
- Use a major hub node (e.g., PJM_RTO, HB_HOUSTON)

### Fallback to Mock

**Problem**: System using mock data when real expected
```python
# Check in Python
from app.services.market_data import MarketDataService
service = MarketDataService()
conn_info = await service.test_gridstatus_connection()
print(conn_info)
```

## 📝 Examples

### Complete Workflow with Real Data

```bash
# 1. Start application with real data
export USE_REAL_DATA=true
docker-compose up -d

# 2. Verify using real data
curl http://localhost:8000/api/market/data-source

# 3. Fetch real prices
curl "http://localhost:8000/api/market/da?date=2025-01-14&node=PJM_RTO"

# 4. Create order based on real prices
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "market": "day-ahead",
    "node": "PJM_RTO",
    "hour_start": "2025-01-15T14:00:00Z",
    "side": "buy",
    "limit_price": 45.50,
    "quantity_mwh": 2.0
  }'

# 5. Match and calculate P&L with real data
curl -X POST "http://localhost:8000/api/orders/match/day/2025-01-15?node=PJM_RTO"
curl -X POST "http://localhost:8000/api/pnl/simulate/day-ahead/2025-01-15?node=PJM_RTO"
```

## 🔍 Monitoring

Check data source in application:
1. Dashboard shows "Real Data" or "Mock Data" indicator
2. API health endpoint includes data source info
3. Logs show GridStatus API calls

```bash
# View real-time logs
docker-compose logs -f backend | grep -E "(GridStatus|Real|Mock)"
```

## 📚 Additional Resources

- [GridStatus.io Documentation](https://www.gridstatus.io/docs)
- [LMP Pricing Guide](https://www.pjm.com/markets-and-operations/energy/real-time/lmp)
- [ISO/RTO Map](https://www.ferc.gov/industries-resources/market-assessments/electric-power-markets)

---

The platform now seamlessly integrates real market data while maintaining reliability through intelligent fallback to mock data when needed. This ensures the application always works, whether for testing, development, or production trading simulation.
