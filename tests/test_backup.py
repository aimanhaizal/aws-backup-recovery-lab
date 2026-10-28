
import json
from pathlib import Path

import pytest

from src.backup_recovery.backup import create_backup, restore_backup


def test_backup_and_restore_preserves_file_contents(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "records.csv").write_text("id,value\n1,alpha\n2,beta\n")
    (source / "nested").mkdir()
    (source / "nested" / "notes.txt").write_text("Recovery test\n")

    backup_dir = create_backup(source, tmp_path / "backups")

    # Simulate data loss.
    (source / "records.csv").unlink()
    (source / "nested" / "notes.txt").write_text("CORRUPTED\n")

    restored = tmp_path / "restored"
    count = restore_backup(backup_dir, restored)

    assert count == 2
    assert (restored / "records.csv").read_text() == (
        "id,value\n1,alpha\n2,beta\n"
    )
    assert (restored / "nested" / "notes.txt").read_text() == "Recovery test\n"


def test_restore_rejects_missing_manifest(tmp_path: Path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    with pytest.raises(ValueError, match="manifest"):
        restore_backup(backup_dir, tmp_path / "restored")


def test_restore_rejects_corrupted_backup(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "records.csv").write_text("original data\n")

    backup_dir = create_backup(source, tmp_path / "backups")
    (backup_dir / "records.csv").write_text("tampered data\n")

    with pytest.raises(ValueError, match="Checksum verification failed"):
        restore_backup(backup_dir, tmp_path / "restored")


def test_restore_rejects_unsafe_manifest_path(tmp_path: Path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "manifest.json").write_text(
        json.dumps({"files": {"../outside.txt": "0" * 64}})
    )

    with pytest.raises(ValueError, match="Unsafe path"):
        restore_backup(backup_dir, tmp_path / "restored")


def test_recovery_rejects_corrupted_downloaded_backup(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "records.csv").write_text("original data\n")

    backup_dir = create_backup(source, tmp_path / "backups")

    # Simulate corruption after downloading the backup.
    (backup_dir / "records.csv").write_text("tampered data\n")

    restored = tmp_path / "restored"

    with pytest.raises(ValueError, match="Checksum verification failed"):
        restore_backup(backup_dir, restored)

    assert not (restored / "records.csv").exists()
