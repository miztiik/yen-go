"""Probe the tsumego frame on a random sample of fixture SGFs.

Picks N SGF files at random from the entire fixtures tree (or a
specified sub-directory), applies the tsumego frame, and prints
before/after ASCII boards to stdout.  The same output is also
written to .pm-runtime/frame-test/<YYYYMMDD-HHMMSS>.log so each
run produces a unique, permanent record.

Usage (from tools/puzzle-enrichment-lab/):
    python scripts/probe_frame.py
    python scripts/probe_frame.py --count 10
    python scripts/probe_frame.py --fixtures-dir tests/fixtures/calibration/cho-elementary
    python scripts/probe_frame.py --ko direct --margin 3
    python scripts/probe_frame.py --seed 42
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
_REPO_ROOT = _LAB.parent.parent
if str(_LAB) not in sys.path:
    sys.path.insert(0, str(_LAB))

from analyzers.ascii_board import render_ascii
from analyzers.frame_adapter import apply_frame
from core.tsumego_analysis import extract_position, parse_sgf

_SKIP_DIRS = {"results", "__pycache__", ".pytest_cache"}
_DEFAULT_FIXTURES = _LAB / "tests" / "fixtures"
_LOG_DIR = _LAB / ".lab-runtime" / "frame-test"


def _collect_sgfs(root: Path) -> list[Path]:
    """Recursively collect all .sgf files, skipping result/cache dirs."""
    result = []
    for path in root.rglob("*.sgf"):
        if not any(part in _SKIP_DIRS for part in path.parts):
            result.append(path)
    return sorted(result)


def _sep(title: str, width: int = 60) -> str:
    return f"\n{'-' * width}\n  {title}\n{'-' * width}"


def _render_puzzle(sgf_path: Path, ko: str, margin: int) -> str:
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
        frame_result = apply_frame(position, margin=margin, ko=(ko != "none"))
        framed = frame_result.position
        added = frame_result.frame_stones_added
    except Exception as exc:
        return (
            f"{_sep(f'FILE: {sgf_path}')}\n"
            f"{_sep('ORIGINAL ASCII')}\n{render_ascii(position)}\n"
            f"[FRAME ERROR: {exc}]\n"
        )

    blocks = [
        _sep(f"FILE: {sgf_path}"),
        "\n=== ORIGINAL SGF ===",
        sgf_text.strip(),
        "\n=== ORIGINAL ASCII ===",
        render_ascii(position),
        f"\n=== FRAMED SGF  (+{added} stones, ko={ko}, margin={margin}) ===",
        framed.to_sgf(),
        "\n=== FRAMED ASCII ===",
        render_ascii(framed),
    ]
    return "\n".join(blocks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe tsumego framing on a random sample of fixture SGFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/probe_frame.py
  python scripts/probe_frame.py --count 10
  python scripts/probe_frame.py --fixtures-dir tests/fixtures/calibration/cho-elementary
  python scripts/probe_frame.py --ko direct --margin 3
  python scripts/probe_frame.py --seed 42
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
        choices=["none", "direct", "approach"],
        default="none",
        help="Ko context passed to the frame (default: none).",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=2,
        help="Empty margin around stones (default: 2).",
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
        f"probe_frame  {datetime.now().isoformat(timespec='seconds')}\n"
        f"fixtures root : {fixtures_root}\n"
        f"total SGFs    : {len(all_sgfs)}\n"
        f"sampled       : {len(sample)}\n"
        f"ko            : {args.ko}   margin: {args.margin}\n"
        f"seed          : {args.seed if args.seed is not None else '(random)'}\n"
    )
    print(header)

    log_lines: list[str] = [header]

    for sgf_path in sample:
        block = _render_puzzle(sgf_path, ko=args.ko, margin=args.margin)
        print(block)
        log_lines.append(block)

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n{'-' * 60}")
    print(f"Log written → {log_path}")


if __name__ == "__main__":
    main()
