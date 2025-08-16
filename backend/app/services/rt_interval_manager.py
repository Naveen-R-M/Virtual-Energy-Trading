"""
Real-Time Market Interval Management Service
Handles 5-minute interval timing, cutoffs, and settlement logic
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict
import pytz
import logging

logger = logging.getLogger(__name__)

class RTIntervalManager:
    """
    Manages Real-Time market 5-minute intervals
    PJM operates on 5-minute intervals: 00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55
    """
    
    @staticmethod
    def get_current_interval(timestamp: datetime = None) -> Tuple[datetime, datetime]:
        """
        Get the current 5-minute interval
        
        Returns:
            Tuple of (interval_start, interval_end)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Round down to nearest 5-minute interval
        minutes = timestamp.minute
        interval_minutes = (minutes // 5) * 5
        
        interval_start = timestamp.replace(
            minute=interval_minutes,
            second=0,
            microsecond=0
        )
        interval_end = interval_start + timedelta(minutes=5)
        
        return interval_start, interval_end
    
    @staticmethod
    def get_next_interval(timestamp: datetime = None) -> Tuple[datetime, datetime]:
        """
        Get the next 5-minute interval
        
        Returns:
            Tuple of (interval_start, interval_end)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        current_start, current_end = RTIntervalManager.get_current_interval(timestamp)
        next_start = current_end
        next_end = next_start + timedelta(minutes=5)
        
        return next_start, next_end
    
    @staticmethod
    def get_interval_for_order(order_time: datetime) -> Tuple[datetime, datetime, str]:
        """
        Determine which interval an RT order should be assigned to
        
        Rules:
        - If order is placed before interval ends, it's for current interval
        - If order is placed after interval ends, it's for next interval
        
        Args:
            order_time: Time when order is placed
            
        Returns:
            Tuple of (interval_start, interval_end, status)
            status can be: 'current', 'next', or 'future'
        """
        current_start, current_end = RTIntervalManager.get_current_interval(order_time)
        
        # If we're still in the current interval
        if order_time < current_end:
            return current_start, current_end, 'current'
        
        # Otherwise, assign to next interval
        next_start, next_end = RTIntervalManager.get_next_interval(order_time)
        return next_start, next_end, 'next'
    
    @staticmethod
    def can_place_order_for_interval(
        order_time: datetime,
        target_interval_start: datetime,
        debug: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if an order can be placed for a specific interval
        
        Args:
            order_time: When the order is being placed (UTC)
            target_interval_start: The interval the user wants to trade in (UTC)
            
        Returns:
            Tuple of (can_place, reason)
        """
        # Ensure both are timezone-naive for comparison
        if order_time.tzinfo is not None:
            order_time = order_time.replace(tzinfo=None)
        if target_interval_start.tzinfo is not None:
            target_interval_start = target_interval_start.replace(tzinfo=None)
        
        # Calculate the interval end
        interval_end = target_interval_start + timedelta(minutes=5)
        
        if debug:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Interval check: order_time={order_time}, target_start={target_interval_start}, target_end={interval_end}")
        
        # Can place orders if:
        # 1. The interval hasn't ended yet (current time < interval end)
        # 2. The interval is within 24 hours from now
        
        if interval_end <= order_time:
            # Interval has completely passed - show in Eastern time for clarity
            interval_display = RTIntervalManager.format_interval_display(target_interval_start)
            return False, f"Cannot place orders for past intervals. Interval {interval_display} has already ended."
        
        # Can't place orders too far in the future (max 24 hours ahead)
        max_future = order_time + timedelta(hours=24)
        if target_interval_start > max_future:
            return False, f"Cannot place orders more than 24 hours in advance."
        
        return True, "Order can be placed for this interval"
    
    @staticmethod
    def get_settlement_status(
        interval_start: datetime,
        current_time: datetime = None
    ) -> Dict[str, any]:
        """
        Get the settlement status for an interval
        
        Returns dict with:
        - can_settle: bool - whether the interval can be settled now
        - is_complete: bool - whether the interval has ended
        - expected_settlement_time: datetime - when settlement data should be available
        - message: str - human-readable status
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Ensure both are timezone-naive for comparison
        if interval_start.tzinfo is not None:
            interval_start = interval_start.replace(tzinfo=None)
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        
        interval_end = interval_start + timedelta(minutes=5)
        
        # PJM typically publishes RT prices with a 5-10 minute delay
        expected_settlement = interval_end + timedelta(minutes=5, seconds=30)
        
        result = {
            'interval_start': interval_start,
            'interval_end': interval_end,
            'expected_settlement_time': expected_settlement,
            'current_time': current_time
        }
        
        if current_time < interval_end:
            # Interval hasn't ended yet
            result.update({
                'can_settle': False,
                'is_complete': False,
                'message': f"Interval {interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')} is still active. Settlement after {interval_end.strftime('%H:%M:%S')}."
            })
        elif current_time < expected_settlement:
            # Interval ended but settlement data may not be available
            result.update({
                'can_settle': False,  # Could try, but data might not be ready
                'is_complete': True,
                'message': f"Interval complete. Settlement data expected around {expected_settlement.strftime('%H:%M:%S')}."
            })
        else:
            # Settlement should be available
            result.update({
                'can_settle': True,
                'is_complete': True,
                'message': f"Settlement data should be available for {interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')} interval."
            })
        
        return result
    
    @staticmethod
    def format_interval_display(
        interval_start: datetime,
        timezone: str = 'US/Eastern'
    ) -> str:
        """
        Format interval for display to user
        
        Args:
            interval_start: Start of the interval (UTC)
            timezone: Timezone for display (default: US/Eastern for PJM)
            
        Returns:
            Formatted string like "14:35-14:40 EST"
        """
        interval_end = interval_start + timedelta(minutes=5)
        
        # Convert to local timezone
        tz = pytz.timezone(timezone)
        
        # Handle both naive and aware datetimes
        if interval_start.tzinfo is None:
            local_start = pytz.utc.localize(interval_start).astimezone(tz)
            local_end = pytz.utc.localize(interval_end).astimezone(tz)
        else:
            local_start = interval_start.astimezone(tz)
            local_end = interval_end.astimezone(tz)
        
        return f"{local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')} {local_start.strftime('%Z')}"
    
    @staticmethod
    def get_intervals_for_hour(hour_start: datetime) -> list:
        """
        Get all 12 five-minute intervals within an hour
        
        Args:
            hour_start: Start of the hour
            
        Returns:
            List of (interval_start, interval_end) tuples
        """
        intervals = []
        current = hour_start.replace(minute=0, second=0, microsecond=0)
        
        for i in range(12):  # 12 five-minute intervals per hour
            interval_end = current + timedelta(minutes=5)
            intervals.append((current, interval_end))
            current = interval_end
        
        return intervals
    
    @staticmethod
    def validate_interval_alignment(timestamp: datetime) -> Tuple[bool, datetime]:
        """
        Check if a timestamp is aligned to a 5-minute interval boundary
        
        Args:
            timestamp: Time to check
            
        Returns:
            Tuple of (is_aligned, aligned_timestamp)
        """
        minutes = timestamp.minute
        if minutes % 5 != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
            # Not aligned, compute the aligned version
            aligned_minutes = (minutes // 5) * 5
            aligned = timestamp.replace(
                minute=aligned_minutes,
                second=0,
                microsecond=0
            )
            return False, aligned
        
        return True, timestamp

# Singleton instance
_interval_manager = RTIntervalManager()

def get_interval_manager() -> RTIntervalManager:
    """Get the RT interval manager instance"""
    return _interval_manager
