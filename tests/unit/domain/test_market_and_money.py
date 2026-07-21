"""Domain: Money, Bar, Tick contracts."""

from decimal import Decimal

import pytest
from apex.core.enums import OrderSide, Timeframe
from apex.core.exceptions import ValidationError
from apex.core.types import Price, Quantity
from apex.domain.market import Tick
from apex.domain.money import Money

from tests.conftest import T0, make_bar, price


class TestMoney:
    def test_exact_arithmetic(self) -> None:
        total = Money.parse("USDT", "0.1") + Money.parse("USDT", "0.2")
        assert total.amount == Decimal("0.3")

    def test_currency_safety(self) -> None:
        with pytest.raises(ValidationError):
            _ = Money.parse("USDT", "1") + Money.parse("BTC", "1")

    def test_float_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Money.parse("USDT", 1.5)  # type: ignore[arg-type]

    def test_lowercase_currency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Money.parse("usdt", "1")

    def test_negation_and_sign(self) -> None:
        fee = Money.parse("USDT", "2.5")
        assert (-fee).is_negative
        assert Money.zero("USDT").amount == 0

    def test_scale(self) -> None:
        assert Money.parse("USDT", "10").scale(Decimal("0.5")).amount == Decimal("5")


class TestBar:
    def test_valid_bar(self) -> None:
        bar = make_bar()
        assert bar.is_bullish
        assert bar.close_time.diff_ms(bar.open_time) == Timeframe.H1.duration_ms
        assert bar.natural_key() == f"toobit:BTCUSDT:1h:{T0.epoch_ms}"

    def test_ohlc_geometry_enforced(self) -> None:
        with pytest.raises(ValidationError):
            make_bar(high="90")  # high below low
        with pytest.raises(ValidationError):
            make_bar(close="120")  # close above high
        with pytest.raises(ValidationError):
            make_bar(open_="90")  # open below low

    def test_non_repainting_gate(self) -> None:
        closed = make_bar(is_closed=True)
        forming = make_bar(is_closed=False)
        assert closed.require_closed() is closed
        with pytest.raises(ValidationError) as excinfo:
            forming.require_closed()
        assert excinfo.value.code == "DAT-004"

    def test_content_hash_is_stable(self) -> None:
        assert make_bar().content_hash() == make_bar().content_hash()
        assert make_bar().content_hash() != make_bar(close="106").content_hash()

    def test_symbol_format_enforced(self) -> None:
        with pytest.raises(ValidationError):
            Tick(
                exchange="toobit",
                symbol="btc/usdt",
                occurred_at=T0,
                price=price("100"),
                quantity=Quantity(Decimal(1)),
                aggressor=OrderSide.BUY,
            )

    def test_tick_serializes(self) -> None:
        tick = Tick(
            exchange="toobit",
            symbol="BTCUSDT",
            occurred_at=T0,
            price=Price(Decimal("100.5")),
            quantity=Quantity(Decimal("0.25")),
            aggressor=OrderSide.SELL,
        )
        data = tick.to_dict()
        assert data["price"] == {"value": "100.5"}
        assert data["aggressor"] == "sell"
