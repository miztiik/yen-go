"""
Batching utilities for organizing files into subdirectories.

Organizes files into batch directories (batch-001, batch-002, etc.)
with configurable size limits. Used by all download tools.

Features:
- O(1) fast path for high-throughput ingestion (get_batch_for_file_fast)
- O(N) fallback with filesystem scan (get_batch_for_file)
- Schema versioning with migration support
- Crash recovery via state reconstruction from filesystem
- Comprehensive edge case handling

Usage:
    from tools.core.batching import get_batch_for_file, BatchInfo, count_total_files

    # Get next batch directory for saving a file
    batch_dir = get_batch_for_file(sgf_dir, batch_size=1000)

    # Get batch info
    batch = get_current_batch(sgf_dir, batch_size=1000)
    print(f"Current batch: {batch.name}, files: {batch.file_count}")

    # Fast O(1) path with state tracking
    state = BatchState.load(sgf_dir) or BatchState()
    batch_dir, batch_num = get_batch_for_file_fast(
        sgf_dir, state.current_batch, state.files_in_current_batch, batch_size=500
    )
    # After file save:
    state.record_file_saved(batch_size=500)
    state.save(sgf_dir)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from tools.core.atomic_write import atomic_write_json

logger = logging.getLogger("tools.core.batching")


# ==============================
# Pydantic Configuration Models
# ==============================

class BatchConfig(BaseModel):
    """Batch processing configuration with validation.

    Provides validated configuration for batch operations with sensible defaults.

    Attributes:
        size: Items to process per batch operation.
        max_files_per_dir: Maximum files allowed in a single batch directory.

    Usage:
        config = BatchConfig(size=500, max_files_per_dir=1000)
        writer = BatchWriter(sgf_root, config=config)
    """

    size: int = Field(100, ge=1, le=10000, description="Items per batch operation")
    max_files_per_dir: int = Field(1000, ge=1, le=10000, description="Max files per directory")


# Default batch size - max files per directory
DEFAULT_BATCH_SIZE = 1000

# Schema versioning for forward/backward compatibility
# Version history:
#   1: Initial schema - current_batch, files_in_current_batch
#   2: Added last_error, retry_count, recovery_timestamp
BATCH_STATE_SCHEMA_VERSION = 2

# State file name
BATCH_STATE_FILENAME = ".batch-state.json"


@dataclass
class BatchInfo:
    """Information about a batch directory."""

    path: Path
    batch_number: int
    file_count: int

    @property
    def name(self) -> str:
        """Return batch directory name (e.g., 'batch-001')."""
        return f"batch-{self.batch_number:03d}"

    def is_full(self, max_size: int = DEFAULT_BATCH_SIZE) -> bool:
        """Check if batch has reached max size."""
        return self.file_count >= max_size


@dataclass
class BatchState:
    """Persistent batch tracking state with schema evolution support.

    Provides O(1) batch tracking without filesystem scanning.
    Supports crash recovery via filesystem reconstruction.

    Schema Evolution:
        v1: current_batch, files_in_current_batch
        v2: Added last_error, retry_count, recovery_timestamp

    Usage:
        state = BatchState.load(sgf_dir) or BatchState()
        batch_dir, batch_num = get_batch_for_file_fast(
            sgf_dir, state.current_batch, state.files_in_current_batch
        )
        state.record_file_saved(batch_size=500)
        state.save(sgf_dir)
    """

    schema_version: int = BATCH_STATE_SCHEMA_VERSION
    current_batch: int = 1
    files_in_current_batch: int = 0
    last_updated: str = ""
    # v2 fields
    last_error: str | None = None
    retry_count: int = 0
    recovery_timestamp: str | None = None

    def record_file_saved(self, batch_size: int) -> None:
        """Record a successful file save and update batch tracking.

        MUST be called AFTER file is successfully written to disk.
        Handles batch advancement when current batch becomes full.

        Args:
            batch_size: Maximum files per batch (needed for advancement check)

        Edge cases:
        - files_in_current_batch=0 → 1 (first file)
        - files_in_current_batch=499 → 500 (last slot in batch)
        - files_in_current_batch=500 → advance to next batch, reset to 1
        """
        self.files_in_current_batch += 1
        self.last_error = None  # Clear error on success
        self.retry_count = 0

        # Check if we just filled the batch and need to advance
        if self.files_in_current_batch >= batch_size:
            self.current_batch += 1
            self.files_in_current_batch = 0

    def record_error(self, error: str) -> None:
        """Record an error for debugging and retry tracking."""
        self.last_error = error
        self.retry_count += 1

    def get_batch_state(self) -> tuple[int, int]:
        """Return current batch tracking state.

        Returns:
            Tuple of (current_batch, files_in_current_batch)
        """
        return self.current_batch, self.files_in_current_batch

    def _update_timestamp(self) -> None:
        """Update last_updated to now."""
        self.last_updated = datetime.now(UTC).isoformat()

    def save(self, parent_dir: Path, filename: str = BATCH_STATE_FILENAME) -> None:
        """Save batch state atomically using atomic_write_json.

        Uses atomic_write_json for cross-platform safety with Windows
        retry logic and guaranteed temp file cleanup.

        Args:
            parent_dir: Directory to save state file.
            filename: State filename (default: .batch-state.json).
        """
        self._update_timestamp()
        state_path = parent_dir / filename

        # Atomic write with cross-platform safety
        atomic_write_json(state_path, asdict(self))
        logger.debug(f"Saved batch state to {state_path.name}")

    @classmethod
    def load(
        cls,
        parent_dir: Path,
        filename: str = BATCH_STATE_FILENAME,
    ) -> BatchState | None:
        """Load batch state from file with schema migration.

        Handles corrupted files by deleting and returning None.
        Performs automatic schema migration for older versions.

        Args:
            parent_dir: Directory containing state file.
            filename: State filename (default: .batch-state.json).

        Returns:
            BatchState instance or None if not found/corrupted.
        """
        state_path = parent_dir / filename

        if not state_path.exists():
            return None

        try:
            content = state_path.read_text(encoding="utf-8")
            if not content.strip():
                logger.warning(f"Empty batch state file, deleting: {state_path}")
                state_path.unlink()
                return None

            data = json.loads(content)

            if not isinstance(data, dict):
                logger.warning(f"Invalid batch state format, deleting: {state_path}")
                state_path.unlink()
                return None

            # Schema migration
            schema_version = data.get("schema_version", 1)
            if schema_version < BATCH_STATE_SCHEMA_VERSION:
                logger.info(
                    f"Migrating batch state from v{schema_version} to v{BATCH_STATE_SCHEMA_VERSION}"
                )
                data = cls._migrate_schema(data, schema_version)

            # Create instance, filtering to valid fields only
            valid_fields = {"schema_version", "current_batch", "files_in_current_batch",
                          "last_updated", "last_error", "retry_count", "recovery_timestamp"}
            filtered = {k: v for k, v in data.items() if k in valid_fields}

            state = cls(**filtered)
            logger.debug(f"Loaded batch state: batch {state.current_batch}, files {state.files_in_current_batch}")
            return state

        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted batch state JSON ({e}), deleting: {state_path}")
            state_path.unlink()
            return None
        except (TypeError, KeyError) as e:
            logger.warning(f"Invalid batch state structure ({e}), deleting: {state_path}")
            state_path.unlink()
            return None

    @classmethod
    def _migrate_schema(cls, data: dict, from_version: int) -> dict:
        """Migrate schema from older versions.

        Args:
            data: Raw data dict from older schema.
            from_version: Version to migrate from.

        Returns:
            Migrated data dict.
        """
        # v1 -> v2: Add new fields with defaults
        if from_version < 2:
            data["schema_version"] = 2
            data.setdefault("last_error", None)
            data.setdefault("retry_count", 0)
            data.setdefault("recovery_timestamp", None)

        return data

    @classmethod
    def recover_from_filesystem(
        cls,
        parent_dir: Path,
        file_pattern: str = "*.sgf",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> BatchState:
        """Recover batch state by scanning filesystem.

        Use this after a crash or when state file is lost/corrupted.
        Scans all batch directories to reconstruct state.

        Args:
            parent_dir: Parent directory containing batch dirs.
            file_pattern: Pattern to count files (default: *.sgf).
            batch_size: Expected batch size for determining current batch.

        Returns:
            Recovered BatchState matching filesystem reality.
        """
        logger.info(f"Recovering batch state from filesystem: {parent_dir}")

        batches = find_existing_batches(parent_dir, file_pattern)

        if not batches:
            logger.info("No batches found, starting fresh")
            return cls(
                current_batch=1,
                files_in_current_batch=0,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )

        # Find the current batch (last non-full or next after full)
        last_batch = batches[-1]

        if last_batch.file_count >= batch_size:
            # Last batch is full, next file goes to new batch
            state = cls(
                current_batch=last_batch.batch_number + 1,
                files_in_current_batch=0,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )
        else:
            # Last batch has room
            state = cls(
                current_batch=last_batch.batch_number,
                files_in_current_batch=last_batch.file_count,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )

        total_files = sum(b.file_count for b in batches)
        logger.info(
            f"Recovered state: batch {state.current_batch}, "
            f"{state.files_in_current_batch} files in current, "
            f"{total_files} total across {len(batches)} batches"
        )

        return state

    @classmethod
    def load_or_recover(
        cls,
        parent_dir: Path,
        file_pattern: str = "*.sgf",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> BatchState:
        """Load state from file, or recover from filesystem if missing/corrupted.

        This is the recommended entry point for crash-safe batch tracking.

        Args:
            parent_dir: Parent directory for batch dirs and state file.
            file_pattern: Pattern to count files during recovery.
            batch_size: Expected batch size.

        Returns:
            BatchState from file or recovered from filesystem.
        """
        state = cls.load(parent_dir)
        if state is not None:
            return state

        # No valid state file - recover from filesystem
        return cls.recover_from_filesystem(parent_dir, file_pattern, batch_size)

    def validate_against_filesystem(
        self,
        parent_dir: Path,
        file_pattern: str = "*.sgf",
    ) -> bool:
        """Check if state matches filesystem reality.

        Detects state drift that could cause issues.

        Args:
            parent_dir: Parent directory for batch dirs.
            file_pattern: Pattern to count files.

        Returns:
            True if state is consistent with filesystem.
        """
        batch_dir = parent_dir / f"batch-{self.current_batch:03d}"

        if not batch_dir.exists():
            # Directory doesn't exist - state says it should
            if self.files_in_current_batch > 0:
                logger.warning(
                    f"State says {self.files_in_current_batch} files in batch-{self.current_batch:03d}, "
                    f"but directory doesn't exist"
                )
                return False
            return True  # 0 files, no dir = consistent

        actual_count = len(list(batch_dir.glob(file_pattern)))
        if actual_count != self.files_in_current_batch:
            logger.warning(
                f"State says {self.files_in_current_batch} files in batch-{self.current_batch:03d}, "
                f"but found {actual_count}"
            )
            return False

        return True


def get_batch_dir_number(path: Path) -> int | None:
    """Extract batch number from directory name.

    Args:
        path: Directory path (e.g., /path/to/batch-001)

    Returns:
        Batch number (e.g., 1) or None if not a batch dir.
    """
    match = re.match(r"batch-(\d+)$", path.name)
    return int(match.group(1)) if match else None


def find_existing_batches(parent_dir: Path, file_pattern: str = "*.sgf") -> list[BatchInfo]:
    """Find all existing batch directories.

    Args:
        parent_dir: Parent directory to search.
        file_pattern: Pattern for counting files (default: *.sgf).

    Returns:
        List of BatchInfo sorted by batch number.
    """
    if not parent_dir.exists():
        return []

    batches = []
    for child in parent_dir.iterdir():
        if child.is_dir():
            batch_num = get_batch_dir_number(child)
            if batch_num is not None:
                file_count = len(list(child.glob(file_pattern)))
                batches.append(BatchInfo(
                    path=child,
                    batch_number=batch_num,
                    file_count=file_count,
                ))

    # Sort by batch number
    batches.sort(key=lambda b: b.batch_number)
    return batches


def get_current_batch(
    parent_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    file_pattern: str = "*.sgf",
) -> BatchInfo:
    """Get the current batch directory (last non-full batch or new one).

    Args:
        parent_dir: Parent directory for batch dirs.
        batch_size: Maximum files per batch.
        file_pattern: Pattern for counting files (default: *.sgf).

    Returns:
        BatchInfo for the current batch directory.
    """
    batches = find_existing_batches(parent_dir, file_pattern)

    if not batches:
        # No batches exist, create first one
        batch_path = parent_dir / "batch-001"
        batch_path.mkdir(parents=True, exist_ok=True)
        return BatchInfo(path=batch_path, batch_number=1, file_count=0)

    # Check if last batch is full
    last_batch = batches[-1]
    if last_batch.is_full(batch_size):
        # Create new batch
        new_num = last_batch.batch_number + 1
        batch_path = parent_dir / f"batch-{new_num:03d}"
        batch_path.mkdir(parents=True, exist_ok=True)
        return BatchInfo(path=batch_path, batch_number=new_num, file_count=0)

    return last_batch


def get_batch_for_file(
    parent_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    file_pattern: str = "*.sgf",
) -> Path:
    """Get the directory path where the next file should be saved.

    Creates the directory if it doesn't exist.

    NOTE: This scans the filesystem on every call (O(N) where N = total files).
    For high-volume downloads, use get_batch_for_file_fast() with checkpoint.

    Args:
        parent_dir: Parent directory for batch dirs.
        batch_size: Maximum files per batch.
        file_pattern: Pattern for counting files (default: *.sgf).

    Returns:
        Path to the batch directory for the next file.
    """
    batch = get_current_batch(parent_dir, batch_size, file_pattern)
    return batch.path


def get_batch_for_file_fast(
    parent_dir: Path,
    current_batch: int,
    files_in_current_batch: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[Path, int]:
    """Get batch directory using in-memory state (O(1), no filesystem scan).

    Uses provided batch tracking state to determine the correct batch directory
    without scanning the filesystem. This is much faster for high-volume downloads.

    IMPORTANT: This function is READ-ONLY. The caller must track state updates
    after successful file saves.

    Edge cases handled:
    - files_in_current_batch=0: Returns current batch (batch-001 on first run)
    - files_in_current_batch=499: Returns current batch (room for 1 more)
    - files_in_current_batch=500: Returns NEXT batch (current is full)
    - current_batch=10: Returns batch-010 (3-digit zero-padded)

    Args:
        parent_dir: Parent directory for batch dirs
        current_batch: Current batch number (1-indexed)
        files_in_current_batch: Files already in current batch
        batch_size: Maximum files per batch (default 1000)

    Returns:
        Tuple of (batch directory path, batch number to use)
    """
    # Determine which batch to use based on current count
    # If current batch is full (>= batch_size), use next batch number
    if files_in_current_batch >= batch_size:
        batch_num = current_batch + 1
    else:
        batch_num = current_batch

    batch_dir = parent_dir / f"batch-{batch_num:03d}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    return batch_dir, batch_num


def count_total_files(parent_dir: Path, file_pattern: str = "*.sgf") -> int:
    """Count total files across all batches.

    Args:
        parent_dir: Parent directory for batch dirs.
        file_pattern: Pattern for counting files (default: *.sgf).

    Returns:
        Total count of matching files.
    """
    if not parent_dir.exists():
        return 0

    count = 0
    for batch_dir in parent_dir.iterdir():
        if batch_dir.is_dir() and batch_dir.name.startswith("batch-"):
            count += len(list(batch_dir.glob(file_pattern)))

    return count


def get_batch_summary(parent_dir: Path, file_pattern: str = "*.sgf") -> dict:
    """Get summary statistics for all batches.

    Args:
        parent_dir: Parent directory for batch dirs.
        file_pattern: Pattern for counting files (default: *.sgf).

    Returns:
        Dictionary with batch statistics.
    """
    batches = find_existing_batches(parent_dir, file_pattern)

    return {
        "batch_count": len(batches),
        "total_files": sum(b.file_count for b in batches),
        "batches": [
            {"number": b.batch_number, "files": b.file_count}
            for b in batches
        ],
    }


# ==============================
# BatchWriter Class (OOP API)
# ==============================

class BatchWriter:
    """Batch directory manager with OOP interface.

    Provides both O(1) fast path (with state tracking) and O(N) fallback
    (with filesystem scan) for batch directory resolution.

    Supports optional hierarchical path structure:
        {root}/{category}/{year}/{month}/batch-{NNN}/

    Usage:
        # Simple usage (flat structure)
        writer = BatchWriter(output_dir, max_files_per_dir=1000)
        batch_dir = writer.get_batch_dir()

        # With Pydantic config
        config = BatchConfig(max_files_per_dir=500)
        writer = BatchWriter(output_dir, config=config)

        # O(1) fast path with state tracking
        batch_dir, batch_num = writer.get_batch_dir_fast(
            current_batch=1, files_in_current_batch=50
        )

        # Hierarchical structure
        writer = BatchWriter(sgf_root, max_files_per_dir=100)
        batch_dir = writer.get_batch_dir_for_category("intermediate", "2026", "01")
    """

    def __init__(
        self,
        root_dir: Path,
        max_files_per_dir: int = DEFAULT_BATCH_SIZE,
        config: BatchConfig | None = None,
    ) -> None:
        """Initialize BatchWriter.

        Args:
            root_dir: Root directory for batch operations.
            max_files_per_dir: Maximum files per batch directory (overridden by config).
            config: Optional Pydantic BatchConfig for validated configuration.
        """
        self.root_dir = Path(root_dir)

        # Config takes precedence if provided
        if config is not None:
            self.max_files_per_dir = config.max_files_per_dir
            self.batch_size = config.size
        else:
            self.max_files_per_dir = max_files_per_dir
            self.batch_size = max_files_per_dir

        # Cache batch counts per category to avoid repeated scans
        self._batch_counts: dict[str, int] = {}

    def get_category_dir(
        self,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
    ) -> Path:
        """Get directory path for a category/year/month.

        Args:
            category: Optional category (e.g., "intermediate").
            year: Optional year string (e.g., "2026").
            month: Optional month string (e.g., "01").

        Returns:
            Path to the target directory.
        """
        path = self.root_dir
        if category:
            path = path / category
        if year:
            path = path / year
        if month:
            path = path / month
        return path

    def get_next_batch_number(
        self,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
        file_pattern: str = "*.sgf",
    ) -> int:
        """Get the next batch number (O(N) filesystem scan).

        Caches result for subsequent calls with same category/year/month.

        Args:
            category: Optional category.
            year: Optional year string.
            month: Optional month string.
            file_pattern: Pattern for counting files.

        Returns:
            Next batch number to use (1-indexed).
        """
        cache_key = f"{category or ''}/{year or ''}/{month or ''}"

        if cache_key in self._batch_counts:
            return self._batch_counts[cache_key]

        base_dir = self.get_category_dir(category, year, month)

        if not base_dir.exists():
            self._batch_counts[cache_key] = 1
            return 1

        batch_dirs = sorted(base_dir.glob("batch-*"))
        if not batch_dirs:
            self._batch_counts[cache_key] = 1
            return 1

        # Get highest batch number
        highest = 1
        for batch_dir in batch_dirs:
            match = re.match(r"batch-(\d+)$", batch_dir.name)
            if match:
                num = int(match.group(1))
                if num > highest:
                    highest = num

        # Check if latest batch is full
        latest_batch = base_dir / f"batch-{highest:03d}"
        if latest_batch.exists():
            file_count = len(list(latest_batch.glob(file_pattern)))
            if file_count >= self.max_files_per_dir:
                highest += 1

        self._batch_counts[cache_key] = highest
        return highest

    def advance_batch(
        self,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
    ) -> int:
        """Advance to the next batch.

        Updates the cached batch count and returns the new batch number.

        Args:
            category: Optional category.
            year: Optional year string.
            month: Optional month string.

        Returns:
            New batch number.
        """
        cache_key = f"{category or ''}/{year or ''}/{month or ''}"
        current = self._batch_counts.get(cache_key, 1)
        new_batch = current + 1
        self._batch_counts[cache_key] = new_batch
        return new_batch

    def get_batch_dir(
        self,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
        batch_num: int | None = None,
        file_pattern: str = "*.sgf",
    ) -> Path:
        """Get or create batch directory (O(N) if batch_num not provided).

        Args:
            category: Optional category.
            year: Optional year string.
            month: Optional month string.
            batch_num: Optional batch number (if None, uses get_next_batch_number).
            file_pattern: Pattern for counting files.

        Returns:
            Path to batch directory (created if needed).
        """
        if batch_num is None:
            batch_num = self.get_next_batch_number(category, year, month, file_pattern)

        batch_dir = self.get_category_dir(category, year, month) / f"batch-{batch_num:03d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        return batch_dir

    def get_batch_dir_fast(
        self,
        current_batch: int,
        files_in_current_batch: int,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
    ) -> tuple[Path, int]:
        """Get batch directory using in-memory state (O(1), no filesystem scan).

        Uses provided batch tracking state to determine the correct batch directory
        without scanning the filesystem. Much faster for high-volume operations.

        IMPORTANT: This function is READ-ONLY. The caller must track state updates
        after successful file saves.

        Edge cases handled:
        - files_in_current_batch=0: Returns current batch
        - files_in_current_batch=999: Returns current batch (room for 1 more if max=1000)
        - files_in_current_batch=1000: Returns NEXT batch (current is full)

        Args:
            current_batch: Current batch number (1-indexed).
            files_in_current_batch: Files already in current batch.
            category: Optional category.
            year: Optional year string.
            month: Optional month string.

        Returns:
            Tuple of (batch directory path, batch number to use).
        """
        if files_in_current_batch >= self.max_files_per_dir:
            batch_num = current_batch + 1
        else:
            batch_num = current_batch

        batch_dir = self.get_category_dir(category, year, month) / f"batch-{batch_num:03d}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        return batch_dir, batch_num

    def is_batch_full(
        self,
        batch_num: int,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
        file_pattern: str = "*.sgf",
    ) -> bool:
        """Check if a batch directory is full (O(N) filesystem scan).

        Args:
            batch_num: Batch number to check.
            category: Optional category.
            year: Optional year string.
            month: Optional month string.
            file_pattern: Pattern for counting files.

        Returns:
            True if batch is full.
        """
        batch_dir = self.get_category_dir(category, year, month) / f"batch-{batch_num:03d}"
        if not batch_dir.exists():
            return False
        return len(list(batch_dir.glob(file_pattern))) >= self.max_files_per_dir

    def clear_cache(self) -> None:
        """Clear the batch count cache.

        Call this between runs or when batch state changes externally.
        """
        self._batch_counts.clear()

    def get_summary(
        self,
        category: str | None = None,
        year: str | None = None,
        month: str | None = None,
        file_pattern: str = "*.sgf",
    ) -> dict:
        """Get summary of all batches for a category/year/month.

        Args:
            category: Optional category.
            year: Optional year string.
            month: Optional month string.
            file_pattern: Pattern for counting files.

        Returns:
            Dictionary with batch statistics.
        """
        base_dir = self.get_category_dir(category, year, month)
        return get_batch_summary(base_dir, file_pattern)
