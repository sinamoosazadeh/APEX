"""Portfolio platform: config, ledger, account, exposure, governance,
engine fold, admission contract, store."""

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from apex.core.enums import Direction, PositionStatus, RiskMode, Timeframe
from apex.core.exceptions import ConfigurationError
from apex.core.time.clock import ManualClock
from apex.core.types import Confidence, Drawdown, Price, Probability, QualityScore, Volume
from apex.decision.store import DecisionRecord
from apex.domain.market import Bar
from apex.domain.money import Money
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.position import Position
from apex.domain.signal import PriceZone, Signal
from apex.portfolio.account import (
    AccountFold,
    TradeStatistics,
    constrained_kelly,
    day_key,
    week_key,
)
from apex.portfolio.config import PortfolioCaps, PortfolioSettings, portfolio_settings
from apex.portfolio.engine import PortfolioEngine, SeriesStream
from apex.portfolio.exposure import (
    exposure_view,
    rolling_return_correlation,
    unrealized_pnl,
)
from apex.portfolio.governance import (
    AdmissionContext,
    admission_failures,
    exposure_headroom,
)
from apex.portfolio.ledger import OpenLot, close_lot, open_lot, size_position
from apex.portfolio.store import (
    PositionRecord,
    RejectionRecord,
    SnapshotRecord,
    SqlitePortfolioRepository,
)

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms


def make_bar(
    index: int, o: float, h: float, low: float, c: float, symbol: str = "BTCUSDT"
) -> Bar:
    return Bar(
        exchange="toobit",
        symbol=symbol,
        timeframe=Timeframe.H1,
        open_time=T0.add_ms(index * H1_MS),
        open=Price(Decimal(str(o))),
        high=Price(Decimal(str(h))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(c))),
        volume=Volume(Decimal(100)),
        is_closed=True,
        quality=QualityScore(1.0),
    )


def fired(
    index: int,
    symbol: str,
    *,
    entry: float,
    stop: float,
    targets: tuple[float, ...],
    direction: str = "long",
) -> DecisionRecord:
    return DecisionRecord(
        exchange="toobit",
        symbol=symbol,
        timeframe=Timeframe.H1,
        bar_open_time=T0.add_ms(index * H1_MS),
        action="signal",
        direction=direction,
        setup="Momentum Breakout",
        probability=0.85,
        uncertainty=0.2,
        expected_r=1.2,
        contributors=9,
        failed_gates=(),
        entry=entry,
        stop=stop,
        targets=targets,
        computed_at=T0,
    )


def settings(**overrides: object) -> PortfolioSettings:
    section: dict[str, object] = {
        "portfolio_id": "default",
        "base_currency": "USDT",
        "account": {"initial_capital": "10000", "risk_fraction": 0.01},
        "caps": {},
        "kelly": {},
    }
    caps = overrides.pop("caps", None)
    if caps is not None:
        section["caps"] = caps
    section.update(overrides)
    return portfolio_settings(section)  # type: ignore[arg-type]


def engine(**overrides: object) -> PortfolioEngine:
    return PortfolioEngine(settings=settings(**overrides), clock=ManualClock(T0))


class TestConfig:
    def test_defaults_parse(self) -> None:
        parsed = portfolio_settings({"schema_version": 1})
        assert parsed.portfolio_id == "default"
        assert parsed.account.initial_capital == Decimal(10_000)
        assert parsed.caps.max_open_positions == 4
        assert parsed.kelly.cap == 0.25

    def test_capital_is_exact(self) -> None:
        parsed = portfolio_settings(
            {"account": {"initial_capital": "12345.67"}}
        )
        assert parsed.account.initial_capital == Decimal("12345.67")

    def test_float_capital_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            portfolio_settings({"account": {"initial_capital": 1.5}})

    def test_invalid_fraction_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            portfolio_settings({"account": {"risk_fraction": 0.5}})

    def test_daily_cannot_exceed_weekly(self) -> None:
        with pytest.raises(ConfigurationError):
            portfolio_settings(
                {"caps": {"daily_loss_limit_fraction": 0.1,
                          "weekly_loss_limit_fraction": 0.05}}
            )


class TestLedger:
    def lot(self, *, direction: Direction = Direction.LONG) -> OpenLot:
        entry, stop, target = (
            (Decimal(102), Decimal(100), Decimal(106))
            if direction is Direction.LONG
            else (Decimal(102), Decimal(104), Decimal(98))
        )
        return open_lot(
            bar=make_bar(2, 101, 102.5, 100.5, 102),
            timeframe=Timeframe.H1,
            direction=direction,
            entry=entry,
            stop=stop,
            target=target,
            quantity=Decimal(50),
            risk_amount=Money(currency="USDT", amount=Decimal(100)),
            entry_index=2,
        )

    def test_sizing_is_risk_fraction_over_stop(self) -> None:
        quantity = size_position(Decimal(10_000), 0.01, Decimal(2))
        assert quantity == Decimal(50)

    def test_entry_bar_never_closes(self) -> None:
        lot = self.lot()
        assert close_lot(
            lot, make_bar(2, 101, 107, 99, 102), conservative=True, currency="USDT"
        ) is None

    def test_target_close_realizes_exact_pnl(self) -> None:
        lot = self.lot()
        closed = close_lot(
            lot, make_bar(3, 104, 106.5, 103, 105), conservative=True, currency="USDT"
        )
        assert closed is not None
        position, trade = closed
        assert position.status is PositionStatus.CLOSED
        assert position.object_version == 2  # evolved lineage
        assert trade.realized_pnl.amount == Decimal(200)  # 50 x 4 points
        assert trade.realized_r == pytest.approx(2.0)
        assert trade.reason == "target"

    def test_stop_close_costs_exactly_the_risk(self) -> None:
        lot = self.lot()
        closed = close_lot(
            lot, make_bar(3, 101, 101.5, 99.5, 100), conservative=True, currency="USDT"
        )
        assert closed is not None
        _, trade = closed
        assert trade.realized_pnl.amount == Decimal(-100)
        assert trade.realized_r == pytest.approx(-1.0)

    def test_collision_is_conservative(self) -> None:
        lot = self.lot()
        closed = close_lot(
            lot, make_bar(3, 102, 107, 99, 103), conservative=True, currency="USDT"
        )
        assert closed is not None
        assert closed[1].reason == "stop"

    def test_fee_rate_charges_both_notionals(self) -> None:
        lot = self.lot()
        closed = close_lot(
            lot, make_bar(3, 104, 106.5, 103, 105), conservative=True,
            currency="USDT", fee_rate=Decimal("0.001"),
        )
        assert closed is not None
        _, trade = closed
        # Gross 200; fees = (102 + 106) x 50 x 0.001 = 10.4.
        assert trade.realized_pnl.amount == Decimal("189.6")
        assert trade.realized_r == pytest.approx(2.0)  # geometry unchanged

    def test_short_side_mirrors(self) -> None:
        lot = self.lot(direction=Direction.SHORT)
        closed = close_lot(
            lot, make_bar(3, 100, 100.5, 97.5, 98), conservative=True, currency="USDT"
        )
        assert closed is not None
        _, trade = closed
        assert trade.realized_pnl.amount == Decimal(200)  # short 4 points x 50
        assert trade.reason == "target"


class TestAccount:
    def test_windows_roll_on_boundaries(self) -> None:
        account = AccountFold(base_currency="USDT", initial_capital=Decimal(10_000))
        start = day_key(T0.epoch_ms) * 86_400_000  # aligned midnight
        account.roll_windows(start, Decimal(10_000))
        account.day_realized = Decimal(-100)
        account.roll_windows(start + 3_600_000, Decimal(9_900))  # same day
        assert account.day_realized == Decimal(-100)
        account.roll_windows(start + 86_400_000, Decimal(9_900))  # next day
        assert account.day_realized == Decimal(0)
        assert account.day_start_equity == Decimal(9_900)

    def test_week_key_is_monday_aligned(self) -> None:
        monday = 19_723 * 86_400_000  # 2024-01-01 was a Monday
        sunday = monday - 86_400_000
        assert week_key(monday) == week_key(monday + 6 * 86_400_000)
        assert week_key(sunday) != week_key(monday)

    def test_loss_fraction_and_drawdown(self) -> None:
        account = AccountFold(base_currency="USDT", initial_capital=Decimal(10_000))
        account.roll_windows(T0.epoch_ms, Decimal(10_000))
        account.day_realized = Decimal(-250)
        assert account.window_loss_fraction(weekly=False) == pytest.approx(0.025)
        account.mark(Decimal(10_500))
        account.mark(Decimal(9_975))
        assert account.current_drawdown == pytest.approx(0.05)
        assert account.max_drawdown == pytest.approx(0.05)

    def test_constrained_kelly_is_capped(self) -> None:
        stats = TradeStatistics(
            trades=20, wins=14, losses=6, r_sum=20.0,
            average_win_r=2.5, average_loss_r=-1.0, consecutive_losses=0,
        )
        kelly = constrained_kelly(
            stats, multiplier=0.5, cap=0.25, minimum_trades=12, fallback=0.01
        )
        assert kelly == 0.25  # raw 0.58 halved to 0.29, capped
        thin = TradeStatistics(trades=5, wins=3, losses=2, r_sum=2.0,
                               average_win_r=1.5, average_loss_r=-1.0,
                               consecutive_losses=0)
        assert constrained_kelly(
            thin, multiplier=0.5, cap=0.25, minimum_trades=12, fallback=0.01
        ) == 0.01


class TestExposure:
    def test_view_marks_to_last_close(self) -> None:
        lot = TestLedger().lot()
        view = exposure_view([lot], {"BTCUSDT": Decimal(110)})
        assert view.by_symbol["BTCUSDT"] == Decimal(5_500)  # 50 x 110
        assert view.gross_notional == Decimal(5_500)
        assert view.open_positions == 1
        assert unrealized_pnl([lot], {"BTCUSDT": Decimal(110)}) == Decimal(400)

    def test_correlation_needs_full_window(self) -> None:
        closes = [100.0 + i for i in range(30)]
        assert rolling_return_correlation(closes, closes, 50) is None
        long_closes = [100.0 * 1.01 ** i for i in range(60)]
        rho = rolling_return_correlation(long_closes, long_closes, 50)
        assert rho is not None and rho == pytest.approx(1.0)


class TestGovernance:
    def context(self, **overrides: object) -> AdmissionContext:
        base: dict[str, object] = {
            "positions_open": 0,
            "positions_in_symbol": 0,
            "day_loss_fraction": 0.0,
            "week_loss_fraction": 0.0,
            "consecutive_losses": 0,
            "correlated_symbols": (),
        }
        base.update(overrides)
        return AdmissionContext(**base)  # type: ignore[arg-type]

    def test_clean_context_is_approved(self) -> None:
        assert admission_failures(self.context(), PortfolioCaps()) == ()

    def test_each_binary_cap_rejects_with_its_code(self) -> None:
        caps = PortfolioCaps()
        cases = {
            "max_open_positions": self.context(positions_open=4),
            "symbol_occupied": self.context(positions_in_symbol=1),
            "daily_loss_limit": self.context(day_loss_fraction=0.02),
            "weekly_loss_limit": self.context(week_loss_fraction=0.05),
            "consecutive_losses": self.context(consecutive_losses=4),
            "correlated_exposure": self.context(correlated_symbols=("BTCUSDT",)),
        }
        for code, context in cases.items():
            assert code in admission_failures(context, caps), code

    def test_headroom_is_the_binding_exposure_room(self) -> None:
        caps = PortfolioCaps()  # symbol 35%, gross 100%
        empty = exposure_view([], {})
        assert exposure_headroom(
            "ETHUSDT", empty, Decimal(10_000), caps
        ) == Decimal("3500.0")
        btc_lot = TestLedger().lot()  # 50 BTC units
        held = exposure_view([btc_lot], {"BTCUSDT": Decimal(180)})  # 9000 gross
        assert exposure_headroom(
            "ETHUSDT", held, Decimal(10_000), caps
        ) == Decimal("1000.0")  # gross cap binds before the symbol cap
        assert exposure_headroom(
            "ETHUSDT", held, Decimal(0), caps
        ) == Decimal(0)


class TestEngineFold:
    def stream(
        self,
        symbol: str,
        prices: list[tuple[float, float, float, float]],
        decisions: tuple[DecisionRecord, ...],
    ) -> SeriesStream:
        bars = tuple(
            make_bar(i, o, h, low, c, symbol)
            for i, (o, h, low, c) in enumerate(prices)
        )
        return SeriesStream(
            symbol=symbol, timeframe=Timeframe.H1, bars=bars, decisions=decisions
        )

    def rising(self, symbol: str = "BTCUSDT") -> SeriesStream:
        prices = [(100.0 + i, 101.5 + i, 99.5 + i, 101.0 + i) for i in range(10)]
        record = fired(2, symbol, entry=103.0, stop=101.0, targets=(104.0, 105.0, 107.0))
        return self.stream(symbol, prices, (record,))

    def wide(self) -> dict[str, object]:
        """Caps wide enough that risk-fraction sizing stays unshaped."""
        return {"max_symbol_exposure_fraction": 1.0}

    def test_target_run_realizes_the_win(self) -> None:
        fold = engine(caps=self.wide()).fold_streams([self.rising()]).unwrap()
        assert len(fold.closed_trades) == 1
        trade = fold.closed_trades[0]
        assert trade.reason == "target"
        assert trade.realized_r == pytest.approx(2.0)
        assert trade.realized_pnl.amount == Decimal(200)  # 50 units x 4
        assert fold.final.equity.amount == Decimal(10_200)
        assert fold.final.realized_pnl.amount == Decimal(200)
        assert not fold.open_positions
        assert fold.statistics.trades == 1 and fold.statistics.wins == 1

    def test_stop_run_costs_the_risk_fraction(self) -> None:
        prices = [(100.0, 101.5, 99.5, 101.0)] * 3 + [
            (101.0, 101.2, 97.0, 98.0)
        ] + [(98.0, 99.0, 97.5, 98.5)] * 3
        record = fired(1, "BTCUSDT", entry=101.0, stop=99.0, targets=(102.0, 103.0, 105.0))
        fold = engine(caps=self.wide()).fold_streams(
            [self.stream("BTCUSDT", prices, (record,))]
        ).unwrap()
        assert len(fold.closed_trades) == 1
        assert fold.closed_trades[0].realized_r == pytest.approx(-1.0)
        assert fold.final.equity.amount == Decimal(9_900)  # exactly -1%
        assert fold.final.current_drawdown.value == pytest.approx(0.01)

    def test_open_position_survives_the_fold(self) -> None:
        prices = [(100.0 + i * 0.1, 100.6 + i * 0.1, 99.9 + i * 0.1, 100.5 + i * 0.1)
                  for i in range(6)]
        record = fired(2, "BTCUSDT", entry=100.7, stop=99.7, targets=(101.7, 102.7, 104.7))
        fold = engine(caps=self.wide()).fold_streams(
            [self.stream("BTCUSDT", prices, (record,))]
        ).unwrap()
        assert len(fold.open_positions) == 1
        assert not fold.closed_trades
        assert fold.final.position_count == 1
        assert fold.final.total_exposure.amount > 0

    def test_max_positions_cap_rejects_the_second_series(self) -> None:
        first = self.rising("BTCUSDT")
        eth_prices = [(50.0 + i, 50.8 + i, 49.8 + i, 50.5 + i) for i in range(10)]
        eth_record = fired(4, "ETHUSDT", entry=54.5, stop=53.5, targets=(55.5, 56.5, 58.5))
        second = self.stream("ETHUSDT", eth_prices, (eth_record,))
        fold = (
            engine(caps={"max_open_positions": 1})
            .fold_streams([first, second])
            .unwrap()
        )
        assert len(fold.rejections) == 1
        rejection = fold.rejections[0]
        assert rejection.symbol == "ETHUSDT"
        assert "max_open_positions" in rejection.reasons

    def test_exposure_headroom_reduces_the_size(self) -> None:
        # Default 35% symbol cap: 50 units x 103 = 5150 notional exceeds
        # 3500 -> the trade opens reduced, not rejected (Book II 21.29).
        fold = engine().fold_streams([self.rising()]).unwrap()
        assert not fold.rejections
        assert len(fold.closed_trades) == 1
        trade = fold.closed_trades[0]
        assert trade.quantity < Decimal(50)
        assert trade.quantity * trade.entry <= Decimal(3_500)
        assert trade.realized_r == pytest.approx(2.0)  # geometry unchanged

    def test_fold_is_deterministic(self) -> None:
        streams = [self.rising()]
        first = engine(caps=self.wide()).fold_streams(streams).unwrap()
        second = engine(caps=self.wide()).fold_streams(streams).unwrap()
        assert first.final.equity == second.final.equity
        assert [t.realized_r for t in first.closed_trades] == [
            t.realized_r for t in second.closed_trades
        ]
        assert len(first.snapshots) == len(second.snapshots)

    def test_duplicate_stream_fails_with_code(self) -> None:
        result = engine().fold_streams([self.rising(), self.rising()])
        assert not result.ok
        assert result.error is not None and result.error.code == "PRT-001"


def zone(price: float) -> PriceZone:
    value = Price(Decimal(str(price)))
    return PriceZone(lower=value, upper=value)


def make_signal(symbol: str = "ETHUSDT", stop: float = 96.0) -> Signal:
    return Signal(
        created_at=T0,
        exchange="toobit",
        symbol=symbol,
        timeframe=Timeframe.H1,
        direction=Direction.LONG,
        probability=Probability(0.8),
        confidence=Confidence(0.6),
        entry_zone=zone(100.0),
        stop_zone=zone(stop),
        target_zones=(zone(102.0), zone(107.0), zone(110.5)),
    )


def snapshot_with(
    positions: tuple[Position, ...] = (), drawdown: float = 0.0
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        created_at=T0,
        as_of=T0,
        base_currency="USDT",
        equity=Money(currency="USDT", amount=Decimal(10_000)),
        cash=Money(currency="USDT", amount=Decimal(10_000)),
        total_exposure=Money(currency="USDT", amount=Decimal(0)),
        unrealized_pnl=Money(currency="USDT", amount=Decimal(0)),
        realized_pnl=Money(currency="USDT", amount=Decimal(0)),
        current_drawdown=Drawdown(drawdown),
        open_positions=positions,
    )


class TestAdmissionContract:
    def test_balanced_verdict_sizes_by_risk_fraction(self) -> None:
        assessment = asyncio.run(
            engine().assess(make_signal(), snapshot_with())
        ).unwrap()
        assert assessment.risk_mode is RiskMode.BALANCED
        assert assessment.position_size.value == Decimal(25)  # 100 / 4
        assert assessment.expected_loss.amount == Decimal(100)
        assert assessment.tail_loss.amount == Decimal(300)
        assert assessment.kelly_fraction.value == pytest.approx(0.01)
        assert assessment.max_exposure.amount == Decimal("3500.0")
        assert assessment.is_tradeable

    def test_tight_stop_is_reduced_to_the_headroom(self) -> None:
        assessment = asyncio.run(
            engine().assess(make_signal(stop=98.0), snapshot_with())
        ).unwrap()
        assert assessment.risk_mode is RiskMode.BALANCED
        assert assessment.position_size.value == Decimal(35)  # 3500 / 100
        assert assessment.expected_loss.amount == Decimal(70)

    def test_statistics_inform_the_kelly_fraction(self) -> None:
        stats = TradeStatistics(
            trades=20, wins=12, losses=8, r_sum=16.0,
            average_win_r=2.0, average_loss_r=-1.0, consecutive_losses=0,
        )
        assessment = asyncio.run(
            engine().assess(make_signal(), snapshot_with(), statistics=stats)
        ).unwrap()
        assert assessment.kelly_fraction.value == pytest.approx(0.2)

    def test_occupied_symbol_halts(self) -> None:
        lot = TestLedger().lot()  # BTCUSDT position
        assessment = asyncio.run(
            engine().assess(
                make_signal("BTCUSDT"), snapshot_with(positions=(lot.position,))
            )
        ).unwrap()
        assert assessment.risk_mode is RiskMode.HALTED
        # Quantity is strictly positive: the verdict reports the
        # plan-consistent size; HALTED carries the veto.
        assert assessment.position_size.value > 0
        assert not assessment.is_tradeable

    def test_drawdown_turns_defensive(self) -> None:
        assessment = asyncio.run(
            engine().assess(make_signal(), snapshot_with(drawdown=0.06))
        ).unwrap()
        assert assessment.risk_mode is RiskMode.DEFENSIVE


class TestStore:
    def test_roundtrip_and_statistics(self, tmp_path: Path) -> None:
        asyncio.run(self._roundtrip(tmp_path))

    async def _roundtrip(self, tmp_path: Path) -> None:
        store = SqlitePortfolioRepository(database_path=tmp_path / "portfolio.sqlite")
        await store.open()
        try:
            position = PositionRecord(
                portfolio_id="default", exchange="toobit", symbol="BTCUSDT",
                timeframe=Timeframe.H1, entry_bar_time=T0, position_id="p1",
                lineage_id="l1", direction="long", quantity=Decimal(50),
                entry=Decimal(102), stop=Decimal(100), target=Decimal(106),
                risk_amount=Decimal(100), opened_at=T0.add_ms(H1_MS),
                status="closed", closed_at=T0.add_ms(5 * H1_MS),
                exit_price=Decimal(106), realized_pnl=Decimal(200),
                realized_r=2.0, close_reason="target",
            )
            await store.upsert_positions([position])
            await store.upsert_positions([position])  # idempotent
            stored = await store.get_positions("default")
            assert len(stored) == 1
            assert stored[0].quantity == Decimal(50)
            assert stored[0].realized_pnl == Decimal(200)

            snapshot = SnapshotRecord(
                portfolio_id="default", as_of=T0.add_ms(5 * H1_MS),
                equity=Decimal(10_200), cash=Decimal(10_200),
                gross_exposure=Decimal(0), unrealized_pnl=Decimal(0),
                realized_pnl=Decimal(200), drawdown=0.0, open_positions=0,
            )
            await store.upsert_snapshots([snapshot])
            snapshots = await store.get_snapshots("default")
            assert len(snapshots) == 1 and snapshots[0].equity == Decimal(10_200)

            rejection = RejectionRecord(
                portfolio_id="default", exchange="toobit", symbol="ETHUSDT",
                timeframe=Timeframe.H1, bar_open_time=T0,
                reasons=("max_open_positions",),
            )
            await store.upsert_rejections([rejection])
            rejections = await store.get_rejections("default")
            assert rejections[0].reasons == ("max_open_positions",)

            statistics = await store.statistics("default")
            assert statistics.trades == 1 and statistics.wins == 1
            assert statistics.average_win_r == pytest.approx(2.0)

            await store.clear("default")
            assert await store.get_positions("default") == []
            assert await store.get_snapshots("default") == []
        finally:
            await store.close()

    def test_streak_counts_trailing_losses(self, tmp_path: Path) -> None:
        asyncio.run(self._streak(tmp_path))

    async def _streak(self, tmp_path: Path) -> None:
        store = SqlitePortfolioRepository(database_path=tmp_path / "portfolio.sqlite")
        await store.open()
        try:
            def closed(index: int, *, win: bool) -> PositionRecord:
                return PositionRecord(
                    portfolio_id="default", exchange="toobit", symbol="BTCUSDT",
                    timeframe=Timeframe.H1, entry_bar_time=T0.add_ms(index * H1_MS),
                    position_id=f"p{index}", lineage_id=f"l{index}",
                    direction="long", quantity=Decimal(1), entry=Decimal(100),
                    stop=Decimal(99), target=Decimal(103), risk_amount=Decimal(1),
                    opened_at=T0.add_ms(index * H1_MS),
                    status="closed", closed_at=T0.add_ms((index + 2) * H1_MS),
                    exit_price=Decimal(103) if win else Decimal(99),
                    realized_pnl=Decimal(3) if win else Decimal(-1),
                    realized_r=3.0 if win else -1.0,
                    close_reason="target" if win else "stop",
                )

            await store.upsert_positions(
                [closed(0, win=True), closed(1, win=False), closed(2, win=False)]
            )
            statistics = await store.statistics("default")
            assert statistics.consecutive_losses == 2
            assert statistics.losses == 2
        finally:
            await store.close()


class TestPlugin:
    def test_manifest_requires_the_decision_platform(self) -> None:
        from apex.portfolio.plugin import APEX_PLUGIN

        manifest = APEX_PLUGIN.manifest
        assert manifest.name == "portfolio_platform"
        assert "decision_platform" in manifest.requires
