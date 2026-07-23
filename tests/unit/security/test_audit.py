"""Audit ledger: hash chaining, verification, tamper detection."""

import asyncio
import sqlite3
from pathlib import Path

from apex.security.audit import GENESIS_HASH, SqliteAuditLedger

from tests.conftest import T0


def ledger(tmp_path: Path) -> SqliteAuditLedger:
    return SqliteAuditLedger(database_path=tmp_path / "audit.sqlite")


async def _two_entries(store: SqliteAuditLedger) -> None:
    await store.append(
        actor="operator",
        action="secrets.write",
        target="toobit_api_key",
        result="ok",
        details={},
        occurred_at=T0,
    )
    await store.append(
        actor="monitoring",
        action="kill.transition",
        target="paused",
        result="ok",
        details={"reason": "drill"},
        occurred_at=T0.add_ms(1_000),
    )


class TestAuditChain:
    def test_appends_chain_and_verify(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = ledger(tmp_path)
            await store.open()
            await _two_entries(store)
            records = await store.records()
            assert records[0].previous_hash == GENESIS_HASH
            assert records[1].previous_hash == records[0].entry_hash
            valid, checked, reason = await store.verify_chain()
            assert valid and checked == 2 and reason is None
            assert await store.count() == 2
            newest = await store.records(limit=1)
            assert [record.sequence for record in newest] == [2]
            await store.close()

        asyncio.run(scenario())

    def test_tampering_breaks_the_chain(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            store = ledger(tmp_path)
            await store.open()
            await _two_entries(store)
            await store.close()
            connection = sqlite3.connect(tmp_path / "audit.sqlite")
            with connection:
                connection.execute(
                    "UPDATE audit_ledger SET result = 'forged' WHERE sequence = 1"
                )
            connection.close()
            reopened = ledger(tmp_path)
            await reopened.open()
            valid, checked, reason = await reopened.verify_chain()
            assert not valid
            assert checked == 0
            assert reason is not None and "entry 1" in reason
            await reopened.close()

        asyncio.run(scenario())
