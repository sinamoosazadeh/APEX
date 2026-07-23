"""Encrypted secret vault (Book II 25.10/25.11; Book I 13.7/13.8).

Secrets never live in code, in config files or in logs: they live in
one encrypted file under the storage data directory. Encryption is
Fernet (AES-128-CBC + HMAC-SHA256, authenticated), with the key
derived from the operator's master key via scrypt over a per-vault
random salt. The master key is the single root secret of the model
and reaches the process only through the ``APEX_MASTER_KEY``
environment variable - the documented boundary of the vault design.

Fernet's HMAC doubles as tamper detection (25.17): the smallest
modification of the vault file fails decryption with a coded error.
Every write is atomic (write-scratch-then-replace), so a crash never
leaves a half-written vault (13.17 spirit).
"""

import hashlib
import json
import os
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import Final

from cryptography.fernet import Fernet, InvalidToken

from apex.core.exceptions import SecurityError

MASTER_KEY_ENV: Final[str] = "APEX_MASTER_KEY"
VAULT_MAGIC: Final[bytes] = b"APEXVLT1"
_SALT_BYTES: Final[int] = 16
_SCRYPT_N: Final[int] = 2**14
_SCRYPT_R: Final[int] = 8
_SCRYPT_P: Final[int] = 1

# Canonical secret names - the single source for every credential
# rewiring (execution, telegram, signing, config sealing).
SECRET_TOOBIT_KEY: Final[str] = "toobit_api_key"
SECRET_TOOBIT_SECRET: Final[str] = "toobit_api_secret"
SECRET_TELEGRAM_TOKEN: Final[str] = "telegram_bot_token"
SECRET_TELEGRAM_ADMINS: Final[str] = "telegram_admin_chat_ids"
SECRET_TELEGRAM_VIEWERS: Final[str] = "telegram_viewer_chat_ids"
SECRET_SIGNING_KEY: Final[str] = "artifact_signing_key"
SECRET_CONFIG_SIGNATURE: Final[str] = "config_signature"


def _derive_key(master_key: str, salt: bytes) -> bytes:
    """Fernet key from the master key via scrypt (25.11 at-rest)."""
    raw = hashlib.scrypt(
        master_key.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return urlsafe_b64encode(raw)


class SecretVault:
    """One encrypted name -> value store; values never leave in bulk."""

    __slots__ = ("_master_key", "_path")

    def __init__(self, *, path: Path, master_key: str) -> None:
        if not master_key:
            raise SecurityError("empty vault master key", code="SEC-001")
        self._path = path
        self._master_key = master_key

    # --- File format -----------------------------------------------------------------

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        blob = self._path.read_bytes()
        header = len(VAULT_MAGIC) + _SALT_BYTES
        if not blob.startswith(VAULT_MAGIC) or len(blob) <= header:
            raise SecurityError(
                "vault file is malformed",
                code="SEC-002",
                details={"path": str(self._path)},
            )
        salt = blob[len(VAULT_MAGIC) : header]
        try:
            payload = Fernet(_derive_key(self._master_key, salt)).decrypt(blob[header:])
        except InvalidToken as error:
            raise SecurityError(
                "vault cannot be decrypted (wrong master key or tampered file)",
                code="SEC-003",
                details={"path": str(self._path)},
            ) from error
        loaded = json.loads(payload.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise SecurityError("vault payload is not a mapping", code="SEC-004")
        return {str(name): str(value) for name, value in loaded.items()}

    def _write(self, secrets: dict[str, str], *, master_key: str | None = None) -> None:
        key = self._master_key if master_key is None else master_key
        salt = os.urandom(_SALT_BYTES)
        token = Fernet(_derive_key(key, salt)).encrypt(
            json.dumps(secrets, sort_keys=True).encode("utf-8")
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        scratch = self._path.with_suffix(".tmp")
        scratch.write_bytes(VAULT_MAGIC + salt + token)
        os.replace(scratch, self._path)

    # --- Operations ------------------------------------------------------------------

    def unlockable(self) -> bool:
        """Whether the vault decrypts under the configured master key."""
        try:
            self._read()
        except SecurityError:
            return False
        return True

    def exists(self) -> bool:
        """Whether a vault file is present on disk."""
        return self._path.exists()

    def get(self, name: str) -> str | None:
        """One secret value, if stored."""
        return self._read().get(name)

    def set(self, name: str, value: str) -> None:
        """Store (or replace) one secret; the value is never logged."""
        if not name or not value:
            raise SecurityError(
                "secret name and value must be non-empty", code="SEC-005"
            )
        secrets = self._read()
        secrets[name] = value
        self._write(secrets)

    def delete(self, name: str) -> bool:
        """Remove one secret; True when it existed."""
        secrets = self._read()
        if name not in secrets:
            return False
        del secrets[name]
        self._write(secrets)
        return True

    def names(self) -> tuple[str, ...]:
        """Stored secret names (values are never listed)."""
        return tuple(sorted(self._read()))

    def rotate(self, new_master_key: str) -> int:
        """Re-encrypt everything under a new master key (25.10 rotation)."""
        if not new_master_key:
            raise SecurityError("empty vault master key", code="SEC-001")
        secrets = self._read()
        self._write(secrets, master_key=new_master_key)
        self._master_key = new_master_key
        return len(secrets)

    def __repr__(self) -> str:
        return f"SecretVault(path={self._path.name!r}, master_key=***)"
