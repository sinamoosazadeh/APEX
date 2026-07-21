"""Shared feature calculations (Pine-faithful primitives).

Building blocks used by multiple feature families, ported once from
their Pine counterparts (Constitution 2.12: no duplicate logic):

- Wilder ATR (Pine ``ta.atr``): SMA seed, then recursive smoothing.
- EMA (Pine ``ta.ema``): SMA seed, then ``alpha = 2 / (length + 1)``.
- Strict pivot tracking (Pine ``ta.pivothigh/pivotlow`` semantics):
  a pivot is confirmed ``lookback`` bars after it printed.
- Rolling extremes with a one-bar shift (Pine ``ta.highest(x, n)[1]``).
"""

from dataclasses import dataclass, field

from apex.domain.market import Bar


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
