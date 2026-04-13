"""Ground truth test suite for digit detection on Harada answer images.

Each test case was visually verified from the original GIF image
and cross-checked with the pixel bitmaps extracted by the recognizer.

Run: python -m tools.minoru_harada_tsumego.test_digit_detection
"""

from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image
from tools.core.image_to_board import (
    recognize_position,
    detect_digit,
    BLACK,
    WHITE,
)

_IMG_DIR = Path("tools/minoru_harada_tsumego/_working")

# Ground truth: (label, problem_path, answer_path, [(iy, ix, color, digit), ...])
# Colors: BLACK = "X", WHITE = "O"
# Verified by viewing each GIF and cross-checking with bitmap extraction.
GROUND_TRUTH = [
    # #1 elementary: B[cb]=1 W[bb]=2 B[ac]=3 W[ab]=4 B[ba]=5
    ("001e",
     "_images/1996/1996_001_problem_elementary.gif",
     "_images/1996/1996_001_answer_correct_elementary.gif",
     [(1, 2, BLACK, 1), (1, 1, WHITE, 2), (2, 0, BLACK, 3),
      (1, 0, WHITE, 4), (0, 1, BLACK, 5)]),

    # #8 elementary: B[ab]=1 W[bb]=2 B[ea]=3 W[da]=4 B[ba]=5
    ("008e",
     "_images/1996/1996_008_problem_elementary.gif",
     "_images/1996/1996_008_answer_correct_elementary.gif",
     [(1, 0, BLACK, 1), (1, 1, WHITE, 2), (0, 4, BLACK, 3),
      (0, 3, WHITE, 4), (0, 1, BLACK, 5)]),

    # #12 elementary: B=1 W=2 B=3 W=4 B=5
    ("012e",
     "_images/1996/1996_012_problem_elementary.gif",
     "_images/1996/1996_012_answer_correct_elementary.gif",
     [(0, 1, BLACK, 1), (0, 2, WHITE, 2), (1, 1, BLACK, 3),
      (2, 1, WHITE, 4), (0, 3, BLACK, 5)]),

    # #14 elementary: B=1 W=2 B=3 B=5 W=6 B=7
    ("014e",
     "_images/1996/1996_014_problem_elementary.gif",
     "_images/1996/1996_014_answer_correct_elementary.gif",
     [(0, 3, BLACK, 1), (0, 2, WHITE, 2), (1, 2, BLACK, 3),
      (0, 1, BLACK, 5), (0, 5, WHITE, 6), (1, 0, BLACK, 7)]),

    # #17 elementary: B=1 W=2 B=3 W=4 B=5 W=6 B=7
    ("017e",
     "_images/1996/1996_017_problem_elementary.gif",
     "_images/1996/1996_017_answer_correct_elementary.gif",
     [(0, 2, BLACK, 1), (1, 3, WHITE, 2), (0, 4, BLACK, 3),
      (1, 0, WHITE, 4), (2, 0, BLACK, 5), (2, 1, WHITE, 6),
      (0, 0, BLACK, 7)]),

    # #16 intermediate: bitmap-verified
    ("016m",
     "_images/1996/1996_016_problem_intermediate.gif",
     "_images/1996/1996_016_answer_correct_intermediate.gif",
     [(0, 5, BLACK, 1), (1, 5, WHITE, 2), (1, 6, BLACK, 3),
      (1, 7, WHITE, 4), (0, 6, BLACK, 5), (0, 7, WHITE, 6),
      (0, 4, BLACK, 7)]),

    # #21 intermediate: B=1 W=2 B=3 W=4 B=5 W=6 B=7
    ("021m",
     "_images/1996/1996_021_problem_intermediate.gif",
     "_images/1996/1996_021_answer_correct_intermediate.gif",
     [(2, 0, BLACK, 1), (1, 0, WHITE, 2), (0, 1, BLACK, 3),
      (0, 2, WHITE, 4), (1, 2, BLACK, 5), (1, 3, WHITE, 6),
      (0, 3, BLACK, 7)]),

    # #23 elementary: bitmap-verified
    ("023e",
     "_images/1996/1996_023_problem_elementary.gif",
     "_images/1996/1996_023_answer_correct_elementary.gif",
     [(1, 1, BLACK, 1), (1, 2, WHITE, 2), (2, 0, BLACK, 3),
      (1, 0, WHITE, 4), (0, 0, BLACK, 5), (0, 2, WHITE, 6),
      (3, 0, BLACK, 7), (0, 6, WHITE, 8), (0, 4, BLACK, 9)]),

    # #412 elementary: user-confirmed ground truth
    ("412e",
     "_images/2004/2004_412_problem_elementary.gif",
     "_images/2004/2004_412_answer_correct_elementary.gif",
     [(0, 3, BLACK, 1), (1, 3, WHITE, 2), (0, 7, BLACK, 3),
      (0, 4, WHITE, 4), (1, 5, BLACK, 5)]),
]


def run_tests(verbose: bool = False) -> tuple[int, int, int]:
    """Run digit detection against ground truth. Returns (total, correct, wrong)."""
    total = correct = wrong = 0
    failed: list[tuple[str, int, int, int, int]] = []

    for label, prob_rel, ans_rel, expected_digits in GROUND_TRUTH:
        ans_path = _IMG_DIR / ans_rel
        if not ans_path.exists():
            print(f"SKIP {label}: file not found")
            continue

        ans_pos = recognize_position(str(ans_path))
        img = Image.open(str(ans_path)).convert("RGB")

        for iy, ix, stone_color, expected in expected_digits:
            cx = ans_pos.grid.x_lines[ix]
            cy = ans_pos.grid.y_lines[iy]
            detected = detect_digit(img, cx, cy, stone_color).digit
            total += 1
            if detected == expected:
                correct += 1
                if verbose:
                    print(f"  {label} ({iy},{ix}) d={expected} OK")
            else:
                wrong += 1
                failed.append((label, iy, ix, expected, detected))

    print(f"\n{'=' * 50}")
    print(f"DIGIT DETECTION TEST RESULTS")
    print(f"{'=' * 50}")
    print(f"  Images:  {len(GROUND_TRUTH)}")
    print(f"  Digits:  {total}")
    print(f"  Correct: {correct} ({100 * correct // max(total, 1)}%)")
    print(f"  Wrong:   {wrong}")
    if failed:
        print(f"\nFAILURES:")
        for label, iy, ix, exp, det in failed:
            print(f"  {label} ({iy},{ix}): expected {exp}, got {det}")
    print()
    return total, correct, wrong


if __name__ == "__main__":
    total, correct, wrong = run_tests("--verbose" in sys.argv or "-v" in sys.argv)
    sys.exit(0 if wrong == 0 else 1)
