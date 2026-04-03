"""
Generic checkpoint utilities for download tools.

Provides save/load/clear operations for tool resume support.
Checkpoint files are stored as JSON in the tool's output directory.

Usage:
    from tools.core.checkpoint import ToolCheckpoint, load_checkpoint, save_checkpoint

    # Define your checkpoint dataclass
    @dataclass
    class MyCheckpoint(ToolCheckpoint):
        last_page: int = 0
        items_downloaded: int = 0

    # Load checkpoint
    checkpoint = load_checkpoint(output_dir, MyCheckpoint)

    # Save checkpoint
    save_checkpoint(checkpoint, output_dir)

    # Clear checkpoint after completion
    clear_checkpoint(output_dir)
"""

from __future__ import annotations

import json
import logging
from abc import ABC
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from tools.core.atomic_write import atomic_write_json

logger = logging.getLogger("tools.core.checkpoint")


# Constants
CHECKPOINT_FILENAME = ".checkpoint.json"
CHECKPOINT_VERSION = "1.0.0"


@dataclass
class ToolCheckpoint(ABC):  # noqa: B024
    """Base class for tool checkpoint state.

    All tool-specific checkpoints should inherit from this class.

    Attributes:
        version: Schema version for compatibility checks.
        last_updated: ISO 8601 timestamp when checkpoint was saved.
    """

    version: str = CHECKPOINT_VERSION
    last_updated: str = ""

    def update_timestamp(self) -> None:
        """Update last_updated to now."""
        self.last_updated = datetime.now(UTC).isoformat()


@dataclass
class BatchTrackingMixin:
    """Mixin for checkpoints that track batch state.

    Provides O(1) batch tracking without filesystem scanning.
    Use with get_batch_for_file_fast() from tools.core.batching.

    Usage:
        @dataclass
        class MyCheckpoint(ToolCheckpoint, BatchTrackingMixin):
            # Your tool-specific fields
            puzzles_downloaded: int = 0

        # After successful file save:
        checkpoint.record_file_saved(batch_size=500)
    """

    current_batch: int = 1
    files_in_current_batch: int = 0

    def record_file_saved(self, batch_size: int) -> None:
        """Record a successful file save and update batch tracking.

        MUST be called AFTER file is successfully written to disk.
        Handles batch advancement when current batch becomes full.

        Args:
            batch_size: Maximum files per batch (needed for advancement check)

        State transitions:
        - files_in_current_batch: 0→1, 1→2, ..., 499→500
        - When files_in_current_batch reaches batch_size:
          - current_batch: N → N+1
          - files_in_current_batch: 500 → 0
        """
        self.files_in_current_batch += 1

        # Check if we just filled the batch and need to advance
        if self.files_in_current_batch >= batch_size:
            self.current_batch += 1
            self.files_in_current_batch = 0

    def get_batch_state(self) -> tuple[int, int]:
        """Return current batch tracking state.

        Returns:
            Tuple of (current_batch, files_in_current_batch)
        """
        return self.current_batch, self.files_in_current_batch


T = TypeVar("T", bound=ToolCheckpoint)


def load_checkpoint[T: ToolCheckpoint](
    output_dir: Path,
    checkpoint_class: type[T],
    filename: str = CHECKPOINT_FILENAME,
) -> T | None:
    """Load checkpoint from file.

    Args:
        output_dir: Directory containing checkpoint file.
        checkpoint_class: Dataclass type to deserialize into.
        filename: Checkpoint filename (default: .checkpoint.json).

    Returns:
        Checkpoint instance or None if not found/corrupted.
    """
    checkpoint_path = output_dir / filename

    if not checkpoint_path.exists():
        return None

    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))

        # Handle version migration if needed
        file_version = data.get("version", "unknown")
        if file_version != CHECKPOINT_VERSION:
            logger.warning(
                f"Checkpoint version mismatch: {file_version} vs {CHECKPOINT_VERSION}"
            )

        # Create instance from dict, ignoring extra fields
        # Get only fields that exist in the dataclass
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(checkpoint_class)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        checkpoint = checkpoint_class(**filtered_data)

        logger.info(f"Loaded checkpoint from {checkpoint_path.name}")
        return checkpoint

    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"Corrupted checkpoint file, starting fresh: {e}")
        # Rename corrupted file for debugging
        corrupted_path = output_dir / f".checkpoint.corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        try:
            checkpoint_path.rename(corrupted_path)
        except OSError:
            pass
        return None


def save_checkpoint(
    checkpoint: ToolCheckpoint,
    output_dir: Path,
    filename: str = CHECKPOINT_FILENAME,
) -> None:
    """Save checkpoint to file atomically.

    Uses atomic_write_json for cross-platform safety with Windows
    retry logic and guaranteed temp file cleanup.

    Args:
        checkpoint: Checkpoint state to save.
        output_dir: Directory for checkpoint file.
        filename: Checkpoint filename (default: .checkpoint.json).
    """
    checkpoint.update_timestamp()
    checkpoint_path = output_dir / filename

    # Atomic write with cross-platform safety
    atomic_write_json(checkpoint_path, asdict(checkpoint))

    logger.debug(f"Saved checkpoint to {checkpoint_path.name}")


def clear_checkpoint(
    output_dir: Path,
    filename: str = CHECKPOINT_FILENAME,
) -> None:
    """Remove checkpoint file.

    Args:
        output_dir: Directory containing checkpoint file.
        filename: Checkpoint filename (default: .checkpoint.json).
    """
    checkpoint_path = output_dir / filename

    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info(f"Cleared checkpoint {checkpoint_path.name}")


def checkpoint_exists(
    output_dir: Path,
    filename: str = CHECKPOINT_FILENAME,
) -> bool:
    """Check if checkpoint file exists.

    Args:
        output_dir: Directory containing checkpoint file.
        filename: Checkpoint filename (default: .checkpoint.json).

    Returns:
        True if checkpoint file exists.
    """
    return (output_dir / filename).exists()
