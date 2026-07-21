"""APEX time system.

Book II 4.14: direct use of ``datetime.now()`` is forbidden everywhere
outside this package. All time is read from an injected clock so the
platform can replay, simulate and test deterministically. All
timestamps are UTC (Book II 4.16).
"""

from apex.core.time.clock import Clock, ManualClock, SystemClock
from apex.core.time.timestamp import Timestamp

__all__ = ["Clock", "ManualClock", "SystemClock", "Timestamp"]
