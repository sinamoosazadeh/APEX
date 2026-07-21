"""Toobit REST client (Book VII).

Thin, typed transport layer for Toobit's public quote API. Knows HTTP,
retries and Toobit's error envelope - and nothing about the domain.
Translation into domain contracts is the translator's job (the
anti-corruption layer, Book II 5.37).

The HTTP transport is injectable, so unit tests run against a mock
transport with zero network access (Constitution 3.27).
"""

import asyncio
from typing import Final

import httpx

from apex.core.exceptions import DataError, MarketError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue

KLINES_PATH: Final[str] = "/quote/v1/klines"
TRADES_PATH: Final[str] = "/quote/v1/trades"

# Toobit hard limits (Book VII).
MAX_KLINE_LIMIT: Final[int] = 1000
MAX_TRADES_LIMIT: Final[int] = 60

_HTTP_OK: Final[int] = 200
_HTTP_TOO_MANY_REQUESTS: Final[int] = 429
_HTTP_IP_BAN: Final[int] = 418
_HTTP_SERVER_ERROR_FLOOR: Final[int] = 500


class ToobitRestClient:
    """Async client for Toobit public market data endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        request_timeout_ms: int,
        max_retries: int,
        retry_backoff_ms: int,
        logger: StructuredLogger,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_ms = request_timeout_ms
        self._max_retries = max_retries
        self._retry_backoff_ms = retry_backoff_ms
        self._logger = logger
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        """Create the HTTP session."""
        if self._client is not None:
            raise MarketError("client is already open", code="MKT-001")
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

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_ms: int,
        end_ms: int,
        limit: int,
    ) -> list[list[JsonValue]]:
        """Fetch raw klines with open time in [start_ms, end_ms].

        Book VII: without explicit start/end Toobit returns only the
        latest kline, so both bounds are always sent.
        """
        if not 1 <= limit <= MAX_KLINE_LIMIT:
            raise MarketError(
                f"kline limit must be within [1, {MAX_KLINE_LIMIT}]",
                code="MKT-002",
                details={"limit": limit},
            )
        payload = await self._get(
            KLINES_PATH,
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": str(start_ms),
                "endTime": str(end_ms),
                "limit": str(limit),
            },
        )
        if not isinstance(payload, list):
            raise DataError(
                "klines response is not a list",
                code="DAT-010",
                details={"symbol": symbol, "type": type(payload).__name__},
            )
        rows: list[list[JsonValue]] = []
        for item in payload:
            if not isinstance(item, list):
                raise DataError(
                    "klines response contains a non-array row",
                    code="DAT-010",
                    details={"symbol": symbol, "row_type": type(item).__name__},
                )
            rows.append(item)
        return rows

    async def get_trades(self, symbol: str, *, limit: int) -> list[dict[str, JsonValue]]:
        """Fetch recent public trades (newest window Toobit provides)."""
        if not 1 <= limit <= MAX_TRADES_LIMIT:
            raise MarketError(
                f"trades limit must be within [1, {MAX_TRADES_LIMIT}]",
                code="MKT-003",
                details={"limit": limit},
            )
        payload = await self._get(TRADES_PATH, {"symbol": symbol, "limit": str(limit)})
        if not isinstance(payload, list):
            raise DataError(
                "trades response is not a list of objects",
                code="DAT-011",
                details={"symbol": symbol},
            )
        trades: list[dict[str, JsonValue]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise DataError(
                    "trades response is not a list of objects",
                    code="DAT-011",
                    details={"symbol": symbol, "row_type": type(item).__name__},
                )
            trades.append(item)
        return trades

    # --- Transport ---------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, str]) -> JsonValue:
        client = self._require_client()
        last_error: MarketError | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(self._retry_backoff_ms * attempt / 1000)
            try:
                response = await client.get(path, params=params)
            except httpx.HTTPError as error:
                last_error = MarketError(
                    "transport failure calling Toobit",
                    code="MKT-004",
                    details={"path": path, "reason": str(error), "attempt": attempt},
                )
                self._logger.failure("toobit_transport_error", last_error)
                continue
            outcome = self._classify(response, path, attempt)
            if isinstance(outcome, MarketError):
                last_error = outcome
                continue
            return outcome
        assert last_error is not None
        raise last_error

    def _classify(
        self,
        response: httpx.Response,
        path: str,
        attempt: int,
    ) -> JsonValue | MarketError:
        """Map a response to payload, retryable error, or raise fatal."""
        if response.status_code in (_HTTP_TOO_MANY_REQUESTS, _HTTP_IP_BAN):
            error = MarketError(
                "Toobit rate limit hit",
                code="MKT-005",
                details={"path": path, "status": response.status_code, "attempt": attempt},
            )
            self._logger.failure("toobit_rate_limited", error)
            return error
        if response.status_code >= _HTTP_SERVER_ERROR_FLOOR:
            error = MarketError(
                "Toobit server error",
                code="MKT-006",
                details={"path": path, "status": response.status_code, "attempt": attempt},
            )
            self._logger.failure("toobit_server_error", error)
            return error
        if response.status_code != _HTTP_OK:
            raise MarketError(
                "Toobit request rejected",
                code="MKT-007",
                details={"path": path, "status": response.status_code},
            )
        try:
            payload: JsonValue = response.json()
        except ValueError as error:
            raise DataError(
                "Toobit response is not valid JSON",
                code="DAT-012",
                details={"path": path, "reason": str(error)},
            ) from error
        if isinstance(payload, dict) and "code" in payload and "msg" in payload:
            raise MarketError(
                "Toobit API error",
                code="MKT-008",
                details={
                    "path": path,
                    "api_code": str(payload.get("code")),
                    "api_message": str(payload.get("msg")),
                },
            )
        return payload

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise MarketError("client is not open", code="MKT-009")
        return self._client
