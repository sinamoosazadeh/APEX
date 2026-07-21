"""OB/FVG family: creation scans, lifecycle, retests, inversion, BPR."""

from decimal import Decimal

import pytest
from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Volume
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.orderblocks.definitions import orderblock_definitions
from apex.features.orderblocks.engine import (
    FEATURE_NAMES,
    OrderBlockEngine,
    OrderBlockParams,
)
from apex.features.registry import FeatureRegistry

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Small, fast parameters: warmup = max(3, 2*2+1, 3, 3) = 5 bars.
PARAMS = OrderBlockParams(
    pivot_lookback=2,
    atr_length=3,
    displacement_body_atr=1.2,
    break_decay=0.9,
    scan_lookback=10,
    scan_cap=20,
    ob_decay=0.9,
    fvg_decay=0.9,
    max_live_objects=3,
    max_object_age=50,
    min_fvg_size_atr=0.05,
    volume_sma_length=3,
    range_sma_length=3,
)


def make_bar(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
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
        volume=Volume(Decimal(100)),
        is_closed=closed,
        quality=QualityScore(1.0),
    )


def dull_bar(index: int) -> Bar:
    """A quiet bar around 100 with no pivot-worthy extremes."""
    return make_bar(index, 100.0, 101.5, 99.0, 100.5)


def compute(bars: list[Bar]) -> list[Feature]:
    engine = OrderBlockEngine(params=PARAMS, clock=ManualClock(T0))
    context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
    return list(engine.compute(bars, context).unwrap())


def value_of(features: list[Feature], name: str, index: int) -> float:
    open_ms = T0.add_ms(index * H1_MS).epoch_ms
    for feature in features:
        if feature.name == name and feature.bar_open_time.epoch_ms == open_ms:
            return feature.value
    raise AssertionError(f"{name} not emitted for bar {index}")


def order_block_scenario() -> list[Bar]:
    """Rally through a pivot high with a down-candle origin, then break down.

    Bar 4 prints a strict pivot high (106, confirmed at bar 6); bars 5-6
    are the down candles a bull OB can anchor to. Bar 8 closes above the
    pivot (BOS up -> OB creation, zone 101..105 from bar 5). Bar 9 leaves
    the zone, bar 10 retests it, bar 11 closes below its bottom (breaker).
    """
    return [
        dull_bar(0),
        dull_bar(1),
        dull_bar(2),
        make_bar(3, 100.5, 103.0, 100.0, 102.5),
        make_bar(4, 102.5, 106.0, 102.0, 104.0),
        make_bar(5, 104.0, 105.0, 101.0, 102.0),
        make_bar(6, 102.0, 103.5, 100.5, 101.0),
        make_bar(7, 101.0, 102.5, 100.0, 101.5),
        make_bar(8, 101.5, 108.0, 101.0, 107.5),
        make_bar(9, 107.5, 110.0, 106.5, 109.0),
        make_bar(10, 109.0, 109.5, 104.0, 106.0),
        make_bar(11, 106.0, 106.5, 99.5, 100.0),
        make_bar(12, 100.0, 101.0, 99.0, 100.5),
    ]


def fvg_scenario() -> list[Bar]:
    """Gap up over bar 4's high, partially fill, then invert.

    Bar 6 gaps (low 102.5 > high[4] 101.5) creating a bull FVG
    [101.5, 102.5]; bar 7 dips to 102 (half fill, inside); bar 8
    closes below 101.5 (inversion -> IFVG bear).
    """
    return [
        dull_bar(0),
        dull_bar(1),
        dull_bar(2),
        dull_bar(3),
        dull_bar(4),
        make_bar(5, 100.5, 102.0, 100.0, 101.5),
        make_bar(6, 103.0, 106.0, 102.5, 105.5),
        make_bar(7, 105.5, 107.0, 102.0, 106.0),
        make_bar(8, 106.0, 106.2, 100.0, 100.5),
    ]


def bpr_scenario() -> list[Bar]:
    """A bear gap immediately answered by a bull gap (balanced price range).

    Bar 6 gaps down under bar 4's low (bear FVG); bar 7 gaps up over
    bar 5's high (bull FVG) -> bpr_bull fires on bar 7.
    """
    return [
        dull_bar(0),
        dull_bar(1),
        dull_bar(2),
        dull_bar(3),
        dull_bar(4),
        make_bar(5, 100.5, 101.0, 97.0, 98.0),
        make_bar(6, 98.0, 98.5, 95.0, 95.5),
        make_bar(7, 102.5, 105.0, 102.0, 104.5),
    ]


class TestOrderBlockLifecycle:
    def test_structure_break_creates_bull_order_block(self) -> None:
        features = compute(order_block_scenario())
        assert value_of(features, "orderblocks.bull_ob_count", 8) == 1.0
        assert value_of(features, "orderblocks.ob_long_confidence", 8) > 0.0
        # Born this bar: full freshness.
        assert value_of(features, "orderblocks.ob_long_freshness", 8) == 1.0
        # No bull OB exists before the break.
        assert value_of(features, "orderblocks.bull_ob_count", 7) == 0.0

    def test_retest_is_detected_inside_the_zone(self) -> None:
        features = compute(order_block_scenario())
        # Bar 9 trades above the zone, bar 10 dips back into it.
        assert value_of(features, "orderblocks.in_bull_ob", 9) == 0.0
        assert value_of(features, "orderblocks.in_bull_ob", 10) == 1.0
        assert value_of(features, "orderblocks.ob_long_confidence", 10) > 0.0

    def test_mitigation_raises_the_breaker_flag(self) -> None:
        features = compute(order_block_scenario())
        assert value_of(features, "orderblocks.bull_breaker", 11) == 1.0
        assert value_of(features, "orderblocks.bull_ob_count", 11) == 0.0
        # The flag is an event, not a state.
        assert value_of(features, "orderblocks.bull_breaker", 12) == 0.0

    def test_confidence_decays_without_interaction(self) -> None:
        bars = order_block_scenario()[:10]  # stop before retest/mitigation
        bars.append(make_bar(10, 109.0, 110.5, 108.0, 110.0))
        bars.append(make_bar(11, 110.0, 111.5, 109.0, 111.0))
        features = compute(bars)
        early = value_of(features, "orderblocks.ob_long_confidence", 9)
        late = value_of(features, "orderblocks.ob_long_confidence", 11)
        assert late < early


class TestFairValueGaps:
    def test_gap_creates_a_scored_fvg(self) -> None:
        features = compute(fvg_scenario())
        assert value_of(features, "orderblocks.new_bull_fvg", 6) == 1.0
        assert value_of(features, "orderblocks.bull_fvg_count", 6) == 1.0
        assert value_of(features, "orderblocks.fvg_long_confidence", 6) > 0.0
        assert value_of(features, "orderblocks.new_bull_fvg", 7) == 0.0

    def test_partial_fill_keeps_the_gap_alive(self) -> None:
        features = compute(fvg_scenario())
        assert value_of(features, "orderblocks.in_bull_fvg", 7) == 1.0
        assert value_of(features, "orderblocks.bull_fvg_count", 7) == 1.0

    def test_close_through_the_gap_inverts_it(self) -> None:
        features = compute(fvg_scenario())
        assert value_of(features, "orderblocks.ifvg_bear", 8) == 1.0
        assert value_of(features, "orderblocks.bull_fvg_count", 8) == 0.0
        assert value_of(features, "orderblocks.fvg_long_confidence", 8) == 0.0

    def test_balanced_price_range_fires_on_opposing_gaps(self) -> None:
        features = compute(bpr_scenario())
        assert value_of(features, "orderblocks.new_bear_fvg", 6) == 1.0
        assert value_of(features, "orderblocks.new_bull_fvg", 7) == 1.0
        assert value_of(features, "orderblocks.bpr_bull", 7) == 1.0
        assert value_of(features, "orderblocks.bpr_bear", 7) == 0.0


class TestEngineContract:
    def test_emits_nothing_during_warmup(self) -> None:
        features = compute(order_block_scenario())
        first_ms = min(feature.bar_open_time.epoch_ms for feature in features)
        assert first_ms == T0.add_ms(PARAMS.warmup_bars * H1_MS).epoch_ms

    def test_all_names_and_normalized_bounds(self) -> None:
        features = compute(order_block_scenario())
        emitted = {feature.name for feature in features}
        assert emitted == set(FEATURE_NAMES)
        assert all(-1.0 <= feature.normalized_value <= 1.0 for feature in features)

    def test_deterministic_and_causal(self) -> None:
        bars = order_block_scenario()
        full = compute(bars)
        again = compute(bars)
        key = [(f.name, f.bar_open_time.epoch_ms, f.value) for f in full]
        assert key == [(f.name, f.bar_open_time.epoch_ms, f.value) for f in again]
        # A shorter window must produce identical values for its bars:
        # the fold is causal, so later bars cannot repaint earlier ones.
        short = compute(bars[:11])
        short_key = {(f.name, f.bar_open_time.epoch_ms): f.value for f in short}
        for f in full:
            probe = (f.name, f.bar_open_time.epoch_ms)
            if probe in short_key:
                assert short_key[probe] == f.value

    def test_rejects_forming_bars(self) -> None:
        bars = order_block_scenario()
        bars.append(make_bar(13, 100.5, 101.0, 100.0, 100.8, closed=False))
        engine = OrderBlockEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "DAT-004"

    def test_rejects_unsorted_bars(self) -> None:
        bars = order_block_scenario()
        bars.append(dull_bar(3))
        engine = OrderBlockEngine(params=PARAMS, clock=ManualClock(T0))
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = engine.compute(bars, context)
        assert not result.ok
        assert result.error is not None and result.error.code == "FEA-010"

    def test_invalid_params_are_rejected(self) -> None:
        with pytest.raises(Exception, match="ob_decay"):
            OrderBlockParams(ob_decay=1.5)


class TestDefinitions:
    def test_definitions_cover_engine_names(self) -> None:
        definitions = orderblock_definitions(PARAMS)
        assert {d.name for d in definitions} == set(FEATURE_NAMES)
        registry = FeatureRegistry()
        registry.register_all(definitions)
        assert all(d.family == "orderblocks" for d in definitions)

    def test_emission_matches_registry(self) -> None:
        registry = FeatureRegistry()
        registry.register_all(orderblock_definitions(PARAMS))
        for feature in compute(order_block_scenario()):
            assert registry.get(feature.name).family == "orderblocks"
