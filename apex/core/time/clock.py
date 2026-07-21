"""Clock service.

The only module in APEX allowed to read the operating system clock.
Everything else receives a :class:`Clock` by injection, which makes
replay, simulation and time-dependent tests deterministic
(Constitution 3.25).
"""

import time
from typing import Protocol, runtime_checkable

from apex.core.enums import ClockSourceType
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp


@runtime_checkable
class Clock(Protocol):
    """Time source contract."""

    @property
    def source(self) -> ClockSourceType:
        """Where this clock's readings originate."""
        ...

    def now(self) -> Timestamp:
        """Current instant according to this clock."""
        ...


class SystemClock:
    """Wall clock backed by the operating system (UTC).

    This is the single sanctioned call site of OS time in APEX.
    """

    @property
    def source(self) -> ClockSourceType:
        return ClockSourceType.SYSTEM

    def now(self) -> Timestamp:
        return Timestamp(epoch_ms=time.time_ns() // 1_000_000)


class ManualClock:
    """Deterministic clock for tests, replay and simulation.

    Time only moves when explicitly set or advanced, and never moves
    backwards - replayed event order must stay monotonic.
    """

    def __init__(
        self,
        start: Timestamp,
        *,
        source: ClockSourceType = ClockSourceType.MANUAL,
    ) -> None:
        self._current = start
        self._source = source

    @property
    def source(self) -> ClockSourceType:
        return self._source

    def now(self) -> Timestamp:
        return self._current

    def advance_ms(self, delta_ms: int) -> Timestamp:
        """Move the clock forward by ``delta_ms`` and return the new time."""
        if delta_ms < 0:
            raise ValidationError(
                "clock cannot move backwards",
                code="VAL-020",
                details={"delta_ms": delta_ms},
            )
        self._current = self._current.add_ms(delta_ms)
        return self._current

    def set_time(self, value: Timestamp) -> None:
        """Jump to ``value``; must not be earlier than the current time."""
        if value < self._current:
            raise ValidationError(
                "clock cannot move backwards",
                code="VAL-020",
                details={"current": str(self._current), "requested": str(value)},
            )
        self._current = value
