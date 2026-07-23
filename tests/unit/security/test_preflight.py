"""Secure-boot preflight: paper leniency, live strictness, integrity."""

import asyncio
from pathlib import Path

from apex.core.config import load_config
from apex.core.time.clock import ManualClock
from apex.security.audit import SqliteAuditLedger
from apex.security.config import SecuritySettings
from apex.security.preflight import PreflightReport, SecurePreflight
from apex.security.signing import sign_payload
from apex.security.vault import (
    SECRET_CONFIG_SIGNATURE,
    SECRET_SIGNING_KEY,
    SECRET_TOOBIT_KEY,
    SECRET_TOOBIT_SECRET,
    SecretVault,
)
from apex.storage.bars import SqliteBarRepository

from tests.conftest import T0


async def _report(
    config_dir: Path,
    tmp_path: Path,
    *,
    live: bool,
    vault: SecretVault | None,
    corrupt: bool = False,
) -> PreflightReport:
    config = load_config(config_dir)
    data_dir = tmp_path / "runtime"
    data_dir.mkdir(exist_ok=True)
    ledger = SqliteAuditLedger(database_path=data_dir / "audit.sqlite")
    bars = SqliteBarRepository(database_path=data_dir / "bars.sqlite")
    await ledger.open()
    await bars.open()
    if corrupt:
        (data_dir / "broken.sqlite").write_bytes(b"garbage, not a database")
    preflight = SecurePreflight(
        settings=SecuritySettings(),
        config=config,
        data_dir=data_dir,
        vault=vault,
        ledger=ledger,
        bars=bars,
        exchange_id="toobit",
        clock=ManualClock(T0),
    )
    report = await preflight.run(live=live)
    await bars.close()
    await ledger.close()
    return report


def _check(report: PreflightReport, name: str) -> tuple[bool, bool]:
    for check in report.checks:
        if check.name == name:
            return check.passed, check.skipped
    raise AssertionError(f"missing check {name}")


class TestPreflight:
    def test_paper_mode_passes_without_a_vault(
        self, config_dir: Path, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            report = await _report(config_dir, tmp_path, live=False, vault=None)
            assert report.passed
            assert _check(report, "config_seal") == (True, True)  # skipped
            assert _check(report, "credentials") == (True, True)
            assert _check(report, "databases") == (True, False)
            assert _check(report, "audit_chain") == (True, False)

        asyncio.run(scenario())

    def test_live_mode_refuses_unsealed_and_credentialless(
        self, config_dir: Path, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            report = await _report(config_dir, tmp_path, live=True, vault=None)
            assert not report.passed
            assert _check(report, "config_seal") == (False, False)
            assert _check(report, "credentials") == (False, False)

        asyncio.run(scenario())

    def test_live_mode_passes_sealed_with_vault_credentials(
        self, config_dir: Path, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            config = load_config(config_dir)
            vault = SecretVault(
                path=tmp_path / "vault.enc", master_key="master"
            )
            vault.set(SECRET_SIGNING_KEY, "signing-key")
            vault.set(
                SECRET_CONFIG_SIGNATURE,
                sign_payload("signing-key", config.config_hash),
            )
            vault.set(SECRET_TOOBIT_KEY, "K")
            vault.set(SECRET_TOOBIT_SECRET, "S")
            report = await _report(config_dir, tmp_path, live=True, vault=vault)
            assert report.passed
            assert _check(report, "config_seal") == (True, False)
            assert _check(report, "credentials") == (True, False)
            assert _check(report, "vault") == (True, False)

        asyncio.run(scenario())

    def test_corrupt_database_fails_integrity(
        self, config_dir: Path, tmp_path: Path
    ) -> None:
        async def scenario() -> None:
            report = await _report(
                config_dir, tmp_path, live=False, vault=None, corrupt=True
            )
            passed, skipped = _check(report, "databases")
            assert not passed and not skipped
            assert not report.passed

        asyncio.run(scenario())
