"""Statistical family: regime, candle DNA, patterns, kinetic oscillators."""

from decimal import Decimal

import pytest
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Volume
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.registry import FeatureRegistry
from apex.features.statistical.definitions import statistical_definitions
from apex.features.statistical.engine import (
    FEATURE_NAMES,
    StatisticalEngine,
    StatisticalParams,
)

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Small, fast parameters: warmup = max(3, 6, 5, 8, 10, 10, 3, 12, 7, 4, 5) = 12.
PARAMS = StatisticalParams(
    atr_length=3,
    adx_length=3,
    adx_trend_threshold=23.0,
    efficiency_length=5,
    entropy_window=8,
    normalization_window=10,
    rank_window=10,
    range_sma_length=3,
    wavetrend_channel=3,
    wavetrend_average=4,
    stc_cycle=4,
    stc_fast=3,
    stc_slow=8,
    cci_length=4,
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


def trending_series(count: int) -> list[Bar]:
    """Clean directional grind: every bar closes higher than it opens."""
    bars: list[Bar] = []
    previous = 100.0
    for i in range(count):
        close = previous + 2.0
        bars.append(make_bar(i, previous, close + 0.2, previous - 0.2, close))
        previous = close
    return bars


def choppy_series(count: int) -> list[Bar]:
    """Alternating up/down closes around a flat level (no net progress)."""
    bars: list[Bar] = []
    previous = 100.0
    for i in range(count):
        close = 100.0 + (2.0 if i % 2 == 0 else -2.0)
        low = min(previous, close) - 1.0
        high = max(previous, close) + 1.0
        bars.append(make_bar(i, previous, high, low, close))
        previous = close
    return bars


def compute(bars: list[Bar]) -> list[Feature]:
    engine = StatisticalEngine(params=PARAMS, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    return list(engine.compute(bars, context).unwrap())


def value_of(features: list[Feature], name: str, index: int) -> float:
    open_ms = T0.add_ms(index * H1_MS).epoch_ms
    for feature in features:
        if feature.name == name and feature.bar_open_time.epoch_ms == open_ms:
            return feature.value
    raise AssertionError(f"{name} not emitted for bar {index}")


class TestRegimeDetection:
    def test_grind_reads_as_trending(self) -> None:
        features = compute(trending_series(20))
        assert value_of(features, "statistical.is_trending", 19) == 1.0
        assert value_of(features, "statistical.is_ranging", 19) == 0.0
        assert value_of(features, "statistical.trend_confidence", 19) >= 0.55
        # A monotone path is maximally efficient.
        assert value_of(features, "statistical.efficiency_ratio", 19) == pytest.approx(1.0)
        assert value_of(features, "statistical.slope_quality", 19) > 0.95

    def test_chop_reads_as_ranging(self) -> None:
        features = compute(choppy_series(20))
        assert value_of(features, "statistical.is_trending", 19) == 0.0
        assert value_of(features, "statistical.efficiency_ratio", 19) <= 0.2
        confidence_chop = value_of(features, "statistical.trend_confidence", 19)
        trend_features = compute(trending_series(20))
        confidence_trend = value_of(trend_features, "statistical.trend_confidence", 19)
        assert confidence_chop < confidence_trend

    def test_adx_rises_in_the_trend(self) -> None:
        features = compute(trending_series(20))
        assert value_of(features, "statistical.adx", 19) > 23.0


class TestCandleDna:
    def test_persistent_rally_scores_bullish_dna(self) -> None:
        features = compute(trending_series(20))
        assert value_of(features, "statistical.persistence", 19) == 1.0
        assert value_of(features, "statistical.sequence_bull_bias", 19) == 1.0
        assert value_of(features, "statistical.sequence_bear_bias", 19) == 0.0
        dna_bull = value_of(features, "statistical.dna_bull", 19)
        dna_bear = value_of(features, "statistical.dna_bear", 19)
        assert dna_bull > dna_bear

    def test_pin_bar_and_hammer_fire_on_a_rejection_candle(self) -> None:
        bars = trending_series(14)
        # Long lower wick, tiny body, close near the high.
        base = float(bars[-1].close.value)
        bars.append(make_bar(14, base, base + 0.5, base - 8.0, base + 0.4))
        features = compute(bars)
        assert value_of(features, "statistical.pin_bull", 14) == 1.0
        assert value_of(features, "statistical.hammer", 14) == 1.0
        assert value_of(features, "statistical.pin_bear", 14) == 0.0

    def test_bear_engulfing_detected(self) -> None:
        bars = trending_series(14)
        base = float(bars[-1].close.value)  # previous bar: up body (base-2 -> base)
        bars.append(make_bar(14, base + 0.5, base + 1.0, base - 4.0, base - 3.0))
        features = compute(bars)
        assert value_of(features, "statistical.bear_engulfing", 14) == 1.0
        assert value_of(features, "statistical.bull_engulfing", 14) == 0.0

    def test_doji_detected_on_a_flat_candle(self) -> None:
        bars = trending_series(14)
        base = float(bars[-1].close.value)
        bars.append(make_bar(14, base, base + 2.0, base - 2.0, base + 0.1))
        features = compute(bars)
        assert value_of(features, "statistical.doji", 14) == 1.0


def wave_then_rally_series(count: int) -> list[Bar]:
    """Oscillating chop resolving into a rally: a live oscillator cycle.

    Piecewise-linear paths saturate the double-stochastic (Pine's na
    fallback holds STC at 50); waves keep the cycle range alive.
    """
    from math import sin

    closes: list[float] = [100.0 + 6.0 * sin(0.8 * i) for i in range(count - 8)]
    for _ in range(8):
        closes.append(closes[-1] + 3.0)
    bars: list[Bar] = []
    previous = 100.0
    for i, close in enumerate(closes):
        low = min(previous, close) - 0.3
        high = max(previous, close) + 0.3
        bars.append(make_bar(i, previous, high, low, close))
        previous = close
    return bars


class TestKineticOscillators:
    def test_reversal_rally_reads_kinetically_long(self) -> None:
        features = compute(wave_then_rally_series(24))
        assert value_of(features, "statistical.wavetrend_bull", 23) == 1.0
        assert value_of(features, "statistical.cci", 23) > 0.0
        assert value_of(features, "statistical.kinetic_long", 23) > 0.0
        assert value_of(features, "statistical.stc", 23) > 50.0

    def test_degenerate_cycle_reads_neutral_stc(self) -> None:
        # A constant-slope grind collapses the double-stochastic range;
        # the cycle correctly holds its 50 fallback (Pine nz(st, 50)).
        linear = compute(trending_series(24))
        assert value_of(linear, "statistical.stc", 23) == 50.0

    def test_kinetic_scores_stay_bounded(self) -> None:
        for series in (trending_series(24), choppy_series(24)):
            features = compute(series)
            for index in (18, 23):
                assert 0.0 <= value_of(features, "statistical.kinetic_long", index) <= 1.0
                assert 0.0 <= value_of(features, "statistical.kinetic_short", index) <= 1.0


class TestEngineContract:
    def test_emits_nothing_during_warmup(self) -> None:
        features = compute(trending_series(20))
        first_ms = min(feature.bar_open_time.epoch_ms for feature in features)
        assert first_ms == T0.add_ms(PARAMS.warmup_bars * H1_MS).epoch_ms

    def test_all_names_and_normalized_bounds(self) -> None:
        features = compute(choppy_series(20))
        assert {feature.name for feature in features} == set(FEATURE_NAMES)
        assert all(-1.0 <= feature.normalized_value <= 1.0 for feature in features)

    def test_deterministic_and_causal(self) -> None:
        bars = trending_series(20)
        full = compute(bars)
        short = {(f.name, f.bar_open_time.epoch_ms): f.value for f in compute(bars[:16])}
        for feature in full:
            probe = (feature.name, feature.bar_open_time.epoch_ms)
            if probe in short:
                assert short[probe] == feature.value

    def test_rejects_forming_bars(self) -> None:
        from dataclasses import replace

        bars = trending_series(16)
        bars[-1] = replace(bars[-1], is_closed=False)
        engine = StatisticalEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "DAT-004"

    def test_invalid_params_are_rejected(self) -> None:
        with pytest.raises(Exception, match="adx_length"):
            StatisticalParams(adx_length=0)


class TestDefinitions:
    def test_definitions_cover_engine_names(self) -> None:
        definitions = statistical_definitions(PARAMS)
        assert {d.name for d in definitions} == set(FEATURE_NAMES)
        registry = FeatureRegistry()
        registry.register_all(definitions)
        assert all(d.family == "statistical" for d in definitions)
