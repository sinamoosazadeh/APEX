"""Console end to end: commands, callbacks, confirm flow, notifications.

Boots the real kernel (all platform services over tmp stores) and
drives the console through a scripted Bot API transport - zero
network, real routing, real kill-switch effects.
"""

import asyncio
import io
import json
from pathlib import Path

import httpx
from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IEventBus
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.kernel.kernel import Kernel
from apex.monitoring.events import MonitoringEvent, monitoring_event
from apex.monitoring.records import KillSwitchLevel
from apex.monitoring.service import MonitoringService
from apex.portfolio.config import portfolio_settings
from apex.portfolio.store import SqlitePortfolioRepository
from apex.research.service import ResearchService
from apex.telegram.client import TelegramBotClient
from apex.telegram.config import TelegramSettings
from apex.telegram.credentials import TelegramCredentials
from apex.telegram.service import TelegramConsoleService

from tests.conftest import T0

_ADMIN = 1001
_STRANGER = 4004


def logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.console")


class _BotApi:
    """A scripted Bot API: queued updates, recorded outbound calls."""

    def __init__(self, clock: ManualClock) -> None:
        self._clock = clock
        self.pending: list[dict[str, object]] = []
        self.sent: list[dict[str, object]] = []
        self.edited: list[dict[str, object]] = []
        self._next_update_id = 1

    def queue_message(self, chat_id: int, text: str) -> None:
        self.pending.append(
            {
                "update_id": self._next_update_id,
                "message": {"chat": {"id": chat_id}, "text": text},
            }
        )
        self._next_update_id += 1

    def queue_callback(self, chat_id: int, data: str) -> None:
        self.pending.append(
            {
                "update_id": self._next_update_id,
                "callback_query": {
                    "id": f"cb-{self._next_update_id}",
                    "data": data,
                    "message": {"chat": {"id": chat_id}, "message_id": 500},
                },
            }
        )
        self._next_update_id += 1

    async def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[1]
        if method == "getMe":
            return httpx.Response(
                200, json={"ok": True, "result": {"username": "apex_test_bot"}}
            )
        if method == "getUpdates":
            # A real long poll suspends; the scripted one must too, or
            # the console loop starves every other task. Each poll also
            # advances the deterministic clock so bounded sessions end.
            await asyncio.sleep(0.001)
            self._clock.advance_ms(400)
            batch, self.pending = self.pending, []
            return httpx.Response(200, json={"ok": True, "result": batch})
        body = json.loads(request.content.decode())
        if method == "sendMessage":
            self.sent.append(body)
            return httpx.Response(
                200, json={"ok": True, "result": {"message_id": len(self.sent)}}
            )
        if method == "editMessageText":
            self.edited.append(body)
            self._maybe_confirm(body)
            return httpx.Response(200, json={"ok": True, "result": True})
        return httpx.Response(200, json={"ok": True, "result": True})

    def _maybe_confirm(self, body: dict[str, object]) -> None:
        """Auto-press Confirm when a confirmation gate renders."""
        markup = body.get("reply_markup")
        if not isinstance(markup, str) or "confirm." not in markup:
            return
        keyboard = json.loads(markup)
        for row in keyboard["inline_keyboard"]:
            for button in row:
                data = str(button["callback_data"])
                if data.startswith("confirm."):
                    chat = body.get("chat_id")
                    assert isinstance(chat, int)
                    self.queue_callback(chat, data)
                    return


def console_over(
    kernel: Kernel, api: _BotApi, clock: ManualClock
) -> TelegramConsoleService:
    credentials = TelegramCredentials(
        token="123:test", admin_chat_ids=frozenset({_ADMIN})
    )
    client = TelegramBotClient(
        token="123:test",
        poll_timeout_s=1,
        logger=logger(),
        transport=httpx.MockTransport(api.handler),
    )
    config = kernel.container.resolve(AppConfig)
    return TelegramConsoleService(
        settings=TelegramSettings(),
        credentials=credentials,
        client=client,
        monitoring=kernel.container.resolve(MonitoringService),
        research=kernel.container.resolve(ResearchService),
        portfolio_repository=kernel.container.resolve(SqlitePortfolioRepository),
        portfolio_id=portfolio_settings(config.section("portfolio")).portfolio_id,
        series=(("BTCUSDT", config.market.timeframes[0]),),
        bus=kernel.container.resolve(IEventBus),  # type: ignore[type-abstract]
        clock=clock,
        logger=logger(),
    )


class TestConsole:
    def test_commands_callbacks_and_confirm_flow(self, config_dir: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            kernel = Kernel(config_dir=config_dir, clock=clock)
            await kernel.boot()
            try:
                api = _BotApi(clock)
                console = console_over(kernel, api, clock)
                api.queue_message(_ADMIN, "/status")
                api.queue_message(_STRANGER, "/status")
                api.queue_callback(_ADMIN, "menu.portfolio")
                api.queue_callback(_ADMIN, "emergency.pause")
                stats = await console.run(seconds=5)
                assert stats.commands == 1  # denied commands never count
                assert stats.denied == 1
                assert stats.callbacks >= 3  # menu + pause + auto-confirm
                assert stats.notifications >= 1  # kill-switch change pushed
                status_reply = api.sent[0]
                assert "Status" in str(status_reply["text"])
                denied_reply = api.sent[1]
                assert "not authorized" in str(denied_reply["text"])
                edits = [str(edit["text"]) for edit in api.edited]
                assert any("Portfolio" in text for text in edits)
                assert any("Please confirm." in text for text in edits)
                assert any("Completed" in text for text in edits)
                monitoring = kernel.container.resolve(MonitoringService)
                level = await monitoring.kill_switch.level()
                assert level is KillSwitchLevel.PAUSED
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_alert_events_push_notifications(self, config_dir: Path) -> None:
        async def scenario() -> None:
            clock = ManualClock(T0)
            kernel = Kernel(config_dir=config_dir, clock=clock)
            await kernel.boot()
            try:
                api = _BotApi(clock)
                console = console_over(kernel, api, clock)
                bus = kernel.container.resolve(IEventBus)  # type: ignore[type-abstract]
                task = asyncio.create_task(console.run(seconds=0))
                await asyncio.sleep(0.05)
                await bus.publish(
                    monitoring_event(
                        MonitoringEvent.ALERT_RAISED,
                        occurred_at=clock.now(),
                        source="tests",
                        payload={
                            "severity": "emergency",
                            "category": "portfolio",
                            "message": "drawdown critical",
                            "dedup_key": "portfolio.drawdown_critical",
                        },
                    )
                )
                await bus.publish(
                    monitoring_event(
                        MonitoringEvent.ALERT_RAISED,
                        occurred_at=clock.now(),
                        source="tests",
                        payload={
                            "severity": "low",
                            "category": "system",
                            "message": "quiet",
                            "dedup_key": "system.quiet",
                        },
                    )
                )
                console.request_stop()
                stats = await task
                assert stats.notifications == 1  # low severity filtered
                pushed = [str(message["text"]) for message in api.sent]
                assert any("drawdown critical" in text for text in pushed)
                assert not any("quiet" in text for text in pushed)
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())
