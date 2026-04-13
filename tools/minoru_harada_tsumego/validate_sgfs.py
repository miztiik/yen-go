"""Comprehensive SGF validation for Harada tsumego collection.

Checks every generated SGF for structural correctness:
  1. Board position — has AB[]/AW[] setup stones
  2. Solution tree — has at least one move branch
  3. Color alternation — B-W-B-W in every branch
  4. BM markers — only on first wrong move, not continuations
  5. Comment quality — no mid-sentence newlines, no HTML artifacts
  6. SGF spec compliance — valid properties, no stray attributes
  7. Move validity — coordinates within board bounds
  8. No phantom/noise moves — flag branches with suspiciously many moves

Run:
    python -m tools.minoru_harada_tsumego.validate_sgfs [--dir PATH] [--sample N] [--verbose]
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """One validation failure."""
    rule: str       # e.g. "COLOR_ALTERNATION"
    severity: str   # "error" | "warning"
    detail: str     # human-readable explanation


@dataclass
class FileResult:
    """Validation result for one SGF file."""
    filename: str
    issues: list[Issue] = field(default_factory=list)
    branch_count: int = 0
    move_count: int = 0
    has_setup: bool = False
    has_solution: bool = False

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# ---------------------------------------------------------------------------
# Individual validation rules
# ---------------------------------------------------------------------------

# Valid SGF root properties we expect
_EXPECTED_ROOT_PROPS = {"SZ", "FF", "GM", "PL", "C", "AB", "AW",
                        "YV", "YG", "YT", "YQ", "YX", "YH", "YL",
                        "YK", "YO", "YC", "YR", "YM", "GN", "DT",
                        "SO", "AP", "CA", "KM", "RU", "HA", "RE"}

# HTML/CSS artifacts that should not appear in SGF comments
_HTML_ARTIFACTS = re.compile(
    r"(?i)(<[a-z]+[^>]*>|</[a-z]+>|#[0-9a-f]{6}\b|"
    r"font-size|background-color|text-align|margin:|padding:|"
    r"&nbsp;|&amp;|&lt;|&gt;|class=|style=)",
)

# Footer boilerplate from the source website
_FOOTER_PATTERNS = re.compile(
    r"(?i)(page top|term of use|all rights reserved|hitachi|"
    r"problems/answers|copyright|\u00a9|powered by)",
)


def _check_setup(content: str, result: FileResult) -> None:
    """Rule 1: Board has setup stones."""
    has_ab = "AB[" in content
    has_aw = "AW[" in content
    result.has_setup = has_ab or has_aw
    if not result.has_setup:
        result.issues.append(Issue(
            "NO_SETUP_STONES", "error",
            "SGF has no AB[] or AW[] — empty board",
        ))


def _check_solution_tree(content: str, result: FileResult) -> None:
    """Rule 2: Has at least one solution branch with moves."""
    # Count branches: (;B[...] or (;W[...]
    branches = re.findall(r"\(;[BW]\[", content)
    result.branch_count = len(branches)

    # Count total moves
    moves = re.findall(r";[BW]\[[a-s]{2}\]", content)
    result.move_count = len(moves)

    result.has_solution = result.move_count > 0
    if not result.has_solution:
        result.issues.append(Issue(
            "NO_SOLUTION_MOVES", "warning",
            "SGF has no solution moves — setup-only puzzle",
        ))


def _check_color_alternation(content: str, result: FileResult) -> None:
    """Rule 3: Move colors alternate in every branch."""
    # Extract each variation branch
    for branch_match in re.finditer(r"\(;([^()]+)\)", content):
        branch = branch_match.group(1)
        moves = re.findall(r";([BW])\[([a-s]{2})\]", branch)
        if len(moves) < 2:
            continue
        for i in range(len(moves) - 1):
            if moves[i][0] == moves[i + 1][0]:
                coords = [f"{m[0]}[{m[1]}]" for m in moves]
                result.issues.append(Issue(
                    "COLOR_ALTERNATION", "error",
                    f"Consecutive {moves[i][0]} at positions {i+1}-{i+2}: "
                    f"{', '.join(coords)}",
                ))
                break


def _check_bm_markers(content: str, result: FileResult) -> None:
    """Rule 4: BM[1] only on first wrong move, not continuations."""
    for branch_match in re.finditer(r"\(;([^()]+)\)", content):
        branch = branch_match.group(1)
        if "C[Wrong]" not in branch:
            continue
        bm_count = branch.count("BM[1]")
        if bm_count > 1:
            result.issues.append(Issue(
                "EXCESS_BM_MARKERS", "error",
                f"Wrong branch has {bm_count} BM[1] markers "
                f"(should be 1)",
            ))


def _check_comments(content: str, result: FileResult) -> None:
    """Rule 5: Comment quality — no artifacts, no mid-sentence newlines."""
    for comment_match in re.finditer(r"C\[([^\]]*)\]", content):
        comment = comment_match.group(1)

        # HTML/CSS artifacts
        html_match = _HTML_ARTIFACTS.search(comment)
        if html_match:
            result.issues.append(Issue(
                "HTML_ARTIFACT", "error",
                f"HTML/CSS artifact in comment: '{html_match.group()}'",
            ))

        # Footer boilerplate
        footer_match = _FOOTER_PATTERNS.search(comment)
        if footer_match:
            result.issues.append(Issue(
                "FOOTER_BOILERPLATE", "error",
                f"Footer text in comment: '{footer_match.group()}'",
            ))

        # Mid-sentence newlines (lowercase letter + \n + letter)
        if re.search(r"[a-z,]\n[a-zA-Z]", comment):
            result.issues.append(Issue(
                "MID_SENTENCE_NEWLINE", "warning",
                "Comment has mid-sentence line break",
            ))


def _check_move_bounds(content: str, result: FileResult) -> None:
    """Rule 6: All move coordinates are within board bounds."""
    sz_match = re.search(r"SZ\[(\d+)\]", content)
    if not sz_match:
        return
    size = int(sz_match.group(1))
    max_coord = chr(ord("a") + size - 1)  # 'a' + 18 = 's' for 19x19

    for move_match in re.finditer(r";[BW]\[([a-z])([a-z])\]", content):
        col, row = move_match.group(1), move_match.group(2)
        if col > max_coord or row > max_coord:
            result.issues.append(Issue(
                "MOVE_OUT_OF_BOUNDS", "error",
                f"Move [{col}{row}] exceeds board size {size}",
            ))


def _check_player_first_move(content: str, result: FileResult) -> None:
    """Rule 7: PL[] matches the first move color in the SGF.

    Checks the very first B[]/W[] move in the file (which is the main
    line's first move, regardless of branch structure).
    """
    pl_match = re.search(r"PL\[([BW])\]", content)
    if not pl_match:
        return
    player = pl_match.group(1)

    # Find the first move in the entire SGF (main line starts before branches)
    first_move = re.search(r";([BW])\[[a-s]{2}\]", content)
    if first_move:
        if first_move.group(1) != player:
            result.issues.append(Issue(
                "PL_MISMATCH", "error",
                f"PL[{player}] but first move is "
                f"{first_move.group(1)}",
            ))


def _check_suspicious_move_count(content: str, result: FileResult) -> None:
    """Rule 8: Flag branches with suspiciously many moves (noise)."""
    for branch_match in re.finditer(r"\(;([^()]+)\)", content):
        branch = branch_match.group(1)
        moves = re.findall(r";[BW]\[", branch)
        # Harada elementary = 3-7 moves typical; >15 is suspicious
        if len(moves) > 15:
            result.issues.append(Issue(
                "EXCESSIVE_MOVES", "warning",
                f"Branch has {len(moves)} moves — possible noise",
            ))


def _check_move_on_occupied(content: str, result: FileResult) -> None:
    """Rule 10: No move plays on an intersection already occupied at setup."""
    # Parse setup stones
    occupied: set[str] = set()
    for m in re.finditer(r"A[BW]\[([a-s]{2})\]", content):
        occupied.add(m.group(1))

    if not occupied:
        return

    # Check each branch for moves on occupied points
    # Note: some are legitimate capture-replays (ko, snapback)
    # where a stone is captured then the same point replayed.
    for branch_match in re.finditer(r"\(;([^()]+)\)", content):
        branch = branch_match.group(1)
        for move_match in re.finditer(r";[BW]\[([a-s]{2})\]", branch):
            coord = move_match.group(1)
            if coord in occupied:
                result.issues.append(Issue(
                    "MOVE_ON_OCCUPIED", "warning",
                    f"Move at [{coord}] plays on a setup stone "
                    f"(may be capture-replay)",
                ))


def _check_outlier_moves(content: str, result: FileResult) -> None:
    """Rule 11: Flag moves far from the action area (likely noise).

    Computes the bounding box of setup stones and flags any move
    more than 3 intersections outside that box.
    """
    # Parse setup stone coordinates
    coords: list[tuple[int, int]] = []
    for m in re.finditer(r"A[BW]\[([a-s])([a-s])\]", content):
        coords.append((ord(m.group(1)) - ord("a"), ord(m.group(2)) - ord("a")))

    if len(coords) < 3:
        return

    min_x = min(c[0] for c in coords)
    max_x = max(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_y = max(c[1] for c in coords)

    # Expand bounding box by 3 (generous margin for approach moves)
    margin = 3
    for branch_match in re.finditer(r"\(;([^()]+)\)", content):
        branch = branch_match.group(1)
        for move_match in re.finditer(r";[BW]\[([a-s])([a-s])\]", branch):
            mx = ord(move_match.group(1)) - ord("a")
            my = ord(move_match.group(2)) - ord("a")
            if (mx < min_x - margin or mx > max_x + margin or
                    my < min_y - margin or my > max_y + margin):
                coord = move_match.group(1) + move_match.group(2)
                result.issues.append(Issue(
                    "OUTLIER_MOVE", "warning",
                    f"Move [{coord}] is far outside the setup area "
                    f"(box: [{chr(min_x+97)}{chr(min_y+97)}]-"
                    f"[{chr(max_x+97)}{chr(max_y+97)}])",
                ))


def _check_stray_properties(content: str, result: FileResult) -> None:
    """Rule 9: No unexpected SGF properties in root node."""
    # Extract root node properties (before first branch)
    root_end = content.find("(;", 2)
    if root_end == -1:
        root_end = content.find(";", 3)  # first move
    root_section = content[:root_end] if root_end > 0 else content

    props = re.findall(r"([A-Z]{1,2})\[", root_section)
    for prop in props:
        if prop not in _EXPECTED_ROOT_PROPS:
            # Not an error, just a warning for unknown properties
            result.issues.append(Issue(
                "UNKNOWN_PROPERTY", "warning",
                f"Unexpected root property: {prop}[]",
            ))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    _check_setup,
    _check_solution_tree,
    _check_color_alternation,
    _check_bm_markers,
    _check_comments,
    _check_move_bounds,
    _check_player_first_move,
    _check_suspicious_move_count,
    _check_move_on_occupied,
    _check_outlier_moves,
    _check_stray_properties,
]


def validate_file(filepath: Path) -> FileResult:
    """Run all validation checks on one SGF file."""
    content = filepath.read_text(encoding="utf-8")
    result = FileResult(filename=filepath.name)

    for check in ALL_CHECKS:
        check(content, result)

    return result


def validate_directory(
    sgf_dir: Path,
    *,
    sample: int | None = None,
    verbose: bool = False,
) -> list[FileResult]:
    """Validate all SGFs in a directory.

    Args:
        sgf_dir: Directory containing .sgf files.
        sample: If set, randomly sample N files instead of all.
        verbose: Print per-file results.

    Returns:
        List of FileResult for every validated file.
    """
    files = sorted(sgf_dir.glob("*.sgf"))
    if not files:
        print(f"No SGF files found in {sgf_dir}", file=sys.stderr)
        return []

    if sample and sample < len(files):
        files = random.sample(files, sample)
        files.sort()

    results: list[FileResult] = []
    for filepath in files:
        result = validate_file(filepath)
        results.append(result)

        if verbose and result.issues:
            print(f"\n{result.filename}:")
            for issue in result.issues:
                marker = "ERROR" if issue.severity == "error" else "WARN"
                print(f"  [{marker}] {issue.rule}: {issue.detail}")

    return results


def print_summary(results: list[FileResult]) -> None:
    """Print aggregate validation summary."""
    total = len(results)
    clean = sum(1 for r in results if r.ok)
    with_errors = sum(1 for r in results if not r.ok)
    with_warnings = sum(1 for r in results if r.warning_count > 0 and r.ok)
    with_solution = sum(1 for r in results if r.has_solution)
    setup_only = sum(1 for r in results if r.has_setup and not r.has_solution)
    no_setup = sum(1 for r in results if not r.has_setup)

    # Aggregate by rule
    rule_counts: dict[str, dict[str, int]] = {}
    for r in results:
        for issue in r.issues:
            key = issue.rule
            if key not in rule_counts:
                rule_counts[key] = {"error": 0, "warning": 0}
            rule_counts[key][issue.severity] += 1

    print(f"\n{'=' * 60}")
    print(f"VALIDATION SUMMARY — {total} SGFs")
    print(f"{'=' * 60}")
    print(f"  Clean (no errors):     {clean:4d} ({clean/total*100:.0f}%)")
    print(f"  With errors:           {with_errors:4d} ({with_errors/total*100:.0f}%)")
    print(f"  Warnings only:         {with_warnings:4d}")
    print(f"  With solution tree:    {with_solution:4d}")
    print(f"  Setup-only:            {setup_only:4d}")
    print(f"  No setup stones:       {no_setup:4d}")

    if rule_counts:
        print(f"\n{'Rule':<30s} {'Errors':>7s} {'Warns':>7s}")
        print("-" * 46)
        for rule in sorted(rule_counts, key=lambda r: -sum(rule_counts[r].values())):
            counts = rule_counts[rule]
            print(f"  {rule:<28s} {counts['error']:>5d} {counts['warning']:>5d}")

    print()


def export_for_agent(results: list[FileResult], output_path: Path) -> None:
    """Export validation results + comments as JSON for sub-agent review."""
    records = []
    for r in results:
        records.append({
            "filename": r.filename,
            "ok": r.ok,
            "errors": r.error_count,
            "warnings": r.warning_count,
            "branches": r.branch_count,
            "moves": r.move_count,
            "has_setup": r.has_setup,
            "has_solution": r.has_solution,
            "issues": [
                {"rule": i.rule, "severity": i.severity, "detail": i.detail}
                for i in r.issues
            ],
        })
    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Exported {len(records)} results → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Harada tsumego SGF files",
    )
    parser.add_argument(
        "--dir",
        default="external-sources/authors/Minoru Harada/sgf/batch-001",
        help="Directory containing SGF files",
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Randomly validate N files (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-file issues",
    )
    parser.add_argument(
        "--export", type=str, default=None,
        help="Export results as JSON for agent review",
    )
    args = parser.parse_args()

    sgf_dir = Path(args.dir)
    if not sgf_dir.exists():
        print(f"Directory not found: {sgf_dir}", file=sys.stderr)
        return 1

    results = validate_directory(
        sgf_dir, sample=args.sample, verbose=args.verbose,
    )
    if not results:
        return 1

    print_summary(results)

    if args.export:
        export_for_agent(results, Path(args.export))

    # Exit code: 0 if all clean, 1 if any errors
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
