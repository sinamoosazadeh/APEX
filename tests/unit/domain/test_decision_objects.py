"""Domain: Signal, Order, ProbabilityAssessment, Position, Portfolio."""

import uuid
from decimal import Decimal

import pytest
from apex.core.enums import (
    Direction,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionStatus,
    RiskMode,
)
from apex.core.exceptions import ValidationError
from apex.core.types import (
    Drawdown,
    Entropy,
    Leverage,
    Probability,
    Quantity,
    RiskScore,
    Volatility,
)
from apex.domain.money import Money
from apex.domain.order import Order
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.position import Position
from apex.domain.probability import ConfidenceInterval, ProbabilityAssessment
from apex.domain.risk import RiskAssessment
from apex.domain.snapshot import StateSnapshot

from tests.conftest import T0, make_signal, price

T1 = T0.add_ms(3_600_000)


class TestSignal:
    def test_valid_long_signal(self) -> None:
        signal = make_signal()
        assert signal.direction is Direction.LONG
        assert signal.object_version == 1

    def test_neutral_rejected(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            make_signal(direction=Direction.NEUTRAL)
        assert excinfo.value.code == "SIG-001"

    def test_long_requires_stop_below_entry(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            make_signal(direction=Direction.LONG, stop=("105", "106"))
        assert excinfo.value.code == "SIG-004"

    def test_short_requires_stop_above_entry(self) -> None:
        signal = make_signal(
            direction=Direction.SHORT,
            entry=("100", "101"),
            stop=("105", "106"),
            targets=(("90", "92"),),
        )
        assert signal.direction is Direction.SHORT
        with pytest.raises(ValidationError):
            make_signal(direction=Direction.SHORT, stop=("95", "96"))

    def test_requires_targets(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            make_signal(targets=())
        assert excinfo.value.code == "SIG-002"

    def test_zone_geometry(self) -> None:
        with pytest.raises(ValidationError):
            make_signal(entry=("101", "100"))

    def test_evolution_keeps_lineage(self) -> None:
        v1 = make_signal()
        v2 = v1.evolve(created_at=T1, probability=Probability(0.7))
        assert v2.lineage_id == v1.lineage_id
        assert v2.object_version == 2
        assert v1.probability.value == 0.62


class TestOrder:
    def make_order(self, **overrides: object) -> Order:
        defaults: dict[str, object] = {
            "created_at": T0,
            "exchange": "toobit",
            "symbol": "BTCUSDT",
            "side": OrderSide.BUY,
            "order_type": OrderType.LIMIT,
            "quantity": Quantity(Decimal("0.5")),
            "limit_price": price("42000"),
        }
        defaults.update(overrides)
        return Order(**defaults)  # type: ignore[arg-type]

    def test_limit_requires_price(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_order(limit_price=None)
        assert excinfo.value.code == "EXE-001"

    def test_market_must_not_carry_limit_price(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_order(order_type=OrderType.MARKET)
        assert excinfo.value.code == "EXE-002"

    def test_stop_orders_require_stop_price(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_order(order_type=OrderType.STOP_LIMIT)
        assert excinfo.value.code == "EXE-003"

    def test_status_progression_via_evolve(self) -> None:
        submitted = self.make_order()
        filled = submitted.evolve(created_at=T1, status=OrderStatus.FILLED)
        assert not submitted.is_terminal
        assert filled.is_terminal
        assert filled.lineage_id == submitted.lineage_id


class TestProbabilityAssessment:
    def make_assessment(self, **overrides: object) -> ProbabilityAssessment:
        defaults: dict[str, object] = {
            "created_at": T0,
            "subject": "signal.success",
            "probability": Probability(0.6),
            "distribution": {"win": Probability(0.6), "loss": Probability(0.4)},
            "confidence_interval": ConfidenceInterval(
                lower=Probability(0.5), upper=Probability(0.7)
            ),
            "entropy": Entropy(0.29),
            "sample_size": 250,
        }
        defaults.update(overrides)
        return ProbabilityAssessment(**defaults)  # type: ignore[arg-type]

    def test_valid_assessment(self) -> None:
        assert self.make_assessment().probability.value == 0.6

    def test_distribution_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_assessment(
                distribution={"win": Probability(0.6), "loss": Probability(0.3)}
            )
        assert excinfo.value.code == "VAL-102"

    def test_point_estimate_inside_interval(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_assessment(
                confidence_interval=ConfidenceInterval(
                    lower=Probability(0.65), upper=Probability(0.7)
                )
            )
        assert excinfo.value.code == "VAL-103"


class TestRiskAndPortfolio:
    def test_risk_assessment_invariants(self) -> None:
        assessment = RiskAssessment(
            created_at=T0,
            signal_id=uuid.uuid4(),
            risk_score=RiskScore(0.4),
            position_size=Quantity(Decimal("0.25")),
            max_exposure=Money.parse("USDT", "5000"),
            expected_loss=Money.parse("USDT", "50"),
            tail_loss=Money.parse("USDT", "180"),
            expected_drawdown=Drawdown(0.05),
            kelly_fraction=Probability(0.12),
            volatility_budget=Volatility(0.3),
            risk_mode=RiskMode.BALANCED,
        )
        assert assessment.is_tradeable
        with pytest.raises(ValidationError):
            RiskAssessment(
                created_at=T0,
                signal_id=uuid.uuid4(),
                risk_score=RiskScore(0.4),
                position_size=Quantity(Decimal("0.25")),
                max_exposure=Money.parse("USDT", "5000"),
                expected_loss=Money.parse("USDT", "200"),
                tail_loss=Money.parse("USDT", "100"),
                expected_drawdown=Drawdown(0.05),
                kelly_fraction=Probability(0.12),
                volatility_budget=Volatility(0.3),
                risk_mode=RiskMode.BALANCED,
            )

    def make_position(self, **overrides: object) -> Position:
        defaults: dict[str, object] = {
            "created_at": T0,
            "exchange": "toobit",
            "symbol": "BTCUSDT",
            "direction": Direction.LONG,
            "quantity": Quantity(Decimal("0.5")),
            "average_entry": price("42000"),
            "opened_at": T0,
            "leverage": Leverage(2.0),
        }
        defaults.update(overrides)
        return Position(**defaults)  # type: ignore[arg-type]

    def test_position_close_requires_timestamp(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_position(status=PositionStatus.CLOSED)
        assert excinfo.value.code == "RSK-011"

    def test_position_cannot_close_before_open(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self.make_position(
                status=PositionStatus.CLOSED,
                closed_at=T0.add_ms(-1000),
            )
        assert excinfo.value.code == "RSK-013"

    def test_portfolio_currency_consistency(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            PortfolioSnapshot(
                created_at=T0,
                as_of=T0,
                base_currency="USDT",
                equity=Money.parse("USDT", "10000"),
                cash=Money.parse("BTC", "1"),
                total_exposure=Money.parse("USDT", "0"),
                unrealized_pnl=Money.zero("USDT"),
                realized_pnl=Money.zero("USDT"),
                current_drawdown=Drawdown(0.0),
            )
        assert excinfo.value.code == "RSK-020"

    def test_portfolio_rejects_closed_positions_in_open_list(self) -> None:
        closed = self.make_position(
            status=PositionStatus.CLOSED, closed_at=T0.add_ms(1000)
        )
        with pytest.raises(ValidationError) as excinfo:
            PortfolioSnapshot(
                created_at=T0,
                as_of=T0,
                base_currency="USDT",
                equity=Money.parse("USDT", "10000"),
                cash=Money.parse("USDT", "5000"),
                total_exposure=Money.parse("USDT", "5000"),
                unrealized_pnl=Money.zero("USDT"),
                realized_pnl=Money.zero("USDT"),
                current_drawdown=Drawdown(0.0),
                open_positions=(closed,),
            )
        assert excinfo.value.code == "RSK-022"


class TestStateSnapshot:
    def test_hash_autofilled_and_verified(self) -> None:
        snapshot = StateSnapshot(
            created_at=T0,
            state_type="portfolio",
            taken_at=T0,
            payload={"equity": "10000"},
        )
        assert len(snapshot.payload_hash) == 64
        with pytest.raises(ValidationError) as excinfo:
            StateSnapshot(
                created_at=T0,
                state_type="portfolio",
                taken_at=T0,
                payload={"equity": "10000"},
                payload_hash="tampered",
            )
        assert excinfo.value.code == "VAL-110"
