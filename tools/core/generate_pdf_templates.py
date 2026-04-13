"""Generate synthetic digit templates optimized for PDF rendering style.

PDF-generated tsumego books use THICKER, anti-aliased digits compared to
the GIF-style templates used for Harada. This script generates templates
with OpenCV putText using thicker fonts.

Run: python -m tools.core.generate_pdf_templates
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

_TEMPLATE_SIZE = (10, 14)  # width, height — matches standard template size
_OUTPUT_DIR = Path(__file__).parent / "digit_templates_pdf"


def _render_digit(digit: int, size: tuple[int, int] = _TEMPLATE_SIZE) -> np.ndarray:
    """Render a single digit as a binary template image.

    Uses a thick, anti-aliased font to match PDF rendering style.
    """
    w, h = size
    # Start with larger canvas for better rendering, then resize
    scale = 4
    canvas = np.zeros((h * scale, w * scale), dtype=np.uint8)

    text = str(digit)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    thickness = 3  # Thicker than GIF-style

    # Get text size for centering
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x = (canvas.shape[1] - tw) // 2
    y = (canvas.shape[0] + th) // 2

    cv2.putText(canvas, text, (x, y), font, font_scale, 255, thickness, cv2.LINE_AA)

    # Resize to target template size
    template = cv2.resize(canvas, size, interpolation=cv2.INTER_AREA)

    # Binarize
    _, template = cv2.threshold(template, 128, 255, cv2.THRESH_BINARY)

    return template


def generate() -> None:
    """Generate all digit templates for PDF style."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for digit in range(10):
        template = _render_digit(digit)
        path = _OUTPUT_DIR / f"digit_{digit}.npy"
        np.save(str(path), template)

        # For black stones: digit is bright on dark background
        black_path = _OUTPUT_DIR / f"digit_{digit}_black.npy"
        np.save(str(black_path), template)

        # For white stones: digit is dark on light background (invert)
        white_template = 255 - template
        white_path = _OUTPUT_DIR / f"digit_{digit}_white.npy"
        np.save(str(white_path), white_template)

    print(f"Generated {10 * 3} templates in {_OUTPUT_DIR}")


if __name__ == "__main__":
    generate()
