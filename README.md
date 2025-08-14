# ⚡ Virtual Energy Trader

A comprehensive simulation platform for trading electricity in the **Day-Ahead (DA)** and **Real-Time (RT)** energy markets. Help balance the grid while maximizing profits through strategic energy trading.

**Tech Stack**: React + Arco Design (frontend) • FastAPI + SQLite (backend) • GridStatus.io API (market data)

> 🎯 **Goal**: Buy low, sell high while helping balance energy markets as a virtual trader

---

## 📋 Project Requirements

This platform simulates a virtual energy trader that can:

### Day-Ahead Market
- **Trading Window**: Submit bids/offers before 11:00 AM local time
- **Time Slots**: 1-hour increments for next day delivery
- **Order Limits**: Maximum 10 orders per hour slot
- **Settlement**: Orders filled at market closing price if limit price is met
- **Order Types**: Buy/Sell with price and quantity (MWh)

### Real-Time Market
- **Frequency**: Price updates every 5 minutes
- **Purpose**: Offset day-ahead positions during actual delivery
- **P&L Calculation**: Compare DA contract price vs RT market prices

### Core Features
- 📊 **Real market data** from GridStatus.io API
- 📈 **Interactive visualizations** of DA hourly vs RT 5-minute pricing
- 📝 **Order management** with validation and limits enforcement
- ⚖️ **Matching engine** that settles DA orders at market close
- 💰 **P&L simulation** comparing DA positions against RT prices
- 📊 **Trading analytics** with KPIs, win rates, and performance metrics

---

## 🏗️ Architecture

```
Virtual-Energy-Trading/
├── frontend/           # React + Arco Design UI
│   ├── src/
│   │   ├── components/ # Charts, forms, tables
│   │   ├── pages/      # Dashboard, Orders, Analytics
│   │   └── api/        # API client
├── backend/            # FastAPI + SQLite API
│   ├── app/
│   │   ├── models/     # Database models
│   │   ├── routes/     # API endpoints
│   │   └── services/   # Business logic
│   └── scripts/        # Data ingestion, utilities
└── docs/               # Documentation
```

**Data Flow**: GridStatus.io → Backend → SQLite → API → React UI

---

## 🚀 Quick Start

### 🐳 Docker (Recommended - No Installation Required!)

**Prerequisites**: Only [Docker Desktop](https://docker.com/products/docker-desktop) required

```bash
cd Virtual-Energy-Trading

# Production setup
docker-compose up -d --build
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock

# OR Development setup (with hot reloading)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/fetch_prices.py --node PJM_RTO --date yesterday --mock
```

**That's it!** ✨
- 🖥️ **Frontend**: http://localhost (production) or http://localhost:5173 (dev)
- 🌐 **Backend API**: http://localhost:8000 
- 📚 **API Docs**: http://localhost:8000/docs

📖 **Detailed Docker Guide**: [docs/DOCKER.md](docs/DOCKER.md)

---

### 🛠️ Manual Installation (Alternative)

**Prerequisites**: Python 3.8+, Node.js 16+, Git

#### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend Setup  
```bash
cd frontend
npm install
npm run dev
```

📖 **Manual Setup Guide**: [docs/SETUP.md](docs/SETUP.md)

---

## 🎮 How to Use

### 1. **Select Market & Date**
Choose a grid node (e.g., PJM_RTO) and trading date

### 2. **Analyze Market Data**
- View DA hourly prices vs RT 5-minute price overlay
- Identify arbitrage opportunities
- Study price volatility patterns

### 3. **Place Orders**
- Submit buy/sell orders before 11:00 AM cutoff
- Set limit prices and quantities (MWh)
- Maximum 10 orders per hour slot

### 4. **Execute Trading Day**
- **Match Orders**: Run matching engine at DA market close
- Orders fill if limit price is met at closing price
- **Calculate P&L**: Offset DA positions against RT prices during delivery

### 5. **Analyze Performance**
- Review hourly P&L breakdown
- Track cumulative performance
- Analyze win rates and drawdowns

---

## 📡 API Reference

### Market Data
- `GET /api/market/da?date=YYYY-MM-DD&node=PJM_RTO` - Day-ahead hourly prices
- `GET /api/market/rt?start=...&end=...&node=PJM_RTO` - Real-time 5-min prices

### Order Management
- `POST /api/orders` - Submit new order
- `GET /api/orders?date=YYYY-MM-DD&node=PJM_RTO` - List orders

### Trading Operations
- `POST /api/match/day/{date}?node=PJM_RTO` - Execute DA market matching
- `POST /api/simulate/day/{date}?node=PJM_RTO` - Calculate P&L vs RT prices

---

## 💡 Trading Strategy Example

**Scenario**: Expecting high RT prices during afternoon peak

1. **Morning (before 11 AM)**: Submit DA buy order at $45/MWh for Hour 15 (3 PM)
2. **DA Close**: Order fills at $44/MWh (below your $45 limit)
3. **Real-Time**: RT prices average $52/MWh during Hour 15
4. **P&L**: Profit = ($52 - $44) × Quantity = $8/MWh profit

---

## 🧪 Development

### Run Tests
```bash
cd backend
pytest

cd ../frontend
npm test
```

### Database Schema
- `market_da`: Day-ahead hourly prices
- `market_rt`: Real-time 5-minute prices  
- `orders`: Trading orders with status
- `fills`: Executed trades with prices

---

## 📊 Screenshots

### Dashboard - Market Overview
- Dual-axis chart showing DA hourly vs RT 5-minute prices
- Order book visualization
- Key performance indicators

### Orders - Trading Interface  
- Order entry form with validation
- Orders table with status tracking
- Per-hour order count limits

### Analytics - Performance Review
- P&L breakdown by hour and day
- Trading statistics and win rates
- Performance comparison charts

---

## 🗺️ Roadmap

- **Phase 1**: ✅ Core trading platform (DA orders, RT offsetting, P&L)
- **Phase 2**: 🚧 Advanced analytics (portfolio optimization, risk metrics)
- **Phase 3**: 📋 Multi-node support, live data feeds
- **Phase 4**: 📋 Machine learning price predictions, automated strategies

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push branch: `git push origin feature-name` 
5. Submit a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[GridStatus.io](https://gridstatus.io)** - Real-time grid data API
- **[Arco Design](https://arco.design)** - React UI component library
- **[FastAPI](https://fastapi.tiangolo.com)** - Modern Python web framework

---

**Ready to start trading? Follow the setup instructions above and begin your virtual energy trading journey!** ⚡💰
