"""
Cleanup module for managing old files.

Implements 45-day retention policy (FR-078).
Spec 107: Collection cleanup consistency (FR-025 to FR-033).
"""

import gc
import logging
import shutil
import time
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


def _unlink_with_retry(path: Path, attempts: int = 5) -> None:
    """Unlink ``path`` with short backoff between attempts.

    Windows refuses ``unlink()`` with ``WinError 32`` when another handle
    holds the file (a SQLite reader's cache, an editor extension, etc.).
    A ``gc.collect()`` between attempts gives Python finalizers a chance
    to release lingering ``sqlite3.Connection`` objects whose refcount
    has just hit zero.
    """
    delays = (0.05, 0.10, 0.25, 0.50)
    last_err: OSError | None = None
    # First pass: pre-empt finalizer lag — collect once before the first
    # attempt so the common refcount-just-dropped case clears in one shot.
    gc.collect()
    for i in range(attempts):
        try:
            path.unlink()
            return
        except PermissionError as e:
            last_err = e
            gc.collect()
            if i < attempts - 1:
                time.sleep(delays[i])
    assert last_err is not None
    raise last_err


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
            _unlink_with_retry(legacy_pagination)
            logger.debug(f"Deleted legacy: {rel_path(legacy_pagination)}")
        cleaned = True

    # Remove yengo-search.db if present
    db_file = output_dir / "yengo-search.db"
    if db_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(db_file)}")
        else:
            _unlink_with_retry(db_file)
            logger.debug(f"Deleted: {rel_path(db_file)}")
        cleaned = True

    # Remove db-version.json if present
    db_version_file = output_dir / "db-version.json"
    if db_version_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(db_version_file)}")
        else:
            _unlink_with_retry(db_version_file)
            logger.debug(f"Deleted: {rel_path(db_version_file)}")
        cleaned = True

    # Remove yengo-content.db if present
    content_db_file = output_dir / "yengo-content.db"
    if content_db_file.exists():
        if dry_run:
            logger.debug(f"Would delete: {rel_path(content_db_file)}")
        else:
            _unlink_with_retry(content_db_file)
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


def _iter_retention_files(
    directory: Path,
    cutoff: datetime,
    patterns: list[str],
    recursive: bool = False,
):
    """Yield files under ``directory`` matching ``patterns`` whose mtime
    predates ``cutoff``.

    Shared by ``_cleanup_directory`` (which unlinks) and ``preview_clean``
    (which only enumerates). Keeping the scan logic in one place is the
    contract: the preview must list exactly the files the real run would
    delete.
    """
    if not directory.exists():
        return
    for pattern in patterns:
        files = directory.rglob(pattern) if recursive else directory.glob(pattern)
        for fp in files:
            if not fp.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime, UTC)
            except OSError:
                continue
            if mtime < cutoff:
                yield fp


def _iter_all_managed_files(
    directory: Path,
    exclude_dirs: list[str] | None = None,
):
    """Yield every file under ``directory`` that ``_clean_all_files`` would
    unlink. Honours the same protected-files allowlist (Spec 052).
    """
    if not directory.exists():
        return
    exclude = exclude_dirs or []
    for fp in directory.rglob("*"):
        if not fp.is_file():
            continue
        if any(ex in fp.parts for ex in exclude):
            continue
        if fp.name in PROTECTED_FILES:
            continue
        yield fp


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
    count = 0
    for file_path in _iter_retention_files(directory, cutoff, patterns, recursive):
        try:
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
    count = 0
    for file_path in _iter_all_managed_files(directory, exclude_dirs):
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


def _publish_log_iter_old(log_dir: Path, retention_days: int):
    """Yield publish-log files older than the retention cutoff.

    Mirrors ``PublishLogReader.cleanup_old_logs`` selection logic exactly:
    skips audit logs (FR-052) and any non-date-formatted filename. Living
    in cleanup.py rather than publish_log.py avoids a circular dep —
    cleanup.py already imports publish_log indirectly.
    """
    if not log_dir.exists():
        return
    cutoff_str = (
        datetime.now(UTC) - timedelta(days=retention_days)
    ).strftime("%Y-%m-%d")
    for path in log_dir.glob("*.jsonl"):
        if path.name in ("audit.jsonl", "rollback-audit.jsonl"):
            continue
        date_str = path.stem
        if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
            continue
        if date_str < cutoff_str:
            yield path


def _to_preview_item(path: Path) -> tuple[str, int] | None:
    """Convert an absolute Path to (rel_posix_path, byte_size).

    Returns None if the file vanished between scan and stat (e.g., a
    parallel cleanup beat us to it). The caller treats None as "skip".
    """
    try:
        size = path.stat().st_size
    except OSError:
        return None
    posix = Path(rel_path(path)).as_posix()
    return posix, size


def preview_clean(
    target: str | None = None,
    retention_days: int = 45,
) -> tuple[list[tuple[str, int]], list[str]]:
    """Enumerate files that ``clean`` would delete, without deleting.

    Mirrors ``cleanup_target`` and ``cleanup_old_files`` scan logic via
    the shared iterators above — the preview must list exactly the same
    files the real run would unlink (modulo races).

    Args:
        target: Same semantics as ``cleanup_target.target`` (or None to
            mirror ``cleanup_old_files``).
        retention_days: Same semantics as the CLI ``--retention-days``.

    Returns:
        ``(items, errors)`` where each item is ``(relative_posix_path,
        byte_size)`` and ``errors`` lists non-fatal scan warnings (e.g.,
        a directory the scanner could not stat).
    """
    items: list[tuple[str, int]] = []
    errors: list[str] = []
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    def _collect(iter_paths) -> None:
        for p in iter_paths:
            entry = _to_preview_item(p)
            if entry is not None:
                items.append(entry)

    if target is None:
        # Retention-based default — mirrors cleanup_old_files()
        _collect(_iter_retention_files(
            get_logs_dir(), cutoff, ["*.log", "*.log.*"]
        ))
        state_dir = get_pm_state_dir()
        _collect(_iter_retention_files(
            state_dir / "runs", cutoff, ["*.json"]
        ))
        _collect(_iter_retention_files(
            state_dir / "failures", cutoff, ["*.json"]
        ))
        _collect(_iter_retention_files(
            get_pm_staging_dir() / "failed", cutoff, ["*.sgf", "*.error"],
            recursive=True,
        ))
        _collect(_iter_retention_files(
            get_pm_raw_dir(), cutoff, ["*.json"], recursive=True,
        ))
    elif target == "staging":
        _collect(_iter_all_managed_files(get_pm_staging_dir()))
    elif target == "state":
        _collect(_iter_all_managed_files(get_pm_state_dir()))
    elif target == "logs":
        _collect(_iter_all_managed_files(get_logs_dir()))
    elif target == "puzzles-collection":
        output_dir = get_output_dir()
        ops_dir = output_dir / ".puzzle-inventory-state"
        _collect(_iter_all_managed_files(output_dir / "sgf"))
        _collect(_iter_all_managed_files(output_dir / "views"))
        _collect(_iter_all_managed_files(ops_dir / "publish-log"))
        _collect(_iter_all_managed_files(ops_dir / "rollback-backup"))
        for db_name in (
            "yengo-search.db",
            "db-version.json",
            "yengo-content.db",
        ):
            db_path = output_dir / db_name
            if db_path.exists():
                entry = _to_preview_item(db_path)
                if entry is not None:
                    items.append(entry)
        legacy_pagination = output_dir / "views" / ".pagination-state.json"
        if legacy_pagination.exists():
            entry = _to_preview_item(legacy_pagination)
            if entry is not None:
                items.append(entry)
    elif target == "publish-logs":
        from backend.puzzle_manager.paths import get_publish_log_dir
        _collect(_publish_log_iter_old(
            get_publish_log_dir(), retention_days,
        ))
    else:
        errors.append(f"Unknown target: {target}")

    return items, errors
