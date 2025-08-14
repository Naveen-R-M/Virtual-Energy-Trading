# 🚀 Development Setup Instructions

Follow these step-by-step instructions to set up the Virtual Energy Trading platform.

## Prerequisites

- **Python 3.8+** (Download from [python.org](https://python.org))
- **Node.js 16+** (Download from [nodejs.org](https://nodejs.org))
- **Git** (Download from [git-scm.com](https://git-scm.com))

## Step-by-Step Setup

### 1. Clone and Navigate to Project
```bash
cd C:\Users\navee\Projects\Virtual-Energy-Trading
```

### 2. Backend Setup

#### A. Create Python Virtual Environment
```bash
cd backend
python -m venv .venv
```

#### B. Activate Virtual Environment
**Windows:**
```cmd
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

#### C. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### D. Setup Environment Variables
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env file with your settings (optional for now)
# You can use the defaults for development
```

#### E. Initialize Database
Create the initial database setup script:

**File: `backend/scripts/init_db.py`**
```python
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.models import SQLModel

def init_database():
    """Initialize the database with all tables."""
    SQLModel.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
```

Run the initialization:
```bash
python scripts/init_db.py
```

#### F. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Interactive API**: http://localhost:8000/redoc

### 3. Frontend Setup

#### A. Navigate to Frontend Directory
```bash
cd ../frontend
```

#### B. Install Node.js Dependencies
```bash
npm install
```

#### C. Start Development Server
```bash
npm run dev
```

The frontend will be available at:
- **UI**: http://localhost:5173

### 4. Verify Installation

#### Test Backend
```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response: {"status": "healthy"}
```

#### Test Frontend
Open your browser to http://localhost:5173 and verify the React app loads.

## Next Steps

### 1. Create Basic Models
Create your database models in `backend/app/models.py`:

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"

class MarketDAPrice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    node: str = Field(index=True)
    hour_start_utc: datetime = Field(index=True)
    close_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketRTPrice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    node: str = Field(index=True)
    timestamp_utc: datetime = Field(index=True)
    price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TradingOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="demo_user")
    node: str = Field(index=True)
    hour_start_utc: datetime = Field(index=True)
    side: OrderSide
    limit_price: float
    quantity_mwh: float
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    filled_price: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2. Create Basic FastAPI App
Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Virtual Energy Trader API",
    description="API for virtual energy trading simulation",
    version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Virtual Energy Trader API"}
```

### 3. Create Database Connection
Create `backend/app/database.py`:

```python
from sqlmodel import create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./energy_trader.db")

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session
```

### 4. Start Development

Now you're ready to start implementing the features according to the TodoList.md:

1. **Day 1**: Complete database models and basic API endpoints
2. **Day 2**: Implement order matching and P&L calculation
3. **Day 3**: Build the React frontend components
4. **Day 4**: Add analytics and polish the UI
5. **Day 5**: Testing and documentation

## Common Issues & Solutions

### Python Virtual Environment Issues
- **Windows Path Issues**: Use forward slashes or escape backslashes
- **Permission Errors**: Run command prompt as administrator
- **Module Not Found**: Ensure virtual environment is activated

### Database Issues
- **SQLite Locked**: Close any DB browser tools
- **Migration Errors**: Delete the .db file and reinitialize

### Frontend Issues
- **Port Already in Use**: Change port with `npm run dev -- --port 3000`
- **Module Resolution**: Clear npm cache with `npm cache clean --force`

### API Connection Issues
- **CORS Errors**: Ensure CORS middleware is properly configured
- **Network Errors**: Verify backend is running on correct port

## Development Workflow

1. **Start Backend**: `cd backend && uvicorn app.main:app --reload`
2. **Start Frontend**: `cd frontend && npm run dev`
3. **Make Changes**: Edit code files
4. **Test Changes**: Both servers auto-reload on file changes
5. **Commit Progress**: Regular git commits as you complete features

## Ready to Code! 🎯

You now have a complete development environment set up. Follow the TodoList.md for detailed implementation steps, and refer to the README.md for project overview and architecture details.

**Happy Trading!** ⚡💰
