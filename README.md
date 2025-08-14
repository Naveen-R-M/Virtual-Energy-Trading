# ⚡ Virtual Energy Trading Platform

A sophisticated simulation platform for trading electricity in **Day-Ahead (DA)** and **Real-Time (RT)** energy markets. Built with **React + Arco Design** (frontend) and **FastAPI + SQLite** (backend), integrated with **GridStatus.io API for real market data**.

> **Goal:** Buy low, sell high — while helping balance the energy grid through strategic trading in both hourly and 5-minute markets.

![Energy Trading Platform](https://img.shields.io/badge/Status-Ready%20to%20Trade-success)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)

## 🎯 Features

### Two-Market Trading System
- **📅 Day-Ahead Market**
  - 1-hour delivery slots
  - 11 AM daily cutoff (EST)
  - Max 10 orders per hour
  - Settlement at DA closing price
  - P&L calculated against RT prices during delivery

- **⚡ Real-Time Market**
  - 5-minute delivery slots with countdown timers
  - Continuous trading (24/7)
  - Max 50 orders per slot
  - Immediate settlement at execution
  - Auto-selects next available slot
  - 2-minute lock before execution

### Position Management & Validation
- **🚫 No Naked Short Selling** — Must buy energy before selling
- **📊 Real-time Position Tracking** — Net position per time slot
- **✅ Smart Validation** — Client and server-side checks
- **📈 Position Display** — Shows max sellable quantity

### Data Source Control (STRICT MODE)
- **🔴 USE_REAL_DATA=true** — ONLY uses GridStatus API, no fallback
- **🟢 USE_REAL_DATA=false** — ONLY uses mock data generation
- **⚠️ No Automatic Fallback** — If real data fails, API returns 503 errors
- **🔧 Configure via `.env`** — Strict enforcement of data source

### Core Functionality
- **📈 Advanced Price Visualization** — Overlay DA hourly vs RT 5-minute prices
- **📝 Smart Order Management** — Market-specific validation and limit enforcement
- **✅ Automated Matching Engine** — Fill orders based on limit prices
- **💰 P&L Simulation** — Calculate profits comparing DA fills vs RT delivery prices
- **📊 Performance Analytics** — Win rate, max drawdown, volume tracking
- **🎯 Portfolio View** — Combined P&L across both markets

## 🏗 Architecture

```
frontend/              # React + TypeScript + Arco Design
├── src/
│   ├── components/    # Charts, forms, tables
│   ├── pages/        # Dashboard, Order Management
│   └── utils/        # API client, mock data
│
backend/              # FastAPI + SQLModel + SQLite
├── app/
│   ├── models.py     # Database models
│   ├── database.py   # DB connection
│   ├── routes/       # API endpoints
│   │   ├── market.py # Price data endpoints
│   │   ├── orders.py # Order management
│   │   └── pnl.py    # P&L calculations
│   └── services/     # Business logic
│       ├── market_data.py     # Price fetching (STRICT MODE)
│       ├── position_manager.py # Position validation
│       ├── matching_engine.py # Order matching
│       └── pnl_calculator.py  # P&L engine
└── scripts/
    ├── init_db.py    # Database setup
    └── fetch_prices.py # Data ingestion
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Environment Configuration

```bash
cd backend
cp .env.example .env
```

Edit `.env` and configure data source:
```env
# STRICT MODE - No fallback between real and mock data
USE_REAL_DATA=true  # Set to 'false' for mock data only
GRIDSTATUS_API_KEY=your_api_key_here  # Required if USE_REAL_DATA=true
```

### One-Command Setup

#### Windows
```bash
./start-all.bat
```

#### Linux/Mac
```bash
chmod +x start-all.sh
./start-all.sh
```

This will:
1. Create Python virtual environment
2. Install all dependencies
3. Initialize the database
4. Start both backend and frontend servers
5. Use data source based on `USE_REAL_DATA` flag

### Manual Setup

#### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure data source
cp .env.example .env
# Edit .env - set USE_REAL_DATA and API key

# Initialize database
python scripts/init_db.py

# Start server
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: http://localhost:5173

## 📡 API Documentation

Interactive API docs available at: http://localhost:8000/docs

### Key Endpoints

#### Market Data
- `GET /api/market/da?date=YYYY-MM-DD&node=PJM_RTO` - Day-ahead prices
- `GET /api/market/rt?start=...&end=...&node=PJM_RTO` - Real-time prices
- `GET /api/market/latest?node=PJM_RTO` - Latest prices for both markets
- `GET /api/market/data-source` - Check data source status

#### Order Management
- `POST /api/orders` - Create order with position validation
- `GET /api/orders` - List orders with filters
- `POST /api/orders/match/day/{date}` - Match DA orders
- `GET /api/orders/position/summary` - Portfolio position summary
- `GET /api/orders/position/hourly` - Hour-by-hour positions

#### P&L Simulation
- `POST /api/pnl/simulate/day-ahead/{date}` - DA P&L calculation
- `POST /api/pnl/simulate/real-time/{date}` - RT P&L calculation
- `GET /api/pnl/portfolio/{date}` - Combined portfolio P&L
- `GET /api/pnl/analytics` - Performance metrics

## 📊 Data Source Behavior

### Real Data Mode (`USE_REAL_DATA=true`)
```json
// Success Response
{
  "prices": [...],
  "source": "gridstatus"
}

// Failure Response (NO FALLBACK)
{
  "status_code": 503,
  "detail": "Real data unavailable: GridStatus API error"
}
```

### Mock Data Mode (`USE_REAL_DATA=false`)
- Generates realistic price patterns
- Peak hours (2-7 PM): $50-80/MWh
- Off-peak (midnight-6 AM): $20-40/MWh
- RT prices ±15% volatility from DA

## 💼 Business Logic

### Position Management Rules
1. **Initial State**: Net position = 0 MWh
2. **Buy Order**: Increases net position
3. **Sell Order**: Decreases net position (must not go negative)
4. **Validation**: Max sellable = Current net position

Example:
```
Hour 14:00 - Buy 10 MWh → Net: +10 MWh
Hour 14:00 - Sell 6 MWh → Net: +4 MWh  ✓
Hour 14:00 - Sell 5 MWh → BLOCKED (Max: 4 MWh)
```

### Real-Time Market Features
- **Auto-selection**: Next available slot pre-selected
- **Live Countdown**: Shows time until execution
- **Slot Locking**: Orders lock 2 minutes before execution
- **Warning System**: Alerts when slot is about to lock

## 🖼 Screenshots

### Dashboard
- Dual-axis price chart (DA vs RT)
- P&L performance over time
- Market status indicators
- KPI cards with win rate

### Order Management
- Market type selection (DA/RT)
- Position display with max sellable
- Real-time countdown for RT slots
- Order table with status tracking

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Test position validation
pytest tests/test_position_manager.py

# Test data source modes
pytest tests/test_market_data.py
```

## 🔧 Configuration

### Backend (.env)
```env
# Data Source (STRICT MODE)
USE_REAL_DATA=true              # true for real data, false for mock
GRIDSTATUS_API_KEY=your_key     # Required if USE_REAL_DATA=true

# Database
DATABASE_URL=sqlite:///./data/trading.db

# Market Settings
DEFAULT_NODE=PJM_RTO
MARKET_TIMEZONE=America/New_York
ORDER_CUTOFF_HOUR=11
MAX_ORDERS_PER_HOUR=10
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
```

## 📈 Roadmap

- [x] Phase 1: Two-market architecture
- [x] Phase 2: Position validation (no naked shorts)
- [x] Phase 3: Real-time market countdown/locking
- [x] Phase 4: Strict data source control
- [x] Phase 5: GridStatus.io API integration
- [ ] Phase 6: Advanced analytics and ML predictions
- [ ] Phase 7: Multi-node arbitrage support
- [ ] Phase 8: Risk management tools

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- [Arco Design](https://arco.design) - UI component library
- [FastAPI](https://fastapi.tiangolo.com) - Modern web API framework
- [Recharts](https://recharts.org) - Charting library
- [GridStatus.io](https://gridstatus.io) - Real energy market data

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check API docs at http://localhost:8000/docs
- Review the [Trading Strategies Guide](docs/TRADING_STRATEGIES.md)

---

**Built for CVector Energy Trading Assessment** | Demonstrating expertise in full-stack development, financial logic validation, and energy market simulation
