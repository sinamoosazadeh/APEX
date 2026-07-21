"""Structured logging: JSON lines, level gating, error records."""

import io
import json

from apex.core.exceptions import RiskError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp

T0 = Timestamp(epoch_ms=1_750_000_000_000)


def make_factory(stream: io.StringIO, *, level: LogLevel = LogLevel.DEBUG) -> LoggerFactory:
    return LoggerFactory(
        clock=ManualClock(T0),
        level=level,
        log_format=LogFormat.JSON,
        stream=stream,
    )


class TestStructuredLogging:
    def test_json_record_structure(self) -> None:
        stream = io.StringIO()
        logger = make_factory(stream).get("core.test")
        logger.info("bar_ingested", symbol="BTCUSDT", count=5)
        record = json.loads(stream.getvalue().strip())
        assert record == {
            "ts": T0.epoch_ms,
            "level": "info",
            "logger": "apex.core.test",
            "event": "bar_ingested",
            "symbol": "BTCUSDT",
            "count": 5,
        }

    def test_level_gating(self) -> None:
        stream = io.StringIO()
        logger = make_factory(stream, level=LogLevel.WARNING).get("core.test")
        logger.debug("ignored")
        logger.info("ignored_too")
        logger.warning("kept")
        lines = [line for line in stream.getvalue().splitlines() if line]
        assert len(lines) == 1
        assert json.loads(lines[0])["event"] == "kept"

    def test_failure_records_error_contract(self) -> None:
        stream = io.StringIO()
        logger = make_factory(stream).get("core.test")
        error = RiskError("exposure overflow", code="RSK-021", details={"limit": 3})
        logger.failure("risk_rejected", error, symbol="ETHUSDT")
        record = json.loads(stream.getvalue().strip())
        assert record["error_code"] == "RSK-021"
        assert record["error_limit"] == 3
        assert record["symbol"] == "ETHUSDT"
        assert record["level"] == "error"

    def test_console_format_is_single_line(self) -> None:
        stream = io.StringIO()
        factory = LoggerFactory(
            clock=ManualClock(T0),
            level=LogLevel.INFO,
            log_format=LogFormat.CONSOLE,
            stream=stream,
        )
        factory.get("kernel").info("kernel_ready", health="healthy")
        line = stream.getvalue().strip()
        assert "kernel_ready" in line and "health=healthy" in line
        assert "\n" not in line
