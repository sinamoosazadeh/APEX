"""Security CLI runners (Phase 13): preflight, secrets, audit.

Thin kernel-booting runners behind ``apex secure-check``,
``apex secrets`` and ``apex audit`` (the kill-switch command lives in
``apex.__main__`` beside the other cross-layer compositions). Secret
VALUES never travel through argv (shell history is a log too, 13.7):
writes read them from named environment variables. The local CLI acts
as the OPERATOR role except for vault administration, which the
policy reserves for ADMINISTRATOR - the local operator holds both by
default; the policy stays config-overridable.
"""

import os
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock
from apex.core.exceptions import ValidationError
from apex.kernel.kernel import Kernel
from apex.security.audit import SqliteAuditLedger
from apex.security.config import SecuritySettings
from apex.security.preflight import PreflightReport, SecurePreflight
from apex.security.service import VAULT_UNLOCKED, SecurityService
from apex.security.vault import MASTER_KEY_ENV
from apex.storage.bars import SqliteBarRepository


def build_preflight(kernel: Kernel) -> SecurePreflight:
    """The 13.11 preflight assembled from a booted kernel's services."""
    config = kernel.container.resolve(AppConfig)
    service = kernel.container.resolve(SecurityService)
    clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
    return SecurePreflight(
        settings=kernel.container.resolve(SecuritySettings),
        config=config,
        data_dir=Path(config.system.data_dir),
        vault=service.vault,
        ledger=kernel.container.resolve(SqliteAuditLedger),
        bars=kernel.container.resolve(SqliteBarRepository),
        exchange_id="toobit",
        clock=clock,
    )


async def run_secure_check(config_dir: Path, *, live: bool) -> PreflightReport:
    """Boot, run the preflight, audit the verdict, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        report = await build_preflight(kernel).run(live=live)
        service = kernel.container.resolve(SecurityService)
        await service.record_preflight(
            live=live, passed=report.passed, actor="operator"
        )
        return report
    finally:
        await kernel.shutdown()


async def run_secrets(
    config_dir: Path, *, action: str, name: str | None, from_env: str | None
) -> list[str]:
    """Boot, perform one vault operation, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        service = kernel.container.resolve(SecurityService)
        if action == "list":
            return _list_lines(service)
        if action == "set":
            await service.store_secret(
                _required_name(name), _env_value(from_env), actor="operator"
            )
            return [f"secret stored: {name}"]
        if action == "delete":
            existed = await service.delete_secret(
                _required_name(name), actor="operator"
            )
            return [f"secret {'deleted' if existed else 'was absent'}: {name}"]
        if action == "rotate":
            count = await service.rotate_master_key(
                _env_value(from_env), actor="operator"
            )
            return [
                f"vault re-encrypted: {count} secret(s) under the new master key",
                f"update {MASTER_KEY_ENV} to the new value for future runs",
            ]
        config = kernel.container.resolve(AppConfig)
        await service.seal_config(config.config_hash, actor="operator")
        return [f"config sealed: {config.config_hash[:16]}"]
    finally:
        await kernel.shutdown()


def _list_lines(service: SecurityService) -> list[str]:
    state = service.vault_state()
    lines = [f"vault: {state}"]
    if service.vault is not None and state == VAULT_UNLOCKED:
        names = service.vault.names()
        lines.extend(f"  {stored}" for stored in names)
        if not names:
            lines.append("  (empty)")
    return lines


def _required_name(name: str | None) -> str:
    if not name:
        raise ValidationError("--name is required", code="VAL-141")
    return name


def _env_value(from_env: str | None) -> str:
    if not from_env:
        raise ValidationError(
            "--from-env is required (values never travel through argv)",
            code="VAL-142",
        )
    value = os.environ.get(from_env, "")
    if not value:
        raise ValidationError(
            f"environment variable {from_env} is unset or empty",
            code="VAL-143",
        )
    return value


async def run_audit(config_dir: Path, *, tail: int) -> list[str]:
    """Boot, verify the chain and tail the ledger, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        ledger = kernel.container.resolve(SqliteAuditLedger)
        valid, checked, reason = await ledger.verify_chain()
        lines = [
            f"audit chain : {'VALID' if valid else 'BROKEN'} ({checked} entries)"
            + (f" - {reason}" if reason else "")
        ]
        records = await ledger.records(limit=tail) if tail else []
        for record in records:
            lines.append(
                f"  #{record.sequence} {record.occurred_at.epoch_ms} "
                f"{record.actor} {record.action} {record.target} "
                f"[{record.result}]"
            )
        if tail and not records:
            lines.append("  (no audit entries)")
        return lines
    finally:
        await kernel.shutdown()
