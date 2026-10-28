
import argparse
from pathlib import Path

from src.backup_recovery.backup import create_backup, restore_backup
from src.backup_recovery.s3_storage import upload_backup, download_backup


def main():
    parser = argparse.ArgumentParser(
        description="Backup and recovery utility with local and S3 support."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a local backup")
    backup_parser.add_argument("--source", required=True, type=Path)
    backup_parser.add_argument("--destination", required=True, type=Path)

    restore_parser = subparsers.add_parser("restore", help="Restore a local backup")
    restore_parser.add_argument("--backup", required=True, type=Path)
    restore_parser.add_argument("--destination", required=True, type=Path)

    upload_parser = subparsers.add_parser("upload", help="Upload a backup to S3")
    upload_parser.add_argument("--backup", required=True, type=Path)
    upload_parser.add_argument("--bucket", required=True)
    upload_parser.add_argument("--prefix", default="backups")

    download_parser = subparsers.add_parser(
        "download", help="Download a backup from S3"
    )
    download_parser.add_argument("--bucket", required=True)
    download_parser.add_argument("--backup-id", required=True)
    download_parser.add_argument("--destination", required=True, type=Path)
    download_parser.add_argument("--prefix", default="backups")

    args = parser.parse_args()

    try:
        if args.command == "backup":
            backup_dir = create_backup(args.source, args.destination)
            print(f"Backup created: {backup_dir}")

        elif args.command == "restore":
            count = restore_backup(args.backup, args.destination)
            print(f"Restored and verified {count} file(s).")

        elif args.command == "upload":
            count = upload_backup(args.backup, args.bucket, args.prefix)
            print(f"Uploaded {count} file(s) to S3.")

        elif args.command == "download":
            backup_dir = download_backup(
                args.bucket,
                args.backup_id,
                args.destination,
                args.prefix,
            )
            print(f"Downloaded backup: {backup_dir}")

    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
