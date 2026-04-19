"""
SGF Directory Merge CLI.

Merges puzzle files from two directories by combining solution trees and
comments from matched puzzles. Uses compare_dirs indexing and D4-aware
position matching to find matches, then applies merge decisions.

Usage:
    python tools/puzzle-manager-scripts/merge_dirs.py \\
      --primary "external-sources/authors/TSUMEGO CLASSIC - Xuan Xuan Qi Jing-enriched" \\
      --secondary "external-sources/t-hero/sgf-by-global-slug/xuanxuan-qijing" \\
      [--output "path/to/output"] \\
      [--dry-run] \\
      [--min-level 4]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import argparse
import json
import logging
import shutil
import time
from datetime import UTC, datetime

from tools.core.logging import format_duration, setup_logging
from tools.core.paths import get_project_root, rel_path
from tools.core.position_transform import find_transform
from tools.core.sgf_compare import classify_match, make_unmatched_result
from tools.core.sgf_merge import (
    build_merged_sgf,
    merge_comments,
    merge_solution_trees,
    plan_merge,
)

# Import index building from compare_dirs (same directory)
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from compare_dirs import ParsedFile, _build_index as build_index

logger = logging.getLogger("merge_dirs")

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_BASE = SCRIPT_DIR / "output"


# ---------------------------------------------------------------------------
# Merge engine
# ---------------------------------------------------------------------------


def _merge_directories(
    primary_dir: Path,
    secondary_dir: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
    min_level: int = 4,
    in_place: bool = False,
    log: logging.Logger | None = None,
) -> dict:
    """Merge SGF files from two directories.

    When in_place=True, merged files are written back to primary_dir
    (only matched files are touched). Unmatched files are ignored.

    Returns summary dict with counts and decisions.
    """
    if log is None:
        log = logger

    # Build indexes for both directories
    log.info("Building primary index...")
    pri_pos, pri_canonical, pri_names, pri_errors = build_index(primary_dir, "primary", log)

    log.info("Building secondary index...")
    sec_pos, sec_canonical, sec_names, sec_errors = build_index(secondary_dir, "secondary", log)

    # Collect all primary files in deterministic order
    all_primary: list[ParsedFile] = []
    for pf_list in pri_pos.values():
        all_primary.extend(pf_list)
    all_primary.sort(key=lambda pf: pf.rel_path)

    # Track matched secondary files
    matched_secondary: set[str] = set()

    # Merge decisions and stats
    decisions: list[dict] = []
    action_counts: dict[str, int] = {}
    sgf_dir = output_dir / "sgf" if not in_place else None

    if not dry_run and sgf_dir is not None:
        sgf_dir.mkdir(parents=True, exist_ok=True)

    # Process each primary file
    for pf in all_primary:
        # Find match in secondary (same 3-tier cascade as compare_dirs)
        target_pf = None
        transform = None

        # Tier 1: Identity hash
        candidates = sec_pos.get(pf.pos_hash, [])
        if candidates:
            target_pf = candidates[0]
        else:
            # Tier 2: D4 canonical hash
            canonical_candidates = sec_canonical.get(pf.canonical_hash, [])
            for cand in canonical_candidates:
                t = find_transform(
                    pf.tree.black_stones, pf.tree.white_stones,
                    cand.tree.black_stones, cand.tree.white_stones,
                    pf.tree.board_size,
                )
                if t is not None:
                    target_pf = cand
                    transform = t
                    break

        if target_pf:
            matched_secondary.add(target_pf.rel_path)

            # Classify the match
            compare_result = classify_match(
                pf.tree, target_pf.tree,
                pf.rel_path, target_pf.rel_path,
                raw_a=pf.raw, raw_b=target_pf.raw,
                transform=transform,
            )

            # Decide merge action
            decision = plan_merge(
                compare_result,
                min_level=min_level,
                primary_tree=pf.tree,
                secondary_tree=target_pf.tree,
            )
        else:
            # No match — copy primary
            compare_result = make_unmatched_result(pf.rel_path, pf.tree)
            decision = plan_merge(compare_result, min_level=min_level)

        # Execute the action
        action = decision.action
        action_counts[action] = action_counts.get(action, 0) + 1

        if not dry_run:
            _execute_merge_action(
                decision, pf, target_pf, sgf_dir, pf.tree.board_size, log,
                in_place=in_place,
            )

        decisions.append(decision.to_dict())

    # Handle unmatched secondary files (skip in in-place mode)
    unmatched_secondary_count = 0
    if not in_place:
        for sec_list in sec_pos.values():
            for sec_pf in sec_list:
                if sec_pf.rel_path not in matched_secondary:
                    unmatched_secondary_count += 1
                    if not dry_run:
                        out_path = sgf_dir / sec_pf.path.name
                        shutil.copy2(sec_pf.path, out_path)

    # Analyze skipped matches — quantify missed value
    skip_analysis = _analyze_skips(decisions, all_primary, pri_pos, sec_pos, sec_canonical)

    return {
        "primary_count": len(all_primary),
        "secondary_count": sum(len(v) for v in sec_pos.values()),
        "primary_errors": len(pri_errors),
        "secondary_errors": len(sec_errors),
        "matched": sum(
            v for k, v in action_counts.items() if k != "copy_primary"
        ),
        "action_counts": action_counts,
        "decisions": decisions,
        "unmatched_secondary": unmatched_secondary_count,
        "skip_analysis": skip_analysis,
    }


def _execute_merge_action(
    decision,
    primary_pf: ParsedFile,
    secondary_pf: ParsedFile | None,
    sgf_dir: Path | None,
    board_size: int,
    log: logging.Logger,
    *,
    in_place: bool = False,
) -> None:
    """Execute a single merge action, writing the result.

    When in_place=True, writes back to primary_pf.path.
    When in_place=False, writes to sgf_dir.
    """
    out_path = primary_pf.path if in_place else sgf_dir / primary_pf.path.name

    if decision.action == "use_primary" or decision.action == "copy_primary":
        if not in_place:
            # Only copy when writing to output dir; in-place already has the file
            shutil.copy2(primary_pf.path, out_path)

    elif decision.action == "use_secondary" and secondary_pf:
        # Use secondary's tree but in primary's orientation
        # We need to transform secondary to primary's coordinate system
        if decision.transform and not decision.transform.is_identity:
            from tools.core.position_transform import inverse_transform, transform_node

            inv = inverse_transform(decision.transform)
            transformed_solution = transform_node(
                secondary_pf.tree.solution_tree,
                board_size,
                inv,
            )
            merged_comment = merge_comments(
                primary_pf.tree.root_comment,
                secondary_pf.tree.root_comment,
            )
            sgf = build_merged_sgf(primary_pf.tree, transformed_solution, merged_comment)
        else:
            # Same orientation — use secondary's solution directly
            merged_comment = merge_comments(
                primary_pf.tree.root_comment,
                secondary_pf.tree.root_comment,
            )
            sgf = build_merged_sgf(primary_pf.tree, secondary_pf.tree.solution_tree, merged_comment)

        out_path.write_text(sgf, encoding="utf-8")

    elif decision.action == "merge_trees" and secondary_pf:
        merged_solution = merge_solution_trees(
            primary_pf.tree.solution_tree,
            secondary_pf.tree.solution_tree,
            board_size,
            decision.transform,
        )
        merged_comment = merge_comments(
            primary_pf.tree.root_comment,
            secondary_pf.tree.root_comment,
        )
        sgf = build_merged_sgf(primary_pf.tree, merged_solution, merged_comment)
        out_path.write_text(sgf, encoding="utf-8")

    elif decision.action == "merge_trees_inferred" and secondary_pf:
        merged_solution = merge_solution_trees(
            primary_pf.tree.solution_tree,
            secondary_pf.tree.solution_tree,
            board_size,
            decision.transform,
            primary_correctness_wins=True,
        )
        merged_comment = merge_comments(
            primary_pf.tree.root_comment,
            secondary_pf.tree.root_comment,
        )
        sgf = build_merged_sgf(primary_pf.tree, merged_solution, merged_comment)
        out_path.write_text(sgf, encoding="utf-8")

    elif decision.action == "skip":
        # Don't write anything for skipped files
        pass
    else:
        log.warning(f"Unknown action '{decision.action}' for {primary_pf.rel_path}")


def _analyze_skips(
    decisions: list[dict],
    all_primary: list[ParsedFile],
    pri_pos: dict[str, list[ParsedFile]],
    sec_pos: dict[str, list[ParsedFile]],
    sec_canonical: dict[str, list[ParsedFile]],
) -> dict:
    """Analyze skipped matches to quantify missed merge value.

    For Level 3 skips, checks if the secondary source marks all first moves
    as correct (indicating a different correctness convention rather than a
    genuinely different solution). Computes node count ratios to show the
    potential value of these matches.
    """
    from tools.core.sgf_analysis import count_total_nodes

    skipped = [d for d in decisions if d["action"] == "skip" and d.get("target_file")]
    if not skipped:
        return {"skip_count": 0}

    # Build secondary lookup by rel_path
    sec_by_path: dict[str, ParsedFile] = {}
    for pf_list in sec_pos.values():
        for pf in pf_list:
            sec_by_path[pf.rel_path] = pf
    for pf_list in sec_canonical.values():
        for pf in pf_list:
            sec_by_path[pf.rel_path] = pf

    # Build primary lookup by rel_path
    pri_by_path: dict[str, ParsedFile] = {}
    for pf in all_primary:
        pri_by_path[pf.rel_path] = pf

    total_pri_nodes = 0
    total_sec_nodes = 0
    all_sec_correct_count = 0
    sec_richer_count = 0
    first_move_diff = 0
    correct_line_diff = 0

    for d in skipped:
        tgt_path = d["target_file"]
        src_path = d["source_file"]
        sec_pf = sec_by_path.get(tgt_path)
        pri_pf = pri_by_path.get(src_path)
        if not sec_pf or not pri_pf:
            continue

        pri_nodes = count_total_nodes(pri_pf.tree.solution_tree)
        sec_nodes = count_total_nodes(sec_pf.tree.solution_tree)
        total_pri_nodes += pri_nodes
        total_sec_nodes += sec_nodes

        if sec_nodes > pri_nodes:
            sec_richer_count += 1

        # Check if secondary marks ALL first moves as correct
        sec_children = sec_pf.tree.solution_tree.children
        if sec_children and all(c.is_correct for c in sec_children):
            all_sec_correct_count += 1

        # Categorize skip reason
        reason = d.get("reason", "")
        if "first correct move differs" in reason:
            first_move_diff += 1
        elif "correct line diverges" in reason:
            correct_line_diff += 1

    return {
        "skip_count": len(skipped),
        "total_pri_nodes": total_pri_nodes,
        "total_sec_nodes": total_sec_nodes,
        "node_ratio": round(total_sec_nodes / total_pri_nodes, 1) if total_pri_nodes else 0,
        "sec_richer_count": sec_richer_count,
        "all_sec_correct_count": all_sec_correct_count,
        "first_move_diff": first_move_diff,
        "correct_line_diff": correct_line_diff,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _write_manifest(decisions: list[dict], output_dir: Path) -> Path:
    """Write merge manifest as JSONL."""
    path = output_dir / "manifest.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return path


def _write_summary(
    summary: dict,
    primary_dir: Path,
    secondary_dir: Path,
    duration_sec: float,
    output_dir: Path,
) -> Path:
    """Write Markdown summary report."""
    path = output_dir / "summary.md"
    action_counts = summary["action_counts"]

    lines = [
        "## SGF Directory Merge Report",
        "",
        f"- **Run:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Duration:** {format_duration(duration_sec)}",
        f"- **Primary:** {rel_path(str(primary_dir))} ({summary['primary_count']} files)",
        f"- **Secondary:** {rel_path(str(secondary_dir))} ({summary['secondary_count']} files)",
        "",
        "### Actions",
        "",
        "| Action | Count |",
        "|--------|------:|",
    ]

    for action in ["merge_trees", "merge_trees_inferred", "use_secondary", "use_primary", "copy_primary", "skip"]:
        count = action_counts.get(action, 0)
        if count > 0:
            lines.append(f"| {action} | {count} |")

    lines.extend([
        "",
        "### Summary",
        "",
        f"- Primary files: {summary['primary_count']}",
        f"- Secondary files: {summary['secondary_count']}",
        f"- Matched pairs: {summary['matched']}",
        f"- Unmatched secondary: {summary['unmatched_secondary']}",
        f"- Primary parse errors: {summary['primary_errors']}",
        f"- Secondary parse errors: {summary['secondary_errors']}",
        "",
    ])

    # Skip analysis section
    sa = summary.get("skip_analysis", {})
    if sa.get("skip_count", 0) > 0:
        lines.extend([
            "### Skipped Match Analysis",
            "",
            f"**{sa['skip_count']}** position matches were skipped (Level 3: solution differs).",
            "",
            f"- First correct move differs: {sa.get('first_move_diff', 0)}",
            f"- Correct line diverges: {sa.get('correct_line_diff', 0)}",
            f"- Secondary marks ALL first moves as correct: "
            f"**{sa.get('all_sec_correct_count', 0)}/{sa['skip_count']}**",
            "",
            "#### Potential value if merged",
            "",
            f"- Primary solution nodes (total): {sa.get('total_pri_nodes', 0)}",
            f"- Secondary solution nodes (total): {sa.get('total_sec_nodes', 0)}",
            f"- Node ratio: **{sa.get('node_ratio', 0)}x** more in secondary",
            f"- Cases where secondary has richer trees: "
            f"{sa.get('sec_richer_count', 0)}/{sa['skip_count']}",
            "",
            "*These matches are blocked because the secondary source uses a different "
            "correctness convention (all moves marked correct, including refutations). "
            "The position match is confirmed via D4 symmetry.*",
            "",
        ])

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def _print_console_summary(
    summary: dict,
    primary_dir: Path,
    secondary_dir: Path,
    duration: float,
) -> None:
    """Print merge summary to console."""
    action_counts = summary["action_counts"]

    print(f"\n--- Merge Summary ({format_duration(duration)}) ---")
    print(f"  Primary: {rel_path(str(primary_dir))} ({summary['primary_count']} files)")
    print(f"  Secondary: {rel_path(str(secondary_dir))} ({summary['secondary_count']} files)")
    print(f"  Matched pairs: {summary['matched']}")
    print("  Actions:")
    for action in ["merge_trees", "merge_trees_inferred", "use_secondary", "use_primary", "copy_primary", "skip"]:
        count = action_counts.get(action, 0)
        if count > 0:
            print(f"    {action}: {count}")
    if summary["unmatched_secondary"] > 0:
        print(f"  Unmatched secondary (copied as-is): {summary['unmatched_secondary']}")

    # Skip analysis
    sa = summary.get("skip_analysis", {})
    if sa.get("skip_count", 0) > 0:
        print(f"  Skipped matches: {sa['skip_count']} (Level 3: solution differs)")
        if sa.get("all_sec_correct_count", 0) > 0:
            print(f"    Secondary marks all moves correct: {sa['all_sec_correct_count']}/{sa['skip_count']}")
            print(f"    Potential value: {sa.get('node_ratio', 0)}x more nodes in secondary "
                  f"({sa.get('total_sec_nodes', 0)} vs {sa.get('total_pri_nodes', 0)})")
            print(f"    Secondary is richer: {sa.get('sec_richer_count', 0)}/{sa['skip_count']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_dir(path_str: str) -> Path:
    """Resolve a directory path (relative to project root or absolute)."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return get_project_root() / p


def _normalize_name(path_str: str) -> str:
    """Extract leaf directory name and normalize to filesystem-safe form."""
    import re as _re

    name = path_str.replace("\\", "/").strip("/")
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    name = _re.sub(r"[^a-zA-Z0-9-]", "_", name)
    name = _re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge two directories of SGF tsumego files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--primary",
        required=True,
        help="Primary directory (orientation preserved, comments preferred)",
    )
    parser.add_argument(
        "--secondary",
        required=True,
        help="Secondary directory (solution trees merged in)",
    )
    parser.add_argument(
        "--output",
        help="Output directory (default: auto-generated under output/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only, no SGF writes",
    )
    parser.add_argument(
        "--min-level",
        type=int,
        default=4,
        help="Minimum match level to merge (default: 4)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Merge matched files in-place (update primary directory, ignore unmatched)",
    )

    args = parser.parse_args()

    primary_dir = _resolve_dir(args.primary)
    secondary_dir = _resolve_dir(args.secondary)

    if not primary_dir.is_dir():
        print(f"Error: primary directory not found: {primary_dir}", file=sys.stderr)
        sys.exit(1)
    if not secondary_dir.is_dir():
        print(f"Error: secondary directory not found: {secondary_dir}", file=sys.stderr)
        sys.exit(1)

    # Output directory
    in_place = args.in_place
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if in_place:
        output_dir = OUTPUT_BASE / f"{timestamp}_inplace_{_normalize_name(args.primary)}"
    elif args.output:
        output_dir = _resolve_dir(args.output)
    else:
        dir_name = f"{timestamp}_merge_{_normalize_name(args.primary)}__with__{_normalize_name(args.secondary)}"
        output_dir = OUTPUT_BASE / dir_name

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    structured_log = setup_logging(
        output_dir if not args.dry_run else Path("."),
        "merge_dirs",
        verbose=False,
        log_to_file=not args.dry_run,
        log_suffix="merge",
    )

    structured_log.run_start(
        output_dir=str(output_dir),
        dry_run=args.dry_run,
        in_place=in_place,
        primary=str(primary_dir),
        secondary=str(secondary_dir),
        min_level=args.min_level,
    )

    start_time = time.monotonic()

    summary = _merge_directories(
        primary_dir,
        secondary_dir,
        output_dir,
        dry_run=args.dry_run,
        min_level=args.min_level,
        in_place=in_place,
        log=logging.getLogger("merge_dirs"),
    )

    duration = time.monotonic() - start_time

    _print_console_summary(summary, primary_dir, secondary_dir, duration)

    if not args.dry_run:
        manifest_path = _write_manifest(summary["decisions"], output_dir)
        summary_path = _write_summary(
            summary, primary_dir, secondary_dir, duration, output_dir,
        )

        if in_place:
            merged_count = sum(
                v for k, v in summary["action_counts"].items()
                if k in ("merge_trees", "merge_trees_inferred", "use_secondary")
            )
            print(f"\n  Updated {merged_count} files in-place in {rel_path(str(primary_dir))}/")
            print(f"  Log: {rel_path(str(output_dir))}/")
        else:
            print(f"\n  Output: {rel_path(str(output_dir))}/")
            print(f"    {manifest_path.name}")
            print(f"    {summary_path.name}")
            print(f"    sgf/ ({len(list((output_dir / 'sgf').glob('*.sgf')))} files)")

    structured_log.run_end(
        downloaded=summary["primary_count"],
        skipped=summary["action_counts"].get("skip", 0),
        errors=summary["primary_errors"] + summary["secondary_errors"],
        duration_sec=duration,
    )


if __name__ == "__main__":
    main()
