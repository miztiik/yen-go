"""
Cleanup module for managing old files.

Implements 45-day retention policy (FR-078).
Spec 107: Collection cleanup consistency (FR-025 to FR-033).
"""

import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.puzzle_manager.audit import write_audit_entry
from backend.puzzle_manager.core.fs_utils import remove_empty_directories
from backend.puzzle_manager.exceptions import CleanupError
from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.paths import (
    get_logs_dir,
    get_output_dir,
    get_pm_raw_dir,
    get_pm_staging_dir,
    get_pm_state_dir,
    rel_path,
)
from backend.puzzle_manager.pm_logging import close_all_file_handlers

logger = logging.getLogger("puzzle_manager.pipeline.cleanup")


# Protected files that should never be deleted by cleanup operations (Spec 052)
# Spec 107: inventory.json now lives in .puzzle-inventory-state/
PROTECTED_FILES: frozenset[str] = frozenset([
    "puzzle-collection-inventory.json",  # Legacy location (backward compat)
    "inventory.json",  # Spec 107: New location
])


@dataclass
class CleanupAuditEntry:
    """Audit entry for collection cleanup operations.

    T051 (Spec 107): Dataclass for cleanup audit records.

    DEPRECATED: Use backend.puzzle_manager.audit.AuditEntry instead.
    Kept for backward compatibility with existing test imports.

    Attributes:
        timestamp: ISO 8601 timestamp of cleanup operation.
        operation: Always "cleanup" for cleanup operations.
        target: The target that was cleaned (e.g., "puzzles-collection").
        files_deleted: Per-category breakdown of deleted file counts.
        paths_cleared: List of paths that were cleared.
    """
    timestamp: str
    operation: str
    target: str
    files_deleted: dict[str, int]
    paths_cleared: list[str]


def count_puzzles_in_dir(sgf_dir: Path) -> int:
    """Count SGF puzzle files in a directory.

    T052 (Spec 107): Count puzzles before cleanup.

    Args:
        sgf_dir: Directory containing SGF files.

    Returns:
        Number of SGF files found.
    """
    if not sgf_dir.exists():
        return 0
    return len(list(sgf_dir.rglob("*.sgf")))


def write_cleanup_audit_entry(
    audit_file: Path,
    target: str,
    files_deleted: dict[str, int],
    paths_cleared: list[str],
) -> None:
    """Write cleanup audit entry to audit log.

    T053 (Spec 107): Write cleanup audit entry after clearing files.

    Args:
        audit_file: Path to audit.jsonl file.
        target: The cleanup target (e.g., "puzzles-collection").
        files_deleted: Per-category breakdown of deleted file counts.
        paths_cleared: List of paths that were cleared.
    """
    write_audit_entry(
        audit_file=audit_file,
        operation="cleanup",
        target=target,
        details={
            "files_deleted": files_deleted,
            "paths_cleared": paths_cleared,
        },
    )


def clear_index_state(output_dir: Path, dry_run: bool = False) -> bool:
    """Clear index state files (DB files and legacy pagination state).

    Removes yengo-search.db, db-version.json, and legacy pagination state.

    Args:
        output_dir: Output directory containing index state.
        dry_run: If True, only report what would be deleted.

    Returns:
        True if any files were deleted (or would be deleted in dry_run).
    """
    cleaned = False

    # Remove legacy views/ pagination state if it exists (backward compat)
    legacy_pagination = output_dir / "views" / ".pagination-state.json"
    if legacy_pagination.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(legacy_pagination)}")
        else:
            legacy_pagination.unlink()
            logger.debug(f"Deleted legacy: {rel_path(legacy_pagination)}")
        cleaned = True

    # Remove yengo-search.db if present
    db_file = output_dir / "yengo-search.db"
    if db_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(db_file)}")
        else:
            db_file.unlink()
            logger.debug(f"Deleted: {rel_path(db_file)}")
        cleaned = True

    # Remove db-version.json if present
    db_version_file = output_dir / "db-version.json"
    if db_version_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(db_version_file)}")
        else:
            db_version_file.unlink()
            logger.debug(f"Deleted: {rel_path(db_version_file)}")
        cleaned = True

    # Remove yengo-content.db if present
    content_db_file = output_dir / "yengo-content.db"
    if content_db_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(content_db_file)}")
        else:
            content_db_file.unlink()
            logger.debug(f"Deleted: {rel_path(content_db_file)}")
        cleaned = True

    return cleaned


def _reset_inventory() -> None:
    """Reset inventory to empty state when collection is cleaned.

    Creates a fresh inventory with all counts at zero.
    """
    try:
        manager = InventoryManager()
        run_id = f"clean-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        inventory = manager.create_empty(run_id)
        manager.save(inventory)
        logger.info("Reset inventory to empty state")
    except Exception as e:
        logger.warning(f"Failed to reset inventory: {e}")


def cleanup_old_files(
    retention_days: int = 45,
    dry_run: bool = False,
) -> dict[str, int]:
    """Clean up files older than retention period.

    Implements FR-078: 45-day retention for logs, state, failed files.
    Also cleans raw/ directory (adapter API responses) per NFR-005.

    Args:
        retention_days: Number of days to retain files (default: 45)
        dry_run: If True, only report what would be deleted

    Returns:
        Dict of category -> count of deleted files
    """
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    counts = {
        "logs": 0,
        "state": 0,
        "failed": 0,
        "raw": 0,
    }

    logger.info(f"Cleanup: retention={retention_days} days, dry_run={dry_run}")

    # Clean logs - close file handlers first on Windows
    try:
        if not dry_run:
            closed = close_all_file_handlers()
            if closed > 0:
                logger.info(f"Closed {closed} log file handlers before cleanup")
        logs_dir = get_logs_dir()
        counts["logs"] = _cleanup_directory(
            logs_dir,
            cutoff,
            patterns=["*.log", "*.log.*"],
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning(f"Log cleanup error: {e}")

    # Clean old state runs
    try:
        state_dir = get_pm_state_dir()
        counts["state"] = _cleanup_directory(
            state_dir / "runs",
            cutoff,
            patterns=["*.json"],
            dry_run=dry_run,
        )
        # Also clean old failure records
        counts["state"] += _cleanup_directory(
            state_dir / "failures",
            cutoff,
            patterns=["*.json"],
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning(f"State cleanup error: {e}")

    # Clean failed files
    try:
        staging_dir = get_pm_staging_dir()
        failed_dir = staging_dir / "failed"
        counts["failed"] = _cleanup_directory(
            failed_dir,
            cutoff,
            patterns=["*.sgf", "*.error"],
            recursive=True,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning(f"Failed files cleanup error: {e}")

    # Clean raw API response files (NFR-005: 45-day retention for raw/)
    try:
        raw_dir = get_pm_raw_dir()
        counts["raw"] = _cleanup_directory(
            raw_dir,
            cutoff,
            patterns=["*.json"],
            recursive=True,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning(f"Raw files cleanup error: {e}")

    logger.info(
        f"Cleanup complete: logs={counts['logs']}, "
        f"state={counts['state']}, failed={counts['failed']}, raw={counts['raw']}"
    )

    return counts


def _cleanup_directory(
    directory: Path,
    cutoff: datetime,
    patterns: list[str],
    recursive: bool = False,
    dry_run: bool = False,
) -> int:
    """Clean up files in a directory matching patterns and older than cutoff.

    Args:
        directory: Directory to clean
        cutoff: Delete files modified before this time
        patterns: Glob patterns to match
        recursive: If True, search recursively
        dry_run: If True, only count files

    Returns:
        Number of files deleted (or would be deleted in dry_run)
    """
    if not directory.exists():
        return 0

    count = 0

    for pattern in patterns:
        if recursive:
            files = directory.rglob(pattern)
        else:
            files = directory.glob(pattern)

        for file_path in files:
            if not file_path.is_file():
                continue

            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, UTC)
                if mtime < cutoff:
                    if dry_run:
                        logger.debug(f"Would delete: {rel_path(file_path)}")
                    else:
                        file_path.unlink()
                        logger.debug(f"Deleted: {rel_path(file_path)}")
                    count += 1
            except Exception as e:
                logger.warning(f"Cannot process {rel_path(file_path)}: {e}")

    return count


def cleanup_empty_directories(base_dir: Path, dry_run: bool = False) -> int:
    """Remove empty directories.

    DEPRECATED: Use core.fs_utils.remove_empty_directories instead.
    This function is kept for backward compatibility.

    Args:
        base_dir: Base directory to start from
        dry_run: If True, only count directories

    Returns:
        Number of directories removed
    """
    return remove_empty_directories(base_dir, dry_run=dry_run)


def reset_staging(confirm: bool = False, dry_run: bool = False) -> bool:
    """Reset staging directory for fresh start.

    WARNING: This deletes all staging data!

    Args:
        confirm: Must be True to actually delete
        dry_run: If True, only report what would be deleted

    Returns:
        True if reset was performed
    """
    if not confirm:
        raise CleanupError("Reset requires confirm=True")

    staging_dir = get_pm_staging_dir()

    if not staging_dir.exists():
        logger.info("Staging directory does not exist")
        return True

    if dry_run:
        logger.info(f"Would delete staging directory: {rel_path(staging_dir)}")
        return True

    try:
        shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Reset staging directory: {rel_path(staging_dir)}")
        return True
    except Exception as e:
        raise CleanupError(f"Failed to reset staging: {e}") from e


def cleanup_target(
    target: str,
    dry_run: bool | None = None,
) -> dict[str, int]:
    """Clean a specific target directory.

    Args:
        target: Target to clean ('staging', 'state', 'logs', 'puzzles-collection')
        dry_run: If True, only report what would be deleted.
            Defaults to True for 'puzzles-collection' (safety), False for others.
            Callers must pass explicit dry_run=False to delete puzzles-collection.

    Returns:
        Dict of category -> count of deleted files
    """
    # Safe default: puzzles-collection requires explicit dry_run=False
    if dry_run is None:
        dry_run = target == "puzzles-collection"

    counts: dict[str, int] = {}

    if target == "staging":
        staging_dir = get_pm_staging_dir()
        counts["staging"] = _clean_all_files(staging_dir, dry_run=dry_run)
    elif target == "state":
        state_dir = get_pm_state_dir()
        counts["state"] = _clean_all_files(state_dir, dry_run=dry_run)
    elif target == "logs":
        # Close file handlers before deleting logs (Windows file locking)
        if not dry_run:
            closed = close_all_file_handlers()
            if closed > 0:
                logger.info(f"Closed {closed} log file handlers before cleanup")
        logs_dir = get_logs_dir()
        counts["logs"] = _clean_all_files(logs_dir, dry_run=dry_run)
    elif target == "puzzles-collection":
        output_dir = get_output_dir()
        ops_dir = output_dir / ".puzzle-inventory-state"

        # T052: Count puzzles before cleanup (for audit entry)
        puzzle_count = count_puzzles_in_dir(output_dir / "sgf")

        # FR-025: Delete all SGF files
        counts["sgf"] = _clean_all_files(output_dir / "sgf", dry_run=dry_run)

        # Delete legacy views/ if it exists (backward compat)
        counts["views"] = _clean_all_files(output_dir / "views", dry_run=dry_run)

        # T054 (FR-028): Clear publish-log/ directory
        counts["publish-log"] = _clean_all_files(
            ops_dir / "publish-log", dry_run=dry_run
        )

        # T055 (FR-030): Clear rollback-backup/ directory
        counts["rollback-backup"] = _clean_all_files(
            ops_dir / "rollback-backup", dry_run=dry_run
        )

        # Clear index state (DB files)
        if clear_index_state(output_dir, dry_run=dry_run):
            counts["index-state"] = 1

        # Clean up empty directories left behind after file deletion
        counts["empty_dirs"] = remove_empty_directories(output_dir, dry_run=dry_run)

        if not dry_run:
            remaining = count_puzzles_in_dir(output_dir / "sgf")

            # T053: Write audit entry FIRST — journal before destructive mutation.
            # If audit write fails, exception propagates and inventory is preserved.
            paths_cleared = [
                "sgf/",
                "yengo-search.db",
                "db-version.json",
                "publish-log/",
                ".rollback-backup/",
                "inventory.json",
            ]
            # Build per-category breakdown (exclude zero counts)
            # Note: puzzle_count is the pre-cleanup *.sgf count (audit metadata),
            # NOT added to counts dict to avoid double-counting with counts["sgf"]
            # which already tracks all files deleted from sgf/.
            files_deleted = {
                k: v for k, v in counts.items() if v > 0
            }
            files_deleted["puzzles-collection"] = puzzle_count
            write_cleanup_audit_entry(
                audit_file=ops_dir / "audit.jsonl",
                target="puzzles-collection",
                files_deleted=files_deleted,
                paths_cleared=paths_cleared,
            )

            # Reset inventory AFTER audit succeeds (Spec 052, FR-027)
            # Only reset if files were actually deleted. If deletion failed
            # (e.g., Windows file locking), resetting inventory creates a
            # state mismatch where inventory says 0 but SGF files exist.
            if remaining == 0:
                _reset_inventory()
            else:
                logger.warning(
                    f"Skipping inventory reset: {remaining} SGF files still exist "
                    f"on disk (expected 0 after cleanup). Run cleanup again or "
                    f"delete files manually, then use 'inventory --reconcile'."
                )

    logger.info(f"Target cleanup complete: {counts}")
    return counts


def _clean_all_files(
    directory: Path,
    dry_run: bool = False,
    exclude_dirs: list[str] | None = None,
) -> int:
    """Delete all files in a directory.

    Args:
        directory: Directory to clean
        dry_run: If True, only count files
        exclude_dirs: List of directory names to exclude from cleanup

    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0

    exclude_dirs = exclude_dirs or []
    count = 0

    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue

        # Skip files in excluded directories
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue

        # Skip protected files (Spec 052 - T043)
        if file_path.name in PROTECTED_FILES:
            logger.debug(f"Skipping protected file: {rel_path(file_path)}")
            continue

        try:
            if dry_run:
                logger.debug(f"Would delete: {rel_path(file_path)}")
            else:
                file_path.unlink()
                logger.debug(f"Deleted: {rel_path(file_path)}")
            count += 1
        except Exception as e:
            logger.warning(f"Cannot delete {rel_path(file_path)}: {e}")

    return count
