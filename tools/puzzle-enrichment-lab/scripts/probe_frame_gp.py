"""Probe the GoProblems.com-style tsumego frame on random fixture SGFs.

Picks N SGF files at random from the entire fixtures tree (or a
specified sub-directory), applies the GP frame (count-based fill),
and prints before/after ASCII boards to stdout.  The same output is
also written to .lab-runtime/frame-test-gp/<YYYYMMDD-HHMMSS>.log so
each run produces a unique, permanent record.

Usage (from tools/puzzle-enrichment-lab/):
    python scripts/probe_frame_gp.py
    python scripts/probe_frame_gp.py --count 10
    python scripts/probe_frame_gp.py --fixtures-dir tests/fixtures/calibration/cho-elementary
    python scripts/probe_frame_gp.py --ko --offence-to-win 10
    python scripts/probe_frame_gp.py --seed 42
"""

from __future__ import annotations

import argparse
import io
import random
import sys
from datetime import datetime
from pathlib import Path

# On Windows the default console encoding (cp1252) can't represent characters
# found in some SGF files (CJK text, etc.). Force UTF-8 output so the log
# file and terminal both receive the same bytes.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure the lab root is on sys.path regardless of cwd
_LAB = Path(__file__).resolve().parent.parent
if str(_LAB) not in sys.path:
    sys.path.insert(0, str(_LAB))

from analyzers.ascii_board import render_ascii
from analyzers.tsumego_frame_gp import apply_gp_frame
from core.tsumego_analysis import extract_position, parse_sgf

_SKIP_DIRS = {"results", "__pycache__", ".pytest_cache"}
_DEFAULT_FIXTURES = _LAB / "tests" / "fixtures"
_LOG_DIR = _LAB / ".lab-runtime" / "frame-test-gp"


def _collect_sgfs(root: Path) -> list[Path]:
    """Recursively collect all .sgf files, skipping result/cache dirs."""
    result = []
    for path in root.rglob("*.sgf"):
        if not any(part in _SKIP_DIRS for part in path.parts):
            result.append(path)
    return sorted(result)


def _sep(title: str, width: int = 60) -> str:
    return f"\n{'-' * width}\n  {title}\n{'-' * width}"


def _render_puzzle(
    sgf_path: Path,
    *,
    margin: int,
    komi: float,
    ko: bool,
    offence_to_win: int,
) -> str:
    """Return the full probe block for one SGF file."""
    try:
        sgf_text = sgf_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        sgf_text = sgf_path.read_text(encoding="latin-1")

    try:
        root = parse_sgf(sgf_text)
        position = extract_position(root)
    except Exception as exc:
        return f"{_sep(f'FILE: {sgf_path}')}\n[PARSE ERROR: {exc}]\n"

    try:
        result = apply_gp_frame(
            position,
            margin=margin,
            komi=komi,
            ko=ko,
            offence_to_win=offence_to_win,
        )
    except Exception as exc:
        return (
            f"{_sep(f'FILE: {sgf_path}')}\n"
            f"{_sep('ORIGINAL ASCII')}\n{render_ascii(position)}\n"
            f"[FRAME ERROR: {exc}]\n"
        )

    attacker = "Black" if result.black_to_attack else "White"
    meta = (
        f"+{result.frame_stones_added} stones, "
        f"attacker={attacker}({result.attacker_color.value}), "
        f"ko={ko}, margin={margin}, offence_to_win={offence_to_win}"
    )

    blocks = [
        _sep(f"FILE: {sgf_path}"),
        "\n=== ORIGINAL SGF ===",
        sgf_text.strip(),
        "\n=== ORIGINAL ASCII ===",
        render_ascii(position),
        f"\n=== GP FRAMED  ({meta}) ===",
        result.position.to_sgf(),
        "\n=== GP FRAMED ASCII ===",
        render_ascii(result.position),
    ]
    return "\n".join(blocks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe GoProblems.com-style (count-based) tsumego framing on fixture SGFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/probe_frame_gp.py
  python scripts/probe_frame_gp.py --count 10
  python scripts/probe_frame_gp.py --fixtures-dir tests/fixtures/calibration/cho-elementary
  python scripts/probe_frame_gp.py --ko --offence-to-win 10
  python scripts/probe_frame_gp.py --seed 42
""",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of SGF files to sample (default: 5).",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help="Root directory to search for SGFs (default: tests/fixtures/).",
    )
    parser.add_argument(
        "--ko",
        action="store_true",
        default=False,
        help="Enable ko-threat patterns on the frame (default: off).",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=2,
        help="Empty margin around stones (default: 2).",
    )
    parser.add_argument(
        "--komi",
        type=float,
        default=0.0,
        help="Komi for territory balance calculation (default: 0).",
    )
    parser.add_argument(
        "--offence-to-win",
        type=int,
        default=5,
        help="Extra points for offense: 5=KaTrain, 10=ghostban (default: 5).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: random).",
    )
    args = parser.parse_args()

    fixtures_root = args.fixtures_dir or _DEFAULT_FIXTURES
    if not fixtures_root.is_absolute():
        fixtures_root = Path.cwd() / fixtures_root

    all_sgfs = _collect_sgfs(fixtures_root)
    if not all_sgfs:
        print(f"No SGF files found under: {fixtures_root}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    sample = rng.sample(all_sgfs, min(args.count, len(all_sgfs)))

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"{timestamp}.log"

    header = (
        f"probe_frame_gp  {datetime.now().isoformat(timespec='seconds')}\n"
        f"fixtures root   : {fixtures_root}\n"
        f"total SGFs      : {len(all_sgfs)}\n"
        f"sampled         : {len(sample)}\n"
        f"ko              : {args.ko}   margin: {args.margin}\n"
        f"komi            : {args.komi}\n"
        f"offence_to_win  : {args.offence_to_win}\n"
        f"seed            : {args.seed if args.seed is not None else '(random)'}\n"
    )
    print(header)

    log_lines: list[str] = [header]

    for sgf_path in sample:
        block = _render_puzzle(
            sgf_path,
            margin=args.margin,
            komi=args.komi,
            ko=args.ko,
            offence_to_win=args.offence_to_win,
        )
        print(block)
        log_lines.append(block)

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n{'-' * 60}")
    print(f"Log written -> {log_path}")


if __name__ == "__main__":
    main()
