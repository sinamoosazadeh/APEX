"""Telegram Bot API client (Book IV transport layer).

A minimal, dependency-light client over httpx: long-poll getUpdates,
sendMessage, editMessageText and answerCallbackQuery - everything the
console needs, nothing more. The transport is injectable for tests
(the platform's standard seam); the bot token never appears in logs
or error details - errors carry the API method name only.
"""

import json
from typing import Final

import httpx

from apex.core.exceptions import TelegramError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue

_BASE_URL: Final[str] = "https://api.telegram.org"
# Long polls hold the connection up to poll_timeout_s; the transport
# timeout must comfortably exceed it.
_TIMEOUT_MARGIN_S: Final[float] = 10.0


class TelegramBotClient:
    """Async client for the handful of Bot API methods the console uses."""

    def __init__(
        self,
        *,
        token: str,
        poll_timeout_s: int,
        logger: StructuredLogger,
        base_url: str = _BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._poll_timeout_s = poll_timeout_s
        self._logger = logger
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        """Create the HTTP session (no network contact)."""
        if self._client is not None:
            raise TelegramError("telegram client is already open", code="TGM-010")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._poll_timeout_s + _TIMEOUT_MARGIN_S,
            transport=self._transport,
        )

    async def close(self) -> None:
        """Close the HTTP session; idempotent."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- Methods -----------------------------------------------------------------

    async def get_me(self) -> dict[str, JsonValue]:
        """getMe - identity check."""
        result = await self._call("getMe", {})
        return result if isinstance(result, dict) else {}

    async def get_updates(self, *, offset: int) -> list[dict[str, JsonValue]]:
        """getUpdates long poll from ``offset``."""
        result = await self._call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": self._poll_timeout_s,
                "allowed_updates": ["message", "callback_query"],
            },
        )
        if not isinstance(result, list):
            return []
        return [item for item in result if isinstance(item, dict)]

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        keyboard: JsonValue | None = None,
    ) -> int:
        """sendMessage; returns the new message id."""
        params: dict[str, JsonValue] = {"chat_id": chat_id, "text": text}
        if keyboard is not None:
            params["reply_markup"] = json.dumps(keyboard)
        result = await self._call("sendMessage", params)
        if isinstance(result, dict):
            message_id = result.get("message_id")
            if isinstance(message_id, int):
                return message_id
        raise TelegramError("sendMessage returned no message id", code="TGM-011")

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        *,
        keyboard: JsonValue | None = None,
    ) -> None:
        """editMessageText - the navigation edit-in-place policy."""
        params: dict[str, JsonValue] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if keyboard is not None:
            params["reply_markup"] = json.dumps(keyboard)
        await self._call("editMessageText", params)

    async def answer_callback(
        self, callback_query_id: str, *, text: str | None = None
    ) -> None:
        """answerCallbackQuery - every callback is acknowledged."""
        params: dict[str, JsonValue] = {"callback_query_id": callback_query_id}
        if text is not None:
            params["text"] = text
        await self._call("answerCallbackQuery", params)

    # --- Transport -----------------------------------------------------------------

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise TelegramError("telegram client is not open", code="TGM-012")
        return self._client

    async def _call(self, method: str, params: dict[str, JsonValue]) -> JsonValue:
        """POST one Bot API method; errors never carry the token."""
        client = self._require_client()
        try:
            response = await client.post(f"/bot{self._token}/{method}", json=params)
        except httpx.HTTPError as error:
            raise TelegramError(
                "telegram transport failure",
                code="TGM-013",
                details={"method": method, "reason": type(error).__name__},
            ) from error
        if response.status_code != 200:
            raise TelegramError(
                "telegram API rejected the request",
                code="TGM-014",
                details={"method": method, "status": response.status_code},
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise TelegramError(
                "telegram API returned invalid JSON",
                code="TGM-015",
                details={"method": method},
            ) from error
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise TelegramError(
                "telegram API reported failure",
                code="TGM-016",
                details={"method": method},
            )
        result: JsonValue = payload.get("result")
        return result
