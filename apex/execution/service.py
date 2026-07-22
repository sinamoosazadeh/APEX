"""Execution service (Book II ch. 12/20).

Orchestrates one execution attempt end to end while honoring the two
golden rules: nothing decided upstream is ever altered (12.30), and
no order reaches a venue without readiness re-checks (20.31/20.25):

1. Load the latest fired signal of the series from the decision store.
2. Re-check risk and portfolio admission (``IRiskEngine.assess``
   against the stored portfolio state and closed-trade statistics) -
   a HALTED verdict rejects the execution with its reason set.
3. Construct the entry order (config entry style; sizing is the
   assessment's, never recomputed here) with an idempotent client id.
4. Execute: paper fills from confirmed bars, or the live venue
   lifecycle with bracket protection attached at the exchange.
5. Persist the audit (12.29), fold the fill into the portfolio's
   positions, and announce the outcome.

Live execution requires run mode ``live`` AND venue credentials; every
other mode executes on paper. Reconciliation (12.25) compares the
stored open positions against the venue account when trading is live.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from apex.core.context import ExecutionContext
from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import (
    Direction,
    OrderSide,
    OrderType,
    PositionStatus,
    RiskMode,
    RunMode,
    Timeframe,
)
from apex.core.exceptions import ApexError, ExecutionError
from apex.core.logging import StructuredLogger
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Confidence, Drawdown, Price, Probability, Quantity
from apex.decision.store import DecisionRecord, SqliteDecisionRepository
from apex.domain.money import Money
from apex.domain.order import Order
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.position import Position
from apex.domain.signal import PriceZone, Signal
from apex.domain.trade import Trade
from apex.execution.config import ENTRY_TYPE_LIMIT, ExecutionSettings
from apex.execution.engine import LiveExecutionEngine
from apex.execution.events import ExecutionEvent, execution_event
from apex.execution.paper import PaperExecutionEngine
from apex.execution.store import (
    STATUS_FILLED,
    STATUS_REJECTED,
    STATUS_UNFILLED,
    ExecutionRecord,
    FillRecord,
    SqliteExecutionRepository,
)
from apex.execution.trading.translator import client_order_id
from apex.features.calculations import clamp
from apex.portfolio.config import PortfolioSettings
from apex.portfolio.engine import PortfolioEngine
from apex.portfolio.store import PositionRecord, SqlitePortfolioRepository

_SOURCE: Final[str] = "apex.execution.service"
_BPS: Final[Decimal] = Decimal(10_000)
_EIGHT: Final[Decimal] = Decimal("0.00000001")

MODE_PAPER: Final[str] = "paper"
MODE_LIVE: Final[str] = "live"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSummary:
    """Outcome of one execution attempt."""

    execution_id: str
    mode: str
    symbol: str
    timeframe: Timeframe
    direction: str
    status: str
    order_type: str
    requested_quantity: str
    filled_quantity: str
    decision_price: str
    fill_price: str | None
    slippage: str | None
    fees: str
    position_opened: bool
    reasons: tuple[str, ...]


class ExecutionService:
    """Turns approved signals into audited, reconciled executions."""

    def __init__(
        self,
        *,
        exchange_id: str,
        settings: ExecutionSettings,
        portfolio_settings: PortfolioSettings,
        run_mode: RunMode,
        decision_repository: SqliteDecisionRepository,
        portfolio_repository: SqlitePortfolioRepository,
        portfolio_engine: PortfolioEngine,
        paper_engine: PaperExecutionEngine,
        live_engine: LiveExecutionEngine,
        execution_repository: SqliteExecutionRepository,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._exchange_id = exchange_id
        self._settings = settings
        self._portfolio_settings = portfolio_settings
        self._run_mode = run_mode
        self._decisions = decision_repository
        self._portfolio_store = portfolio_repository
        self._portfolio = portfolio_engine
        self._paper = paper_engine
        self._live = live_engine
        self._executions = execution_repository
        self._bus = bus
        self._clock = clock
        self._logger = logger

    async def execute_latest_signal(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
        live: bool = False,
    ) -> Result[ExecutionSummary]:
        """Execute the newest fired signal in [start, end)."""
        try:
            summary = await self._execute(symbol, timeframe, start, end, live)
        except ApexError as error:
            await self._announce_failure(symbol, timeframe, error)
            return Result.failure(error)
        return Result.success(summary)

    async def _execute(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: Timestamp,
        end: Timestamp,
        live: bool,
    ) -> ExecutionSummary:
        record = await self._latest_signal(symbol, timeframe, start, end)
        mode = self._resolve_mode(live)
        execution_id = uuid.uuid4()
        signal = self._signal(record)
        snapshot = await self._portfolio_state()
        statistics = await self._portfolio_store.statistics(
            self._portfolio_settings.portfolio_id
        )
        assessed = await self._portfolio.assess(
            signal, snapshot, statistics=statistics
        )
        assessment = assessed.unwrap()
        if assessment.risk_mode is RiskMode.HALTED or not assessment.is_tradeable:
            return await self._reject(execution_id, record, mode, "portfolio_halted")
        order = self._order(record, assessment.position_size, execution_id)
        # The execution request anchors at the decision instant - the
        # signal bar's close - so paper fills replay deterministically
        # and live fills coincide with it (the signal just closed).
        # The audit's requested_at stays the wall clock.
        signal_close = Timestamp(
            epoch_ms=record.bar_open_time.epoch_ms + timeframe.duration_ms
        )
        context = ExecutionContext(
            execution_id=execution_id,
            correlation_id=execution_id,
            signal_id=signal.object_id,
            exchange=self._exchange_id,
            symbol=symbol,
            requested_at=signal_close,
            timeframe=timeframe,
        )
        fills = await self._dispatch(order, context, record, mode)
        return await self._complete(execution_id, record, mode, order, fills)

    # --- Steps ----------------------------------------------------------------

    async def _latest_signal(
        self, symbol: str, timeframe: Timeframe, start: Timestamp, end: Timestamp
    ) -> DecisionRecord:
        decisions = await self._decisions.get_range(
            self._exchange_id, symbol, timeframe, start=start, end=end
        )
        fired = [
            record
            for record in decisions
            if record.action == "signal"
            and record.entry is not None
            and record.stop is not None
            and record.targets
        ]
        if not fired:
            raise ExecutionError(
                "no fired signal in the window",
                code="EXE-030",
                details={"symbol": symbol, "timeframe": timeframe.value},
            )
        return fired[-1]

    def _resolve_mode(self, live: bool) -> str:
        if not live:
            return MODE_PAPER
        if self._run_mode is not RunMode.LIVE:
            raise ExecutionError(
                "live execution requires run_mode live (system.yaml)",
                code="EXE-031",
                details={"run_mode": self._run_mode.value},
            )
        if not self._live.can_trade:
            raise ExecutionError(
                "live execution requires venue credentials",
                code="EXE-032",
            )
        return MODE_LIVE

    def _signal(self, record: DecisionRecord) -> Signal:
        def zone(price: float) -> PriceZone:
            value = Price(Decimal(str(price)))
            return PriceZone(lower=value, upper=value)

        assert record.entry is not None and record.stop is not None
        return Signal(
            created_at=self._clock.now(),
            exchange=record.exchange,
            symbol=record.symbol,
            timeframe=record.timeframe,
            direction=Direction(record.direction),
            probability=Probability(clamp(record.probability, 0.0, 1.0)),
            confidence=Confidence(
                clamp(record.probability * (1.0 - record.uncertainty), 0.0, 1.0)
            ),
            entry_zone=zone(record.entry),
            stop_zone=zone(record.stop),
            target_zones=tuple(zone(target) for target in record.targets),
        )

    async def _portfolio_state(self) -> PortfolioSnapshot:
        """Latest stored snapshot; a fresh account when none exists."""
        snapshots = await self._portfolio_store.get_snapshots(
            self._portfolio_settings.portfolio_id
        )
        currency = self._portfolio_settings.account.base_currency
        if snapshots:
            latest = snapshots[-1]
            open_records = await self._portfolio_store.get_positions(
                self._portfolio_settings.portfolio_id,
                status=PositionStatus.OPEN.value,
            )
            return PortfolioSnapshot(
                created_at=latest.as_of,
                as_of=latest.as_of,
                base_currency=currency,
                equity=Money(currency=currency, amount=latest.equity),
                cash=Money(currency=currency, amount=latest.cash),
                total_exposure=Money(currency=currency, amount=latest.gross_exposure),
                unrealized_pnl=Money(currency=currency, amount=latest.unrealized_pnl),
                realized_pnl=Money(currency=currency, amount=latest.realized_pnl),
                current_drawdown=Drawdown(latest.drawdown),
                open_positions=tuple(
                    self._position_from_record(record) for record in open_records
                ),
            )
        now = self._clock.now()
        capital = self._portfolio_settings.account.initial_capital
        zero = Money(currency=currency, amount=Decimal(0))
        return PortfolioSnapshot(
            created_at=now,
            as_of=now,
            base_currency=currency,
            equity=Money(currency=currency, amount=capital),
            cash=Money(currency=currency, amount=capital),
            total_exposure=zero,
            unrealized_pnl=zero,
            realized_pnl=zero,
            current_drawdown=Drawdown(0.0),
            open_positions=(),
        )

    def _position_from_record(self, record: PositionRecord) -> Position:
        return Position(
            created_at=record.opened_at,
            exchange=record.exchange,
            symbol=record.symbol,
            direction=Direction(record.direction),
            quantity=Quantity(record.quantity),
            average_entry=Price(record.entry),
            opened_at=record.opened_at,
            status=PositionStatus.OPEN,
        )

    def _order(
        self, record: DecisionRecord, quantity: Quantity, execution_id: uuid.UUID
    ) -> Order:
        assert record.entry is not None
        side = (
            OrderSide.BUY if record.direction == Direction.LONG.value else OrderSide.SELL
        )
        limit_price: Price | None = None
        order_type = OrderType.MARKET
        if self._settings.entry_order_type == ENTRY_TYPE_LIMIT:
            order_type = OrderType.LIMIT
            offset = Decimal(str(self._settings.limit_offset_bps)) / _BPS
            sign = Decimal(1) if side is OrderSide.BUY else Decimal(-1)
            price = Decimal(str(record.entry)) * (Decimal(1) - sign * offset)
            limit_price = Price(price.quantize(_EIGHT))
        return Order(
            created_at=self._clock.now(),
            exchange=self._exchange_id,
            symbol=record.symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            client_order_id=client_order_id(execution_id),
        )

    async def _dispatch(
        self,
        order: Order,
        context: ExecutionContext,
        record: DecisionRecord,
        mode: str,
    ) -> tuple[Trade, ...]:
        assert record.stop is not None
        if mode == MODE_LIVE:
            result = await self._live.execute_bracket(
                order,
                context,
                stop_loss=Decimal(str(record.stop)),
                take_profit=Decimal(str(record.targets[-1])),
            )
        else:
            result = await self._paper.execute(order, context)
        return tuple(result.unwrap())

    async def _reject(
        self,
        execution_id: uuid.UUID,
        record: DecisionRecord,
        mode: str,
        reason: str,
    ) -> ExecutionSummary:
        summary = self._summary(
            execution_id, record, mode, None, (), STATUS_REJECTED, (reason,)
        )
        await self._persist(execution_id, record, mode, None, (), summary)
        await self._announce(ExecutionEvent.REJECTED, summary)
        return summary

    async def _complete(
        self,
        execution_id: uuid.UUID,
        record: DecisionRecord,
        mode: str,
        order: Order,
        fills: tuple[Trade, ...],
    ) -> ExecutionSummary:
        status = STATUS_FILLED if fills else STATUS_UNFILLED
        summary = self._summary(
            execution_id, record, mode, order, fills, status, ()
        )
        await self._persist(execution_id, record, mode, order, fills, summary)
        if fills:
            await self._open_position(execution_id, record, fills)
            await self._announce(ExecutionEvent.FILLED, summary)
        else:
            await self._announce(ExecutionEvent.UNFILLED, summary)
        return summary

    # --- Persistence and reporting -----------------------------------------------

    def _summary(
        self,
        execution_id: uuid.UUID,
        record: DecisionRecord,
        mode: str,
        order: Order | None,
        fills: tuple[Trade, ...],
        status: str,
        reasons: tuple[str, ...],
    ) -> ExecutionSummary:
        assert record.entry is not None
        decision_price = Decimal(str(record.entry))
        filled_quantity = sum((fill.quantity.value for fill in fills), Decimal(0))
        fees = sum((fill.fee.amount for fill in fills), Decimal(0))
        fill_price: Decimal | None = None
        slippage: Decimal | None = None
        if fills and filled_quantity > 0:
            notional = sum(
                (fill.price.value * fill.quantity.value for fill in fills), Decimal(0)
            )
            fill_price = (notional / filled_quantity).quantize(_EIGHT)
            sign = Decimal(1) if record.direction == "long" else Decimal(-1)
            slippage = ((fill_price - decision_price) * sign).quantize(_EIGHT)
        return ExecutionSummary(
            execution_id=str(execution_id),
            mode=mode,
            symbol=record.symbol,
            timeframe=record.timeframe,
            direction=record.direction,
            status=status,
            order_type=order.order_type.value if order else "none",
            requested_quantity=str(order.quantity.value) if order else "0",
            filled_quantity=str(filled_quantity),
            decision_price=str(decision_price),
            fill_price=str(fill_price) if fill_price is not None else None,
            slippage=str(slippage) if slippage is not None else None,
            fees=str(fees),
            position_opened=bool(fills),
            reasons=reasons,
        )

    async def _persist(
        self,
        execution_id: uuid.UUID,
        record: DecisionRecord,
        mode: str,
        order: Order | None,
        fills: tuple[Trade, ...],
        summary: ExecutionSummary,
    ) -> None:
        assert record.entry is not None and record.stop is not None
        now = self._clock.now()
        await self._executions.upsert_execution(
            ExecutionRecord(
                execution_id=summary.execution_id,
                portfolio_id=self._portfolio_settings.portfolio_id,
                exchange=self._exchange_id,
                symbol=record.symbol,
                timeframe=record.timeframe,
                mode=mode,
                signal_bar_time=record.bar_open_time,
                direction=record.direction,
                order_type=summary.order_type,
                client_order_id=(
                    order.client_order_id
                    if order and order.client_order_id
                    else client_order_id(execution_id)
                ),
                requested_at=now,
                completed_at=now,
                status=summary.status,
                quantity=Decimal(summary.requested_quantity),
                decision_price=Decimal(summary.decision_price),
                fill_price=(
                    Decimal(summary.fill_price)
                    if summary.fill_price is not None
                    else None
                ),
                fees=Decimal(summary.fees),
                slippage=(
                    Decimal(summary.slippage)
                    if summary.slippage is not None
                    else None
                ),
                stop=Decimal(str(record.stop)),
                target=Decimal(str(record.targets[-1])),
                reasons=summary.reasons,
            )
        )
        await self._executions.upsert_fills(
            [
                FillRecord(
                    execution_id=summary.execution_id,
                    exchange_trade_id=fill.exchange_trade_id or str(fill.object_id),
                    price=fill.price.value,
                    quantity=fill.quantity.value,
                    fee=fill.fee.amount,
                    liquidity_role=fill.liquidity_role.value,
                    executed_at=fill.executed_at,
                )
                for fill in fills
            ]
        )

    async def _open_position(
        self,
        execution_id: uuid.UUID,
        record: DecisionRecord,
        fills: tuple[Trade, ...],
    ) -> None:
        """Fold the executed entry into the portfolio's positions."""
        assert record.entry is not None and record.stop is not None
        quantity = sum((fill.quantity.value for fill in fills), Decimal(0))
        notional = sum(
            (fill.price.value * fill.quantity.value for fill in fills), Decimal(0)
        )
        entry = (notional / quantity).quantize(_EIGHT)
        stop = Decimal(str(record.stop))
        opened_at = fills[-1].executed_at
        await self._portfolio_store.upsert_positions(
            [
                PositionRecord(
                    portfolio_id=self._portfolio_settings.portfolio_id,
                    exchange=self._exchange_id,
                    symbol=record.symbol,
                    timeframe=record.timeframe,
                    entry_bar_time=record.bar_open_time,
                    position_id=str(execution_id),
                    lineage_id=str(execution_id),
                    direction=record.direction,
                    quantity=quantity,
                    entry=entry,
                    stop=stop,
                    target=Decimal(str(record.targets[-1])),
                    risk_amount=(abs(entry - stop) * quantity).quantize(_EIGHT),
                    opened_at=opened_at,
                    status=PositionStatus.OPEN.value,
                    closed_at=None,
                    exit_price=None,
                    realized_pnl=None,
                    realized_r=None,
                    close_reason=None,
                )
            ]
        )

    async def _announce(self, kind: ExecutionEvent, summary: ExecutionSummary) -> None:
        await self._bus.publish(
            execution_event(
                kind,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "execution_id": summary.execution_id,
                    "mode": summary.mode,
                    "symbol": summary.symbol,
                    "timeframe": summary.timeframe.value,
                    "direction": summary.direction,
                    "status": summary.status,
                    "fill_price": summary.fill_price,
                    "fees": summary.fees,
                },
            )
        )
        self._logger.info(
            "execution_completed",
            execution_id=summary.execution_id,
            mode=summary.mode,
            symbol=summary.symbol,
            status=summary.status,
            fill_price=summary.fill_price or "-",
        )

    async def _announce_failure(
        self, symbol: str, timeframe: Timeframe, error: ApexError
    ) -> None:
        await self._bus.publish(
            execution_event(
                ExecutionEvent.FAILED,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "error_code": error.code,
                    "error_message": str(error),
                },
            )
        )
        self._logger.error(
            "execution_failed",
            symbol=symbol,
            timeframe=timeframe.value,
            error_code=error.code,
        )
