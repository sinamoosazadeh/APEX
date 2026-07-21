"""Toobit anti-corruption layer (Book II 5.37).

Translates Toobit wire formats into domain contracts. No Toobit
concept crosses this boundary: consumers see :class:`Bar` and
:class:`Tick`, never kline arrays or ``ibm`` flags.

Non-repainting: a kline whose close time has not passed yet is a
*forming* bar (``is_closed=False``); decision engines are gated on
confirmed bars only (Master Prompt 3.2).
"""

from decimal import Decimal, InvalidOperation
from typing import Final

from apex.core.enums import OrderSide, Timeframe
from apex.core.exceptions import DataError
from apex.core.serialization import JsonValue
from apex.core.time.timestamp import Timestamp
from apex.core.types import Price, QualityScore, Quantity, Volume
from apex.domain.market import Bar, Tick

EXCHANGE_ID: Final[str] = "toobit"

# Kline array indices (Book VII, GET /quote/v1/klines).
_OPEN_TIME: Final[int] = 0
_OPEN: Final[int] = 1
_HIGH: Final[int] = 2
_LOW: Final[int] = 3
_CLOSE: Final[int] = 4
_VOLUME: Final[int] = 5
_TRADE_COUNT: Final[int] = 8
_MIN_KLINE_FIELDS: Final[int] = 6

_FULL_QUALITY: Final[QualityScore] = QualityScore(1.0)


def interval_for(timeframe: Timeframe) -> str:
    """Toobit interval notation; identical to the canonical enum value."""
    return timeframe.value


class ToobitTranslator:
    """Maps Toobit wire payloads onto domain contracts."""

    def to_bar(
        self,
        symbol: str,
        timeframe: Timeframe,
        kline: list[JsonValue],
        *,
        now: Timestamp,
    ) -> Bar:
        """Translate one kline array into a domain Bar."""
        if len(kline) < _MIN_KLINE_FIELDS:
            raise DataError(
                "kline array has too few fields",
                code="DAT-013",
                details={"symbol": symbol, "fields": len(kline)},
            )
        open_time = self._parse_time(kline[_OPEN_TIME], symbol)
        close_time = open_time.add_ms(timeframe.duration_ms)
        trade_count: int | None = None
        raw_trades = kline[_TRADE_COUNT] if len(kline) > _TRADE_COUNT else None
        if isinstance(raw_trades, int) and not isinstance(raw_trades, bool):
            trade_count = raw_trades
        return Bar(
            exchange=EXCHANGE_ID,
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            open=Price(self._parse_decimal(kline[_OPEN], "open", symbol)),
            high=Price(self._parse_decimal(kline[_HIGH], "high", symbol)),
            low=Price(self._parse_decimal(kline[_LOW], "low", symbol)),
            close=Price(self._parse_decimal(kline[_CLOSE], "close", symbol)),
            volume=Volume(self._parse_decimal(kline[_VOLUME], "volume", symbol)),
            is_closed=close_time.epoch_ms <= now.epoch_ms,
            trade_count=trade_count,
            quality=_FULL_QUALITY,
        )

    def to_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        klines: list[list[JsonValue]],
        *,
        now: Timestamp,
    ) -> list[Bar]:
        """Translate a kline batch, sorted by open time ascending."""
        bars = [self.to_bar(symbol, timeframe, kline, now=now) for kline in klines]
        return sorted(bars, key=lambda bar: bar.open_time.epoch_ms)

    def to_tick(self, symbol: str, trade: dict[str, JsonValue]) -> Tick:
        """Translate one public trade object into a domain Tick.

        Toobit semantics: ``ibm`` (is buyer maker) true means the
        seller was the aggressor.
        """
        for field in ("p", "q", "t"):
            if field not in trade:
                raise DataError(
                    "trade object missing required field",
                    code="DAT-014",
                    details={"symbol": symbol, "field": field},
                )
        aggressor = OrderSide.SELL if bool(trade.get("ibm")) else OrderSide.BUY
        return Tick(
            exchange=EXCHANGE_ID,
            symbol=symbol,
            occurred_at=self._parse_time(trade["t"], symbol),
            price=Price(self._parse_decimal(trade["p"], "price", symbol)),
            quantity=Quantity(self._parse_decimal(trade["q"], "quantity", symbol)),
            aggressor=aggressor,
        )

    # --- WebSocket stream payloads (Book VII, /quote/ws/v1) -----------------------

    def stream_klines_to_bars(
        self,
        message: dict[str, JsonValue],
        timeframe: Timeframe,
        *,
        now: Timestamp,
    ) -> list[Bar]:
        """Translate a kline stream message into Bars (oldest first).

        Stream kline objects are ``{"t","o","h","l","c","v"}`` keyed
        dictionaries - a different shape from the REST arrays.
        """
        symbol = self._require_symbol(message)
        rows = message.get("data")
        if not isinstance(rows, list):
            raise DataError(
                "kline stream message has no data array",
                code="DAT-021",
                details={"symbol": symbol},
            )
        bars: list[Bar] = []
        for row in rows:
            if not isinstance(row, dict):
                raise DataError(
                    "kline stream row is not an object",
                    code="DAT-021",
                    details={"symbol": symbol},
                )
            open_time = self._parse_time(row.get("t"), symbol)
            bars.append(
                Bar(
                    exchange=EXCHANGE_ID,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    open=Price(self._parse_decimal(row.get("o"), "open", symbol)),
                    high=Price(self._parse_decimal(row.get("h"), "high", symbol)),
                    low=Price(self._parse_decimal(row.get("l"), "low", symbol)),
                    close=Price(self._parse_decimal(row.get("c"), "close", symbol)),
                    volume=Volume(self._parse_decimal(row.get("v"), "volume", symbol)),
                    is_closed=open_time.add_ms(timeframe.duration_ms).epoch_ms
                    <= now.epoch_ms,
                    quality=_FULL_QUALITY,
                )
            )
        return sorted(bars, key=lambda bar: bar.open_time.epoch_ms)

    def stream_trades_to_ticks(self, message: dict[str, JsonValue]) -> list[Tick]:
        """Translate a trade stream message into Ticks (oldest first).

        Stream semantics (Book VII): ``v`` is the globally unique trade
        id; ``m`` true means a buy, false means a sell.
        """
        symbol = self._require_symbol(message)
        rows = message.get("data")
        if not isinstance(rows, list):
            raise DataError(
                "trade stream message has no data array",
                code="DAT-022",
                details={"symbol": symbol},
            )
        ticks: list[Tick] = []
        for row in rows:
            if not isinstance(row, dict):
                raise DataError(
                    "trade stream row is not an object",
                    code="DAT-022",
                    details={"symbol": symbol},
                )
            trade_id = row.get("v")
            ticks.append(
                Tick(
                    exchange=EXCHANGE_ID,
                    symbol=symbol,
                    occurred_at=self._parse_time(row.get("t"), symbol),
                    price=Price(self._parse_decimal(row.get("p"), "price", symbol)),
                    quantity=Quantity(self._parse_decimal(row.get("q"), "quantity", symbol)),
                    aggressor=OrderSide.BUY if bool(row.get("m")) else OrderSide.SELL,
                    trade_id=str(trade_id) if trade_id is not None else None,
                )
            )
        return sorted(ticks, key=lambda tick: tick.occurred_at.epoch_ms)

    @staticmethod
    def _require_symbol(message: dict[str, JsonValue]) -> str:
        symbol = message.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise DataError("stream message has no symbol", code="DAT-023")
        return symbol

    @staticmethod
    def _parse_decimal(raw: JsonValue, field: str, symbol: str) -> Decimal:
        if not isinstance(raw, (str, int)) or isinstance(raw, bool):
            raise DataError(
                f"kline field {field} has unsupported type",
                code="DAT-015",
                details={"symbol": symbol, "field": field, "value": repr(raw)},
            )
        try:
            return Decimal(raw)
        except InvalidOperation as error:
            raise DataError(
                f"kline field {field} is not a valid number",
                code="DAT-016",
                details={"symbol": symbol, "field": field, "value": str(raw)},
            ) from error

    @staticmethod
    def _parse_time(raw: JsonValue, symbol: str) -> Timestamp:
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise DataError(
                "timestamp field must be integer epoch milliseconds",
                code="DAT-017",
                details={"symbol": symbol, "value": repr(raw)},
            )
        return Timestamp(epoch_ms=raw)
