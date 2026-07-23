"""Release packaging (Book II 29.25).

Every release carries source, configs, contracts, documentation and
tests with per-file SHA256 checksums, a manifest hash and - when the
security platform holds a signing key - an HMAC signature (25.18).
The archive is byte-deterministic: sorted members, normalized
ownership and timestamps, gzip without embedded mtime - the same tree
and version always produce the same bytes (Constitution determinism).
"""

import gzip
import hashlib
import json
import tarfile
from collections.abc import Callable
from pathlib import Path

from apex.core.exceptions import DeploymentError
from apex.core.time.timestamp import Timestamp

# Directories and files that never enter a release package.
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "runtime",
        "dist",
        "backups",
    }
)
EXCLUDED_SUFFIXES: frozenset[str] = frozenset({".sqlite", ".enc", ".pyc"})


def collect_files(root: Path) -> list[Path]:
    """Every packaged file, sorted by relative path."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if relative.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    if not files:
        raise DeploymentError(
            "nothing to package under the release root",
            code="DEP-001",
            details={"root": str(root)},
        )
    return files


def build_manifest(
    root: Path,
    *,
    version: str,
    created_at: Timestamp,
    signer: Callable[[str], str | None] | None = None,
) -> dict[str, object]:
    """The 29.25 release manifest: files, checksums, hash, signature."""
    entries: list[dict[str, object]] = []
    total_bytes = 0
    for path in collect_files(root):
        blob = path.read_bytes()
        total_bytes += len(blob)
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
            }
        )
    body: dict[str, object] = {
        "name": "apex",
        "version": version,
        "created_at_ms": created_at.epoch_ms,
        "total_files": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    if signer is not None:
        signature = signer(canonical)
        if signature is not None:
            body["signature"] = signature
    return body


def _write_archive(
    root: Path,
    files: list[Path],
    manifest_bytes: bytes,
    archive_path: Path,
    *,
    version: str,
    created_at: Timestamp,
) -> None:
    """A byte-deterministic tar.gz of the release tree + manifest."""
    prefix = f"apex-{version}"
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
        import io

        info = tarfile.TarInfo(name=f"{prefix}/RELEASE_MANIFEST.json")
        info.size = len(manifest_bytes)
        archive.addfile(normalized(info), io.BytesIO(manifest_bytes))
        for path in files:
            arcname = f"{prefix}/{path.relative_to(root).as_posix()}"
            entry = archive.gettarinfo(str(path), arcname=arcname)
            with open(path, "rb") as handle:
                archive.addfile(normalized(entry), handle)


def write_release(
    root: Path,
    dist_dir: Path,
    *,
    version: str,
    created_at: Timestamp,
    signer: Callable[[str], str | None] | None = None,
) -> tuple[Path, Path]:
    """Publish the manifest and archive; returns both paths."""
    manifest = build_manifest(
        root, version=version, created_at=created_at, signer=signer
    )
    dist_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dist_dir / f"apex-{version}.manifest.json"
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
    manifest_path.write_bytes(manifest_bytes)
    archive_path = dist_dir / f"apex-{version}.tar.gz"
    _write_archive(
        root,
        collect_files(root),
        manifest_bytes,
        archive_path,
        version=version,
        created_at=created_at,
    )
    return manifest_path, archive_path
