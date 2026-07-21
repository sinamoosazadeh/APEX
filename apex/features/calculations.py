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
from math import exp

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
