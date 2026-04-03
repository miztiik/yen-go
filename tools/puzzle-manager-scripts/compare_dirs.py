"""
SGF Directory Comparison CLI.

Compares two directories of SGF tsumego puzzle files, identifies duplicates
by board position, and produces granular match-level reports (JSONL + Markdown).

Usage:
    python tools/puzzle-manager-scripts/compare_dirs.py \\
      --source "external-sources/Xuan Xuan Qi Jing" \\
      --target "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - XUAN XUAN QI JING"

Design reference: docs/architecture/tools/sgf-directory-comparison.md
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so "from tools.core..." imports work
# when invoked directly (python tools/puzzle-manager-scripts/compare_dirs.py)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import argparse
import json
import logging
import signal
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from tools.core.checkpoint import (
    ToolCheckpoint,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from tools.core.logging import format_duration, setup_logging
from tools.core.paths import get_project_root, rel_path
from tools.core.sgf_analysis import compute_solution_depth, count_total_nodes
from tools.core.sgf_compare import (
    MATCH_LEVEL_NAMES,
    CompareResult,
    MatchLevel,
    classify_match,
    full_hash,
    make_error_result,
    make_filename_mismatch_result,
    make_unmatched_result,
    position_hash,
)
from tools.core.sgf_parser import SGFParseError, SgfTree, parse_sgf

logger = logging.getLogger("compare_dirs")

CHECKPOINT_INTERVAL = 50
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_BASE = SCRIPT_DIR / "output"


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


@dataclass
class CompareCheckpoint(ToolCheckpoint):
    """Checkpoint state for directory comparison runs."""

    source_dir: str = ""
    target_dir: str = ""
    compared_files: list[str] = field(default_factory=list)
    match_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------


@dataclass
class ParsedFile:
    """A parsed SGF file with computed hashes."""

    path: Path
    rel_path: str  # relative to the scanned root dir (e.g. "Vol1/prob0001.sgf")
    tree: SgfTree
    raw: str
    pos_hash: str
    f_hash: str | None


def _build_index(
    directory: Path, label: str, log: logging.Logger
) -> tuple[dict[str, list[ParsedFile]], dict[str, ParsedFile], list[tuple[str, str]]]:
    """Parse all SGF files in a directory and build hash indexes.

    Returns:
        (pos_hash_index, name_index, errors)
        - pos_hash_index: maps position_hash -> list of ParsedFile
        - name_index: maps rel_path -> ParsedFile
        - errors: list of (rel_path, error_message)
    """
    sgf_files = sorted(directory.rglob("*.sgf"))
    log.info(f"[{label}] Found {len(sgf_files)} SGF files in {rel_path(str(directory))}")

    pos_index: dict[str, list[ParsedFile]] = {}
    name_index: dict[str, ParsedFile] = {}
    errors: list[tuple[str, str]] = []

    for sgf_path in sgf_files:
        # Use path relative to scanned root so subdirectory files don't collide
        file_rel = sgf_path.relative_to(directory).as_posix()
        try:
            raw = sgf_path.read_text(encoding="utf-8")
            tree = parse_sgf(raw)

            if not tree.black_stones and not tree.white_stones:
                errors.append((file_rel, "no_stones"))
                log.warning(f"[{label}] {file_rel}: no stones (AB/AW missing)")
                continue

            pf = ParsedFile(
                path=sgf_path,
                rel_path=file_rel,
                tree=tree,
                raw=raw,
                pos_hash=position_hash(tree),
                f_hash=full_hash(tree),
            )
            pos_index.setdefault(pf.pos_hash, []).append(pf)
            name_index[file_rel] = pf

        except SGFParseError as e:
            errors.append((file_rel, str(e)))
            log.error(f"[{label}] {file_rel}: parse error: {e}")
        except Exception as e:
            errors.append((file_rel, str(e)))
            log.error(f"[{label}] {file_rel}: unexpected error: {e}")

    log.info(
        f"[{label}] Parsed {sum(len(v) for v in pos_index.values())} files, "
        f"{len(errors)} errors"
    )
    return pos_index, name_index, errors


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------


def _compare_directories(
    source_dir: Path,
    target_dir: Path,
    *,
    resume: bool = False,
    dry_run: bool = False,
    output_dir: Path | None = None,
    log: logging.Logger | None = None,
) -> list[CompareResult]:
    """Compare all SGF files between source and target directories.

    Returns list of CompareResult (one per source file + one per unmatched target).
    """
    if log is None:
        log = logger

    # Build indexes for both directories
    log.info("Building source index...")
    source_index, source_names, source_errors = _build_index(source_dir, "source", log)

    log.info("Building target index...")
    target_index, target_names, target_errors = _build_index(target_dir, "target", log)

    # Load checkpoint if resuming
    compared_set: set[str] = set()
    checkpoint: CompareCheckpoint | None = None
    if resume and output_dir:
        checkpoint = load_checkpoint(output_dir, CompareCheckpoint)
        if checkpoint:
            compared_set = set(checkpoint.compared_files)
            log.info(f"Resuming: {len(compared_set)} files already compared")

    results: list[CompareResult] = []
    match_counts: dict[int, int] = dict.fromkeys(range(8), 0)
    files_since_checkpoint = 0
    interrupted = False

    def _handle_sigint(signum, frame):
        nonlocal interrupted
        interrupted = True
        log.warning("Interrupted — saving checkpoint...")

    old_handler = signal.signal(signal.SIGINT, _handle_sigint)

    try:
        # Collect all source files in deterministic order
        all_source_files: list[ParsedFile] = []
        for pf_list in source_index.values():
            all_source_files.extend(pf_list)
        all_source_files.sort(key=lambda pf: pf.rel_path)

        # Process source errors
        for file_rel, error_msg in source_errors:
            if file_rel in compared_set:
                continue
            result = make_error_result(file_rel, error_msg)
            results.append(result)
            match_counts[0] = match_counts.get(0, 0) + 1

        # Track which target files were matched
        matched_target_files: set[str] = set()

        # Compare each source file against target index
        for pf in all_source_files:
            if interrupted:
                break
            if pf.rel_path in compared_set:
                continue

            # Look up by position hash in target
            target_candidates = target_index.get(pf.pos_hash, [])

            if target_candidates:
                # Position match found — classify against best candidate
                # For 1:1 collections we expect exactly 1 match per hash
                target_pf = target_candidates[0]
                matched_target_files.add(target_pf.rel_path)

                result = classify_match(
                    pf.tree,
                    target_pf.tree,
                    pf.rel_path,
                    target_pf.rel_path,
                    raw_a=pf.raw,
                    raw_b=target_pf.raw,
                )
                results.append(result)
                match_counts[result.match_level] = (
                    match_counts.get(result.match_level, 0) + 1
                )
            else:
                # No position match — check filename correlation (Level 1)
                if pf.rel_path in target_names:
                    target_pf = target_names[pf.rel_path]
                    matched_target_files.add(target_pf.rel_path)
                    result = make_filename_mismatch_result(
                        pf.rel_path, pf.tree, target_pf.tree, target_pf.rel_path
                    )
                    results.append(result)
                    match_counts[1] = match_counts.get(1, 0) + 1
                else:
                    result = make_unmatched_result(pf.rel_path, pf.tree)
                    results.append(result)
                    match_counts[0] = match_counts.get(0, 0) + 1

            compared_set.add(pf.rel_path)
            files_since_checkpoint += 1

            # Checkpoint every N files
            if (
                not dry_run
                and output_dir
                and files_since_checkpoint >= CHECKPOINT_INTERVAL
            ):
                _save_compare_checkpoint(
                    output_dir, source_dir, target_dir, compared_set, match_counts
                )
                files_since_checkpoint = 0

        # Report unmatched target files (files in target not in source)
        for target_pf_list in target_index.values():
            for target_pf in target_pf_list:
                if target_pf.rel_path not in matched_target_files:
                    # Target-only file — report as informational
                    result = CompareResult(
                        source_file="(target-only)",
                        target_file=target_pf.rel_path,
                        match_level=MatchLevel.UNMATCHED,
                        position_hash=target_pf.pos_hash,
                        full_hash=target_pf.f_hash,
                        board_size=target_pf.tree.board_size,
                        player_to_move_source=None,
                        player_to_move_target=(
                            target_pf.tree.player_to_move.value
                            if target_pf.f_hash
                            else None
                        ),
                        pl_status=None,
                        first_move_match=None,
                        correct_line_match=None,
                        source_nodes=None,
                        target_nodes=count_total_nodes(target_pf.tree.solution_tree),
                        source_depth=None,
                        target_depth=compute_solution_depth(
                            target_pf.tree.solution_tree
                        ),
                        detail="File exists only in target directory.",
                    )
                    results.append(result)

    finally:
        signal.signal(signal.SIGINT, old_handler)

        # Save final checkpoint on interruption
        if interrupted and not dry_run and output_dir:
            _save_compare_checkpoint(
                output_dir, source_dir, target_dir, compared_set, match_counts
            )

    return results


def _save_compare_checkpoint(
    output_dir: Path,
    source_dir: Path,
    target_dir: Path,
    compared_set: set[str],
    match_counts: dict[int, int],
) -> None:
    """Save comparison checkpoint."""
    cp = CompareCheckpoint(
        source_dir=str(source_dir),
        target_dir=str(target_dir),
        compared_files=sorted(compared_set),
        match_counts={str(k): v for k, v in match_counts.items()},
    )
    save_checkpoint(cp, output_dir)


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _print_console_summary(
    results: list[CompareResult],
    source_dir: Path,
    target_dir: Path,
    duration: float,
    header: str = "",
) -> None:
    """Print comparison summary to console."""
    source_results = [r for r in results if r.source_file != "(target-only)"]
    target_only_count = sum(1 for r in results if r.source_file == "(target-only)")

    counts: dict[int, int] = dict.fromkeys(range(8), 0)
    for r in source_results:
        counts[r.match_level] = counts.get(r.match_level, 0) + 1

    source_total = len(source_results)
    matched = sum(counts[lv] for lv in range(1, 8))  # Levels 1-7 = matched
    source_unmatched = counts[0]

    # Calculate target total from matched + target-only
    target_total = matched + target_only_count

    if header:
        print(f"\n--- {header} ({format_duration(duration)}) ---")
        print(f"  Source: {rel_path(str(source_dir))}")
        print(f"  Target: {rel_path(str(target_dir))}")

    # File counts
    print(f"  Source: {source_total} files | Target: {target_total} files | Matched: {matched}")

    # Match breakdown (only non-zero, only matched levels 1-7)
    matched_levels = [(lv, counts[lv]) for lv in range(7, 0, -1) if counts[lv] > 0]
    if matched_levels:
        pct_total = matched / source_total * 100 if source_total else 0
        print(f"  Match rate: {pct_total:.1f}%")
        for lv, count in matched_levels:
            print(f"    Level {lv} ({MATCH_LEVEL_NAMES[lv]}): {count}")

    # Delta
    if source_unmatched > 0 or target_only_count > 0:
        print("  Delta:")
        if source_unmatched > 0:
            print(f"    Source-only (no match in target): {source_unmatched}")
        if target_only_count > 0:
            print(f"    Target-only (no match in source): {target_only_count}")


def _write_jsonl(results: list[CompareResult], output_dir: Path) -> Path:
    """Write comparison results as JSONL."""
    path = output_dir / "comparison.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    return path


def _write_summary(
    results: list[CompareResult],
    source_dir: Path,
    target_dir: Path,
    source_errors: int,
    target_errors: int,
    duration_sec: float,
    output_dir: Path,
) -> Path:
    """Write Markdown summary report."""
    path = output_dir / "summary.md"

    # Separate source-side and target-only results
    source_results = [r for r in results if r.source_file != "(target-only)"]
    target_only = [r for r in results if r.source_file == "(target-only)"]

    # Count match levels for SOURCE files only
    counts: dict[int, int] = dict.fromkeys(range(8), 0)
    pl_absent_count = 0
    pl_conflict_count = 0
    for r in source_results:
        counts[r.match_level] = counts.get(r.match_level, 0) + 1
        if r.pl_status and "absent" in r.pl_status:
            pl_absent_count += 1
        if r.pl_status == "conflict":
            pl_conflict_count += 1

    source_total = len(source_results)
    target_only_count = len(target_only)
    matched = sum(counts[lv] for lv in range(1, 8))
    source_unmatched = counts[0]
    target_total = matched + target_only_count
    pct_match = matched / source_total * 100 if source_total else 0

    lines = [
        "## SGF Directory Comparison Report",
        "",
        f"- **Run:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Duration:** {format_duration(duration_sec)}",
        f"- **Source:** {rel_path(str(source_dir))} ({source_total} files)",
        f"- **Target:** {rel_path(str(target_dir))} ({target_total} files)",
        f"- **Matched:** {matched} ({pct_match:.1f}%)",
        "",
    ]

    # Match breakdown (only non-zero levels 1-7)
    lines.extend([
        "### Matches",
        "",
        "| Level | Name | Count | % of source |",
        "|------:|------|------:|------------:|",
    ])
    total = source_total if source_total > 0 else 1
    for level in range(7, -1, -1):
        count = counts[level]
        if count == 0 or level == 0:
            continue
        pct = count / total * 100
        lines.append(f"| {level} | {MATCH_LEVEL_NAMES[level]} | {count} | {pct:.1f}% |")
    lines.append(f"| | **Total matched** | **{matched}** | **{pct_match:.1f}%** |")

    # Delta section
    if source_unmatched > 0 or target_only_count > 0:
        lines.extend([
            "",
            "### Unmatched (Delta)",
            "",
        ])
        if source_unmatched > 0:
            lines.append(f"- **Source-only** (no match in target): {source_unmatched}")
        if target_only_count > 0:
            lines.append(f"- **Target-only** (no match in source): {target_only_count}")

    # Details
    lines.extend([
        "",
        "### Details",
        "",
        f"- Parse errors (source): {source_errors}",
        f"- Parse errors (target): {target_errors}",
        f"- PL-absent matches: {pl_absent_count}",
        f"- PL-conflict matches: {pl_conflict_count}",
    ])

    # Notable findings (Level 3 or below)
    notable = [
        r for r in source_results
        if 0 < r.match_level <= 3
    ]
    lines.extend(["", "### Notable Findings", ""])
    if notable:
        for r in notable:
            lines.append(
                f"- **{r.source_file}** \u2192 Level {r.match_level} "
                f"({MATCH_LEVEL_NAMES[r.match_level]}): {r.detail}"
            )
    else:
        lines.append("- No notable findings (all matches Level 4+).")

    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


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
    """Extract the leaf directory name and normalize to filesystem-safe form.

    Uses only the final directory component to keep names short
    (avoids Windows MAX_PATH issues with deeply nested output dirs).
    """
    import re as _re

    name = path_str.replace("\\", "/").strip("/")
    # Take only the leaf directory name
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    # Replace any non-alphanumeric (except hyphen) with underscore
    name = _re.sub(r"[^a-zA-Z0-9-]", "_", name)
    # Collapse consecutive underscores
    name = _re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def _make_output_dirname(timestamp: str, source_str: str, target_str: str) -> str:
    """Build descriptive output dir name: {timestamp}_{source}__vs__{target}."""
    src = _normalize_name(source_str)
    tgt = _normalize_name(target_str)
    return f"{timestamp}_{src}__vs__{tgt}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two directories of SGF tsumego files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source directory path (relative to project root or absolute)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target directory path (relative to project root or absolute)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and hash only, print summary to console, no output files",
    )

    args = parser.parse_args()

    source_dir = _resolve_dir(args.source)
    target_dir = _resolve_dir(args.target)

    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)
    if not target_dir.is_dir():
        print(f"Error: target directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    # Create descriptive output directory: {timestamp}_{source}__vs__{target}
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = OUTPUT_BASE / _make_output_dirname(timestamp, args.source, args.target)

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    structured_log = setup_logging(
        output_dir if not args.dry_run else Path("."),
        "compare_dirs",
        verbose=False,
        log_to_file=not args.dry_run,
        log_suffix="compare",
    )

    structured_log.run_start(
        output_dir=str(output_dir),
        resume=args.resume,
        dry_run=args.dry_run,
        source=str(source_dir),
        target=str(target_dir),
    )

    start_time = time.monotonic()

    # Run comparison
    results = _compare_directories(
        source_dir,
        target_dir,
        resume=args.resume,
        dry_run=args.dry_run,
        output_dir=output_dir if not args.dry_run else None,
        log=logging.getLogger("compare_dirs"),
    )

    duration = time.monotonic() - start_time

    # Count errors
    source_errors = sum(1 for r in results if r.error and r.source_file != "(target-only)")
    target_errors = 0  # Target errors are in the index building phase

    if args.dry_run:
        _print_console_summary(results, source_dir, target_dir, duration, header="Dry Run")
    else:
        # Write output files
        jsonl_path = _write_jsonl(results, output_dir)
        summary_path = _write_summary(
            results, source_dir, target_dir, source_errors, target_errors,
            duration, output_dir,
        )

        # Clear checkpoint on successful completion
        clear_checkpoint(output_dir)

        print(f"\nComparison complete ({format_duration(duration)})")
        print(f"  Source: {rel_path(str(source_dir))}")
        print(f"  Target: {rel_path(str(target_dir))}")
        print(f"  Output: {rel_path(str(output_dir))}/")
        print(f"    {jsonl_path.name}")
        print(f"    {summary_path.name}")
        _print_console_summary(results, source_dir, target_dir, duration)

    structured_log.run_end(
        downloaded=len(results),
        skipped=0,
        errors=source_errors,
        duration_sec=duration,
    )


if __name__ == "__main__":
    main()
