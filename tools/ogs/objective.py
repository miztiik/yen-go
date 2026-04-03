"""
Objective parser for OGS puzzle HTML pages.

Extracts objective phrases like "Black to play and live" or "White to kill"
from the puzzle page HTML (title, meta tags, or visible text) and maps them
to canonical YenGo tags using the aliases defined in config/tags.json.

The mapping is minimal and deterministic: each keyword maps to exactly one
tag, and the same HTML always produces the same tag set.
"""

from __future__ import annotations

import logging
import re

from .tags import get_tag_mapper

logger = logging.getLogger("ogs.objective")


# Deterministic keyword-to-tag mapping.
# Keys are lowercase phrases found in OGS puzzle objectives;
# values are canonical tag IDs from config/tags.json.
_OBJECTIVE_KEYWORDS: list[tuple[str, str]] = [
    # Longer phrases first to avoid partial matches
    ("life and death", "life-and-death"),
    ("life-and-death", "life-and-death"),
    ("connect and die", "connect-and-die"),
    ("capture race", "capture-race"),
    ("capturing race", "capture-race"),
    ("double atari", "double-atari"),
    ("under the stones", "under-the-stones"),
    ("snap back", "snapback"),
    ("throw in", "throw-in"),
    ("throw-in", "throw-in"),
    ("and live", "living"),
    ("to live", "living"),
    ("make life", "living"),
    ("and kill", "life-and-death"),
    ("to kill", "life-and-death"),
    ("and die", "life-and-death"),
    ("semeai", "capture-race"),
    ("snapback", "snapback"),
    ("ladder", "ladder"),
    ("shicho", "ladder"),
    ("geta", "net"),
    ("net", "net"),
    ("ko", "ko"),
    ("seki", "seki"),
    ("nakade", "nakade"),
    ("tesuji", "tesuji"),
    ("escape", "escape"),
    ("connect", "connection"),
    ("cut", "cutting"),
    ("endgame", "endgame"),
    ("yose", "endgame"),
    ("joseki", "joseki"),
    ("fuseki", "fuseki"),
]


def extract_objective_text(html: str) -> str | None:
    """Extract the objective/title text from OGS puzzle HTML.

    Looks for the puzzle name in:
    1. <title> tag
    2. <meta property="og:title"> tag
    3. <h1> or heading text

    Args:
        html: Raw HTML page content

    Returns:
        Extracted objective text, or None if not found
    """
    if not html:
        return None

    # Try <title> tag first
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = _strip_html_tags(m.group(1)).strip()
        # OGS titles look like "Puzzle Name - OGS" — strip the suffix
        title = re.sub(r"\s*[-|]\s*OGS.*$", "", title, flags=re.IGNORECASE).strip()
        if title:
            return title

    # Try og:title meta tag
    m = re.search(
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if m:
        return _strip_html_tags(m.group(1)).strip()

    return None


def parse_objective_tags(text: str) -> list[str]:
    """Parse objective text into canonical tag IDs.

    Scans the text for known keywords and maps them to tags from
    config/tags.json. Results are deduplicated and sorted.

    Args:
        text: Objective text (e.g. "Black to play and live")

    Returns:
        Sorted list of unique canonical tag IDs (e.g. ["living"])
    """
    if not text:
        return []

    lower = text.lower()
    mapper = get_tag_mapper()
    tags: set[str] = set()

    for keyword, tag_id in _OBJECTIVE_KEYWORDS:
        if keyword in lower:
            # Validate the tag exists in the system
            if mapper.map_puzzle_type(tag_id) is not None or tag_id in mapper._tags:
                tags.add(tag_id)

    return sorted(tags)


def parse_objective_from_html(html: str) -> list[str]:
    """End-to-end: extract objective text from HTML and return tags.

    Args:
        html: Raw puzzle page HTML

    Returns:
        Sorted list of canonical tag IDs, empty if nothing found
    """
    text = extract_objective_text(html)
    if not text:
        logger.debug("No objective text found in HTML")
        return []

    tags = parse_objective_tags(text)
    if tags:
        logger.debug(f"Parsed objective '{text}' -> tags: {tags}")
    else:
        logger.debug(f"Objective text '{text}' matched no tags")

    return tags


def _strip_html_tags(s: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", s)
