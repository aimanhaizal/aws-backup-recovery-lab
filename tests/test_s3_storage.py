from unittest.mock import Mock
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.backup_recovery import s3_storage


def test_upload_backup_uploads_files_and_manifest(tmp_path: Path, monkeypatch):
    backup_dir = tmp_path / "20261028T000000000000Z"
    backup_dir.mkdir()
    (backup_dir / "records.csv").write_text("id,value\n1,alpha\n")
    (backup_dir / "manifest.json").write_text(
        json.dumps({"files": {"records.csv": "0" * 64}})
    )

    client = Mock()
    session = Mock()
    session.client.return_value = client
    monkeypatch.setattr(s3_storage.boto3, "Session", Mock(return_value=session))

    count = s3_storage.upload_backup(
        backup_dir,
        "example-backup-bucket",
        "backups",
    )

    assert count == 2
    assert client.upload_file.call_count == 2

    uploaded_keys = {
        call.args[2] for call in client.upload_file.call_args_list
    }
    assert uploaded_keys == {
        f"backups/{backup_dir.name}/manifest.json",
        f"backups/{backup_dir.name}/records.csv",
    }


def test_upload_rejects_missing_manifest(tmp_path: Path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    with pytest.raises(ValueError, match="manifest"):
        s3_storage.upload_backup(backup_dir, "example-backup-bucket")


def test_download_backup_downloads_manifest_and_files(tmp_path: Path, monkeypatch):
    client = Mock()
    client.get_paginator.return_value.paginate.return_value = [
        {
            "Contents": [
                {"Key": "backups/backup-123/manifest.json"},
                {"Key": "backups/backup-123/records.csv"},
            ]
        }
    ]

    client.download_file.side_effect = (
    lambda bucket, key, target: Path(target).write_text("test content")
    )

    session = Mock()
    session.client.return_value = client
    monkeypatch.setattr(s3_storage.boto3, "Session", Mock(return_value=session))

    destination = tmp_path / "downloads"
    backup_dir = s3_storage.download_backup(
        "example-backup-bucket",
        "backup-123",
        destination,
    )

    assert backup_dir == destination.resolve() / "backup-123"
    assert client.download_file.call_count == 2
    assert (backup_dir / "manifest.json").is_file()
    assert (backup_dir / "records.csv").is_file()


def test_download_backup_rejects_missing_s3_backup(tmp_path: Path, monkeypatch):
    client = Mock()
    client.get_paginator.return_value.paginate.return_value = [{}]

    session = Mock()
    session.client.return_value = client
    monkeypatch.setattr(s3_storage.boto3, "Session", Mock(return_value=session))

    with pytest.raises(ValueError, match="No backup objects"):
        s3_storage.download_backup(
            "example-backup-bucket",
            "missing-backup",
            tmp_path / "downloads",
        )
