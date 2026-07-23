"""Telegram Bot API client: transport, errors, token hygiene."""

import asyncio
import io
import json

import httpx
import pytest
from apex.core.exceptions import TelegramError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.telegram.client import TelegramBotClient

from tests.conftest import T0

_TOKEN = "123:secret-token"


def logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.telegram")


def client(handler: object) -> TelegramBotClient:
    return TelegramBotClient(
        token=_TOKEN,
        poll_timeout_s=1,
        logger=logger(),
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


class TestMethods:
    def test_get_updates_sends_offset_and_timeout(self) -> None:
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["body"] = json.loads(request.content.decode())
            return httpx.Response(
                200, json={"ok": True, "result": [{"update_id": 7}]}
            )

        async def scenario() -> None:
            bot = client(handler)
            await bot.open()
            updates = await bot.get_updates(offset=42)
            await bot.close()
            assert updates == [{"update_id": 7}]

        asyncio.run(scenario())
        assert seen["path"] == f"/bot{_TOKEN}/getUpdates"
        body = seen["body"]
        assert isinstance(body, dict)
        assert body["offset"] == 42
        assert body["timeout"] == 1

    def test_send_message_returns_message_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode())
            assert body["chat_id"] == 11
            assert "reply_markup" in body
            return httpx.Response(
                200, json={"ok": True, "result": {"message_id": 99}}
            )

        async def scenario() -> None:
            bot = client(handler)
            await bot.open()
            message_id = await bot.send_message(
                11, "hello", keyboard={"inline_keyboard": []}
            )
            await bot.close()
            assert message_id == 99

        asyncio.run(scenario())


class TestErrors:
    def test_api_failure_maps_to_tgm_016(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False, "description": "nope"})

        async def scenario() -> None:
            bot = client(handler)
            await bot.open()
            with pytest.raises(TelegramError) as excinfo:
                await bot.get_me()
            await bot.close()
            assert excinfo.value.code == "TGM-016"

        asyncio.run(scenario())

    def test_http_error_maps_to_tgm_014_without_token(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        async def scenario() -> None:
            bot = client(handler)
            await bot.open()
            with pytest.raises(TelegramError) as excinfo:
                await bot.get_me()
            await bot.close()
            assert excinfo.value.code == "TGM-014"
            assert "secret-token" not in str(excinfo.value)
            assert "secret-token" not in str(excinfo.value.details)

        asyncio.run(scenario())

    def test_unopened_client_rejected(self) -> None:
        async def scenario() -> None:
            bot = client(lambda request: httpx.Response(200, json={"ok": True}))
            with pytest.raises(TelegramError) as excinfo:
                await bot.get_me()
            assert excinfo.value.code == "TGM-012"

        asyncio.run(scenario())
