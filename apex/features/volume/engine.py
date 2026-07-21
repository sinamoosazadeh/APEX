"""Volume & normalization feature family - migrated from AICE.

Faithful port of the AICE Pine v6 volume/volatility statistics (Book VI
spec lines ~985-1016), the delta approximation block (~1704-1720), the
rolling volume-profile approximation (~1594-1628) and the zero-lag
momentum filter (~1061-1066), per the Book II ch. 2 migration matrix
("volume & normalization: percentile ranks, z-scores, volume
confirmation"):

- **Relative volume**: ``vol / sma(vol, 20)`` with AICE's na fallback.
- **Volatility rank**: ATR percent-rank and width vs its own mean over
  the rank window, collapsed into the discrete ``vol_factor`` regime
  multiplier (1.3 wide / 0.75 narrow / 1.0).
- **Volatility forecast**: EWMA variance of log returns against the
  historical deviation (``vol_fc_ratio``) and the adaptive ATR ratio
  ``clamp(0.85 + 0.25*(fc-1) + 0.30*(pctile-0.5), 0.65, 1.45)``.
- **VWAP deviation**: distance from the session VWAP in ATR units and
  as a winsorized z-score over the normalization window. Pine's
  ``ta.vwap`` anchors to the symbol session; Toobit perpetuals trade
  continuously, so the session is the UTC day (documented decision).
- **Range state**: expansion/compression vs ``sma(range, 14)``.
- **Delta approximation**: ``net_delta = vol * (2*close_loc - 1)``;
  aggression (net delta over mean volume), rolling and cumulative
  delta biases, absorption (high RVOL + dominant wick + narrow bar),
  volume spikes and buying/selling climaxes.
- **Volume profile approximation**: binned volume over the rolling
  window; POC distance in ATR, acceptance share, above/below POC.
- **Zero-lag momentum**: ``f_zpf`` fast/slow crossover with slope
  (``local_bull/bear``) and the squashed winsorized slope z-score.

Composite one-off signals that AND this family with structure series
(``spring = sweep_low and up-close and expansion``, ``upthrust``,
``sos``) are intentionally not duplicated here: the probability layer
composes them from the stored vectors ``structure.sweep_low/high``,
``structure.bos_*`` x ``volume.expansion`` x bar direction (Book II
composition; single source per Constitution 2.12).

Window-relative state (cumulative delta and its EMA baseline, EWMA
variance) folds from the start of the provided window, exactly like
the Pine ``var`` declarations fold from the start of the chart. All
values come from confirmed bars only; nothing is emitted in warmup.
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
from apex.core.validation import ensure_in_range, ensure_positive
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.calculations import (
    clamp,
    ema,
    percent_rank,
    robust_z,
    sma,
    squash,
    stdev,
    wilder_atr,
    zero_lag_filter,
)

FAMILY = "volume"
_SOURCE = "apex.features.volume"

# Discrete volatility regime multiplier (AICE line 988).
_WIDTH_WIDE, _WIDTH_NARROW = 1.5, 0.6
_FACTOR_WIDE, _FACTOR_NARROW = 1.3, 0.75
# Adaptive ATR shape (AICE line 1010).
_ADAPTIVE_BASE, _ADAPTIVE_FC, _ADAPTIVE_RANK = 0.85, 0.25, 0.30
_ADAPTIVE_FLOOR, _ADAPTIVE_CEIL = 0.65, 1.45
# Range state thresholds (AICE lines 1039-1040).
_EXPANSION_RATIO, _COMPRESSION_RATIO = 1.5, 0.6
# Volume confirmation thresholds (AICE lines 1713-1717).
_ABSORPTION_RVOL = 1.3
_ABSORPTION_WICK_BODY = 1.2
_ABSORPTION_CLOSE_HIGH, _ABSORPTION_CLOSE_LOW = 0.55, 0.45
_SPIKE_RVOL = 2.0
# Momentum slope lag (AICE line 1063: ``zpf_slow - zpf_slow[3]``).
_SLOPE_LAG = 3
# Normalization horizons for emission (family-local conventions).
_RVOL_NORM = 2.5
_WIDTH_NORM = 2.0
_VWAP_ATR_NORM = 3.0
_POC_ATR_NORM = 3.0

FEATURE_NAMES: tuple[str, ...] = (
    "volume.rvol",
    "volume.volume_available",
    "volume.atr_percentile",
    "volume.volatility_width",
    "volume.volatility_factor",
    "volume.forecast_ratio",
    "volume.adaptive_atr_ratio",
    "volume.vwap_deviation_atr",
    "volume.vwap_deviation_z",
    "volume.expansion",
    "volume.compression",
    "volume.aggression",
    "volume.rolling_delta_bias",
    "volume.cumulative_delta_bias",
    "volume.absorption_buy",
    "volume.absorption_sell",
    "volume.spike",
    "volume.selling_climax",
    "volume.buying_climax",
    "volume.poc_distance_atr",
    "volume.poc_acceptance",
    "volume.above_poc",
    "volume.momentum_bull",
    "volume.momentum_bear",
    "volume.momentum_slope",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class VolumeParams:
    """Tunables of the volume & normalization family (AICE defaults)."""

    atr_length: int = 14
    volume_sma_length: int = 20
    range_sma_length: int = 14
    normalization_window: int = 200
    rank_window: int = 200
    forecast_length: int = 50
    winsor_z: float = 3.0
    zpf_fast_length: int = 12
    zpf_slow_length: int = 26
    profile_length: int = 96
    profile_bins: int = 16
    delta_roll_length: int = 50
    delta_bias_ema_length: int = 100

    def __post_init__(self) -> None:
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.volume_sma_length, "volume_sma_length")
        ensure_positive(self.range_sma_length, "range_sma_length")
        ensure_positive(self.normalization_window, "normalization_window")
        ensure_positive(self.rank_window, "rank_window")
        ensure_positive(self.forecast_length, "forecast_length")
        ensure_in_range(self.winsor_z, 1.0, 10.0, "winsor_z")
        ensure_positive(self.zpf_fast_length, "zpf_fast_length")
        ensure_positive(self.zpf_slow_length, "zpf_slow_length")
        ensure_positive(self.profile_length, "profile_length")
        ensure_positive(self.profile_bins, "profile_bins")
        ensure_positive(self.delta_roll_length, "delta_roll_length")
        ensure_positive(self.delta_bias_ema_length, "delta_bias_ema_length")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission (AICE 979)."""
        return max(
            self.atr_length,
            self.volume_sma_length,
            self.range_sma_length,
            self.normalization_window,
            self.rank_window,
            self.forecast_length,
            self.profile_length + 1,
            2 * (self.zpf_slow_length - 1) + _SLOPE_LAG,
            self.delta_bias_ema_length,
        )


@dataclass(slots=True)
class _Series:
    """Precomputed per-bar inputs for the snapshot pass."""

    bars: list[Bar]
    closes: list[float]
    volumes: list[float]
    ranges: list[float]
    close_locations: list[float]
    atr: list[float | None]
    volume_sma: list[float | None]
    range_sma: list[float | None]
    atr_percentile: list[float | None]
    atr_mean: list[float | None]
    ewma_vol: list[float]
    hist_vol: list[float | None]
    vwap: list[float | None]
    vwap_z: list[float]
    net_delta: list[float]
    rolling_delta: list[float | None]
    cumulative_delta: list[float]
    delta_baseline: list[float | None]
    momentum_fast: list[float | None]
    momentum_slow: list[float | None]
    momentum_slope_z: list[float]


class VolumeEngine:
    """Computes the volume & normalization family over a bar window."""

    def __init__(self, *, params: VolumeParams, clock: Clock) -> None:
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
            snapshot = self._snapshot(series, index)
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

    def _prepare(self, bars: list[Bar]) -> _Series:
        params = self._params
        closes = [float(bar.close.value) for bar in bars]
        volumes = [float(bar.volume.value) for bar in bars]
        ranges = [float(bar.high.value) - float(bar.low.value) for bar in bars]
        close_locations = [
            (float(bar.close.value) - float(bar.low.value)) / spread if spread > 0 else 0.5
            for bar, spread in zip(bars, ranges, strict=True)
        ]
        atr = wilder_atr(bars, params.atr_length)
        atr_percentile, atr_mean = self._atr_statistics(atr)
        log_returns = self._log_returns(closes)
        vwap = self._session_vwap(bars)
        net_delta = [
            volumes[i] * (2.0 * close_locations[i] - 1.0) for i in range(len(bars))
        ]
        cumulative = self._running_sum(net_delta)
        slow = zero_lag_filter(closes, params.zpf_slow_length)
        return _Series(
            bars=bars,
            closes=closes,
            volumes=volumes,
            ranges=ranges,
            close_locations=close_locations,
            atr=atr,
            volume_sma=sma(volumes, params.volume_sma_length),
            range_sma=sma(ranges, params.range_sma_length),
            atr_percentile=atr_percentile,
            atr_mean=atr_mean,
            ewma_vol=self._ewma_volatility(log_returns),
            hist_vol=stdev(log_returns, params.forecast_length),
            vwap=vwap,
            vwap_z=self._vwap_z(closes, vwap),
            net_delta=net_delta,
            rolling_delta=self._rolling_sum(net_delta, params.delta_roll_length),
            cumulative_delta=cumulative,
            delta_baseline=ema(cumulative, params.delta_bias_ema_length),
            momentum_fast=zero_lag_filter(closes, params.zpf_fast_length),
            momentum_slow=slow,
            momentum_slope_z=self._slope_z(slow),
        )

    def _vwap_z(self, closes: list[float], vwap: list[float | None]) -> list[float]:
        """Winsorized z of the VWAP deviation (0.0 where VWAP is unset)."""
        params = self._params
        deviation = [
            closes[i] - value if (value := vwap[i]) is not None else 0.0
            for i in range(len(closes))
        ]
        return robust_z(deviation, params.normalization_window, params.winsor_z)

    def _slope_z(self, slow: list[float | None]) -> list[float]:
        """Winsorized z of the zero-lag slope (Pine ``nz`` -> 0.0)."""
        params = self._params
        slope = [0.0] * len(slow)
        for i in range(_SLOPE_LAG, len(slow)):
            current = slow[i]
            lagged = slow[i - _SLOPE_LAG]
            if current is not None and lagged is not None:
                slope[i] = current - lagged
        return robust_z(slope, params.normalization_window, params.winsor_z)

    def _atr_statistics(
        self, atr: list[float | None]
    ) -> tuple[list[float | None], list[float | None]]:
        """Percent rank and mean of ATR over its valid tail (Pine na rules)."""
        params = self._params
        offset = next((i for i, value in enumerate(atr) if value is not None), len(atr))
        tail = [value for value in atr[offset:] if value is not None]
        rank_tail = percent_rank(tail, params.rank_window)
        mean_tail = sma(tail, params.rank_window)
        percentile: list[float | None] = [None] * len(atr)
        mean: list[float | None] = [None] * len(atr)
        for i in range(len(tail)):
            percentile[offset + i] = rank_tail[i]
            mean[offset + i] = mean_tail[i]
        return percentile, mean

    def _log_returns(self, closes: list[float]) -> list[float]:
        """Per-bar log return; 0.0 on the first bar (AICE line 1003)."""
        out = [0.0] * len(closes)
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i - 1] > 0:
                out[i] = log(closes[i] / closes[i - 1])
        return out

    def _ewma_volatility(self, log_returns: list[float]) -> list[float]:
        """EWMA deviation of log returns (AICE lines 1004-1007)."""
        lam = 2.0 / (self._params.forecast_length + 1.0)
        out = [0.0] * len(log_returns)
        variance: float | None = None
        for i, ret in enumerate(log_returns):
            squared = ret * ret
            variance = squared if variance is None else variance * (1.0 - lam) + lam * squared
            out[i] = max(variance, 0.0) ** 0.5
        return out

    def _session_vwap(self, bars: list[Bar]) -> list[float | None]:
        """VWAP anchored to the UTC day of each bar's open time."""
        out: list[float | None] = [None] * len(bars)
        day_ms = 86_400_000
        session_day: int | None = None
        priced = 0.0
        traded = 0.0
        for i, bar in enumerate(bars):
            day = bar.open_time.epoch_ms // day_ms
            if day != session_day:
                session_day = day
                priced = 0.0
                traded = 0.0
            typical = (
                float(bar.high.value) + float(bar.low.value) + float(bar.close.value)
            ) / 3.0
            volume = float(bar.volume.value)
            priced += typical * volume
            traded += volume
            out[i] = priced / traded if traded > 0 else None
        return out

    def _running_sum(self, values: list[float]) -> list[float]:
        out = [0.0] * len(values)
        total = 0.0
        for i, value in enumerate(values):
            total += value
            out[i] = total
        return out

    def _rolling_sum(self, values: list[float], length: int) -> list[float | None]:
        out: list[float | None] = [None] * len(values)
        running = 0.0
        for i, value in enumerate(values):
            running += value
            if i >= length:
                running -= values[i - length]
            if i >= length - 1:
                out[i] = running
        return out

    # --- Volume profile ---------------------------------------------------------

    def _volume_profile(self, series: _Series, index: int) -> tuple[float | None, float]:
        """Rolling binned profile: (POC price, acceptance share).

        AICE lines 1605-1626: bins span the window's low/high; each
        bar's volume lands in the bin holding its typical price; the
        POC is the max bin's center and acceptance is the close bin's
        share of the POC volume (0.5 when undefined).
        """
        params = self._params
        if index <= params.profile_length:
            return None, 0.5
        start = index - params.profile_length + 1
        window = range(start, index + 1)
        lows = [float(series.bars[i].low.value) for i in window]
        highs = [float(series.bars[i].high.value) for i in window]
        low, high = min(lows), max(highs)
        span = high - low
        if span <= 0:
            return None, 0.5
        bin_size = span / params.profile_bins
        totals = [0.0] * params.profile_bins
        close_bin_volume = 0.0
        close = series.closes[index]
        for i in window:
            bar = series.bars[i]
            typical = (
                float(bar.high.value) + float(bar.low.value) + float(bar.close.value)
            ) / 3.0
            slot = min(int((typical - low) / bin_size), params.profile_bins - 1)
            totals[slot] += series.volumes[i]
        poc_slot = max(range(params.profile_bins), key=lambda b: totals[b])
        close_slot = min(
            max(int((close - low) / bin_size), 0), params.profile_bins - 1
        )
        close_bin_volume = totals[close_slot]
        poc_volume = totals[poc_slot]
        poc = low + bin_size * (poc_slot + 0.5)
        acceptance = clamp(close_bin_volume / poc_volume, 0.0, 1.0) if poc_volume > 0 else 0.5
        return poc, acceptance

    # --- Snapshot ----------------------------------------------------------------

    def _snapshot(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        """(raw, normalized) per feature for one bar."""
        volatility = self._volatility_block(series, index)
        vwap_block = self._vwap_block(series, index)
        delta = self._delta_block(series, index)
        profile = self._profile_block(series, index)
        momentum = self._momentum_block(series, index)
        values: dict[str, tuple[float, float]] = {}
        values.update(volatility)
        values.update(vwap_block)
        values.update(delta)
        values.update(profile)
        values.update(momentum)
        rvol = self._rvol(series, index)
        available = 1.0 if series.volumes[index] > 0 else 0.0
        values["volume.rvol"] = (rvol, clamp(rvol / _RVOL_NORM, 0.0, 1.0) * 2.0 - 1.0)
        values["volume.volume_available"] = (available, available)
        range_mean = series.range_sma[index]
        has_range_mean = range_mean is not None and range_mean > 0
        expansion = (
            1.0
            if has_range_mean and series.ranges[index] > (range_mean or 0.0) * _EXPANSION_RATIO
            else 0.0
        )
        compression = (
            1.0
            if has_range_mean and series.ranges[index] < (range_mean or 0.0) * _COMPRESSION_RATIO
            else 0.0
        )
        values["volume.expansion"] = (expansion, expansion)
        values["volume.compression"] = (compression, compression)
        return values

    def _rvol(self, series: _Series, index: int) -> float:
        mean = series.volume_sma[index]
        if mean is not None and mean > 0:
            return series.volumes[index] / mean
        return 1.0

    def _volatility_block(
        self, series: _Series, index: int
    ) -> dict[str, tuple[float, float]]:
        atr = series.atr[index]
        percentile = series.atr_percentile[index]
        pct = percentile if percentile is not None else 0.5
        mean = series.atr_mean[index]
        width = atr / mean if atr is not None and mean is not None and mean > 0 else 1.0
        factor = (
            _FACTOR_WIDE
            if width > _WIDTH_WIDE
            else _FACTOR_NARROW
            if width < _WIDTH_NARROW
            else 1.0
        )
        hist = series.hist_vol[index]
        forecast = series.ewma_vol[index] / hist if hist is not None and hist > 0 else 1.0
        adaptive = clamp(
            _ADAPTIVE_BASE + _ADAPTIVE_FC * (forecast - 1.0) + _ADAPTIVE_RANK * (pct - 0.5),
            _ADAPTIVE_FLOOR,
            _ADAPTIVE_CEIL,
        )
        return {
            "volume.atr_percentile": (pct, pct * 2.0 - 1.0),
            "volume.volatility_width": (
                width,
                clamp(width / _WIDTH_NORM, 0.0, 1.0) * 2.0 - 1.0,
            ),
            "volume.volatility_factor": (factor, clamp((factor - 1.0) * 2.0, -1.0, 1.0)),
            "volume.forecast_ratio": (forecast, clamp(forecast - 1.0, -1.0, 1.0)),
            "volume.adaptive_atr_ratio": (
                adaptive,
                clamp((adaptive - 1.0) / (_ADAPTIVE_CEIL - 1.0), -1.0, 1.0),
            ),
        }

    def _vwap_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        atr = series.atr[index]
        vwap = series.vwap[index]
        deviation_atr = (
            (series.closes[index] - vwap) / atr
            if vwap is not None and atr is not None and atr > 0
            else 0.0
        )
        deviation_z = series.vwap_z[index]
        return {
            "volume.vwap_deviation_atr": (
                deviation_atr,
                clamp(deviation_atr / _VWAP_ATR_NORM, -1.0, 1.0),
            ),
            "volume.vwap_deviation_z": (
                deviation_z,
                clamp(deviation_z / self._params.winsor_z, -1.0, 1.0),
            ),
        }

    def _delta_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        params = self._params
        volume_mean = series.volume_sma[index]
        has_mean = volume_mean is not None and volume_mean > 0
        aggression = (
            series.net_delta[index] / volume_mean
            if volume_mean is not None and volume_mean > 0
            else 0.0
        )
        rolling = series.rolling_delta[index]
        rolling_raw = rolling if rolling is not None else 0.0
        rolling_norm = (
            clamp(rolling_raw / ((volume_mean or 1.0) * params.delta_roll_length), -1.0, 1.0)
            if has_mean
            else 0.0
        )
        baseline = series.delta_baseline[index]
        bias = series.cumulative_delta[index] - baseline if baseline is not None else 0.0
        bias_norm = (
            clamp(bias / ((volume_mean or 1.0) * params.delta_bias_ema_length), -1.0, 1.0)
            if has_mean
            else 0.0
        )
        return {
            "volume.aggression": (aggression, clamp(aggression / _RVOL_NORM, -1.0, 1.0)),
            "volume.rolling_delta_bias": (rolling_raw, rolling_norm),
            "volume.cumulative_delta_bias": (bias, bias_norm),
            **self._confirmation_block(series, index, aggression),
        }

    def _confirmation_block(
        self, series: _Series, index: int, aggression: float
    ) -> dict[str, tuple[float, float]]:
        """Absorption, spikes and climaxes (AICE lines 1713-1718)."""
        bar = series.bars[index]
        close = series.closes[index]
        open_ = float(bar.open.value)
        body = abs(close - open_)
        upper_wick = float(bar.high.value) - max(open_, close)
        lower_wick = min(open_, close) - float(bar.low.value)
        close_loc = series.close_locations[index]
        rvol = self._rvol(series, index)
        range_mean = series.range_sma[index]
        narrow = range_mean is not None and series.ranges[index] < range_mean
        absorption_buy = (
            rvol > _ABSORPTION_RVOL
            and lower_wick > body * _ABSORPTION_WICK_BODY
            and close_loc > _ABSORPTION_CLOSE_HIGH
            and narrow
        )
        absorption_sell = (
            rvol > _ABSORPTION_RVOL
            and upper_wick > body * _ABSORPTION_WICK_BODY
            and close_loc < _ABSORPTION_CLOSE_LOW
            and narrow
        )
        volume_mean = series.volume_sma[index]
        spike = volume_mean is not None and series.volumes[index] > volume_mean * _SPIKE_RVOL
        upper_dom = upper_wick > lower_wick and upper_wick > body
        lower_dom = lower_wick > upper_wick and lower_wick > body
        selling_climax = spike and lower_dom and aggression > 0
        buying_climax = spike and upper_dom and aggression < 0
        return {
            "volume.absorption_buy": self._binary(absorption_buy),
            "volume.absorption_sell": self._binary(absorption_sell),
            "volume.spike": self._binary(spike),
            "volume.selling_climax": self._binary(selling_climax),
            "volume.buying_climax": self._binary(buying_climax),
        }

    def _profile_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        poc, acceptance = self._volume_profile(series, index)
        atr = series.atr[index]
        close = series.closes[index]
        distance = (
            abs(close - poc) / atr if poc is not None and atr is not None and atr > 0 else 0.0
        )
        above = 1.0 if poc is not None and close > poc else 0.0
        return {
            "volume.poc_distance_atr": (
                distance,
                clamp(distance / _POC_ATR_NORM, 0.0, 1.0) * 2.0 - 1.0,
            ),
            "volume.poc_acceptance": (acceptance, acceptance * 2.0 - 1.0),
            "volume.above_poc": (above, above),
        }

    def _momentum_block(self, series: _Series, index: int) -> dict[str, tuple[float, float]]:
        fast = series.momentum_fast[index]
        slow = series.momentum_slow[index]
        lagged = series.momentum_slow[index - _SLOPE_LAG] if index >= _SLOPE_LAG else None
        slope = slow - lagged if slow is not None and lagged is not None else 0.0
        bull = fast is not None and slow is not None and fast > slow and slope > 0
        bear = fast is not None and slow is not None and fast < slow and slope < 0
        slope_norm = squash(series.momentum_slope_z[index])
        return {
            "volume.momentum_bull": self._binary(bull),
            "volume.momentum_bear": self._binary(bear),
            "volume.momentum_slope": (slope_norm, slope_norm * 2.0 - 1.0),
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
