"""
Enrichment module — maps BTP metadata to YenGo properties.

Maps:
- BTP rating → YenGo level slug (via _local_level_mapping.json)
- BTP tags → YenGo tags (via _local_tag_mapping.json)
- BTP categories → YenGo collections (via _local_collections_mapping.json)
- BTP categories → intent/objective signals (via intent_signals.json)

All mapping data is loaded from config JSON files on first use (cached).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Final

from .config import (
    COLLECTIONS_MAPPING_PATH,
    INTENT_SIGNALS_PATH,
    LEVEL_MAPPING_PATH,
    TAG_MAPPING_PATH,
)

logger = logging.getLogger("btp.enrichment")


# ============================================================================
# Config loading (cached)
# ============================================================================


@lru_cache(maxsize=1)
def _load_level_mapping() -> list[dict]:
    """Load BTP rating → YenGo level breakpoints."""
    with open(LEVEL_MAPPING_PATH) as f:
        data = json.load(f)
    return data["breakpoints"]


@lru_cache(maxsize=1)
def _load_tag_mapping() -> dict[str, dict]:
    """Load BTP tag → YenGo tag mappings."""
    with open(TAG_MAPPING_PATH) as f:
        data = json.load(f)
    return data["mappings"]


@lru_cache(maxsize=1)
def _load_collections_mapping() -> tuple[dict[str, list[str]], dict[str, str]]:
    """Load BTP category → YenGo collection mappings.

    Returns:
        (name_to_slugs, letter_to_name) tuple.
    """
    with open(COLLECTIONS_MAPPING_PATH) as f:
        data = json.load(f)
    return data["mappings"], data["category_decode"]


@lru_cache(maxsize=1)
def _load_intent_signals() -> dict:
    """Load category → objective domain signals."""
    with open(INTENT_SIGNALS_PATH) as f:
        return json.load(f)


# ============================================================================
# BTP tag decoding
# ============================================================================

# Static tag list — the 99 BTP tags in canonical order.
# BTP encodes tags as 2-char strings: uppercase letter + lowercase letter.
# Index = uppercase_index(c[0]) * 26 + lowercase_index(c[1])
# e.g., "Ae" → 0*26 + 4 = 4 → "blocking"

_STATIC_TAGS: Final[list[str]] = [
    "atari", "attachment", "bamboo-joint", "bent-four", "blocking",
    "broken-ladder", "cap", "capture", "carriers-pigeon", "clamp",
    "close-off", "combination", "connect", "connection-cut", "crane-neck",
    "cross-cut", "cut", "dead-shape", "descend", "diagonal-tesuji",
    "double-atari", "double-hane", "draw-back", "exchange", "extend",
    "eye-shape", "geta", "guzumi", "hane", "jump",
    "keima-jump", "ko", "ko-fight", "kosumi", "ladder",
    "large-capture", "large-kill-group", "making-territory", "monkey-jump",
    "more-than-one-solution", "nakade", "net", "peep", "placement",
    "probing", "push-through", "reduce", "sacrifice", "seal-in",
    "seki", "separation", "shortage-of-liberties", "snapback", "squeeze",
    "table-shape", "throw-in", "tigers-mouth", "tombstone", "under-the-stones",
    "vital-point", "wedge", "carpenters-square", "ten-thousand-year-ko",
    "semeai", "cranes-nest", "making-eyes", "denying-eyes", "permanent-ko",
    "mirror-symmetry", "eternal-life", "thick-shape", "breaking-connection",
    "maintaining-connection", "two-step-ko", "windmill", "running",
    "surrounding", "weakening", "preventing-escape", "oiotoshi",
    "turning-move", "approach-move", "contact-play", "loose-ladder",
    "multi-step", "l-group", "bent-three", "straight-three", "bulky-five",
    "j-group", "rabbity-six", "group-status", "good-shape", "bad-shape",
    "mannen-ko", "two-headed-dragon", "flower-six", "enclosure-joseki",
    "large-scale-reduction",
]


def decode_btp_tags(tag_string: str) -> list[str]:
    """Decode BTP's 2-char encoded tag string to tag names.

    Args:
        tag_string: Pipe-delimited 2-char encoded tags (e.g. "Ae|Bf|Ca").

    Returns:
        List of decoded tag names.
    """
    if not tag_string:
        return []

    tags: list[str] = []
    parts = tag_string.split("|")
    for part in parts:
        part = part.strip()
        if len(part) != 2:
            continue
        upper_idx = ord(part[0]) - ord("A")
        lower_idx = ord(part[1]) - ord("a")
        if 0 <= upper_idx < 26 and 0 <= lower_idx < 26:
            idx = upper_idx * 26 + lower_idx
            if idx < len(_STATIC_TAGS):
                tags.append(_STATIC_TAGS[idx])

    return tags


# ============================================================================
# Rating → Level
# ============================================================================


def rating_to_level_slug(rating: int) -> str:
    """Map BTP rating (0–3000) to YenGo level slug.

    Uses breakpoints from _local_level_mapping.json.

    Args:
        rating: BTP difficulty rating.

    Returns:
        YenGo level slug (e.g., "intermediate").
    """
    breakpoints = _load_level_mapping()
    for bp in breakpoints:
        if bp["min_rating"] <= rating <= bp["max_rating"]:
            return bp["yengo_level"]

    # Fallback: if above 3000, treat as expert; if below 0, treat as novice
    if rating > 3000:
        return "expert"
    return "novice"


# ============================================================================
# Tags → YenGo Tags
# ============================================================================


def map_tags_to_yengo(btp_tags: list[str]) -> list[str]:
    """Map decoded BTP tag names to YenGo tag slugs.

    Uses confidence-weighted mappings from _local_tag_mapping.json.
    Unmapped tags are silently skipped.

    Args:
        btp_tags: List of decoded BTP tag names.

    Returns:
        Sorted, deduplicated list of YenGo tag slugs.
    """
    mapping = _load_tag_mapping()
    yengo_tags: set[str] = set()

    for tag_name in btp_tags:
        entry = mapping.get(tag_name)
        if entry and entry.get("yengo_tags"):
            for yt in entry["yengo_tags"]:
                yengo_tags.add(yt)

    return sorted(yengo_tags)


# ============================================================================
# Categories → Collections
# ============================================================================


def map_categories_to_collections(category_letters: str) -> list[str]:
    """Map BTP category letters (A–O) to YenGo collection slugs.

    Args:
        category_letters: String of category letters (e.g., "CF").

    Returns:
        Sorted, deduplicated list of YenGo collection slugs.
    """
    name_to_slugs, letter_to_name = _load_collections_mapping()
    collections: set[str] = set()

    for letter in category_letters:
        name = letter_to_name.get(letter, "")
        if name:
            slugs = name_to_slugs.get(name, [])
            collections.update(slugs)

    return sorted(collections)


# ============================================================================
# Categories → Intent (root comment objective)
# ============================================================================


def derive_intent(category_letters: str, btp_tags: list[str]) -> str:
    """Derive puzzle intent/objective from categories and tags.

    Uses intent_signals.json to map categories to objective domains,
    then refines based on tag presence.

    Args:
        category_letters: BTP category letters.
        btp_tags: Decoded BTP tag names.

    Returns:
        Objective string (e.g., "Kill the group") or empty string.
    """
    signals = _load_intent_signals()
    cat_map = signals.get("category_to_objective_domain", {})
    refinements = signals.get("tag_refinement", {})

    _, letter_to_name = _load_collections_mapping()

    # Find the primary domain from first matching category
    domain = ""
    for letter in category_letters:
        name = letter_to_name.get(letter, "")
        if name:
            domain = cat_map.get(name, "")
            if domain:
                break

    if not domain:
        return ""

    # Check for tag-based refinement within the domain
    tag_set = set(btp_tags)
    rules = refinements.get(domain, {})

    # Check each rule group
    for rule_key, rule_value in rules.items():
        if rule_key == "default":
            continue
        if isinstance(rule_value, list):
            if tag_set & set(rule_value):
                return _domain_action_to_text(domain, rule_key)

    # Fall back to default action
    default_action = rules.get("default", "")
    if default_action:
        return _domain_action_to_text(domain, default_action)

    return _domain_to_text(domain)


def _domain_action_to_text(domain: str, action: str) -> str:
    """Convert domain + action to human-readable objective text."""
    mapping = {
        ("LIFE_AND_DEATH", "KILL"): "Kill the group",
        ("LIFE_AND_DEATH", "escape"): "Help the group escape",
        ("LIFE_AND_DEATH", "live"): "Make the group live",
        ("LIFE_AND_DEATH", "kill"): "Kill the group",
        ("SHAPE", "CONNECT"): "Connect the stones",
        ("SHAPE", "cut"): "Cut the opponent's stones",
        ("SHAPE", "connect"): "Connect the stones",
        ("CAPTURING", "CAPTURE"): "Capture the stones",
        ("TESUJI", "FIND_TESUJI"): "Find the tesuji",
        ("ENDGAME", "FIND_BEST_MOVE"): "Find the best endgame move",
        ("FIGHT", "FIGHT"): "Win the fight",
    }
    return mapping.get((domain, action), _domain_to_text(domain))


def _domain_to_text(domain: str) -> str:
    """Convert domain to generic objective text."""
    return {
        "LIFE_AND_DEATH": "Solve the life and death problem",
        "SHAPE": "Find the best shape move",
        "CAPTURING": "Capture the stones",
        "TESUJI": "Find the tesuji",
        "ENDGAME": "Find the best endgame move",
        "FIGHT": "Win the fight",
    }.get(domain, "")


# ============================================================================
# Combined enrichment
# ============================================================================


def enrich_puzzle(
    rating: int,
    tag_string: str,
    category_letters: str,
) -> dict:
    """Compute all YenGo enrichment properties for a BTP puzzle.

    Args:
        rating: BTP difficulty rating.
        tag_string: Raw BTP tag string (pipe-delimited 2-char codes).
        category_letters: BTP category letters (e.g., "CF").

    Returns:
        Dict with keys: level_slug, yengo_tags, collections, intent.
    """
    btp_tags = decode_btp_tags(tag_string)
    yengo_tags = map_tags_to_yengo(btp_tags)
    level_slug = rating_to_level_slug(rating)
    collections = map_categories_to_collections(category_letters)
    intent = derive_intent(category_letters, btp_tags)

    return {
        "level_slug": level_slug,
        "yengo_tags": yengo_tags,
        "collections": collections,
        "intent": intent,
        "btp_tags_decoded": btp_tags,
    }
