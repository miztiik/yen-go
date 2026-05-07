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
            return _apply_fix(args, manager)

        if getattr(args, "reconcile", False):
            return _apply_reconcile(args, manager)

        if getattr(args, "rebuild", False):
            return _apply_rebuild(args, manager)

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
        would_rebuild_search_db=False,
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


def _emit_apply_result(args: "argparse.Namespace", result: object) -> None:
    """Print the apply result as JSON (when --json) or human text."""
    if getattr(args, "json", False):
        print(result.model_dump_json())  # type: ignore[attr-defined]
        return
    r = result
    lines = [
        f"Inventory --{r.op}",  # type: ignore[attr-defined]
        "─" * 40,
        f"Executed:                  {r.executed}",  # type: ignore[attr-defined]
        f"Snapshot total before:     {r.snapshot_total_before if r.snapshot_total_before is not None else '—'}",  # type: ignore[attr-defined]
        f"Snapshot total after:      {r.snapshot_total_after}",  # type: ignore[attr-defined]
        f"Delta:                     {r.delta:+d}",  # type: ignore[attr-defined]
        f"Rewrote snapshot:          {r.rewrote_snapshot}",  # type: ignore[attr-defined]
        f"Rebuilt search DB:         {r.rebuilt_search_db}",  # type: ignore[attr-defined]
    ]
    if r.audit_timestamp:  # type: ignore[attr-defined]
        lines.append(f"Audit timestamp:           {r.audit_timestamp}")  # type: ignore[attr-defined]
    if r.fix_skip_reason:  # type: ignore[attr-defined]
        lines.append("")
        lines.append(f"Note: {r.fix_skip_reason}")  # type: ignore[attr-defined]
    print("\n".join(lines))


def _snapshot_total(manager: InventoryManager) -> int | None:
    """Read current snapshot total puzzles, or None when no snapshot exists."""
    if not manager.exists():
        return None
    try:
        return manager.load().collection.total_puzzles
    except Exception as exc:
        logger.warning("Snapshot present but unreadable; treating as absent: %s", exc)
        return None


def _audit_inventory_op(
    op: str,
    *,
    total_before: int | None,
    total_after: int,
    rewrote_snapshot: bool,
    rebuilt_search_db: bool,
) -> str:
    """Append an audit entry for an inventory mutation. Returns the timestamp."""
    from datetime import UTC, datetime

    from backend.puzzle_manager.audit import write_audit_entry
    from backend.puzzle_manager.paths import get_audit_log_path

    timestamp = datetime.now(UTC).isoformat()
    write_audit_entry(
        audit_file=get_audit_log_path(),
        operation=f"inventory_{op}",
        target="puzzle-collection",
        details={
            "timestamp": timestamp,
            "total_before": total_before,
            "total_after": total_after,
            "delta": total_after - (total_before or 0),
            "rewrote_snapshot": rewrote_snapshot,
            "rebuilt_search_db": rebuilt_search_db,
        },
    )
    return timestamp


def _apply_rebuild(
    args: "argparse.Namespace", manager: InventoryManager
) -> int:
    """Theme 14c2: lock + rebuild inventory snapshot + audit."""
    from backend.puzzle_manager.inventory.reconcile import reconcile_inventory
    from backend.puzzle_manager.models.inventory_preview import (
        InventoryMutationResult,
    )
    from backend.puzzle_manager.pipeline.lock import PipelineLock

    total_before = _snapshot_total(manager)

    with PipelineLock(run_id="inventory-rebuild"):
        logger.info("Rebuilding inventory from SGF files...")
        inventory = reconcile_inventory()
        manager.save(inventory)
        total_after = inventory.collection.total_puzzles
        timestamp = _audit_inventory_op(
            "rebuild",
            total_before=total_before,
            total_after=total_after,
            rewrote_snapshot=True,
            rebuilt_search_db=False,
        )

    result = InventoryMutationResult(
        op="rebuild",
        executed=True,
        snapshot_total_before=total_before,
        snapshot_total_after=total_after,
        delta=total_after - (total_before or 0),
        rewrote_snapshot=True,
        rebuilt_search_db=False,
        audit_timestamp=timestamp,
    )
    _emit_apply_result(args, result)
    return 0


def _apply_reconcile(
    args: "argparse.Namespace", manager: InventoryManager
) -> int:
    """Theme 14c2: lock + reconcile inventory from disk + audit."""
    from backend.puzzle_manager.inventory.reconcile import reconcile_inventory
    from backend.puzzle_manager.models.inventory_preview import (
        InventoryMutationResult,
    )
    from backend.puzzle_manager.pipeline.lock import PipelineLock

    total_before = _snapshot_total(manager)

    with PipelineLock(run_id="inventory-reconcile"):
        logger.info("Reconciling inventory from SGF files on disk...")
        inventory = reconcile_inventory(run_id=None)
        manager.save(inventory)
        total_after = inventory.collection.total_puzzles
        timestamp = _audit_inventory_op(
            "reconcile",
            total_before=total_before,
            total_after=total_after,
            rewrote_snapshot=True,
            rebuilt_search_db=False,
        )

    result = InventoryMutationResult(
        op="reconcile",
        executed=True,
        snapshot_total_before=total_before,
        snapshot_total_after=total_after,
        delta=total_after - (total_before or 0),
        rewrote_snapshot=True,
        rebuilt_search_db=False,
        audit_timestamp=timestamp,
    )
    _emit_apply_result(args, result)
    return 0


def _apply_fix(
    args: "argparse.Namespace", manager: InventoryManager
) -> int:
    """Theme 14c2: lock + fix inventory (no-op when clean) + audit on success."""
    from backend.puzzle_manager.inventory.check import (
        check_integrity,
        fix_integrity,
    )
    from backend.puzzle_manager.models.inventory_preview import (
        InventoryMutationResult,
    )
    from backend.puzzle_manager.pipeline.lock import PipelineLock

    total_before = _snapshot_total(manager)

    inventory = manager.load() if manager.exists() else None
    pre = check_integrity(inventory=inventory)
    if pre.is_valid:
        result = InventoryMutationResult(
            op="fix",
            executed=True,
            snapshot_total_before=total_before,
            snapshot_total_after=total_before or 0,
            delta=0,
            rewrote_snapshot=False,
            rebuilt_search_db=False,
            audit_timestamp=None,
            fix_skip_reason=(
                "Inventory is already consistent — `inventory --fix` skipped."
            ),
        )
        _emit_apply_result(args, result)
        return 0

    with PipelineLock(run_id="inventory-fix"):
        logger.info("Fixing inventory...")
        fixed = fix_integrity()
        manager.save(fixed)
        total_after = fixed.collection.total_puzzles
        post = check_integrity(inventory=fixed)
        timestamp = _audit_inventory_op(
            "fix",
            total_before=total_before,
            total_after=total_after,
            rewrote_snapshot=True,
            rebuilt_search_db=False,
        )

    result = InventoryMutationResult(
        op="fix",
        executed=True,
        snapshot_total_before=total_before,
        snapshot_total_after=total_after,
        delta=total_after - (total_before or 0),
        rewrote_snapshot=True,
        rebuilt_search_db=False,
        audit_timestamp=timestamp,
    )
    _emit_apply_result(args, result)
    # Match the prior CLI contract: rc=1 when post-fix issues remain.
    return 0 if post.is_valid else 1
