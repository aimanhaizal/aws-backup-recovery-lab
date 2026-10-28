
from pathlib import Path, PurePosixPath

import boto3


def upload_backup(backup_dir: Path, bucket: str, prefix: str = "backups") -> int:
    """Upload a backup directory, including its manifest, to S3."""
    backup_dir = backup_dir.resolve()
    manifest = backup_dir / "manifest.json"

    if not backup_dir.is_dir() or not manifest.is_file():
        raise ValueError("Backup directory or manifest is missing.")

    s3 = boto3.Session().client("s3")
    uploaded = 0

    for path in sorted(backup_dir.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(backup_dir).as_posix()
        key = str(PurePosixPath(prefix) / backup_dir.name / relative)

        s3.upload_file(str(path), bucket, key)
        uploaded += 1

    return uploaded


def download_backup(
    bucket: str,
    backup_id: str,
    destination: Path,
    prefix: str = "backups",
) -> Path:
    """Download a backup from S3 into a new local directory."""
    if (
        not backup_id
        or "/" in backup_id
        or "\\" in backup_id
        or backup_id in {".", ".."}
    ):
        raise ValueError("Invalid backup ID.")

    destination = destination.resolve()
    backup_dir = destination / backup_id

    if backup_dir.exists():
        raise ValueError(f"Download destination already exists: {backup_dir}")

    s3 = boto3.Session().client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    object_prefix = str(PurePosixPath(prefix) / backup_id) + "/"

    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=object_prefix):
        keys.extend(
            item["Key"]
            for item in page.get("Contents", [])
            if item["Key"] != object_prefix
        )

    if not keys:
        raise ValueError(f"No backup objects found for: {backup_id}")

    try:
        backup_dir.mkdir(parents=True)

        for key in keys:
            relative_key = key[len(object_prefix):]
            relative = PurePosixPath(relative_key)

            if (
                relative.is_absolute()
                or not relative.parts
                or ".." in relative.parts
                or "\\" in relative_key
            ):
                raise ValueError(f"Unsafe S3 object key: {key}")

            target = backup_dir.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(target))

        if not (backup_dir / "manifest.json").is_file():
            raise ValueError("Downloaded backup is missing its manifest.")

        return backup_dir

    except Exception:
        import shutil
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise
