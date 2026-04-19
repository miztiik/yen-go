"""Parse text-based solution sequences from PDF answer pages.

Many tsumego books list solutions as text rather than board diagrams:
    (1) D1 F1 G1
    (2) D1 C1 A2 A4 E1 A5 D2
    ...

This module extracts those text solutions from PDF pages using PyMuPDF
and parses GTP coordinates into Point objects for SGF generation.

Usage:
    from tools.pdf_to_sgf.text_solution_parser import extract_text_solutions_from_pdf

    solutions = extract_text_solutions_from_pdf(pdf_path, (26, 28))
    sol = solutions[1]  # solution for problem 1
    print(sol.moves)    # [Point(3, 18), Point(5, 18), Point(6, 18)]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.sgf_types import Color, Point

log = logging.getLogger(__name__)

# Matches lines like "(42) D1 C1 A2 A4 E1" or "(1) D1 F1 G1"
# Captures: group(1) = problem number, group(2) = move sequence
_SOLUTION_LINE_RE = re.compile(
    r"\((\d+)\)\s+((?:[A-Ta-t]\d{1,2}\s*)+)",
)

# Matches individual GTP coordinates within the move sequence
_GTP_MOVE_RE = re.compile(r"[A-Ta-t]\d{1,2}")


@dataclass
class TextSolution:
    """A parsed text-based solution for a puzzle."""

    problem_number: int
    """Problem number as it appears in the solution key."""

    moves: list[Point] = field(default_factory=list)
    """Solution moves in order (GTP-parsed)."""

    raw_text: str = ""
    """Original text for debugging."""


def parse_solution_line(
    line: str,
    board_size: int = 19,
) -> TextSolution | None:
    """Parse a single solution line like '(42) D1 C1 A2 A4 E1'.

    Returns None if the line doesn't match the expected format.
    """
    m = _SOLUTION_LINE_RE.search(line)
    if not m:
        return None

    problem_num = int(m.group(1))
    move_text = m.group(2)

    gtp_coords = _GTP_MOVE_RE.findall(move_text)
    moves: list[Point] = []
    for coord in gtp_coords:
        try:
            pt = Point.from_gtp(coord, board_size=board_size)
            moves.append(pt)
        except ValueError as exc:
            log.warning("Skipping invalid GTP coordinate %r in problem %d: %s",
                        coord, problem_num, exc)

    if not moves:
        return None

    return TextSolution(
        problem_number=problem_num,
        moves=moves,
        raw_text=line.strip(),
    )


def parse_text_solutions(
    text: str,
    board_size: int = 19,
) -> dict[int, TextSolution]:
    """Parse multi-line solution text into a dict keyed by problem number.

    Handles solutions that may span multiple lines by joining the full
    text and scanning for all `(N) moves...` patterns.
    """
    # Normalize: collapse newlines to spaces so multi-line solutions work
    normalized = " ".join(text.split())

    solutions: dict[int, TextSolution] = {}

    # Find all solution entries: (N) followed by GTP moves, up to next (N) or end
    # Split on solution boundaries
    parts = re.split(r"(?=\(\d+\)\s)", normalized)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        sol = parse_solution_line(part, board_size=board_size)
        if sol:
            if sol.problem_number in solutions:
                log.warning("Duplicate solution for problem %d — keeping first",
                            sol.problem_number)
            else:
                solutions[sol.problem_number] = sol

    return solutions


def extract_text_solutions_from_pdf(
    pdf_path: str | Path,
    page_range: tuple[int, int | None],
    board_size: int = 19,
) -> dict[int, TextSolution]:
    """Extract text solutions from PDF answer pages using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.
        page_range: (start, end) 1-based page numbers. end=None means last page.
        board_size: Go board size for coordinate parsing.

    Returns:
        Dict mapping problem number to TextSolution.
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    start_page, end_page = page_range
    if end_page is None:
        end_page = total_pages

    # Collect all text from answer pages
    all_text_parts: list[str] = []
    for page_num in range(start_page, end_page + 1):
        if page_num < 1 or page_num > total_pages:
            continue
        page = doc[page_num - 1]  # 0-indexed
        text = page.get_text()
        if text.strip():
            log.debug("[TEXT_SOL] Page %d text (%d chars): %s",
                      page_num, len(text), text[:200].replace("\n", "\\n"))
            all_text_parts.append(text)

    doc.close()

    if not all_text_parts:
        log.warning("No text found on answer pages %d-%d", start_page, end_page)
        return {}

    combined = "\n".join(all_text_parts)
    solutions = parse_text_solutions(combined, board_size=board_size)

    log.info("Extracted %d text solutions from pages %d-%d",
             len(solutions), start_page, end_page)

    return solutions
