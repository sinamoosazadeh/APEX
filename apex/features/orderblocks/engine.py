"""Order block / fair value gap feature family - migrated from AICE.

Faithful port of the AICE Pine v6 "ORDER BLOCKS & FVG" section (Book VI
spec lines ~1248-1592), per the Book II ch. 2 migration matrix:

- **Order block creation** on a structure break (BOS/CHoCH): scan back
  up to ``min(scan_lookback, scan_cap, bar_index)`` bars for opposing
  candles and keep the highest-quality one. Quality is the AICE
  nine-term weighted sum ``f_ob_quality`` (body/ATR, relative volume,
  break quality, displacement, absorption, location vs the dealing
  range equilibrium, nesting, imbalance, MTF context).
- **Order block lifecycle**: per-bar confidence decay, retest bonus
  ``0.05 * max(0, 1 - retests * 0.12)`` on entering the zone,
  mitigation on close beyond the zone (raising the breaker flag),
  expiry by age or confidence floor, at most ``max_live_objects``
  zones per side (oldest evicted first).
- **FVG creation** from the three-bar gap rule (``low > high[2]`` /
  ``high < low[2]``) with a minimum ATR size, scored by the six-term
  ``f_fvg_quality``; lifecycle tracks the maximum fill fraction,
  decays confidence, inverts on close through the far edge (IFVG)
  and expires like order blocks.
- **Aggregation**: per side, the best zone by effective score
  ``conf * (0.45 + 0.55 * proximity) * retestQ * nestedQ`` (+ inside
  bonus) for order blocks and ``conf * (0.45 + 0.55 * proximity) *
  (1 - 0.20 * fill)`` (+ inside bonus) for FVGs.
- **BPR**: a balanced price range fires when a new bull FVG follows a
  new bear FVG on the previous bar (and mirrored).

FVG ``trendQ`` is fully wired: the zero-lag momentum filter (AICE
``local_bull/bear``, spec lines 1061-1066) is computed internally from
the shared ``zero_lag_filter`` primitive, so the term evaluates the
true AICE ternary ``local ? 1.0 : trend-aligned ? 0.75 : 0.35``.

All context terms are fully wired. ``mtfQ``/``htfQ`` and the FVG
``locQ`` HTF branch evaluate the true AICE ternaries against the HTF
context computed from closed macro bars (shared
``htf_context_series``); when the engine runs without auxiliary macro
series, those terms fall back to AICE's own ``htf_align == 0`` neutral
values - identical arithmetic to an undecided macro state.

Two Pine artifacts are replicated exactly for parity with the
reference: creation runs *before* the lifecycle pass on the same bar
(a newborn zone is decayed once immediately), and the IFVG flag takes
the ``inverted`` value of the *last removed* gap in the newest-to-
oldest lifecycle sweep. All values are computed from confirmed bars
only; the engine emits nothing during warmup.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise

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
    HtfContext,
    PivotTracker,
    StructureFold,
    StructureSignals,
    clamp,
    htf_context_series,
    sma,
    wilder_atr,
    zero_lag_filter,
)

FAMILY = "orderblocks"
_SOURCE = "apex.features.orderblocks"

# f_ob_quality weights (AICE lines 1289-1300): body/ATR, relative
# volume, break quality, displacement, absorption, location, nested,
# imbalance, MTF context.
_OB_QUALITY_WEIGHTS = (0.18, 0.16, 0.18, 0.14, 0.10, 0.10, 0.06, 0.05, 0.03)
# f_fvg_quality weights (AICE lines 1302-1310): size/ATR,
# displacement, relative volume, trend, location, HTF context.
_FVG_QUALITY_WEIGHTS = (0.25, 0.25, 0.18, 0.18, 0.14, 0.10)
# Normalizers inside the quality terms (AICE lines 1291-1292, 1304).
_QUALITY_ATR_NORM = 1.5
_RVOL_NORM = 2.5
# HTF context ternaries (AICE lines 1334, 1490): favorable -> 1.0,
# undecided (or no macro series) -> 0.60, against -> 0.25; the FVG
# location HTF branch scores 0.75 (line 1489).
_HTF_NEUTRAL_QUALITY = 0.60
_HTF_AGAINST_QUALITY = 0.25
_HTF_LOCATION_QUALITY = 0.75
# FVG trendQ ternary (AICE line 1488): local momentum -> 1.0.
_TREND_LOCAL_QUALITY = 1.0
_TREND_ALIGNED_QUALITY = 0.75
_TREND_AGAINST_QUALITY = 0.35
# Zero-lag slope lag (AICE line 1063).
_SLOPE_LAG = 3
_LOCATION_MISS_QUALITY = 0.45
_LOCATION_UNKNOWN_QUALITY = 0.5
# Absorption: high relative volume inside a narrow bar (line 1332).
_ABSORPTION_RVOL = 1.3
# Zone confidence floors at creation (lines 1344, 1493).
_MIN_OB_CONFIDENCE = 0.45
_MIN_FVG_CONFIDENCE = 0.35
# Retest bonus/penalty and expiry floor (lifecycle loops).
_RETEST_BONUS = 0.05
_RETEST_PENALTY = 0.12
_RETEST_FLOOR = 0.35
_EXPIRY_CONFIDENCE = 0.03
# Aggregation shape (lines 1448-1590).
_PROXIMITY_ATR = 3.0
_BASE_SHARE = 0.45
_PROXIMITY_SHARE = 0.55
_NESTED_MULTIPLIER = 1.08
_INSIDE_OB_BONUS = 0.10
_INSIDE_FVG_BONUS = 0.08
_FILL_PENALTY = 0.20
# Structure breaks this early cannot seed a scan (line 1315).
_MIN_CREATION_INDEX = 5

FEATURE_NAMES: tuple[str, ...] = (
    "orderblocks.ob_long_confidence",
    "orderblocks.ob_short_confidence",
    "orderblocks.ob_long_freshness",
    "orderblocks.ob_short_freshness",
    "orderblocks.in_bull_ob",
    "orderblocks.in_bear_ob",
    "orderblocks.bull_ob_count",
    "orderblocks.bear_ob_count",
    "orderblocks.bull_breaker",
    "orderblocks.bear_breaker",
    "orderblocks.new_bull_fvg",
    "orderblocks.new_bear_fvg",
    "orderblocks.fvg_long_confidence",
    "orderblocks.fvg_short_confidence",
    "orderblocks.in_bull_fvg",
    "orderblocks.in_bear_fvg",
    "orderblocks.bull_fvg_count",
    "orderblocks.bear_fvg_count",
    "orderblocks.ifvg_bull",
    "orderblocks.ifvg_bear",
    "orderblocks.bpr_bull",
    "orderblocks.bpr_bear",
    "orderblocks.bull_ob_bottom",
    "orderblocks.bear_ob_top",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderBlockParams:
    """Tunables of the OB/FVG family (AICE input defaults)."""

    pivot_lookback: int = 8
    atr_length: int = 14
    displacement_body_atr: float = 1.20
    break_decay: float = 0.985
    scan_lookback: int = 150
    scan_cap: int = 300
    ob_decay: float = 0.985
    fvg_decay: float = 0.975
    max_live_objects: int = 12
    max_object_age: int = 300
    min_fvg_size_atr: float = 0.05
    volume_sma_length: int = 20
    range_sma_length: int = 14
    zpf_fast_length: int = 12
    zpf_slow_length: int = 26
    htf_pivot_lookback: int = 8
    htf_ema_length: int = 50

    def __post_init__(self) -> None:
        ensure_positive(self.pivot_lookback, "pivot_lookback")
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.displacement_body_atr, "displacement_body_atr")
        ensure_in_range(self.break_decay, 0.0, 1.0, "break_decay")
        ensure_positive(self.scan_lookback, "scan_lookback")
        ensure_positive(self.scan_cap, "scan_cap")
        ensure_in_range(self.ob_decay, 0.0, 1.0, "ob_decay")
        ensure_in_range(self.fvg_decay, 0.0, 1.0, "fvg_decay")
        ensure_positive(self.max_live_objects, "max_live_objects")
        ensure_positive(self.max_object_age, "max_object_age")
        ensure_positive(self.min_fvg_size_atr, "min_fvg_size_atr")
        ensure_positive(self.volume_sma_length, "volume_sma_length")
        ensure_positive(self.range_sma_length, "range_sma_length")
        ensure_positive(self.zpf_fast_length, "zpf_fast_length")
        ensure_positive(self.zpf_slow_length, "zpf_slow_length")
        ensure_positive(self.htf_pivot_lookback, "htf_pivot_lookback")
        ensure_positive(self.htf_ema_length, "htf_ema_length")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission."""
        return max(
            self.atr_length,
            2 * self.pivot_lookback + 1,
            self.volume_sma_length,
            self.range_sma_length,
        )


@dataclass(slots=True)
class _OrderBlock:
    """Live order block record (AICE ``type OB``)."""

    top: float
    bot: float
    confidence: float
    quality: float
    born: int
    retests: int = 0
    was_inside: bool = False
    nested: bool = False
    imbalance: bool = False


@dataclass(slots=True)
class _FairValueGap:
    """Live fair value gap record (AICE ``type FVG``)."""

    top: float
    bot: float
    confidence: float
    quality: float
    size_atr: float
    born: int
    fill: float = 0.0


@dataclass(slots=True)
class _Series:
    """Precomputed per-bar inputs shared by the fold steps."""

    bars: list[Bar]
    atr: list[float | None]
    volumes: list[float]
    volume_sma: list[float | None]
    ranges: list[float]
    range_sma: list[float | None]
    momentum_fast: list[float | None]
    momentum_slow: list[float | None]
    htf: list[HtfContext | None] = field(default_factory=list)
    equilibriums: list[float | None] = field(default_factory=list)

    def local_momentum(self, index: int, *, bullish: bool) -> bool:
        """AICE ``local_bull/bear``: zero-lag cross with confirming slope."""
        fast = self.momentum_fast[index]
        slow = self.momentum_slow[index]
        lagged = self.momentum_slow[index - _SLOPE_LAG] if index >= _SLOPE_LAG else None
        if fast is None or slow is None or lagged is None:
            return False
        slope = slow - lagged
        if bullish:
            return fast > slow and slope > 0
        return fast < slow and slope < 0


@dataclass(slots=True)
class _ZoneState:
    """Mutable fold state mirroring the AICE ``var`` arrays."""

    bull_obs: list[_OrderBlock] = field(default_factory=list)
    bear_obs: list[_OrderBlock] = field(default_factory=list)
    bull_fvgs: list[_FairValueGap] = field(default_factory=list)
    bear_fvgs: list[_FairValueGap] = field(default_factory=list)
    prev_new_bull_fvg: bool = False
    prev_new_bear_fvg: bool = False


def _weighted(terms: tuple[float, ...], weights: tuple[float, ...]) -> float:
    """Clamped weighted sum shared by both quality formulas."""
    total = sum(term * weight for term, weight in zip(terms, weights, strict=True))
    return clamp(total, 0.0, 1.0)


class OrderBlockEngine:
    """Computes the OB/FVG family over a confirmed-bar window."""

    def __init__(
        self,
        *,
        params: OrderBlockParams,
        clock: Clock,
        macro_timeframes: tuple[Timeframe, Timeframe] | None = None,
    ) -> None:
        self._params = params
        self._clock = clock
        self._macro = macro_timeframes

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
        """Macro series feeding the HTF quality terms (when configured)."""
        if self._macro is None:
            return ()
        return ((symbol, self._macro[0]), (symbol, self._macro[1]))

    def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Auxiliary-free path: HTF terms use AICE's undecided neutrals."""
        return self.compute_with_context(bars, {}, context)

    def compute_with_context(
        self,
        bars: Sequence[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Fold the window, emitting one feature set per post-warmup bar."""
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
        params = self._params
        volumes = [float(bar.volume.value) for bar in bars]
        ranges = [float(bar.high.value) - float(bar.low.value) for bar in bars]
        closes = [float(bar.close.value) for bar in bars]
        series = _Series(
            bars=bars,
            atr=wilder_atr(bars, params.atr_length),
            volumes=volumes,
            volume_sma=sma(volumes, params.volume_sma_length),
            ranges=ranges,
            range_sma=sma(ranges, params.range_sma_length),
            momentum_fast=zero_lag_filter(closes, params.zpf_fast_length),
            momentum_slow=zero_lag_filter(closes, params.zpf_slow_length),
            htf=self._htf_series(bars, auxiliary, context),
        )
        fold = StructureFold(
            pivots=PivotTracker(lookback=params.pivot_lookback),
            displacement_body_atr=params.displacement_body_atr,
            break_decay=params.break_decay,
        )
        state = _ZoneState()
        features: list[Feature] = []
        for index, bar in enumerate(bars):
            snapshot = self._step(state, fold, series, index)
            if index >= params.warmup_bars and series.atr[index] is not None:
                features.extend(self._emit(bar, snapshot))
        return features

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

    def _step(
        self,
        state: _ZoneState,
        fold: StructureFold,
        series: _Series,
        index: int,
    ) -> dict[str, float]:
        """One bar in AICE script order: OBs, then FVGs, then BPR."""
        signals = fold.update(series.bars, index, series.atr[index])
        series.equilibriums.append(signals.equilibrium)
        raw_bull_gap, raw_bear_gap = self._raw_gaps(series, index)

        self._create_order_blocks(state, series, index, signals, raw_bull_gap, raw_bear_gap)
        bull_breaker = self._age_order_blocks(state, series, index, bullish=True)
        bear_breaker = self._age_order_blocks(state, series, index, bullish=False)
        ob_long = self._aggregate_order_blocks(state.bull_obs, series, index)
        ob_short = self._aggregate_order_blocks(state.bear_obs, series, index)

        new_bull_fvg = raw_bull_gap and self._create_fvg(state, series, index, signals, True)
        new_bear_fvg = raw_bear_gap and self._create_fvg(state, series, index, signals, False)
        ifvg_bear = self._age_fvgs(state, series, index, bullish=True)
        ifvg_bull = self._age_fvgs(state, series, index, bullish=False)
        fvg_long = self._aggregate_fvgs(state.bull_fvgs, series, index)
        fvg_short = self._aggregate_fvgs(state.bear_fvgs, series, index)

        bpr_bull = new_bull_fvg and state.prev_new_bear_fvg
        bpr_bear = new_bear_fvg and state.prev_new_bull_fvg
        state.prev_new_bull_fvg = new_bull_fvg
        state.prev_new_bear_fvg = new_bear_fvg

        return self._snapshot(
            state=state,
            ob_long=ob_long,
            ob_short=ob_short,
            breakers=(bull_breaker, bear_breaker),
            new_fvgs=(new_bull_fvg, new_bear_fvg),
            fvg_long=fvg_long,
            fvg_short=fvg_short,
            ifvgs=(ifvg_bull, ifvg_bear),
            bprs=(bpr_bull, bpr_bear),
        )

    def _raw_gaps(self, series: _Series, index: int) -> tuple[bool, bool]:
        """Three-bar gap flags (AICE lines 1286-1287)."""
        if index < 2:
            return False, False
        bar = series.bars[index]
        high_two_back = float(series.bars[index - 2].high.value)
        low_two_back = float(series.bars[index - 2].low.value)
        raw_bull = float(bar.low.value) > high_two_back
        raw_bear = float(bar.high.value) < low_two_back
        return raw_bull, raw_bear

    # --- Order blocks --------------------------------------------------------

    def _create_order_blocks(
        self,
        state: _ZoneState,
        series: _Series,
        index: int,
        signals: StructureSignals,
        raw_bull_gap: bool,
        raw_bear_gap: bool,
    ) -> None:
        """Scan for the best opposing candle on a structure break."""
        if index <= _MIN_CREATION_INDEX:
            return
        htf = series.htf[index]
        if signals.bos_up or signals.choch_up:
            imbalance = raw_bull_gap or signals.is_displacement
            mtf_quality = self._htf_quality(htf, bullish=True)
            zone = self._scan_order_block(
                state.bull_obs, series, index, signals, imbalance, mtf_quality, True
            )
            if zone is not None:
                self._push_zone(state.bull_obs, zone)
        if signals.bos_down or signals.choch_down:
            imbalance = raw_bear_gap or signals.is_displacement
            mtf_quality = self._htf_quality(htf, bullish=False)
            zone = self._scan_order_block(
                state.bear_obs, series, index, signals, imbalance, mtf_quality, False
            )
            if zone is not None:
                self._push_zone(state.bear_obs, zone)

    def _push_zone(self, zones: list[_OrderBlock], zone: _OrderBlock) -> None:
        """Append and evict the oldest above the live cap (Pine shift)."""
        zones.append(zone)
        if len(zones) > self._params.max_live_objects:
            zones.pop(0)

    def _htf_quality(self, htf: HtfContext | None, *, bullish: bool) -> float:
        """AICE mtfQ/htfQ ternary; missing macro reads as undecided."""
        if htf is None or htf.alignment == 0:
            return _HTF_NEUTRAL_QUALITY
        favorable = htf.bull_context if bullish else htf.bear_context
        return 1.0 if favorable else _HTF_AGAINST_QUALITY

    def _htf_series(
        self,
        bars: list[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> list[HtfContext | None]:
        """HTF context per chart bar; all-None without macro series."""
        if self._macro is None:
            return [None] * len(bars)
        macro1 = list(auxiliary.get((context.symbol, self._macro[0]), ()))
        macro2 = list(auxiliary.get((context.symbol, self._macro[1]), ()))
        if not macro1 and not macro2:
            return [None] * len(bars)
        return htf_context_series(
            bars,
            macro1,
            macro2,
            pivot_lookback=self._params.htf_pivot_lookback,
            ema_length=self._params.htf_ema_length,
        )

    def _scan_order_block(
        self,
        zones: list[_OrderBlock],
        series: _Series,
        index: int,
        signals: StructureSignals,
        imbalance: bool,
        mtf_quality: float,
        bullish: bool,
    ) -> _OrderBlock | None:
        """Best-quality opposing candle within the scan window."""
        params = self._params
        max_look = min(params.scan_lookback, params.scan_cap, index)
        best: _OrderBlock | None = None
        best_quality = -1.0
        for offset in range(1, max_look + 1):
            candidate = index - offset
            scored = self._candidate_quality(
                zones, series, candidate, signals, imbalance, mtf_quality, bullish
            )
            if scored is None:
                continue
            quality, nested = scored
            if quality > best_quality:
                best_quality = quality
                best = _OrderBlock(
                    top=float(series.bars[candidate].high.value),
                    bot=float(series.bars[candidate].low.value),
                    confidence=max(_MIN_OB_CONFIDENCE, quality),
                    quality=quality,
                    born=index,
                    nested=nested,
                    imbalance=imbalance,
                )
        return best

    def _candidate_quality(
        self,
        zones: list[_OrderBlock],
        series: _Series,
        candidate: int,
        signals: StructureSignals,
        imbalance: bool,
        mtf_quality: float,
        bullish: bool,
    ) -> tuple[float, bool] | None:
        """f_ob_quality for one candidate bar; None if wrong direction."""
        bar = series.bars[candidate]
        close = float(bar.close.value)
        open_ = float(bar.open.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        opposing = close < open_ if bullish else close > open_
        if not opposing:
            return None
        nested = any(high <= zone.top and low >= zone.bot for zone in zones)
        atr = series.atr[candidate]
        body_atr = abs(close - open_) / atr if atr is not None and atr > 0 else 0.0
        volume_mean = series.volume_sma[candidate]
        rvol = (
            series.volumes[candidate] / volume_mean
            if volume_mean is not None and volume_mean > 0
            else 1.0
        )
        range_mean = series.range_sma[candidate]
        narrow = range_mean is not None and range_mean > 0 and series.ranges[candidate] < range_mean
        absorption = 1.0 if rvol > _ABSORPTION_RVOL and narrow else 0.0
        location = self._candidate_location(series, candidate, high, low, bullish)
        displacement_quality = clamp(
            signals.body_atr / self._params.displacement_body_atr, 0.0, 1.0
        )
        terms = (
            clamp(body_atr / _QUALITY_ATR_NORM, 0.0, 1.0),
            clamp(rvol / _RVOL_NORM, 0.0, 1.0),
            signals.break_quality,
            displacement_quality,
            absorption,
            location,
            1.0 if nested else 0.0,
            1.0 if imbalance else 0.0,
            mtf_quality,
        )
        return _weighted(terms, _OB_QUALITY_WEIGHTS), nested

    def _candidate_location(
        self,
        series: _Series,
        candidate: int,
        high: float,
        low: float,
        bullish: bool,
    ) -> float:
        """locQ: candidate side vs the dealing-range equilibrium then."""
        equilibrium = series.equilibriums[candidate]
        if equilibrium is None:
            return _LOCATION_UNKNOWN_QUALITY
        in_zone = low < equilibrium if bullish else high > equilibrium
        return 1.0 if in_zone else _LOCATION_MISS_QUALITY

    def _age_order_blocks(
        self,
        state: _ZoneState,
        series: _Series,
        index: int,
        *,
        bullish: bool,
    ) -> bool:
        """Decay, retest, mitigate and expire one side's order blocks."""
        params = self._params
        bar = series.bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        zones = state.bull_obs if bullish else state.bear_obs
        survivors: list[_OrderBlock] = []
        breaker = False
        for zone in zones:
            inside = low <= zone.top and high >= zone.bot
            age = index - zone.born
            zone.confidence = clamp(zone.confidence * params.ob_decay, 0.0, 1.0)
            if inside and not zone.was_inside:
                zone.retests += 1
                bonus = _RETEST_BONUS * max(0.0, 1.0 - zone.retests * _RETEST_PENALTY)
                zone.confidence = clamp(zone.confidence + bonus, 0.0, 1.0)
            zone.was_inside = inside
            mitigated = close < zone.bot if bullish else close > zone.top
            expired = age > params.max_object_age or zone.confidence < _EXPIRY_CONFIDENCE
            if mitigated:
                breaker = True
            elif not expired:
                survivors.append(zone)
        if bullish:
            state.bull_obs = survivors
        else:
            state.bear_obs = survivors
        return breaker

    def _aggregate_order_blocks(
        self,
        zones: list[_OrderBlock],
        series: _Series,
        index: int,
    ) -> tuple[float, float, bool, _OrderBlock | None]:
        """Best zone by effective score: (confidence, freshness,
        inside, zone). The winning zone's boundary is AICE's
        ``ob_long_bot``/``ob_short_top`` (lines 1459/1477)."""
        params = self._params
        bar = series.bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        atr = series.atr[index]
        best_score = -1.0
        confidence = freshness = 0.0
        inside_best = False
        best_zone: _OrderBlock | None = None
        for zone in zones:
            inside = low <= zone.top and high >= zone.bot
            proximity = self._proximity(close, zone.top, zone.bot, atr)
            retest_quality = clamp(
                1.0 - max(zone.retests - 1, 0) * _RETEST_PENALTY, _RETEST_FLOOR, 1.0
            )
            nested_quality = _NESTED_MULTIPLIER if zone.nested else 1.0
            effective = (
                zone.confidence
                * (_BASE_SHARE + _PROXIMITY_SHARE * proximity)
                * retest_quality
                * nested_quality
            ) + (_INSIDE_OB_BONUS * zone.quality if inside else 0.0)
            if effective > best_score:
                best_score = effective
                confidence = clamp(effective, 0.0, 1.0)
                age = index - zone.born
                freshness = clamp(1.0 - age / max(params.max_object_age, 1), 0.0, 1.0)
                inside_best = inside
                best_zone = zone
        return confidence, freshness, inside_best, best_zone

    def _proximity(self, close: float, top: float, bot: float, atr: float | None) -> float:
        """clamp(1 - distance / (ATR x 3)); zero without a usable ATR."""
        if atr is None or atr <= 0:
            return 0.0
        if close > top:
            distance = close - top
        elif close < bot:
            distance = bot - close
        else:
            distance = 0.0
        return clamp(1.0 - distance / (atr * _PROXIMITY_ATR), 0.0, 1.0)

    # --- Fair value gaps ------------------------------------------------------

    def _create_fvg(
        self,
        state: _ZoneState,
        series: _Series,
        index: int,
        signals: StructureSignals,
        bullish: bool,
    ) -> bool:
        """Score and store a qualified three-bar gap; True when created."""
        params = self._params
        bar = series.bars[index]
        atr = series.atr[index]
        if bullish:
            top = float(bar.low.value)
            bot = float(series.bars[index - 2].high.value)
        else:
            top = float(series.bars[index - 2].low.value)
            bot = float(bar.high.value)
        size_atr = (top - bot) / atr if atr is not None and atr > 0 else 0.0
        if size_atr < params.min_fvg_size_atr:
            return False
        volume_mean = series.volume_sma[index]
        rvol = (
            series.volumes[index] / volume_mean
            if volume_mean is not None and volume_mean > 0
            else 1.0
        )
        local = series.local_momentum(index, bullish=bullish)
        aligned = signals.trend_direction == (1 if bullish else -1)
        trend_quality = (
            _TREND_LOCAL_QUALITY
            if local
            else _TREND_ALIGNED_QUALITY
            if aligned
            else _TREND_AGAINST_QUALITY
        )
        htf = series.htf[index]
        in_zone = signals.in_discount if bullish else signals.in_premium
        htf_in_zone = (
            htf is not None and (htf.in_discount if bullish else htf.in_premium)
        )
        location_quality = (
            1.0
            if in_zone
            else _HTF_LOCATION_QUALITY
            if htf_in_zone
            else _LOCATION_MISS_QUALITY
        )
        terms = (
            clamp(size_atr / _QUALITY_ATR_NORM, 0.0, 1.0),
            clamp(signals.body_atr / params.displacement_body_atr, 0.0, 1.0),
            clamp(rvol / _RVOL_NORM, 0.0, 1.0),
            trend_quality,
            location_quality,
            self._htf_quality(htf, bullish=bullish),
        )
        quality = _weighted(terms, _FVG_QUALITY_WEIGHTS)
        gaps = state.bull_fvgs if bullish else state.bear_fvgs
        gaps.append(
            _FairValueGap(
                top=top,
                bot=bot,
                confidence=max(_MIN_FVG_CONFIDENCE, quality),
                quality=quality,
                size_atr=size_atr,
                born=index,
            )
        )
        if len(gaps) > params.max_live_objects:
            gaps.pop(0)
        return True

    def _age_fvgs(
        self,
        state: _ZoneState,
        series: _Series,
        index: int,
        *,
        bullish: bool,
    ) -> bool:
        """Fill, decay, invert and expire one side's gaps.

        Pine iterates newest to oldest and assigns the IFVG flag from
        each *removed* gap's ``inverted`` value, so the oldest removal
        wins; replicated exactly for parity (see module docstring).
        """
        params = self._params
        bar = series.bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        gaps = state.bull_fvgs if bullish else state.bear_fvgs
        survivors: list[_FairValueGap] = []
        flag = False
        for gap in reversed(gaps):
            width = gap.top - gap.bot
            fill_now = self._fill_fraction(gap, width, high, low, bullish)
            gap.fill = max(gap.fill, clamp(fill_now, 0.0, 1.0))
            gap.confidence = clamp(gap.confidence * params.fvg_decay, 0.0, 1.0)
            inverted = close < gap.bot if bullish else close > gap.top
            expired = index - gap.born > params.max_object_age or (
                gap.confidence < _EXPIRY_CONFIDENCE
            )
            if inverted or expired:
                flag = inverted
            else:
                survivors.append(gap)
        survivors.reverse()
        if bullish:
            state.bull_fvgs = survivors
        else:
            state.bear_fvgs = survivors
        return flag

    def _fill_fraction(
        self,
        gap: _FairValueGap,
        width: float,
        high: float,
        low: float,
        bullish: bool,
    ) -> float:
        """How much of the gap this bar covered (AICE lines 1522, 1541)."""
        if width <= 0:
            return 0.0
        if bullish:
            if low <= gap.bot:
                return 1.0
            return (gap.top - low) / width if low < gap.top else 0.0
        if high >= gap.top:
            return 1.0
        return (high - gap.bot) / width if high > gap.bot else 0.0

    def _aggregate_fvgs(
        self,
        gaps: list[_FairValueGap],
        series: _Series,
        index: int,
    ) -> tuple[float, bool]:
        """Best gap by fill-discounted score: (confidence, inside)."""
        bar = series.bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        atr = series.atr[index]
        best_score = -1.0
        confidence = 0.0
        inside_best = False
        for gap in gaps:
            inside = low <= gap.top and high >= gap.bot
            proximity = self._proximity(close, gap.top, gap.bot, atr)
            score = (
                gap.confidence
                * (_BASE_SHARE + _PROXIMITY_SHARE * proximity)
                * (1.0 - _FILL_PENALTY * gap.fill)
            ) + (_INSIDE_FVG_BONUS * gap.quality if inside else 0.0)
            if score > best_score:
                best_score = score
                confidence = clamp(score, 0.0, 1.0)
                inside_best = inside
        return confidence, inside_best

    # --- Snapshot & emission --------------------------------------------------

    def _snapshot(
        self,
        *,
        state: _ZoneState,
        ob_long: tuple[float, float, bool, _OrderBlock | None],
        ob_short: tuple[float, float, bool, _OrderBlock | None],
        breakers: tuple[bool, bool],
        new_fvgs: tuple[bool, bool],
        fvg_long: tuple[float, bool],
        fvg_short: tuple[float, bool],
        ifvgs: tuple[bool, bool],
        bprs: tuple[bool, bool],
    ) -> dict[str, float]:
        values: dict[str, float] = {}
        # Zone levels (Phase 10): the best zone's protective boundary,
        # emitted only while a zone is live - an absent key is the
        # AICE na-branch (ob_long_bot / ob_short_top stay na).
        if ob_long[3] is not None:
            values["orderblocks.bull_ob_bottom"] = ob_long[3].bot
        if ob_short[3] is not None:
            values["orderblocks.bear_ob_top"] = ob_short[3].top
        return values | {
            "orderblocks.ob_long_confidence": ob_long[0],
            "orderblocks.ob_short_confidence": ob_short[0],
            "orderblocks.ob_long_freshness": ob_long[1],
            "orderblocks.ob_short_freshness": ob_short[1],
            "orderblocks.in_bull_ob": 1.0 if ob_long[2] else 0.0,
            "orderblocks.in_bear_ob": 1.0 if ob_short[2] else 0.0,
            "orderblocks.bull_ob_count": float(len(state.bull_obs)),
            "orderblocks.bear_ob_count": float(len(state.bear_obs)),
            "orderblocks.bull_breaker": 1.0 if breakers[0] else 0.0,
            "orderblocks.bear_breaker": 1.0 if breakers[1] else 0.0,
            "orderblocks.new_bull_fvg": 1.0 if new_fvgs[0] else 0.0,
            "orderblocks.new_bear_fvg": 1.0 if new_fvgs[1] else 0.0,
            "orderblocks.fvg_long_confidence": fvg_long[0],
            "orderblocks.fvg_short_confidence": fvg_short[0],
            "orderblocks.in_bull_fvg": 1.0 if fvg_long[1] else 0.0,
            "orderblocks.in_bear_fvg": 1.0 if fvg_short[1] else 0.0,
            "orderblocks.bull_fvg_count": float(len(state.bull_fvgs)),
            "orderblocks.bear_fvg_count": float(len(state.bear_fvgs)),
            "orderblocks.ifvg_bull": 1.0 if ifvgs[0] else 0.0,
            "orderblocks.ifvg_bear": 1.0 if ifvgs[1] else 0.0,
            "orderblocks.bpr_bull": 1.0 if bprs[0] else 0.0,
            "orderblocks.bpr_bear": 1.0 if bprs[1] else 0.0,
        }

    def _emit(self, bar: Bar, values: dict[str, float]) -> list[Feature]:
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
                normalized_value=self._normalize(name, raw),
                weight=Weight(1.0),
                confidence=Confidence(1.0),
                reliability=Reliability(1.0),
                source=_SOURCE,
                computed_at=computed_at,
            )
            for name, raw in values.items()
        ]

    def _normalize(self, name: str, raw: float) -> float:
        """Map raw values into [-1, 1] per feature semantics."""
        if name.endswith(("_bottom", "_top")):
            # Absolute price levels: consumers read the raw value; the
            # normalized channel is neutral by definition.
            return 0.0
        if name.endswith("_count"):
            share = clamp(raw / self._params.max_live_objects, 0.0, 1.0)
            return share * 2.0 - 1.0
        if name.endswith(("_confidence", "_freshness")):
            return clamp(raw, 0.0, 1.0) * 2.0 - 1.0
        # Binary flags are already within [-1, 1].
        return clamp(raw, -1.0, 1.0)
