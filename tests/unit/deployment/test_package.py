"""Release packaging: exclusions, checksums, determinism, signature."""

import hashlib
import json
from pathlib import Path

from apex.deployment.package import build_manifest, write_release

from tests.conftest import T0


def make_tree(root: Path) -> None:
    (root / "apex").mkdir(parents=True)
    (root / "apex" / "module.py").write_text("VALUE = 1\n")
    (root / "config").mkdir()
    (root / "config" / "system.yaml").write_text("schema_version: 1\n")
    (root / "runtime").mkdir()
    (root / "runtime" / "bars.sqlite").write_bytes(b"never packaged")
    (root / "vault.enc").write_bytes(b"never packaged either")


class TestPackaging:
    def test_manifest_checksums_and_exclusions(self, tmp_path: Path) -> None:
        make_tree(tmp_path)
        manifest = build_manifest(
            tmp_path,
            version="9.9.9",
            created_at=T0,
            signer=lambda payload: "sig-" + payload[:8],
        )
        files = manifest["files"]
        assert isinstance(files, list)
        paths = {entry["path"] for entry in files if isinstance(entry, dict)}
        assert paths == {"apex/module.py", "config/system.yaml"}
        module = next(
            entry
            for entry in files
            if isinstance(entry, dict) and entry["path"] == "apex/module.py"
        )
        assert module["sha256"] == hashlib.sha256(b"VALUE = 1\n").hexdigest()
        assert isinstance(manifest["sha256"], str)
        assert str(manifest["signature"]).startswith("sig-")

    def test_release_is_byte_deterministic(self, tmp_path: Path) -> None:
        root = tmp_path / "tree"
        make_tree(root)
        manifest_a, archive_a = write_release(
            root, tmp_path / "out-a", version="9.9.9", created_at=T0
        )
        manifest_b, archive_b = write_release(
            root, tmp_path / "out-b", version="9.9.9", created_at=T0
        )
        assert manifest_a.read_bytes() == manifest_b.read_bytes()
        assert archive_a.read_bytes() == archive_b.read_bytes()
        loaded = json.loads(manifest_a.read_text())
        assert loaded["total_files"] == 2
