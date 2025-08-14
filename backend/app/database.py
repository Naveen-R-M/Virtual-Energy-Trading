"""
Database configuration and session management for Virtual Energy Trading Platform
"""

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment or use default SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/trading.db")

# Ensure data directory exists for SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using SQLite database at: {db_path}")

# Create engine with connection pooling
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Set to True for SQL debugging
    connect_args=connect_args
)

# Create session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False
)

def init_db():
    """Initialize database and create all tables"""
    try:
        logger.info("Initializing database...")
        SQLModel.metadata.create_all(engine)
        
        # Insert default grid nodes if they don't exist
        from .models import GridNode
        from sqlmodel import select
        with Session(engine) as session:
            existing_nodes = len(session.exec(select(GridNode)).all())
            if existing_nodes == 0:
                logger.info("Inserting default grid nodes...")
                from .models import insert_sample_nodes
                insert_sample_nodes(session)
                logger.info("Default grid nodes inserted successfully")
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def get_session():
    """Dependency for getting database session"""
    with Session(engine) as session:
        yield session

def get_db():
    """Alternative dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check function
def check_database_health() -> dict:
    """Check database health and connectivity"""
    try:
        with Session(engine) as session:
            # Simple query to test connection
            session.exec("SELECT 1")
            
            # Count tables
            from .models import GridNode, TradingOrder, DayAheadPrice, RealTimePrice
            from sqlmodel import select
            
            node_count = len(session.exec(select(GridNode)).all())
            order_count = len(session.exec(select(TradingOrder)).all())
            da_price_count = len(session.exec(select(DayAheadPrice)).all())
            rt_price_count = len(session.exec(select(RealTimePrice)).all())
            
            return {
                "status": "healthy",
                "connection": "active",
                "statistics": {
                    "grid_nodes": node_count,
                    "trading_orders": order_count,
                    "day_ahead_prices": da_price_count,
                    "real_time_prices": rt_price_count
                }
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }
