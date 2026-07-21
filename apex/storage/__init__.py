"""APEX Storage Platform (Book II ch. 24).

First delivered slice: SQLite backends behind the core storage
contracts - a namespaced key/value store (:class:`SqliteKeyValueStorage`
implements ``IStorage``), the market data system of record
(:class:`SqliteBarRepository`) and durable event archiving
(:class:`EventArchiveModule`, Book II 5.32).

DuckDB/Parquet analytical backends join in later phases behind the
same contracts.
"""

from apex.storage.archive import EventArchiveModule
from apex.storage.bars import SqliteBarRepository
from apex.storage.sqlite import SqliteKeyValueStorage

__all__ = ["EventArchiveModule", "SqliteBarRepository", "SqliteKeyValueStorage"]
