"""Shared feature calculations (Pine-faithful primitives).

Building blocks used by multiple feature families, ported once from
their Pine counterparts (Constitution 2.12: no duplicate logic):

- Wilder ATR (Pine ``ta.atr``): SMA seed, then recursive smoothing.
- EMA (Pine ``ta.ema``): SMA seed, then ``alpha = 2 / (length + 1)``.
- Strict pivot tracking (Pine ``ta.pivothigh/pivotlow`` semantics):
  a pivot is confirmed ``lookback`` bars after it printed.
- Rolling extremes with a one-bar shift (Pine ``ta.highest(x, n)[1]``).
- The chart-structure fold (AICE "STRUCTURE" block): BOS/CHoCH state
  machine, decayed break quality, displacement and the dealing range.
  Consumed by every family that needs structure context.
"""

from dataclasses import dataclass, field
from math import exp, log

from apex.domain.market import Bar

# Break quality denominator factor (AICE line 1163).
BREAK_QUALITY_FACTOR = 1.5


def clamp(value: float, lower: float, upper: float) -> float:
    """Pine ``f_clamp``: bound a value into [lower, upper]."""
    return max(lower, min(upper, value))


def true_range(bars: list[Bar], index: int) -> float:
    """True range of one bar (uses the previous close when available)."""
    high = float(bars[index].high.value)
    low = float(bars[index].low.value)
    if index == 0:
        return high - low
    prev_close = float(bars[index - 1].close.value)
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def wilder_atr(bars: list[Bar], length: int) -> list[float | None]:
    """Wilder ATR per bar; None during the seed window (Pine ``ta.atr``)."""
    values: list[float | None] = [None] * len(bars)
    atr: float | None = None
    for index in range(len(bars)):
        if index < length - 1:
            continue
        if atr is None:
            atr = sum(true_range(bars, i) for i in range(length)) / length
        else:
            atr = (atr * (length - 1) + true_range(bars, index)) / length
        values[index] = atr
    return values


def sma(values: list[float], length: int) -> list[float | None]:
    """Simple moving average per index; None until a full window exists."""
    out: list[float | None] = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= length:
            running -= values[index - length]
        if index >= length - 1:
            out[index] = running / length
    return out


def stdev(values: list[float], length: int) -> list[float | None]:
    """Population standard deviation per index (Pine ``ta.stdev``).

    Pine's default is the biased estimator: divide by N over the
    ``length``-bar window including the current bar; None until a full
    window exists.
    """
    out: list[float | None] = [None] * len(values)
    for index in range(length - 1, len(values)):
        window = values[index - length + 1 : index + 1]
        mean = sum(window) / length
        variance = sum((value - mean) ** 2 for value in window) / length
        out[index] = variance**0.5
    return out


def percent_rank(values: list[float], length: int) -> list[float | None]:
    """Percent rank in [0, 1] per index (Pine ``ta.percentrank`` / 100).

    Share of the ``length`` values BEFORE the current bar that are less
    than or equal to the current value; None until that much history
    exists.
    """
    out: list[float | None] = [None] * len(values)
    for index in range(length, len(values)):
        current = values[index]
        below = sum(1 for i in range(index - length, index) if values[i] <= current)
        out[index] = below / length
    return out


def squash(value: float) -> float:
    """Pine ``f_squash``: logistic sigmoid into (0, 1)."""
    return 1.0 / (1.0 + exp(-value))


def robust_z(values: list[float], length: int, winsor: float) -> list[float]:
    """Winsorized z-score per index (Pine ``f_zrobust``).

    ``(x - sma) / stdev`` clamped into [-winsor, +winsor]; 0.0 while
    the window is incomplete or the deviation is degenerate.
    """
    means = sma(values, length)
    deviations = stdev(values, length)
    out: list[float] = [0.0] * len(values)
    for index, value in enumerate(values):
        mean = means[index]
        deviation = deviations[index]
        if mean is not None and deviation is not None and deviation > 0:
            out[index] = clamp((value - mean) / deviation, -winsor, winsor)
    return out


def zero_lag_filter(values: list[float], length: int) -> list[float | None]:
    """Zero-lag price filter per index (Pine ``f_zpf``): ``e1 + (e1 - e2)``.

    ``e1`` is the EMA of the source and ``e2`` the EMA of ``e1``; None
    until both seeds exist. Like Pine, ``e2`` seeds from ``e1``'s first
    valid values (the warmup does not contaminate the second pass).
    """
    e1 = ema(values, length)
    offset = length - 1
    tail = [value for value in e1[offset:] if value is not None]
    e2_tail = ema(tail, length)
    out: list[float | None] = [None] * len(values)
    for tail_index, second in enumerate(e2_tail):
        first = e1[offset + tail_index]
        if first is not None and second is not None:
            out[offset + tail_index] = first + (first - second)
    return out


def ema(values: list[float], length: int) -> list[float | None]:
    """EMA per index; SMA-seeded like Pine ``ta.ema``."""
    out: list[float | None] = [None] * len(values)
    alpha = 2.0 / (length + 1.0)
    current: float | None = None
    for index, value in enumerate(values):
        if index < length - 1:
            continue
        if current is None:
            current = sum(values[: length]) / length
        else:
            current = current + alpha * (value - current)
        out[index] = current
    return out


def rolling_extremes(
    bars: list[Bar],
    index: int,
    window: int,
) -> tuple[float | None, float | None]:
    """Highest high / lowest low of the ``window`` bars BEFORE ``index``.

    Pine ``ta.highest(high, n)[1]`` semantics: the current bar is
    excluded; None until a full window of history exists.
    """
    start = index - window
    if start < 0:
        return None, None
    highs = [float(bars[i].high.value) for i in range(start, index)]
    lows = [float(bars[i].low.value) for i in range(start, index)]
    return max(highs), min(lows)


@dataclass(slots=True)
class PivotTracker:
    """Strict pivot state for one lookback (Pine pivot semantics).

    ``update`` must be called once per bar in ascending order; it
    reports whether a new pivot high/low was *confirmed* at this bar
    (the pivot itself printed ``lookback`` bars earlier).
    """

    lookback: int
    last_high: float | None = None
    prev_high: float | None = None
    last_low: float | None = None
    prev_low: float | None = None
    _highs: list[float] = field(default_factory=list)
    _lows: list[float] = field(default_factory=list)

    def update(self, bar: Bar) -> tuple[bool, bool]:
        """Feed one bar; returns (new_high_confirmed, new_low_confirmed)."""
        self._highs.append(float(bar.high.value))
        self._lows.append(float(bar.low.value))
        index = len(self._highs) - 1
        lb = self.lookback
        candidate = index - lb
        if candidate < lb:
            return False, False
        window = range(candidate - lb, candidate + lb + 1)
        new_high = all(
            self._highs[candidate] > self._highs[i] for i in window if i != candidate
        )
        new_low = all(
            self._lows[candidate] < self._lows[i] for i in window if i != candidate
        )
        if new_high:
            self.prev_high = self.last_high
            self.last_high = self._highs[candidate]
        if new_low:
            self.prev_low = self.last_low
            self.last_low = self._lows[candidate]
        return new_high, new_low


@dataclass(frozen=True, slots=True, kw_only=True)
class StructureSignals:
    """Per-bar snapshot of the shared chart-structure fold."""

    new_pivot_high: bool
    new_pivot_low: bool
    body_atr: float
    is_displacement: bool
    bos_up: bool
    bos_down: bool
    choch_up: bool
    choch_down: bool
    break_quality: float
    trend_direction: int
    dealing_range_position: float
    equilibrium: float | None
    in_premium: bool
    in_discount: bool


@dataclass(slots=True)
class StructureFold:
    """AICE chart-structure state machine, shared across families.

    Encapsulates the ``var`` block of the AICE "STRUCTURE / LIQUIDITY
    HIERARCHY" section: strict-pivot break detection with cross
    semantics (close crossing the last swing), the BOS/CHoCH trend
    state machine, break quality ``clamp(body_atr / (displacement x
    1.5))`` decaying per bar, displacement, and the dealing range from
    the last swing pair. The structure and order-block/FVG families
    fold this once per bar (Constitution 2.12: single source of logic).

    ``update`` must be called exactly once per bar in ascending order.
    """

    pivots: PivotTracker
    displacement_body_atr: float
    break_decay: float
    trend_direction: int = 0
    protected_high: float | None = None
    protected_low: float | None = None
    _break_quality: float = 0.0
    _last_break_index: int | None = None

    def update(self, bars: list[Bar], index: int, atr: float | None) -> StructureSignals:
        """Advance the fold by one bar and return its signal snapshot."""
        bar = bars[index]
        close = float(bar.close.value)
        prev_close = float(bars[index - 1].close.value) if index > 0 else close
        usable_atr = atr if atr is not None and atr > 0 else None
        new_high, new_low = self.pivots.update(bar)
        last_ph, last_pl = self.pivots.last_high, self.pivots.last_low

        body = abs(close - float(bar.open.value))
        body_atr = body / usable_atr if usable_atr else 0.0
        is_displacement = body_atr >= self.displacement_body_atr

        bos_up = bos_dn = choch_up = choch_dn = False
        if last_ph is not None and close > last_ph and prev_close <= last_ph:
            if self.trend_direction == -1:
                choch_up = True
            else:
                bos_up = True
            self.trend_direction = 1
            self.protected_low = last_pl
            self._record_break(index, body_atr)
        if last_pl is not None and close < last_pl and prev_close >= last_pl:
            if self.trend_direction == 1:
                choch_dn = True
            else:
                bos_dn = True
            self.trend_direction = -1
            self.protected_high = last_ph
            self._record_break(index, body_atr)

        if self._last_break_index is not None:
            age = index - self._last_break_index
            break_quality = self._break_quality * (self.break_decay**age)
        else:
            break_quality = 0.0

        dr_pos = 0.5
        equilibrium: float | None = None
        in_premium = in_discount = False
        if last_ph is not None and last_pl is not None:
            top = max(last_ph, last_pl)
            bottom = min(last_ph, last_pl)
            size = top - bottom
            if size > 0:
                dr_pos = clamp((close - bottom) / size, 0.0, 1.0)
                equilibrium = (top + bottom) / 2.0
                in_discount = close < equilibrium
                in_premium = close > equilibrium

        return StructureSignals(
            new_pivot_high=new_high,
            new_pivot_low=new_low,
            body_atr=body_atr,
            is_displacement=is_displacement,
            bos_up=bos_up,
            bos_down=bos_dn,
            choch_up=choch_up,
            choch_down=choch_dn,
            break_quality=break_quality,
            trend_direction=self.trend_direction,
            dealing_range_position=dr_pos,
            equilibrium=equilibrium,
            in_premium=in_premium,
            in_discount=in_discount,
        )

    def _record_break(self, index: int, body_atr: float) -> None:
        """Stamp break quality and age origin at a structure break."""
        self._break_quality = clamp(
            body_atr / (self.displacement_body_atr * BREAK_QUALITY_FACTOR), 0.0, 1.0
        )
        self._last_break_index = index


def correlation(xs: list[float], ys: list[float], length: int) -> list[float | None]:
    """Rolling Pearson correlation (Pine ``ta.correlation``); None until full."""
    out: list[float | None] = [None] * len(xs)
    for index in range(length - 1, len(xs)):
        wx = xs[index - length + 1 : index + 1]
        wy = ys[index - length + 1 : index + 1]
        mean_x = sum(wx) / length
        mean_y = sum(wy) / length
        cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(wx, wy, strict=True))
        var_x = sum((a - mean_x) ** 2 for a in wx)
        var_y = sum((b - mean_y) ** 2 for b in wy)
        denominator = (var_x * var_y) ** 0.5
        if denominator > 0:
            out[index] = cov / denominator
    return out


def last_closed_indices(
    chart_close_ms: list[int],
    other_close_ms: list[int],
) -> list[int | None]:
    """Causal series mapping: latest other-series bar closed by each chart bar.

    Both inputs are ascending close times. Index ``i`` of the result is
    the position of the last other-series bar whose close time is at or
    before chart bar ``i``'s close time - the strict non-repainting
    stand-in for Pine's ``request.security`` (Constitution over AICE).
    """
    out: list[int | None] = [None] * len(chart_close_ms)
    other_index = -1
    for i, close_ms in enumerate(chart_close_ms):
        while (
            other_index + 1 < len(other_close_ms)
            and other_close_ms[other_index + 1] <= close_ms
        ):
            other_index += 1
        out[i] = other_index if other_index >= 0 else None
    return out


@dataclass(frozen=True, slots=True)
class StructBias:
    """One bar of the AICE ``f_struct_pack`` fold: bias and equilibrium."""

    bias: int
    equilibrium: float | None


def struct_bias_series(
    bars: list[Bar],
    *,
    lookback: int,
    ema_length: int,
) -> list[StructBias]:
    """AICE ``f_struct_pack`` per bar: swing-break bias with EMA fallback.

    bias = +1 above the last pivot high, -1 below the last pivot low,
    else the side of the EMA (0 while nothing is defined); equilibrium
    is the midpoint of the last pivot pair when both exist.
    """
    closes = [float(bar.close.value) for bar in bars]
    ema_series = ema(closes, ema_length)
    pivots = PivotTracker(lookback=lookback)
    out: list[StructBias] = []
    for index, bar in enumerate(bars):
        pivots.update(bar)
        close = closes[index]
        last_ph, last_pl = pivots.last_high, pivots.last_low
        mean = ema_series[index]
        if last_ph is not None and close > last_ph:
            bias = 1
        elif last_pl is not None and close < last_pl:
            bias = -1
        elif mean is not None and close > mean:
            bias = 1
        elif mean is not None and close < mean:
            bias = -1
        else:
            bias = 0
        equilibrium = (
            (last_ph + last_pl) / 2.0
            if last_ph is not None and last_pl is not None
            else None
        )
        out.append(StructBias(bias=bias, equilibrium=equilibrium))
    return out


@dataclass(frozen=True, slots=True, kw_only=True)
class HtfContext:
    """AICE HTF context for one chart bar (spec lines 1087-1095)."""

    macro1_bias: int
    macro2_bias: int
    alignment: int
    bull_context: bool
    bear_context: bool
    confidence: float
    in_discount: bool
    in_premium: bool


def htf_context_series(
    chart_bars: list[Bar],
    macro1_bars: list[Bar],
    macro2_bars: list[Bar],
    *,
    pivot_lookback: int,
    ema_length: int,
) -> list[HtfContext | None]:
    """HTF alignment/discount per chart bar from closed macro bars.

    Shared by the HTF family and the OB/FVG quality terms
    (Constitution 2.12). None where no macro bar has closed yet.
    """
    macro1 = struct_bias_series(macro1_bars, lookback=pivot_lookback, ema_length=ema_length)
    macro2 = struct_bias_series(macro2_bars, lookback=pivot_lookback, ema_length=ema_length)
    chart_close = [bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in chart_bars]
    map1 = last_closed_indices(
        chart_close,
        [bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in macro1_bars],
    )
    map2 = last_closed_indices(
        chart_close,
        [bar.open_time.epoch_ms + bar.timeframe.duration_ms for bar in macro2_bars],
    )
    out: list[HtfContext | None] = []
    for index, bar in enumerate(chart_bars):
        first = map1[index]
        second = map2[index]
        if first is None and second is None:
            out.append(None)
            continue
        bias1 = macro1[first].bias if first is not None else 0
        bias2 = macro2[second].bias if second is not None else 0
        equilibrium = macro1[first].equilibrium if first is not None else None
        close = float(bar.close.value)
        alignment = bias1 + bias2
        out.append(
            HtfContext(
                macro1_bias=bias1,
                macro2_bias=bias2,
                alignment=alignment,
                bull_context=alignment > 0,
                bear_context=alignment < 0,
                confidence=abs(alignment) / 2.0,
                in_discount=equilibrium is not None and close < equilibrium,
                in_premium=equilibrium is not None and close > equilibrium,
            )
        )
    return out


def entropy01(probability: float) -> float:
    """Pine ``f_entropy01``: binary entropy of p, normalized to [0, 1]."""
    p = clamp(probability, 0.0001, 0.9999)
    return -(p * log(p) + (1.0 - p) * log(1.0 - p)) / log(2.0)


def min_max_scale(values: list[float], length: int) -> list[float]:
    """Pine ``f_minmax``: rolling min-max position; 0.5 while undefined."""
    out = [0.5] * len(values)
    for index in range(length - 1, len(values)):
        window = values[index - length + 1 : index + 1]
        low, high = min(window), max(window)
        span = high - low
        if span > 0:
            out[index] = (values[index] - low) / span
    return out


def rma(values: list[float], length: int) -> list[float | None]:
    """Wilder moving average (Pine ``ta.rma``): SMA seed, then recursive."""
    out: list[float | None] = [None] * len(values)
    current: float | None = None
    for index, value in enumerate(values):
        if index < length - 1:
            continue
        if current is None:
            current = sum(values[index - length + 1 : index + 1]) / length
        else:
            current = (current * (length - 1) + value) / length
        out[index] = current
    return out


def adx(bars: list[Bar], length: int) -> list[float | None]:
    """Average directional index (Pine ``ta.dmi`` third output)."""
    count = len(bars)
    plus_dm = [0.0] * count
    minus_dm = [0.0] * count
    true_ranges = [true_range(bars, index) for index in range(count)]
    for index in range(1, count):
        up = float(bars[index].high.value) - float(bars[index - 1].high.value)
        down = float(bars[index - 1].low.value) - float(bars[index].low.value)
        plus_dm[index] = up if up > down and up > 0 else 0.0
        minus_dm[index] = down if down > up and down > 0 else 0.0
    smoothed_tr = rma(true_ranges, length)
    smoothed_plus = rma(plus_dm, length)
    smoothed_minus = rma(minus_dm, length)
    dx: list[float] = [0.0] * count
    for index in range(count):
        tr_value = smoothed_tr[index]
        plus = smoothed_plus[index]
        minus = smoothed_minus[index]
        if tr_value is None or plus is None or minus is None or tr_value <= 0:
            continue
        plus_di = 100.0 * plus / tr_value
        minus_di = 100.0 * minus / tr_value
        total = plus_di + minus_di
        dx[index] = 100.0 * abs(plus_di - minus_di) / total if total > 0 else 0.0
    return rma(dx, length)


def cci(values: list[float], length: int) -> list[float | None]:
    """Commodity channel index (Pine ``ta.cci``) over a typical-price series."""
    out: list[float | None] = [None] * len(values)
    for index in range(length - 1, len(values)):
        window = values[index - length + 1 : index + 1]
        mean = sum(window) / length
        deviation = sum(abs(value - mean) for value in window) / length
        if deviation > 0:
            out[index] = (values[index] - mean) / (0.015 * deviation)
        else:
            out[index] = 0.0
    return out


def stochastic(values: list[float | None], length: int) -> list[float | None]:
    """Pine ``ta.stoch(x, x, x, len)``: rolling range position, 0-100."""
    out: list[float | None] = [None] * len(values)
    for index in range(len(values)):
        window = [
            value
            for value in values[max(0, index - length + 1) : index + 1]
            if value is not None
        ]
        if index < length - 1 or values[index] is None or not window:
            continue
        low, high = min(window), max(window)
        span = high - low
        current = values[index]
        if span > 0 and current is not None:
            out[index] = 100.0 * (current - low) / span
    return out


def schaff_trend_cycle(
    values: list[float],
    fast: int,
    slow: int,
    cycle: int,
) -> list[float]:
    """Pine ``f_stc``: double-stochastic MACD with half-speed smoothing.

    50.0 while undefined (the AICE ``nz(st, 50)`` fallback).
    """
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd: list[float | None] = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema, strict=True)
    ]
    k = stochastic(macd, cycle)
    d: list[float | None] = [None] * len(values)
    current_d: float | None = None
    for index, value in enumerate(k):
        if value is not None:
            current_d = value if current_d is None else current_d + 0.5 * (value - current_d)
        d[index] = current_d
    kd = stochastic(d, cycle)
    out = [50.0] * len(values)
    current_st: float | None = None
    for index, value in enumerate(kd):
        if value is not None:
            current_st = (
                value if current_st is None else current_st + 0.5 * (value - current_st)
            )
        if current_st is not None:
            out[index] = clamp(current_st, 0.0, 100.0)
    return out


# Discrete volatility regime multiplier (AICE line 988), shared by the
# volume and statistical families (Constitution 2.12).
WIDTH_WIDE, WIDTH_NARROW = 1.5, 0.6
FACTOR_WIDE, FACTOR_NARROW = 1.3, 0.75


def volatility_regime_factor(width: float) -> float:
    """AICE ``vol_factor``: 1.3 wide / 0.75 narrow / 1.0 normal."""
    if width > WIDTH_WIDE:
        return FACTOR_WIDE
    if width < WIDTH_NARROW:
        return FACTOR_NARROW
    return 1.0


def valid_tail(series: list[float | None]) -> tuple[int, list[float]]:
    """(offset of the first non-None value, dense tail from there)."""
    offset = next((i for i, value in enumerate(series) if value is not None), len(series))
    return offset, [value for value in series[offset:] if value is not None]
