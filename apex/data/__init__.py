"""APEX Data Platform (Book II ch. 6/16) - Phase 3.

First delivered slice: the Toobit market data gateway behind the
IMarketDataGateway contract, the bar ingestion pipeline (fetch,
quality-inspect, persist, announce), gap detection, and a replay
gateway that serves stored history through the same contract.

Ingestion is on-demand (CLI ``apex ingest``; the Phase 11 scheduler
automates it) - kernel boot never touches the network.
"""

from apex.data.events import MarketEvent, market_event
from apex.data.module import MarketDataModule
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.data.quality import BarQualityInspector, GapReport
from apex.data.replay import ReplayMarketDataGateway

__all__ = [
    "BarIngestionPipeline",
    "BarQualityInspector",
    "GapReport",
    "IngestionSummary",
    "MarketDataModule",
    "MarketEvent",
    "ReplayMarketDataGateway",
    "market_event",
]
