"""Probability contract (Book II 5.9).

A probability in APEX is never a bare number: it carries its
distribution, confidence interval, entropy, calibration diagnostics,
sample size and the evidence behind it.
"""

import uuid
from dataclasses import dataclass, field

from apex.core.base import BaseObject
from apex.core.constants import FLOAT_COMPARISON_TOLERANCE
from apex.core.exceptions import ValidationError
from apex.core.types import Entropy, Probability
from apex.core.validation import ensure_in_range, ensure_not_empty


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    """A [lower, upper] interval on a probability."""

    lower: Probability
    upper: Probability

    def __post_init__(self) -> None:
        if self.lower.value > self.upper.value:
            raise ValidationError(
                "confidence interval lower bound above upper",
                code="VAL-100",
                details={"lower": self.lower.value, "upper": self.upper.value},
            )

    def contains(self, probability: Probability) -> bool:
        """Whether the interval contains ``probability``."""
        return self.lower.value <= probability.value <= self.upper.value


@dataclass(frozen=True, slots=True, kw_only=True)
class ProbabilityAssessment(BaseObject):
    """A full probabilistic judgement (probability contract, 5.9).

    Attributes:
        subject: what is being assessed (e.g. ``signal.success``).
        probability: point estimate.
        distribution: outcome name -> probability; must sum to 1.
        confidence_interval: uncertainty band around the estimate.
        entropy: dispersion of the distribution.
        sample_size: number of observations behind the estimate.
        calibration_error: measured calibration gap, when known.
        drift: measured distribution drift, when known.
        evidence_ids: objects (features, experiments) supporting this.
    """

    subject: str
    probability: Probability
    distribution: dict[str, Probability]
    confidence_interval: ConfidenceInterval
    entropy: Entropy
    sample_size: int
    calibration_error: float | None = None
    drift: float | None = None
    evidence_ids: tuple[uuid.UUID, ...] = field(default=())

    def _validate(self) -> None:
        ensure_not_empty(self.subject, "subject")
        ensure_not_empty(self.distribution, "distribution")
        if self.sample_size < 0:
            raise ValidationError(
                "sample_size must be non-negative",
                code="VAL-101",
                details={"sample_size": self.sample_size},
            )
        total = sum(p.value for p in self.distribution.values())
        if abs(total - 1.0) > 1e-9:
            raise ValidationError(
                "distribution probabilities must sum to 1",
                code="VAL-102",
                details={"total": total},
            )
        if not self.confidence_interval.contains(self.probability):
            raise ValidationError(
                "point estimate outside its confidence interval",
                code="VAL-103",
                details={"probability": self.probability.value},
            )
        if self.calibration_error is not None:
            ensure_in_range(self.calibration_error, 0.0, 1.0, "calibration_error")
        if self.drift is not None:
            ensure_in_range(
                self.drift,
                -1.0 - FLOAT_COMPARISON_TOLERANCE,
                1.0 + FLOAT_COMPARISON_TOLERANCE,
                "drift",
            )
