"""Centralized datetime utilities for timezone-aware operations.

This module provides a single source of truth for datetime handling,
replacing deprecated datetime.utcnow() with timezone-aware alternatives.

Usage:
    from backend.puzzle_manager.core.datetime_utils import utc_now

    # Instead of: datetime.utcnow()
    timestamp = utc_now()
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    Returns:
        datetime: Current time in UTC with timezone info attached.

    Example:
        >>> ts = utc_now()
        >>> ts.tzinfo == timezone.utc
        True
    """
    return datetime.now(UTC)
