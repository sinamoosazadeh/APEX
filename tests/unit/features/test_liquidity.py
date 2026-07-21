"""Liquidity family: pools, equals, proximity, sweeps, inducement."""

import io
from decimal import Decimal

import pytest
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Volume
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.liquidity.definitions import liquidity_definitions
from apex.features.liquidity.engine import (
    FEATURE_NAMES,
    LiquidityEngine,
    LiquidityParams,
)
from apex.features.registry import FeatureRegistry

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Small, fast parameters: warmup = max(3, 2*3+1, 5) = 7 bars.
PARAMS = LiquidityParams(
    chart_lookback=2,
    internal_lookback=1,
    external_lookback=3,
    atr_length=3,
    equal_tolerance_atr=0.10,
    liquidity_decay=0.9,
    ema_length=5,
)


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.liquidity")


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


def dull_bar(index: int) -> Bar:
    """A quiet bar around 100 with no pivot-worthy extremes."""
    return make_bar(index, 100.0, 101.5, 99.0, 100.5)


def compute(bars: list[Bar]) -> list[Feature]:
    engine = LiquidityEngine(params=PARAMS, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    return list(engine.compute(bars, context).unwrap())


def value_of(features: list[Feature], name: str, index: int) -> float:
    anchor = T0.add_ms(index * H1_MS)
    for feature in features:
        if feature.name == name and feature.bar_open_time == anchor:
            return float(feature.value)
    raise AssertionError(f"{name} not found at bar {index}")


def pool_scenario() -> list[Bar]:
    """Equal internal lows at 8/11, chart equal at 13, sweep at 15.

    - V-lows 95.00 (index 8) and 95.02 (index 11) within ATR tolerance;
    - internal (lb=1) confirms them at 9 and 12 -> internal equal at 12;
    - chart (lb=2) confirms them at 10 and 13 -> chart equal at 13;
    - index 15 wicks below the chart swing low and closes back above.
    """
    bars = [dull_bar(i) for i in range(20)]
    bars[8] = make_bar(8, 100.0, 101.5, 95.0, 100.5)
    bars[11] = make_bar(11, 100.0, 101.5, 95.02, 100.5)
    bars[15] = make_bar(15, 100.0, 101.5, 94.5, 100.5)
    return bars


class TestLiquidityPools:
    def test_equal_lows_bump_pool_with_scale_priority(self) -> None:
        features = compute(pool_scenario())
        # Internal scale confirms the equal pair first.
        assert value_of(features, "liquidity.equal_lows_internal", 12) == 1.0
        assert value_of(features, "liquidity.pool_low_confidence", 12) == pytest.approx(
            0.25
        )
        # Chart scale confirms one bar later: decay then chart bump.
        expected_13 = 0.25 * 0.9 + 0.35
        assert value_of(features, "liquidity.pool_low_confidence", 13) == pytest.approx(
            expected_13
        )
        # Pure decay on the following bar.
        assert value_of(features, "liquidity.pool_low_confidence", 14) == pytest.approx(
            expected_13 * 0.9
        )
        # The high-side pool never accumulated (all highs equal, no pivots).
        assert value_of(features, "liquidity.pool_high_confidence", 14) == 0.0

    def test_sweep_resets_pool_and_flags_inducement(self) -> None:
        features = compute(pool_scenario())
        # Index 15 sweeps the chart swing low (wick below, close above).
        assert value_of(features, "liquidity.sweep_low_efficiency", 15) > 0.5
        assert value_of(features, "liquidity.pool_low_confidence", 15) == 0.0
        # Trend never turned bearish and internal bias is bullish -> inducement.
        assert value_of(features, "liquidity.inducement_long", 15) == 1.0
        assert value_of(features, "liquidity.inducement_short", 15) == 0.0
        # No chart equal printed at the sweep bar -> not a stop hunt.
        assert value_of(features, "liquidity.stop_hunt_low", 15) == 0.0

    def test_resting_liquidity_composite(self) -> None:
        features = compute(pool_scenario())
        # At bar 13 the external window (3*8=24) is still incomplete,
        # so proximity is 0 and resting = pool * 0.35 exactly.
        pool_13 = value_of(features, "liquidity.pool_low_confidence", 13)
        assert value_of(features, "liquidity.resting_low", 13) == pytest.approx(
            pool_13 * 0.35
        )

    def test_normalization_bounds(self) -> None:
        features = compute(pool_scenario())
        for feature in features:
            assert -1.0 <= feature.normalized_value <= 1.0


class TestExternalProximity:
    def test_proximity_rises_near_the_external_extreme(self) -> None:
        # external_lookback=1 -> extreme window is the previous 8 bars.
        params = LiquidityParams(
            chart_lookback=2,
            internal_lookback=1,
            external_lookback=1,
            atr_length=3,
            equal_tolerance_atr=0.10,
            liquidity_decay=0.9,
            ema_length=5,
        )
        bars = [dull_bar(i) for i in range(14)]
        bars[9] = make_bar(9, 100.0, 106.0, 99.0, 100.5)  # prior extreme high
        bars[13] = make_bar(13, 104.5, 106.0, 104.0, 105.8)  # close approaches it
        engine = LiquidityEngine(params=params, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        features = list(engine.compute(bars, context).unwrap())
        far = value_of(features, "liquidity.external_high_proximity", 11)
        near = value_of(features, "liquidity.external_high_proximity", 13)
        assert near > far
        assert near > 0.9  # close sits within a fraction of an ATR


class TestDefinitionsAndRegistry:
    def test_definitions_cover_engine_names(self) -> None:
        registry = FeatureRegistry()
        registry.register_all(liquidity_definitions(PARAMS))
        for name in FEATURE_NAMES:
            assert registry.is_registered(name)

    def test_families_do_not_collide_with_structure(self) -> None:
        from apex.features.structure.definitions import structure_definitions
        from apex.features.structure.engine import StructureParams

        registry = FeatureRegistry()
        registry.register_all(structure_definitions(StructureParams()))
        registry.register_all(liquidity_definitions(PARAMS))
        assert registry.families == ("liquidity", "structure")

    def test_forming_bar_rejected(self) -> None:
        from dataclasses import replace

        bars = [dull_bar(i) for i in range(9)]
        bars[-1] = replace(bars[-1], is_closed=False)
        engine = LiquidityEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "DAT-004"
