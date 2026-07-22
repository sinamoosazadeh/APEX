"""Execution platform configuration (``exchange.yaml``, Phase 10).

Deep-validates the ``execution`` section: venue trading parameters
(signature receive window, fee rates), the paper fill model (slippage
in basis points), order lifecycle policy (poll cadence, timeout,
bounded retries) and entry construction defaults. Everything-is-config
(Constitution 3.7): the engines hardcode no rate, cadence or offset.
"""

from dataclasses import dataclass

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError

_CODE = "CFG-036"

ENTRY_TYPE_MARKET = "market"
ENTRY_TYPE_LIMIT = "limit"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSettings:
    """The validated execution platform configuration."""

    recv_window_ms: int = 5_000
    taker_fee_rate: float = 0.0006
    maker_fee_rate: float = 0.0002
    paper_slippage_bps: float = 2.0
    poll_interval_ms: int = 1_000
    order_timeout_ms: int = 30_000
    max_retries: int = 2
    entry_order_type: str = ENTRY_TYPE_MARKET
    limit_offset_bps: float = 5.0
    paper_patience_bars: int = 3
    contract_infix: str = "-SWAP-"

    def __post_init__(self) -> None:
        _require(self.recv_window_ms >= 1_000, "recv_window_ms must be >= 1000")
        _require(0 <= self.taker_fee_rate < 0.01, "taker_fee_rate must be in [0, 0.01)")
        _require(0 <= self.maker_fee_rate < 0.01, "maker_fee_rate must be in [0, 0.01)")
        _require(
            0 <= self.paper_slippage_bps <= 100,
            "paper_slippage_bps must be in [0, 100]",
        )
        _require(self.poll_interval_ms >= 100, "poll_interval_ms must be >= 100")
        _require(
            self.order_timeout_ms >= self.poll_interval_ms,
            "order_timeout_ms must cover at least one poll",
        )
        _require(0 <= self.max_retries <= 5, "max_retries must be in [0, 5]")
        _require(
            self.entry_order_type in (ENTRY_TYPE_MARKET, ENTRY_TYPE_LIMIT),
            "entry_order_type must be market or limit",
        )
        _require(
            0 <= self.limit_offset_bps <= 100, "limit_offset_bps must be in [0, 100]"
        )
        _require(
            1 <= self.paper_patience_bars <= 48,
            "paper_patience_bars must be in [1, 48]",
        )
        _require(bool(self.contract_infix), "contract_infix must not be empty")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message, code=_CODE, details={})


def _number(section: ConfigSection, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"execution value {key} must be a number",
            code="CFG-037",
            details={"found": repr(value)},
        )
    return float(value)


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"execution value {key} must be an integer",
            code="CFG-037",
            details={"found": repr(value)},
        )
    return value


def _text(section: ConfigSection, key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(
            f"execution value {key} must be a non-empty string",
            code="CFG-037",
            details={"found": repr(value)},
        )
    return value


def execution_settings(section: ConfigSection) -> ExecutionSettings:
    """Parse and validate the ``execution`` section of exchange.yaml."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "exchange.execution must be a mapping", code="CFG-038", details={}
        )
    defaults = ExecutionSettings()
    return ExecutionSettings(
        recv_window_ms=_integer(section, "recv_window_ms", defaults.recv_window_ms),
        taker_fee_rate=_number(section, "taker_fee_rate", defaults.taker_fee_rate),
        maker_fee_rate=_number(section, "maker_fee_rate", defaults.maker_fee_rate),
        paper_slippage_bps=_number(
            section, "paper_slippage_bps", defaults.paper_slippage_bps
        ),
        poll_interval_ms=_integer(
            section, "poll_interval_ms", defaults.poll_interval_ms
        ),
        order_timeout_ms=_integer(
            section, "order_timeout_ms", defaults.order_timeout_ms
        ),
        max_retries=_integer(section, "max_retries", defaults.max_retries),
        entry_order_type=_text(
            section, "entry_order_type", defaults.entry_order_type
        ),
        limit_offset_bps=_number(
            section, "limit_offset_bps", defaults.limit_offset_bps
        ),
        paper_patience_bars=_integer(
            section, "paper_patience_bars", defaults.paper_patience_bars
        ),
        contract_infix=_text(section, "contract_infix", defaults.contract_infix),
    )
