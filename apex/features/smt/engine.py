"""SMT divergence feature family - migrated from AICE.

Faithful port of the AICE SMT core (Book VI): ``f_smt_pack`` pivot
state per series (last/previous pivot values plus bars since the last
confirmation), the divergence conditions ``f_smt_bull``/``f_smt_bear``
(spec lines 339-346) gated by pivot age, and the correlation engine
(lines 1795-1823): rolling Pearson correlation of log returns, its
dynamic ratio against an EMA of its absolute value, and the AICE
quality mapping ``clamp((|corr| - min) / (1 - min)) * min(dyn, 1)``.

A bullish SMT fires when one series prints a lower low while the
correlated reference holds a higher-or-equal low (and mirrored for
highs). Each fired divergence bumps a per-side confidence pool to the
correlation quality, decaying by ``decay_rate`` per bar - the family-
level reduction of AICE's event quality ``q * decay^age``.

Reference symbols are drawn from the configured market universe (each
symbol references its first peer). Deferred to the multi-exchange
expansion: inverse/dominance references (CRYPTOCAP:USDT.D-style) and
the institutional event layer (entry windows, zone proxies, type
scores), which composes cross-family context and belongs to the
probability-platform consumers per Book II composition.

Auxiliary-free fallback: without a stored reference series the engine
emits nothing (the documented neutral behavior for context families).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import log

from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, FeatureError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import ensure_in_range, ensure_positive
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.calculations import (
    PivotTracker,
    clamp,
    correlation,
    ema,
    last_closed_indices,
)

FAMILY = "smt"
_SOURCE = "apex.features.smt"

# Dynamic correlation ratio bounds (AICE lines 1817-1819).
_DYNAMIC_FLOOR, _DYNAMIC_CEIL = 0.35, 1.15

FEATURE_NAMES: tuple[str, ...] = (
    "smt.bull_divergence",
    "smt.bear_divergence",
    "smt.correlation",
    "smt.correlation_quality",
    "smt.bull_confidence",
    "smt.bear_confidence",
    "smt.reference_available",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SmtParams:
    """Tunables of the SMT family (AICE input defaults)."""

    pivot_lookback: int = 5
    max_pivot_age: int = 10
    correlation_length: int = 120
    correlation_minimum: float = 0.60
    correlation_slope_length: int = 34
    decay_rate: float = 0.985
    min_score: float = 0.35

    def __post_init__(self) -> None:
        ensure_positive(self.pivot_lookback, "pivot_lookback")
        ensure_positive(self.max_pivot_age, "max_pivot_age")
        ensure_positive(self.correlation_length, "correlation_length")
        ensure_in_range(self.correlation_minimum, 0.0, 1.0, "correlation_minimum")
        ensure_positive(self.correlation_slope_length, "correlation_slope_length")
        ensure_in_range(self.decay_rate, 0.0, 1.0, "decay_rate")
        ensure_in_range(self.min_score, 0.0, 1.0, "min_score")


@dataclass(slots=True)
class _PivotState:
    """AICE ``f_smt_pack``: pivot values and confirmation ages."""

    tracker: PivotTracker
    last_low: float | None = None
    prev_low: float | None = None
    last_high: float | None = None
    prev_high: float | None = None
    low_confirmed_at: int | None = None
    high_confirmed_at: int | None = None

    def update(self, bar: Bar, index: int) -> None:
        new_high, new_low = self.tracker.update(bar)
        if new_low:
            self.prev_low = self.last_low
            self.last_low = self.tracker.last_low
            self.low_confirmed_at = index
        if new_high:
            self.prev_high = self.last_high
            self.last_high = self.tracker.last_high
            self.high_confirmed_at = index

    def low_age(self, index: int) -> int | None:
        return index - self.low_confirmed_at if self.low_confirmed_at is not None else None

    def high_age(self, index: int) -> int | None:
        return index - self.high_confirmed_at if self.high_confirmed_at is not None else None


def _bull_divergence(chart: _PivotState, ref: _PivotState, i: int, j: int, max_age: int) -> bool:
    """AICE ``f_smt_bull``: opposing fresh swing lows across the pair."""
    c_age, r_age = chart.low_age(i), ref.low_age(j)
    clp, cpp = chart.last_low, chart.prev_low
    rlp, rpp = ref.last_low, ref.prev_low
    if clp is None or cpp is None or rlp is None or rpp is None:
        return False
    if c_age is None or r_age is None or c_age > max_age or r_age > max_age:
        return False
    return (clp < cpp and rlp >= rpp) or (clp >= cpp and rlp < rpp)


def _bear_divergence(chart: _PivotState, ref: _PivotState, i: int, j: int, max_age: int) -> bool:
    """AICE ``f_smt_bear``: opposing fresh swing highs across the pair."""
    c_age, r_age = chart.high_age(i), ref.high_age(j)
    clh, cph = chart.last_high, chart.prev_high
    rlh, rph = ref.last_high, ref.prev_high
    if clh is None or cph is None or rlh is None or rph is None:
        return False
    if c_age is None or r_age is None or c_age > max_age or r_age > max_age:
        return False
    return (clh > cph and rlh <= rph) or (clh <= cph and rlh > rph)


class SmtEngine:
    """Computes SMT divergence against a correlated reference symbol."""

    def __init__(
        self,
        *,
        params: SmtParams,
        references: Mapping[str, str],
        clock: Clock,
    ) -> None:
        self._params = params
        self._references = dict(references)
        self._clock = clock

    @property
    def family(self) -> str:
        """Feature family identifier."""
        return FAMILY

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Every feature this engine emits."""
        return FEATURE_NAMES

    def required_series(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> tuple[tuple[str, Timeframe], ...]:
        """The reference symbol's series at the chart timeframe."""
        reference = self._references.get(symbol)
        return ((reference, timeframe),) if reference is not None else ()

    def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Auxiliary-free fallback: no reference series, nothing to say."""
        return self.compute_with_context(bars, {}, context)

    def compute_with_context(
        self,
        bars: Sequence[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Fold the chart window against the reference series."""
        try:
            features = self._compute_all(list(bars), auxiliary, context)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(tuple(features))

    # --- Fold ---------------------------------------------------------------

    def _compute_all(
        self,
        bars: list[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> list[Feature]:
        self._require_confirmed_series(bars)
        reference_symbol = self._references.get(context.symbol)
        if reference_symbol is None or not bars:
            return []
        reference = list(auxiliary.get((reference_symbol, context.timeframe), ()))
        if not reference:
            return []
        self._require_confirmed_series(reference)
        mapping = last_closed_indices(
            [bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in bars],
            [bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in reference],
        )
        quality = self._correlation_quality(bars, reference, mapping)
        return self._fold(bars, reference, mapping, quality)

    def _fold(
        self,
        bars: list[Bar],
        reference: list[Bar],
        mapping: list[int | None],
        quality: tuple[list[float | None], list[float]],
    ) -> list[Feature]:
        params = self._params
        chart_state = _PivotState(tracker=PivotTracker(lookback=params.pivot_lookback))
        ref_state = _PivotState(tracker=PivotTracker(lookback=params.pivot_lookback))
        correlations, qualities = quality
        features: list[Feature] = []
        bull_pool = bear_pool = 0.0
        ref_cursor = -1
        for index, bar in enumerate(bars):
            chart_state.update(bar, index)
            ref_index = mapping[index]
            while ref_cursor < (ref_index if ref_index is not None else -1):
                ref_cursor += 1
                ref_state.update(reference[ref_cursor], ref_cursor)
            bull_pool = clamp(bull_pool * params.decay_rate, 0.0, 1.0)
            bear_pool = clamp(bear_pool * params.decay_rate, 0.0, 1.0)
            if ref_index is None:
                features.extend(self._emit(bar, False, False, 0.0, 0.0, 0.0, 0.0, False))
                continue
            corr = correlations[index]
            corr_quality = qualities[index]
            bull = _bull_divergence(chart_state, ref_state, index, ref_index, params.max_pivot_age)
            bear = _bear_divergence(chart_state, ref_state, index, ref_index, params.max_pivot_age)
            strength = corr_quality if corr_quality >= params.min_score else 0.0
            if bull and strength > 0:
                bull_pool = max(bull_pool, strength)
            if bear and strength > 0:
                bear_pool = max(bear_pool, strength)
            features.extend(
                self._emit(
                    bar, bull, bear, corr if corr is not None else 0.0,
                    corr_quality, bull_pool, bear_pool, True,
                )
            )
        return features

    def _correlation_quality(
        self,
        bars: list[Bar],
        reference: list[Bar],
        mapping: list[int | None],
    ) -> tuple[list[float | None], list[float]]:
        """(raw correlation, AICE correlation quality) per chart bar."""
        params = self._params
        chart_returns = self._log_returns([float(bar.close.value) for bar in bars])
        ref_returns = self._log_returns([float(bar.close.value) for bar in reference])
        aligned = [
            ref_returns[j] if (j := mapping[i]) is not None else 0.0
            for i in range(len(bars))
        ]
        raw = correlation(chart_returns, aligned, params.correlation_length)
        magnitudes = [abs(value) if value is not None else 0.0 for value in raw]
        smoothed = ema(magnitudes, params.correlation_slope_length)
        qualities: list[float] = []
        for index, value in enumerate(raw):
            magnitude = magnitudes[index]
            mean = smoothed[index]
            dynamic = (
                clamp(magnitude / mean, _DYNAMIC_FLOOR, _DYNAMIC_CEIL)
                if mean is not None and mean > 0
                else 1.0
            )
            base = clamp(
                (magnitude - params.correlation_minimum)
                / max(1.0 - params.correlation_minimum, 0.0001),
                0.0,
                1.0,
            )
            qualities.append(base * min(dynamic, 1.0) if value is not None else 0.0)
        return raw, qualities

    def _log_returns(self, closes: list[float]) -> list[float]:
        out = [0.0] * len(closes)
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i - 1] > 0:
                out[i] = log(closes[i] / closes[i - 1])
        return out

    def _require_confirmed_series(self, bars: list[Bar]) -> None:
        for bar in bars:
            bar.require_closed()
        for previous, current in pairwise(bars):
            if current.open_time.epoch_ms <= previous.open_time.epoch_ms:
                raise FeatureError(
                    "bars must be strictly ascending by open time",
                    code="FEA-010",
                    details={"at": str(current.open_time)},
                )

    # --- Emission -----------------------------------------------------------

    def _emit(
        self,
        bar: Bar,
        bull: bool,
        bear: bool,
        corr: float,
        corr_quality: float,
        bull_pool: float,
        bear_pool: float,
        available: bool,
    ) -> list[Feature]:
        values: dict[str, tuple[float, float]] = {
            "smt.bull_divergence": self._binary(bull),
            "smt.bear_divergence": self._binary(bear),
            "smt.correlation": (corr, clamp(corr, -1.0, 1.0)),
            "smt.correlation_quality": (corr_quality, corr_quality * 2.0 - 1.0),
            "smt.bull_confidence": (bull_pool, bull_pool * 2.0 - 1.0),
            "smt.bear_confidence": (bear_pool, bear_pool * 2.0 - 1.0),
            "smt.reference_available": self._binary(available),
        }
        computed_at = self._clock.now()
        return [
            Feature(
                created_at=computed_at,
                name=name,
                family=FAMILY,
                exchange=bar.exchange,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                bar_open_time=bar.open_time,
                value=raw,
                normalized_value=normalized,
                weight=Weight(1.0),
                confidence=Confidence(1.0),
                reliability=Reliability(1.0),
                source=_SOURCE,
                computed_at=computed_at,
            )
            for name, (raw, normalized) in values.items()
        ]

    def _binary(self, flag: bool) -> tuple[float, float]:
        value = 1.0 if flag else 0.0
        return value, value
