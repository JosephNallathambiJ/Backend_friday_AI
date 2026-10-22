"""Application lifecycle and runtime uptime tracker."""

import time

_SERVER_START_TIME: float = time.time()


def set_server_start_time(timestamp: float | None = None) -> None:
    """Set or reset server boot timestamp."""
    global _SERVER_START_TIME
    _SERVER_START_TIME = timestamp if timestamp is not None else time.time()


def get_uptime_seconds() -> float:
    """Return seconds since server initialized."""
    return round(time.time() - _SERVER_START_TIME, 2)
