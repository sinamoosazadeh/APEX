# apex.storage — Storage Platform

Book II ch. 24, first slice. `SqliteKeyValueStorage` implements the
`IStorage` contract (namespaced key/value, WAL, async via thread
offload). `SqliteBarRepository` is the market data system of record:
idempotent upsert on the natural key (exchange, symbol, timeframe,
open time), range queries, closed-only filtering. `EventArchiveModule`
persists every bus event (journal catch-up on start, sequence-keyed,
Book II 5.32). `plugin.py` exposes the `storage_core` plugin.

Tests: `tests/unit/storage/`.
