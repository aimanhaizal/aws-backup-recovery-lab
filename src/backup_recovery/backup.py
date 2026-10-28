
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def create_backup(source: Path, backup_root: Path) -> Path:
    """Copy a directory into a timestamped backup with a checksum manifest."""
    source = source.resolve()
    backup_root = backup_root.resolve()

    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")

    if source == backup_root or source in backup_root.parents:
        raise ValueError("Backup destination must not be inside the source.")

    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = backup_root / timestamp
    backup_dir.mkdir()

    try:
        files = sorted(path for path in source.rglob("*") if path.is_file())
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }

        for file_path in files:
            relative_path = file_path.relative_to(source)
            destination = backup_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)

            manifest["files"][relative_path.as_posix()] = sha256_file(destination)

        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        return backup_dir

    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise


def restore_backup(backup_dir: Path, destination: Path) -> int:
    """Restore a backup and verify each restored file against its manifest."""
    backup_dir = backup_dir.resolve()
    destination = destination.resolve()
    manifest_path = backup_dir / "manifest.json"

    if not manifest_path.is_file():
        raise ValueError(f"Backup manifest is missing: {manifest_path}")

    if destination == backup_dir or destination in backup_dir.parents:
        raise ValueError("Restore destination must be separate from the backup.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")

    if not isinstance(files, dict):
        raise ValueError("Backup manifest has an invalid files section.")

    # Validate all manifest paths before writing any files.
    validated: list[tuple[str, str, Path]] = []

    for relative_name, expected_hash in files.items():
        relative = Path(relative_name)

        if (
            relative.is_absolute()
            or not relative.parts
            or ".." in relative.parts
            or relative.as_posix() != relative_name
            or relative_name == "manifest.json"
        ):
            raise ValueError(f"Unsafe path in manifest: {relative_name}")

        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(c not in "0123456789abcdef" for c in expected_hash)
        ):
            raise ValueError(f"Invalid checksum for: {relative_name}")

        source_file = (backup_dir / relative).resolve()

        if backup_dir not in source_file.parents or not source_file.is_file():
            raise ValueError(f"Backup file is missing or unsafe: {relative_name}")

        validated.append((relative_name, expected_hash, relative))


    # Verify every source file before writing any restored files.
    for relative_name, expected_hash, relative in validated:
        if sha256_file(backup_dir / relative) != expected_hash:
            raise ValueError(f"Checksum verification failed: {relative_name}")

    # Only restore after the entire backup passes verification.
    for _, _, relative in validated:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_dir / relative, target)

    return len(validated)