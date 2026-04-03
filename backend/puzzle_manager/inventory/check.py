"""
Inventory integrity check functionality.

Implements integrity checking to detect and fix inventory discrepancies.
T028-T032 from Spec 107 (US4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from backend.puzzle_manager.inventory.models import PuzzleCollectionInventory
from backend.puzzle_manager.paths import get_output_dir, rel_path
from backend.puzzle_manager.publish_log import PublishLogReader

logger = logging.getLogger("puzzle_manager.inventory.check")


@dataclass
class IntegrityResult:
    """Result of an inventory integrity check.

    T028 (Spec 107): Dataclass to hold integrity check results.

    Attributes:
        is_valid: True if inventory is consistent with actual files.
        total_expected: Total puzzles according to inventory.
        total_actual: Total puzzles actually found on disk.
        discrepancies: List of discrepancy descriptions.
        orphan_entries: Publish log entries without corresponding files.
        orphan_files: SGF files without publish log entries.
        level_mismatches: Dict of level -> (expected, actual) for mismatches.
        tag_mismatches: Dict of tag -> (expected, actual) for mismatches.
    """
    is_valid: bool = True
    total_expected: int = 0
    total_actual: int = 0
    discrepancies: list[str] = field(default_factory=list)
    orphan_entries: list[str] = field(default_factory=list)
    orphan_files: list[str] = field(default_factory=list)
    level_mismatches: dict[str, tuple[int, int]] = field(default_factory=dict)
    tag_mismatches: dict[str, tuple[int, int]] = field(default_factory=dict)


def check_integrity(
    output_dir: Path | None = None,
    inventory: PuzzleCollectionInventory | None = None,
) -> IntegrityResult:
    """Check inventory integrity against actual files.

    T029 (Spec 107): Implement check_integrity() function.

    Compares inventory counts against:
    - Actual SGF files on disk
    - Publish log entries

    Args:
        output_dir: Output directory to check. Uses default if None.
        inventory: Inventory to verify. Loads from disk if None.

    Returns:
        IntegrityResult with findings.
    """
    if output_dir is None:
        output_dir = get_output_dir()

    result = IntegrityResult()

    # Spec 107: Publish log is now under .puzzle-inventory-state/
    ops_dir = output_dir / ".puzzle-inventory-state"
    publish_log_dir = ops_dir / "publish-log"

    # Scan publish log entries
    log_reader = PublishLogReader(log_dir=publish_log_dir)

    entries_with_files: set[str] = set()
    entries_without_files: list[str] = []
    seen_paths: set[str] = set()  # Track processed paths to deduplicate

    for entry in log_reader.read_all():
        sgf_path = output_dir / entry.path
        if sgf_path.exists():
            entries_with_files.add(entry.path)
            seen_paths.add(entry.path)
        else:
            # Only report as orphan if not already seen
            if entry.path not in seen_paths:
                entries_without_files.append(entry.path)
            seen_paths.add(entry.path)

    # Scan actual SGF files
    sgf_dir = output_dir / "sgf"
    actual_files: set[str] = set()

    if sgf_dir.exists():
        for sgf_file in sgf_dir.rglob("*.sgf"):
            rel = sgf_file.relative_to(output_dir)
            path_str = str(rel).replace("\\", "/")
            actual_files.add(path_str)

    # Set result counts
    result.total_actual = len(actual_files)
    if inventory:
        result.total_expected = inventory.collection.total_puzzles

    # Check for orphan entries (log entries without files)
    result.orphan_entries = entries_without_files
    if entries_without_files:
        result.is_valid = False
        result.discrepancies.append(
            f"Found {len(entries_without_files)} orphan entries "
            f"(publish log entries without files)"
        )

    # Check for orphan files (files without log entries)
    orphan_files = actual_files - entries_with_files
    result.orphan_files = list(orphan_files)
    if orphan_files:
        result.discrepancies.append(
            f"Found {len(orphan_files)} orphan files "
            f"(SGF files without publish log entries)"
        )

    # FR-018: Check total_puzzles matches actual file count
    if inventory and result.total_expected != result.total_actual:
        result.is_valid = False
        result.discrepancies.append(
            f"Total mismatch: inventory says {result.total_expected}, "
            f"actual is {result.total_actual}"
        )

    # FR-019: Check by_puzzle_level counts match actual files per level
    if inventory:
        actual_by_level: dict[str, int] = {}
        for path_str in actual_files:
            parts = path_str.split("/")
            if len(parts) >= 2:
                actual_by_level[parts[1]] = actual_by_level.get(parts[1], 0) + 1

        for level, expected_count in inventory.collection.by_puzzle_level.items():
            actual_count = actual_by_level.get(level, 0)
            if expected_count != actual_count:
                result.is_valid = False
                result.level_mismatches[level] = (expected_count, actual_count)
                result.discrepancies.append(
                    f"Level mismatch for '{level}': inventory says {expected_count}, "
                    f"actual is {actual_count}"
                )

    logger.info(
        f"Integrity check complete: valid={result.is_valid}, "
        f"actual={result.total_actual}, "
        f"orphan_entries={len(result.orphan_entries)}, "
        f"orphan_files={len(result.orphan_files)}"
    )

    return result


def fix_integrity(
    output_dir: Path | None = None,
    run_id: str | None = None,
) -> PuzzleCollectionInventory:
    """Fix inventory by rebuilding from publish logs.

    T031 (Spec 107): Implement --fix flag functionality.

    Calls reconcile_inventory() to reconstruct accurate counts
    from SGF files on disk.

    Args:
        output_dir: Output directory to rebuild. Uses default if None.
        run_id: Run ID for the rebuild. Auto-generated if None.

    Returns:
        Rebuilt PuzzleCollectionInventory.
    """
    if output_dir is None:
        output_dir = get_output_dir()

    logger.info(f"Fixing inventory by reconciling from {rel_path(output_dir)}")

    from backend.puzzle_manager.inventory.reconcile import reconcile_inventory
    return reconcile_inventory(output_dir=output_dir, run_id=run_id)


def format_integrity_result(result: IntegrityResult) -> str:
    """Format IntegrityResult for CLI output.

    T032 (Spec 107): Implement CLI output formatting.

    Args:
        result: IntegrityResult to format.

    Returns:
        Human-readable string representation.
    """
    lines = []

    if result.is_valid:
        lines.append("✓ Inventory integrity check PASSED")
        lines.append(f"  Total puzzles: {result.total_actual}")
    else:
        lines.append("✗ Inventory integrity check FAILED")
        lines.append("")
        lines.append("Discrepancies found:")
        for discrepancy in result.discrepancies:
            lines.append(f"  • {discrepancy}")

    if result.orphan_entries:
        lines.append("")
        lines.append("Orphan entries (missing files):")
        for entry in result.orphan_entries[:10]:  # Limit to first 10
            lines.append(f"  - {entry}")
        if len(result.orphan_entries) > 10:
            lines.append(f"  ... and {len(result.orphan_entries) - 10} more")

    if result.orphan_files:
        lines.append("")
        lines.append("Orphan files (no log entry):")
        for file_path in result.orphan_files[:10]:
            lines.append(f"  - {file_path}")
        if len(result.orphan_files) > 10:
            lines.append(f"  ... and {len(result.orphan_files) - 10} more")

    if result.level_mismatches:
        lines.append("")
        lines.append("Level mismatches:")
        for level, (expected, actual) in result.level_mismatches.items():
            lines.append(f"  {level}: expected {expected}, actual {actual}")

    return "\n".join(lines)
