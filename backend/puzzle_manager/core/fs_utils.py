"""File system utilities for puzzle manager.

Provides shared file operations used by cleanup, rollback, and other modules.
Follows the core utility pattern established by datetime_utils.py, naming.py, etc.

Usage:
    from backend.puzzle_manager.core.fs_utils import (
        remove_empty_directories,
        cleanup_processed_files,
        extract_level_from_path,
    )

    # Remove empty directories after file deletion
    count = remove_empty_directories(base_dir)

    # Clean up processed files from staging
    deleted = cleanup_processed_files(processed_files, logger)

    # Extract level from SGF path
    level = extract_level_from_path("sgf/beginner/batch-0001/abc.sgf")
"""

import logging
from pathlib import Path

from backend.puzzle_manager.core.constants import VALID_LEVEL_SLUGS
from backend.puzzle_manager.paths import rel_path

logger = logging.getLogger("puzzle_manager.core.fs_utils")


def remove_empty_directories(
    base_dir: Path,
    dry_run: bool = False,
) -> int:
    """Remove empty directories bottom-up.

    Safely removes only directories that are confirmed empty.
    Walks the directory tree bottom-up to handle nested empty directories.

    Args:
        base_dir: Base directory to start from (not deleted itself)
        dry_run: If True, only count directories without deleting

    Returns:
        Number of directories removed (or would be removed in dry_run)

    Note:
        - Only removes directories that are EMPTY (no files or subdirs)
        - Uses bottom-up traversal to handle nested empty dirs
        - Logs warnings for permission errors but continues
        - The base_dir itself is never removed

    Example:
        >>> # After deleting files from sgf/beginner/batch-0001/
        >>> removed = remove_empty_directories(Path("sgf/beginner"))
        >>> print(f"Cleaned up {removed} empty directories")
    """
    if not base_dir.exists():
        return 0

    if not base_dir.is_dir():
        logger.warning(f"Not a directory: {rel_path(base_dir)}")
        return 0

    count = 0

    # Walk bottom-up (reverse sorted) to handle nested empty directories
    # This ensures child directories are processed before parents
    try:
        all_dirs = sorted(base_dir.rglob("*"), reverse=True)
    except PermissionError as e:
        logger.warning(f"Permission denied scanning {rel_path(base_dir)}: {e}")
        return 0

    for dirpath in all_dirs:
        if not dirpath.is_dir():
            continue

        # Skip the base directory itself
        if dirpath == base_dir:
            continue

        try:
            # Check if directory is empty
            # any() returns False for empty iterator, so `not any()` means empty
            if not any(dirpath.iterdir()):
                if dry_run:
                    logger.debug(f"Would remove empty dir: {rel_path(dirpath)}")
                else:
                    dirpath.rmdir()
                    logger.debug(f"Removed empty dir: {rel_path(dirpath)}")
                count += 1
        except PermissionError as e:
            logger.warning(f"Permission denied removing {rel_path(dirpath)}: {e}")
        except OSError as e:
            # Directory might have been removed by another process
            # or might not be empty anymore (race condition)
            logger.warning(f"Cannot remove {rel_path(dirpath)}: {e}")

    if count > 0:
        action = "Would remove" if dry_run else "Removed"
        logger.info(f"{action} {count} empty directories under {rel_path(base_dir)}")

    return count


def is_directory_empty(dir_path: Path) -> bool:
    """Check if a directory is empty.

    Args:
        dir_path: Path to directory to check

    Returns:
        True if directory exists and is empty, False otherwise
    """
    if not dir_path.exists():
        return False

    if not dir_path.is_dir():
        return False

    return not any(dir_path.iterdir())


def cleanup_processed_files(
    processed_files: list[Path],
    stage_logger: logging.Logger | None = None,
) -> int:
    """Delete processed files from staging directories.

    Used by analyze and publish stages to clean up after successful processing.
    Logs warnings for failures but continues processing remaining files.

    Args:
        processed_files: List of file paths to delete.
        stage_logger: Optional logger for output (uses module logger if None).

    Returns:
        Number of files successfully deleted.

    Example:
        >>> deleted = cleanup_processed_files(processed_files)
        >>> logger.info(f"Cleanup: deleted {deleted} files")
    """
    log = stage_logger or logger
    deleted = 0

    for file_path in processed_files:
        try:
            if file_path.exists():
                file_path.unlink()
                deleted += 1
        except OSError as e:
            log.warning(f"Failed to delete {file_path.name}: {e}")

    return deleted


def extract_level_from_path(path: str) -> str | None:
    """Extract puzzle level from SGF file path (legacy format only).

    Legacy path format: sgf/{level}/batch-NNNN/{puzzle_id}.sgf
    New flat format: sgf/{NNNN}/{puzzle_id}.sgf (level NOT in path)

    In the new flat format, the level is stored in the SGF file's YG property
    and in view index entries (l field), not in the directory path.
    This function only works for legacy paths.

    Args:
        path: Relative path to SGF file (POSIX format with forward slashes).

    Returns:
        Level slug (e.g., 'beginner', 'intermediate') or None if not extractable
        or not a valid level slug.

    Example:
        >>> extract_level_from_path("sgf/beginner/batch-0001/abc.sgf")
        'beginner'
        >>> extract_level_from_path("sgf/0001/abc.sgf")
        None
        >>> extract_level_from_path("invalid/path")
        None
    """
    parts = path.split("/")
    # Expected: ['sgf', '{level}', 'batch-NNNN', '{puzzle_id}.sgf']
    if len(parts) >= 2 and parts[0] == "sgf":
        candidate = parts[1]
        # Validate against known level slugs
        if candidate in VALID_LEVEL_SLUGS:
            return candidate
        logger.debug("Invalid level in path: %s (got '%s')", path, candidate)
    return None
