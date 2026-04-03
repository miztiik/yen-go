"""Diagnostic script: render a puzzle SGF before and after tsumego frame.

Usage:
    python scripts/show_frame.py path/to/puzzle.sgf
    echo "(;SZ[19]...)" | python scripts/show_frame.py -

Prints an ASCII board for the raw position and again after the tsumego
frame is applied, so you can visually verify the frame is correct.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make sure puzzle-enrichment-lab root is on the path regardless of cwd.
_LAB = Path(__file__).resolve().parent.parent
if str(_LAB) not in sys.path:
    sys.path.insert(0, str(_LAB))

from analyzers.ascii_board import render_ascii
from analyzers.frame_adapter import apply_frame
from core.tsumego_analysis import extract_position, parse_sgf


def _load_sgf(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _separator(title: str, width: int = 50) -> str:
    return f"\n{'-' * width}\n  {title}\n{'-' * width}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a puzzle SGF before and after tsumego frame."
    )
    parser.add_argument(
        "sgf",
        help="Path to .sgf file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=2,
        help="Empty margin around stones in the frame (default: 2).",
    )
    parser.add_argument(
        "--no-coords",
        action="store_true",
        help="Hide coordinate labels.",
    )
    args = parser.parse_args()

    sgf_text = _load_sgf(args.sgf)
    root = parse_sgf(sgf_text)
    position = extract_position(root)

    show_coords = not args.no_coords

    print(_separator("BEFORE frame  (raw puzzle position)"))
    print(render_ascii(position, show_coords=show_coords))

    result = apply_frame(position, margin=args.margin)

    print(_separator(f"AFTER  frame  (+{result.frame_stones_added} stones added)"))
    print(render_ascii(result.position, show_coords=show_coords))


if __name__ == "__main__":
    main()
