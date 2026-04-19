"""OCR utilities for PDF-to-SGF pipeline.

Provides text recognition for:
- Player-to-move detection (footer text below board)
- Problem label detection (header text above board)
- Answer section detection (page header markers)

Requires: pytesseract + Tesseract engine installed on system.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    import pytesseract  # noqa: F401 — type hints only

log = logging.getLogger(__name__)


def _get_pytesseract():
    """Lazy-import pytesseract to avoid blocking when Tesseract binary is missing."""
    import pytesseract as _pt
    return _pt


def ensure_tesseract() -> str:
    """Validate that Tesseract is accessible. Returns version string.

    Raises RuntimeError with installation instructions if not found.
    """
    pt = _get_pytesseract()
    try:
        version = pt.get_tesseract_version()
        log.debug("[OCR] Tesseract version: %s", version)
        return str(version)
    except pt.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract OCR engine not found. Install it:\n"
            "  Windows: choco install tesseract\n"
            "  macOS:   brew install tesseract\n"
            "  Linux:   apt install tesseract-ocr\n"
            "Also install language packs: tesseract-ocr-jpn (Japanese)"
        ) from None


def ocr_region(image: Image.Image, lang: str = "eng+jpn") -> str:
    """Extract text from an image region via Tesseract.

    Args:
        image: PIL Image to OCR.
        lang: Tesseract language string (default: English + Japanese).

    Returns:
        Extracted text, stripped of leading/trailing whitespace.
    """
    pt = _get_pytesseract()
    try:
        text = pt.image_to_string(image, lang=lang, config="--psm 6")
        return text.strip()
    except Exception as exc:
        log.warning("[OCR] Failed to extract text: %s", exc)
        return ""


def ocr_line(image: Image.Image, lang: str = "eng+jpn",
             tesseract_config: str = "--psm 7") -> str:
    """Extract a single line of text from an image region.

    Uses PSM 7 (single text line) for better accuracy on short text.
    """
    pt = _get_pytesseract()
    try:
        text = pt.image_to_string(image, lang=lang, config=tesseract_config)
        return text.strip()
    except Exception as exc:
        log.warning("[OCR] Failed to extract line: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Player-to-move detection
# ---------------------------------------------------------------------------

# Patterns for "Black to play" / "White to play" in multiple languages
_BLACK_PATTERNS = re.compile(
    r"black\s+to\s+(?:play|move)|黒番|黒先|黑先|黑番|black'?s?\s+turn",
    re.IGNORECASE,
)
_WHITE_PATTERNS = re.compile(
    r"white\s+to\s+(?:play|move)|白番|白先|white'?s?\s+turn",
    re.IGNORECASE,
)


def detect_player_to_move(
    page_image: Image.Image,
    board_bbox: tuple[int, int, int, int],
    footer_height: int = 50,
) -> str | None:
    """Detect player-to-move from text below the board.

    Args:
        page_image: Full page image.
        board_bbox: (x, y, w, h) of the board region on the page.
        footer_height: Height of footer region to scan (pixels).

    Returns:
        "B" for Black, "W" for White, or None if undetected.
    """
    x, y, w, h = board_bbox
    page_w, page_h = page_image.size

    # Extract region below the board
    footer_top = min(y + h, page_h)
    footer_bottom = min(footer_top + footer_height, page_h)
    if footer_bottom - footer_top < 10:
        return None

    footer = page_image.crop(
        (max(0, x - 20), footer_top, min(x + w + 20, page_w), footer_bottom)
    )

    text = ocr_line(footer)
    if not text:
        return None

    if _BLACK_PATTERNS.search(text):
        log.debug("[OCR] Detected: Black to play (text=%r)", text)
        return "B"
    if _WHITE_PATTERNS.search(text):
        log.debug("[OCR] Detected: White to play (text=%r)", text)
        return "W"

    return None


# ---------------------------------------------------------------------------
# Problem label detection
# ---------------------------------------------------------------------------

_LABEL_PATTERNS = [
    re.compile(r"(?:Problem|Prob\.?)\s*#?\s*(\d+)", re.IGNORECASE),
    re.compile(r"第\s*(\d+)\s*問"),
    re.compile(r"問題\s*(\d+)"),
    re.compile(r"#\s*(\d+)"),
    re.compile(r"^(\d+)[\.\)]\s*$"),  # Just "42." or "42)"
    re.compile(r"^(\d+)\s*$"),          # Bare number "1", "42"
]


def detect_problem_label(
    page_image: Image.Image,
    board_bbox: tuple[int, int, int, int],
    header_height: int = 40,
    footer_height: int = 50,
) -> str | None:
    """Detect problem label from text above or below the board.

    Scans the header region first, then the footer region if no label
    is found above. Some PDFs place problem numbers below the board.

    Args:
        page_image: Full page image.
        board_bbox: (x, y, w, h) of the board region.
        header_height: Height of header region to scan (pixels).
        footer_height: Height of footer region to scan (pixels).

    Returns:
        Detected label string or None.
    """
    x, y, w, h = board_bbox
    page_w, page_h = page_image.size

    # Try header region (above the board) first
    header_bottom = max(y, 0)
    header_top = max(header_bottom - header_height, 0)
    if header_bottom - header_top >= 10:
        header = page_image.crop(
            (max(0, x - 20), header_top, min(x + w + 20, page_w), header_bottom)
        )
        text = ocr_line(header)
        if text:
            for pattern in _LABEL_PATTERNS:
                m = pattern.search(text)
                if m:
                    label = text.strip()
                    log.debug("[OCR] Detected label (header): %r (raw=%r)", label, text)
                    return label

    # Try footer region (below the board)
    footer_top = min(y + h, page_h)
    footer_bottom = min(footer_top + footer_height, page_h)
    if footer_bottom - footer_top >= 10:
        footer = page_image.crop(
            (max(0, x - 20), footer_top, min(x + w + 20, page_w), footer_bottom)
        )
        # Use digits-only whitelist for footer labels (typically bare numbers)
        text = ocr_line(footer, lang="eng",
                        tesseract_config="--psm 7 -c tessedit_char_whitelist=0123456789")
        if text:
            for pattern in _LABEL_PATTERNS:
                m = pattern.search(text)
                if m:
                    label = text.strip()
                    log.debug("[OCR] Detected label (footer): %r (raw=%r)", label, text)
                    return label

    return None


# ---------------------------------------------------------------------------
# Answer section detection
# ---------------------------------------------------------------------------

_ANSWER_MARKERS = re.compile(
    r"答え|answer|solution|解答|正解|solutions|answers",
    re.IGNORECASE,
)


def detect_answer_page(page_image: Image.Image) -> tuple[bool, str]:
    """Detect if a page is the start of an answer section.

    Scans the top 15% of the page for answer-section header markers.

    Args:
        page_image: Full page image.

    Returns:
        (is_answer_page, matched_marker_text)
    """
    w, h = page_image.size
    header_h = max(int(h * 0.15), 50)
    header = page_image.crop((0, 0, w, header_h))

    text = ocr_region(header)
    if not text:
        return False, ""

    match = _ANSWER_MARKERS.search(text)
    if match:
        marker = match.group()
        log.debug("[OCR] Answer section marker found: %r (full=%r)", marker, text)
        return True, marker

    return False, ""


def find_answer_start(
    pages: list[Image.Image],
    page_numbers: list[int] | None = None,
) -> tuple[int | None, str]:
    """Scan pages from end backwards to find the answer section start.

    Solutions are typically at the back of tsumego books, so scanning
    backwards is more efficient.

    Args:
        pages: List of page images.
        page_numbers: Optional 1-based page numbers (defaults to 1..N).

    Returns:
        (page_number, marker_text) or (None, "") if not found.
    """
    if page_numbers is None:
        page_numbers = list(range(1, len(pages) + 1))

    # Track the earliest answer page found scanning backwards
    earliest_answer: int | None = None
    earliest_marker: str = ""

    for i in reversed(range(len(pages))):
        is_answer, marker = detect_answer_page(pages[i])
        if is_answer:
            earliest_answer = page_numbers[i]
            earliest_marker = marker
        else:
            # Stop scanning backwards once we hit a non-answer page
            # (answer section is contiguous at the end)
            if earliest_answer is not None:
                break

    return earliest_answer, earliest_marker


# ---------------------------------------------------------------------------
# PDF text-layer label extraction (no OCR needed)
# ---------------------------------------------------------------------------


def extract_labels_from_pdf_text(
    pdf_path: str | Path,
    page_number: int,
    board_count: int,
) -> list[str]:
    """Extract problem labels from the PDF text layer using PyMuPDF.

    Much more reliable than image-based OCR for digitally-created PDFs.
    Each board diagram is a multi-line text block whose last line is
    the problem number. Blocks are sorted in reading order (top-to-bottom,
    left-to-right) and matched positionally to detected boards.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number to extract from.
        board_count: Expected number of boards on this page (for
            validation — returns empty if mismatch).

    Returns:
        List of label strings in reading order, one per board.
        Empty list if extraction fails or count doesn't match.
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    if page_number < 1 or page_number > len(doc):
        log.warning("[OCR] Page %d out of range (PDF has %d pages)",
                    page_number, len(doc))
        doc.close()
        return []

    page = doc[page_number - 1]  # 0-indexed
    blocks = page.get_text("blocks")

    # Filter to board-diagram blocks: multi-line (>=5 lines) with a
    # trailing digit.  Page headers, titles, etc. have fewer lines.
    board_blocks: list[tuple[float, float, str]] = []
    for block in blocks:
        x0, y0, x1, y1, text_raw, _block_no, _flags = block
        text = text_raw.strip()
        if not text:
            continue

        lines = text.split("\n")
        if len(lines) < 5:
            continue

        last_line = lines[-1].strip()
        if last_line.isdigit():
            # Use block center for sorting into reading order
            board_blocks.append((y0, x0, last_line))

    if not board_blocks:
        log.debug("[OCR] No text-layer labels found on page %d", page_number)
        doc.close()
        return []

    # Sort in reading order: top-to-bottom (y), then left-to-right (x).
    # Y coordinates may have sub-pixel jitter within the same visual row,
    # so bucket by rounding to nearest integer point before comparing.
    board_blocks.sort(key=lambda b: (round(b[0]), b[1]))
    labels = [lbl for _, _, lbl in board_blocks]

    if len(labels) != board_count:
        log.warning("[OCR] Text-layer found %d labels but %d boards on page %d "
                    "— skipping text-layer extraction",
                    len(labels), board_count, page_number)
        doc.close()
        return []

    log.debug("[OCR] Text-layer labels on page %d: %s", page_number, labels)
    doc.close()
    return labels
