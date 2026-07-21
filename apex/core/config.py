"""Configuration platform.

Constitution 3.7: no magic numbers in code - every tunable lives in
configuration. Book II 5.18: every config file has a schema and the
system refuses to boot when a file is missing, malformed or
schema-incompatible. Environment variables may override scalar keys
using the pattern ``APEX__<FILE>__<KEY>[__<NESTED_KEY>...]``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml

from apex.core.constants import CONFIG_SCHEMA_VERSION, ENV_PREFIX, ENV_SEPARATOR
from apex.core.enums import Environment, RunMode, Timeframe
from apex.core.exceptions import ConfigurationError, ValidationError
from apex.core.logging import LogFormat, LogLevel
from apex.core.serialization import content_hash
from apex.core.validation import ensure_symbol

type ConfigValue = str | int | float | bool | None | list["ConfigValue"] | ConfigSection
type ConfigSection = dict[str, "ConfigValue"]

# Deep-validated files (consumed by delivered phases). The remaining
# files are owned by later phases; their deep schemas ship with those
# phases, but presence, mapping shape and schema_version are enforced
# from Phase 0 so the config contract is never violated silently.
DEEP_VALIDATED_FILES: Final[tuple[str, ...]] = ("system", "logging", "market", "exchange")
PHASE_OWNED_FILES: Final[tuple[str, ...]] = (
    "signal",
    "risk",
    "optimizer",
    "portfolio",
    "research",
    "telemetry",
    "scheduler",
    "device",
)
ALL_CONFIG_FILES: Final[tuple[str, ...]] = DEEP_VALIDATED_FILES + PHASE_OWNED_FILES


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemConfig:
    """Deep-validated contents of ``system.yaml``."""

    app_name: str
    environment: Environment
    run_mode: RunMode
    deterministic_ids: bool
    id_seed: int | None
    event_journal_capacity: int
    event_fail_fast: bool
    data_dir: str
    plugin_modules: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketConfig:
    """Deep-validated contents of ``market.yaml`` (Phase 3)."""

    symbols: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    history_bars: int
    gap_penalty: float
    forming_bar_quality: float
    stream_forming_flush_ms: int
    stream_reconnect_backoff_ms: int
    stream_max_reconnects: int
    features: ConfigSection


@dataclass(frozen=True, slots=True, kw_only=True)
class ToobitConfig:
    """Deep-validated ``toobit`` section of ``exchange.yaml`` (Phase 3)."""

    base_url: str
    ws_url: str
    request_timeout_ms: int
    max_retries: int
    retry_backoff_ms: int
    kline_page_limit: int
    ws_ping_interval_ms: int
    ws_recv_timeout_ms: int


@dataclass(frozen=True, slots=True, kw_only=True)
class LoggingConfig:
    """Deep-validated contents of ``logging.yaml``."""

    level: LogLevel
    output_format: LogFormat


@dataclass(frozen=True, slots=True, kw_only=True)
class AppConfig:
    """The complete validated configuration of one platform run."""

    system: SystemConfig
    logging: LoggingConfig
    market: MarketConfig
    toobit: ToobitConfig
    sections: Mapping[str, ConfigSection]
    config_dir: str
    config_hash: str

    def section(self, name: str) -> ConfigSection:
        """Return a phase-owned raw section by file name."""
        if name not in self.sections:
            raise ConfigurationError(
                "unknown configuration section",
                code="CFG-010",
                details={"section": name},
            )
        return self.sections[name]


def load_config(
    config_dir: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load, override and validate the full configuration set.

    Raises :class:`ConfigurationError` on any violation - the platform
    must not boot with invalid configuration (Book II 5.18).
    """
    if not config_dir.is_dir():
        raise ConfigurationError(
            "configuration directory not found",
            code="CFG-001",
            details={"config_dir": str(config_dir)},
        )
    raw_sections: dict[str, ConfigSection] = {}
    for file_name in ALL_CONFIG_FILES:
        section = _read_config_file(config_dir / f"{file_name}.yaml")
        _apply_env_overrides(section, file_name, env or {})
        _check_schema_version(section, file_name)
        raw_sections[file_name] = section

    phase_sections = {name: raw_sections[name] for name in PHASE_OWNED_FILES}
    return AppConfig(
        system=_parse_system(raw_sections["system"]),
        logging=_parse_logging(raw_sections["logging"]),
        market=_parse_market(raw_sections["market"]),
        toobit=_parse_exchange(raw_sections["exchange"]),
        sections=phase_sections,
        config_dir=str(config_dir),
        config_hash=content_hash(raw_sections),
    )


def _read_config_file(path: Path) -> ConfigSection:
    if not path.is_file():
        raise ConfigurationError(
            "required configuration file is missing",
            code="CFG-002",
            details={"file": path.name},
        )
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            "configuration file is not valid YAML",
            code="CFG-003",
            details={"file": path.name, "reason": str(exc)},
        ) from exc
    if not isinstance(loaded, dict) or not all(isinstance(k, str) for k in loaded):
        raise ConfigurationError(
            "configuration file must contain a string-keyed mapping",
            code="CFG-004",
            details={"file": path.name},
        )
    return loaded


def _apply_env_overrides(
    section: ConfigSection,
    file_name: str,
    env: Mapping[str, str],
) -> None:
    prefix = f"{ENV_PREFIX}{ENV_SEPARATOR}{file_name.upper()}{ENV_SEPARATOR}"
    for env_key, raw_value in env.items():
        if not env_key.startswith(prefix):
            continue
        path_parts = [p.lower() for p in env_key[len(prefix) :].split(ENV_SEPARATOR) if p]
        if not path_parts:
            continue
        _set_override(section, path_parts, _coerce_env_value(raw_value), env_key)


def _set_override(
    section: ConfigSection,
    path_parts: list[str],
    value: ConfigValue,
    env_key: str,
) -> None:
    cursor: ConfigSection = section
    for part in path_parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            raise ConfigurationError(
                "environment override path does not match config structure",
                code="CFG-005",
                details={"variable": env_key},
            )
        cursor = nested
    cursor[path_parts[-1]] = value


def _coerce_env_value(raw: str) -> ConfigValue:
    lowered = raw.strip().lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("null", "none", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def _check_schema_version(section: ConfigSection, file_name: str) -> None:
    version = section.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ConfigurationError(
            "configuration file must declare an integer schema_version",
            code="CFG-006",
            details={"file": f"{file_name}.yaml"},
        )
    if version != CONFIG_SCHEMA_VERSION:
        raise ConfigurationError(
            "configuration schema_version is not supported",
            code="CFG-007",
            details={
                "file": f"{file_name}.yaml",
                "found": version,
                "expected": CONFIG_SCHEMA_VERSION,
            },
        )


def _require(section: ConfigSection, key: str, file_name: str) -> ConfigValue:
    if key not in section:
        raise ConfigurationError(
            "required configuration key is missing",
            code="CFG-008",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    return section[key]


def _require_str(section: ConfigSection, key: str, file_name: str) -> str:
    value = _require(section, key, file_name)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(
            "configuration key must be a non-empty string",
            code="CFG-009",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    return value


def _require_bool(section: ConfigSection, key: str, file_name: str) -> bool:
    value = _require(section, key, file_name)
    if not isinstance(value, bool):
        raise ConfigurationError(
            "configuration key must be a boolean",
            code="CFG-011",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    return value


def _require_int(
    section: ConfigSection,
    key: str,
    file_name: str,
    *,
    minimum: int,
) -> int:
    value = _require(section, key, file_name)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ConfigurationError(
            f"configuration key must be an integer >= {minimum}",
            code="CFG-012",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    return value


def _parse_enum[E](
    section: ConfigSection,
    key: str,
    file_name: str,
    parser: dict[str, E],
) -> E:
    raw = _require_str(section, key, file_name)
    if raw not in parser:
        raise ConfigurationError(
            "configuration key has an unsupported value",
            code="CFG-013",
            details={
                "file": f"{file_name}.yaml",
                "key": key,
                "value": raw,
                "allowed": ", ".join(sorted(parser)),
            },
        )
    return parser[raw]


def _require_mapping(section: ConfigSection, key: str, file_name: str) -> ConfigSection:
    value = _require(section, key, file_name)
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"{file_name}.{key} must be a mapping",
            code="CFG-014",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    return value


def _require_str_list(section: ConfigSection, key: str, file_name: str) -> tuple[str, ...]:
    value = _require(section, key, file_name)
    if not isinstance(value, list):
        raise ConfigurationError(
            "configuration key must be a list of strings",
            code="CFG-017",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigurationError(
                "configuration key must be a list of strings",
                code="CFG-017",
                details={"file": f"{file_name}.yaml", "key": key},
            )
        items.append(item)
    return tuple(items)


def _require_fraction(section: ConfigSection, key: str, file_name: str) -> float:
    value = _require(section, key, file_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            "configuration key must be a number",
            code="CFG-018",
            details={"file": f"{file_name}.yaml", "key": key},
        )
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ConfigurationError(
            "configuration key must be within [0, 1]",
            code="CFG-019",
            details={"file": f"{file_name}.yaml", "key": key, "value": number},
        )
    return number


def _parse_system(section: ConfigSection) -> SystemConfig:
    events = _require_mapping(section, "events", "system")
    storage = _require_mapping(section, "storage", "system")
    plugins = _require_mapping(section, "plugins", "system")
    id_seed_raw = section.get("id_seed")
    id_seed: int | None
    if id_seed_raw is None:
        id_seed = None
    elif isinstance(id_seed_raw, int) and not isinstance(id_seed_raw, bool):
        id_seed = id_seed_raw
    else:
        raise ConfigurationError("system.id_seed must be an integer or null", code="CFG-015")
    deterministic = _require_bool(section, "deterministic_ids", "system")
    if deterministic and id_seed is None:
        raise ConfigurationError(
            "deterministic_ids requires an explicit id_seed",
            code="CFG-016",
        )
    return SystemConfig(
        app_name=_require_str(section, "app_name", "system"),
        environment=_parse_enum(
            section, "environment", "system", {e.value: e for e in Environment}
        ),
        run_mode=_parse_enum(section, "run_mode", "system", {m.value: m for m in RunMode}),
        deterministic_ids=deterministic,
        id_seed=id_seed,
        event_journal_capacity=_require_int(events, "journal_capacity", "system", minimum=1),
        event_fail_fast=_require_bool(events, "fail_fast", "system"),
        data_dir=_require_str(storage, "data_dir", "system"),
        plugin_modules=_require_str_list(plugins, "enabled", "system"),
    )


def _parse_market(section: ConfigSection) -> MarketConfig:
    symbols = _require_str_list(section, "symbols", "market")
    for symbol in symbols:
        try:
            ensure_symbol(symbol)
        except ValidationError as error:
            raise ConfigurationError(
                "market.symbols contains a non-canonical symbol",
                code="CFG-022",
                details={"symbol": symbol},
            ) from error
    timeframe_by_value = {tf.value: tf for tf in Timeframe}
    timeframes: list[Timeframe] = []
    for raw in _require_str_list(section, "timeframes", "market"):
        if raw not in timeframe_by_value:
            raise ConfigurationError(
                "unsupported timeframe in market.timeframes",
                code="CFG-020",
                details={"value": raw, "allowed": ", ".join(sorted(timeframe_by_value))},
            )
        timeframes.append(timeframe_by_value[raw])
    quality = _require_mapping(section, "quality", "market")
    streaming = _require_mapping(section, "streaming", "market")
    return MarketConfig(
        symbols=symbols,
        timeframes=tuple(timeframes),
        history_bars=_require_int(section, "history_bars", "market", minimum=1),
        gap_penalty=_require_fraction(quality, "gap_penalty", "market"),
        forming_bar_quality=_require_fraction(quality, "forming_bar_quality", "market"),
        stream_forming_flush_ms=_require_int(
            streaming, "forming_flush_ms", "market", minimum=1
        ),
        stream_reconnect_backoff_ms=_require_int(
            streaming, "reconnect_backoff_ms", "market", minimum=0
        ),
        stream_max_reconnects=_require_int(
            streaming, "max_reconnects", "market", minimum=0
        ),
        features=_require_mapping(section, "features", "market"),
    )


def _parse_exchange(section: ConfigSection) -> ToobitConfig:
    toobit = _require_mapping(section, "toobit", "exchange")
    base_url = _require_str(toobit, "base_url", "exchange")
    if not base_url.startswith("https://"):
        raise ConfigurationError(
            "exchange.toobit.base_url must use https",
            code="CFG-021",
            details={"base_url": base_url},
        )
    ws_url = _require_str(toobit, "ws_url", "exchange")
    if not ws_url.startswith("wss://"):
        raise ConfigurationError(
            "exchange.toobit.ws_url must use wss",
            code="CFG-023",
            details={"ws_url": ws_url},
        )
    page_limit = _require_int(toobit, "kline_page_limit", "exchange", minimum=1)
    return ToobitConfig(
        base_url=base_url,
        ws_url=ws_url,
        request_timeout_ms=_require_int(toobit, "request_timeout_ms", "exchange", minimum=1),
        max_retries=_require_int(toobit, "max_retries", "exchange", minimum=0),
        retry_backoff_ms=_require_int(toobit, "retry_backoff_ms", "exchange", minimum=0),
        kline_page_limit=page_limit,
        ws_ping_interval_ms=_require_int(
            toobit, "ws_ping_interval_ms", "exchange", minimum=1
        ),
        ws_recv_timeout_ms=_require_int(
            toobit, "ws_recv_timeout_ms", "exchange", minimum=1
        ),
    )


def _parse_logging(section: ConfigSection) -> LoggingConfig:
    return LoggingConfig(
        level=_parse_enum(section, "level", "logging", {lv.value: lv for lv in LogLevel}),
        output_format=_parse_enum(
            section, "format", "logging", {f.value: f for f in LogFormat}
        ),
    )
