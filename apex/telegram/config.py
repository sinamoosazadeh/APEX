"""Telegram console configuration (``telegram.yaml``, Phase 12).

Deep-validates the console's operating parameters: long-poll cadence,
the 10-minute session timeout (Book IV Part 5's authoritative value),
pagination, the double-confirmation TTL for dangerous actions, and
the notification policy (which severities push proactively).
"""

from dataclasses import dataclass

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError
from apex.monitoring.records import AlertSeverity

_CODE = "CFG-041"


@dataclass(frozen=True, slots=True, kw_only=True)
class TelegramSettings:
    """The validated Telegram console configuration."""

    enabled: bool = True
    poll_timeout_s: int = 25
    session_timeout_ms: int = 600_000
    page_size: int = 5
    confirm_ttl_ms: int = 60_000
    notify_min_severity: AlertSeverity = AlertSeverity.HIGH
    notify_fills: bool = True
    notify_signals: bool = True
    notify_promotions: bool = True

    def __post_init__(self) -> None:
        _require(1 <= self.poll_timeout_s <= 50, "poll_timeout_s must be in [1, 50]")
        _require(
            self.session_timeout_ms >= 60_000, "session_timeout_ms must be >= 60000"
        )
        _require(1 <= self.page_size <= 20, "page_size must be in [1, 20]")
        _require(self.confirm_ttl_ms >= 5_000, "confirm_ttl_ms must be >= 5000")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message, code=_CODE, details={})


def _boolean(section: ConfigSection, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"telegram value {key} must be a boolean",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"telegram value {key} must be an integer",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _severity(section: ConfigSection, key: str, default: AlertSeverity) -> AlertSeverity:
    value = section.get(key, default.value)
    values = {severity.value: severity for severity in AlertSeverity}
    if not isinstance(value, str) or value not in values:
        raise ConfigurationError(
            f"telegram value {key} must be one of {sorted(values)}",
            code=_CODE,
            details={"found": repr(value)},
        )
    return values[value]


def telegram_settings(section: ConfigSection) -> TelegramSettings:
    """Parse and validate telegram.yaml's ``console`` section."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "telegram configuration must be a mapping", code=_CODE, details={}
        )
    console = section.get("console", {})
    if not isinstance(console, dict):
        raise ConfigurationError(
            "telegram.console must be a mapping", code=_CODE, details={}
        )
    defaults = TelegramSettings()
    return TelegramSettings(
        enabled=_boolean(console, "enabled", defaults.enabled),
        poll_timeout_s=_integer(console, "poll_timeout_s", defaults.poll_timeout_s),
        session_timeout_ms=_integer(
            console, "session_timeout_ms", defaults.session_timeout_ms
        ),
        page_size=_integer(console, "page_size", defaults.page_size),
        confirm_ttl_ms=_integer(console, "confirm_ttl_ms", defaults.confirm_ttl_ms),
        notify_min_severity=_severity(
            console, "notify_min_severity", defaults.notify_min_severity
        ),
        notify_fills=_boolean(console, "notify_fills", defaults.notify_fills),
        notify_signals=_boolean(console, "notify_signals", defaults.notify_signals),
        notify_promotions=_boolean(
            console, "notify_promotions", defaults.notify_promotions
        ),
    )
