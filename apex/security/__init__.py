"""Security platform (Phase 13): vault, audit, access, preflight.

The Book II ch. 25 / Book I ch. 13 security and reliability layer:
the encrypted secret vault (25.10), the immutable hash-chained audit
ledger (25.16), HMAC artifact/config signing (25.18/13.10), the role
model and access policy (25.9/13.14) and the secure-boot preflight
(13.11) - the layer that makes a controlled, safe stop always
preferable to an uncertain run (25.32).
"""

from apex.security.access import AccessPolicy, Role
from apex.security.audit import GENESIS_HASH, AuditRecord, SqliteAuditLedger
from apex.security.config import SecuritySettings, security_settings
from apex.security.signing import canonical_json, sign_payload, verify_payload
from apex.security.vault import MASTER_KEY_ENV, SecretVault

__all__ = [
    "GENESIS_HASH",
    "MASTER_KEY_ENV",
    "AccessPolicy",
    "AuditRecord",
    "Role",
    "SecretVault",
    "SecuritySettings",
    "SqliteAuditLedger",
    "canonical_json",
    "security_settings",
    "sign_payload",
    "verify_payload",
]
