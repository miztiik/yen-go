"""
AdapterCheckpoint - Generic checkpoint utility for adapter resume support.

Provides save/load/clear/exists/get_path operations for adapter checkpoint state.
Checkpoint files are stored as JSON in .pm-runtime/state/{adapter_id}_checkpoint.json

Schema Versioning:
    - Version 1: Initial schema (pre-spec-109)
    - Version 2: Added config_signature for folder filtering config tracking

    The schema_version field enables forward/backward compatibility.
    Older checkpoints without schema_version are treated as version 1.

File format (v2):
{
    "schema_version": 2,
    "adapter_id": "sanderland",
    "timestamp": "2025-01-15T10:30:00Z",
    "state": {
        "current_folder": "1a. Tsumego Beginner",
        "files_completed": 50,  // 1-indexed: how many files done
        "config_signature": "a1b2c3d4",
        ...adapter-specific state...
    }
}

Usage:
    from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint

    # Save checkpoint
    AdapterCheckpoint.save("sanderland", {"files_completed": 50})

    # Load checkpoint (returns None if not found)
    data = AdapterCheckpoint.load("sanderland")
    if data:
        state = data["state"]  # The actual adapter state

    # Check if checkpoint exists
    if AdapterCheckpoint.exists("sanderland"):
        ...

    # Clear checkpoint after successful completion
    AdapterCheckpoint.clear("sanderland")
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

# Checkpoint schema versioning for forward/backward compatibility
# Version history:
#   1: Initial schema (pre-spec-109) - adapter_id, timestamp, state
#   2: Added config_signature tracking for folder filtering (spec-109)
CHECKPOINT_SCHEMA_VERSION = 2


def get_runtime_dir() -> Path:
    """Get the runtime directory path.

    Returns .pm-runtime directory at project root.
    Can be overridden via YENGO_RUNTIME_DIR environment variable.
    """
    import os

    if custom_dir := os.environ.get("YENGO_RUNTIME_DIR"):
        return Path(custom_dir)

    # Default: .pm-runtime at project root
    return Path(__file__).parent.parent.parent.parent / ".pm-runtime"


class CheckpointData(TypedDict):
    """Type definition for checkpoint file structure (v2).

    Attributes:
        schema_version: Schema version for compatibility checks (default: 2)
        adapter_id: Unique identifier for the adapter
        timestamp: ISO 8601 timestamp when checkpoint was saved
        state: Adapter-specific state dictionary
    """
    schema_version: int
    adapter_id: str
    timestamp: str
    state: dict[str, Any]


class AdapterCheckpoint:
    """Generic checkpoint utility for adapter resume support.

    All methods are static/class methods - no instance state needed.
    Thread-safe for single-writer, multiple-reader scenarios.
    """

    @classmethod
    def get_path(cls, adapter_id: str) -> Path:
        """Get the checkpoint file path for an adapter.

        Args:
            adapter_id: Unique adapter identifier (e.g., "sanderland", "kisvadim")

        Returns:
            Path to checkpoint file: .pm-runtime/state/{adapter_id}_checkpoint.json
        """
        return get_runtime_dir() / "state" / f"{adapter_id}_checkpoint.json"

    @classmethod
    def save(cls, adapter_id: str, state: dict[str, Any]) -> None:
        """Save adapter checkpoint state.

        Creates the checkpoint file with wrapped structure including
        adapter_id, ISO 8601 timestamp, and the adapter state.

        Creates directory structure if it doesn't exist.

        Args:
            adapter_id: Unique adapter identifier
            state: Adapter-specific state dictionary to persist
        """
        checkpoint_path = cls.get_path(adapter_id)

        # Ensure directory exists
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        # Build checkpoint structure
        checkpoint_data: CheckpointData = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "adapter_id": adapter_id,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "state": state,
        }

        # Atomic write with cross-platform safety
        from backend.puzzle_manager.core.atomic_write import atomic_write_json
        atomic_write_json(checkpoint_path, checkpoint_data, ensure_ascii=False)
        logger.debug(f"Checkpoint saved for adapter '{adapter_id}'")

    @classmethod
    def load(cls, adapter_id: str) -> CheckpointData | None:
        """Load adapter checkpoint state.

        Returns the full checkpoint wrapper including adapter_id, timestamp,
        and state. Access the adapter state via result["state"].

        Handles corrupted files by logging warning, deleting the file,
        and returning None.

        Args:
            adapter_id: Unique adapter identifier

        Returns:
            Checkpoint data dict with keys: adapter_id, timestamp, state
            Returns None if checkpoint doesn't exist or is corrupted.
        """
        checkpoint_path = cls.get_path(adapter_id)

        if not checkpoint_path.exists():
            return None

        try:
            content = checkpoint_path.read_text(encoding="utf-8")
            if not content.strip():
                # Empty file - treat as corrupted
                logger.warning(
                    f"Corrupted checkpoint for adapter '{adapter_id}': empty file. "
                    f"Deleting {checkpoint_path}"
                )
                checkpoint_path.unlink()
                return None

            data = json.loads(content)

            # Validate required structure
            if not isinstance(data, dict) or "state" not in data:
                logger.warning(
                    f"Corrupted checkpoint for adapter '{adapter_id}': "
                    f"missing 'state' key. Deleting {checkpoint_path}"
                )
                checkpoint_path.unlink()
                return None

            # Handle schema version migration
            schema_version = data.get("schema_version", 1)  # Default to v1 for old checkpoints
            if schema_version < CHECKPOINT_SCHEMA_VERSION:
                logger.info(
                    f"Checkpoint for adapter '{adapter_id}' is schema v{schema_version}, "
                    f"current is v{CHECKPOINT_SCHEMA_VERSION}. Migrating..."
                )
                # v1 -> v2: Add schema_version field (state remains compatible)
                data["schema_version"] = CHECKPOINT_SCHEMA_VERSION

            logger.debug(f"Checkpoint loaded for adapter '{adapter_id}' (schema v{data.get('schema_version', 1)})")
            # Cast to CheckpointData - JSON structure is validated above
            return data  # type: ignore[return-value]

        except json.JSONDecodeError as e:
            logger.warning(
                f"Corrupted checkpoint for adapter '{adapter_id}': "
                f"invalid JSON ({e}). Deleting {checkpoint_path}"
            )
            checkpoint_path.unlink()
            return None
        except OSError as e:
            logger.warning(
                f"Failed to read checkpoint for adapter '{adapter_id}': {e}"
            )
            return None

    @classmethod
    def exists(cls, adapter_id: str) -> bool:
        """Check if checkpoint exists for an adapter.

        Args:
            adapter_id: Unique adapter identifier

        Returns:
            True if checkpoint file exists, False otherwise.
        """
        return cls.get_path(adapter_id).exists()

    @classmethod
    def clear(cls, adapter_id: str) -> bool:
        """Clear/delete checkpoint for an adapter.

        Called after successful pipeline completion to clean up state.

        Args:
            adapter_id: Unique adapter identifier

        Returns:
            True if checkpoint was deleted, False if it didn't exist.
        """
        checkpoint_path = cls.get_path(adapter_id)

        if not checkpoint_path.exists():
            return False

        checkpoint_path.unlink()
        logger.debug(f"Checkpoint cleared for adapter '{adapter_id}'")
        return True
