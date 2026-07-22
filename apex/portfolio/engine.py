"""Portfolio Intelligence Engine (Book II ch. 13/21; Book I ch. 8).

The institutional layer between decisions and execution: folds the
fired-signal streams of one or more series into a single governed
portfolio - positions, account state, exposure, risk budgets - and
answers the admission contract (:class:`IRiskEngine`) for prospective
trades. The golden rule (Book II 13.30/21.30) is structural here: a
signal only becomes a position when the whole portfolio can carry it,
and every rejection records its full reason set.

The fold is pure and deterministic: series merge on confirmed bar
CLOSE time (signals fire at closes; a 4h bar joins the timeline at
its close, not its open), entries precede closes within a bar (the
AICE order the kernel ledger follows), and all money arithmetic is
exact Decimal. Sizing uses realized (cash) equity - unrealized PnL is
not bankable - while exposure caps measure against marked equity.

Documented deferrals: effective/beta exposure, sector dimensions and
the scenario/stress engines need their data sources (Phases 11+).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from apex.core.enums import Direction, RiskMode, Timeframe
from apex.core.exceptions import ApexError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Drawdown, Probability, Quantity, RiskScore, Volatility
from apex.decision.store import DecisionRecord
from apex.domain.market import Bar
from apex.domain.money import Money
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.position import Position
from apex.domain.risk import RiskAssessment
from apex.domain.signal import Signal
from apex.portfolio.account import AccountFold, TradeStatistics, constrained_kelly
from apex.portfolio.config import PortfolioSettings
from apex.portfolio.exposure import (
    ExposureView,
    exposure_view,
    rolling_return_correlation,
    unrealized_pnl,
)
from apex.portfolio.governance import (
    REJECT_EXPOSURE_HEADROOM,
    AdmissionContext,
    admission_failures,
    exposure_headroom,
)
from apex.portfolio.ledger import (
    ClosedTrade,
    OpenLot,
    close_lot,
    open_lot,
    size_position,
)

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesStream:
    """One series' confirmed bars and persisted decisions."""

    symbol: str
    timeframe: Timeframe
    bars: tuple[Bar, ...]
    decisions: tuple[DecisionRecord, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Rejection:
    """One governed rejection with its full reason set (21.26)."""

    exchange: str
    symbol: str
    timeframe: Timeframe
    bar_open_time: Timestamp
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioFold:
    """The complete outcome of one deterministic portfolio fold."""

    open_positions: tuple[OpenLot, ...]
    closed_positions: tuple[Position, ...]
    closed_trades: tuple[ClosedTrade, ...]
    rejections: tuple[Rejection, ...]
    snapshots: tuple[PortfolioSnapshot, ...]
    final: PortfolioSnapshot
    statistics: TradeStatistics


@dataclass(slots=True)
class _FoldState:
    """Mutable working state of one fold."""

    account: AccountFold
    lots: list[OpenLot]
    last_close: dict[str, Decimal]
    history: dict[tuple[str, Timeframe], list[float]]
    closed_positions: list[Position]
    closed_trades: list[ClosedTrade]
    rejections: list[Rejection]
    snapshots: list[PortfolioSnapshot]


class PortfolioEngine:
    """Folds decision streams into a governed portfolio state."""

    def __init__(
        self,
        *,
        settings: PortfolioSettings,
        clock: Clock,
        conservative_resolver: bool = True,
    ) -> None:
        self._settings = settings
        self._clock = clock
        # Same-bar collision convention shared with the kernel ledger
        # (market.yaml decision section); the two folds never drift.
        self._conservative = conservative_resolver

    # --- Fold -----------------------------------------------------------------

    def fold_streams(self, streams: Sequence[SeriesStream]) -> Result[PortfolioFold]:
        """Fold the series into one portfolio, oldest close first."""
        try:
            fold = self._fold(list(streams))
        except ApexError as error:
            return Result.failure(error)
        return Result.success(fold)

    def _fold(self, streams: list[SeriesStream]) -> PortfolioFold:
        keys = [(stream.symbol, stream.timeframe) for stream in streams]
        if len(set(keys)) != len(keys):
            raise ApexError("duplicate series stream", code="PRT-001")
        signals = {
            (stream.symbol, stream.timeframe, record.bar_open_time.epoch_ms): record
            for stream in streams
            for record in stream.decisions
            if record.action == "signal"
        }
        timeline = sorted(
            (
                (bar.open_time.epoch_ms + bar.timeframe.duration_ms, stream, bar)
                for stream in streams
                for bar in stream.bars
            ),
            key=lambda item: (item[0], item[1].symbol, item[1].timeframe.value),
        )
        currency = self._settings.account.base_currency
        state = _FoldState(
            account=AccountFold(
                base_currency=currency,
                initial_capital=self._settings.account.initial_capital,
            ),
            lots=[],
            last_close={},
            history={},
            closed_positions=[],
            closed_trades=[],
            rejections=[],
            snapshots=[],
        )
        last_time = Timestamp(epoch_ms=0)
        for close_ms, stream, bar in timeline:
            self._fold_bar(state, signals, stream, bar, close_ms)
            last_time = Timestamp(epoch_ms=close_ms)
        final = self._snapshot(state, last_time)
        return PortfolioFold(
            open_positions=tuple(state.lots),
            closed_positions=tuple(state.closed_positions),
            closed_trades=tuple(state.closed_trades),
            rejections=tuple(state.rejections),
            snapshots=tuple(state.snapshots),
            final=final,
            statistics=state.account.statistics(),
        )

    def _fold_bar(
        self,
        state: _FoldState,
        signals: dict[tuple[str, Timeframe, int], DecisionRecord],
        stream: SeriesStream,
        bar: Bar,
        close_ms: int,
    ) -> None:
        symbol = stream.symbol
        state.history.setdefault((symbol, stream.timeframe), []).append(
            float(bar.close.value)
        )
        state.last_close[symbol] = bar.close.value
        marked = state.account.equity(unrealized_pnl(state.lots, state.last_close))
        state.account.roll_windows(close_ms, marked)
        activity = False
        record = signals.get((symbol, stream.timeframe, bar.open_time.epoch_ms))
        if record is not None:
            activity = self._admit(state, stream, bar, record) or activity
        activity = self._close_pass(state, stream, bar) or activity
        state.account.mark(
            state.account.equity(unrealized_pnl(state.lots, state.last_close))
        )
        if activity:
            state.snapshots.append(self._snapshot(state, Timestamp(epoch_ms=close_ms)))

    def _admit(
        self,
        state: _FoldState,
        stream: SeriesStream,
        bar: Bar,
        record: DecisionRecord,
    ) -> bool:
        """Judge one fired signal: open (possibly reduced) or reject.

        Binary caps reject outright; the exposure caps reduce quantity
        to the remaining headroom (Book II 21.29's adjusted trade) and
        reject only when no headroom is left.
        """
        if record.entry is None or record.stop is None or not record.targets:
            return False
        entry = Decimal(str(record.entry))
        stop = Decimal(str(record.stop))
        target = Decimal(str(record.targets[-1]))
        direction = Direction(record.direction)
        exposure = exposure_view(state.lots, state.last_close)
        marked_equity = state.account.equity(
            unrealized_pnl(state.lots, state.last_close)
        )
        context = AdmissionContext(
            positions_open=exposure.open_positions,
            positions_in_symbol=sum(
                1 for lot in state.lots if lot.position.symbol == stream.symbol
            ),
            day_loss_fraction=state.account.window_loss_fraction(weekly=False),
            week_loss_fraction=state.account.window_loss_fraction(weekly=True),
            consecutive_losses=state.account.consecutive_losses,
            correlated_symbols=self._correlated(state, stream, direction),
        )
        failures = admission_failures(context, self._settings.caps)
        quantity = self._shaped_quantity(
            cash=state.account.closed_equity,
            marked_equity=marked_equity,
            entry=entry,
            stop=stop,
            symbol=stream.symbol,
            exposure=exposure,
        )
        if quantity <= 0:
            failures = (*failures, REJECT_EXPOSURE_HEADROOM)
        if failures:
            state.rejections.append(self._rejection(record, failures))
            return True
        risk_amount = Money(
            currency=self._settings.account.base_currency,
            amount=quantity * abs(entry - stop),
        )
        state.lots.append(
            open_lot(
                bar=bar,
                timeframe=stream.timeframe,
                direction=direction,
                entry=entry,
                stop=stop,
                target=target,
                quantity=quantity,
                risk_amount=risk_amount,
                entry_index=len(state.history[(stream.symbol, stream.timeframe)]) - 1,
            )
        )
        return True

    def _shaped_quantity(
        self,
        *,
        cash: Decimal,
        marked_equity: Decimal,
        entry: Decimal,
        stop: Decimal,
        symbol: str,
        exposure: ExposureView,
    ) -> Decimal:
        """Risk-fraction size reduced to the exposure headroom.

        Sizing risks a fraction of realized (cash) equity - unrealized
        PnL is not bankable - while the headroom measures against
        marked equity, the exposure caps' basis.
        """
        risk_quantity = size_position(
            cash, self._settings.account.risk_fraction, abs(entry - stop)
        )
        if risk_quantity <= 0 or entry <= 0:
            return Decimal(0)
        headroom = exposure_headroom(
            symbol, exposure, marked_equity, self._settings.caps
        )
        cap_quantity = (headroom / entry).quantize(Decimal("0.00000001"))
        return min(risk_quantity, cap_quantity)

    def _close_pass(self, state: _FoldState, stream: SeriesStream, bar: Bar) -> bool:
        """Close this series' touched lots (entries precede closes)."""
        remaining: list[OpenLot] = []
        closed_any = False
        for lot in state.lots:
            if (
                lot.position.symbol != stream.symbol
                or lot.timeframe is not stream.timeframe
            ):
                remaining.append(lot)
                continue
            closed = close_lot(
                lot,
                bar,
                conservative=self._conservative,
                currency=self._settings.account.base_currency,
                fee_rate=Decimal(str(self._settings.account.fee_rate)),
            )
            if closed is None:
                remaining.append(lot)
                continue
            position, trade = closed
            state.closed_positions.append(position)
            state.closed_trades.append(trade)
            state.account.apply_close(trade)
            closed_any = True
        state.lots = remaining
        return closed_any

    def _correlated(
        self, state: _FoldState, stream: SeriesStream, direction: Direction
    ) -> tuple[str, ...]:
        """Open same-direction symbols over the correlation ceiling."""
        caps = self._settings.caps
        candidate = state.history.get((stream.symbol, stream.timeframe), [])
        flagged: list[str] = []
        for lot in state.lots:
            symbol = lot.position.symbol
            if symbol == stream.symbol or lot.position.direction is not direction:
                continue
            other = state.history.get((symbol, stream.timeframe))
            if other is None:
                continue
            rho = rolling_return_correlation(
                candidate, other, caps.correlation_window
            )
            if rho is not None and rho > caps.correlation_ceiling:
                flagged.append(symbol)
        return tuple(dict.fromkeys(flagged))

    def _rejection(
        self, record: DecisionRecord, reasons: tuple[str, ...]
    ) -> Rejection:
        return Rejection(
            exchange=record.exchange,
            symbol=record.symbol,
            timeframe=record.timeframe,
            bar_open_time=record.bar_open_time,
            reasons=reasons,
        )

    def _snapshot(self, state: _FoldState, as_of: Timestamp) -> PortfolioSnapshot:
        currency = self._settings.account.base_currency
        unrealized = unrealized_pnl(state.lots, state.last_close)
        exposure = exposure_view(state.lots, state.last_close)
        return PortfolioSnapshot(
            created_at=as_of,
            as_of=as_of,
            base_currency=currency,
            equity=Money(currency=currency, amount=state.account.equity(unrealized)),
            cash=Money(currency=currency, amount=state.account.closed_equity),
            total_exposure=Money(currency=currency, amount=exposure.gross_notional),
            unrealized_pnl=Money(currency=currency, amount=unrealized),
            realized_pnl=Money(currency=currency, amount=state.account.realized),
            current_drawdown=Drawdown(state.account.current_drawdown),
            open_positions=tuple(lot.position for lot in state.lots),
        )

    # --- Admission contract (IRiskEngine) ---------------------------------------

    async def assess(
        self,
        signal: Signal,
        portfolio: PortfolioSnapshot,
        *,
        statistics: TradeStatistics | None = None,
    ) -> Result[RiskAssessment]:
        """Risk verdict for one prospective trade (Book II 5.10).

        Sizing is risk-fraction against the snapshot's cash equity;
        the constrained-Kelly fraction (Book V 4.11) is reported from
        the closed-trade ``statistics`` when supplied (the service
        passes them from the store). Caps that need series history
        (correlation control) are enforced in the fold path - a bare
        snapshot cannot answer them and this method never guesses.
        """
        try:
            assessment = self._assess(signal, portfolio, statistics)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(assessment)

    def _assess(
        self,
        signal: Signal,
        portfolio: PortfolioSnapshot,
        statistics: TradeStatistics | None,
    ) -> RiskAssessment:
        settings = self._settings
        currency = settings.account.base_currency
        entry = signal.entry_zone.lower.value
        stop = signal.stop_zone.lower.value
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            raise ApexError("signal carries no stop distance", code="PRT-002")
        equity = portfolio.equity.amount
        exposure = self._snapshot_exposure(portfolio)
        context = AdmissionContext(
            positions_open=len(portfolio.open_positions),
            positions_in_symbol=sum(
                1
                for position in portfolio.open_positions
                if position.symbol == signal.symbol
            ),
            day_loss_fraction=0.0,
            week_loss_fraction=0.0,
            consecutive_losses=statistics.consecutive_losses if statistics else 0,
            correlated_symbols=(),
        )
        failures = admission_failures(context, settings.caps)
        quantity = self._shaped_quantity(
            cash=portfolio.cash.amount,
            marked_equity=equity,
            entry=entry,
            stop=stop,
            symbol=signal.symbol,
            exposure=exposure,
        )
        if quantity <= 0:
            failures = (*failures, REJECT_EXPOSURE_HEADROOM)
            # Quantity is strictly positive: a vetoed assessment still
            # reports the plan-consistent size; HALTED carries the veto.
            quantity = size_position(
                portfolio.cash.amount, settings.account.risk_fraction, risk_per_unit
            )
        if quantity <= 0:
            raise ApexError("account cannot size the trade", code="PRT-003")
        drawdown = portfolio.current_drawdown.value
        if failures:
            mode = RiskMode.HALTED
        elif drawdown >= settings.account.defensive_drawdown_fraction:
            mode = RiskMode.DEFENSIVE
        else:
            mode = RiskMode.BALANCED
        risk_amount = quantity * risk_per_unit
        headroom = exposure_headroom(signal.symbol, exposure, equity, settings.caps)
        return RiskAssessment(
            created_at=self._clock.now(),
            signal_id=signal.object_id,
            risk_score=RiskScore(
                min(max(1.0 - signal.probability.value, 0.0), 1.0)
            ),
            position_size=Quantity(quantity),
            max_exposure=Money(currency=currency, amount=headroom),
            expected_loss=Money(currency=currency, amount=risk_amount),
            tail_loss=Money(
                currency=currency,
                amount=risk_amount
                * Decimal(str(settings.account.tail_loss_multiple)),
            ),
            expected_drawdown=Drawdown(
                min(float(risk_amount / equity), 1.0) if equity > 0 else 0.0
            ),
            kelly_fraction=Probability(self._kelly(statistics)),
            volatility_budget=Volatility(float(risk_per_unit / entry)),
            risk_mode=mode,
        )

    def _snapshot_exposure(self, portfolio: PortfolioSnapshot) -> ExposureView:
        """Exposure over the snapshot's positions, marked at entry.

        The snapshot carries no live prices; entry marks are the
        honest available basis for the admission fractions here.
        """
        by_symbol: dict[str, Decimal] = {}
        longs = 0
        shorts = 0
        for position in portfolio.open_positions:
            notional = position.quantity.value * position.average_entry.value
            if position.direction is Direction.LONG:
                longs += 1
                signed = notional
            else:
                shorts += 1
                signed = -notional
            by_symbol[position.symbol] = (
                by_symbol.get(position.symbol, _ZERO) + signed
            )
        return ExposureView(
            gross_notional=sum(
                (abs(value) for value in by_symbol.values()), _ZERO
            ),
            net_notional=sum(by_symbol.values(), _ZERO),
            by_symbol=by_symbol,
            open_positions=len(portfolio.open_positions),
            long_positions=longs,
            short_positions=shorts,
        )

    def _kelly(self, statistics: TradeStatistics | None) -> float:
        """Constrained Kelly (Book V 4.11); risk fraction below the
        minimum trade count - exactly a fresh AICE chart's behavior."""
        kelly = self._settings.kelly
        fallback = self._settings.account.risk_fraction
        if statistics is None:
            return fallback
        return constrained_kelly(
            statistics,
            multiplier=kelly.multiplier,
            cap=kelly.cap,
            minimum_trades=kelly.minimum_trades,
            fallback=fallback,
        )
