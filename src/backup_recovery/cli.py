
import argparse
from pathlib import Path

from src.backup_recovery.backup import create_backup, restore_backup


def main():
    parser = argparse.ArgumentParser(
        description="Local backup and recovery utility."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument("--source", required=True, type=Path)
    backup_parser.add_argument("--destination", required=True, type=Path)

    restore_parser = subparsers.add_parser("restore", help="Restore a backup")
    restore_parser.add_argument("--backup", required=True, type=Path)
    restore_parser.add_argument("--destination", required=True, type=Path)

    args = parser.parse_args()

    try:
        if args.command == "backup":
            backup_dir = create_backup(args.source, args.destination)
            print(f"Backup created: {backup_dir}")
        else:
            count = restore_backup(args.backup, args.destination)
            print(f"Restored and verified {count} file(s).")

    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
