"""UTC datetime helpers for Python 3.12+ compatibility."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return naive UTC datetime without Python 3.12 deprecation warning."""
    return datetime.now(UTC).replace(tzinfo=None)
