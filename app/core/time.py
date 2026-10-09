from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import get_settings


@lru_cache
def business_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().business_timezone)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def business_now() -> datetime:
    """Return the current timestamp in the configured business timezone."""
    return datetime.now(business_timezone())


def ensure_utc(value: datetime) -> datetime:
    """Normalize stored timestamps to UTC.

    SQLite may return timezone-aware values as naive datetimes. BeautyFlow stores
    appointment timestamps in UTC, so legacy naive database values are treated
    as UTC here.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def local_datetime_to_utc(value: datetime) -> datetime:
    """Interpret naive API timestamps as local business time and convert to UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=business_timezone())
    return value.astimezone(timezone.utc)


def utc_to_business(value: datetime) -> datetime:
    """Convert a stored UTC timestamp to the configured business timezone."""
    return ensure_utc(value).astimezone(business_timezone())
