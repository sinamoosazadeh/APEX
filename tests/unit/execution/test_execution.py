"""Execution platform: config, translator, signed client, paper fills,
audit store, end-to-end paper service."""

import asyncio
import io
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from apex.core.context import ExecutionContext
from apex.core.enums import (
    LiquidityRole,
    OrderSide,
    OrderStatus,
    OrderType,
    RunMode,
    Timeframe,
)
from apex.core.exceptions import ConfigurationError, ExecutionError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.core.types import Price, QualityScore, Quantity, Volume
from apex.decision.store import DecisionRecord, SqliteDecisionRepository
from apex.domain.market import Bar
from apex.domain.order import Order
from apex.execution.config import ExecutionSettings, execution_settings
from apex.execution.paper import PaperExecutionEngine
from apex.execution.service import ExecutionService
from apex.execution.store import (
    ExecutionRecord,
    FillRecord,
    SqliteExecutionRepository,
)
from apex.execution.trading.client import ToobitTradingClient, TradingCredentials
from apex.execution.trading.translator import (
    client_order_id,
    contract_symbol,
    order_params,
    parse_status,
    parse_trades,
    unwrap,
)
from apex.portfolio.config import portfolio_settings
from apex.portfolio.engine import PortfolioEngine
from apex.portfolio.store import PositionRecord, SqlitePortfolioRepository

from tests.conftest import T0

H1_MS = Timeframe.H1.duration_ms

# Book VII SIGNED endpoint example. The doc's printed signature is
# copy-pasted across four different payloads (so it cannot be exact);
# the pinned value below is the doc's own algorithm run over its
# exact payload and secret:
#   echo -n "<payload>" | openssl dgst -sha256 -hmac "<secret>"
_SPEC_SECRET = "30lfjDT51iOG1kYZnDoLNynOyMdIcmQyO1XYfxzYOmQfx9tjiI98Pzio4uhZ0Uk2"
_SPEC_PAYLOAD = (
    "symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC"
    "&quantity=1&price=400&recvWindow=100000&timestamp=1668481902307"
)
_SPEC_SIGNATURE = "c51bc80daaf1608a3ab11bec7e3b35a41d351e0224f46b0326447c489d790034"


def logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.ERROR,
        log_format=LogFormat.CONSOLE,
        stream=io.StringIO(),
    )
    return factory.get("test.execution")


class _Bus:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def publish(self, event: object) -> None:
        self.events.append(event)


def make_bar(
    index: int, o: float, h: float, low: float, c: float, symbol: str = "BTCUSDT"
) -> Bar:
    return Bar(
        exchange="toobit",
        symbol=symbol,
        timeframe=Timeframe.H1,
        open_time=T0.add_ms(index * H1_MS),
        open=Price(Decimal(str(o))),
        high=Price(Decimal(str(h))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(c))),
        volume=Volume(Decimal(100)),
        is_closed=True,
        quality=QualityScore(1.0),
    )


def make_order(
    *,
    order_type: OrderType = OrderType.MARKET,
    limit: float | None = None,
    side: OrderSide = OrderSide.BUY,
) -> Order:
    return Order(
        created_at=T0,
        exchange="toobit",
        symbol="BTCUSDT",
        side=side,
        order_type=order_type,
        quantity=Quantity(Decimal(2)),
        limit_price=Price(Decimal(str(limit))) if limit is not None else None,
        client_order_id="apex-test-0001",
    )


class TestConfig:
    def test_defaults_parse(self) -> None:
        settings = execution_settings({})
        assert settings.recv_window_ms == 5_000
        assert settings.entry_order_type == "market"
        assert settings.contract_infix == "-SWAP-"

    def test_invalid_entry_type_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            execution_settings({"entry_order_type": "twap"})

    def test_invalid_patience_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            execution_settings({"paper_patience_bars": 0})


class TestTranslator:
    def test_contract_symbol_mapping(self) -> None:
        assert contract_symbol("BTCUSDT", "-SWAP-") == "BTC-SWAP-USDT"
        assert contract_symbol("ETHUSDT", "-SWAP-") == "ETH-SWAP-USDT"
        with pytest.raises(ExecutionError):
            contract_symbol("ETHBTC", "-SWAP-")

    def test_signature_matches_the_spec_vector(self) -> None:
        credentials = TradingCredentials(api_key="key", api_secret=_SPEC_SECRET)
        assert credentials.sign(_SPEC_PAYLOAD) == _SPEC_SIGNATURE

    def test_secret_never_leaks_in_repr(self) -> None:
        credentials = TradingCredentials(api_key="key", api_secret=_SPEC_SECRET)
        assert _SPEC_SECRET not in repr(credentials)

    def test_market_bracket_params(self) -> None:
        params = order_params(
            make_order(),
            contract="BTC-SWAP-USDT",
            stop_loss=Decimal("98.5"),
            take_profit=Decimal("107.25"),
        )
        assert params["symbol"] == "BTC-SWAP-USDT"
        assert params["side"] == "BUY" and params["positionSide"] == "LONG"
        assert params["type"] == "MARKET"
        assert "price" not in params and "timeInForce" not in params
        assert params["stopLoss"] == "98.5" and params["takeProfit"] == "107.25"
        assert params["slTriggerBy"] == "MARK_PRICE"

    def test_limit_params_carry_price_and_tif(self) -> None:
        params = order_params(
            make_order(order_type=OrderType.LIMIT, limit=99.5),
            contract="BTC-SWAP-USDT",
        )
        assert params["type"] == "LIMIT"
        assert params["price"] == "99.5"
        assert params["timeInForce"] == "GTC"

    def test_missing_client_id_rejected(self) -> None:
        order = Order(
            created_at=T0,
            exchange="toobit",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Quantity(Decimal(1)),
        )
        with pytest.raises(ExecutionError):
            order_params(order, contract="BTC-SWAP-USDT")

    def test_unwrap_raises_business_errors(self) -> None:
        assert unwrap({"code": 200, "data": {"x": 1}}, path="/p") == {"x": 1}
        with pytest.raises(ExecutionError):
            unwrap({"code": -1121, "msg": "Invalid symbol"}, path="/p")

    def test_parse_status_golden(self) -> None:
        from apex.core.serialization import JsonValue

        payload: JsonValue = {
            "orderId": "1289182123551455488",
            "status": "FILLED",
            "executedQty": "2",
            "avgPrice": "19010.5",
        }
        venue_id, status, executed, average = parse_status(payload, path="/p")
        assert venue_id == "1289182123551455488"
        assert status is OrderStatus.FILLED
        assert executed == Decimal(2)
        assert average == Decimal("19010.5")

    def test_parse_trades_filters_by_order(self) -> None:
        from apex.core.serialization import JsonValue

        order = make_order()
        payload: JsonValue = [
            {
                "time": "1668419000000", "id": "9876543210",
                "orderId": "111", "symbol": "BTC-SWAP-USDT",
                "price": "19000", "qty": "1.5", "commission": "0.01",
                "commissionAsset": "USDT", "isMaker": True,
            },
            {
                "time": "1668419000500", "id": "9876543211",
                "orderId": "222", "symbol": "BTC-SWAP-USDT",
                "price": "19001", "qty": "1", "commission": "0.02",
                "commissionAsset": "USDT", "isMaker": False,
            },
        ]
        fills = parse_trades(payload, order=order, venue_order_id="111", path="/p")
        assert len(fills) == 1
        fill = fills[0]
        assert fill.price.value == Decimal(19000)
        assert fill.quantity.value == Decimal("1.5")
        assert fill.fee.amount == Decimal("0.01")
        assert fill.liquidity_role is LiquidityRole.MAKER

    def test_client_order_id_is_deterministic(self) -> None:
        import uuid

        execution_id = uuid.UUID(int=7)
        assert client_order_id(execution_id) == client_order_id(execution_id)
        assert client_order_id(execution_id).startswith("apex-")


class TestTradingClient:
    def client(
        self, transport: httpx.AsyncBaseTransport | None = None
    ) -> ToobitTradingClient:
        return ToobitTradingClient(
            base_url="https://api.toobit.test",
            request_timeout_ms=2_000,
            recv_window_ms=5_000,
            max_retries=1,
            retry_backoff_ms=1,
            clock=ManualClock(T0),
            logger=logger(),
            credentials=TradingCredentials(api_key="k", api_secret=_SPEC_SECRET),
            transport=transport,
        )

    def test_order_key_is_exclusive(self) -> None:
        client = self.client()
        with pytest.raises(ExecutionError):
            client._order_key(None, None)
        with pytest.raises(ExecutionError):
            client._order_key("1", "2")
        assert client._order_key("1", None) == {"orderId": "1"}
        assert client._order_key(None, "c") == {"origClientOrderId": "c"}

    def test_signed_request_carries_header_and_signature(self) -> None:
        asyncio.run(self._signed_roundtrip())

    async def _signed_roundtrip(self) -> None:
        import hashlib
        import hmac as hmac_module
        from urllib.parse import parse_qsl

        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["header"] = request.headers.get("X-BB-APIKEY")
            body = dict(parse_qsl(request.content.decode()))
            seen["body"] = body
            return httpx.Response(200, json={"code": 200, "data": {"ok": True}})

        client = self.client(httpx.MockTransport(handler))
        await client.open()
        try:
            payload = await client.place_order({"symbol": "BTC-SWAP-USDT"})
        finally:
            await client.close()
        assert payload == {"code": 200, "data": {"ok": True}}
        assert seen["header"] == "k"
        body = seen["body"]
        assert isinstance(body, dict)
        signature = body.pop("signature")
        from urllib.parse import urlencode

        expected = hmac_module.new(
            _SPEC_SECRET.encode(), urlencode(body).encode(), hashlib.sha256
        ).hexdigest()
        assert signature == expected

    def test_retryable_errors_retry_then_succeed(self) -> None:
        asyncio.run(self._retry())

    async def _retry(self) -> None:
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(503, text="unavailable")
            return httpx.Response(200, json={"code": 200, "data": []})

        client = self.client(httpx.MockTransport(handler))
        await client.open()
        try:
            payload = await client.balance()
        finally:
            await client.close()
        assert calls["count"] == 2
        assert payload == {"code": 200, "data": []}

    def test_missing_credentials_fail_loudly(self) -> None:
        client = ToobitTradingClient(
            base_url="https://api.toobit.test",
            request_timeout_ms=2_000,
            recv_window_ms=5_000,
            max_retries=0,
            retry_backoff_ms=1,
            clock=ManualClock(T0),
            logger=logger(),
            credentials=None,
        )
        assert not client.can_trade
        with pytest.raises(ExecutionError):
            asyncio.run(self._use(client))

    async def _use(self, client: ToobitTradingClient) -> None:
        await client.open()
        try:
            await client.balance()
        finally:
            await client.close()


class TestPaperEngine:
    def settings(self) -> ExecutionSettings:
        return execution_settings(
            {"paper_slippage_bps": 2.0, "taker_fee_rate": 0.0006,
             "maker_fee_rate": 0.0002, "paper_patience_bars": 2}
        )

    def context(self) -> ExecutionContext:
        import uuid

        return ExecutionContext(
            execution_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            signal_id=None,
            exchange="toobit",
            symbol="BTCUSDT",
            requested_at=T0.add_ms(3 * H1_MS),  # bar 2 just closed
            timeframe=Timeframe.H1,
        )

    async def _engine(self, tmp_path: Path, bars: list[Bar]) -> PaperExecutionEngine:
        from apex.storage.bars import SqliteBarRepository

        store = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        await store.open()
        await store.upsert(bars)
        return PaperExecutionEngine(
            settings=self.settings(),
            bar_repository=store,
            clock=ManualClock(T0),
            logger=logger(),
        )

    def test_market_fills_next_open_with_slippage_and_fee(
        self, tmp_path: Path
    ) -> None:
        asyncio.run(self._market(tmp_path))

    async def _market(self, tmp_path: Path) -> None:
        bars = [make_bar(i, 100 + i, 101.5 + i, 99.5 + i, 101 + i) for i in range(6)]
        engine = await self._engine(tmp_path, bars)
        fills = (await engine.execute(make_order(), self.context())).unwrap()
        assert len(fills) == 1
        fill = fills[0]
        # Bar 3 opens at 103; +2 bps against the BUY.
        assert fill.price.value == Decimal("103.02060000")
        assert fill.quantity.value == Decimal(2)
        expected_fee = (fill.price.value * 2 * Decimal("0.0006")).quantize(
            Decimal("0.00000001")
        )
        assert fill.fee.amount == expected_fee
        assert fill.liquidity_role is LiquidityRole.TAKER

    def test_limit_fills_on_touch_with_maker_fee(self, tmp_path: Path) -> None:
        asyncio.run(self._limit(tmp_path))

    async def _limit(self, tmp_path: Path) -> None:
        bars = [make_bar(i, 100 + i, 101.5 + i, 99.5 + i, 101 + i) for i in range(6)]
        engine = await self._engine(tmp_path, bars)
        order = make_order(order_type=OrderType.LIMIT, limit=102.6)  # bar 3 low 102.5
        fills = (await engine.execute(order, self.context())).unwrap()
        assert len(fills) == 1
        assert fills[0].price.value == Decimal("102.60000000")
        assert fills[0].liquidity_role is LiquidityRole.MAKER

    def test_untouched_limit_expires_empty(self, tmp_path: Path) -> None:
        asyncio.run(self._expire(tmp_path))

    async def _expire(self, tmp_path: Path) -> None:
        bars = [make_bar(i, 100 + i, 101.5 + i, 99.5 + i, 101 + i) for i in range(6)]
        engine = await self._engine(tmp_path, bars)
        order = make_order(order_type=OrderType.LIMIT, limit=90.0)  # never touched
        fills = (await engine.execute(order, self.context())).unwrap()
        assert fills == ()

    def test_missing_timeframe_is_an_error(self, tmp_path: Path) -> None:
        asyncio.run(self._missing_timeframe(tmp_path))

    async def _missing_timeframe(self, tmp_path: Path) -> None:
        import uuid

        engine = await self._engine(tmp_path, [make_bar(0, 100, 101, 99, 100.5)])
        context = ExecutionContext(
            execution_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            signal_id=None,
            exchange="toobit",
            symbol="BTCUSDT",
            requested_at=T0,
        )
        result = await engine.execute(make_order(), context)
        assert not result.ok
        assert result.error is not None and result.error.code == "EXE-026"


class TestStore:
    def test_roundtrip(self, tmp_path: Path) -> None:
        asyncio.run(self._roundtrip(tmp_path))

    async def _roundtrip(self, tmp_path: Path) -> None:
        store = SqliteExecutionRepository(database_path=tmp_path / "executions.sqlite")
        await store.open()
        try:
            record = ExecutionRecord(
                execution_id="e1", portfolio_id="default", exchange="toobit",
                symbol="BTCUSDT", timeframe=Timeframe.H1, mode="paper",
                signal_bar_time=T0, direction="long", order_type="market",
                client_order_id="apex-1", requested_at=T0.add_ms(H1_MS),
                completed_at=T0.add_ms(H1_MS), status="filled",
                quantity=Decimal(2), decision_price=Decimal(102),
                fill_price=Decimal("103.02"), fees=Decimal("0.12"),
                slippage=Decimal("1.02"), stop=Decimal(100),
                target=Decimal(107), reasons=(),
            )
            await store.upsert_execution(record)
            await store.upsert_execution(record)  # idempotent
            stored = await store.get_executions("default")
            assert len(stored) == 1
            assert stored[0].fill_price == Decimal("103.02")
            fills = [
                FillRecord(
                    execution_id="e1", exchange_trade_id="t1",
                    price=Decimal("103.02"), quantity=Decimal(2),
                    fee=Decimal("0.12"), liquidity_role="taker",
                    executed_at=T0.add_ms(H1_MS),
                )
            ]
            assert await store.upsert_fills(fills) == 1
            stored_fills = await store.get_fills("e1")
            assert len(stored_fills) == 1
            assert stored_fills[0].price == Decimal("103.02")
        finally:
            await store.close()


def fired(index: int, symbol: str = "BTCUSDT") -> DecisionRecord:
    return DecisionRecord(
        exchange="toobit",
        symbol=symbol,
        timeframe=Timeframe.H1,
        bar_open_time=T0.add_ms(index * H1_MS),
        action="signal",
        direction="long",
        setup="Momentum Breakout",
        probability=0.85,
        uncertainty=0.2,
        expected_r=1.2,
        contributors=9,
        failed_gates=(),
        entry=103.0,
        stop=99.0,
        targets=(105.0, 107.0, 111.0),
        computed_at=T0,
    )


class TestServicePaper:
    async def _service(
        self, tmp_path: Path, *, occupied: bool = False
    ) -> tuple[ExecutionService, SqlitePortfolioRepository, SqliteExecutionRepository]:
        from apex.execution.engine import LiveExecutionEngine
        from apex.storage.bars import SqliteBarRepository

        bars_store = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
        await bars_store.open()
        await bars_store.upsert(
            [make_bar(i, 100 + i, 101.5 + i, 99.5 + i, 101 + i) for i in range(6)]
        )
        decisions = SqliteDecisionRepository(
            database_path=tmp_path / "decisions.sqlite"
        )
        await decisions.open()
        await decisions.upsert([fired(2)])
        portfolio_store = SqlitePortfolioRepository(
            database_path=tmp_path / "portfolio.sqlite"
        )
        await portfolio_store.open()
        if occupied:
            await portfolio_store.upsert_positions(
                [
                    PositionRecord(
                        portfolio_id="default", exchange="toobit", symbol="BTCUSDT",
                        timeframe=Timeframe.H1, entry_bar_time=T0,
                        position_id="p0", lineage_id="l0", direction="long",
                        quantity=Decimal(1), entry=Decimal(100), stop=Decimal(98),
                        target=Decimal(106), risk_amount=Decimal(2),
                        opened_at=T0, status="open", closed_at=None,
                        exit_price=None, realized_pnl=None, realized_r=None,
                        close_reason=None,
                    )
                ]
            )
            # A snapshot so the service sees the occupied portfolio state.
            from apex.portfolio.store import SnapshotRecord

            await portfolio_store.upsert_snapshots(
                [
                    SnapshotRecord(
                        portfolio_id="default", as_of=T0.add_ms(H1_MS),
                        equity=Decimal(10_000), cash=Decimal(10_000),
                        gross_exposure=Decimal(100), unrealized_pnl=Decimal(0),
                        realized_pnl=Decimal(0), drawdown=0.0, open_positions=1,
                    )
                ]
            )
        executions = SqliteExecutionRepository(
            database_path=tmp_path / "executions.sqlite"
        )
        await executions.open()
        settings = portfolio_settings(
            {"account": {"initial_capital": "10000", "risk_fraction": 0.01}}
        )
        clock = ManualClock(T0.add_ms(3 * H1_MS))  # signal bar just closed
        execution_config = execution_settings({"paper_patience_bars": 2})
        paper = PaperExecutionEngine(
            settings=execution_config,
            bar_repository=bars_store,
            clock=clock,
            logger=logger(),
        )
        live = LiveExecutionEngine(
            client=ToobitTradingClient(
                base_url="https://api.toobit.test",
                request_timeout_ms=1_000,
                recv_window_ms=5_000,
                max_retries=0,
                retry_backoff_ms=1,
                clock=clock,
                logger=logger(),
                credentials=None,
            ),
            settings=execution_config,
            clock=clock,
            logger=logger(),
        )
        service = ExecutionService(
            exchange_id="toobit",
            settings=execution_config,
            portfolio_settings=settings,
            run_mode=RunMode.BACKTEST,
            decision_repository=decisions,
            portfolio_repository=portfolio_store,
            portfolio_engine=PortfolioEngine(settings=settings, clock=clock),
            paper_engine=paper,
            live_engine=live,
            execution_repository=executions,
            bus=_Bus(),  # type: ignore[arg-type]
            clock=clock,
            logger=logger(),
        )
        return service, portfolio_store, executions

    def test_paper_execution_end_to_end(self, tmp_path: Path) -> None:
        asyncio.run(self._end_to_end(tmp_path))

    async def _end_to_end(self, tmp_path: Path) -> None:
        service, portfolio_store, executions = await self._service(tmp_path)
        summary = (
            await service.execute_latest_signal(
                "BTCUSDT", Timeframe.H1,
                start=T0, end=T0.add_ms(6 * H1_MS),
            )
        ).unwrap()
        assert summary.status == "filled"
        assert summary.mode == "paper"
        assert summary.position_opened
        # Fill at bar 3 open (103) + 2 bps slippage; decision price 103.
        assert summary.fill_price == "103.02060000"
        assert summary.slippage == "0.02060000"
        positions = await portfolio_store.get_positions("default", status="open")
        assert len(positions) == 1
        assert positions[0].entry == Decimal("103.02060000")
        stored = await executions.get_executions("default")
        assert len(stored) == 1 and stored[0].status == "filled"

    def test_occupied_portfolio_rejects(self, tmp_path: Path) -> None:
        asyncio.run(self._occupied(tmp_path))

    async def _occupied(self, tmp_path: Path) -> None:
        service, _, executions = await self._service(tmp_path, occupied=True)
        summary = (
            await service.execute_latest_signal(
                "BTCUSDT", Timeframe.H1,
                start=T0, end=T0.add_ms(6 * H1_MS),
            )
        ).unwrap()
        assert summary.status == "rejected"
        assert "portfolio_halted" in summary.reasons
        stored = await executions.get_executions("default", status="rejected")
        assert len(stored) == 1

    def test_no_signal_is_a_coded_failure(self, tmp_path: Path) -> None:
        asyncio.run(self._no_signal(tmp_path))

    async def _no_signal(self, tmp_path: Path) -> None:
        service, _, _ = await self._service(tmp_path)
        result = await service.execute_latest_signal(
            "ETHUSDT", Timeframe.H1, start=T0, end=T0.add_ms(6 * H1_MS)
        )
        assert not result.ok
        assert result.error is not None and result.error.code == "EXE-030"
