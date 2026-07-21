"""Result object.

Book II 4.30: no function communicates success with a bare boolean.
Operations return a :class:`Result` carrying data, error, warnings,
metadata and execution time, so every outcome is loggable and
explainable.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from apex.core.exceptions import ApexError, ValidationError


@dataclass(frozen=True, slots=True)
class Result[T]:
    """Outcome of an operation.

    Exactly one of ``data`` (on success) or ``error`` (on failure) is
    meaningful; construction enforces the invariant.
    """

    ok: bool
    data: T | None = None
    error: ApexError | None = None
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
    duration_ms: float | None = None

    def __post_init__(self) -> None:
        if self.ok and self.error is not None:
            raise ValidationError("successful result cannot carry an error", code="VAL-040")
        if not self.ok and self.error is None:
            raise ValidationError("failed result must carry an error", code="VAL-041")

    @classmethod
    def success(
        cls,
        data: T,
        *,
        warnings: tuple[str, ...] = (),
        metadata: Mapping[str, str | int | float | bool | None] | None = None,
        duration_ms: float | None = None,
    ) -> "Result[T]":
        """Build a successful result."""
        return cls(
            ok=True,
            data=data,
            warnings=warnings,
            metadata=dict(metadata or {}),
            duration_ms=duration_ms,
        )

    @classmethod
    def failure(
        cls,
        error: ApexError,
        *,
        warnings: tuple[str, ...] = (),
        metadata: Mapping[str, str | int | float | bool | None] | None = None,
        duration_ms: float | None = None,
    ) -> "Result[T]":
        """Build a failed result."""
        return cls(
            ok=False,
            error=error,
            warnings=warnings,
            metadata=dict(metadata or {}),
            duration_ms=duration_ms,
        )

    def unwrap(self) -> T:
        """Return the data or raise the carried error."""
        if not self.ok:
            assert self.error is not None
            raise self.error
        assert self.data is not None or self.ok
        return self.data  # type: ignore[return-value]

    def to_dict(self) -> dict[str, object]:
        """Serialize the outcome envelope (not the payload semantics)."""
        return {
            "ok": self.ok,
            "error": self.error.to_dict() if self.error else None,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
            "duration_ms": self.duration_ms,
        }
