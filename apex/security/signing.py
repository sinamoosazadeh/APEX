"""HMAC payload signing (Book II 25.18; Book I 13.10).

Deployments, configs and optimizer artifacts carry digital signatures:
HMAC-SHA256 over the canonical JSON serialization under a vault-held
signing key. Verification uses a constant-time comparison.
"""

import hashlib
import hmac
import json
from collections.abc import Mapping

from apex.core.exceptions import SecurityError


def canonical_json(payload: Mapping[str, object]) -> str:
    """The canonical serialization every signature is computed over."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sign_payload(key: str, payload: str) -> str:
    """HMAC-SHA256 signature of ``payload`` under ``key`` (hex)."""
    if not key:
        raise SecurityError("empty signing key", code="SEC-006")
    return hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_payload(key: str, payload: str, signature: str) -> bool:
    """Constant-time signature verification (25.17 tamper detection)."""
    if not key or not signature:
        return False
    return hmac.compare_digest(sign_payload(key, payload), signature)
