"""Time system: timestamps and clocks."""

from datetime import UTC, datetime

import pytest
from apex.core.enums import ClockSourceType
from apex.core.exceptions import ValidationError
from apex.core.time.clock import ManualClock, SystemClock
from apex.core.time.timestamp import Timestamp

T0 = Timestamp(epoch_ms=1_750_000_000_000)


class TestTimestamp:
    def test_round_trip_iso(self) -> None:
        ts = Timestamp.from_iso("2026-07-21T12:00:00+00:00")
        assert ts.to_iso() == "2026-07-21T12:00:00Z"

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Timestamp.from_datetime(datetime(2026, 1, 1))

    def test_non_utc_normalized(self) -> None:
        aware = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
        assert Timestamp.from_datetime(aware).to_datetime() == aware

    def test_arithmetic(self) -> None:
        assert T0.add_ms(1000).diff_ms(T0) == 1000

    def test_floor_alignment(self) -> None:
        ts = Timestamp(epoch_ms=1_750_000_123_456)
        assert ts.floor(60_000).epoch_ms % 60_000 == 0
        assert ts.floor(60_000) <= ts

    def test_floor_requires_positive_interval(self) -> None:
        with pytest.raises(ValidationError):
            T0.floor(0)

    def test_range_guard(self) -> None:
        with pytest.raises(ValidationError):
            Timestamp(epoch_ms=-1)
        with pytest.raises(ValidationError):
            Timestamp(epoch_ms=10**18)  # nanoseconds passed by mistake

    def test_non_int_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Timestamp(epoch_ms=1.5)  # type: ignore[arg-type]

    def test_ordering(self) -> None:
        assert T0.add_ms(1) > T0


class TestClocks:
    def test_system_clock_is_utc_and_recent(self) -> None:
        clock = SystemClock()
        assert clock.source is ClockSourceType.SYSTEM
        now = clock.now()
        assert Timestamp.from_iso("2026-01-01T00:00:00Z") < now

    def test_manual_clock_is_frozen_until_advanced(self) -> None:
        clock = ManualClock(T0)
        assert clock.now() == T0
        assert clock.now() == T0
        clock.advance_ms(500)
        assert clock.now() == T0.add_ms(500)

    def test_manual_clock_never_moves_backwards(self) -> None:
        clock = ManualClock(T0)
        with pytest.raises(ValidationError):
            clock.advance_ms(-1)
        with pytest.raises(ValidationError):
            clock.set_time(Timestamp(epoch_ms=T0.epoch_ms - 1))

    def test_manual_clock_source_label(self) -> None:
        replay = ManualClock(T0, source=ClockSourceType.REPLAY)
        assert replay.source is ClockSourceType.REPLAY
