"""HTF context and SMT divergence families (multi-series engines)."""

from decimal import Decimal

from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Volume
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.htf.definitions import htf_definitions
from apex.features.htf.engine import FEATURE_NAMES as HTF_NAMES
from apex.features.htf.engine import HtfContextEngine, HtfParams
from apex.features.registry import FeatureRegistry
from apex.features.smt.definitions import smt_definitions
from apex.features.smt.engine import FEATURE_NAMES as SMT_NAMES
from apex.features.smt.engine import SmtEngine, SmtParams

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms
H4_MS = Timeframe.H4.duration_ms


def bar(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    timeframe: Timeframe = Timeframe.H1,
    symbol: str = "BTCUSDT",
) -> Bar:
    return Bar(
        exchange="toobit",
        symbol=symbol,
        timeframe=timeframe,
        open_time=T0.add_ms(index * timeframe.duration_ms),
        open=Price(Decimal(str(o))),
        high=Price(Decimal(str(h))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(c))),
        volume=Volume(Decimal(100)),
        is_closed=True,
        quality=QualityScore(1.0),
    )


def rising(count: int, *, timeframe: Timeframe, symbol: str = "BTCUSDT") -> list[Bar]:
    bars: list[Bar] = []
    previous = 100.0
    for i in range(count):
        close = previous + 1.0
        bars.append(
            bar(i, previous, close + 0.3, previous - 0.3, close,
                timeframe=timeframe, symbol=symbol)
        )
        previous = close
    return bars


def value_of(
    features: list[Feature], name: str, index: int, *, timeframe: Timeframe = Timeframe.H1
) -> float:
    open_ms = T0.add_ms(index * timeframe.duration_ms).epoch_ms
    for feature in features:
        if feature.name == name and feature.bar_open_time.epoch_ms == open_ms:
            return feature.value
    raise AssertionError(f"{name} not emitted for bar {index}")


HTF_PARAMS = HtfParams(pivot_lookback=2, ema_length=3)


class TestHtfContextFamily:
    def engine(self) -> HtfContextEngine:
        return HtfContextEngine(
            params=HTF_PARAMS,
            macro_timeframes=(Timeframe.H1, Timeframe.H4),
            clock=ManualClock(T0),
        )

    def test_rising_macro_series_read_bullish(self) -> None:
        chart = rising(24, timeframe=Timeframe.H1)
        macro2 = rising(6, timeframe=Timeframe.H4)
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        auxiliary = {
            ("BTCUSDT", Timeframe.H1): chart,
            ("BTCUSDT", Timeframe.H4): macro2,
        }
        features = list(self.engine().compute_with_context(chart, auxiliary, context).unwrap())
        # Above the EMA on both macro scales: full bullish alignment.
        assert value_of(features, "htf.alignment", 23) == 2.0
        assert value_of(features, "htf.bull_context", 23) == 1.0
        assert value_of(features, "htf.confidence", 23) == 1.0
        assert value_of(features, "htf.bear_context", 23) == 0.0

    def test_macro_mapping_is_causal(self) -> None:
        """A chart bar may only see macro bars already closed."""
        chart = rising(14, timeframe=Timeframe.H1)
        macro2 = rising(6, timeframe=Timeframe.H4)
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        auxiliary = {
            ("BTCUSDT", Timeframe.H1): chart,
            ("BTCUSDT", Timeframe.H4): macro2,
        }
        features = list(self.engine().compute_with_context(chart, auxiliary, context).unwrap())
        # Bars 0-2 close before the first 4h bar does: neutral macro-2.
        assert value_of(features, "htf.macro2_bias", 2) == 0.0
        # Chart bar 10 (closes 11h) sees two closed 4h bars - the macro
        # EMA(3) has not seeded, so the bias is still neutral; bar 11
        # (closes 12h) sees the third closed 4h bar and turns bullish.
        assert value_of(features, "htf.macro2_bias", 10) == 0.0
        assert value_of(features, "htf.macro2_bias", 11) == 1.0

    def test_without_macro_series_emits_nothing(self) -> None:
        chart = rising(10, timeframe=Timeframe.H1)
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        assert self.engine().compute(chart, context).unwrap() == ()

    def test_definitions_cover_engine_names(self) -> None:
        definitions = htf_definitions(HTF_PARAMS)
        assert {d.name for d in definitions} == set(HTF_NAMES)
        FeatureRegistry().register_all(definitions)


SMT_PARAMS = SmtParams(
    pivot_lookback=2,
    max_pivot_age=6,
    correlation_length=5,
    correlation_minimum=0.30,
    correlation_slope_length=3,
    decay_rate=0.9,
    min_score=0.10,
)


def swing_series(lows: list[float], *, symbol: str) -> list[Bar]:
    """Bars whose lows trace the given path (highs shadow above)."""
    bars: list[Bar] = []
    for i, low in enumerate(lows):
        close = low + 1.0
        bars.append(bar(i, low + 0.5, close + 0.5, low, close, symbol=symbol))
    return bars


class TestSmtFamily:
    def engine(self) -> SmtEngine:
        return SmtEngine(
            params=SMT_PARAMS,
            references={"ETHUSDT": "BTCUSDT"},
            clock=ManualClock(T0),
        )

    def compute(self, chart: list[Bar], reference: list[Bar]) -> list[Feature]:
        context = MarketContext(symbol="ETHUSDT", timeframe=Timeframe.H1, as_of=T0)
        auxiliary = {("BTCUSDT", Timeframe.H1): reference}
        return list(self.engine().compute_with_context(chart, auxiliary, context).unwrap())

    def test_lower_low_against_higher_low_fires_bull_divergence(self) -> None:
        # Chart (ETH): second swing low LOWER than the first.
        chart_lows = [10, 10, 8, 10, 10, 10, 6, 10, 10, 10]
        # Reference (BTC): second swing low HIGHER than the first.
        ref_lows = [10, 10, 8, 10, 10, 10, 9, 10, 10, 10]
        chart = swing_series([float(x) for x in chart_lows], symbol="ETHUSDT")
        reference = swing_series([float(x) for x in ref_lows], symbol="BTCUSDT")
        features = self.compute(chart, reference)
        # Both second pivots confirm at bar 8 (lookback 2).
        assert value_of(features, "smt.bull_divergence", 8) == 1.0
        assert value_of(features, "smt.bull_confidence", 8) > 0.0
        assert value_of(features, "smt.reference_available", 8) == 1.0

    def test_agreeing_swings_do_not_fire(self) -> None:
        lows = [10, 10, 8, 10, 10, 10, 6, 10, 10, 10]
        chart = swing_series([float(x) for x in lows], symbol="ETHUSDT")
        reference = swing_series([float(x) for x in lows], symbol="BTCUSDT")
        features = self.compute(chart, reference)
        assert value_of(features, "smt.bull_divergence", 8) == 0.0
        assert value_of(features, "smt.bull_confidence", 8) == 0.0

    def test_confidence_decays_once_the_pivots_age_out(self) -> None:
        # Divergent pivots confirm at bar 8 and re-fire while fresh
        # (age <= 6); past bar 14 they age out and the pool decays.
        chart_lows = [10, 10, 8, 10, 10, 10, 6, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        ref_lows = [10, 10, 8, 10, 10, 10, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        chart = swing_series([float(x) for x in chart_lows], symbol="ETHUSDT")
        reference = swing_series([float(x) for x in ref_lows], symbol="BTCUSDT")
        features = self.compute(chart, reference)
        held = value_of(features, "smt.bull_confidence", 14)
        assert value_of(features, "smt.bull_divergence", 14) == 1.0
        assert value_of(features, "smt.bull_divergence", 15) == 0.0
        assert value_of(features, "smt.bull_confidence", 15) < held
        assert value_of(features, "smt.bull_confidence", 16) < value_of(
            features, "smt.bull_confidence", 15
        )

    def test_without_reference_emits_nothing(self) -> None:
        chart = swing_series([10.0] * 8, symbol="ETHUSDT")
        context = MarketContext(symbol="ETHUSDT", timeframe=Timeframe.H1, as_of=T0)
        assert self.engine().compute(chart, context).unwrap() == ()

    def test_symbol_without_reference_emits_nothing(self) -> None:
        chart = swing_series([10.0] * 8, symbol="BTCUSDT")
        context = MarketContext(symbol="BTCUSDT", timeframe=Timeframe.H1, as_of=T0)
        result = self.engine().compute_with_context(chart, {}, context)
        assert result.unwrap() == ()

    def test_definitions_cover_engine_names(self) -> None:
        definitions = smt_definitions(SMT_PARAMS)
        assert {d.name for d in definitions} == set(SMT_NAMES)
        FeatureRegistry().register_all(definitions)
