"""Feature contract (Book II 5.8).

Every feature - ICT, SMC, statistical, volume, whatever family -
shares this exact contract, which is what makes the feature platform
pluggable and the probability engine family-agnostic.
"""

from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.types import Confidence, Reliability, Weight
from apex.core.validation import ensure_finite, ensure_in_range, ensure_not_empty


@dataclass(frozen=True, slots=True, kw_only=True)
class Feature(BaseObject):
    """One computed feature value.

    Attributes:
        name: unique feature name within its family.
        family: feature family (e.g. ``ict``, ``volume``, ``statistical``).
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
        ensure_not_empty(self.source, "source")
        ensure_finite(self.value, "value")
        ensure_in_range(self.normalized_value, -1.0, 1.0, "normalized_value")
        if self.family != self.family.lower():
            raise ValidationError(
                "feature family must be lowercase",
                code="VAL-090",
                details={"family": self.family},
            )
