#!/usr/bin/env python3
"""
Batch SGF files into subdirectories.

Organizes SGF files into batch-001, batch-002, etc. subdirectories
with configurable batch size (default 500 files per batch).

Files are sorted numerically by filename (e.g., 191.sgf < 1623.sgf < 10107.sgf).
"""

import argparse
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: Path, dry_run: bool) -> logging.Logger:
    """Set up logging with timestamped filename and immediate flush."""
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_dryrun" if dry_run else ""
    log_file = log_dir / f"{timestamp}_batch_sgf{suffix}.log"

    logger = logging.getLogger("batch_sgf")
    logger.setLevel(logging.INFO)

    # Custom handler that flushes after every write for real-time monitoring
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record: logging.LogRecord) -> None:
            super().emit(record)
            self.flush()

    # File handler with immediate flush
    file_handler = FlushingFileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    logger.info(f"Log file: {log_file}")
    return logger


def extract_number(filename: str) -> int:
    """Extract numeric portion from filename for sorting."""
    match = re.match(r"(\d+)", filename)
    return int(match.group(1)) if match else 0


def batch_sgf_files(
    target_dir: Path,
    batch_size: int,
    dry_run: bool,
    logger: logging.Logger,
) -> dict:
    """
    Organize SGF files into batch subdirectories.

    Returns:
        dict with stats: {total_files, batches_created, files_moved}
    """
    # Find all SGF files (not in batch directories)
    sgf_files = [
        f for f in target_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".sgf"
    ]

    if not sgf_files:
        logger.warning(f"No SGF files found in {target_dir}")
        return {"total_files": 0, "batches_created": 0, "files_moved": 0}

    # Sort numerically by filename
    sgf_files.sort(key=lambda f: extract_number(f.name))

    total_files = len(sgf_files)
    batches_needed = (total_files + batch_size - 1) // batch_size  # Ceiling division

    logger.info(f"Directory: {target_dir}")
    logger.info(f"Found {total_files} SGF files")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Batches needed: {batches_needed}")

    files_moved = 0

    for batch_num in range(1, batches_needed + 1):
        batch_dir = target_dir / f"batch-{batch_num:03d}"

        # Get files for this batch
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(batch_num * batch_size, total_files)
        batch_files = sgf_files[start_idx:end_idx]

        if dry_run:
            logger.info(f"[DRY-RUN] Would create: {batch_dir}")
            logger.info(f"[DRY-RUN] Would move {len(batch_files)} files ({batch_files[0].name} ... {batch_files[-1].name})")
        else:
            batch_dir.mkdir(exist_ok=True)
            for f in batch_files:
                shutil.move(str(f), str(batch_dir / f.name))
                files_moved += 1
            logger.info(f"Created {batch_dir.name}: {len(batch_files)} files ({batch_files[0].name} ... {batch_files[-1].name})")

    return {
        "total_files": total_files,
        "batches_created": batches_needed,
        "files_moved": files_moved if not dry_run else 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Batch SGF files into subdirectories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run on one directory
  python batch_sgf_files.py --path ../../external-sources/ambak-tsumego/problems/intermediate --dry-run

  # Batch with default 500 files per batch
  python batch_sgf_files.py --path ../../external-sources/ambak-tsumego/problems/intermediate

  # Custom batch size
  python batch_sgf_files.py --path ./my-sgf-folder --batch-size 100
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Directory containing SGF files to batch",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Maximum files per batch directory (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without moving files",
    )

    args = parser.parse_args()

    # Resolve path relative to current working directory
    target_dir = args.path.resolve()

    if not target_dir.exists():
        print(f"Error: Directory not found: {target_dir}")
        return 1

    if not target_dir.is_dir():
        print(f"Error: Not a directory: {target_dir}")
        return 1

    # Log directory is relative to script location
    script_dir = Path(__file__).parent
    log_dir = script_dir / "logs"

    logger = setup_logging(log_dir, args.dry_run)

    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")

    stats = batch_sgf_files(target_dir, args.batch_size, args.dry_run, logger)

    logger.info("---")
    logger.info(f"Summary: {stats['total_files']} files -> {stats['batches_created']} batches")
    if not args.dry_run:
        logger.info(f"Files moved: {stats['files_moved']}")

    return 0


if __name__ == "__main__":
    exit(main())
