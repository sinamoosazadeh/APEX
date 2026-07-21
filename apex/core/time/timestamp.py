"""UTC timestamp value type.

Stored as integer milliseconds since the Unix epoch - the native unit
of crypto exchange APIs - so serialization is exact and comparisons are
deterministic (no floating point time arithmetic).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from apex.core.exceptions import ValidationError

_MIN_EPOCH_MS = 0
# 9999-12-31T23:59:59Z upper bound guards against second/nanosecond mixups.
_MAX_EPOCH_MS = 253_402_300_799_000

#: Largest representable instant (exclusive upper bound for open ranges).
MAX_EPOCH_MS = _MAX_EPOCH_MS


@dataclass(frozen=True, slots=True, order=True)
class Timestamp:
    """An instant in time, UTC, millisecond precision."""

    epoch_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.epoch_ms, int):
            raise ValidationError(
                "timestamp must be integer epoch milliseconds",
                code="VAL-010",
                details={"value": repr(self.epoch_ms)},
            )
        if not _MIN_EPOCH_MS <= self.epoch_ms <= _MAX_EPOCH_MS:
            raise ValidationError(
                "timestamp out of representable range",
                code="VAL-011",
                details={"epoch_ms": self.epoch_ms},
            )

    @classmethod
    def from_datetime(cls, value: datetime) -> Self:
        """Build from a timezone-aware datetime (must be UTC-convertible)."""
        if value.tzinfo is None:
            raise ValidationError(
                "naive datetime rejected; timestamps must be timezone-aware UTC",
                code="VAL-012",
            )
        return cls(epoch_ms=int(value.astimezone(UTC).timestamp() * 1000))

    @classmethod
    def from_iso(cls, value: str) -> Self:
        """Build from an ISO-8601 string with explicit offset."""
        return cls.from_datetime(datetime.fromisoformat(value))

    def to_datetime(self) -> datetime:
        """Return the equivalent timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.epoch_ms / 1000, tz=UTC)

    def to_iso(self) -> str:
        """Return the ISO-8601 UTC representation."""
        return self.to_datetime().isoformat().replace("+00:00", "Z")

    def add_ms(self, delta_ms: int) -> "Timestamp":
        """Return a new timestamp shifted by ``delta_ms`` milliseconds."""
        return Timestamp(epoch_ms=self.epoch_ms + delta_ms)

    def diff_ms(self, other: "Timestamp") -> int:
        """Return ``self - other`` in milliseconds."""
        return self.epoch_ms - other.epoch_ms

    def floor(self, interval_ms: int) -> "Timestamp":
        """Round down to an interval boundary (bar alignment)."""
        if interval_ms <= 0:
            raise ValidationError(
                "interval must be positive",
                code="VAL-013",
                details={"interval_ms": interval_ms},
            )
        return Timestamp(epoch_ms=(self.epoch_ms // interval_ms) * interval_ms)

    def __str__(self) -> str:
        return self.to_iso()
