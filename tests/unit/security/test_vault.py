"""Vault: encrypted roundtrip, rotation, tamper detection."""

from pathlib import Path

import pytest
from apex.core.exceptions import SecurityError
from apex.security.vault import SecretVault


def vault(tmp_path: Path, key: str = "master-key-1") -> SecretVault:
    return SecretVault(path=tmp_path / "vault.enc", master_key=key)


class TestVault:
    def test_roundtrip_names_and_delete(self, tmp_path: Path) -> None:
        store = vault(tmp_path)
        assert not store.exists()
        assert store.get("absent") is None
        store.set("toobit_api_key", "K123")
        store.set("alpha", "v")
        assert store.exists()
        assert store.get("toobit_api_key") == "K123"
        assert store.names() == ("alpha", "toobit_api_key")
        assert store.delete("alpha") is True
        assert store.delete("alpha") is False
        assert store.names() == ("toobit_api_key",)
        assert store.unlockable()

    def test_wrong_master_key_is_rejected(self, tmp_path: Path) -> None:
        vault(tmp_path).set("name", "value")
        wrong = vault(tmp_path, key="other")
        with pytest.raises(SecurityError) as caught:
            wrong.get("name")
        assert caught.value.code == "SEC-003"
        assert not wrong.unlockable()

    def test_rotation_reencrypts_under_the_new_key(self, tmp_path: Path) -> None:
        store = vault(tmp_path)
        store.set("name", "value")
        assert store.rotate("master-key-2") == 1
        assert store.get("name") == "value"
        assert not vault(tmp_path).unlockable()
        assert vault(tmp_path, key="master-key-2").get("name") == "value"

    def test_tampering_is_detected(self, tmp_path: Path) -> None:
        store = vault(tmp_path)
        store.set("name", "value")
        path = tmp_path / "vault.enc"
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0xFF
        path.write_bytes(bytes(blob))
        with pytest.raises(SecurityError) as caught:
            store.get("name")
        assert caught.value.code == "SEC-003"

    def test_guards_and_masking(self, tmp_path: Path) -> None:
        with pytest.raises(SecurityError) as empty_key:
            SecretVault(path=tmp_path / "v.enc", master_key="")
        assert empty_key.value.code == "SEC-001"
        store = vault(tmp_path)
        with pytest.raises(SecurityError) as empty_name:
            store.set("", "x")
        assert empty_name.value.code == "SEC-005"
        (tmp_path / "vault.enc").write_bytes(b"garbage")
        with pytest.raises(SecurityError) as malformed:
            store.get("x")
        assert malformed.value.code == "SEC-002"
        assert "***" in repr(store)
