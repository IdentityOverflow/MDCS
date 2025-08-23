"""
Time and date plugin functions for advanced modules.

Provides various time-related functions that can be used in advanced module scripts.
"""

from datetime import datetime, timedelta
from app.core.script_plugins import plugin_registry


@plugin_registry.register("get_current_time")
def get_current_time(format: str = "%Y-%m-%d %H:%M") -> str:
    """
    Get current time in specified format.
    
    Args:
        format: strftime format string (default: "%Y-%m-%d %H:%M")
        
    Returns:
        Current time as formatted string
        
    Example:
        get_current_time() -> "2025-08-23 14:30"
        get_current_time("%H:%M") -> "14:30"
    """
    return datetime.now().strftime(format)


@plugin_registry.register("get_relative_time")
def get_relative_time(minutes_offset: int = 0, format: str = "%H:%M") -> str:
    """
    Get time relative to now with specified offset.
    
    Args:
        minutes_offset: Minutes to add/subtract from current time
        format: strftime format string (default: "%H:%M")
        
    Returns:
        Relative time as formatted string
        
    Example:
        get_relative_time(30) -> "15:00" (30 minutes from now)
        get_relative_time(-60) -> "13:30" (1 hour ago)
    """
    target_time = datetime.now() + timedelta(minutes=minutes_offset)
    return target_time.strftime(format)


@plugin_registry.register("is_business_hours")
def is_business_hours(start_hour: int = 9, end_hour: int = 17) -> bool:
    """
    Check if current time is during business hours.
    
    Args:
        start_hour: Business day start hour (default: 9)
        end_hour: Business day end hour (default: 17)
        
    Returns:
        True if current time is during business hours
        
    Example:
        is_business_hours() -> True (if between 9:00-17:00)
        is_business_hours(8, 20) -> True (if between 8:00-20:00)
    """
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour


@plugin_registry.register("get_day_of_week")
def get_day_of_week(full_name: bool = True) -> str:
    """
    Get the current day of the week.
    
    Args:
        full_name: If True, return full name (e.g., "Monday"), 
                  if False, return abbreviated (e.g., "Mon")
        
    Returns:
        Day of the week as string
        
    Example:
        get_day_of_week() -> "Monday"
        get_day_of_week(False) -> "Mon"
    """
    now = datetime.now()
    if full_name:
        return now.strftime("%A")
    else:
        return now.strftime("%a")


@plugin_registry.register("format_timestamp")
def format_timestamp(timestamp: float, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a Unix timestamp to human-readable string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        format: strftime format string
        
    Returns:
        Formatted timestamp string
        
    Example:
        format_timestamp(1692794400) -> "2023-08-23 12:00:00"
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(format)