# src/time_utils.py
from datetime import datetime, timezone

def utc_now():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    """Return ISO-8601 formatted UTC time string."""
    return utc_now().isoformat()
