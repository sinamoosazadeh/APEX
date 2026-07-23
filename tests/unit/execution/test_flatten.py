"""Emergency flattening: ledger close at the mark, venue reduce-only."""

import asyncio
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from apex.core.enums import Timeframe
from apex.core.identity import IdProvider
from apex.core.serialization import JsonValue
from apex.core.time.clock import ManualClock
from apex.execution.flatten import flatten_positions
from apex.execution.trading.client import ToobitTradingClient, TradingCredentials
from apex.execution.trading.translator import close_params
from apex.portfolio.store import PositionRecord, SqlitePortfolioRepository
from apex.storage.bars import SqliteBarRepository

from tests.conftest import T0, make_bar
from tests.unit.monitoring.support import logger

H1_MS = Timeframe.H1.duration_ms


class RecordingClient(ToobitTradingClient):
    """Records orders instead of reaching a venue."""

    def __init__(self, *, trade: bool) -> None:
        super().__init__(
            base_url="https://venue.invalid",
            request_timeout_ms=1_000,
            recv_window_ms=1_000,
            max_retries=0,
            retry_backoff_ms=1,
            clock=ManualClock(T0),
            logger=logger(),
            credentials=(
                TradingCredentials(api_key="k", api_secret="s") if trade else None
            ),
        )
        self.orders: list[dict[str, str]] = []

    async def place_order(self, params: Mapping[str, str]) -> JsonValue:
        self.orders.append(dict(params))
        return {"orderId": "1"}


def open_position() -> PositionRecord:
    return PositionRecord(
        portfolio_id="default",
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        entry_bar_time=T0,
        position_id="flat-1",
        lineage_id="flat-1",
        direction="long",
        quantity=Decimal("2"),
        entry=Decimal("100"),
        stop=Decimal("95"),
        target=Decimal("115"),
        risk_amount=Decimal("10"),
        opened_at=T0,
        status="open",
        closed_at=None,
        exit_price=None,
        realized_pnl=None,
        realized_r=None,
        close_reason=None,
    )


async def _flatten(
    tmp_path: Path, client: RecordingClient
) -> tuple[int, PositionRecord]:
    portfolio = SqlitePortfolioRepository(database_path=tmp_path / "p.sqlite")
    bars = SqliteBarRepository(database_path=tmp_path / "bars.sqlite")
    await portfolio.open()
    await bars.open()
    await portfolio.upsert_positions([open_position()])
    await bars.upsert(
        [
            make_bar(open_time=T0, close="104"),
            make_bar(open_time=T0.add_ms(H1_MS), close="108"),
        ]
    )
    closed = await flatten_positions(
        portfolio=portfolio,
        portfolio_id="default",
        bars=bars,
        exchange_id="toobit",
        client=client,
        contract_infix="-SWAP-",
        fee_rate=Decimal("0.0005"),
        ids=IdProvider(seed=7),
        clock=ManualClock(T0.add_ms(2 * H1_MS)),
        logger=logger(),
    )
    records = await portfolio.get_positions("default")
    await portfolio.close()
    await bars.close()
    return closed, records[0]


class TestFlatten:
    def test_ledger_close_at_the_latest_confirmed_mark(
        self, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            closed, record = await _flatten(tmp_path, RecordingClient(trade=False))
            assert closed == 1
            assert record.status == "closed"
            assert record.close_reason == "flattened"
            assert record.exit_price == Decimal("108")
            # gross (108-100)*2 = 16; fees 0.0005*(100+108)*2 = 0.208
            assert record.realized_pnl == Decimal("16") - Decimal("0.208")
            assert record.realized_r is not None
            assert abs(record.realized_r - 1.6) < 1e-9

        asyncio.run(scenario())

    def test_live_sends_reduce_only_market_closes(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            client = RecordingClient(trade=True)
            closed, record = await _flatten(tmp_path, client)
            assert closed == 1 and record.status == "closed"
            assert len(client.orders) == 1
            order = client.orders[0]
            assert order["symbol"] == "BTC-SWAP-USDT"
            assert order["side"] == "SELL"
            assert order["positionSide"] == "LONG"
            assert order["reduceOnly"] == "true"
            assert order["type"] == "MARKET"

        asyncio.run(scenario())

    def test_close_params_mirror_short_positions(self) -> None:
        params = close_params(
            contract="ETH-SWAP-USDT",
            direction="short",
            quantity=Decimal("1.5"),
            client_order_id="apex-x",
        )
        assert params["side"] == "BUY"
        assert params["positionSide"] == "SHORT"
        assert params["reduceOnly"] == "true"
