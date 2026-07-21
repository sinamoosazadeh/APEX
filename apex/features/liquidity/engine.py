"""Liquidity feature family - migrated from AICE (Book VI).

Faithful port of the AICE Pine v6 liquidity block (spec lines
~1195-1244), per the Book II ch. 2 migration matrix:

- three pivot scales: chart (8), internal (3), external (21), each
  with equal-high/low detection within ``ATR x tolerance``;
- liquidity confidence pools: decayed by ``liq_decay`` every bar,
  bumped when equal extremes print (external 0.45, internal 0.25,
  chart 0.35 - the exact AICE ternary priority), capped at 1, and
  reset to zero when the corresponding side is swept;
- resting liquidity composite:
  ``clamp(pool_pre*0.35 + int_eq*0.20 + ext_eq*0.30 + proximity*0.15)``;
- external extremes: highest/lowest of the previous ``lookback x 8``
  bars (Pine ``ta.highest(high, n)[1]``), with ATR-scaled proximity
  ``clamp(1 - |extreme - close| / (ATR x 10))``;
- internal bias (``f_struct_pack``): close beyond the last internal
  pivot, else close versus EMA(50);
- sweeps of the chart swings with wick-efficiency
  ``(close - low) / range``; stop hunts (sweep + equal extremes);
- inducement: a sweep aligned with chart trend and internal bias.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Final

from apex.core.context import MarketContext
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
    ema,
    rolling_extremes,
    wilder_atr,
)

FAMILY = "liquidity"
_SOURCE = "apex.features.liquidity"

# Pool bump sizes by scale (AICE lines 1226/1229 ternary priority).
_BUMP_EXTERNAL: Final[float] = 0.45
_BUMP_INTERNAL: Final[float] = 0.25
_BUMP_CHART: Final[float] = 0.35
# Resting liquidity composite weights (AICE lines 1234-1235).
_REST_POOL_W: Final[float] = 0.35
_REST_INTERNAL_W: Final[float] = 0.20
_REST_EXTERNAL_W: Final[float] = 0.30
_REST_PROXIMITY_W: Final[float] = 0.15
# Proximity horizon in ATR units (AICE lines 1217-1218).
_PROXIMITY_ATR: Final[float] = 10.0
# External extreme window = lookback x 8 (AICE f_struct_pack).
_EXTREME_WINDOW_MULTIPLE: Final[int] = 8

FEATURE_NAMES: tuple[str, ...] = (
    "liquidity.pool_high_confidence",
    "liquidity.pool_low_confidence",
    "liquidity.resting_high",
    "liquidity.resting_low",
    "liquidity.equal_highs_internal",
    "liquidity.equal_lows_internal",
    "liquidity.equal_highs_external",
    "liquidity.equal_lows_external",
    "liquidity.external_high_proximity",
    "liquidity.external_low_proximity",
    "liquidity.sweep_high_efficiency",
    "liquidity.sweep_low_efficiency",
    "liquidity.stop_hunt_high",
    "liquidity.stop_hunt_low",
    "liquidity.inducement_long",
    "liquidity.inducement_short",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class LiquidityParams:
    """Tunables of the liquidity family (AICE input defaults)."""

    chart_lookback: int = 8
    internal_lookback: int = 3
    external_lookback: int = 21
    atr_length: int = 14
    equal_tolerance_atr: float = 0.10
    liquidity_decay: float = 0.990
    ema_length: int = 50

    def __post_init__(self) -> None:
        ensure_positive(self.chart_lookback, "chart_lookback")
        ensure_positive(self.internal_lookback, "internal_lookback")
        ensure_positive(self.external_lookback, "external_lookback")
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.equal_tolerance_atr, "equal_tolerance_atr")
        ensure_in_range(self.liquidity_decay, 0.0, 1.0, "liquidity_decay")
        ensure_positive(self.ema_length, "ema_length")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission."""
        return max(
            self.atr_length,
            2 * self.external_lookback + 1,
            self.ema_length,
        )


@dataclass(slots=True)
class _LiquidityState:
    """Mutable fold state mirroring the AICE ``var`` block."""

    trend_dir: int = 0
    pool_high: float = 0.0
    pool_low: float = 0.0


class LiquidityEngine:
    """Computes the liquidity family over a confirmed-bar window."""

    def __init__(self, *, params: LiquidityParams, clock: Clock) -> None:
        self._params = params
        self._clock = clock

    @property
    def family(self) -> str:
        """Feature family identifier."""
        return FAMILY

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Every feature this engine emits."""
        return FEATURE_NAMES

    def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Fold the window, emitting one feature set per post-warmup bar."""
        try:
            features = self._compute_all(list(bars))
        except ApexError as error:
            return Result.failure(error)
        return Result.success(tuple(features))

    # --- Fold ---------------------------------------------------------------

    def _compute_all(self, bars: list[Bar]) -> list[Feature]:
        self._require_confirmed_series(bars)
        params = self._params
        state = _LiquidityState()
        chart = PivotTracker(lookback=params.chart_lookback)
        internal = PivotTracker(lookback=params.internal_lookback)
        external = PivotTracker(lookback=params.external_lookback)
        atr_series = wilder_atr(bars, params.atr_length)
        ema_series = ema([float(bar.close.value) for bar in bars], params.ema_length)
        features: list[Feature] = []
        for index, bar in enumerate(bars):
            snapshot = self._step(
                state,
                bars,
                index,
                atr=atr_series[index],
                ema_value=ema_series[index],
                chart=chart,
                internal=internal,
                external=external,
            )
            if index >= params.warmup_bars and atr_series[index] is not None:
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
        state: _LiquidityState,
        bars: list[Bar],
        index: int,
        *,
        atr: float | None,
        ema_value: float | None,
        chart: PivotTracker,
        internal: PivotTracker,
        external: PivotTracker,
    ) -> dict[str, float]:
        params = self._params
        bar = bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        prev_close = float(bars[index - 1].close.value) if index > 0 else close
        effective_atr = atr if atr is not None and atr > 0 else None
        tolerance = (effective_atr or 0.0) * params.equal_tolerance_atr

        chart_high_new, chart_low_new = chart.update(bar)
        internal_high_new, internal_low_new = internal.update(bar)
        external_high_new, external_low_new = external.update(bar)

        eq_high_chart = self._is_equal(chart, chart_high_new, tolerance, side="high")
        eq_low_chart = self._is_equal(chart, chart_low_new, tolerance, side="low")
        eq_high_int = self._is_equal(internal, internal_high_new, tolerance, side="high")
        eq_low_int = self._is_equal(internal, internal_low_new, tolerance, side="low")
        eq_high_ext = self._is_equal(external, external_high_new, tolerance, side="high")
        eq_low_ext = self._is_equal(external, external_low_new, tolerance, side="low")

        self._update_trend(state, chart, close, prev_close)
        internal_bias = self._internal_bias(internal, close, ema_value)

        window = params.external_lookback * _EXTREME_WINDOW_MULTIPLE
        ext_hi, ext_lo = rolling_extremes(bars, index, window)
        high_prox = (
            clamp(1.0 - abs(ext_hi - close) / (effective_atr * _PROXIMITY_ATR), 0.0, 1.0)
            if ext_hi is not None and effective_atr
            else 0.0
        )
        low_prox = (
            clamp(1.0 - abs(close - ext_lo) / (effective_atr * _PROXIMITY_ATR), 0.0, 1.0)
            if ext_lo is not None and effective_atr
            else 0.0
        )

        # Pools: decay, then bump with the AICE ternary priority.
        state.pool_low *= params.liquidity_decay
        state.pool_high *= params.liquidity_decay
        if eq_low_chart or eq_low_int or eq_low_ext:
            bump = _BUMP_EXTERNAL if eq_low_ext else _BUMP_INTERNAL if eq_low_int else _BUMP_CHART
            state.pool_low = min(state.pool_low + bump, 1.0)
        if eq_high_chart or eq_high_int or eq_high_ext:
            bump = (
                _BUMP_EXTERNAL if eq_high_ext else _BUMP_INTERNAL if eq_high_int else _BUMP_CHART
            )
            state.pool_high = min(state.pool_high + bump, 1.0)

        pool_low_pre = state.pool_low
        pool_high_pre = state.pool_high

        rest_low = clamp(
            pool_low_pre * _REST_POOL_W
            + (_REST_INTERNAL_W if eq_low_int else 0.0)
            + (_REST_EXTERNAL_W if eq_low_ext else 0.0)
            + low_prox * _REST_PROXIMITY_W,
            0.0,
            1.0,
        )
        rest_high = clamp(
            pool_high_pre * _REST_POOL_W
            + (_REST_INTERNAL_W if eq_high_int else 0.0)
            + (_REST_EXTERNAL_W if eq_high_ext else 0.0)
            + high_prox * _REST_PROXIMITY_W,
            0.0,
            1.0,
        )

        sweep_high = (
            chart.last_high is not None and high > chart.last_high and close < chart.last_high
        )
        sweep_low = (
            chart.last_low is not None and low < chart.last_low and close > chart.last_low
        )
        bar_range = high - low
        sweep_low_eff = (close - low) / bar_range if sweep_low and bar_range > 0 else 0.0
        sweep_high_eff = (high - close) / bar_range if sweep_high and bar_range > 0 else 0.0
        stop_hunt_high = sweep_high and eq_high_chart
        stop_hunt_low = sweep_low and eq_low_chart

        inducement_long = sweep_low and state.trend_dir >= 0 and internal_bias >= 0
        inducement_short = sweep_high and state.trend_dir <= 0 and internal_bias <= 0

        if sweep_low:
            state.pool_low = 0.0
        if sweep_high:
            state.pool_high = 0.0

        return {
            "liquidity.pool_high_confidence": state.pool_high,
            "liquidity.pool_low_confidence": state.pool_low,
            "liquidity.resting_high": rest_high,
            "liquidity.resting_low": rest_low,
            "liquidity.equal_highs_internal": 1.0 if eq_high_int else 0.0,
            "liquidity.equal_lows_internal": 1.0 if eq_low_int else 0.0,
            "liquidity.equal_highs_external": 1.0 if eq_high_ext else 0.0,
            "liquidity.equal_lows_external": 1.0 if eq_low_ext else 0.0,
            "liquidity.external_high_proximity": high_prox,
            "liquidity.external_low_proximity": low_prox,
            "liquidity.sweep_high_efficiency": sweep_high_eff,
            "liquidity.sweep_low_efficiency": sweep_low_eff,
            "liquidity.stop_hunt_high": 1.0 if stop_hunt_high else 0.0,
            "liquidity.stop_hunt_low": 1.0 if stop_hunt_low else 0.0,
            "liquidity.inducement_long": 1.0 if inducement_long else 0.0,
            "liquidity.inducement_short": 1.0 if inducement_short else 0.0,
        }

    @staticmethod
    def _is_equal(
        tracker: PivotTracker,
        confirmed: bool,
        tolerance: float,
        *,
        side: str,
    ) -> bool:
        if not confirmed:
            return False
        last = tracker.last_high if side == "high" else tracker.last_low
        prev = tracker.prev_high if side == "high" else tracker.prev_low
        return last is not None and prev is not None and abs(last - prev) <= tolerance

    @staticmethod
    def _update_trend(
        state: _LiquidityState,
        chart: PivotTracker,
        close: float,
        prev_close: float,
    ) -> None:
        """Chart trend state machine (same cross semantics as structure)."""
        broke_up = (
            chart.last_high is not None
            and close > chart.last_high
            and prev_close <= chart.last_high
        )
        if broke_up:
            state.trend_dir = 1
        if chart.last_low is not None and close < chart.last_low and prev_close >= chart.last_low:
            state.trend_dir = -1

    @staticmethod
    def _internal_bias(
        internal: PivotTracker,
        close: float,
        ema_value: float | None,
    ) -> int:
        """AICE ``f_struct_pack`` bias: pivots first, EMA fallback."""
        if internal.last_high is not None and close > internal.last_high:
            return 1
        if internal.last_low is not None and close < internal.last_low:
            return -1
        if ema_value is not None:
            if close > ema_value:
                return 1
            if close < ema_value:
                return -1
        return 0

    # --- Emission -----------------------------------------------------------

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
                normalized_value=self._normalize(raw),
                weight=Weight(1.0),
                confidence=Confidence(1.0),
                reliability=Reliability(1.0),
                source=_SOURCE,
                computed_at=computed_at,
            )
            for name, raw in values.items()
        ]

    @staticmethod
    def _normalize(raw: float) -> float:
        """All liquidity values live in [0, 1]; map onto [-1, 1]."""
        return clamp(raw, 0.0, 1.0) * 2.0 - 1.0
