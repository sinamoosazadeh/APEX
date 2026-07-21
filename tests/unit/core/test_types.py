"""Wrapper value types: bounds, cross-type safety, arithmetic."""

from decimal import Decimal

import pytest
from apex.core.exceptions import ValidationError
from apex.core.types import (
    Confidence,
    Latency,
    Leverage,
    Price,
    Probability,
    Quantity,
    RiskReward,
    Volume,
    Weight,
)


class TestFloatTypes:
    def test_probability_bounds(self) -> None:
        assert Probability(0.0).value == 0.0
        assert Probability(1.0).value == 1.0
        with pytest.raises(ValidationError):
            Probability(1.01)
        with pytest.raises(ValidationError):
            Probability(-0.01)

    def test_nan_and_infinity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Probability(float("nan"))
        with pytest.raises(ValidationError):
            Latency(float("inf"))

    def test_cross_type_arithmetic_is_a_contract_violation(self) -> None:
        with pytest.raises(ValidationError):
            _ = Probability(0.5) + Confidence(0.5)
        with pytest.raises(ValidationError):
            _ = Weight(1.0) - Probability(0.2)

    def test_same_type_arithmetic(self) -> None:
        assert (Weight(1.5) + Weight(0.5)).value == 2.0
        assert (Weight(1.5) - Weight(0.5)).value == 1.0
        assert Weight(2.0).scale(1.5).value == 3.0
        assert Weight(3.0).ratio_to(Weight(2.0)) == 1.5

    def test_bounds_survive_arithmetic(self) -> None:
        with pytest.raises(ValidationError):
            _ = Probability(0.9) + Probability(0.2)

    def test_exclusive_minimum(self) -> None:
        with pytest.raises(ValidationError):
            Leverage(0.0)
        with pytest.raises(ValidationError):
            RiskReward(0.0)
        assert Leverage(0.5).value == 0.5

    def test_probability_complement(self) -> None:
        assert Probability(0.3).complement().value == pytest.approx(0.7)

    def test_ordering_within_type(self) -> None:
        assert Probability(0.2) < Probability(0.4)

    def test_bool_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Probability(True)


class TestDecimalTypes:
    def test_price_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Price(Decimal(0))
        with pytest.raises(ValidationError):
            Price(Decimal(-1))
        assert Price(Decimal("0.00000001")).value == Decimal("0.00000001")

    def test_volume_allows_zero(self) -> None:
        assert Volume(Decimal(0)).value == 0

    def test_parse_rejects_float(self) -> None:
        with pytest.raises(ValidationError):
            Price.parse(1.5)  # type: ignore[arg-type]

    def test_parse_exact(self) -> None:
        assert Price.parse("42500.50").value == Decimal("42500.50")
        assert Quantity.parse(3).value == Decimal(3)

    def test_direct_float_construction_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Price(1.5)  # type: ignore[arg-type]

    def test_cross_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _ = Price(Decimal(10)) + Volume(Decimal(5))

    def test_exact_arithmetic(self) -> None:
        total = Price.parse("0.1") + Price.parse("0.2")
        assert total.value == Decimal("0.3")
        assert Price.parse("10").scale(Decimal("2.5")).value == Decimal("25")
        assert Price.parse("10").ratio_to(Price.parse("4")) == Decimal("2.5")

    def test_parse_garbage_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Price.parse("not-a-number")
