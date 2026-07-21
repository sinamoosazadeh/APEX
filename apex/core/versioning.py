"""Contract versioning and interface stability.

Book II 5.26: every contract carries a version and evolves with
backward compatibility. Book II 5.36: every interface declares a
stability level before it may be published.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar
from weakref import WeakKeyDictionary

from apex.core.enums import StabilityLevel
from apex.core.exceptions import ValidationError

_T = TypeVar("_T")

# Declarations live OUTSIDE the classes: a ``setattr`` on a
# ``@runtime_checkable`` Protocol would register the marker as a
# protocol member and silently break every ``isinstance`` check
# against it (each implementation would suddenly need the marker).
_STABILITY_REGISTRY: WeakKeyDictionary[type, StabilityLevel] = WeakKeyDictionary()
_CONTRACT_VERSION_REGISTRY: WeakKeyDictionary[type, int] = WeakKeyDictionary()


@dataclass(frozen=True, slots=True, order=True)
class SemanticVersion:
    """Semantic version triple."""

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for part_name in ("major", "minor", "patch"):
            part = getattr(self, part_name)
            if part < 0:
                raise ValidationError(
                    f"version {part_name} must be non-negative",
                    code="VAL-070",
                    details={part_name: part},
                )

    @classmethod
    def parse(cls, text: str) -> "SemanticVersion":
        """Parse ``major.minor.patch``."""
        parts = text.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValidationError(
                "version must be 'major.minor.patch'",
                code="VAL-071",
                details={"text": text},
            )
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def is_compatible_with(self, other: "SemanticVersion") -> bool:
        """Same-major versions are backward compatible (Book II 5.26)."""
        return self.major == other.major

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def stability(level: StabilityLevel) -> Callable[[type[_T]], type[_T]]:
    """Class decorator declaring an interface's stability level."""

    def apply(cls: type[_T]) -> type[_T]:
        _STABILITY_REGISTRY[cls] = level
        return cls

    return apply


def contract_version(version: int) -> Callable[[type[_T]], type[_T]]:
    """Class decorator declaring a contract's schema version."""

    def apply(cls: type[_T]) -> type[_T]:
        if version < 1:
            raise ValidationError(
                "contract version must be >= 1",
                code="VAL-072",
                details={"version": version},
            )
        _CONTRACT_VERSION_REGISTRY[cls] = version
        return cls

    return apply


def stability_of(cls: type) -> StabilityLevel:
    """Read a class's declared stability (default EXPERIMENTAL).

    Walks the MRO so subclasses inherit the nearest declaration,
    matching the previous attribute-lookup semantics.
    """
    for base in cls.__mro__:
        level = _STABILITY_REGISTRY.get(base)
        if level is not None:
            if not isinstance(level, StabilityLevel):
                raise ValidationError("invalid stability attribute", code="VAL-073")
            return level
    return StabilityLevel.EXPERIMENTAL
