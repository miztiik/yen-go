"""Render all technique fixtures as ASCII boards for expert review.
Standalone script — run from tools/puzzle-enrichment-lab/.
"""
import os
import re
import sys

sys.path.insert(0, ".")
from analyzers.ascii_board import render_sgf_ascii

FIXTURES_DIR = "tests/fixtures"

# Technique files only (skip test artifacts)
SKIP_PREFIXES = ("board_", "broken_", "position_only_", "no_pl_", "white_to_play")


def extract_prop(sgf: str, prop: str) -> str:
    m = re.search(rf"{prop}\[([^\]]*)\]", sgf)
    return m.group(1) if m else ""


def main():
    files = sorted(
        f
        for f in os.listdir(FIXTURES_DIR)
        if f.endswith(".sgf") and not f.startswith(SKIP_PREFIXES)
    )
    print(f"Found {len(files)} technique fixture files\n")

    results = []
    for fname in files:
        path = os.path.join(FIXTURES_DIR, fname)
        sgf = open(path, encoding="utf-8").read()
        technique = fname.replace(".sgf", "").replace("_puzzle", "").replace("_", " ").title()

        print(f"=== {fname} (Technique: {technique}) ===")
        try:
            ascii_board = render_sgf_ascii(sgf)
            print(ascii_board)
        except Exception as e:
            print(f"ERROR rendering: {e}")
            ascii_board = f"ERROR: {e}"

        sz = extract_prop(sgf, "SZ") or "??"
        yt = extract_prop(sgf, "YT") or "none"
        yg = extract_prop(sgf, "YG") or "none"
        pc = extract_prop(sgf, "PC") or "unknown"
        yk = extract_prop(sgf, "YK") or "none"

        right_count = sgf.upper().count("RIGHT") + sgf.upper().count("CORRECT")
        wrong_count = sgf.upper().count("WRONG")

        print(f"Board: {sz}x{sz}")
        print(f"Tags: {yt}")
        print(f"Level: {yg}")
        print(f"Source: {pc}")
        print(f"Ko: {yk}")
        print(f"Solution: {right_count} correct, {wrong_count} wrong branches")
        print()

        results.append({
            "filename": fname,
            "technique": technique,
            "board": ascii_board,
            "size": sz,
            "tags": yt,
            "level": yg,
            "source": pc,
            "ko": yk,
            "correct": right_count,
            "wrong": wrong_count,
        })

    return results


if __name__ == "__main__":
    main()
