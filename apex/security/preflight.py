"""Secure-boot preflight (Book I 13.11; Book II 25.19 fail-safe).

Before live trading, the system verifies itself: configuration hash
and its seal (13.10), the integrity of every SQLite store (PRAGMA
quick_check, 25.26), the audit chain (25.17), vault accessibility,
clock sanity against venue-stamped bars (13.23) and live-credential
resolvability. Any live-blocking failure means live trading does not
start (13.11) - a controlled stop over an uncertain run (25.32).
"""

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from apex.core.config import AppConfig
from apex.core.time.clock import Clock
from apex.security.audit import SqliteAuditLedger
from apex.security.config import SecuritySettings
from apex.security.vault import (
    SECRET_CONFIG_SIGNATURE,
    SECRET_TOOBIT_KEY,
    SECRET_TOOBIT_SECRET,
    SecretVault,
)
from apex.storage.bars import SqliteBarRepository

_TOOBIT_KEY_ENV = "TOOBIT_API_KEY"
_TOOBIT_SECRET_ENV = "TOOBIT_API_SECRET"


@dataclass(frozen=True, slots=True, kw_only=True)
class PreflightCheck:
    """One verified condition."""

    name: str
    passed: bool
    skipped: bool
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PreflightReport:
    """The full secure-boot verdict."""

    live: bool
    checks: tuple[PreflightCheck, ...]

    @property
    def passed(self) -> bool:
        """True when no non-skipped check failed."""
        return all(check.passed or check.skipped for check in self.checks)

    def lines(self) -> list[str]:
        """Human-readable report lines."""
        rows = [f"secure preflight ({'live' if self.live else 'paper'} mode)"]
        for check in self.checks:
            mark = "SKIP" if check.skipped else ("ok" if check.passed else "FAIL")
            rows.append(f"  {check.name:<18}: {mark:<4} {check.detail}")
        rows.append(f"  verdict           : {'PASS' if self.passed else 'FAIL'}")
        return rows


class SecurePreflight:
    """Runs the 13.11 checklist over the booted platform."""

    def __init__(
        self,
        *,
        settings: SecuritySettings,
        config: AppConfig,
        data_dir: Path,
        vault: SecretVault | None,
        ledger: SqliteAuditLedger,
        bars: SqliteBarRepository,
        exchange_id: str,
        clock: Clock,
    ) -> None:
        self._settings = settings
        self._config = config
        self._data_dir = data_dir
        self._vault = vault
        self._ledger = ledger
        self._bars = bars
        self._exchange_id = exchange_id
        self._clock = clock

    async def run(self, *, live: bool) -> PreflightReport:
        """Every check; live mode escalates seal/credential requirements."""
        checks = (
            self._check_config(),
            self._check_config_seal(live),
            self._check_databases(),
            await self._check_audit_chain(),
            self._check_vault(),
            await self._check_clock(),
            self._check_live_credentials(live),
        )
        return PreflightReport(live=live, checks=checks)

    # --- Checks ------------------------------------------------------------------------

    def _check_config(self) -> PreflightCheck:
        digest = self._config.config_hash
        return PreflightCheck(
            name="config",
            passed=bool(digest),
            skipped=False,
            detail=f"hash {digest[:16]}" if digest else "no config hash",
        )

    def _check_config_seal(self, live: bool) -> PreflightCheck:
        name = "config_seal"
        required = live and self._settings.require_sealed_config_live
        if self._vault is None or not self._vault.unlockable():
            return PreflightCheck(
                name=name,
                passed=not required,
                skipped=not required,
                detail="vault unavailable",
            )
        signature = self._vault.get(SECRET_CONFIG_SIGNATURE)
        if signature is None:
            return PreflightCheck(
                name=name,
                passed=not required,
                skipped=not required,
                detail="config is not sealed",
            )
        from apex.security.signing import verify_payload
        from apex.security.vault import SECRET_SIGNING_KEY

        key = self._vault.get(SECRET_SIGNING_KEY) or ""
        valid = verify_payload(key, self._config.config_hash, signature)
        return PreflightCheck(
            name=name,
            passed=valid,
            skipped=False,
            detail="seal verified" if valid else "config changed since sealing",
        )

    def _check_databases(self) -> PreflightCheck:
        files = sorted(self._data_dir.glob("*.sqlite"))
        if not files:
            return PreflightCheck(
                name="databases", passed=True, skipped=True, detail="no stores yet"
            )
        for path in files:
            try:
                connection = sqlite3.connect(
                    f"file:{path}?mode=ro", uri=True, check_same_thread=False
                )
                try:
                    row = connection.execute("PRAGMA quick_check").fetchone()
                finally:
                    connection.close()
            except sqlite3.Error as error:
                return PreflightCheck(
                    name="databases",
                    passed=False,
                    skipped=False,
                    detail=f"{path.name}: {error}",
                )
            if row is None or str(row[0]) != "ok":
                return PreflightCheck(
                    name="databases",
                    passed=False,
                    skipped=False,
                    detail=f"{path.name}: integrity check failed",
                )
        return PreflightCheck(
            name="databases",
            passed=True,
            skipped=False,
            detail=f"{len(files)} stores ok",
        )

    async def _check_audit_chain(self) -> PreflightCheck:
        valid, checked, reason = await self._ledger.verify_chain()
        return PreflightCheck(
            name="audit_chain",
            passed=valid,
            skipped=False,
            detail=f"{checked} entries ok" if valid else str(reason),
        )

    def _check_vault(self) -> PreflightCheck:
        if self._vault is None:
            return PreflightCheck(
                name="vault", passed=True, skipped=True, detail="no master key set"
            )
        unlockable = self._vault.unlockable()
        return PreflightCheck(
            name="vault",
            passed=unlockable,
            skipped=False,
            detail="unlocked" if unlockable else "cannot decrypt",
        )

    async def _check_clock(self) -> PreflightCheck:
        """Local clock vs the newest venue-stamped bar (13.23)."""
        newest = 0
        for symbol in self._config.market.symbols:
            for timeframe in self._config.market.timeframes:
                latest = await self._bars.latest_open_time(
                    self._exchange_id, symbol, timeframe
                )
                if latest is not None:
                    newest = max(newest, latest.epoch_ms)
        if newest == 0:
            return PreflightCheck(
                name="clock", passed=True, skipped=True, detail="no bars stored"
            )
        skew = newest - self._clock.now().epoch_ms
        if skew > self._settings.clock_skew_tolerance_ms:
            return PreflightCheck(
                name="clock",
                passed=False,
                skipped=False,
                detail=f"local clock {skew}ms behind venue bars",
            )
        return PreflightCheck(
            name="clock", passed=True, skipped=False, detail="sane vs venue bars"
        )

    def _check_live_credentials(self, live: bool) -> PreflightCheck:
        if not live:
            return PreflightCheck(
                name="credentials",
                passed=True,
                skipped=True,
                detail="paper mode",
            )
        from_vault = (
            self._vault is not None
            and self._vault.unlockable()
            and self._vault.get(SECRET_TOOBIT_KEY) is not None
            and self._vault.get(SECRET_TOOBIT_SECRET) is not None
        )
        from_env = bool(
            os.environ.get(_TOOBIT_KEY_ENV) and os.environ.get(_TOOBIT_SECRET_ENV)
        )
        resolvable = from_vault or from_env
        return PreflightCheck(
            name="credentials",
            passed=resolvable,
            skipped=False,
            detail=(
                "vault" if from_vault else "environment" if from_env else
                "no trading credentials resolvable"
            ),
        )
