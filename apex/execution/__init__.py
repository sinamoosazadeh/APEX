"""Execution platform (Phase 10): paper and live order execution.

Order management, venue trading, fills and reconciliation into the
portfolio (Book II ch. 12/20; Book VII) - the last layer between an
approved decision and the market, bound by the golden rule: nothing
decided upstream is ever altered here.
"""

from apex.execution.config import ExecutionSettings, execution_settings
from apex.execution.engine import LiveExecutionEngine
from apex.execution.paper import PaperExecutionEngine
from apex.execution.service import ExecutionService, ExecutionSummary
from apex.execution.store import (
    ExecutionRecord,
    FillRecord,
    SqliteExecutionRepository,
)
from apex.execution.trading.client import ToobitTradingClient, TradingCredentials

__all__ = [
    "ExecutionRecord",
    "ExecutionService",
    "ExecutionSettings",
    "ExecutionSummary",
    "FillRecord",
    "LiveExecutionEngine",
    "PaperExecutionEngine",
    "SqliteExecutionRepository",
    "ToobitTradingClient",
    "TradingCredentials",
    "execution_settings",
]
