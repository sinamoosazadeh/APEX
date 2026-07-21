"""APEX Storage Platform (Book II ch. 24).

SQLite backends behind the core storage contracts: a namespaced
key/value store (IStorage), the market data system of record
(bars + ticks, idempotent on natural keys / trade ids) and durable
event archiving (Book II 5.32). DuckDB/Parquet analytical backends
join in later phases behind the same contracts.
"""

from apex.storage.archive import EventArchiveModule
from apex.storage.bars import SqliteBarRepository
from apex.storage.sqlite import SqliteKeyValueStorage
from apex.storage.ticks import SqliteTickRepository

__all__ = [
    "EventArchiveModule",
    "SqliteBarRepository",
    "SqliteKeyValueStorage",
    "SqliteTickRepository",
]
