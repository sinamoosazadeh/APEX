"""Decision platform: setups, gating, timing, signal construction, store."""

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from apex.contracts.engines import DecisionSnapshot, IDecisionEngine
from apex.core.context import MarketContext
from apex.core.enums import Direction, Timeframe
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, QualityScore, Volume
from apex.decision.kernel import (
    TIMING_IMMEDIATE,
    CentralDecisionKernel,
    DecisionOutcome,
    DecisionParams,
)
from apex.decision.setups import classify_long
from apex.decision.store import DecisionRecord, SqliteDecisionRepository
from apex.domain.market import Bar

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

PARAMS = DecisionParams(
    execution_timing=TIMING_IMMEDIATE,
    cooldown_bars=3,
    atr_length=3,
    ema_length=3,
    micro_bos_length=2,
    rvol_gate_enabled=False,
    similarity_cooldown_enabled=False,
)


def make_bar(index: int, o: float, h: float, low: float, c: float) -> Bar:
    return Bar(
        exchange="toobit",
        symbol="BTCUSDT",
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


def bullish_vector() -> dict[str, float]:
    return {
        "structure.bos_up": 1.0,
        "structure.choch_up": 1.0,
        "structure.is_displacement": 1.0,
        "structure.sweep_low": 1.0,
        "structure.in_discount": 1.0,
        "structure.equal_lows": 1.0,
        "orderblocks.in_bull_ob": 1.0,
        "orderblocks.in_bull_fvg": 1.0,
        "orderblocks.bull_fvg_count": 2.0,
        "orderblocks.bull_breaker": 0.0,
        "volume.rvol": 2.0,
        "volume.volume_available": 1.0,
        "volume.expansion": 1.0,
        "volume.compression": 0.0,
        "volume.adaptive_atr_ratio": 1.0,
        "volume.selling_climax": 1.0,
        "htf.alignment": 2.0,
        "statistical.is_trending": 1.0,
        "statistical.is_ranging": 0.0,
        "statistical.return_entropy": 0.2,
        "statistical.market_entropy": 0.2,
        "statistical.volatility_clustering": 0.0,
        "statistical.direction": 1.0,
        "statistical.pin_bull": 1.0,
        "statistical.bull_engulfing": 1.0,
        "statistical.hammer": 0.0,
    }


def strong_channels() -> dict[str, float]:
    channels: dict[str, float] = {}
    for name in (
        "structure", "liquidity", "orderblock", "fvg", "zone", "dna",
        "kinetic", "delta", "sequence", "trend", "mtf", "smt", "profile",
    ):
        channels[f"{name}_long"] = 0.8
        channels[f"{name}_short"] = 0.05
    return channels


def snapshot(
    index: int,
    *,
    probability_long: float = 0.85,
    probability_short: float = 0.05,
    vector: dict[str, float] | None = None,
    channels: dict[str, float] | None = None,
) -> DecisionSnapshot:
    base = 100.0 + index
    return DecisionSnapshot(
        bar=make_bar(index, base, base + 2.2, base - 0.4, base + 2.0),
        vector=vector if vector is not None else bullish_vector(),
        probability_long=probability_long,
        probability_short=probability_short,
        channels=channels if channels is not None else strong_channels(),
        macro_high=base + 30.0,
        macro_low=base - 30.0,
    )


def kernel(params: DecisionParams = PARAMS) -> CentralDecisionKernel:
    return CentralDecisionKernel(params=params, clock=ManualClock(T0))


def context() -> MarketContext:
    return MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)


def decide(
    snapshots: list[DecisionSnapshot], params: DecisionParams = PARAMS
) -> tuple[DecisionOutcome, ...]:
    return kernel(params).decide_series(snapshots, context()).unwrap()


class TestSetupTaxonomy:
    def test_institutional_long_takes_priority(self) -> None:
        name = classify_long(
            bullish_vector(), strong_channels(), previous_compression=False
        )
        assert name == "SMT Turtle Soup Long"

    def test_priority_falls_through_without_smt(self) -> None:
        channels = strong_channels()
        channels["smt_long"] = 0.0
        name = classify_long(bullish_vector(), channels, previous_compression=False)
        assert name == "Institutional Long"

    def test_confluence_fallback(self) -> None:
        name = classify_long({}, {}, previous_compression=False)
        assert name == "Confluence Long"


class TestKernelSignals:
    def test_strong_confluence_fires_a_long_signal(self) -> None:
        outcomes = decide([snapshot(i) for i in range(8)])
        fired = [outcome for outcome in outcomes if outcome.action == "signal"]
        assert fired
        first = fired[0]
        assert first.direction is Direction.LONG
        assert first.signal is not None
        assert first.setup == "SMT Turtle Soup Long"
        assert not first.failed_gates

    def test_signal_carries_coherent_entry_context(self) -> None:
        outcomes = decide([snapshot(i) for i in range(4)])
        fired = [outcome for outcome in outcomes if outcome.action == "signal"]
        assert fired
        signal = fired[0].signal
        assert signal is not None
        entry = float(signal.entry_zone.lower.value)
        stop = float(signal.stop_zone.lower.value)
        targets = [float(zone.lower.value) for zone in signal.target_zones]
        assert stop < entry  # long stop below entry
        assert targets[0] < targets[1] < targets[2]
        assert all(target > entry for target in targets)
        risk = entry - stop
        assert targets[1] == pytest.approx(entry + risk * PARAMS.base_risk_reward)

    def test_cooldown_blocks_the_next_signal(self) -> None:
        outcomes = decide([snapshot(i) for i in range(5)])
        fired_indexes = [
            index for index, outcome in enumerate(outcomes)
            if outcome.action == "signal"
        ]
        assert fired_indexes
        first = fired_indexes[0]
        assert outcomes[first + 1].action != "signal"
        assert "cooldown" in outcomes[first + 1].failed_gates

    def test_weak_probability_stands_aside(self) -> None:
        weak = [
            snapshot(i, probability_long=0.2, probability_short=0.1)
            for i in range(2)
        ]
        outcomes = decide(weak)
        assert all(outcome.action == "stand_aside" for outcome in outcomes)

    def test_htf_opposition_vetoes_with_reason(self) -> None:
        vector = bullish_vector()
        vector["htf.alignment"] = -2.0
        outcomes = decide([snapshot(0, vector=vector)])
        assert outcomes[0].action == "veto"
        assert "htf_permission" in outcomes[0].failed_gates

    def test_contract_satisfied(self) -> None:
        assert isinstance(kernel(), IDecisionEngine)

    def test_deterministic(self) -> None:
        first = decide([snapshot(i) for i in range(4)])
        second = decide([snapshot(i) for i in range(4)])
        assert [outcome.action for outcome in first] == [
            outcome.action for outcome in second
        ]

    def test_invalid_params_are_rejected(self) -> None:
        with pytest.raises(Exception, match="timing"):
            DecisionParams(execution_timing="warp_speed")


class TestPendingStateMachine:
    def test_retest_mode_waits_for_confirmation(self) -> None:
        params = DecisionParams(
            cooldown_bars=3,
            atr_length=3,
            ema_length=3,
            micro_bos_length=2,
            rvol_gate_enabled=False,
            similarity_cooldown_enabled=False,
        )
        # Readiness fires on bar 2 (post ATR warmup) then drops below
        # the threshold: pending stays armed (AICE re-arms while ready,
        # so age only grows once readiness lapses) and confirms on the
        # next trigger candle within the pending window.
        snapshots = [snapshot(i) for i in range(3)]
        snapshots += [
            snapshot(i, probability_long=0.60, probability_short=0.05)
            for i in range(3, 6)
        ]
        outcomes = decide(snapshots, params)
        fired_indexes = [
            index for index, outcome in enumerate(outcomes)
            if outcome.action == "signal"
        ]
        assert fired_indexes
        first = fired_indexes[0]
        # Fired from pending after the arming bar, below full readiness.
        assert first >= 3
        assert outcomes[first].probability == pytest.approx(0.60)


class TestDecisionStore:
    def test_roundtrip_and_idempotency(self, tmp_path: Path) -> None:
        asyncio.run(self._roundtrip(tmp_path))

    async def _roundtrip(self, tmp_path: Path) -> None:
        repository = SqliteDecisionRepository(database_path=tmp_path / "d.sqlite")
        await repository.open()
        try:
            record = DecisionRecord(
                exchange="toobit",
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                bar_open_time=T0,
                action="signal",
                direction="long",
                setup="Institutional Long",
                probability=0.81,
                uncertainty=0.22,
                expected_r=1.4,
                contributors=9,
                failed_gates=(),
                entry=101.5,
                stop=99.0,
                targets=(103.0, 105.0, 108.0),
                computed_at=T0,
            )
            assert await repository.upsert([record]) == 1
            assert await repository.upsert([record]) == 1
            assert await repository.count("toobit", "BTCUSDT", Timeframe.H1) == 1
            assert (
                await repository.count(
                    "toobit", "BTCUSDT", Timeframe.H1, action="signal"
                )
                == 1
            )
            rows = await repository.get_range(
                "toobit", "BTCUSDT", Timeframe.H1,
                start=Timestamp(epoch_ms=0), end=Timestamp(epoch_ms=10**14),
            )
            assert rows == [record]
        finally:
            await repository.close()
