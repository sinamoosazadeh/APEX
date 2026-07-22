"""Portfolio governance (Book II 13.27/21.12; Book I 8.15).

The macro-level admission rules, independent of any strategy. Binary
caps - position ceilings, the daily/weekly realized-loss budgets, the
consecutive-loss brake and the correlated-exposure ceiling - reject a
trade outright. Exposure caps *shape* instead: per Book II 21.29 the
portfolio may send an adjusted version of the trade, so the engine
reduces quantity to the remaining exposure headroom and rejects only
when no headroom is left. Every rejection carries its full reason set
(the 21.26 explainability contract) and the check order is fixed, so
verdicts are deterministic and auditable.
"""

from dataclasses import dataclass
from decimal import Decimal

from apex.portfolio.config import PortfolioCaps
from apex.portfolio.exposure import ExposureView

REJECT_MAX_OPEN_POSITIONS = "max_open_positions"
REJECT_SYMBOL_OCCUPIED = "symbol_occupied"
REJECT_EXPOSURE_HEADROOM = "exposure_headroom"
REJECT_DAILY_LOSS_LIMIT = "daily_loss_limit"
REJECT_WEEKLY_LOSS_LIMIT = "weekly_loss_limit"
REJECT_CONSECUTIVE_LOSSES = "consecutive_losses"
REJECT_CORRELATED_EXPOSURE = "correlated_exposure"

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True, kw_only=True)
class AdmissionContext:
    """Everything the binary caps need to judge one prospective open."""

    positions_open: int
    positions_in_symbol: int
    day_loss_fraction: float
    week_loss_fraction: float
    consecutive_losses: int
    correlated_symbols: tuple[str, ...]


def admission_failures(
    context: AdmissionContext, caps: PortfolioCaps
) -> tuple[str, ...]:
    """The ordered set of violated binary caps (empty means admitted)."""
    failures: list[str] = []
    if context.positions_open >= caps.max_open_positions:
        failures.append(REJECT_MAX_OPEN_POSITIONS)
    if context.positions_in_symbol >= caps.max_positions_per_symbol:
        failures.append(REJECT_SYMBOL_OCCUPIED)
    if context.day_loss_fraction >= caps.daily_loss_limit_fraction:
        failures.append(REJECT_DAILY_LOSS_LIMIT)
    if context.week_loss_fraction >= caps.weekly_loss_limit_fraction:
        failures.append(REJECT_WEEKLY_LOSS_LIMIT)
    if context.consecutive_losses >= caps.max_consecutive_losses:
        failures.append(REJECT_CONSECUTIVE_LOSSES)
    if context.correlated_symbols:
        failures.append(REJECT_CORRELATED_EXPOSURE)
    return tuple(failures)


def exposure_headroom(
    symbol: str,
    exposure: ExposureView,
    equity: Decimal,
    caps: PortfolioCaps,
) -> Decimal:
    """Remaining admissible notional for one symbol (never negative).

    The binding constraint of the per-symbol and gross exposure caps,
    measured against marked equity - the room an adjusted trade may
    still occupy (Book II 21.29).
    """
    if equity <= 0:
        return _ZERO
    symbol_room = (
        equity * Decimal(str(caps.max_symbol_exposure_fraction))
        - exposure.symbol_notional(symbol)
    )
    gross_room = (
        equity * Decimal(str(caps.max_gross_exposure_fraction))
        - exposure.gross_notional
    )
    return max(min(symbol_room, gross_room), _ZERO)
