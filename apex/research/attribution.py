"""Trade attribution (Book II 14.13-14.15; AICE lines 3255-3271).

Joins the system's own durable records into the learning substrate:
each closed portfolio trade is matched to the decision that fired it
(setup, probability at entry) and the assessment channels of the same
bar (per-channel evidence of the fired side - AICE's ``open_f0..12``).
The join is exact on (symbol, timeframe, entry bar); trades without a
matching decision or assessment are skipped and counted, never
guessed.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from apex.core.enums import Timeframe
from apex.decision.store import DecisionRecord
from apex.domain.learning import CHANNEL_NAMES
from apex.portfolio.store import PositionRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeOutcome:
    """One closed trade with its decision-time evidence."""

    symbol: str
    timeframe: Timeframe
    entry_bar_ms: int
    closed_at_ms: int
    setup: str
    direction: str
    probability: float
    win: bool
    realized_r: float
    channel_scores: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributionResult:
    """The joined outcome stream and its join accounting."""

    outcomes: tuple[TradeOutcome, ...]
    closed_trades: int
    unmatched_decisions: int
    unmatched_channels: int


def join_outcomes(
    positions: Sequence[PositionRecord],
    decisions: Sequence[DecisionRecord],
    channels_by_bar: Mapping[int, Mapping[str, float]],
) -> AttributionResult:
    """Match closed positions to their decision and evidence.

    ``channels_by_bar`` maps the entry bar's open ms to that bar's
    assessment channels payload. Outcomes come back in close order -
    the fold order of every learning consumer.
    """
    decision_by_bar = {
        record.bar_open_time.epoch_ms: record
        for record in decisions
        if record.action == "signal"
    }
    closed = [
        record
        for record in positions
        if record.status == "closed"
        and record.realized_r is not None
        and record.closed_at is not None
    ]
    closed.sort(key=lambda record: (record.closed_at.epoch_ms if record.closed_at else 0))
    outcomes: list[TradeOutcome] = []
    unmatched_decisions = 0
    unmatched_channels = 0
    for record in closed:
        entry_ms = record.entry_bar_time.epoch_ms
        decision = decision_by_bar.get(entry_ms)
        if decision is None:
            unmatched_decisions += 1
            continue
        channels = channels_by_bar.get(entry_ms)
        if channels is None:
            unmatched_channels += 1
            continue
        suffix = "long" if record.direction == "long" else "short"
        scores = tuple(
            float(channels.get(f"{name}_{suffix}", 0.0)) for name in CHANNEL_NAMES
        )
        assert record.realized_r is not None and record.closed_at is not None
        outcomes.append(
            TradeOutcome(
                symbol=record.symbol,
                timeframe=record.timeframe,
                entry_bar_ms=entry_ms,
                closed_at_ms=record.closed_at.epoch_ms,
                setup=decision.setup,
                direction=record.direction,
                probability=decision.probability,
                win=record.close_reason == "target",
                realized_r=record.realized_r,
                channel_scores=scores,
            )
        )
    return AttributionResult(
        outcomes=tuple(outcomes),
        closed_trades=len(closed),
        unmatched_decisions=unmatched_decisions,
        unmatched_channels=unmatched_channels,
    )
