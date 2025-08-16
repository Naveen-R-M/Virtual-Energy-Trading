"""
Debug endpoint for RT interval timezone issues
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
import pytz

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/time-conversion")
async def debug_time_conversion(
    edt_time: str = Query(..., description="Time in EDT format (HH:MM)", example="01:05")
):
    """
    Debug endpoint to show correct time conversion from EDT to UTC
    
    Example: If user selects "01:05 AM EDT", what should be sent to API?
    """
    try:
        # Parse the EDT time (assuming today's date)
        today = datetime.utcnow().date()
        hour, minute = map(int, edt_time.split(':'))
        
        # Create EDT datetime
        et = pytz.timezone('US/Eastern')
        edt_datetime = et.localize(datetime(today.year, today.month, today.day, hour, minute))
        
        # Convert to UTC
        utc_datetime = edt_datetime.astimezone(pytz.UTC)
        
        # Get 5-minute interval
        interval_minutes = (minute // 5) * 5
        interval_start_edt = edt_datetime.replace(minute=interval_minutes, second=0, microsecond=0)
        interval_end_edt = interval_start_edt + timedelta(minutes=5)
        
        interval_start_utc = interval_start_edt.astimezone(pytz.UTC)
        interval_end_utc = interval_end_edt.astimezone(pytz.UTC)
        
        return {
            "user_selected": f"{edt_time} EDT",
            "conversion": {
                "edt_time": edt_datetime.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "utc_time": utc_datetime.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "api_format": utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "interval": {
                "display": f"{interval_start_edt.strftime('%H:%M')}-{interval_end_edt.strftime('%H:%M')} EDT",
                "start_edt": interval_start_edt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "start_utc": interval_start_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "start_api": interval_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_api": interval_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "instructions": {
                "correct": f"Send time_slot as: {interval_start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                "wrong": f"DON'T send as: {interval_start_edt.strftime('%Y-%m-%dT%H:%M:%SZ')} (this would be wrong!)"
            },
            "current_time": {
                "utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "edt": datetime.now(et).strftime("%Y-%m-%d %H:%M:%S %Z")
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.get("/validate-timestamp")
async def validate_timestamp(
    timestamp: str = Query(..., description="Timestamp to validate", example="2025-08-16T01:05:00Z")
):
    """
    Validate what a timestamp means in different timezones
    """
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Convert to EDT
        et = pytz.timezone('US/Eastern')
        # Handle both naive and aware datetimes
        if dt.tzinfo is None:
            edt_time = pytz.UTC.localize(dt).astimezone(et)
        else:
            edt_time = dt.astimezone(et)
        
        # Make dt naive for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        # Check if it's in the past
        now_utc = datetime.utcnow()
        is_past = dt < now_utc
        
        # Get the interval
        interval_end = dt + timedelta(minutes=5)
        interval_past = interval_end <= now_utc
        
        return {
            "input": timestamp,
            "interpretation": {
                "as_utc": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "as_edt": edt_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "interval": f"{dt.strftime('%H:%M')}-{interval_end.strftime('%H:%M')} UTC",
                "interval_edt": f"{edt_time.strftime('%H:%M')}-{(edt_time + timedelta(minutes=5)).strftime('%H:%M')} EDT"
            },
            "status": {
                "current_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "is_timestamp_past": is_past,
                "is_interval_past": interval_past,
                "can_place_order": not interval_past
            },
            "advice": "This timestamp represents " + edt_time.strftime("%I:%M %p EDT") + 
                     (" - CANNOT place order (interval passed)" if interval_past else " - CAN place order")
        }
        
    except Exception as e:
        return {"error": str(e)}
