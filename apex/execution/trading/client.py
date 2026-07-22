"""Toobit signed trading client (Book VII, API v2 futures).

Every trading request is signed per Book VII: the request parameters
(including ``timestamp`` and ``recvWindow``) urlencode in insertion
order, HMAC-SHA256 under the API secret produces ``signature``, and
the API key travels in the ``X-BB-APIKEY`` header. POST bodies are
form-encoded exactly like the signed payload.

Credentials come from the environment (``TOOBIT_API_KEY`` /
``TOOBIT_API_SECRET``) until the secrets platform lands (Phase 13) -
they are never logged, never persisted and never appear in errors.
The transport is injectable for tests; timestamps come from the
injected Clock (Constitution: no ambient time).
"""

import asyncio
import hashlib
import hmac
import os
from collections.abc import Mapping
from typing import Final
from urllib.parse import urlencode

import httpx

from apex.core.exceptions import ExecutionError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import Clock

ORDER_PATH: Final[str] = "/api/v2/futures/order"
OPEN_ORDERS_PATH: Final[str] = "/api/v2/futures/open-orders"
USER_TRADES_PATH: Final[str] = "/api/v2/futures/user-trades"
BALANCE_PATH: Final[str] = "/api/v1/futures/balance"

_KEY_ENV: Final[str] = "TOOBIT_API_KEY"
_SECRET_ENV: Final[str] = "TOOBIT_API_SECRET"
_HEADER: Final[str] = "X-BB-APIKEY"


class TradingCredentials:
    """API key material; the secret never leaves this object."""

    __slots__ = ("_api_key", "_api_secret")

    def __init__(self, *, api_key: str, api_secret: str) -> None:
        if not api_key or not api_secret:
            raise ExecutionError("empty trading credentials", code="EXE-010")
        self._api_key = api_key
        self._api_secret = api_secret

    @classmethod
    def from_environment(cls) -> "TradingCredentials | None":
        """Read the env credentials; None when trading is unavailable."""
        api_key = os.environ.get(_KEY_ENV, "")
        api_secret = os.environ.get(_SECRET_ENV, "")
        if not api_key or not api_secret:
            return None
        return cls(api_key=api_key, api_secret=api_secret)

    @property
    def api_key(self) -> str:
        """The public API key (header value)."""
        return self._api_key

    def sign(self, payload: str) -> str:
        """HMAC-SHA256 signature of the urlencoded payload."""
        return hmac.new(
            self._api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    def __repr__(self) -> str:
        return "TradingCredentials(api_key=***, api_secret=***)"


class ToobitTradingClient:
    """Async client for the Toobit signed futures trading endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        request_timeout_ms: int,
        recv_window_ms: int,
        max_retries: int,
        retry_backoff_ms: int,
        clock: Clock,
        logger: StructuredLogger,
        credentials: TradingCredentials | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_ms = request_timeout_ms
        self._recv_window_ms = recv_window_ms
        self._max_retries = max_retries
        self._retry_backoff_ms = retry_backoff_ms
        self._clock = clock
        self._logger = logger
        self._credentials = credentials
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def can_trade(self) -> bool:
        """Whether credentials are present."""
        return self._credentials is not None

    async def open(self) -> None:
        """Create the HTTP session."""
        if self._client is not None:
            raise ExecutionError("trading client is already open", code="EXE-011")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_ms / 1000,
            transport=self._transport,
        )

    async def close(self) -> None:
        """Close the HTTP session; idempotent."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- Endpoints ---------------------------------------------------------------

    async def place_order(self, params: Mapping[str, str]) -> JsonValue:
        """POST /api/v2/futures/order."""
        return await self._signed("POST", ORDER_PATH, dict(params))

    async def query_order(
        self, *, order_id: str | None = None, client_order_id: str | None = None
    ) -> JsonValue:
        """GET /api/v2/futures/order by venue or client id."""
        return await self._signed("GET", ORDER_PATH, self._order_key(order_id, client_order_id))

    async def cancel_order(
        self, *, order_id: str | None = None, client_order_id: str | None = None
    ) -> JsonValue:
        """DELETE /api/v2/futures/order by venue or client id."""
        return await self._signed(
            "DELETE", ORDER_PATH, self._order_key(order_id, client_order_id)
        )

    async def open_orders(self, symbol: str) -> JsonValue:
        """GET /api/v2/futures/open-orders for one contract."""
        return await self._signed("GET", OPEN_ORDERS_PATH, {"symbol": symbol})

    async def user_trades(self, symbol: str, *, limit: int = 100) -> JsonValue:
        """GET /api/v2/futures/user-trades for one contract."""
        return await self._signed(
            "GET", USER_TRADES_PATH, {"symbol": symbol, "limit": str(limit)}
        )

    async def balance(self) -> JsonValue:
        """GET /api/v1/futures/balance."""
        return await self._signed("GET", BALANCE_PATH, {})

    def _order_key(
        self, order_id: str | None, client_order_id: str | None
    ) -> dict[str, str]:
        if (order_id is None) == (client_order_id is None):
            raise ExecutionError(
                "pass exactly one of order_id / client_order_id",
                code="EXE-012",
            )
        if order_id is not None:
            return {"orderId": order_id}
        assert client_order_id is not None
        return {"origClientOrderId": client_order_id}

    # --- Signed transport ----------------------------------------------------------

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise ExecutionError("trading client is not open", code="EXE-013")
        return self._client

    def _require_credentials(self) -> TradingCredentials:
        if self._credentials is None:
            raise ExecutionError(
                "trading credentials are not configured "
                f"(set {_KEY_ENV} and {_SECRET_ENV})",
                code="EXE-014",
            )
        return self._credentials

    async def _signed(
        self, method: str, path: str, params: dict[str, str]
    ) -> JsonValue:
        client = self._require_client()
        credentials = self._require_credentials()
        last_error: ExecutionError | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(self._retry_backoff_ms * attempt / 1000)
            signed = dict(params)
            signed["timestamp"] = str(self._clock.now().epoch_ms)
            signed["recvWindow"] = str(self._recv_window_ms)
            payload = urlencode(signed)
            signed["signature"] = credentials.sign(payload)
            try:
                response = await self._send(client, method, path, signed, credentials)
            except httpx.HTTPError as error:
                last_error = ExecutionError(
                    "transport failure calling Toobit trading API",
                    code="EXE-015",
                    details={"path": path, "reason": str(error), "attempt": attempt},
                )
                self._logger.failure("toobit_trading_transport_error", last_error)
                continue
            outcome = self._classify(response, path, attempt)
            if isinstance(outcome, ExecutionError):
                last_error = outcome
                continue
            return outcome
        assert last_error is not None
        raise last_error

    async def _send(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        signed: dict[str, str],
        credentials: TradingCredentials,
    ) -> httpx.Response:
        headers = {_HEADER: credentials.api_key}
        if method == "POST":
            return await client.post(path, data=signed, headers=headers)
        if method == "DELETE":
            return await client.delete(path, params=signed, headers=headers)
        return await client.get(path, params=signed, headers=headers)

    def _classify(
        self, response: httpx.Response, path: str, attempt: int
    ) -> JsonValue | ExecutionError:
        retryable = response.status_code in (429, 500, 502, 503, 504)
        if response.status_code != 200:
            error = ExecutionError(
                "Toobit trading API rejected the request",
                code="EXE-016",
                details={
                    "path": path,
                    "status": response.status_code,
                    "body": response.text[:300],
                    "attempt": attempt,
                },
            )
            if retryable:
                self._logger.failure("toobit_trading_retryable_error", error)
                return error
            raise error
        try:
            payload: JsonValue = response.json()
        except ValueError as error:
            raise ExecutionError(
                "Toobit trading API returned invalid JSON",
                code="EXE-017",
                details={"path": path, "reason": str(error)},
            ) from error
        return payload
