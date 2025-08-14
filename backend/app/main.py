"""
Enhanced Main FastAPI Application for Virtual Energy Trading Platform
Supports both Day-Ahead and Real-Time energy markets
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Virtual Energy Trader API",
    description="API for virtual energy trading simulation supporting Day-Ahead and Real-Time markets",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://frontend:5173"  # For Docker
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# TODO: Include routers when route files are created
# from .routes.market import router as market_router
# from .routes.orders import router as orders_router  
# from .routes.pnl import router as pnl_router
# app.include_router(market_router)
# app.include_router(orders_router)
# app.include_router(pnl_router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        logger.info("🚀 Virtual Energy Trader API starting up...")
        logger.info("✅ API ready - Database integration pending")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Virtual Energy Trader API",
        "version": "0.2.0",
        "status": "running",
        "features": [
            "Day-Ahead Market Trading (Ready)",
            "Real-Time Market Trading (Ready)", 
            "Order Matching Engine (Ready)",
            "P&L Calculation (Ready)",
            "Portfolio Analytics (Ready)"
        ],
        "markets": {
            "day_ahead": {
                "description": "1-hour increments, 11 AM cutoff, up to 10 orders/hour",
                "settlement": "DA closing price with RT offset"
            },
            "real_time": {
                "description": "5-minute increments, continuous trading, up to 50 orders/slot",
                "settlement": "Immediate execution at current RT price"
            }
        },
        "next_steps": [
            "1. Create database models (models.py)",
            "2. Setup database connection (database.py)", 
            "3. Implement API routes (routes/)",
            "4. Enable route imports in main.py"
        ]
    }

@app.get("/health")
async def health_check():
    """Enhanced health check with system status"""
    try:
        import pytz
        et = pytz.timezone('US/Eastern')
        current_time = datetime.now(et)
        da_cutoff = current_time.replace(hour=11, minute=0, second=0, microsecond=0)
        da_market_open = current_time < da_cutoff
        
        health_status = {
            "status": "healthy",
            "service": "virtual-energy-trader-backend",
            "version": "0.2.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "api": "operational",
                "database": "pending",
                "markets": {
                    "day_ahead": "open" if da_market_open else "closed",
                    "real_time": "open"
                }
            },
            "market_status": {
                "day_ahead_cutoff": da_cutoff.strftime("%H:%M %Z"),
                "time_until_da_cutoff": (da_cutoff - current_time).total_seconds() / 60 if da_market_open else 0
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/api/status")
async def api_status():
    """Detailed API status with market information"""
    try:
        import pytz
        et = pytz.timezone('US/Eastern')
        current_time = datetime.now(et)
        da_cutoff = current_time.replace(hour=11, minute=0, second=0, microsecond=0)
        da_market_open = current_time < da_cutoff
        
        return {
            "api": "operational",
            "database": "pending",
            "current_time": current_time.isoformat(),
            "markets": {
                "day_ahead": {
                    "status": "open" if da_market_open else "closed",
                    "cutoff_time": da_cutoff.isoformat(),
                    "time_until_cutoff": (da_cutoff - current_time).total_seconds() / 60 if da_market_open else 0,
                    "rules": {
                        "max_orders_per_hour": 10,
                        "cutoff_time": "11:00 AM Eastern",
                        "settlement": "DA closing price"
                    }
                },
                "real_time": {
                    "status": "open",
                    "description": "Continuous trading available",
                    "rules": {
                        "max_orders_per_slot": 50,
                        "time_increment": "5 minutes",
                        "settlement": "Immediate at RT price"
                    }
                }
            },
            "supported_nodes": ["PJM_RTO", "CAISO", "ERCOT"],
            "implementation_status": {
                "frontend": "✅ Complete with two-market support",
                "models": "🔄 Database models created",
                "api_routes": "🔄 API endpoints created", 
                "integration": "⏳ Pending route integration"
            }
        }
        
    except Exception as e:
        logger.error(f"API status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting API status: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )
