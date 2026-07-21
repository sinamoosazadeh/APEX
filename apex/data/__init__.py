"""APEX Data Platform (Book II ch. 6/16) - Phase 3.

The Toobit connector (REST + WebSocket) behind IMarketDataGateway,
the bar ingestion pipeline (fetch, quality-inspect, persist, announce),
gap detection, catch-up synchronization, live streaming (closed-bar
events + tick capture) and replay of stored history through the same
contract live engines consume.

Boot never touches the network; ingestion runs on demand:
``apex sync``, ``apex stream --seconds N``, ``apex ingest ...``.
"""

from apex.data.catchup import CatchUpReport, CatchUpService
from apex.data.events import MarketEvent, market_event
from apex.data.module import MarketDataModule
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.data.quality import BarQualityInspector, GapReport
from apex.data.replay import ReplayMarketDataGateway
from apex.data.streaming import MarketStreamService, StreamStats

__all__ = [
    "BarIngestionPipeline",
    "BarQualityInspector",
    "CatchUpReport",
    "CatchUpService",
    "GapReport",
    "IngestionSummary",
    "MarketDataModule",
    "MarketEvent",
    "MarketStreamService",
    "ReplayMarketDataGateway",
    "StreamStats",
    "market_event",
]
