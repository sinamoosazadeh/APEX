"""Structured logging.

Constitution 3.13: logging exists from the first line of code; every
important operation, decision and failure is logged. Book II 5.24: log
records share one structure - there is no free-form text. A record is
an event name plus typed fields, serialized as canonical JSON lines.

The logger receives its clock by injection so replayed runs produce
identical log timestamps (Constitution 3.25).
"""

import logging
import sys
from enum import Enum, unique
from typing import Final, TextIO

from apex.core.exceptions import ApexError
from apex.core.serialization import canonical_json
from apex.core.time.clock import Clock

type LogFieldValue = str | int | float | bool | None
type LogFields = dict[str, LogFieldValue]


@unique
class LogLevel(Enum):
    """Supported log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def stdlib_level(self) -> int:
        """Map onto the stdlib numeric level."""
        return _STDLIB_LEVELS[self]


_STDLIB_LEVELS: Final[dict[LogLevel, int]] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


@unique
class LogFormat(Enum):
    """Output rendering."""

    JSON = "json"
    CONSOLE = "console"


class StructuredLogger:
    """Event-structured logger bound to a component name."""

    def __init__(
        self,
        name: str,
        *,
        clock: Clock,
        log_format: LogFormat,
        stdlib_logger: logging.Logger,
    ) -> None:
        self._name = name
        self._clock = clock
        self._format = log_format
        self._stdlib = stdlib_logger

    @property
    def name(self) -> str:
        """Component name this logger is bound to."""
        return self._name

    def debug(self, event: str, **fields: LogFieldValue) -> None:
        """Log a diagnostic event."""
        self._emit(LogLevel.DEBUG, event, fields)

    def info(self, event: str, **fields: LogFieldValue) -> None:
        """Log a routine operational event."""
        self._emit(LogLevel.INFO, event, fields)

    def warning(self, event: str, **fields: LogFieldValue) -> None:
        """Log a degraded-but-operational event."""
        self._emit(LogLevel.WARNING, event, fields)

    def error(self, event: str, **fields: LogFieldValue) -> None:
        """Log a failure event."""
        self._emit(LogLevel.ERROR, event, fields)

    def critical(self, event: str, **fields: LogFieldValue) -> None:
        """Log a platform-threatening event."""
        self._emit(LogLevel.CRITICAL, event, fields)

    def failure(self, event: str, error: ApexError, **fields: LogFieldValue) -> None:
        """Log an :class:`ApexError` with its structured code and details."""
        merged: LogFields = {"error_code": error.code, "error_message": error.message}
        merged.update({f"error_{k}": v for k, v in error.details.items()})
        merged.update(fields)
        self._emit(LogLevel.ERROR, event, merged)

    def _emit(self, level: LogLevel, event: str, fields: LogFields) -> None:
        record: dict[str, LogFieldValue] = {
            "ts": self._clock.now().epoch_ms,
            "level": level.value,
            "logger": self._name,
            "event": event,
        }
        record.update(fields)
        if self._format is LogFormat.JSON:
            line = canonical_json(record)
        else:
            details = " ".join(f"{k}={v}" for k, v in fields.items())
            line = f"{self._clock.now().to_iso()} {level.value.upper():8s} {self._name} {event}"
            if details:
                line = f"{line} | {details}"
        self._stdlib.log(level.stdlib_level, line)


class LoggerFactory:
    """Builds structured loggers sharing one sink, level and clock."""

    ROOT_NAME: Final[str] = "apex"

    def __init__(
        self,
        *,
        clock: Clock,
        level: LogLevel,
        log_format: LogFormat,
        stream: TextIO | None = None,
    ) -> None:
        self._clock = clock
        self._format = log_format
        self._root = logging.getLogger(self.ROOT_NAME)
        self._root.setLevel(level.stdlib_level)
        self._root.propagate = False
        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._root.handlers.clear()
        self._root.addHandler(handler)

    def get(self, name: str) -> StructuredLogger:
        """Return a logger for a component (dotted name under ``apex``)."""
        qualified = name if name.startswith(self.ROOT_NAME) else f"{self.ROOT_NAME}.{name}"
        return StructuredLogger(
            qualified,
            clock=self._clock,
            log_format=self._format,
            stdlib_logger=self._root,
        )
