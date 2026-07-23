"""Security service (Book II 25.31 security contract).

One facade over the platform's security state: secret resolution
(vault-first), the audit sink, the access policy, artifact/config
signing and the aggregated security status. Decision, order and event
history already live in their durable stores and the append-only
event archive (13.24); this ledger covers *operator and security*
actions - secrets, sealing, kill-switch transitions, flattening and
preflight verdicts (13.25).
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.exceptions import SecurityError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import Clock
from apex.security.access import AccessPolicy, Role
from apex.security.audit import AuditRecord, SqliteAuditLedger
from apex.security.config import SecuritySettings
from apex.security.events import SecurityEvent, security_event
from apex.security.signing import sign_payload, verify_payload
from apex.security.vault import (
    MASTER_KEY_ENV,
    SECRET_CONFIG_SIGNATURE,
    SECRET_SIGNING_KEY,
    SecretVault,
)

_SOURCE: Final[str] = "apex.security.service"

VAULT_ABSENT: Final[str] = "absent"
VAULT_LOCKED: Final[str] = "locked"
VAULT_UNLOCKED: Final[str] = "unlocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class SecurityStatus:
    """The 25.31 security status contract."""

    vault_state: str
    secrets_stored: int
    audit_entries: int
    audit_chain_valid: bool
    audit_chain_reason: str | None
    signing_enabled: bool
    config_sealed: bool | None
    policy_actions: int


class SecurityService:
    """Vault-first secrets, audit sink, policy and signing facade."""

    def __init__(
        self,
        *,
        settings: SecuritySettings,
        vault: SecretVault | None,
        ledger: SqliteAuditLedger,
        policy: AccessPolicy,
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._settings = settings
        self._vault = vault
        self._ledger = ledger
        self._policy = policy
        self._bus = bus
        self._clock = clock
        self._logger = logger

    # --- Vault -----------------------------------------------------------------------

    @property
    def vault(self) -> SecretVault | None:
        """The vault, when a master key was provided."""
        return self._vault

    def vault_state(self) -> str:
        """absent (no master key) / locked (undecryptable) / unlocked."""
        if self._vault is None:
            return VAULT_ABSENT
        return VAULT_UNLOCKED if self._vault.unlockable() else VAULT_LOCKED

    def secret(self, name: str) -> str | None:
        """One secret value; None when absent or the vault is locked."""
        if self._vault is None:
            return None
        try:
            return self._vault.get(name)
        except SecurityError as error:
            self._logger.failure("vault_read_failed", error)
            return None

    def _require_vault(self) -> SecretVault:
        if self._vault is None:
            raise SecurityError(
                f"vault master key is not configured (set {MASTER_KEY_ENV})",
                code="SEC-030",
            )
        return self._vault

    async def store_secret(self, name: str, value: str, *, actor: str) -> None:
        """Store one secret; audited and announced by NAME only."""
        self._policy.require(Role.ADMINISTRATOR, "secrets.write")
        self._require_vault().set(name, value)
        await self.audit(
            actor=actor, action="secrets.write", target=name, result="ok",
            details={},
        )
        await self._announce(SecurityEvent.SECRET_UPDATED, {"name": name})

    async def delete_secret(self, name: str, *, actor: str) -> bool:
        """Delete one secret; audited."""
        self._policy.require(Role.ADMINISTRATOR, "secrets.write")
        existed = self._require_vault().delete(name)
        await self.audit(
            actor=actor, action="secrets.delete", target=name,
            result="ok" if existed else "absent", details={},
        )
        if existed:
            await self._announce(SecurityEvent.SECRET_UPDATED, {"name": name})
        return existed

    async def rotate_master_key(self, new_master_key: str, *, actor: str) -> int:
        """Re-encrypt the vault under a new master key; audited."""
        self._policy.require(Role.ADMINISTRATOR, "secrets.rotate")
        count = self._require_vault().rotate(new_master_key)
        await self.audit(
            actor=actor, action="secrets.rotate", target="vault", result="ok",
            details={"secrets": count},
        )
        return count

    # --- Signing (25.18) ---------------------------------------------------------------

    @property
    def signing_enabled(self) -> bool:
        """Whether a signing key is stored."""
        return self.secret(SECRET_SIGNING_KEY) is not None

    def ensure_signing_key(self) -> str:
        """The signing key, generated on first use (hex, vault-held)."""
        vault = self._require_vault()
        existing = vault.get(SECRET_SIGNING_KEY)
        if existing is not None:
            return existing
        generated = os.urandom(32).hex()
        vault.set(SECRET_SIGNING_KEY, generated)
        return generated

    def sign(self, payload: str) -> str | None:
        """Signature under the vault signing key; None when unavailable."""
        key = self.secret(SECRET_SIGNING_KEY)
        return sign_payload(key, payload) if key else None

    def verify(self, payload: str, signature: str) -> bool:
        """Verify a signature under the vault signing key."""
        key = self.secret(SECRET_SIGNING_KEY)
        return bool(key) and verify_payload(key or "", payload, signature)

    # --- Config sealing (13.10) ---------------------------------------------------------

    async def seal_config(self, config_hash: str, *, actor: str) -> None:
        """Sign the booted configuration hash into the vault."""
        self._policy.require(Role.ADMINISTRATOR, "config.seal")
        key = self.ensure_signing_key()
        self._require_vault().set(
            SECRET_CONFIG_SIGNATURE, sign_payload(key, config_hash)
        )
        await self.audit(
            actor=actor, action="config.seal", target="config", result="ok",
            details={"config_hash": config_hash},
        )
        await self._announce(
            SecurityEvent.CONFIG_SEALED, {"config_hash": config_hash}
        )

    def config_sealed(self, config_hash: str) -> bool | None:
        """True/False against the seal; None when unsealed or no vault."""
        signature = self.secret(SECRET_CONFIG_SIGNATURE)
        if signature is None:
            return None
        return self.verify(config_hash, signature)

    # --- Preflight (13.11) ---------------------------------------------------------------

    async def record_preflight(
        self, *, live: bool, passed: bool, actor: str
    ) -> None:
        """Audit and announce one secure-boot verdict."""
        await self.audit(
            actor=actor,
            action="preflight.run",
            target="live" if live else "paper",
            result="pass" if passed else "fail",
            details={},
        )
        await self._announce(
            SecurityEvent.PREFLIGHT_COMPLETED, {"live": live, "passed": passed}
        )

    # --- Policy ------------------------------------------------------------------------

    @property
    def policy(self) -> AccessPolicy:
        """The active access policy."""
        return self._policy

    def authorize(self, role: Role, action: str) -> bool:
        """Whether the role may perform the action."""
        return self._policy.authorize(role, action)

    # --- Audit -------------------------------------------------------------------------

    async def audit(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        result: str,
        details: Mapping[str, JsonValue],
    ) -> AuditRecord:
        """Chain one entry onto the immutable ledger (25.16)."""
        record = await self._ledger.append(
            actor=actor,
            action=action,
            target=target,
            result=result,
            details=details,
            occurred_at=self._clock.now(),
        )
        self._logger.info(
            "audited", actor=actor, action=action, target=target, result=result
        )
        return record

    # --- Status (25.31) ------------------------------------------------------------------

    async def status(self, *, config_hash: str) -> SecurityStatus:
        """The aggregated security status contract."""
        valid, checked, reason = await self._ledger.verify_chain()
        vault_state = self.vault_state()
        return SecurityStatus(
            vault_state=vault_state,
            secrets_stored=(
                len(self._vault.names())
                if self._vault is not None and vault_state == VAULT_UNLOCKED
                else 0
            ),
            audit_entries=checked,
            audit_chain_valid=valid,
            audit_chain_reason=reason,
            signing_enabled=self.signing_enabled,
            config_sealed=self.config_sealed(config_hash),
            policy_actions=len(self._policy.actions()),
        )

    async def _announce(
        self, kind: SecurityEvent, payload: dict[str, JsonValue]
    ) -> None:
        await self._bus.publish(
            security_event(
                kind,
                occurred_at=self._clock.now(),
                source=_SOURCE,
                payload=payload,
            )
        )
