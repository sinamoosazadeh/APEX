"""Portfolio platform configuration (``portfolio.yaml``, Phase 9).

Deep-validates the phase-owned ``portfolio`` section: the account
(initial capital, per-trade risk fraction), the governance caps
(Book II 13.27/21.12; Book I 8.15's daily/weekly risk budgets) and
the constrained-Kelly settings (Book V 4.11 - full Kelly is never
allowed). Everything-is-config: the engine hardcodes no cap, fraction
or threshold.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apex.core.config import ConfigSection, ConfigValue
from apex.core.exceptions import ConfigurationError

_CODE = "CFG-030"


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountSettings:
    """Account identity and per-trade risk (Book I 8.4)."""

    base_currency: str = "USDT"
    initial_capital: Decimal = Decimal(10_000)
    risk_fraction: float = 0.01
    tail_loss_multiple: float = 3.0
    defensive_drawdown_fraction: float = 0.05
    # Taker fee per fill as a fraction of notional (entry and exit
    # each charge it). 0 keeps ideal fills; the Phase 10 execution
    # engine supplies the venue rate through portfolio.yaml.
    fee_rate: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioCaps:
    """Governance caps (Book II 13.27/21.12; Book V portfolio risk)."""

    max_open_positions: int = 4
    max_positions_per_symbol: int = 1
    max_symbol_exposure_fraction: float = 0.35
    max_gross_exposure_fraction: float = 1.0
    daily_loss_limit_fraction: float = 0.02
    weekly_loss_limit_fraction: float = 0.05
    max_consecutive_losses: int = 4
    correlation_ceiling: float = 0.85
    correlation_window: int = 50


@dataclass(frozen=True, slots=True, kw_only=True)
class KellySettings:
    """Constrained Kelly (Book V 4.11: capped, never full)."""

    multiplier: float = 0.5
    cap: float = 0.25
    minimum_trades: int = 12


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSettings:
    """The validated portfolio platform configuration."""

    portfolio_id: str = "default"
    account: AccountSettings = AccountSettings()
    caps: PortfolioCaps = PortfolioCaps()
    kelly: KellySettings = KellySettings()

    def __post_init__(self) -> None:
        account = self.account
        caps = self.caps
        kelly = self.kelly
        _require(bool(self.portfolio_id), "portfolio_id must not be empty")
        _require(account.initial_capital > 0, "initial_capital must be positive")
        _require(0 < account.risk_fraction <= 0.1, "risk_fraction must be in (0, 0.1]")
        _require(account.tail_loss_multiple >= 1.0, "tail_loss_multiple must be >= 1")
        _require(0 <= account.fee_rate < 0.01, "fee_rate must be in [0, 0.01)")
        _require(
            0 < account.defensive_drawdown_fraction < 1,
            "defensive_drawdown_fraction must be in (0, 1)",
        )
        _require(caps.max_open_positions >= 1, "max_open_positions must be >= 1")
        _require(
            caps.max_positions_per_symbol >= 1, "max_positions_per_symbol must be >= 1"
        )
        _require(
            0 < caps.max_symbol_exposure_fraction <= caps.max_gross_exposure_fraction,
            "max_symbol_exposure_fraction must be in (0, gross cap]",
        )
        _require(
            0 < caps.daily_loss_limit_fraction <= caps.weekly_loss_limit_fraction,
            "daily_loss_limit_fraction must be in (0, weekly limit]",
        )
        _require(caps.weekly_loss_limit_fraction < 1, "weekly loss limit must be < 1")
        _require(caps.max_consecutive_losses >= 1, "max_consecutive_losses must be >= 1")
        _require(
            0.5 <= caps.correlation_ceiling <= 1.0,
            "correlation_ceiling must be in [0.5, 1.0]",
        )
        _require(caps.correlation_window >= 10, "correlation_window must be >= 10")
        _require(0 < kelly.multiplier <= 0.75, "kelly multiplier must be in (0, 0.75]")
        _require(0 < kelly.cap <= 0.5, "kelly cap must be in (0, 0.5]")
        _require(kelly.minimum_trades >= 1, "kelly minimum_trades must be >= 1")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message, code=_CODE, details={})


def _mapping(value: ConfigValue | None, name: str) -> ConfigSection:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"portfolio.{name} must be a mapping",
            code="CFG-031",
            details={"found": type(value).__name__},
        )
    return value


def _number(section: ConfigSection, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"portfolio value {key} must be a number",
            code="CFG-032",
            details={"found": repr(value)},
        )
    return float(value)


def _integer(section: ConfigSection, key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"portfolio value {key} must be an integer",
            code="CFG-033",
            details={"found": repr(value)},
        )
    return value


def _capital(section: ConfigSection, key: str, default: Decimal) -> Decimal:
    value = section.get(key, None)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConfigurationError(
            "portfolio initial_capital must be a string or integer (exact)",
            code="CFG-034",
            details={"found": repr(value)},
        )
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ConfigurationError(
            "portfolio initial_capital could not be parsed",
            code="CFG-034",
            details={"found": repr(value)},
        ) from exc


def portfolio_settings(section: ConfigSection) -> PortfolioSettings:
    """Parse and validate the ``portfolio`` config section."""
    if not isinstance(section, dict):
        raise ConfigurationError(
            "portfolio config must be a mapping", code="CFG-031", details={}
        )
    account_raw = _mapping(section.get("account"), "account")
    caps_raw = _mapping(section.get("caps"), "caps")
    kelly_raw = _mapping(section.get("kelly"), "kelly")
    base_currency = section.get("base_currency", "USDT")
    if not isinstance(base_currency, str) or not base_currency:
        raise ConfigurationError(
            "portfolio.base_currency must be a non-empty string",
            code="CFG-035",
            details={"found": repr(base_currency)},
        )
    portfolio_id = section.get("portfolio_id", "default")
    if not isinstance(portfolio_id, str) or not portfolio_id:
        raise ConfigurationError(
            "portfolio.portfolio_id must be a non-empty string",
            code="CFG-035",
            details={"found": repr(portfolio_id)},
        )
    account_defaults = AccountSettings()
    caps_defaults = PortfolioCaps()
    kelly_defaults = KellySettings()
    account = AccountSettings(
        base_currency=base_currency,
        initial_capital=_capital(
            account_raw, "initial_capital", account_defaults.initial_capital
        ),
        risk_fraction=_number(
            account_raw, "risk_fraction", account_defaults.risk_fraction
        ),
        tail_loss_multiple=_number(
            account_raw, "tail_loss_multiple", account_defaults.tail_loss_multiple
        ),
        defensive_drawdown_fraction=_number(
            account_raw,
            "defensive_drawdown_fraction",
            account_defaults.defensive_drawdown_fraction,
        ),
        fee_rate=_number(account_raw, "fee_rate", account_defaults.fee_rate),
    )
    caps = PortfolioCaps(
        max_open_positions=_integer(
            caps_raw, "max_open_positions", caps_defaults.max_open_positions
        ),
        max_positions_per_symbol=_integer(
            caps_raw, "max_positions_per_symbol", caps_defaults.max_positions_per_symbol
        ),
        max_symbol_exposure_fraction=_number(
            caps_raw,
            "max_symbol_exposure_fraction",
            caps_defaults.max_symbol_exposure_fraction,
        ),
        max_gross_exposure_fraction=_number(
            caps_raw,
            "max_gross_exposure_fraction",
            caps_defaults.max_gross_exposure_fraction,
        ),
        daily_loss_limit_fraction=_number(
            caps_raw,
            "daily_loss_limit_fraction",
            caps_defaults.daily_loss_limit_fraction,
        ),
        weekly_loss_limit_fraction=_number(
            caps_raw,
            "weekly_loss_limit_fraction",
            caps_defaults.weekly_loss_limit_fraction,
        ),
        max_consecutive_losses=_integer(
            caps_raw, "max_consecutive_losses", caps_defaults.max_consecutive_losses
        ),
        correlation_ceiling=_number(
            caps_raw, "correlation_ceiling", caps_defaults.correlation_ceiling
        ),
        correlation_window=_integer(
            caps_raw, "correlation_window", caps_defaults.correlation_window
        ),
    )
    kelly = KellySettings(
        multiplier=_number(kelly_raw, "multiplier", kelly_defaults.multiplier),
        cap=_number(kelly_raw, "cap", kelly_defaults.cap),
        minimum_trades=_integer(
            kelly_raw, "minimum_trades", kelly_defaults.minimum_trades
        ),
    )
    return PortfolioSettings(
        portfolio_id=portfolio_id, account=account, caps=caps, kelly=kelly
    )
