"""Market structure feature family - migrated from AICE (Book VI).

Faithful port of the AICE Pine v6 "STRUCTURE / LIQUIDITY HIERARCHY"
block (spec lines ~1113-1201), per the Book II ch. 2 migration matrix:

- swing detection: strict pivot highs/lows confirmed ``lookback`` bars
  later (Pine ``ta.pivothigh(high, lb, lb)`` semantics - inherently
  non-repainting);
- break detection with cross semantics: ``close`` crossing the last
  swing (previous close on the inactive side);
- trend state machine: a break against the trend is a CHoCH, with the
  trend is a BOS; breaks flip ``trend_dir`` and update the protected
  swing;
- break quality ``clamp(body_atr / (displacement * 1.5), 0, 1)``
  decaying by ``0.985`` per bar (configurable);
- displacement: candle body in ATR units against a threshold;
- dealing range from the last swing pair: position, premium/discount,
  OTE windows [0.21, 0.38] and [0.62, 0.79];
- liquidity sweeps: wick beyond the swing with close back inside;
  equal highs/lows within ``ATR x tolerance``.

ATR is Wilder's (Pine ``ta.atr``): SMA seed over the first window,
then recursive smoothing. All values are computed from confirmed bars
only; the engine emits nothing during warmup.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from apex.core.context import MarketContext
from apex.core.exceptions import ApexError, FeatureError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import ensure_in_range, ensure_positive
from apex.domain.feature import Feature
from apex.domain.market import Bar

FAMILY = "structure"
_SOURCE = "apex.features.structure"

# OTE retracement windows (AICE spec lines 1192-1193).
_OTE_LONG_LOW, _OTE_LONG_HIGH = 0.21, 0.38
_OTE_SHORT_LOW, _OTE_SHORT_HIGH = 0.62, 0.79
# Break quality denominator factor (AICE line 1163).
_BREAK_QUALITY_FACTOR = 1.5
# Swing distance normalization horizon in ATR units.
_DISTANCE_NORM_ATR = 10.0

FEATURE_NAMES: tuple[str, ...] = (
    "structure.trend_direction",
    "structure.bos_up",
    "structure.bos_down",
    "structure.choch_up",
    "structure.choch_down",
    "structure.break_quality",
    "structure.displacement_body_atr",
    "structure.is_displacement",
    "structure.dealing_range_position",
    "structure.in_premium",
    "structure.in_discount",
    "structure.in_ote_long",
    "structure.in_ote_short",
    "structure.sweep_high",
    "structure.sweep_low",
    "structure.equal_highs",
    "structure.equal_lows",
    "structure.swing_high_distance",
    "structure.swing_low_distance",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StructureParams:
    """Tunables of the structure family (AICE input defaults)."""

    pivot_lookback: int = 8
    atr_length: int = 14
    displacement_body_atr: float = 1.20
    equal_tolerance_atr: float = 0.10
    break_decay: float = 0.985

    def __post_init__(self) -> None:
        ensure_positive(self.pivot_lookback, "pivot_lookback")
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.displacement_body_atr, "displacement_body_atr")
        ensure_positive(self.equal_tolerance_atr, "equal_tolerance_atr")
        ensure_in_range(self.break_decay, 0.0, 1.0, "break_decay")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission."""
        return max(self.atr_length, 2 * self.pivot_lookback + 1)


@dataclass(slots=True)
class _StructureState:
    """Mutable fold state mirroring the AICE ``var`` block."""

    last_ph: float | None = None
    prev_ph: float | None = None
    last_pl: float | None = None
    prev_pl: float | None = None
    trend_dir: int = 0
    protected_high: float | None = None
    protected_low: float | None = None
    break_quality: float = 0.0
    last_break_index: int | None = None
    atr: float | None = None


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


class MarketStructureEngine:
    """Computes the structure family over a confirmed-bar window."""

    def __init__(self, *, params: StructureParams, clock: Clock) -> None:
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
        state = _StructureState()
        highs = [float(bar.high.value) for bar in bars]
        lows = [float(bar.low.value) for bar in bars]
        features: list[Feature] = []
        for index, bar in enumerate(bars):
            self._update_atr(state, bars, index)
            pivot_flags = self._confirm_pivots(state, highs, lows, index)
            snapshot = self._step(state, bars, index, pivot_flags)
            if index >= params.warmup_bars and state.atr is not None:
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

    def _update_atr(self, state: _StructureState, bars: list[Bar], index: int) -> None:
        """Wilder ATR (Pine ``ta.atr``): SMA seed, then recursive."""
        length = self._params.atr_length
        tr = self._true_range(bars, index)
        if index < length - 1:
            return
        if state.atr is None:
            seed = sum(self._true_range(bars, i) for i in range(length)) / length
            state.atr = seed
            return
        state.atr = (state.atr * (length - 1) + tr) / length

    @staticmethod
    def _true_range(bars: list[Bar], index: int) -> float:
        high = float(bars[index].high.value)
        low = float(bars[index].low.value)
        if index == 0:
            return high - low
        prev_close = float(bars[index - 1].close.value)
        return max(high - low, abs(high - prev_close), abs(low - prev_close))

    def _confirm_pivots(
        self,
        state: _StructureState,
        highs: list[float],
        lows: list[float],
        index: int,
    ) -> tuple[bool, bool]:
        """Pine pivot semantics: bar ``lb`` back is a strict extremum."""
        lb = self._params.pivot_lookback
        candidate = index - lb
        if candidate < lb:
            return False, False
        window = range(candidate - lb, candidate + lb + 1)
        new_high = all(
            highs[candidate] > highs[i] for i in window if i != candidate
        )
        new_low = all(lows[candidate] < lows[i] for i in window if i != candidate)
        if new_high:
            state.prev_ph = state.last_ph
            state.last_ph = highs[candidate]
        if new_low:
            state.prev_pl = state.last_pl
            state.last_pl = lows[candidate]
        return new_high, new_low

    def _step(
        self,
        state: _StructureState,
        bars: list[Bar],
        index: int,
        pivot_flags: tuple[bool, bool],
    ) -> dict[str, float]:
        """One bar of the AICE structure state machine."""
        params = self._params
        bar = bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        prev_close = float(bars[index - 1].close.value) if index > 0 else close
        atr = state.atr if state.atr is not None and state.atr > 0 else None

        body = abs(close - float(bar.open.value))
        body_atr = body / atr if atr else 0.0
        is_displacement = body_atr >= params.displacement_body_atr

        new_high, new_low = pivot_flags
        tolerance = (atr or 0.0) * params.equal_tolerance_atr
        equal_highs = (
            new_high
            and state.prev_ph is not None
            and state.last_ph is not None
            and abs(state.last_ph - state.prev_ph) <= tolerance
        )
        equal_lows = (
            new_low
            and state.prev_pl is not None
            and state.last_pl is not None
            and abs(state.last_pl - state.prev_pl) <= tolerance
        )

        bos_up = bos_dn = choch_up = choch_dn = False
        if state.last_ph is not None and close > state.last_ph and prev_close <= state.last_ph:
            if state.trend_dir == -1:
                choch_up = True
            else:
                bos_up = True
            state.trend_dir = 1
            state.protected_low = state.last_pl
            state.break_quality = _clamp(
                body_atr / (params.displacement_body_atr * _BREAK_QUALITY_FACTOR), 0.0, 1.0
            )
            state.last_break_index = index
        if state.last_pl is not None and close < state.last_pl and prev_close >= state.last_pl:
            if state.trend_dir == 1:
                choch_dn = True
            else:
                bos_dn = True
            state.trend_dir = -1
            state.protected_high = state.last_ph
            state.break_quality = _clamp(
                body_atr / (params.displacement_body_atr * _BREAK_QUALITY_FACTOR), 0.0, 1.0
            )
            state.last_break_index = index

        if state.last_break_index is not None:
            age = index - state.last_break_index
            break_quality_live = state.break_quality * (params.break_decay**age)
        else:
            break_quality_live = 0.0

        dr_pos = 0.5
        in_premium = in_discount = False
        if state.last_ph is not None and state.last_pl is not None:
            top = max(state.last_ph, state.last_pl)
            bottom = min(state.last_ph, state.last_pl)
            size = top - bottom
            if size > 0:
                dr_pos = _clamp((close - bottom) / size, 0.0, 1.0)
                equilibrium = (top + bottom) / 2.0
                in_discount = close < equilibrium
                in_premium = close > equilibrium

        sweep_high = state.last_ph is not None and high > state.last_ph and close < state.last_ph
        sweep_low = state.last_pl is not None and low < state.last_pl and close > state.last_pl

        swing_high_distance = (
            (close - state.last_ph) / atr if atr and state.last_ph is not None else 0.0
        )
        swing_low_distance = (
            (close - state.last_pl) / atr if atr and state.last_pl is not None else 0.0
        )

        return {
            "structure.trend_direction": float(state.trend_dir),
            "structure.bos_up": 1.0 if bos_up else 0.0,
            "structure.bos_down": 1.0 if bos_dn else 0.0,
            "structure.choch_up": 1.0 if choch_up else 0.0,
            "structure.choch_down": 1.0 if choch_dn else 0.0,
            "structure.break_quality": break_quality_live,
            "structure.displacement_body_atr": body_atr,
            "structure.is_displacement": 1.0 if is_displacement else 0.0,
            "structure.dealing_range_position": dr_pos,
            "structure.in_premium": 1.0 if in_premium else 0.0,
            "structure.in_discount": 1.0 if in_discount else 0.0,
            "structure.in_ote_long": (
                1.0 if _OTE_LONG_LOW <= dr_pos <= _OTE_LONG_HIGH else 0.0
            ),
            "structure.in_ote_short": (
                1.0 if _OTE_SHORT_LOW <= dr_pos <= _OTE_SHORT_HIGH else 0.0
            ),
            "structure.sweep_high": 1.0 if sweep_high else 0.0,
            "structure.sweep_low": 1.0 if sweep_low else 0.0,
            "structure.equal_highs": 1.0 if equal_highs else 0.0,
            "structure.equal_lows": 1.0 if equal_lows else 0.0,
            "structure.swing_high_distance": swing_high_distance,
            "structure.swing_low_distance": swing_low_distance,
        }

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
        params = self._params
        if name in ("structure.break_quality",):
            return _clamp(raw, 0.0, 1.0) * 2.0 - 1.0
        if name == "structure.dealing_range_position":
            return raw * 2.0 - 1.0
        if name == "structure.displacement_body_atr":
            return _clamp(raw / (2.0 * params.displacement_body_atr), 0.0, 1.0) * 2.0 - 1.0
        if name in ("structure.swing_high_distance", "structure.swing_low_distance"):
            return _clamp(raw / _DISTANCE_NORM_ATR, -1.0, 1.0)
        # Trend direction and binary flags are already within [-1, 1].
        return _clamp(raw, -1.0, 1.0)
