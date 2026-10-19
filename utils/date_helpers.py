from datetime import datetime, timezone
from typing import Optional

def format_relative_time(dt: Optional[datetime]) -> str:
    """
    Formats a datetime into a human-readable relative time string:
    - 'Just now' (< 60s)
    - 'X min ago' / 'X mins ago' (< 60m)
    - 'X hour ago' / 'X hours ago' (< 24h)
    - '1 day ago', '2 days ago', etc. (< 7d)
    - '1 week ago', '2 weeks ago', etc. (< 30d)
    - '1 month ago', '2 months ago', etc. (< 365d)
    - '1 year ago', '2 years ago', etc. (>= 365d)
    """
    if not dt:
        return "Recently"

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    total_seconds = diff.total_seconds()

    if total_seconds < 0 or total_seconds < 60:
        return "Just now"

    minutes = int(total_seconds // 60)
    if minutes < 60:
        return f"{minutes} min ago" if minutes == 1 else f"{minutes} mins ago"

    hours = int(total_seconds // 3600)
    if hours < 24:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"

    days = diff.days
    if days < 7:
        return f"{days} day ago" if days == 1 else f"{days} days ago"

    weeks = int(days // 7)
    if days < 30:
        return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"

    months = int(days // 30)
    if days < 365:
        return f"{months} month ago" if months == 1 else f"{months} months ago"

    years = int(days // 365)
    return f"{years} year ago" if years == 1 else f"{years} years ago"
