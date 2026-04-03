"""Shared SGF regex parsing utilities for test render/report scripts.

Extracted from render_fixtures.py and generate_review_report.py to
eliminate copy-paste duplication (Finding F5).

These are visualization utilities (not production code). Regex parsing
is intentionally simpler than the full KaTrain/sgfmill parsers since
these tools only need root-node properties and stone positions.
"""

from __future__ import annotations

import re


def parse_sgf_properties(sgf_text: str) -> dict[str, str]:
    """Extract root-level SGF properties.

    Returns a dict mapping property keys (e.g. ``SZ``, ``AB``) to their
    first value string.  Only the first 2000 characters are scanned.
    """
    props: dict[str, str] = {}
    for m in re.finditer(r"([A-Z]{1,2})\[([^\]]*)\]", sgf_text[:2000]):
        key, val = m.group(1), m.group(2)
        if key not in props:
            props[key] = val
    return props


def parse_all_stones(
    sgf_text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Parse all AB and AW stones from root node.

    Returns ``(black_stones, white_stones)`` as lists of ``(x, y)`` tuples
    where ``a=0, b=1, ...``.
    """
    black: list[tuple[int, int]] = []
    white: list[tuple[int, int]] = []

    ab_match = re.search(r"AB(\[[a-s]{2}\])+", sgf_text)
    if ab_match:
        black = [
            (ord(c[0]) - ord("a"), ord(c[1]) - ord("a"))
            for c in re.findall(r"\[([a-s]{2})\]", ab_match.group())
        ]
    aw_match = re.search(r"AW(\[[a-s]{2}\])+", sgf_text)
    if aw_match:
        white = [
            (ord(c[0]) - ord("a"), ord(c[1]) - ord("a"))
            for c in re.findall(r"\[([a-s]{2})\]", aw_match.group())
        ]
    return black, white


def parse_first_move(sgf_text: str) -> tuple[str, tuple[int, int] | None]:
    """Parse the first move in the main variation (correct answer).

    Returns ``(color, (x, y))`` or ``("?", None)`` if no move found.
    """
    m = re.search(
        r";([BW])\[([a-s]{2})\]",
        sgf_text[sgf_text.find(";", 1):] if ";" in sgf_text[1:] else "",
    )
    if m:
        color = m.group(1)
        coord = (ord(m.group(2)[0]) - ord("a"), ord(m.group(2)[1]) - ord("a"))
        return color, coord
    return "?", None
