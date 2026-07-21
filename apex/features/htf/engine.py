"""HTF/MTF context feature family - migrated from AICE.

Faithful port of the AICE macro context block (Book VI spec lines
1087-1097): ``f_struct_pack`` evaluated on two macro timeframes gives
each a bias (+1 above the last pivot high, -1 below the last pivot
low, else the EMA side); their sum is the HTF alignment, and the
macro-1 pivot midpoint splits HTF discount from premium.

Non-repainting mapping (Constitution over AICE on conflict): Pine's
``request.security(lookahead_off)`` exposes the forming macro bar's
running values; APEX instead maps every chart bar to the **last
closed** macro bar at that bar's close time, so no value can change
after emission.

Auxiliary-free fallback: without stored macro series the engine emits
nothing (the documented neutral behavior for context families).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from apex.core.context import MarketContext
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, FeatureError
from apex.core.result import Result
from apex.core.time.clock import Clock
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import ensure_positive
from apex.domain.feature import Feature
from apex.domain.market import Bar
from apex.features.calculations import HtfContext, clamp, htf_context_series

FAMILY = "htf"
_SOURCE = "apex.features.htf"

FEATURE_NAMES: tuple[str, ...] = (
    "htf.macro1_bias",
    "htf.macro2_bias",
    "htf.alignment",
    "htf.bull_context",
    "htf.bear_context",
    "htf.confidence",
    "htf.in_discount",
    "htf.in_premium",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class HtfParams:
    """Tunables of the HTF context family (AICE input defaults)."""

    pivot_lookback: int = 8
    ema_length: int = 50

    def __post_init__(self) -> None:
        ensure_positive(self.pivot_lookback, "pivot_lookback")
        ensure_positive(self.ema_length, "ema_length")


class HtfContextEngine:
    """Computes HTF alignment/discount from closed macro bars."""

    def __init__(
        self,
        *,
        params: HtfParams,
        macro_timeframes: tuple[Timeframe, Timeframe],
        clock: Clock,
    ) -> None:
        self._params = params
        self._macro = macro_timeframes
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
        """Both macro series of the chart symbol."""
        return ((symbol, self._macro[0]), (symbol, self._macro[1]))

    def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Auxiliary-free fallback: no macro series, nothing to say."""
        return self.compute_with_context(bars, {}, context)

    def compute_with_context(
        self,
        bars: Sequence[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Fold the chart window against the closed macro series."""
        try:
            features = self._compute_all(list(bars), auxiliary, context)
        except ApexError as error:
            return Result.failure(error)
        return Result.success(tuple(features))

    def _compute_all(
        self,
        bars: list[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> list[Feature]:
        self._require_confirmed_series(bars)
        macro1 = list(auxiliary.get((context.symbol, self._macro[0]), ()))
        macro2 = list(auxiliary.get((context.symbol, self._macro[1]), ()))
        if not bars or (not macro1 and not macro2):
            return []
        for series in (macro1, macro2):
            self._require_confirmed_series(series)
        contexts = htf_context_series(
            bars,
            macro1,
            macro2,
            pivot_lookback=self._params.pivot_lookback,
            ema_length=self._params.ema_length,
        )
        features: list[Feature] = []
        for bar, snapshot in zip(bars, contexts, strict=True):
            if snapshot is not None:
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

    def _emit(self, bar: Bar, snapshot: HtfContext) -> list[Feature]:
        values: dict[str, tuple[float, float]] = {
            "htf.macro1_bias": (float(snapshot.macro1_bias), float(snapshot.macro1_bias)),
            "htf.macro2_bias": (float(snapshot.macro2_bias), float(snapshot.macro2_bias)),
            "htf.alignment": (float(snapshot.alignment), clamp(snapshot.alignment / 2.0, -1, 1)),
            "htf.bull_context": self._binary(snapshot.bull_context),
            "htf.bear_context": self._binary(snapshot.bear_context),
            "htf.confidence": (snapshot.confidence, snapshot.confidence * 2.0 - 1.0),
            "htf.in_discount": self._binary(snapshot.in_discount),
            "htf.in_premium": self._binary(snapshot.in_premium),
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
