"""Feature contract (Book II 5.8).

Every feature - ICT, SMC, statistical, volume, whatever family -
shares this exact contract, which is what makes the feature platform
pluggable and the probability engine family-agnostic.

Contract evolution (5.35, Phase 4): a feature is anchored to the
series bar it was computed from (exchange, symbol, timeframe, bar
open time) - the Feature Store keys on this anchor, and every value
derives from confirmed bars only (non-repainting).
"""

from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.enums import Timeframe
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import (
    ensure_finite,
    ensure_in_range,
    ensure_not_empty,
    ensure_symbol,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Feature(BaseObject):
    """One computed feature value anchored to a series bar.

    Attributes:
        name: unique feature name within its family.
        family: feature family (e.g. ``structure``, ``volume``).
        exchange: source exchange of the underlying series.
        symbol: instrument the feature was computed for.
        timeframe: bar timeframe of the underlying series.
        bar_open_time: open time of the confirmed bar the value
            belongs to (the feature's anchor in the store).
        value: raw computed value.
        normalized_value: value mapped into [-1, 1] for model consumption.
        weight: combination weight assigned by configuration/optimizer.
        confidence: producer's confidence in this computation.
        reliability: historical reliability of the source.
        source: dotted name of the producing component.
        computed_at: when the value was computed (confirmed data only).
    """

    name: str
    family: str
    exchange: str
    symbol: str
    timeframe: Timeframe
    bar_open_time: Timestamp
    value: float
    normalized_value: float
    weight: Weight
    confidence: Confidence
    reliability: Reliability
    source: str
    computed_at: Timestamp

    def _validate(self) -> None:
        ensure_not_empty(self.name, "name")
        ensure_not_empty(self.family, "family")
        ensure_not_empty(self.exchange, "exchange")
        ensure_symbol(self.symbol)
        ensure_not_empty(self.source, "source")
        ensure_finite(self.value, "value")
        ensure_in_range(self.normalized_value, -1.0, 1.0, "normalized_value")
        if self.family != self.family.lower():
            raise ValidationError(
                "feature family must be lowercase",
                code="VAL-090",
                details={"family": self.family},
            )
