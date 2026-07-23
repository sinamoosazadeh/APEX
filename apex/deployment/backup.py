"""Durable-state backup and verified restore (13.19/13.20; 25.30).

One archive carries everything the platform cannot recompute: the
SQLite stores (copied through sqlite's backup API so a live WAL never
yields a torn file), the encrypted vault and the optimizer artifacts,
each with a SHA256 checksum in an embedded manifest. Restore verifies
EVERY member against the manifest before a single byte lands (25.26)
and refuses to overwrite existing state without ``--force``.
"""

import gzip
import hashlib
import io
import json
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from typing import Final

from apex.core.exceptions import DeploymentError
from apex.core.time.timestamp import Timestamp

BACKUP_MANIFEST: Final[str] = "BACKUP_MANIFEST.json"
BACKUP_PREFIX: Final[str] = "apex-backup-"
_STATE_PREFIX: Final[str] = "state/"
_SKIPPED_SUFFIXES: Final[frozenset[str]] = frozenset({".tmp"})


def _consistent_copy(source: Path, target: Path) -> None:
    """SQLite-consistent copy via the backup API; raw copy otherwise."""
    if source.suffix == ".sqlite":
        origin = sqlite3.connect(source)
        duplicate = sqlite3.connect(target)
        try:
            with duplicate:
                origin.backup(duplicate)
        finally:
            duplicate.close()
            origin.close()
    else:
        shutil.copy2(source, target)


def _collect_state(data_dir: Path) -> list[Path]:
    """Every durable file worth carrying (WAL side files excluded)."""
    files = [
        path
        for path in sorted(data_dir.rglob("*"))
        if path.is_file()
        and not path.name.endswith(("-wal", "-shm"))
        and path.suffix not in _SKIPPED_SUFFIXES
    ]
    if not files:
        raise DeploymentError(
            "nothing to back up under the data directory",
            code="DEP-003",
            details={"data_dir": str(data_dir)},
        )
    return files


def create_backup(
    data_dir: Path,
    backup_dir: Path,
    *,
    created_at: Timestamp,
) -> Path:
    """Write one verified-restorable archive; returns its path."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive_path = backup_dir / f"{BACKUP_PREFIX}{created_at.epoch_ms}.tar.gz"
    entries: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as scratch_name:
        scratch = Path(scratch_name)
        staged: list[tuple[Path, str]] = []
        for source in _collect_state(data_dir):
            relative = source.relative_to(data_dir).as_posix()
            copy = scratch / relative
            copy.parent.mkdir(parents=True, exist_ok=True)
            _consistent_copy(source, copy)
            blob = copy.read_bytes()
            entries.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(blob).hexdigest(),
                    "bytes": len(blob),
                }
            )
            staged.append((copy, relative))
        manifest: dict[str, object] = {
            "created_at_ms": created_at.epoch_ms,
            "total_files": len(entries),
            "files": entries,
        }
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        manifest["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
        _write_archive(archive_path, manifest_bytes, staged, created_at)
    return archive_path


def _write_archive(
    archive_path: Path,
    manifest_bytes: bytes,
    staged: list[tuple[Path, str]],
    created_at: Timestamp,
) -> None:
    mtime = created_at.epoch_ms // 1000

    def normalized(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = info.gid = 0
        info.uname = info.gname = "apex"
        info.mtime = mtime
        return info

    with (
        open(archive_path, "wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        info = tarfile.TarInfo(name=BACKUP_MANIFEST)
        info.size = len(manifest_bytes)
        archive.addfile(normalized(info), io.BytesIO(manifest_bytes))
        for copy, relative in staged:
            entry = archive.gettarinfo(
                str(copy), arcname=f"{_STATE_PREFIX}{relative}"
            )
            with open(copy, "rb") as handle:
                archive.addfile(normalized(entry), handle)


def _read_manifest(archive: tarfile.TarFile) -> dict[str, object]:
    member = archive.extractfile(BACKUP_MANIFEST)
    if member is None:
        raise DeploymentError(
            "backup archive carries no manifest", code="DEP-004", details={}
        )
    loaded = json.loads(member.read().decode("utf-8"))
    if not isinstance(loaded, dict):
        raise DeploymentError(
            "backup manifest is not a mapping", code="DEP-004", details={}
        )
    return loaded


def verify_backup(archive_path: Path) -> tuple[bool, int, str | None]:
    """Recompute every member checksum; (ok, files checked, reason)."""
    with tarfile.open(archive_path, "r:gz") as archive:
        manifest = _read_manifest(archive)
        files = manifest.get("files")
        if not isinstance(files, list):
            return False, 0, "manifest carries no file list"
        checked = 0
        for entry in files:
            if not isinstance(entry, dict):
                return False, checked, "malformed manifest entry"
            relative = str(entry.get("path"))
            member = archive.extractfile(f"{_STATE_PREFIX}{relative}")
            if member is None:
                return False, checked, f"missing member: {relative}"
            digest = hashlib.sha256(member.read()).hexdigest()
            if digest != entry.get("sha256"):
                return False, checked, f"checksum mismatch: {relative}"
            checked += 1
        return True, checked, None


def restore_backup(
    archive_path: Path, target_dir: Path, *, force: bool
) -> int:
    """Verified extraction into the data directory; returns files restored."""
    ok, _checked, reason = verify_backup(archive_path)
    if not ok:
        raise DeploymentError(
            "backup failed verification; nothing restored",
            code="DEP-004",
            details={"archive": archive_path.name, "reason": str(reason)},
        )
    existing = list(target_dir.glob("*.sqlite")) + list(target_dir.glob("*.enc"))
    if existing and not force:
        raise DeploymentError(
            "target already carries durable state; pass --force to overwrite",
            code="DEP-002",
            details={"target": str(target_dir), "files": len(existing)},
        )
    restored = 0
    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.name.startswith(_STATE_PREFIX) or not member.isfile():
                continue
            relative = Path(member.name[len(_STATE_PREFIX) :])
            if relative.is_absolute() or ".." in relative.parts:
                raise DeploymentError(
                    "backup member escapes the target directory",
                    code="DEP-005",
                    details={"member": member.name},
                )
            handle = archive.extractfile(member)
            if handle is None:
                continue
            destination = target_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(handle.read())
            restored += 1
    return restored


def prune_backups(backup_dir: Path, *, keep: int) -> int:
    """Delete the oldest archives beyond the retention count."""
    archives = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*.tar.gz"))
    removed = 0
    for stale in archives[: max(len(archives) - keep, 0)]:
        stale.unlink()
        removed += 1
    return removed
