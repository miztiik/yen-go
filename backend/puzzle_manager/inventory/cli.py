"""
CLI commands for inventory management.

Provides the `inventory` command for viewing and managing the puzzle collection inventory.

Usage:
    python -m backend.puzzle_manager inventory
    python -m backend.puzzle_manager inventory --json
    python -m backend.puzzle_manager inventory --rebuild
    python -m backend.puzzle_manager inventory --reconcile
"""

import json
import logging
from typing import TYPE_CHECKING

from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import PuzzleCollectionInventory

if TYPE_CHECKING:
    import argparse

logger = logging.getLogger("puzzle_manager.inventory.cli")


def format_inventory_summary(inventory: PuzzleCollectionInventory) -> str:
    """Format inventory as human-readable summary.

    Args:
        inventory: The inventory to format

    Returns:
        Human-readable string matching quickstart.md sample output
    """
    lines: list[str] = []

    # Header
    lines.append("Puzzle Collection Inventory")
    lines.append("===========================")
    lines.append(f"Total Puzzles: {inventory.collection.total_puzzles:,}")
    lines.append("")

    # By Level section
    lines.append("By Level:")
    total = inventory.collection.total_puzzles

    # Define level order per config/puzzle-levels.json
    level_order = [
        "novice", "beginner", "elementary", "intermediate",
        "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"
    ]

    for level in level_order:
        count = inventory.collection.by_puzzle_level.get(level, 0)
        pct = (count / total * 100) if total > 0 else 0.0
        # Right-align level name (18 chars) and count (7 chars)
        lines.append(f"  {level}:{count:>12,} ({pct:.1f}%)")

    lines.append("")

    # By Tag section (top 10)
    lines.append("By Tag (top 10):")
    sorted_tags = sorted(
        inventory.collection.by_tag.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    for tag, count in sorted_tags:
        pct = (count / total * 100) if total > 0 else 0.0
        lines.append(f"  {tag}:{count:>10,} ({pct:.1f}%)")

    lines.append("")

    # By Quality section (ordered 5→1, Premium first)
    lines.append("By Quality:")
    quality_names = {
        "5": "Premium",
        "4": "High",
        "3": "Standard",
        "2": "Basic",
        "1": "Unverified",
    }
    # Display in order 5→1 (best quality first)
    for level in ["5", "4", "3", "2", "1"]:
        count = inventory.collection.by_puzzle_quality.get(level, 0)
        pct = (count / total * 100) if total > 0 else 0.0
        name = quality_names[level]
        lines.append(f"  {name} ({level}):{count:>9,} ({pct:.1f}%)")

    lines.append("")

    # Footer
    if inventory.last_updated:
        lines.append(f"Last Updated: {inventory.last_updated.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if inventory.last_run_id:
        lines.append(f"Last Run ID:  {inventory.last_run_id}")

    return "\n".join(lines)


def format_inventory_json(inventory: PuzzleCollectionInventory) -> str:
    """Format inventory as JSON.

    Args:
        inventory: The inventory to format

    Returns:
        Pretty-printed JSON string
    """
    return json.dumps(
        inventory.model_dump(mode="json"),
        indent=2,
        sort_keys=False,
    )


def cmd_inventory(args: "argparse.Namespace") -> int:
    """Handle the inventory command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        manager = InventoryManager()

        # Theme 14c1: --dry-run for the mutating ops emits an
        # InventoryMutationPreview without touching disk. Routed before the
        # apply branches so the preview path never accidentally writes.
        if getattr(args, "dry_run", False) and (
            getattr(args, "rebuild", False)
            or getattr(args, "reconcile", False)
            or getattr(args, "fix", False)
        ):
            return _emit_mutation_preview(args, manager)

        # T030, T031, T032 (Spec 107): Handle --check and --fix flags
        if getattr(args, "check", False):
            from backend.puzzle_manager.inventory.check import (
                check_integrity,
                format_integrity_result,
            )

            logger.info("Running inventory integrity check...")

            # Load existing inventory if it exists
            inventory = manager.load() if manager.exists() else None

            result = check_integrity(inventory=inventory)

            # Theme 14a: --check --json emits the structured IntegrityReport
            # (Pydantic) so the dashboard can render per-issue rows. Human
            # output stays unchanged for terminal use.
            if getattr(args, "json", False):
                from backend.puzzle_manager.models.integrity import (
                    IntegrityReport,
                )

                report = IntegrityReport.from_legacy_result(result)
                print(report.model_dump_json())
            else:
                print(format_integrity_result(result))

            return 0 if result.is_valid else 1

        if getattr(args, "fix", False):
            from backend.puzzle_manager.inventory.check import (
                check_integrity,
                fix_integrity,
                format_integrity_result,
            )

            logger.info("Fixing inventory...")

            # First check current state
            inventory = manager.load() if manager.exists() else None
            result_before = check_integrity(inventory=inventory)

            if result_before.is_valid:
                print("✓ Inventory is already consistent, no fix needed")
                return 0

            # Fix by rebuilding
            fixed_inventory = fix_integrity()

            # Save the fixed inventory
            manager.save(fixed_inventory)

            # Verify fix
            result_after = check_integrity(inventory=fixed_inventory)

            if result_after.is_valid:
                print("✓ Inventory fixed successfully")
                print(f"  Total puzzles: {fixed_inventory.collection.total_puzzles}")
            else:
                print("✗ Fix completed but issues remain:")
                print(format_integrity_result(result_after))
                return 1

            return 0

        if getattr(args, "reconcile", False):
            # Reconcile from disk — scans actual SGF files for ground truth
            logger.info("Reconciling inventory from SGF files on disk...")
            from backend.puzzle_manager.inventory.reconcile import reconcile_inventory
            inventory = reconcile_inventory(
                run_id=None,  # auto-generated
            )
            manager.save(inventory)
            print(f"[OK] Inventory reconciled from disk: {inventory.collection.total_puzzles} puzzles")
            # Now format and display the reconciled inventory
            if getattr(args, "json", False):
                output = format_inventory_json(inventory)
            else:
                output = format_inventory_summary(inventory)
            print(output)
            return 0

        if getattr(args, "rebuild", False):
            # Rebuild from SGF files on disk (same as reconcile in v2.0)
            logger.info("Rebuilding inventory from SGF files...")
            from backend.puzzle_manager.inventory.reconcile import reconcile_inventory
            inventory = reconcile_inventory()
            manager.save(inventory)
            print(f"[OK] Inventory rebuilt: {inventory.collection.total_puzzles} puzzles")
            # Now format and display the rebuilt inventory
            if getattr(args, "json", False):
                output = format_inventory_json(inventory)
            else:
                output = format_inventory_summary(inventory)
            print(output)
            return 0

        # Load inventory if exists, otherwise show message
        if manager.exists():
            inventory = manager.load()
        else:
            print("[INFO] No inventory file found. Run 'python -m backend.puzzle_manager run' to publish puzzles and create inventory.")
            print(f"[INFO] Expected location: {manager.inventory_path}")
            return 0

        # Format output
        if getattr(args, "json", False):
            output = format_inventory_json(inventory)
        else:
            output = format_inventory_summary(inventory)

        print(output)
        return 0

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        print(f"[ERROR] {e}")
        return 1


def _emit_mutation_preview(
    args: "argparse.Namespace",
    manager: InventoryManager,
) -> int:
    """Theme 14c1: build and emit ``InventoryMutationPreview`` for a dry-run.

    Selects the op (rebuild → reconcile → fix in argparse priority order),
    counts SGFs on disk via ``rglob``, reads the current snapshot total
    (or treats it as absent), and — for ``op=fix`` only — runs the
    metadata-only integrity check to decide whether the apply path would
    no-op.

    Returns exit code 0 on success, 1 on uncaught failure (matches the
    existing inventory CLI convention).
    """
    from backend.puzzle_manager.inventory.check import check_integrity
    from backend.puzzle_manager.models.inventory_preview import (
        InventoryMutationPreview,
    )
    from backend.puzzle_manager.paths import get_output_dir

    op: str
    if getattr(args, "rebuild", False):
        op = "rebuild"
    elif getattr(args, "reconcile", False):
        op = "reconcile"
    else:
        op = "fix"

    output_dir = get_output_dir()
    sgf_dir = output_dir / "sgf"
    disk_total = sum(1 for _ in sgf_dir.rglob("*.sgf")) if sgf_dir.exists() else 0

    snapshot_exists = manager.exists()
    snapshot_total: int | None = None
    if snapshot_exists:
        try:
            snapshot_total = manager.load().collection.total_puzzles
        except Exception as exc:
            logger.warning("Snapshot present but unreadable; treating as absent: %s", exc)
            snapshot_exists = False

    delta = disk_total - (snapshot_total or 0)

    fix_skip_reason: str | None = None
    would_rewrite_snapshot = True
    if op == "fix":
        inventory = manager.load() if snapshot_exists else None
        result = check_integrity(inventory=inventory)
        if result.is_valid:
            fix_skip_reason = (
                "Inventory is already consistent — `inventory --fix` would no-op."
            )
            would_rewrite_snapshot = False

    preview = InventoryMutationPreview(
        op=op,  # type: ignore[arg-type]
        snapshot_exists=snapshot_exists,
        snapshot_total_before=snapshot_total,
        disk_total=disk_total,
        delta=delta,
        would_rewrite_snapshot=would_rewrite_snapshot,
        # Only --rebuild also rewrites yengo-search.db today; reconcile/fix
        # leave the search DB alone.
        would_rebuild_search_db=(op == "rebuild"),
        fix_skip_reason=fix_skip_reason,
    )

    if getattr(args, "json", False):
        print(preview.model_dump_json())
    else:
        print(_format_mutation_preview_human(preview))
    return 0


def _format_mutation_preview_human(preview: object) -> str:
    """Plain-text rendering of the preview for terminal use."""
    p = preview  # local alias for brevity
    lines = [
        f"Inventory --{p.op} --dry-run",  # type: ignore[attr-defined]
        "─" * 40,
        f"Snapshot present:  {p.snapshot_exists}",  # type: ignore[attr-defined]
        f"Snapshot total:    {p.snapshot_total_before if p.snapshot_total_before is not None else '—'}",  # type: ignore[attr-defined]
        f"Disk total:        {p.disk_total}",  # type: ignore[attr-defined]
        f"Delta:             {p.delta:+d}",  # type: ignore[attr-defined]
        f"Would rewrite snapshot:    {p.would_rewrite_snapshot}",  # type: ignore[attr-defined]
        f"Would rebuild search DB:   {p.would_rebuild_search_db}",  # type: ignore[attr-defined]
    ]
    if p.fix_skip_reason:  # type: ignore[attr-defined]
        lines.append("")
        lines.append(f"Note: {p.fix_skip_reason}")  # type: ignore[attr-defined]
    return "\n".join(lines)
