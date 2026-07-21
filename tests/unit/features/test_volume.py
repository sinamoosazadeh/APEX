"""Volume family: RVOL, volatility stats, delta, profile, momentum."""

from decimal import Decimal

import pytest
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Volume
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.registry import FeatureRegistry
from apex.features.volume.definitions import volume_definitions
from apex.features.volume.engine import FEATURE_NAMES, VolumeEngine, VolumeParams

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Small, fast parameters: warmup = max(3,3,3,8,5,4,7,11,5) = 11 bars.
PARAMS = VolumeParams(
    atr_length=3,
    volume_sma_length=3,
    range_sma_length=3,
    normalization_window=8,
    rank_window=5,
    forecast_length=4,
    winsor_z=3.0,
    zpf_fast_length=3,
    zpf_slow_length=4,
    profile_length=6,
    profile_bins=4,
    delta_roll_length=4,
    delta_bias_ema_length=5,
)


def make_bar(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    volume: float = 100.0,
    closed: bool = True,
) -> Bar:
    return Bar(
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        open_time=T0.add_ms(index * H1_MS),
        open=Price(Decimal(str(o))),
        high=Price(Decimal(str(h))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(c))),
        volume=Volume(Decimal(str(volume))),
        is_closed=closed,
        quality=QualityScore(1.0),
    )


def dull_bar(index: int, *, volume: float = 100.0) -> Bar:
    return make_bar(index, 100.0, 101.5, 99.0, 100.5, volume=volume)


def dull_series(count: int) -> list[Bar]:
    return [dull_bar(i) for i in range(count)]


def compute(bars: list[Bar]) -> list[Feature]:
    engine = VolumeEngine(params=PARAMS, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    return list(engine.compute(bars, context).unwrap())


def value_of(features: list[Feature], name: str, index: int) -> float:
    open_ms = T0.add_ms(index * H1_MS).epoch_ms
    for feature in features:
        if feature.name == name and feature.bar_open_time.epoch_ms == open_ms:
            return feature.value
    raise AssertionError(f"{name} not emitted for bar {index}")


class TestVolumeStatistics:
    def test_constant_volume_reads_neutral(self) -> None:
        features = compute(dull_series(14))
        assert value_of(features, "volume.rvol", 12) == 1.0
        assert value_of(features, "volume.volume_available", 12) == 1.0
        assert value_of(features, "volume.spike", 12) == 0.0
        # Identical bars: ATR equals its own mean.
        assert value_of(features, "volume.volatility_width", 12) == pytest.approx(1.0)

    def test_spike_expansion_and_selling_climax(self) -> None:
        bars = dull_series(12)
        # Volume blowout on a wide bar with a dominant lower wick and a
        # strong close: spike + expansion + selling climax (AICE 1717).
        bars.append(make_bar(12, 100.0, 101.0, 95.0, 100.8, volume=500.0))
        features = compute(bars)
        assert value_of(features, "volume.spike", 12) == 1.0
        assert value_of(features, "volume.expansion", 12) == 1.0
        assert value_of(features, "volume.selling_climax", 12) == 1.0
        assert value_of(features, "volume.buying_climax", 12) == 0.0
        # Wide bar defeats the narrow-bar condition of absorption.
        assert value_of(features, "volume.absorption_buy", 12) == 0.0
        assert value_of(features, "volume.aggression", 12) > 0.0

    def test_absorption_requires_a_narrow_bar(self) -> None:
        bars = dull_series(12)
        # High RVOL, dominant lower wick, strong close, range BELOW the
        # rolling mean (2.5): absorption_buy fires without a spike-climax.
        bars.append(make_bar(12, 100.4, 100.6, 98.9, 100.5, volume=200.0))
        features = compute(bars)
        assert value_of(features, "volume.absorption_buy", 12) == 1.0
        assert value_of(features, "volume.compression", 12) == 0.0
        assert value_of(features, "volume.selling_climax", 12) == 0.0


class TestMomentumAndVwap:
    def rally(self, count: int) -> list[Bar]:
        """Accelerating rally: zero-lag fast pulls above slow.

        A perfectly linear ramp leaves both zero-lag filters equal (lag
        fully compensated), so ``local_bull`` correctly needs price to
        accelerate - matching AICE's momentum semantics.
        """
        bars: list[Bar] = []
        previous = 100.0
        for i in range(count):
            close = 100.0 + 0.35 * i * i
            bars.append(make_bar(i, previous, close + 0.3, previous - 0.3, close))
            previous = close
        return bars

    def test_rally_reads_bullish_momentum(self) -> None:
        features = compute(self.rally(14))
        assert value_of(features, "volume.momentum_bull", 13) == 1.0
        assert value_of(features, "volume.momentum_bear", 13) == 0.0
        assert value_of(features, "volume.momentum_slope", 13) > 0.5

    def test_decline_reads_bearish_momentum(self) -> None:
        bars: list[Bar] = []
        previous = 200.0
        for i in range(14):
            close = 200.0 - 0.35 * i * i
            bars.append(make_bar(i, previous, previous + 0.3, close - 0.3, close))
            previous = close
        features = compute(bars)
        assert value_of(features, "volume.momentum_bear", 13) == 1.0
        assert value_of(features, "volume.momentum_bull", 13) == 0.0
        assert value_of(features, "volume.momentum_slope", 13) < 0.5

    def test_rally_closes_above_session_vwap(self) -> None:
        features = compute(self.rally(14))
        assert value_of(features, "volume.vwap_deviation_atr", 13) > 0.0
        assert value_of(features, "volume.vwap_deviation_z", 13) > 0.0


class TestVolumeProfile:
    def test_uniform_bars_fully_accept_the_close_bin(self) -> None:
        features = compute(dull_series(14))
        # Every bar's typical price lands in one bin: acceptance is 1.
        assert value_of(features, "volume.poc_acceptance", 12) == 1.0

    def test_close_above_heavy_lows_reads_above_poc(self) -> None:
        # Heavy volume printed low, then price lifts away from it.
        bars = [dull_bar(i, volume=500.0) for i in range(10)]
        for i in range(10, 14):
            base = 106.0 + 3.0 * (i - 10)
            bars.append(make_bar(i, base, base + 2.0, base - 0.5, base + 1.8, volume=50.0))
        features = compute(bars)
        assert value_of(features, "volume.above_poc", 13) == 1.0
        assert value_of(features, "volume.poc_distance_atr", 13) > 0.0
        assert value_of(features, "volume.poc_acceptance", 13) < 1.0


class TestEngineContract:
    def test_emits_nothing_during_warmup(self) -> None:
        features = compute(dull_series(14))
        first_ms = min(feature.bar_open_time.epoch_ms for feature in features)
        assert first_ms == T0.add_ms(PARAMS.warmup_bars * H1_MS).epoch_ms

    def test_all_names_and_normalized_bounds(self) -> None:
        features = compute(dull_series(14))
        assert {feature.name for feature in features} == set(FEATURE_NAMES)
        assert all(-1.0 <= feature.normalized_value <= 1.0 for feature in features)

    def test_deterministic_and_causal(self) -> None:
        bars = dull_series(12)
        bars.append(make_bar(12, 100.0, 101.0, 95.0, 100.8, volume=500.0))
        bars.append(dull_bar(13))
        full = compute(bars)
        short = {(f.name, f.bar_open_time.epoch_ms): f.value for f in compute(bars[:13])}
        for feature in full:
            probe = (feature.name, feature.bar_open_time.epoch_ms)
            if probe in short:
                assert short[probe] == feature.value

    def test_rejects_forming_bars(self) -> None:
        bars = dull_series(13)
        bars.append(make_bar(13, 100.0, 101.5, 99.0, 100.5, closed=False))
        engine = VolumeEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "DAT-004"

    def test_invalid_params_are_rejected(self) -> None:
        with pytest.raises(Exception, match="winsor_z"):
            VolumeParams(winsor_z=0.5)


class TestDefinitions:
    def test_definitions_cover_engine_names(self) -> None:
        definitions = volume_definitions(PARAMS)
        assert {d.name for d in definitions} == set(FEATURE_NAMES)
        registry = FeatureRegistry()
        registry.register_all(definitions)
        assert all(d.family == "volume" for d in definitions)
