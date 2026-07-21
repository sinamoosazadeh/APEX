"""Statistical feature family - migrated from AICE (closes Phase 4).

Faithful port of three AICE blocks (Book VI):

- **Regime detection** (spec lines 1021-1056): ADX against its trend
  threshold, Kaufman efficiency ratio, the variance-ratio Hurst proxy
  ``clamp(0.5 + (VR - 1) * 0.20)``, normalized-return entropy, price-
  time slope quality ``|corr(close, bar_index)|``, volatility
  clustering ``corr(|r|, |r[1]|)``, the five-term ``trend_evidence``
  weighted sum, the trending/ranging/transition regime split and the
  composite ``market_entropy``.
- **Candle DNA** (lines 1633-1678): direction persistence over five
  bars, body percent-rank, three-bar impulse efficiency, wick
  rejections, the weighted ``dna_bull/bear`` composites, engulfing/
  pin/hammer/shooting-star/doji patterns, sequence bias and
  high-conviction direction flips.
- **Kinetic oscillators** (lines 1680-1702): WaveTrend (channel EMA,
  deviation-normalized CI, signal SMA), the Schaff trend cycle
  (double-stochastic MACD with half-speed smoothing) and CCI, with
  overbought/oversold thresholds scaled by the shared volatility
  regime factor, composed into the AICE ``kin_long/kin_short`` scores.

All values come from confirmed bars only; the engine emits nothing
during warmup.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import log

from apex.core.context import MarketContext
from apex.core.exceptions import ApexError, FeatureError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import ensure_positive
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.calculations import (
    adx,
    cci,
    clamp,
    correlation,
    ema,
    entropy01,
    min_max_scale,
    percent_rank,
    schaff_trend_cycle,
    sma,
    stdev,
    valid_tail,
    volatility_regime_factor,
    wilder_atr,
)

FAMILY = "statistical"
_SOURCE = "apex.features.statistical"

# trend_evidence weights (AICE lines 1042-1047): ADX, efficiency,
# hurst, slope quality, inverse entropy.
_TREND_WEIGHTS = (0.30, 0.25, 0.20, 0.15, 0.10)
_TRENDING_THRESHOLD, _RANGING_THRESHOLD = 0.55, 0.45
# market_entropy composition (line 1053).
_ENTROPY_RETURN_SHARE = 0.60
_ENTROPY_TRANSITION_BONUS = 0.25
_ENTROPY_COMPRESSION_BONUS = 0.15
# Range state thresholds (lines 1039-1040).
_EXPANSION_RATIO, _COMPRESSION_RATIO = 1.5, 0.6
# Hurst proxy shape (line 1029).
_HURST_SLOPE = 0.20
# Candle DNA weights (lines 1648-1662): close location, persistence,
# rejection, impulse, body rank.
_DNA_WEIGHTS = (0.25, 0.15, 0.20, 0.20, 0.20)
_REJECTION_NORM = 3.0
_PIN_BODY_MULTIPLE = 2.0
_DOJI_BODY_FRACTION = 0.1
_FLIP_BODY_RANK = 0.6
_DIRECTION_WINDOW = 5
# WaveTrend shape (lines 1680-1690).
_WT_CI_SCALE = 0.015
_WT_SIGNAL_LENGTH = 4
_WT_THRESHOLD = 53.0
# STC/CCI thresholds (lines 1693-1699).
_STC_LOW, _STC_HIGH = 25.0, 75.0
_CCI_THRESHOLD = 100.0
# kin_long/kin_short weights (lines 1701-1702).
_KIN_CROSS, _KIN_STATE = 0.35, 0.12
_KIN_STC_CROSS, _KIN_STC_STATE = 0.30, 0.12
_KIN_CCI_CROSS, _KIN_CCI_STATE = 0.20, 0.08
_KIN_EXTREME = 0.15

FEATURE_NAMES: tuple[str, ...] = (
    "statistical.adx",
    "statistical.efficiency_ratio",
    "statistical.hurst_proxy",
    "statistical.return_entropy",
    "statistical.slope_quality",
    "statistical.volatility_clustering",
    "statistical.trend_confidence",
    "statistical.is_trending",
    "statistical.is_ranging",
    "statistical.market_entropy",
    "statistical.persistence",
    "statistical.body_rank",
    "statistical.impulse_efficiency",
    "statistical.dna_bull",
    "statistical.dna_bear",
    "statistical.sequence_bull_bias",
    "statistical.sequence_bear_bias",
    "statistical.direction_flip_bull",
    "statistical.direction_flip_bear",
    "statistical.doji",
    "statistical.bull_engulfing",
    "statistical.bear_engulfing",
    "statistical.pin_bull",
    "statistical.pin_bear",
    "statistical.hammer",
    "statistical.shooting_star",
    "statistical.wavetrend",
    "statistical.wavetrend_bull",
    "statistical.stc",
    "statistical.cci",
    "statistical.kinetic_long",
    "statistical.kinetic_short",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticalParams:
    """Tunables of the statistical family (AICE input defaults)."""

    atr_length: int = 14
    adx_length: int = 14
    adx_trend_threshold: float = 23.0
    efficiency_length: int = 20
    entropy_window: int = 50
    normalization_window: int = 200
    rank_window: int = 200
    range_sma_length: int = 14
    wavetrend_channel: int = 10
    wavetrend_average: int = 21
    stc_cycle: int = 48
    stc_fast: int = 23
    stc_slow: int = 50
    cci_length: int = 20

    def __post_init__(self) -> None:
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.adx_length, "adx_length")
        ensure_positive(self.adx_trend_threshold, "adx_trend_threshold")
        ensure_positive(self.efficiency_length, "efficiency_length")
        ensure_positive(self.entropy_window, "entropy_window")
        ensure_positive(self.normalization_window, "normalization_window")
        ensure_positive(self.rank_window, "rank_window")
        ensure_positive(self.range_sma_length, "range_sma_length")
        ensure_positive(self.wavetrend_channel, "wavetrend_channel")
        ensure_positive(self.wavetrend_average, "wavetrend_average")
        ensure_positive(self.stc_cycle, "stc_cycle")
        ensure_positive(self.stc_fast, "stc_fast")
        ensure_positive(self.stc_slow, "stc_slow")
        ensure_positive(self.cci_length, "cci_length")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission."""
        return max(
            self.atr_length,
            2 * self.adx_length,
            self.efficiency_length,
            self.entropy_window,
            self.normalization_window,
            self.rank_window,
            self.stc_slow + self.stc_cycle,
            self.wavetrend_channel + self.wavetrend_average,
            self.cci_length,
            _DIRECTION_WINDOW,
        )


@dataclass(slots=True)
class _Series:
    """Precomputed per-bar inputs for the snapshot pass."""

    bars: list[Bar]
    closes: list[float]
    typical: list[float]
    ranges: list[float]
    bodies: list[float]
    directions: list[int]
    log_returns: list[float]
    atr: list[float | None]
    range_sma: list[float | None]
    adx: list[float | None]
    return_std: list[float | None]
    return_entropy: list[float]
    slope_quality: list[float | None]
    volatility_cluster: list[float | None]
    body_rank: list[float | None]
    volatility_factor: list[float]
    wt1: list[float | None]
    wt2: list[float | None]
    stc: list[float]
    cci: list[float | None]


class StatisticalEngine:
    """Computes the statistical family over a confirmed-bar window."""

    def __init__(self, *, params: StatisticalParams, clock: Clock) -> None:
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

    # --- Series preparation ---------------------------------------------------

    def _compute_all(self, bars: list[Bar]) -> list[Feature]:
        self._require_confirmed_series(bars)
        series = self._prepare(bars)
        params = self._params
        features: list[Feature] = []
        for index, bar in enumerate(bars):
            if index < params.warmup_bars or series.atr[index] is None:
                continue
            features.extend(self._emit(bar, self._snapshot(series, index)))
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

    def _prepare(self, bars: list[Bar]) -> _Series:
        params = self._params
        closes = [float(bar.close.value) for bar in bars]
        typical = [
            (float(bar.high.value) + float(bar.low.value) + float(bar.close.value)) / 3.0
            for bar in bars
        ]
        ranges = [float(bar.high.value) - float(bar.low.value) for bar in bars]
        bodies = [abs(float(bar.close.value) - float(bar.open.value)) for bar in bars]
        directions = [self._direction(bar) for bar in bars]
        log_returns = self._log_returns(closes)
        abs_returns = [abs(value) for value in log_returns]
        lagged_abs = [0.0, *abs_returns[:-1]]
        return_std = stdev(log_returns, params.entropy_window)
        wt1, wt2 = self._wavetrend(typical)
        return _Series(
            bars=bars,
            closes=closes,
            typical=typical,
            ranges=ranges,
            bodies=bodies,
            directions=directions,
            log_returns=log_returns,
            atr=wilder_atr(bars, params.atr_length),
            range_sma=sma(ranges, params.range_sma_length),
            adx=adx(bars, params.adx_length),
            return_std=return_std,
            return_entropy=self._return_entropy(log_returns, return_std),
            slope_quality=correlation(
                closes, [float(i) for i in range(len(bars))], params.efficiency_length
            ),
            volatility_cluster=correlation(abs_returns, lagged_abs, params.entropy_window),
            body_rank=percent_rank(bodies, params.normalization_window),
            volatility_factor=self._volatility_factor(bars),
            wt1=wt1,
            wt2=wt2,
            stc=schaff_trend_cycle(closes, params.stc_fast, params.stc_slow, params.stc_cycle),
            cci=cci(typical, params.cci_length),
        )

    def _direction(self, bar: Bar) -> int:
        close = float(bar.close.value)
        open_ = float(bar.open.value)
        if close > open_:
            return 1
        if close < open_:
            return -1
        return 0

    def _log_returns(self, closes: list[float]) -> list[float]:
        out = [0.0] * len(closes)
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i - 1] > 0:
                out[i] = log(closes[i] / closes[i - 1])
        return out

    def _return_entropy(
        self, log_returns: list[float], return_std: list[float | None]
    ) -> list[float]:
        """Entropy of the min-max-scaled normalized absolute return."""
        normalized = [
            abs(ret) / deviation
            if (deviation := return_std[i]) is not None and deviation > 0
            else 0.0
            for i, ret in enumerate(log_returns)
        ]
        scaled = min_max_scale(normalized, self._params.entropy_window)
        return [entropy01(value) for value in scaled]

    def _volatility_factor(self, bars: list[Bar]) -> list[float]:
        """Shared AICE ``vol_factor`` from ATR width over its own mean."""
        params = self._params
        atr_series = wilder_atr(bars, params.atr_length)
        offset, tail = valid_tail(atr_series)
        mean_tail = sma(tail, params.rank_window)
        out = [1.0] * len(bars)
        for i, value in enumerate(tail):
            mean = mean_tail[i]
            if mean is not None and mean > 0:
                out[offset + i] = volatility_regime_factor(value / mean)
        return out

    def _wavetrend(
        self, typical: list[float]
    ) -> tuple[list[float | None], list[float | None]]:
        """WaveTrend wt1/wt2 (AICE lines 1680-1684)."""
        params = self._params
        esa = ema(typical, params.wavetrend_channel)
        deviation_input = [
            abs(value - mean) if (mean := esa[i]) is not None else 0.0
            for i, value in enumerate(typical)
        ]
        offset, tail = valid_tail(esa)
        deviation_tail = ema(deviation_input[offset:], params.wavetrend_channel)
        ci: list[float] = [0.0] * len(typical)
        for i in range(len(tail)):
            deviation = deviation_tail[i]
            if deviation is not None and deviation > 0:
                ci[offset + i] = (typical[offset + i] - tail[i]) / (_WT_CI_SCALE * deviation)
        wt1 = ema(ci, params.wavetrend_average)
        offset1, tail1 = valid_tail(wt1)
        wt2_tail = sma(tail1, _WT_SIGNAL_LENGTH)
        wt2: list[float | None] = [None] * len(typical)
        for i, value in enumerate(wt2_tail):
            wt2[offset1 + i] = value
        return wt1, wt2

    # --- Snapshot ---------------------------------------------------------------

    def _snapshot(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        values: dict[str, tuple[float, float]] = {}
        regime = self._regime_block(series, index)
        values.update(regime)
        values.update(self._dna_block(series, index))
        values.update(self._pattern_block(series, index))
        values.update(self._kinetic_block(series, index))
        return values

    def _regime_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        params = self._params
        adx_value = series.adx[index] or 0.0
        efficiency = self._efficiency_ratio(series, index)
        hurst = self._hurst_proxy(series, index)
        entropy = series.return_entropy[index]
        slope = series.slope_quality[index]
        slope_quality = abs(slope) if slope is not None else 0.0
        cluster = series.volatility_cluster[index] or 0.0
        adx_term = 1.0 if adx_value > params.adx_trend_threshold else (
            adx_value / params.adx_trend_threshold
        )
        terms = (adx_term, efficiency, hurst, slope_quality, 1.0 - entropy)
        trend_confidence = clamp(
            sum(term * weight for term, weight in zip(terms, _TREND_WEIGHTS, strict=True)),
            0.0,
            1.0,
        )
        is_trending = trend_confidence >= _TRENDING_THRESHOLD
        is_ranging = trend_confidence < _RANGING_THRESHOLD
        is_transition = not is_trending and not is_ranging
        range_mean = series.range_sma[index]
        compression = (
            range_mean is not None
            and range_mean > 0
            and series.ranges[index] < range_mean * _COMPRESSION_RATIO
        )
        market_entropy = clamp(
            entropy * _ENTROPY_RETURN_SHARE
            + (_ENTROPY_TRANSITION_BONUS if is_transition else 0.0)
            + (_ENTROPY_COMPRESSION_BONUS if compression else 0.0),
            0.0,
            1.0,
        )
        return {
            "statistical.adx": (adx_value, clamp(adx_value / 50.0, 0.0, 1.0) * 2.0 - 1.0),
            "statistical.efficiency_ratio": (efficiency, efficiency * 2.0 - 1.0),
            "statistical.hurst_proxy": (hurst, hurst * 2.0 - 1.0),
            "statistical.return_entropy": (entropy, entropy * 2.0 - 1.0),
            "statistical.slope_quality": (slope_quality, slope_quality * 2.0 - 1.0),
            "statistical.volatility_clustering": (cluster, clamp(cluster, -1.0, 1.0)),
            "statistical.trend_confidence": (trend_confidence, trend_confidence * 2.0 - 1.0),
            "statistical.is_trending": self._binary(is_trending),
            "statistical.is_ranging": self._binary(is_ranging),
            "statistical.market_entropy": (market_entropy, market_entropy * 2.0 - 1.0),
        }

    def _efficiency_ratio(self, series: _Series, index: int) -> float:
        """Kaufman efficiency ratio (AICE lines 1022-1024)."""
        length = self._params.efficiency_length
        if index < length:
            return 0.0
        change = abs(series.closes[index] - series.closes[index - length])
        path = sum(
            abs(series.closes[i] - series.closes[i - 1])
            for i in range(index - length + 1, index + 1)
        )
        return change / path if path > 0 else 0.0

    def _hurst_proxy(self, series: _Series, index: int) -> float:
        """Variance-ratio Hurst proxy (AICE lines 1026-1029)."""
        length = self._params.entropy_window
        deviation = series.return_std[index]
        if index < length or deviation is None or deviation <= 0:
            return clamp(0.5 + (1.0 - 1.0) * _HURST_SLOPE, 0.0, 1.0)
        older = series.closes[index - length]
        current = series.closes[index]
        net = log(current / older) if current > 0 and older > 0 else 0.0
        variance_ratio = abs(net) / (deviation * length**0.5)
        return clamp(0.5 + (variance_ratio - 1.0) * _HURST_SLOPE, 0.0, 1.0)

    def _dna_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        bar = series.bars[index]
        close = series.closes[index]
        open_ = float(bar.open.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        spread = series.ranges[index]
        body = series.bodies[index]
        close_loc = (close - low) / spread if spread > 0 else 0.5
        direction = series.directions[index]
        persistence = self._persistence(series, index)
        body_rank = series.body_rank[index] or 0.5
        impulse = self._impulse_efficiency(series, index)
        atr_value = series.atr[index] or 0.0
        rejection_base = max(body + atr_value * 0.1, 1e-9)
        lower_reject = (min(open_, close) - low) / rejection_base
        upper_reject = (high - max(open_, close)) / rejection_base
        dna_bull = clamp(
            close_loc * _DNA_WEIGHTS[0]
            + persistence * (1.0 if direction == 1 else 0.0) * _DNA_WEIGHTS[1]
            + clamp(lower_reject / _REJECTION_NORM, 0.0, 1.0) * _DNA_WEIGHTS[2]
            + impulse * (1.0 if self._rose_over_window(series, index) else 0.0)
            * _DNA_WEIGHTS[3]
            + body_rank * (1.0 if direction == 1 else 0.0) * _DNA_WEIGHTS[4],
            0.0,
            1.0,
        )
        dna_bear = clamp(
            (1.0 - close_loc) * _DNA_WEIGHTS[0]
            + persistence * (1.0 if direction == -1 else 0.0) * _DNA_WEIGHTS[1]
            + clamp(upper_reject / _REJECTION_NORM, 0.0, 1.0) * _DNA_WEIGHTS[2]
            + impulse * (1.0 if self._fell_over_window(series, index) else 0.0)
            * _DNA_WEIGHTS[3]
            + body_rank * (1.0 if direction == -1 else 0.0) * _DNA_WEIGHTS[4],
            0.0,
            1.0,
        )
        sequence = sum(
            series.directions[index - offset]
            for offset in range(_DIRECTION_WINDOW)
            if index - offset >= 0
        )
        flip_bull = (
            direction == 1
            and index >= 1
            and series.directions[index - 1] == -1
            and body_rank > _FLIP_BODY_RANK
        )
        flip_bear = (
            direction == -1
            and index >= 1
            and series.directions[index - 1] == 1
            and body_rank > _FLIP_BODY_RANK
        )
        return {
            "statistical.persistence": (persistence, persistence * 2.0 - 1.0),
            "statistical.body_rank": (body_rank, body_rank * 2.0 - 1.0),
            "statistical.impulse_efficiency": (impulse, impulse * 2.0 - 1.0),
            "statistical.dna_bull": (dna_bull, dna_bull * 2.0 - 1.0),
            "statistical.dna_bear": (dna_bear, dna_bear * 2.0 - 1.0),
            "statistical.sequence_bull_bias": (
                max(0.0, sequence) / _DIRECTION_WINDOW,
                max(0.0, sequence) / _DIRECTION_WINDOW * 2.0 - 1.0,
            ),
            "statistical.sequence_bear_bias": (
                max(0.0, -sequence) / _DIRECTION_WINDOW,
                max(0.0, -sequence) / _DIRECTION_WINDOW * 2.0 - 1.0,
            ),
            "statistical.direction_flip_bull": self._binary(flip_bull),
            "statistical.direction_flip_bear": self._binary(flip_bear),
            "statistical.doji": self._binary(body <= spread * _DOJI_BODY_FRACTION),
        }

    def _persistence(self, series: _Series, index: int) -> float:
        """Share of the previous four bars agreeing with this one."""
        direction = series.directions[index]
        if direction == 0:
            return 0.0
        agreeing = sum(
            1.0
            for offset in range(1, _DIRECTION_WINDOW)
            if index - offset >= 0 and series.directions[index - offset] == direction
        )
        return agreeing / (_DIRECTION_WINDOW - 1)

    def _impulse_efficiency(self, series: _Series, index: int) -> float:
        """Three-bar displacement over the traveled range (lines 1641-1643)."""
        if index < 3:
            return 0.0
        change = abs(series.closes[index] - series.closes[index - 3])
        path = sum(series.ranges[index - offset] for offset in range(3))
        return change / path if path > 0 else 0.0

    def _rose_over_window(self, series: _Series, index: int) -> bool:
        return index >= 3 and series.closes[index] > series.closes[index - 3]

    def _fell_over_window(self, series: _Series, index: int) -> bool:
        return index >= 3 and series.closes[index] < series.closes[index - 3]

    def _pattern_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        bar = series.bars[index]
        close = series.closes[index]
        open_ = float(bar.open.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        body = series.bodies[index]
        spread = series.ranges[index]
        upper_wick = high - max(open_, close)
        lower_wick = min(open_, close) - low
        close_loc = (close - low) / spread if spread > 0 else 0.5
        upper_dom = upper_wick > lower_wick and upper_wick > body
        lower_dom = lower_wick > upper_wick and lower_wick > body
        engulf_bull = engulf_bear = False
        if index >= 1:
            prev = series.bars[index - 1]
            prev_open = float(prev.open.value)
            prev_close = series.closes[index - 1]
            engulf_bull = (
                close > open_
                and prev_close < prev_open
                and close >= prev_open
                and open_ <= prev_close
            )
            engulf_bear = (
                close < open_
                and prev_close > prev_open
                and close <= prev_open
                and open_ >= prev_close
            )
        pin_bull = lower_wick > body * _PIN_BODY_MULTIPLE and upper_wick < body
        pin_bear = upper_wick > body * _PIN_BODY_MULTIPLE and lower_wick < body
        hammer = lower_dom and lower_wick > body * _PIN_BODY_MULTIPLE and close_loc > 0.5
        star = upper_dom and upper_wick > body * _PIN_BODY_MULTIPLE and close_loc < 0.5
        return {
            "statistical.bull_engulfing": self._binary(engulf_bull),
            "statistical.bear_engulfing": self._binary(engulf_bear),
            "statistical.pin_bull": self._binary(pin_bull),
            "statistical.pin_bear": self._binary(pin_bear),
            "statistical.hammer": self._binary(hammer),
            "statistical.shooting_star": self._binary(star),
        }

    def _kinetic_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        factor = series.volatility_factor[index]
        overbought = _WT_THRESHOLD * factor
        oversold = -_WT_THRESHOLD * factor
        wt1 = series.wt1[index] or 0.0
        wt2 = series.wt2[index] or 0.0
        wt1_prev = series.wt1[index - 1] if index >= 1 else None
        wt2_prev = series.wt2[index - 1] if index >= 1 else None
        wt_bull = wt1 > wt2
        wt_bear = wt1 < wt2
        wt_cross_up = (
            wt1_prev is not None and wt2_prev is not None
            and wt1 > wt2 and wt1_prev <= wt2_prev
        )
        wt_cross_down = (
            wt1_prev is not None and wt2_prev is not None
            and wt1 < wt2 and wt1_prev >= wt2_prev
        )
        wt_bull_cross = wt_cross_up and wt1 < oversold
        wt_bear_cross = wt_cross_down and wt1 > overbought
        stc_now = series.stc[index]
        stc_prev = series.stc[index - 1] if index >= 1 else stc_now
        stc_bull = stc_now > _STC_LOW and stc_prev <= _STC_LOW
        stc_bear = stc_now < _STC_HIGH and stc_prev >= _STC_HIGH
        cci_now = series.cci[index] or 0.0
        cci_prev = series.cci[index - 1] if index >= 1 else None
        cci_low = -_CCI_THRESHOLD * factor
        cci_high = _CCI_THRESHOLD * factor
        cci_bull = cci_prev is not None and cci_now > cci_low and cci_prev <= cci_low
        cci_bear = cci_prev is not None and cci_now < cci_high and cci_prev >= cci_high
        kin_long = min(
            (_KIN_CROSS if wt_bull_cross else _KIN_STATE if wt_bull else 0.0)
            + (_KIN_STC_CROSS if stc_bull else _KIN_STC_STATE if stc_now > stc_prev else 0.0)
            + (_KIN_CCI_CROSS if cci_bull else _KIN_CCI_STATE if cci_now > 0 else 0.0)
            + (_KIN_EXTREME if wt1 < oversold else 0.0),
            1.0,
        )
        kin_short = min(
            (_KIN_CROSS if wt_bear_cross else _KIN_STATE if wt_bear else 0.0)
            + (_KIN_STC_CROSS if stc_bear else _KIN_STC_STATE if stc_now < stc_prev else 0.0)
            + (_KIN_CCI_CROSS if cci_bear else _KIN_CCI_STATE if cci_now < 0 else 0.0)
            + (_KIN_EXTREME if wt1 > overbought else 0.0),
            1.0,
        )
        return {
            "statistical.wavetrend": (wt1, clamp(wt1 / 100.0, -1.0, 1.0)),
            "statistical.wavetrend_bull": self._binary(wt_bull),
            "statistical.stc": (stc_now, stc_now / 50.0 - 1.0),
            "statistical.cci": (cci_now, clamp(cci_now / 200.0, -1.0, 1.0)),
            "statistical.kinetic_long": (kin_long, kin_long * 2.0 - 1.0),
            "statistical.kinetic_short": (kin_short, kin_short * 2.0 - 1.0),
        }

    def _binary(self, flag: bool) -> tuple[float, float]:
        value = 1.0 if flag else 0.0
        return value, value

    # --- Emission ------------------------------------------------------------------

    def _emit(self, bar: Bar, values: dict[str, tuple[float, float]]) -> list[Feature]:
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
