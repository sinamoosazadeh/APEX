"""Security platform configuration (``security.yaml``, Phase 13).

Deep-validates the security section set: vault and audit filenames
under the storage data directory, the live-mode sealing requirement
(13.10/13.11) and the preflight clock-skew tolerance (13.23). The
``policy`` section is parsed by :class:`apex.security.access.AccessPolicy`.
"""

from dataclasses import dataclass

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError

_CODE = "CFG-043"


@dataclass(frozen=True, slots=True, kw_only=True)
class SecuritySettings:
    """The validated security platform configuration."""

    vault_filename: str = "vault.enc"
    audit_filename: str = "audit.sqlite"
    require_sealed_config_live: bool = True
    clock_skew_tolerance_ms: int = 120_000

    def __post_init__(self) -> None:
        if not self.vault_filename:
            raise ConfigurationError(
                "security.vault.filename must be non-empty", code=_CODE, details={}
            )
        if not self.audit_filename:
            raise ConfigurationError(
                "security.audit.filename must be non-empty", code=_CODE, details={}
            )
        if self.clock_skew_tolerance_ms < 1_000:
            raise ConfigurationError(
                "security.preflight.clock_skew_tolerance_ms must be >= 1000",
                code=_CODE,
                details={},
            )


def _mapping(section: ConfigSection, key: str) -> ConfigSection:
    value = section.get(key, {})
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"security.{key} must be a mapping",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _string(section: ConfigSection, key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(
            f"security value {key} must be a string",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _boolean(section: ConfigSection, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"security value {key} must be a boolean",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"security value {key} must be an integer",
            code=_CODE,
            details={"found": repr(value)},
        )
    return value


def security_settings(section: ConfigSection) -> SecuritySettings:
    """Parse and validate the security sections of security.yaml."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "security configuration must be a mapping", code=_CODE, details={}
        )
    defaults = SecuritySettings()
    vault = _mapping(section, "vault")
    audit = _mapping(section, "audit")
    preflight = _mapping(section, "preflight")
    return SecuritySettings(
        vault_filename=_string(vault, "filename", defaults.vault_filename),
        audit_filename=_string(audit, "filename", defaults.audit_filename),
        require_sealed_config_live=_boolean(
            preflight,
            "require_sealed_config_live",
            defaults.require_sealed_config_live,
        ),
        clock_skew_tolerance_ms=_integer(
            preflight,
            "clock_skew_tolerance_ms",
            defaults.clock_skew_tolerance_ms,
        ),
    )
