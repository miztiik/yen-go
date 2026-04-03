"""Generate ASCII board + enrichment annotation reports for AI expert review.

Combines SGF fixture rendering (board, stones, correct move) with
enrichment JSON output (validation, difficulty, refutations, flags)
into a single markdown report suitable for evaluation by an AI
acting in a professional Go player persona (Cho Chikun / Lee Sedol).

Run directly::

    python expert_review.py --fixtures tests/fixtures/perf-33 --output output/benchmark-fresh
    python expert_review.py --fixtures tests/fixtures/calibration/cho-elementary --output output/controls

Output goes to ``output/expert-review-{timestamp}.md``.
"""

__test__ = False  # Guard against accidental pytest collection

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config lookups (tag / level name resolution)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # yen-go root


def _load_tag_map() -> dict[int, str]:
    """Return {numeric_id: slug} from config/tags.json."""
    tags_file = _PROJECT_ROOT / "config" / "tags.json"
    data = json.loads(tags_file.read_text(encoding="utf-8"))
    return {v["id"]: v["slug"] for v in data["tags"].values()}


def _load_level_map() -> dict[int, str]:
    """Return {numeric_id: slug} from config/puzzle-levels.json."""
    levels_file = _PROJECT_ROOT / "config" / "puzzle-levels.json"
    data = json.loads(levels_file.read_text(encoding="utf-8"))
    return {entry["id"]: entry["slug"] for entry in data["levels"]}


# Lazy-loaded singletons
_TAG_MAP: dict[int, str] | None = None
_LEVEL_MAP: dict[int, str] | None = None


def tag_name(tid: int) -> str:
    global _TAG_MAP
    if _TAG_MAP is None:
        _TAG_MAP = _load_tag_map()
    return _TAG_MAP.get(tid, f"unknown-{tid}")


def level_name(lid: int) -> str:
    global _LEVEL_MAP
    if _LEVEL_MAP is None:
        _LEVEL_MAP = _load_level_map()
    return _LEVEL_MAP.get(lid, f"unknown-{lid}")


# ---------------------------------------------------------------------------
# SGF parsing — uses sgf_parser (sgfmill-based) instead of regex
# ---------------------------------------------------------------------------


def parse_sgf_properties(sgf_text: str) -> dict[str, str]:
    """Extract root-level SGF properties using the proper SGF parser."""
    from analyzers.sgf_parser import parse_sgf as _parse_sgf

    try:
        root = _parse_sgf(sgf_text)
    except Exception:
        return {}
    props: dict[str, str] = {}
    for key, values in root.properties.items():
        if values:
            props[key] = values[0]
    return props


def parse_all_stones(
    sgf_text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Parse all AB and AW stones from root node using proper SGF parser."""
    from analyzers.sgf_parser import parse_sgf as _parse_sgf

    try:
        root = _parse_sgf(sgf_text)
    except Exception:
        return [], []
    black = [
        (ord(c[0]) - ord("a"), ord(c[1]) - ord("a"))
        for c in root.get_all("AB")
        if len(c) >= 2
    ]
    white = [
        (ord(c[0]) - ord("a"), ord(c[1]) - ord("a"))
        for c in root.get_all("AW")
        if len(c) >= 2
    ]
    return black, white


def parse_first_move(sgf_text: str) -> tuple[str, tuple[int, int] | None]:
    """Parse the first correct move from SGF using proper parser."""
    from analyzers.sgf_parser import parse_sgf as _parse_sgf

    try:
        root = _parse_sgf(sgf_text)
    except Exception:
        return "?", None
    if not root.children:
        return "?", None
    child = root.children[0]
    move = child.move
    if move is None:
        return "?", None
    color_str = "B" if move[0].name == "BLACK" else "W"
    coord_str = move[1]
    if len(coord_str) >= 2:
        coord = (ord(coord_str[0]) - ord("a"), ord(coord_str[1]) - ord("a"))
        return color_str, coord
    return color_str, None


def sgf_to_gtp(col: int, row: int, size: int) -> str:
    """Convert SGF (col, row) 0-indexed to GTP coordinate like 'C6'."""
    letters = "ABCDEFGHJKLMNOPQRST"
    if col < 0 or col >= size or row < 0 or row >= size:
        return "??"
    return f"{letters[col]}{size - row}"


# ---------------------------------------------------------------------------
# ASCII board rendering
# ---------------------------------------------------------------------------


def render_ascii_board(
    size: int,
    black: list[tuple[int, int]],
    white: list[tuple[int, int]],
    first_move: tuple[str, tuple[int, int]] | None = None,
) -> str:
    """Render a Go board as ASCII art with coordinates."""
    board = [["." for _ in range(size)] for _ in range(size)]
    for x, y in black:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = "X"
    for x, y in white:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = "O"
    if first_move and first_move[1]:
        _color, (fx, fy) = first_move
        if 0 <= fx < size and 0 <= fy < size and board[fy][fx] == ".":
            board[fy][fx] = "*"

    lines: list[str] = []
    col_labels = "ABCDEFGHJKLMNOPQRST"[:size]
    lines.append("   " + " ".join(col_labels))
    for y in range(size):
        row_num = size - y
        row_str = f"{row_num:2d} " + " ".join(board[y]) + f" {row_num}"
        lines.append(row_str)
    lines.append("   " + " ".join(col_labels))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Enrichment annotation formatting
# ---------------------------------------------------------------------------


def format_enrichment(data: dict) -> str:
    """Format enriched JSON output as a readable annotation block."""
    v = data.get("validation", {})
    d = data.get("difficulty", {})
    refs = data.get("refutations", [])

    lines: list[str] = []

    # Validation section
    status = v.get("status", "?")
    status_icon = {"accepted": "PASS", "flagged": "FLAG", "rejected": "FAIL"}.get(
        status, "????"
    )
    lines.append(f"  Status:       {status_icon} ({status})")
    lines.append(
        f"  Correct move: {v.get('correct_move_gtp', '?')}  |  KataGo top: {v.get('katago_top_move_gtp', '?')}  |  Agrees: {v.get('katago_agrees', '?')}"
    )
    lines.append(
        f"  Winrate:      {v.get('correct_move_winrate', 0):.4f}  |  Policy: {v.get('correct_move_policy', 0):.4f}"
    )
    lines.append(f"  Validator:    {v.get('validator_used', '?')}")
    flags = v.get("flags", [])
    if flags:
        lines.append(f"  Flags:        {', '.join(flags)}")
    else:
        lines.append("  Flags:        (none)")

    # Difficulty section
    lines.append("")
    suggested = d.get("suggested_level", "?")
    suggested_id = d.get("suggested_level_id", 0)
    lines.append(
        f"  Difficulty:   {suggested} (id:{suggested_id})  |  Score: {d.get('composite_score', 0):.1f}  |  Confidence: {d.get('confidence', '?')}"
    )
    lines.append(
        f"  Policy prior: {d.get('policy_prior_correct', 0):.6f}  |  Visits to solve: {d.get('visits_to_solve', '?')}  |  Trap density: {d.get('trap_density', 0):.3f}"
    )

    # Tags
    tag_ids = data.get("tags", [])
    tag_names = [tag_name(t) for t in tag_ids]
    lines.append(f"  Tags:         {', '.join(tag_names)} ({tag_ids})")

    # Corner / move order
    lines.append(
        f"  Corner:       {data.get('corner', '?')}  |  Move order: {data.get('move_order', '?')}"
    )

    # Engine info
    eng = data.get("engine", {})
    lines.append(
        f"  Engine:       model={eng.get('model', '?')}  visits={eng.get('visits', '?')}"
    )

    # Refutations
    if refs:
        lines.append("")
        lines.append(f"  Refutations ({len(refs)}):")
        for i, r in enumerate(refs, 1):
            wm = r.get("wrong_move", "?")
            pv = r.get("refutation_pv", [])
            delta = r.get("delta", 0)
            depth = r.get("refutation_depth", 0)
            lines.append(
                f"    #{i}: wrong={wm}  delta={delta:+.3f}  depth={depth}  PV={' '.join(pv)}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Single puzzle report
# ---------------------------------------------------------------------------


def build_puzzle_report(
    sgf_path: Path,
    json_path: Path | None,
    puzzle_num: int,
) -> str:
    """Build a complete review block for one puzzle."""
    sgf = sgf_path.read_text(encoding="utf-8").strip()
    props = parse_sgf_properties(sgf)
    size = int(props.get("SZ", "19"))
    black, white = parse_all_stones(sgf)
    first_color, first_coord = parse_first_move(sgf)

    # Player to move
    pl = props.get("PL", "")
    if not pl and first_color and first_color != "?":
        pl = first_color

    # Solution line counts
    correct_count = sgf.count("RIGHT") + sgf.count("CORRECT") + sgf.count("C[+]")
    wrong_count = sgf.count("WRONG") + sgf.count("BM[")

    report: list[str] = []
    report.append(f"{'=' * 72}")
    report.append(f"PUZZLE #{puzzle_num:02d}: {sgf_path.stem}")
    report.append(f"{'=' * 72}")

    # SGF metadata
    report.append(f"  Source:     {props.get('PC', 'unknown')}")
    report.append(f"  Board:      {size}x{size}")
    report.append(
        f"  To play:    {'Black (X)' if pl == 'B' else 'White (O)' if pl == 'W' else '?'}"
    )
    report.append(f"  Objective:  {props.get('C', 'not specified')}")
    report.append(f"  SGF level:  {props.get('YG', 'not set')}")
    report.append(f"  SGF tags:   {props.get('YT', 'none')}")

    if first_coord:
        gtp = sgf_to_gtp(first_coord[0], first_coord[1], size)
        report.append(f"  1st move:   {first_color}[{gtp}] (marked * on board)")

    report.append(
        f"  Solution:   {correct_count} correct, {wrong_count} wrong variations"
    )
    report.append("")

    # ASCII board
    move_tuple = (first_color, first_coord) if first_coord else None
    report.append(render_ascii_board(size, black, white, move_tuple))
    report.append("")

    # Legend
    report.append("  X = Black  |  O = White  |  * = Correct first move  |  . = Empty")
    report.append("")

    # Enrichment annotations
    if json_path and json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        report.append("--- KataGo Enrichment Analysis ---")
        report.append(format_enrichment(data))
    else:
        report.append("--- KataGo Enrichment Analysis ---")
        report.append("  (no enrichment output available)")

    report.append("")

    # Review questions template
    report.append("--- Expert Review Questions ---")
    report.append("  Q1 (Validation):  Is the correct move identified accurately?")
    report.append("  Q2 (Refutations): Are wrong-move refutations tactically sound?")
    report.append(
        "  Q3 (Difficulty):  Is the suggested difficulty within ±1 level of the true difficulty?"
    )
    report.append("  Q4 (Ko/Seki):     Are ko/seki edge cases handled properly?")
    report.append(
        "  Q5 (Edge cases):  Any false positives, missed tesuji, or flawed analysis?"
    )
    report.append("")

    return "\n".join(report)


# ---------------------------------------------------------------------------
# Full report generation
# ---------------------------------------------------------------------------


def generate_review_report(
    fixtures_dir: Path,
    output_dir: Path | None,
    title: str = "Expert Review",
    max_puzzles: int = 0,
) -> str:
    """Generate complete expert review report for all puzzles in fixtures_dir."""
    sgf_files = sorted(fixtures_dir.glob("*.sgf"))
    if max_puzzles > 0:
        sgf_files = sgf_files[:max_puzzles]

    header_lines: list[str] = []
    header_lines.append(f"# {title}")
    header_lines.append(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    header_lines.append(f"Fixtures:  {fixtures_dir}")
    header_lines.append(f"Output:    {output_dir or '(none)'}")
    header_lines.append(f"Puzzles:   {len(sgf_files)}")
    header_lines.append("")
    header_lines.append("## Review Protocol")
    header_lines.append("")
    header_lines.append("For each puzzle, evaluate the ASCII board position and KataGo enrichment.")
    header_lines.append("Answer 5 questions: PASS / FAIL + brief note if FAIL.")
    header_lines.append("A puzzle passes the expert review if all 5 questions are PASS.")
    header_lines.append("")
    header_lines.append("Symbols: X = Black stone, O = White stone, * = Correct first move, . = Empty")
    header_lines.append("")

    sections: list[str] = []
    stats = {"total": 0, "with_output": 0, "accepted": 0, "flagged": 0, "rejected": 0}

    for i, sgf_path in enumerate(sgf_files, 1):
        json_path = None
        if output_dir:
            json_path = output_dir / f"{sgf_path.stem}.json"

        report = build_puzzle_report(sgf_path, json_path, i)
        sections.append(report)

        stats["total"] += 1
        if json_path and json_path.exists():
            stats["with_output"] += 1
            data = json.loads(json_path.read_text(encoding="utf-8"))
            status = data.get("validation", {}).get("status", "")
            if status == "accepted":
                stats["accepted"] += 1
            elif status == "flagged":
                stats["flagged"] += 1
            elif status == "rejected":
                stats["rejected"] += 1

    # Summary
    header_lines.append("## Summary Statistics")
    header_lines.append(f"  Total puzzles:       {stats['total']}")
    header_lines.append(f"  With enrichment:     {stats['with_output']}")
    header_lines.append(
        f"  Accepted:            {stats['accepted']} ({stats['accepted']/max(stats['with_output'],1)*100:.0f}%)"
    )
    header_lines.append(
        f"  Flagged:             {stats['flagged']} ({stats['flagged']/max(stats['with_output'],1)*100:.0f}%)"
    )
    header_lines.append(
        f"  Rejected:            {stats['rejected']} ({stats['rejected']/max(stats['with_output'],1)*100:.0f}%)"
    )
    header_lines.append("")

    return "\n".join(header_lines) + "\n" + "\n".join(sections)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ASCII board + enrichment reports for expert review"
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).resolve().parent / "tests" / "fixtures" / "perf-33",
        help="Directory containing SGF fixture files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Directory containing enrichment JSON outputs (default: output/benchmark-fresh)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        help="Max puzzles to include (0 = all)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Expert Review: KataGo Enrichment",
        help="Report title",
    )
    parser.add_argument(
        "--out-file",
        type=Path,
        default=None,
        help="Output file path (default: auto-generated in output/)",
    )

    args = parser.parse_args()

    fixtures_dir = args.fixtures.resolve()
    output_dir = args.output
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "output" / "benchmark-fresh"
    else:
        output_dir = output_dir.resolve()

    report = generate_review_report(
        fixtures_dir=fixtures_dir,
        output_dir=output_dir,
        title=args.title,
        max_puzzles=args.max,
    )

    if args.out_file:
        out_path = args.out_file.resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"expert-review-{ts}.md"

    out_path.write_text(report, encoding="utf-8")
    print(f"Report written to {out_path}")
    print(f"Puzzles: {report.count('PUZZLE #')}")


if __name__ == "__main__":
    main()
