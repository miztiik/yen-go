"""
Trace map: ephemeral source_file → trace_id mapping for cross-stage correlation.

Replaces the heavy trace registry (JSONL + indexes + reader/writer classes) with
a flat JSON file written once at ingest end, read once at analyze/publish start.

File: .pm-runtime/staging/.trace-map-{run_id}.json
Lifecycle: Written by ingest, read by analyze/publish, deleted after publish.

Design rationale:
- O(1) dict lookup vs O(n) JSONL scan per puzzle
- Single file vs 3 index files + JSONL per run
- Ephemeral (gitignored in .pm-runtime/) vs permanent (in .puzzle-inventory-state/)
- ~30 lines vs ~750 lines of trace registry code
"""

import json
import logging
from pathlib import Path

from backend.puzzle_manager.core.atomic_write import atomic_write_text

logger = logging.getLogger("puzzle_manager.trace_map")


def _get_trace_map_path(staging_dir: Path, run_id: str) -> Path:
    """Get path to trace map file."""
    return staging_dir / f".trace-map-{run_id}.json"


def write_trace_map(
    staging_dir: Path,
    run_id: str,
    mapping: dict[str, str],
) -> Path:
    """Write source_file → trace_id mapping to a flat JSON file.

    Args:
        staging_dir: Pipeline staging directory (.pm-runtime/staging/).
        run_id: Pipeline run ID (used in filename for isolation).
        mapping: Dict of {source_file: trace_id}.

    Returns:
        Path to the written file.
    """
    file_path = _get_trace_map_path(staging_dir, run_id)
    if not mapping:
        return file_path
    staging_dir.mkdir(parents=True, exist_ok=True)
    content = json.dumps(mapping, separators=(",", ":"))
    atomic_write_text(file_path, content)
    logger.debug(f"Wrote trace map with {len(mapping)} entries for run {run_id}")
    return file_path


def read_trace_map(
    staging_dir: Path,
    run_id: str,
) -> dict[str, str]:
    """Read source_file → trace_id mapping from a flat JSON file.

    Returns empty dict if file doesn't exist (backward compat / no ingest trace).

    Args:
        staging_dir: Pipeline staging directory (.pm-runtime/staging/).
        run_id: Pipeline run ID.

    Returns:
        Dict of {source_file: trace_id}, or empty dict if not found.
    """
    file_path = _get_trace_map_path(staging_dir, run_id)
    if not file_path.exists():
        logger.debug(f"No trace map found for run {run_id}")
        return {}
    try:
        content = file_path.read_text(encoding="utf-8")
        mapping = json.loads(content)
        logger.debug(f"Loaded trace map with {len(mapping)} entries for run {run_id}")
        return mapping
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read trace map for run {run_id}: {e}")
        return {}


def delete_trace_map(
    staging_dir: Path,
    run_id: str,
) -> bool:
    """Delete the trace map file after publish completes.

    Args:
        staging_dir: Pipeline staging directory.
        run_id: Pipeline run ID.

    Returns:
        True if file was deleted, False if it didn't exist.
    """
    file_path = _get_trace_map_path(staging_dir, run_id)
    if file_path.exists():
        file_path.unlink()
        logger.debug(f"Deleted trace map for run {run_id}")
        return True
    return False


# --- Original Filenames Map Helpers ---
# Parallel helpers for the original_filenames map that stores
# source_file -> original filename from source (e.g., "puzzle_123" -> "45.sgf")


def _get_original_filenames_path(staging_dir: Path, run_id: str) -> Path:
    """Get path to original filenames map file."""
    return staging_dir / f".original-filenames-{run_id}.json"


def write_original_filenames_map(
    staging_dir: Path,
    run_id: str,
    mapping: dict[str, str],
) -> Path:
    """Write source_file -> original_filename mapping to a flat JSON file.

    Args:
        staging_dir: Pipeline staging directory.
        run_id: Pipeline run ID.
        mapping: Dict of {source_file: original_filename}.

    Returns:
        Path to the written file.
    """
    if not mapping:
        return _get_original_filenames_path(staging_dir, run_id)
    staging_dir.mkdir(parents=True, exist_ok=True)
    file_path = _get_original_filenames_path(staging_dir, run_id)
    content = json.dumps(mapping, separators=(",", ":"))
    atomic_write_text(file_path, content)
    logger.debug(f"Wrote original filenames map with {len(mapping)} entries for run {run_id}")
    return file_path


def read_original_filenames_map(
    staging_dir: Path,
    run_id: str,
) -> dict[str, str]:
    """Read source_file -> original_filename mapping from a flat JSON file.

    Returns empty dict if file doesn't exist (backward compat).

    Args:
        staging_dir: Pipeline staging directory.
        run_id: Pipeline run ID.

    Returns:
        Dict of {source_file: original_filename}, or empty dict if not found.
    """
    file_path = _get_original_filenames_path(staging_dir, run_id)
    if not file_path.exists():
        logger.debug(f"No original filenames map found for run {run_id}")
        return {}
    try:
        content = file_path.read_text(encoding="utf-8")
        mapping = json.loads(content)
        logger.debug(f"Loaded original filenames map with {len(mapping)} entries for run {run_id}")
        return mapping
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read original filenames map for run {run_id}: {e}")
        return {}


def delete_original_filenames_map(
    staging_dir: Path,
    run_id: str,
) -> bool:
    """Delete the original filenames map file after publish completes.

    Args:
        staging_dir: Pipeline staging directory.
        run_id: Pipeline run ID.

    Returns:
        True if file was deleted, False if it didn't exist.
    """
    file_path = _get_original_filenames_path(staging_dir, run_id)
    if file_path.exists():
        file_path.unlink()
        logger.debug(f"Deleted original filenames map for run {run_id}")
        return True
    return False
