"""HMAC signing: roundtrip, wrong-key rejection, canonicalization."""

import pytest
from apex.core.exceptions import SecurityError
from apex.security.signing import canonical_json, sign_payload, verify_payload


class TestSigning:
    def test_roundtrip_and_wrong_key(self) -> None:
        payload = canonical_json({"b": 2, "a": 1})
        assert payload == '{"a":1,"b":2}'
        signature = sign_payload("key-1", payload)
        assert verify_payload("key-1", payload, signature)
        assert not verify_payload("key-2", payload, signature)
        assert not verify_payload("key-1", payload + " ", signature)

    def test_empty_key_paths(self) -> None:
        with pytest.raises(SecurityError) as caught:
            sign_payload("", "payload")
        assert caught.value.code == "SEC-006"
        assert not verify_payload("", "payload", "sig")
        assert not verify_payload("key", "payload", "")
