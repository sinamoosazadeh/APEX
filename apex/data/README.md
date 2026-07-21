# apex.data — Data Platform

Book II ch. 6/16, Phase 3 first slice. The Toobit connector
(`toobit/`: REST client with injected transport, anti-corruption
translator, paginating gateway) implements `IMarketDataGateway`.
`BarQualityInspector` detects gaps and scores bars; forming bars are
down-scored and flagged (non-repainting). `BarIngestionPipeline` is the
single path into the bar store: fetch → inspect → persist → publish
catalog events (`market.bars.ingested`, `market.gap.detected`,
`market.ingestion.failed`). `ReplayMarketDataGateway` serves stored
confirmed history through the same contract for deterministic replay.

Run it: `python -m apex ingest --symbol BTCUSDT --timeframe 1h --bars 200`

Tests: `tests/unit/data/`.
