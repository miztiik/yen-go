"""
SGF enrichment for GoProblems puzzles.

Parses existing SGF from the GoProblems API, modifies root-node properties
(strip unwanted, inject YenGo properties), and rebuilds the SGF string.

Uses tools.core.sgf_parser for parsing and tools.core.sgf_builder for
serialization — ensuring all move-node properties (LB[], MN[], etc.)
are preserved through the round-trip.

Per CLAUDE.md spec:
- Root C[] is REMOVED during enrichment (text extracted for intent resolution)
- Move C[] is PRESERVED
- SO is REMOVED
- RU, SY, DT are REMOVED (non-essential source metadata)
- KM, GN, TM are REMOVED (game metadata irrelevant for puzzles)
- Duplicate GM, FF, CA are REMOVED (we inject canonical versions)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import (
    SGFParseError,
    parse_sgf,
)

logger = logging.getLogger("go_problems.converter")

# YenGo SGF schema version (standalone, no backend import)
YENGO_SGF_VERSION = 10

# Properties to strip from root node during enrichment.
_STRIP_PROPERTIES = {
    "C", "SO", "RU", "SY", "DT", "GM", "FF", "CA", "AP", "ST", "KM", "GN", "TM",
}


def escape_sgf_text(text: str) -> str:
    """Escape special characters in SGF text.

    SGF requires escaping: backslash, close bracket, colon.
    """
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("]", "\\]").replace(":", "\\:")


@dataclass
class ConversionResult:
    """Result of converting/enriching an API response SGF."""

    success: bool
    sgf_content: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _extract_root_comment(sgf: str) -> str | None:
    """Extract root C[] text before enrichment strips it.

    Uses the tree parser internally so escaped brackets are handled
    correctly.

    Returns the unescaped text content of the root comment, or None.
    """
    try:
        tree = parse_sgf(sgf)
        if tree.root_comment:
            return tree.root_comment.strip() or None
        return None
    except SGFParseError:
        return None


def enrich_sgf(
    sgf_content: str,
    puzzle_id: int | str,
    level: str,
    tags: list[str],
    pl_value: str,
    collection_slugs: list[str] | None = None,
    yq_value: str | None = None,
    root_comment: str | None = None,
) -> str:
    """Enrich existing SGF with YenGo properties.

    Parses the SGF into a tree, strips unwanted root properties, injects
    YenGo custom properties, and rebuilds the SGF string.  All move-node
    properties (LB, MN, TR, etc.) are preserved through the round-trip.

    Args:
        sgf_content: Original SGF content from GoProblems API
        puzzle_id: GoProblems puzzle ID
        level: YenGo level slug (e.g., "intermediate")
        tags: List of YenGo tags
        pl_value: Player to move ("B" or "W")
        collection_slugs: Optional list of collection slugs for YL[]
        yq_value: Optional YQ property value (e.g., "q:3;rc:0;hc:0")
        root_comment: Optional resolved objective slug for root C[]

    Returns:
        Enriched SGF string
    """
    from tools.core.sgf_types import Color

    # --- Parse ---
    tree = parse_sgf(sgf_content)

    # --- Build via SGFBuilder.from_tree (preserves solution tree) ---
    builder = SGFBuilder.from_tree(tree)

    # --- Strip unwanted metadata ---
    for key in list(builder.metadata.keys()):
        if key in _STRIP_PROPERTIES:
            del builder.metadata[key]

    # Clear original root comment (it was extracted earlier for intent)
    builder.root_comment = ""

    # --- Inject canonical standard properties ---
    # These replace any stripped originals.  SGFBuilder.build() always
    # emits GM[1], FF[4] so we don't need to set them as metadata.

    # Player to move
    builder.set_player_to_move(
        Color.WHITE if pl_value == "W" else Color.BLACK
    )

    # --- Inject YenGo properties ---
    builder.set_version(YENGO_SGF_VERSION)
    builder.set_level_slug(level)

    if tags:
        builder.add_tags(tags)

    if collection_slugs:
        builder.set_collections(collection_slugs)

    if yq_value:
        builder.yengo_props.quality = yq_value

    if root_comment:
        builder.set_comment(root_comment)

    # --- Rebuild ---
    return builder.build()


def convert_puzzle(
    api_response: dict[str, Any],
    puzzle_ref: str,
    level: str,
    tags: list[str],
    collection_slugs: list[str] | None = None,
    yq_value: str | None = None,
    root_comment: str | None = None,
) -> ConversionResult:
    """Convert/enrich GoProblems API response to YenGo SGF.

    Args:
        api_response: Raw JSON response from /api/v2/problems/{id}
        puzzle_ref: Reference string for logging
        level: YenGo level slug
        tags: List of YenGo tags
        collection_slugs: Optional collection slugs for YL[]
        yq_value: Optional YQ property value
        root_comment: Optional resolved objective slug for root C[]

    Returns:
        ConversionResult with enriched SGF content or error
    """
    try:
        sgf_content = api_response.get("sgf", "")
        if not sgf_content:
            return ConversionResult(
                success=False,
                error=f"Missing SGF content in API response for {puzzle_ref}",
            )

        if not sgf_content.startswith("(;"):
            if "(;" in sgf_content:
                sgf_content = sgf_content[sgf_content.index("(;"):]
            else:
                return ConversionResult(
                    success=False,
                    error=f"Invalid SGF format for {puzzle_ref}: doesn't start with '(;'",
                )

        puzzle_id = api_response.get("id", "unknown")

        # Determine player to move
        player_color = api_response.get("playerColor", "black")
        pl_value = (
            "B" if not player_color or player_color.lower() == "black" else "W"
        )

        enriched_sgf = enrich_sgf(
            sgf_content=sgf_content,
            puzzle_id=puzzle_id,
            level=level,
            tags=tags,
            pl_value=pl_value,
            collection_slugs=collection_slugs,
            yq_value=yq_value,
            root_comment=root_comment,
        )

        # Build metadata
        metadata: dict[str, Any] = {
            "puzzle_id": puzzle_id,
            "level": level,
            "tags": tags,
            "player_to_move": pl_value,
        }

        if api_response.get("rank"):
            rank = api_response["rank"]
            metadata["rank_value"] = rank.get("value")
            metadata["rank_unit"] = rank.get("unit")

        if api_response.get("rating"):
            rating = api_response["rating"]
            metadata["rating_stars"] = rating.get("stars")
            metadata["rating_votes"] = rating.get("votes")

        metadata["is_canon"] = api_response.get("isCanon", False)

        return ConversionResult(
            success=True,
            sgf_content=enriched_sgf,
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Conversion failed for {puzzle_ref}: {e}")
        return ConversionResult(
            success=False,
            error=f"Conversion error for {puzzle_ref}: {e!s}",
        )
