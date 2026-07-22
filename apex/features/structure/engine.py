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
from apex.features.calculations import (
    PivotTracker,
    StructureFold,
    clamp,
    struct_bias_series,
    wilder_atr,
)

FAMILY = "structure"
_SOURCE = "apex.features.structure"

# OTE retracement windows (AICE spec lines 1192-1193).
_OTE_LONG_LOW, _OTE_LONG_HIGH = 0.21, 0.38
_OTE_SHORT_LOW, _OTE_SHORT_HIGH = 0.62, 0.79
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
    "structure.internal_bias",
    "structure.external_bias",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StructureParams:
    """Tunables of the structure family (AICE input defaults)."""

    pivot_lookback: int = 8
    atr_length: int = 14
    displacement_body_atr: float = 1.20
    equal_tolerance_atr: float = 0.10
    break_decay: float = 0.985
    internal_lookback: int = 3
    external_lookback: int = 21
    bias_ema_length: int = 50

    def __post_init__(self) -> None:
        ensure_positive(self.internal_lookback, "internal_lookback")
        ensure_positive(self.external_lookback, "external_lookback")
        ensure_positive(self.bias_ema_length, "bias_ema_length")
        ensure_positive(self.pivot_lookback, "pivot_lookback")
        ensure_positive(self.atr_length, "atr_length")
        ensure_positive(self.displacement_body_atr, "displacement_body_atr")
        ensure_positive(self.equal_tolerance_atr, "equal_tolerance_atr")
        ensure_in_range(self.break_decay, 0.0, 1.0, "break_decay")

    @property
    def warmup_bars(self) -> int:
        """Bars required before the first feature emission."""
        return max(self.atr_length, 2 * self.pivot_lookback + 1)


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
        fold = StructureFold(
            pivots=PivotTracker(lookback=params.pivot_lookback),
            displacement_body_atr=params.displacement_body_atr,
            break_decay=params.break_decay,
        )
        atr_series = wilder_atr(bars, params.atr_length)
        internal = struct_bias_series(
            bars, lookback=params.internal_lookback, ema_length=params.bias_ema_length
        )
        external = struct_bias_series(
            bars, lookback=params.external_lookback, ema_length=params.bias_ema_length
        )
        features: list[Feature] = []
        for index, bar in enumerate(bars):
            atr = atr_series[index]
            snapshot = self._step(fold, bars, index, atr)
            snapshot["structure.internal_bias"] = float(internal[index].bias)
            snapshot["structure.external_bias"] = float(external[index].bias)
            if index >= params.warmup_bars and atr is not None:
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
        fold: StructureFold,
        bars: list[Bar],
        index: int,
        raw_atr: float | None,
    ) -> dict[str, float]:
        """One bar of the AICE structure state machine."""
        params = self._params
        bar = bars[index]
        close = float(bar.close.value)
        high = float(bar.high.value)
        low = float(bar.low.value)
        signals = fold.update(bars, index, raw_atr)
        pivots = fold.pivots
        atr = raw_atr if raw_atr is not None and raw_atr > 0 else None
        last_ph, last_pl = pivots.last_high, pivots.last_low

        tolerance = (atr or 0.0) * params.equal_tolerance_atr
        equal_highs = (
            signals.new_pivot_high
            and pivots.prev_high is not None
            and last_ph is not None
            and abs(last_ph - pivots.prev_high) <= tolerance
        )
        equal_lows = (
            signals.new_pivot_low
            and pivots.prev_low is not None
            and last_pl is not None
            and abs(last_pl - pivots.prev_low) <= tolerance
        )

        sweep_high = last_ph is not None and high > last_ph and close < last_ph
        sweep_low = last_pl is not None and low < last_pl and close > last_pl

        swing_high_distance = (
            (close - last_ph) / atr if atr and last_ph is not None else 0.0
        )
        swing_low_distance = (
            (close - last_pl) / atr if atr and last_pl is not None else 0.0
        )

        dr_pos = signals.dealing_range_position
        return {
            "structure.trend_direction": float(signals.trend_direction),
            "structure.bos_up": 1.0 if signals.bos_up else 0.0,
            "structure.bos_down": 1.0 if signals.bos_down else 0.0,
            "structure.choch_up": 1.0 if signals.choch_up else 0.0,
            "structure.choch_down": 1.0 if signals.choch_down else 0.0,
            "structure.break_quality": signals.break_quality,
            "structure.displacement_body_atr": signals.body_atr,
            "structure.is_displacement": 1.0 if signals.is_displacement else 0.0,
            "structure.dealing_range_position": dr_pos,
            "structure.in_premium": 1.0 if signals.in_premium else 0.0,
            "structure.in_discount": 1.0 if signals.in_discount else 0.0,
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
            return clamp(raw, 0.0, 1.0) * 2.0 - 1.0
        if name == "structure.dealing_range_position":
            return raw * 2.0 - 1.0
        if name == "structure.displacement_body_atr":
            return clamp(raw / (2.0 * params.displacement_body_atr), 0.0, 1.0) * 2.0 - 1.0
        if name in ("structure.swing_high_distance", "structure.swing_low_distance"):
            return clamp(raw / _DISTANCE_NORM_ATR, -1.0, 1.0)
        # Trend direction and binary flags are already within [-1, 1].
        return clamp(raw, -1.0, 1.0)
