"""
Atomic file write utility for tools.

Provides cross-platform atomic file writes with:
- Temp file + rename pattern for atomicity
- Windows retry logic for transient file locking (antivirus, indexer)
- Guaranteed temp file cleanup on failure
- JSON convenience wrapper

Usage:
    from tools.core.atomic_write import atomic_write_text, atomic_write_json

    # Write text atomically
    atomic_write_text(path, content)

    # Write JSON atomically (with proper serialization)
    atomic_write_json(path, data)

Note:
    This is a self-contained copy for tools/ directory.
    Backend has its own copy at backend/puzzle_manager/core/atomic_write.py.
    Do NOT import across boundaries - tools must be self-contained.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("tools.core.atomic_write")

# Default retry configuration for Windows file locking issues
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 0.1  # seconds


def atomic_write_text(
    path: Path,
    content: str,
    *,
    encoding: str = "utf-8",
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> None:
    """Write content to file atomically with cross-platform safety.

    Uses temp file + rename pattern for atomicity. On Windows, retries
    on PermissionError to handle transient file locking by antivirus,
    file indexer, or other processes.

    Always cleans up temp files on failure.

    Args:
        path: Target file path.
        content: Text content to write.
        encoding: File encoding (default: utf-8).
        max_retries: Maximum retry attempts for PermissionError (default: 3).
        retry_delay: Delay between retries in seconds (default: 0.1).

    Raises:
        PermissionError: If file is locked after all retries.
        OSError: If write or rename fails for other reasons.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory for atomic rename
    temp_path = path.with_suffix(path.suffix + ".tmp")

    for attempt in range(max_retries):
        try:
            # Write content to temp file
            temp_path.write_text(content, encoding=encoding)

            # Atomic rename
            try:
                temp_path.replace(path)
            except PermissionError:
                # Windows: target may be locked, try unlink + rename
                if path.exists():
                    path.unlink()
                temp_path.rename(path)

            logger.debug("Atomic write successful: %s", path.name)
            return

        except PermissionError as e:
            # Windows file locking - retry after brief delay
            if attempt < max_retries - 1:
                logger.debug(
                    "PermissionError on %s (attempt %d/%d), retrying...",
                    path.name,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(retry_delay)
                continue

            # Final attempt failed - clean up and raise
            _cleanup_temp(temp_path)
            raise PermissionError(
                f"Cannot write to {path.name}: file locked after {max_retries} retries"
            ) from e

        except Exception:
            # Clean up temp file on any failure
            _cleanup_temp(temp_path)
            raise


def atomic_write_json(
    path: Path,
    data: Any,
    *,
    indent: int | None = 2,
    ensure_ascii: bool = False,
    separators: tuple[str, str] | None = None,
    default: Any = str,
    encoding: str = "utf-8",
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    trailing_newline: bool = True,
) -> None:
    """Write JSON data to file atomically.

    Convenience wrapper around atomic_write_text for JSON serialization.

    Args:
        path: Target file path.
        data: Data to serialize as JSON.
        indent: JSON indentation (default: 2, use None for compact).
        ensure_ascii: If True, escape non-ASCII characters (default: False).
        separators: JSON separators tuple (default: None for standard).
        default: Function for non-serializable objects (default: str).
        encoding: File encoding (default: utf-8).
        max_retries: Maximum retry attempts for PermissionError (default: 3).
        retry_delay: Delay between retries in seconds (default: 0.1).
        trailing_newline: Add trailing newline (default: True, common in tools).

    Raises:
        PermissionError: If file is locked after all retries.
        OSError: If write or rename fails for other reasons.
        TypeError: If data cannot be serialized to JSON.
    """
    content = json.dumps(
        data,
        indent=indent,
        ensure_ascii=ensure_ascii,
        separators=separators,
        default=default,
    )
    if trailing_newline:
        content += "\n"
    atomic_write_text(
        path,
        content,
        encoding=encoding,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def _cleanup_temp(temp_path: Path) -> None:
    """Clean up temp file, ignoring errors."""
    try:
        if temp_path.exists():
            temp_path.unlink()
            logger.debug("Cleaned up temp file: %s", temp_path.name)
    except OSError:
        # Best effort cleanup - don't mask original exception
        pass
