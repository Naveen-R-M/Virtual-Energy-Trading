"""
Enhanced Order Routes with Real-Time Auto-Execution
"""

from fastapi import BackgroundTasks
from ..services.matching_engine import MatchingEngine
import logging

logger = logging.getLogger(__name__)

async def auto_execute_rt_order(order_id: int, session):
    """
    Background task to automatically execute RT orders
    """
    try:
        logger.info(f"Auto-executing RT order {order_id}")
        matching_engine = MatchingEngine(session)
        result = await matching_engine.execute_real_time_order(order_id)
        logger.info(f"RT order {order_id} execution result: {result.status}")
    except Exception as e:
        logger.error(f"Failed to auto-execute RT order {order_id}: {e}")
