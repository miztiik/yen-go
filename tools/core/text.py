"""
Shared text normalization for collection name processing.

Provides CJK/non-Latin detection, bilingual name extraction,
slug generation, and curator/type inference. Used by both
tools.ogs and tools.go_problems bootstrap pipelines.
"""

from __future__ import annotations

import re

from unidecode import unidecode

# ============================================================================
# Character Detection Constants
# ============================================================================

# Regex for detecting non-Latin characters in names
NON_LATIN_RE = re.compile(
    r"[\u0400-\u04ff"  # Cyrillic
    r"\u0e00-\u0e7f"   # Thai
    r"\u3040-\u309f"   # Hiragana
    r"\u30a0-\u30ff"   # Katakana
    r"\u3400-\u4dbf"   # CJK Extension A
    r"\u4e00-\u9fff"   # CJK Unified
    r"\uac00-\ud7af"   # Korean
    r"]"
)

# CJK/special brackets to normalize
SPECIAL_BRACKETS_RE = re.compile(
    r"[\u3010\u3011\u3016\u3017\u300a\u300b\u300c\u300d"
    r"\u300e\u300f\uff08\uff09\u301c\uff5e]"
)

# Go terms for validating extracted English portions
GO_TERMS = frozenset({
    "tesuji", "life", "death", "ko", "semeai", "capturing", "yose",
    "endgame", "fuseki", "joseki", "tsumego", "atari", "ladder",
    "connect", "cut", "shape", "eye", "miai", "geta", "seki",
    "kyu", "dan", "weiqi", "baduk", "puzzle", "problem", "race",
    "formation", "opening", "fundamental", "sente", "gote", "alive",
    "invasion", "reduction", "tenuki", "hane", "peep", "snapback",
    "kill", "live", "value", "double", "basic", "corner", "move",
})


# ============================================================================
# Strip Patterns
# ============================================================================

# Generic patterns to strip from collection names
STRIP_PATTERNS = [
    re.compile(r"\[.*?\]"),         # [Atorrante], [kisvadim], etc.
    re.compile(r"'s\b"),            # possessives
    re.compile(r"^\d+\.\s*"),       # leading numbering
]

# Known Go authors for curator inference
KNOWN_AUTHORS: dict[str, str] = {
    "cho chikun": "Cho Chikun",
    "hashimoto": "Hashimoto Utaro",
    "maeda": "Maeda Nobuaki",
    "fujisawa": "Fujisawa Shuuko",
    "go seigen": "Go Seigen",
    "lee changho": "Lee Changho",
    "segoe": "Segoe Kensaku",
    "ishida": "Ishida Akira",
    "ishida yoshio": "Ishida Yoshio",
    "ishigure": "Ishigure Ikuro",
    "yamada": "Yamada Kimio",
    "kobayashi": "Kobayashi Satoru",
}

TECHNIQUE_KEYWORDS = [
    "tesuji", "life and death", "life & death", "tsumego",
    "ko", "semeai", "ladder", "endgame", "yose", "nakade",
    "capture", "connect", "cut", "kill", "live",
]

LEVEL_KEYWORDS = [
    "beginner", "elementary", "intermediate", "advanced",
    "dan", "kyu", "introduct", "novice",
]


# ============================================================================
# Bilingual Name Extraction
# ============================================================================

def extract_english_portion(name: str) -> str | None:
    """Extract meaningful English text from a bilingual name.

    For names containing both CJK/Thai/Cyrillic and Latin text,
    extracts the English/Latin portion if it contains Go terminology.

    Args:
        name: Collection name (may be bilingual).

    Returns:
        Extracted English portion, or None if no meaningful portion found.
    """
    if not NON_LATIN_RE.search(name):
        return None  # Already entirely Latin, no extraction needed

    # Remove CJK/special brackets
    cleaned = SPECIAL_BRACKETS_RE.sub(" ", name)

    # Remove parenthesized content that contains CJK characters
    cleaned = re.sub(
        r"\([^)]*[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af][^)]*\)",
        "",
        cleaned,
    )

    # Remove [camp] style prefixes
    cleaned = re.sub(r"^\[camp\]\s*", "", cleaned, flags=re.IGNORECASE)

    # Split on runs of non-Latin characters
    parts = re.split(
        r"[\u0400-\u04ff\u0e00-\u0e7f\u3040-\u309f\u30a0-\u30ff"
        r"\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]+",
        cleaned,
    )

    # Filter for meaningful fragments
    fragments = []
    for part in parts:
        part = part.strip(" -_/|:;,.")
        if len(part) >= 2:
            fragments.append(part)

    if not fragments:
        return None

    result = " ".join(fragments)
    result = re.sub(r"\s+", " ", result).strip()

    # Strip leading isolated numbers (e.g., "1 Basic Shapes" -> "Basic Shapes")
    result = re.sub(r"^\d+\s+", "", result)

    if not result:
        return None

    # Check if result is meaningful (has Go term or 2+ meaningful words)
    words = result.lower().split()
    has_go_term = any(
        w.rstrip("s") in GO_TERMS or w in GO_TERMS for w in words
    )
    meaningful_words = [
        w for w in words
        if len(w) >= 3 and re.match(r"^[a-zA-Z]+$", w)
    ]

    if has_go_term or len(meaningful_words) >= 2:
        return result

    return None


# ============================================================================
# Name Cleanup and Slug Generation
# ============================================================================

def clean_name(
    name: str,
    extra_strip_patterns: list[re.Pattern] | None = None,  # type: ignore[type-arg]
) -> str:
    """Clean up a collection name for display.

    Strips bracket suffixes, CJK brackets, possessives, leading numbering,
    and collapses whitespace. Optionally applies extra strip patterns
    (e.g., website prefixes specific to a source).

    Args:
        name: Raw collection name.
        extra_strip_patterns: Additional regex patterns to apply before
            standard cleanup.

    Returns:
        Cleaned display name.
    """
    result = name

    # Apply source-specific extra patterns first
    if extra_strip_patterns:
        for pattern in extra_strip_patterns:
            result = pattern.sub("", result)

    # Normalize CJK/special brackets to spaces
    result = SPECIAL_BRACKETS_RE.sub(" ", result)

    # Remove parenthesized CJK content
    result = re.sub(
        r"\([^)]*[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af][^)]*\)",
        "",
        result,
    )

    for pattern in STRIP_PATTERNS:
        result = pattern.sub("", result)

    # Collapse whitespace and strip leading/trailing dashes
    result = re.sub(r"\s+", " ", result).strip(" -")
    return result


def generate_slug(name: str) -> str:
    """Convert a display name to a kebab-case slug.

    Conforms to collection schema: ``^[a-z0-9][a-z0-9-]*[a-z0-9]$``,
    max 64 characters.

    Args:
        name: Display name.

    Returns:
        Kebab-case slug.
    """
    # Transliterate non-Latin characters to ASCII, then lowercase
    slug = unidecode(name).lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse consecutive hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    # Truncate to 64 chars, ensuring no trailing hyphen
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    # Ensure minimum length (schema requires at least 2 chars)
    if len(slug) < 2:
        slug = f"unknown-{slug}" if slug else "unknown"
    return slug


# ============================================================================
# Curator and Type Inference
# ============================================================================

def infer_curator(name: str) -> str:
    """Infer curator from collection name.

    Checks known author name patterns.

    Args:
        name: Collection name.

    Returns:
        Curator name or "Community".
    """
    name_lower = name.lower()
    for pattern, curator_name in KNOWN_AUTHORS.items():
        if pattern in name_lower:
            return curator_name
    return "Community"


def infer_type(name: str, curator: str) -> str:
    """Infer collection type from name and curator.

    Args:
        name: Collection name.
        curator: Inferred curator.

    Returns:
        Collection type: "author", "technique", "graded", or "reference".
    """
    # Known author -> "author"
    if curator not in ("Community", "Curated", "System"):
        return "author"

    name_lower = name.lower()

    # Technique keywords
    for kw in TECHNIQUE_KEYWORDS:
        if kw in name_lower:
            return "technique"

    # Level-based keywords
    for kw in LEVEL_KEYWORDS:
        if kw in name_lower:
            return "graded"

    # Default for community collections
    return "reference"
