"""Time utilities for RTC/IPTS helpers and timebases."""

from datetime import datetime, timezone, timedelta
from typing import Union


def datetime_to_rtc(dt: datetime, base_time: datetime = None) -> int:
    """
    Convert datetime to RTC format.
    
    Args:
        dt: DateTime to convert
        base_time: If provided, returns microseconds since base_time.
                  Otherwise returns microseconds since Unix epoch.
    
    Returns:
        RTC value in microseconds
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if base_time is not None:
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
        delta = dt - base_time
        return int(delta.total_seconds() * 1_000_000)
    else:
        timestamp = dt.timestamp()
        return int(timestamp * 1_000_000)


def rtc_to_datetime(rtc: int) -> datetime:
    """Convert RTC format to datetime."""
    timestamp = rtc / 1_000_000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_ipts(dt: datetime, base_time: datetime) -> int:
    """Convert datetime to IPTS (nanoseconds since base time)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    delta = dt - base_time
    return int(delta.total_seconds() * 1_000_000_000)


def ipts_to_datetime(ipts: int, base_time: datetime) -> datetime:
    """Convert IPTS to datetime."""
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    delta_seconds = ipts / 1_000_000_000
    return base_time + timedelta(seconds=delta_seconds)


def parse_timestamp(timestamp: Union[str, datetime]) -> datetime:
    """Parse a timestamp string or return datetime object."""
    if isinstance(timestamp, datetime):
        return timestamp
    
    # Try ISO format first
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        pass
    
    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            continue
    
    raise ValueError(f"Could not parse timestamp: {timestamp}")
