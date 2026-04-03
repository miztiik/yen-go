"""
Batch writer utilities for organizing SGF files into directories.

Provides batch directory management for the publish stage with:
- O(1) fast path for high-throughput publishing (get_batch_dir_fast)
- O(N) fallback with filesystem scan (get_next_batch_number)
- Schema versioning and crash recovery
- Global batch tracking with flat sharding (Spec 126)

Supports the standard flat path structure:
    {sgf_root}/{NNNN}/{puzzle_id}.sgf

All puzzles share a single global batch counter regardless of level.
The level is NOT encoded in the directory path — it is stored in the
SGF file itself (YG property) and in view indexes (l field).

max_files_per_dir is read from pipeline config (BatchConfig).
BatchWriter does NOT define its own default — callers MUST supply it.

Usage:
    from backend.puzzle_manager.core.batch_writer import BatchWriter, BatchState

    writer = BatchWriter(sgf_root, max_files_per_dir=2000)

    # Get batch directory (global, not per-level)
    batch_dir = writer.get_batch_dir()

    # O(1) fast path with state tracking
    state = BatchState.load_or_recover(sgf_root, max_files_per_dir=2000)
    batch_dir, batch_num = writer.get_batch_dir_fast(
        state.current_batch, state.files_in_current_batch
    )
    # After successful file write:
    state.record_file_saved(max_files_per_dir)
    state.save(sgf_root)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.core.atomic_write import atomic_write_text
from backend.puzzle_manager.pm_logging import to_relative_path

logger = logging.getLogger("puzzle_manager.batch_writer")


# Schema versioning for forward/backward compatibility
# Version history:
#   1: Initial schema - current_batch, files_in_current_batch
#   2: Added last_error, retry_count, recovery_timestamp
BATCH_STATE_SCHEMA_VERSION = 2

# State file name
BATCH_STATE_FILENAME = ".batch-state.json"


@dataclass
class BatchState:
    """Persistent batch tracking state with schema evolution support.

    Provides O(1) batch tracking without filesystem scanning.
    Supports crash recovery via filesystem reconstruction.

    Schema Evolution:
        v1: current_batch, files_in_current_batch
        v2: Added last_error, retry_count, recovery_timestamp

    Usage:
        state = BatchState.load(sgf_root) or BatchState()
        batch_dir, batch_num = writer.get_batch_dir_fast(
            state.current_batch, state.files_in_current_batch
        )
        state.record_file_saved(max_files_per_dir)
        state.save(sgf_root)
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
        - files_in_current_batch=99 → advance to next batch (for batch_size=100)
        """
        self.files_in_current_batch += 1
        self.last_error = None
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

    def save(self, state_dir: Path, filename: str = BATCH_STATE_FILENAME) -> None:
        """Save batch state atomically using atomic_write_text.

        Args:
            state_dir: Directory to save state file.
            filename: State filename (default: .batch-state.json).
        """
        self._update_timestamp()
        state_path = state_dir / filename
        state_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write with cross-platform safety
        content = json.dumps(asdict(self), indent=2)
        atomic_write_text(state_path, content)
        logger.debug(f"Saved batch state to {to_relative_path(state_path)}")

    @classmethod
    def load(
        cls,
        state_dir: Path,
        filename: str = BATCH_STATE_FILENAME,
    ) -> BatchState | None:
        """Load batch state from file with schema migration.

        Handles corrupted files by deleting and returning None.
        Performs automatic schema migration for older versions.

        Args:
            state_dir: Directory containing state file.
            filename: State filename (default: .batch-state.json).

        Returns:
            BatchState instance or None if not found/corrupted.
        """
        state_path = state_dir / filename

        if not state_path.exists():
            return None

        try:
            content = state_path.read_text(encoding="utf-8")
            if not content.strip():
                logger.warning(f"Empty batch state file, deleting: {to_relative_path(state_path)}")
                state_path.unlink()
                return None

            data = json.loads(content)

            if not isinstance(data, dict):
                logger.warning(f"Invalid batch state format, deleting: {to_relative_path(state_path)}")
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
            logger.warning(f"Corrupted batch state JSON ({e}), deleting: {to_relative_path(state_path)}")
            state_path.unlink()
            return None
        except (TypeError, KeyError) as e:
            logger.warning(f"Invalid batch state structure ({e}), deleting: {to_relative_path(state_path)}")
            state_path.unlink()
            return None

    @classmethod
    def _migrate_schema(cls, data: dict, from_version: int) -> dict:
        """Migrate schema from older versions."""
        if from_version < 2:
            data["schema_version"] = 2
            data.setdefault("last_error", None)
            data.setdefault("retry_count", 0)
            data.setdefault("recovery_timestamp", None)
        return data

    @classmethod
    def recover_from_filesystem(
        cls,
        sgf_root: Path,
        batch_size: int,
        file_pattern: str = "*.sgf",
    ) -> BatchState:
        """Recover batch state by scanning filesystem.

        Use this after a crash or when state file is lost/corrupted.
        Scans sgf/{NNNN} directories (Spec 126 flat sharding).
        Also supports legacy sgf/{level}/batch-{NNNN} layout for migration.

        Args:
            sgf_root: Root SGF directory containing batch dirs.
            batch_size: Maximum files per batch directory (from config).
            file_pattern: Pattern to count files.

        Returns:
            Recovered BatchState matching filesystem reality.
        """
        logger.debug(f"Recovering batch state from filesystem: {to_relative_path(sgf_root)}")

        if not sgf_root.exists():
            return cls(
                current_batch=1,
                files_in_current_batch=0,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )

        # Scan for flat {NNNN} dirs (new format)
        batch_dirs = sorted(
            [d for d in sgf_root.iterdir()
             if d.is_dir() and re.match(r"\d{4}$", d.name)],
            key=lambda d: int(d.name)
        )

        # Fallback: scan for legacy batch-{NNNN} dirs (inside level subdirs)
        if not batch_dirs:
            for level_dir in sorted(sgf_root.iterdir()):
                if not level_dir.is_dir() or level_dir.name.startswith("."):
                    continue
                legacy_dirs = [
                    d for d in level_dir.iterdir()
                    if d.is_dir() and re.match(r"batch-\d+$", d.name)
                ]
                batch_dirs.extend(legacy_dirs)
            batch_dirs.sort(key=lambda d: int(re.search(r"\d+", d.name).group()))  # type: ignore[union-attr]

        if not batch_dirs:
            return cls(
                current_batch=1,
                files_in_current_batch=0,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )

        last_batch = batch_dirs[-1]
        # Extract batch number from either "0001" or "batch-0001"
        batch_name = last_batch.name
        if batch_name.startswith("batch-"):
            batch_num = int(batch_name.split("-")[1])
        else:
            batch_num = int(batch_name)

        file_count = len(list(last_batch.glob(file_pattern)))

        if file_count >= batch_size:
            state = cls(
                current_batch=batch_num + 1,
                files_in_current_batch=0,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )
        else:
            state = cls(
                current_batch=batch_num,
                files_in_current_batch=file_count,
                recovery_timestamp=datetime.now(UTC).isoformat(),
            )

        logger.debug(
            f"Recovered state: batch {state.current_batch}, "
            f"{state.files_in_current_batch} files in current batch"
        )
        return state

    @classmethod
    def load_or_recover(
        cls,
        state_dir: Path,
        batch_size: int,
        file_pattern: str = "*.sgf",
    ) -> BatchState:
        """Load state from file, or recover from filesystem if missing/corrupted.

        Args:
            state_dir: Directory containing state file and batch dirs.
            batch_size: Maximum files per batch (from config, no default).
            file_pattern: Glob pattern for counting files.
        """
        state = cls.load(state_dir)
        if state is not None:
            return state
        return cls.recover_from_filesystem(state_dir, batch_size, file_pattern)


class BatchWriter:
    """Batch directory manager for SGF file publishing.

    Provides both O(1) fast path (with state tracking) and O(N) fallback
    (with filesystem scan) for batch directory resolution.

    Flat path structure (4-digit batch, no level nesting):
        {sgf_root}/{NNNN}/{puzzle_id}.sgf

    All puzzles share a single global batch counter. The level is stored
    in each SGF file (YG property) and in view index entries (l field),
    not in the directory structure.

    max_files_per_dir MUST be supplied by the caller (from config).

    Usage:
        writer = BatchWriter(sgf_root, max_files_per_dir=2000)

        # O(N) fallback (scans filesystem)
        batch_num = writer.get_next_batch_number()
        batch_dir = writer.get_batch_dir()

        # O(1) fast path (uses state tracking)
        batch_dir, batch_num = writer.get_batch_dir_fast(
            current_batch=1, files_in_current_batch=50
        )
    """

    def __init__(
        self,
        sgf_root: Path,
        max_files_per_dir: int,
    ) -> None:
        """Initialize BatchWriter.

        Args:
            sgf_root: Root directory for SGF files.
            max_files_per_dir: Maximum files per batch directory (from config).
                This is a required parameter — callers must pass the value
                from BatchConfig.max_files_per_dir.
        """
        self.sgf_root = sgf_root
        self.max_files_per_dir = max_files_per_dir
        # Cache batch number to avoid repeated scans
        self._cached_batch_num: int | None = None

    def get_next_batch_number(self) -> int:
        """Get the next batch number (O(N) filesystem scan).

        Caches result for subsequent calls.
        Uses 4-digit batch numbering (Spec 126).

        Returns:
            Next batch number to use (1-indexed).
        """
        if self._cached_batch_num is not None:
            return self._cached_batch_num

        if not self.sgf_root.exists():
            self._cached_batch_num = 1
            return 1

        # Scan for {NNNN} dirs
        batch_dirs = sorted(
            [d for d in self.sgf_root.iterdir()
             if d.is_dir() and re.match(r"\d{4}$", d.name)]
        )

        if not batch_dirs:
            self._cached_batch_num = 1
            return 1

        # Get highest batch number
        highest = 1
        for batch_dir in batch_dirs:
            try:
                num = int(batch_dir.name)
                if num > highest:
                    highest = num
            except ValueError:
                continue

        # Check if latest batch is full
        latest_batch = self.sgf_root / f"{highest:04d}"
        if latest_batch.exists():
            file_count = len(list(latest_batch.glob("*.sgf")))
            if file_count >= self.max_files_per_dir:
                highest += 1

        self._cached_batch_num = highest
        return highest

    def advance_batch(self) -> int:
        """Advance to the next batch.

        Updates the cached batch number and returns the new batch number.

        Returns:
            New batch number.
        """
        current = self._cached_batch_num or 1
        new_batch = current + 1
        self._cached_batch_num = new_batch
        return new_batch

    def get_batch_dir(
        self,
        batch_num: int | None = None,
    ) -> Path:
        """Get or create batch directory (O(N) if batch_num not provided).

        Uses 4-digit batch numbering (Spec 126).

        Args:
            batch_num: Optional batch number (if None, uses get_next_batch_number).

        Returns:
            Path to batch directory (created if needed).
        """
        if batch_num is None:
            batch_num = self.get_next_batch_number()

        batch_dir = self.sgf_root / f"{batch_num:04d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        return batch_dir

    def get_batch_dir_fast(
        self,
        current_batch: int,
        files_in_current_batch: int,
    ) -> tuple[Path, int]:
        """Get batch directory using in-memory state (O(1), no filesystem scan).

        Uses provided batch tracking state to determine the correct batch directory
        without scanning the filesystem. Much faster for high-volume publishing.
        Uses 4-digit batch numbering (Spec 126).

        IMPORTANT: This function is READ-ONLY. The caller must track state updates
        after successful file saves.

        Edge cases handled:
        - files_in_current_batch=0: Returns current batch
        - files_in_current_batch=1999: Returns current batch (room for 1 more if max=2000)
        - files_in_current_batch=2000: Returns NEXT batch (current is full)

        Args:
            current_batch: Current batch number (1-indexed).
            files_in_current_batch: Files already in current batch.

        Returns:
            Tuple of (batch directory path, batch number to use).
        """
        if files_in_current_batch >= self.max_files_per_dir:
            batch_num = current_batch + 1
        else:
            batch_num = current_batch

        batch_dir = self.sgf_root / f"{batch_num:04d}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        return batch_dir, batch_num

    def is_batch_full(
        self,
        batch_num: int,
    ) -> bool:
        """Check if a batch directory is full (O(N) filesystem scan).

        Args:
            batch_num: Batch number to check.

        Returns:
            True if batch is full.
        """
        batch_dir = self.sgf_root / f"{batch_num:04d}"
        if not batch_dir.exists():
            return False
        return len(list(batch_dir.glob("*.sgf"))) >= self.max_files_per_dir

    def clear_cache(self) -> None:
        """Clear the batch number cache.

        Call this between runs or when batch state changes externally.
        """
        self._cached_batch_num = None

    def get_batch_summary(self) -> dict:
        """Get summary of all batches.

        Returns:
            Dictionary with batch statistics.
        """
        if not self.sgf_root.exists():
            return {"batch_count": 0, "total_files": 0, "batches": []}

        batches = []
        total_files = 0

        for batch_dir in sorted(
            d for d in self.sgf_root.iterdir()
            if d.is_dir() and re.match(r"\d{4}$", d.name)
        ):
            try:
                batch_num = int(batch_dir.name)
                file_count = len(list(batch_dir.glob("*.sgf")))
                batches.append({"number": batch_num, "files": file_count})
                total_files += file_count
            except ValueError:
                continue

        return {
            "batch_count": len(batches),
            "total_files": total_files,
            "batches": batches,
        }
