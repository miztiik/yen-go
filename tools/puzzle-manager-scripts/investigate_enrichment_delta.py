"""
Enrichment Delta Investigation.

Compares two SGF directories containing the same puzzle collection to quantify
enrichment differences: comment richness, solution tree depth/breadth,
overlap percentage, and merge feasibility.

Read-only investigation — does NOT modify any SGF files.

Usage:
    python tools/puzzle-manager-scripts/investigate_enrichment_delta.py \
      --set-a "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - Xuan Xuan Qi Jing" \
      --set-b "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - Xuan Xuan Qi Jing-enriched"
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import argparse
import json
from dataclasses import dataclass, field

from tools.core.sgf_analysis import (
    compute_main_line_depth,
    count_stones,
    count_total_nodes,
    get_all_paths,
    max_branch_depth,
)
from tools.core.sgf_compare import position_hash
from tools.core.sgf_parser import SgfTree, parse_sgf, read_sgf_file


# ---------------------------------------------------------------------------
# Per-puzzle metrics
# ---------------------------------------------------------------------------


@dataclass
class PuzzleMetrics:
    """Enrichment metrics for a single puzzle."""

    filename: str
    stones: int = 0
    solution_nodes: int = 0
    solution_depth: int = 0
    max_depth: int = 0
    num_paths: int = 0
    root_comment_len: int = 0
    move_comments_count: int = 0
    move_comments_total_chars: int = 0
    has_game_name: bool = False
    has_difficulty: bool = False
    position_hash: str = ""
    parse_error: str | None = None


def _count_move_comments(node) -> tuple[int, int]:
    """Count move-level comments (count, total_chars) recursively."""
    count = 0
    chars = 0
    if node.comment:
        count += 1
        chars += len(node.comment)
    for child in node.children:
        c, ch = _count_move_comments(child)
        count += c
        chars += ch
    return count, chars


def _extract_metrics(filename: str, tree: SgfTree) -> PuzzleMetrics:
    """Extract enrichment metrics from a parsed SGF tree."""
    m = PuzzleMetrics(filename=filename)
    m.stones = count_stones(tree)
    m.position_hash = position_hash(tree)

    if tree.has_solution:
        m.solution_nodes = count_total_nodes(tree.solution_tree)
        m.solution_depth = compute_main_line_depth(tree.solution_tree)
        m.max_depth = max_branch_depth(tree.solution_tree)
        m.num_paths = len(get_all_paths(tree.solution_tree))
        mc, mch = _count_move_comments(tree.solution_tree)
        m.move_comments_count = mc
        m.move_comments_total_chars = mch

    m.root_comment_len = len(tree.root_comment) if tree.root_comment else 0

    # Check for GN and YG via raw SGF (parser may not expose all standard props)
    raw = tree.raw_sgf if hasattr(tree, "raw_sgf") else ""
    m.has_game_name = "GN[" in raw
    m.has_difficulty = bool(tree.yengo_props and tree.yengo_props.level_slug) or "YG[" in raw

    return m


def _parse_directory(directory: Path) -> dict[str, PuzzleMetrics]:
    """Parse all SGFs in a directory and return metrics keyed by filename."""
    results: dict[str, PuzzleMetrics] = {}
    sgf_files = sorted(f for f in directory.iterdir() if f.suffix.lower() == ".sgf")

    for sgf_path in sgf_files:
        fname = sgf_path.name
        try:
            raw, _ = read_sgf_file(sgf_path)
            tree = parse_sgf(raw)
            m = _extract_metrics(fname, tree)
            results[fname] = m
        except Exception as e:
            results[fname] = PuzzleMetrics(filename=fname, parse_error=str(e))

    return results


# ---------------------------------------------------------------------------
# Comparison & reporting
# ---------------------------------------------------------------------------


@dataclass
class SetSummary:
    """Aggregate stats for one set."""

    label: str
    total_files: int = 0
    parse_errors: int = 0
    avg_stones: float = 0.0
    avg_solution_nodes: float = 0.0
    avg_solution_depth: float = 0.0
    avg_max_depth: float = 0.0
    avg_paths: float = 0.0
    avg_root_comment_len: float = 0.0
    avg_move_comments_count: float = 0.0
    avg_move_comments_chars: float = 0.0
    pct_with_game_name: float = 0.0
    pct_with_difficulty: float = 0.0
    total_move_comments: int = 0
    total_comment_chars: int = 0


def _summarize(label: str, metrics: dict[str, PuzzleMetrics]) -> SetSummary:
    """Compute aggregate statistics for a set."""
    s = SetSummary(label=label, total_files=len(metrics))
    valid = [m for m in metrics.values() if m.parse_error is None]
    n = len(valid) or 1
    s.parse_errors = s.total_files - len(valid)
    s.avg_stones = sum(m.stones for m in valid) / n
    s.avg_solution_nodes = sum(m.solution_nodes for m in valid) / n
    s.avg_solution_depth = sum(m.solution_depth for m in valid) / n
    s.avg_max_depth = sum(m.max_depth for m in valid) / n
    s.avg_paths = sum(m.num_paths for m in valid) / n
    s.avg_root_comment_len = sum(m.root_comment_len for m in valid) / n
    s.avg_move_comments_count = sum(m.move_comments_count for m in valid) / n
    s.avg_move_comments_chars = sum(m.move_comments_total_chars for m in valid) / n
    s.pct_with_game_name = sum(1 for m in valid if m.has_game_name) / n * 100
    s.pct_with_difficulty = sum(1 for m in valid if m.has_difficulty) / n * 100
    s.total_move_comments = sum(m.move_comments_count for m in valid)
    s.total_comment_chars = sum(m.move_comments_total_chars for m in valid)
    return s


def _compare_and_report(
    set_a: dict[str, PuzzleMetrics],
    set_b: dict[str, PuzzleMetrics],
    label_a: str,
    label_b: str,
) -> str:
    """Compare two sets and produce a Markdown report."""
    lines: list[str] = []

    sum_a = _summarize(label_a, set_a)
    sum_b = _summarize(label_b, set_b)

    # --- Position overlap ---
    hashes_a = {m.position_hash for m in set_a.values() if not m.parse_error}
    hashes_b = {m.position_hash for m in set_b.values() if not m.parse_error}
    overlap = hashes_a & hashes_b
    only_a = hashes_a - hashes_b
    only_b = hashes_b - hashes_a
    overlap_pct = len(overlap) / max(len(hashes_a | hashes_b), 1) * 100

    lines.append("# Enrichment Delta Investigation Report")
    lines.append("")
    lines.append(f"- **Set A**: {label_a} ({sum_a.total_files} files)")
    lines.append(f"- **Set B**: {label_b} ({sum_b.total_files} files)")
    lines.append("")

    # --- 1. Position Overlap ---
    lines.append("## 1. Position Overlap")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|------:|")
    lines.append(f"| Unique positions in A | {len(hashes_a)} |")
    lines.append(f"| Unique positions in B | {len(hashes_b)} |")
    lines.append(f"| **Overlap** | **{len(overlap)}** ({overlap_pct:.1f}%) |")
    lines.append(f"| Only in A | {len(only_a)} |")
    lines.append(f"| Only in B | {len(only_b)} |")
    lines.append("")

    # --- 2. Aggregate Comparison ---
    lines.append("## 2. Aggregate Comparison")
    lines.append("")
    lines.append("| Metric | Set A | Set B | Delta |")
    lines.append("|--------|------:|------:|------:|")

    def _row(name: str, va: float, vb: float, fmt: str = ".1f") -> str:
        delta = vb - va
        sign = "+" if delta > 0 else ""
        return f"| {name} | {va:{fmt}} | {vb:{fmt}} | {sign}{delta:{fmt}} |"

    lines.append(_row("Avg stones", sum_a.avg_stones, sum_b.avg_stones))
    lines.append(_row("Avg solution nodes", sum_a.avg_solution_nodes, sum_b.avg_solution_nodes))
    lines.append(_row("Avg solution depth", sum_a.avg_solution_depth, sum_b.avg_solution_depth))
    lines.append(_row("Avg max depth", sum_a.avg_max_depth, sum_b.avg_max_depth))
    lines.append(_row("Avg paths", sum_a.avg_paths, sum_b.avg_paths))
    lines.append(_row("Avg root comment (chars)", sum_a.avg_root_comment_len, sum_b.avg_root_comment_len))
    lines.append(_row("Avg move comments (count)", sum_a.avg_move_comments_count, sum_b.avg_move_comments_count))
    lines.append(_row("Avg move comments (chars)", sum_a.avg_move_comments_chars, sum_b.avg_move_comments_chars))
    lines.append(_row("% with game name", sum_a.pct_with_game_name, sum_b.pct_with_game_name))
    lines.append(_row("% with difficulty tag", sum_a.pct_with_difficulty, sum_b.pct_with_difficulty))
    lines.append(f"| Total move comments | {sum_a.total_move_comments} | {sum_b.total_move_comments} | +{sum_b.total_move_comments - sum_a.total_move_comments} |")
    lines.append(f"| Total comment chars | {sum_a.total_comment_chars} | {sum_b.total_comment_chars} | +{sum_b.total_comment_chars - sum_a.total_comment_chars} |")
    lines.append("")

    # --- 3. Per-puzzle enrichment winner ---
    lines.append("## 3. Per-Puzzle Enrichment Winner")
    lines.append("")

    a_wins = 0
    b_wins = 0
    ties = 0
    puzzle_details: list[dict] = []

    # Match by filename (both sets use 0001.sgf etc.)
    common_files = sorted(set(set_a.keys()) & set(set_b.keys()))

    for fname in common_files:
        ma = set_a[fname]
        mb = set_b[fname]
        if ma.parse_error or mb.parse_error:
            continue

        # Enrichment score: solution nodes + comment richness
        score_a = ma.solution_nodes + ma.move_comments_count * 2 + (1 if ma.root_comment_len > 0 else 0)
        score_b = mb.solution_nodes + mb.move_comments_count * 2 + (1 if mb.root_comment_len > 0 else 0)

        if score_a > score_b:
            winner = "A"
            a_wins += 1
        elif score_b > score_a:
            winner = "B"
            b_wins += 1
        else:
            winner = "tie"
            ties += 1

        # Track solution tree difference
        node_delta = mb.solution_nodes - ma.solution_nodes
        comment_delta = mb.move_comments_count - ma.move_comments_count

        puzzle_details.append({
            "file": fname,
            "winner": winner,
            "nodes_a": ma.solution_nodes,
            "nodes_b": mb.solution_nodes,
            "node_delta": node_delta,
            "comments_a": ma.move_comments_count,
            "comments_b": mb.move_comments_count,
            "comment_delta": comment_delta,
            "root_comment_a": ma.root_comment_len,
            "root_comment_b": mb.root_comment_len,
            "position_match": ma.position_hash == mb.position_hash,
        })

    total_compared = a_wins + b_wins + ties
    lines.append(f"Scoring: `solution_nodes + 2*move_comment_count + has_root_comment`")
    lines.append("")
    lines.append(f"| Winner | Count | % |")
    lines.append(f"|--------|------:|--:|")
    lines.append(f"| Set A better | {a_wins} | {a_wins / max(total_compared, 1) * 100:.1f}% |")
    lines.append(f"| Set B better | {b_wins} | {b_wins / max(total_compared, 1) * 100:.1f}% |")
    lines.append(f"| Tied | {ties} | {ties / max(total_compared, 1) * 100:.1f}% |")
    lines.append("")

    # --- 4. Solution tree divergence ---
    lines.append("## 4. Solution Tree Divergence")
    lines.append("")

    # Count puzzles where solution trees differ
    tree_diffs = [d for d in puzzle_details if d["node_delta"] != 0]
    tree_same = len(puzzle_details) - len(tree_diffs)
    lines.append(f"- Identical solution trees: {tree_same} ({tree_same / max(len(puzzle_details), 1) * 100:.1f}%)")
    lines.append(f"- Different solution trees: {len(tree_diffs)} ({len(tree_diffs) / max(len(puzzle_details), 1) * 100:.1f}%)")
    lines.append("")

    if tree_diffs:
        b_richer = sum(1 for d in tree_diffs if d["node_delta"] > 0)
        a_richer = sum(1 for d in tree_diffs if d["node_delta"] < 0)
        lines.append(f"  - B has more nodes: {b_richer}")
        lines.append(f"  - A has more nodes: {a_richer}")
        lines.append("")

        # Show top 10 biggest divergences
        by_delta = sorted(tree_diffs, key=lambda d: abs(d["node_delta"]), reverse=True)[:10]
        lines.append("### Top 10 Largest Tree Divergences")
        lines.append("")
        lines.append("| File | Nodes A | Nodes B | Delta | Comments A | Comments B |")
        lines.append("|------|--------:|--------:|------:|-----------:|-----------:|")
        for d in by_delta:
            sign = "+" if d["node_delta"] > 0 else ""
            lines.append(
                f"| {d['file']} | {d['nodes_a']} | {d['nodes_b']} | {sign}{d['node_delta']} "
                f"| {d['comments_a']} | {d['comments_b']} |"
            )
        lines.append("")

    # --- 5. Comment dimension ---
    lines.append("## 5. Comments Dimension")
    lines.append("")

    puzzles_with_comments_a = sum(1 for m in set_a.values() if not m.parse_error and m.move_comments_count > 0)
    puzzles_with_comments_b = sum(1 for m in set_b.values() if not m.parse_error and m.move_comments_count > 0)
    puzzles_with_root_a = sum(1 for m in set_a.values() if not m.parse_error and m.root_comment_len > 0)
    puzzles_with_root_b = sum(1 for m in set_b.values() if not m.parse_error and m.root_comment_len > 0)

    lines.append(f"| Metric | Set A | Set B |")
    lines.append(f"|--------|------:|------:|")
    lines.append(f"| Puzzles with move comments | {puzzles_with_comments_a} | {puzzles_with_comments_b} |")
    lines.append(f"| Puzzles with root comment | {puzzles_with_root_a} | {puzzles_with_root_b} |")
    lines.append(f"| Total move comments | {sum_a.total_move_comments} | {sum_b.total_move_comments} |")
    lines.append(f"| Total comment chars | {sum_a.total_comment_chars} | {sum_b.total_comment_chars} |")
    lines.append("")

    # --- 6. Position match verification ---
    lines.append("## 6. Position Match Verification")
    lines.append("")
    position_mismatches = [d for d in puzzle_details if not d["position_match"]]
    lines.append(f"- Position matches: {len(puzzle_details) - len(position_mismatches)}/{len(puzzle_details)}")
    if position_mismatches:
        lines.append(f"- **MISMATCHES**: {len(position_mismatches)}")
        for d in position_mismatches[:20]:
            lines.append(f"  - {d['file']}")
    else:
        lines.append(f"- All positions identical (100% overlap)")
    lines.append("")

    # --- 7. Merge feasibility ---
    lines.append("## 7. Merge Feasibility Assessment")
    lines.append("")

    # Can we take the richer tree from each and combine comments?
    identical_trees = tree_same
    comment_only_enrichment = sum(
        1 for d in puzzle_details
        if d["node_delta"] == 0 and d["comment_delta"] != 0
    )

    lines.append("### Scenarios")
    lines.append("")
    lines.append(f"1. **Same tree, B adds comments only**: {comment_only_enrichment} puzzles")
    lines.append(f"   - Merge strategy: Take A's tree structure, overlay B's comments → trivial")
    lines.append("")
    lines.append(f"2. **Same tree, same comments (no-op)**: {identical_trees - comment_only_enrichment} puzzles")
    lines.append(f"   - Merge strategy: Either set works, prefer B for metadata (GN, YG)")
    lines.append("")

    if tree_diffs:
        lines.append(f"3. **Different trees**: {len(tree_diffs)} puzzles")
        lines.append(f"   - Needs manual review or heuristic (take richer tree)")
        lines.append(f"   - B has more nodes in {b_richer} cases, A in {a_richer} cases")
        lines.append("")

    lines.append("### Recommendation")
    lines.append("")
    if len(position_mismatches) == 0 and len(tree_diffs) == 0:
        lines.append("**Simple merge**: Sets have identical positions AND identical trees.")
        lines.append("B strictly enriches A with comments and metadata. Use B as the canonical set.")
    elif len(position_mismatches) == 0 and comment_only_enrichment == len(tree_diffs):
        lines.append("**Clean merge possible**: All differences are comment-only additions.")
        lines.append("Use B as canonical set (superset of A).")
    elif len(position_mismatches) == 0:
        pct_easy = (len(puzzle_details) - len(tree_diffs)) / max(len(puzzle_details), 1) * 100
        lines.append(f"**Mostly mergeable**: {pct_easy:.0f}% of puzzles have identical trees.")
        lines.append(f"{len(tree_diffs)} puzzles need tree-level merge (take richer tree + combine comments).")
        lines.append("Automated merge feasible with per-puzzle best-tree selection.")
    else:
        lines.append("**Complex merge**: Position mismatches exist. Manual alignment needed first.")
    lines.append("")

    # --- 8. Parse errors ---
    errors_a = [m for m in set_a.values() if m.parse_error]
    errors_b = [m for m in set_b.values() if m.parse_error]
    if errors_a or errors_b:
        lines.append("## 8. Parse Errors")
        lines.append("")
        if errors_a:
            lines.append(f"### Set A ({len(errors_a)} errors)")
            for m in errors_a:
                lines.append(f"- {m.filename}: {m.parse_error}")
        if errors_b:
            lines.append(f"### Set B ({len(errors_b)} errors)")
            for m in errors_b:
                lines.append(f"- {m.filename}: {m.parse_error}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Investigate enrichment delta between two SGF directories.",
    )
    parser.add_argument("--set-a", required=True, help="Directory A (e.g. original)")
    parser.add_argument("--set-b", required=True, help="Directory B (e.g. enriched)")
    parser.add_argument("--output", help="Output markdown file (default: stdout)")
    args = parser.parse_args()

    root = Path(_PROJECT_ROOT)

    dir_a = Path(args.set_a) if Path(args.set_a).is_absolute() else root / args.set_a
    dir_b = Path(args.set_b) if Path(args.set_b).is_absolute() else root / args.set_b

    if not dir_a.is_dir():
        print(f"Error: {dir_a} is not a directory", file=sys.stderr)
        sys.exit(1)
    if not dir_b.is_dir():
        print(f"Error: {dir_b} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing Set A: {dir_a.name} ...", file=sys.stderr)
    set_a = _parse_directory(dir_a)
    print(f"  -> {len(set_a)} files", file=sys.stderr)

    print(f"Parsing Set B: {dir_b.name} ...", file=sys.stderr)
    set_b = _parse_directory(dir_b)
    print(f"  -> {len(set_b)} files", file=sys.stderr)

    report = _compare_and_report(set_a, set_b, dir_a.name, dir_b.name)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(report.encode("utf-8"))


if __name__ == "__main__":
    main()
