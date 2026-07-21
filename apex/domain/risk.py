"""Risk contract (Book II 5.10).

The risk platform always answers with a full assessment - sizing,
exposure ceiling, expected and tail loss, Kelly fraction, volatility
budget and posture - never a bare number.
"""

import uuid
from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.enums import RiskMode
from apex.core.exceptions import ValidationError
from apex.core.types import Drawdown, Probability, Quantity, RiskScore, Volatility
from apex.domain.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskAssessment(BaseObject):
    """Risk platform verdict for one prospective trade (5.10)."""

    signal_id: uuid.UUID
    risk_score: RiskScore
    position_size: Quantity
    max_exposure: Money
    expected_loss: Money
    tail_loss: Money
    expected_drawdown: Drawdown
    kelly_fraction: Probability
    volatility_budget: Volatility
    risk_mode: RiskMode

    def _validate(self) -> None:
        if self.max_exposure.is_negative:
            raise ValidationError(
                "max_exposure cannot be negative",
                code="RSK-001",
                details={"max_exposure": str(self.max_exposure)},
            )
        if self.expected_loss.amount > self.tail_loss.amount:
            raise ValidationError(
                "expected loss cannot exceed tail loss",
                code="RSK-002",
                details={
                    "expected_loss": str(self.expected_loss),
                    "tail_loss": str(self.tail_loss),
                },
            )

    @property
    def is_tradeable(self) -> bool:
        """Whether the platform posture permits opening the trade."""
        return self.risk_mode is not RiskMode.HALTED
