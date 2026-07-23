"""Security service: vault facade, sealing, audit sink, status."""

import asyncio
from pathlib import Path

import pytest
from apex.core.exceptions import SecurityError
from apex.core.time.clock import ManualClock
from apex.security.access import AccessPolicy
from apex.security.audit import SqliteAuditLedger
from apex.security.config import SecuritySettings
from apex.security.service import (
    VAULT_ABSENT,
    VAULT_UNLOCKED,
    SecurityService,
)
from apex.security.vault import SecretVault

from tests.conftest import T0
from tests.unit.monitoring.support import logger, make_bus


def build(tmp_path: Path, *, with_vault: bool) -> tuple[SecurityService, SqliteAuditLedger]:
    clock = ManualClock(T0)
    ledger = SqliteAuditLedger(database_path=tmp_path / "audit.sqlite")
    vault = (
        SecretVault(path=tmp_path / "vault.enc", master_key="master")
        if with_vault
        else None
    )
    service = SecurityService(
        settings=SecuritySettings(),
        vault=vault,
        ledger=ledger,
        policy=AccessPolicy.defaults(),
        bus=make_bus(clock),
        clock=clock,
        logger=logger(),
    )
    return service, ledger


class TestSecurityService:
    def test_secrets_seal_and_status(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            service, ledger = build(tmp_path, with_vault=True)
            await ledger.open()
            await service.store_secret("toobit_api_key", "K", actor="operator")
            assert service.secret("toobit_api_key") == "K"
            assert service.vault_state() == VAULT_UNLOCKED
            key = service.ensure_signing_key()
            assert service.ensure_signing_key() == key  # stable
            signature = service.sign("payload")
            assert signature is not None
            assert service.verify("payload", signature)
            assert not service.verify("payload", "forged")
            await service.seal_config("confighash", actor="operator")
            assert service.config_sealed("confighash") is True
            assert service.config_sealed("otherhash") is False
            status = await service.status(config_hash="confighash")
            assert status.vault_state == VAULT_UNLOCKED
            assert status.signing_enabled
            assert status.config_sealed is True
            assert status.audit_chain_valid
            assert status.audit_entries == 2  # secrets.write + config.seal
            assert status.policy_actions > 0
            await service.delete_secret("toobit_api_key", actor="operator")
            assert service.secret("toobit_api_key") is None
            await ledger.close()

        asyncio.run(scenario())

    def test_absent_vault_degrades_honestly(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            service, ledger = build(tmp_path, with_vault=False)
            await ledger.open()
            assert service.vault_state() == VAULT_ABSENT
            assert service.secret("anything") is None
            assert service.sign("payload") is None
            assert not service.verify("payload", "sig")
            assert service.config_sealed("hash") is None
            with pytest.raises(SecurityError) as caught:
                await service.store_secret("name", "value", actor="operator")
            assert caught.value.code == "SEC-030"
            status = await service.status(config_hash="hash")
            assert status.vault_state == VAULT_ABSENT
            assert not status.signing_enabled
            await ledger.close()

        asyncio.run(scenario())

    def test_preflight_verdicts_are_audited(self, tmp_path: Path) -> None:
        async def scenario() -> None:
            service, ledger = build(tmp_path, with_vault=False)
            await ledger.open()
            await service.record_preflight(live=True, passed=False, actor="operator")
            records = await ledger.records()
            assert len(records) == 1
            assert records[0].action == "preflight.run"
            assert records[0].target == "live"
            assert records[0].result == "fail"
            await ledger.close()

        asyncio.run(scenario())
