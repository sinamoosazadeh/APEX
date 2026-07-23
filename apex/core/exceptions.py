"""APEX exception hierarchy.

Book II 4.25: no module raises bare ``Exception``. Every failure is an
``ApexError`` subclass carrying a structured error code (4.26, pattern
``ABC-123``), a message and machine-readable details, so failures are
loggable, serializable and auditable (Book II 5.25 exception contract).
"""

from collections.abc import Mapping
from typing import ClassVar, Final

from apex.core.constants import ERROR_CODE_PATTERN

type ErrorDetails = Mapping[str, str | int | float | bool | None]


class ApexError(Exception):
    """Root of the APEX exception hierarchy.

    Args:
        code: structured error code matching ``ABC-123``.
        message: human-readable, single-line description.
        details: machine-readable context for logging and audit.
    """

    DEFAULT_CODE: ClassVar[str] = "GEN-000"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: ErrorDetails | None = None,
    ) -> None:
        resolved = code if code is not None else type(self).DEFAULT_CODE
        if not ERROR_CODE_PATTERN.match(resolved):
            raise ValueError(f"invalid error code format: {resolved!r}")
        super().__init__(message)
        self.code: Final[str] = resolved
        self.message: Final[str] = message
        self.details: Final[dict[str, str | int | float | bool | None]] = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        """Serialize per the exception contract (Book II 5.25)."""
        return {
            "error": type(self).__name__,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ConfigurationError(ApexError):
    """Invalid, missing or schema-incompatible configuration."""

    DEFAULT_CODE = "CFG-000"


class ValidationError(ApexError):
    """An object or value failed self-validation (Book II 4.18)."""

    DEFAULT_CODE = "VAL-000"


class SerializationError(ApexError):
    """An object could not be serialized or deserialized."""

    DEFAULT_CODE = "SER-000"


class DataError(ApexError):
    """Market data acquisition, quality or integrity failure."""

    DEFAULT_CODE = "DAT-000"


class FeatureError(ApexError):
    """Feature computation or feature contract violation."""

    DEFAULT_CODE = "FEA-000"


class MarketError(ApexError):
    """Market gateway or exchange interaction failure."""

    DEFAULT_CODE = "MKT-000"


class SignalError(ApexError):
    """Signal construction or signal contract violation."""

    DEFAULT_CODE = "SIG-000"


class RiskError(ApexError):
    """Risk engine violation or risk limit breach."""

    DEFAULT_CODE = "RSK-000"


class ExecutionError(ApexError):
    """Order execution failure."""

    DEFAULT_CODE = "EXE-000"


class StorageError(ApexError):
    """Persistence layer failure."""

    DEFAULT_CODE = "STO-000"


class OptimizerError(ApexError):
    """Optimization run failure."""

    DEFAULT_CODE = "OPT-000"


class ResearchError(ApexError):
    """Research or experiment framework failure."""

    DEFAULT_CODE = "RES-000"


class EventError(ApexError):
    """Event contract violation or event bus failure."""

    DEFAULT_CODE = "EVT-000"


class KernelError(ApexError):
    """Kernel boot, dependency injection or lifecycle failure."""

    DEFAULT_CODE = "KRN-000"


class SecurityError(ApexError):
    """Security policy violation."""

    DEFAULT_CODE = "SEC-000"


class MonitoringError(ApexError):
    """Monitoring platform or operational-loop failure."""

    DEFAULT_CODE = "MON-000"


class TelegramError(ApexError):
    """Telegram console transport or command failure."""

    DEFAULT_CODE = "TGM-000"


class DeploymentError(ApexError):
    """Packaging, backup/restore or scheduling failure."""

    DEFAULT_CODE = "DEP-000"
