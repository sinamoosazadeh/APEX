"""Backup/restore: consistency, verification, tamper rejection, prune."""

import sqlite3
import tarfile
import tempfile
from pathlib import Path

import pytest
from apex.core.exceptions import DeploymentError
from apex.deployment.backup import (
    create_backup,
    prune_backups,
    restore_backup,
    verify_backup,
)

from tests.conftest import T0


def make_state(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(data_dir / "bars.sqlite")
    with connection:
        connection.execute("CREATE TABLE bars (open_ms INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO bars VALUES (42)")
    connection.close()
    (data_dir / "vault.enc").write_bytes(b"APEXVLT1-fake-bytes")
    (data_dir / "optimizer").mkdir(exist_ok=True)
    (data_dir / "optimizer" / "BTCUSDT_1h_signal.json").write_text("{}")


class TestBackupRestore:
    def test_roundtrip_preserves_state(self, tmp_path: Path) -> None:
        data = tmp_path / "runtime"
        make_state(data)
        archive = create_backup(data, tmp_path / "backups", created_at=T0)
        ok, files, reason = verify_backup(archive)
        assert ok and files == 3 and reason is None
        target = tmp_path / "restored"
        restored = restore_backup(archive, target, force=False)
        assert restored == 3
        connection = sqlite3.connect(target / "bars.sqlite")
        rows = connection.execute("SELECT open_ms FROM bars").fetchall()
        connection.close()
        assert rows == [(42,)]
        assert (target / "vault.enc").read_bytes() == b"APEXVLT1-fake-bytes"

    def test_refuses_existing_state_without_force(self, tmp_path: Path) -> None:
        data = tmp_path / "runtime"
        make_state(data)
        archive = create_backup(data, tmp_path / "backups", created_at=T0)
        with pytest.raises(DeploymentError) as caught:
            restore_backup(archive, data, force=False)
        assert caught.value.code == "DEP-002"
        assert restore_backup(archive, data, force=True) == 3

    def test_tampered_archive_is_rejected(self, tmp_path: Path) -> None:
        data = tmp_path / "runtime"
        make_state(data)
        archive = create_backup(data, tmp_path / "backups", created_at=T0)
        forged = tmp_path / "forged.tar.gz"
        with (
            tempfile.TemporaryDirectory() as scratch_name,
            tarfile.open(archive, "r:gz") as source,
        ):
            scratch = Path(scratch_name)
            source.extractall(scratch, filter="data")
            (scratch / "state" / "vault.enc").write_bytes(b"tampered!")
            with tarfile.open(forged, "w:gz") as rebuilt:
                for member in sorted(scratch.rglob("*")):
                    if member.is_file():
                        rebuilt.add(
                            member, arcname=member.relative_to(scratch).as_posix()
                        )
        ok, _, reason = verify_backup(forged)
        assert not ok and reason is not None and "vault.enc" in reason
        with pytest.raises(DeploymentError) as caught:
            restore_backup(forged, tmp_path / "elsewhere", force=True)
        assert caught.value.code == "DEP-004"

    def test_prune_keeps_the_newest(self, tmp_path: Path) -> None:
        data = tmp_path / "runtime"
        make_state(data)
        backups = tmp_path / "backups"
        for offset in range(4):
            create_backup(data, backups, created_at=T0.add_ms(offset * 1_000))
        assert prune_backups(backups, keep=2) == 2
        remaining = sorted(path.name for path in backups.glob("*.tar.gz"))
        assert len(remaining) == 2
        assert remaining[-1].endswith(f"{T0.add_ms(3_000).epoch_ms}.tar.gz")
