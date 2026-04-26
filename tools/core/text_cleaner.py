"""
Text cleaning and normalization utilities.

Two main capabilities:
1. Comment Cleaning: Strip HTML, URLs, CJK, boilerplate from SGF comments
2. Collection Name Processing: Bilingual name extraction, slug generation,
   curator/type inference for collection bootstrap pipelines

Used by tools.puzzle_intent, tools.ogs, tools.go_problems, and other tools.
Pure stdlib dependencies plus unidecode for transliteration.
"""

from __future__ import annotations

import html
import re
import unicodedata

from unidecode import unidecode

# ============================================================================
# SECTION 1: Comment Cleaning
# ============================================================================
# Functions for cleaning noisy SGF comment text (strip HTML, URLs, CJK, etc.)

# CJK Unicode ranges to strip from comments
_CJK_PATTERN = re.compile(
    r"[　-〿"  # CJK Punctuation
    r"぀-ゟ"  # Hiragana
    r"゠-ヿ"  # Katakana
    r"一-鿿"  # CJK Unified Ideographs
    r"가-힯"  # Hangul Syllables
    r"豈-﫿"  # CJK Compatibility Ideographs
    r"𠀀-𪛟"  # CJK Extension B
    r"]+",
)

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# URLs (http/https) commonly embedded in SGF comments from online sources.
# SGF escapes colons as \:, so we also match http\:// and https\://.
_URL_PATTERN = re.compile(r"https?\\?://\S+", re.IGNORECASE)

# Geometric Unicode shapes used as Go board annotations (triangle on stone,
# square marker, filled circle, etc.). Stripped — they are visual diagram
# markup with no meaning in plain text.
#   U+25A0-25FF Geometric Shapes
#   U+2605-2606 black/white star
#   U+25B2/25BC/25C0/25B6 (already in 25A0-25FF block)
_GEOMETRIC_MARKER_PATTERN = re.compile(r"[\u25A0-\u25FF\u2605\u2606]+")

# Fullwidth ASCII punctuation common in Chinese SGF translations
# (e.g. U+FF0C "，" → ASCII ","). NFKC normalization handles these in bulk;
# this pattern is for callers that want detection without normalization.
_FULLWIDTH_PUNCT_PATTERN = re.compile(r"[\uFF01-\uFF5E]")

# Vietnamese-specific characters (Latin Extended Additional precomposed
# diacritics + đĐ + ơưăâ). Used to detect Vietnamese-translated SGF
# comments harvested from mixed-language sources.
#   U+1E00-1EFF Latin Extended Additional (covers ắ ớ ế ể ợ etc.)
#   U+0110/0111 Đ/đ
#   U+01A0/01A1 Ơ/ơ
#   U+01AF/01B0 Ư/ư
_VIETNAMESE_PATTERN = re.compile(
    r"[\u1E00-\u1EFF\u0110\u0111\u01A0\u01A1\u01AF\u01B0]"
)

# Numbered problem/question/exercise labels (noise in training sets)
_NUMBERING_PATTERN = re.compile(
    r"\b(?:question|problem|exercise|puzzle)\s*#?\s*\d+\.?",
    re.IGNORECASE,
)


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    text = _HTML_TAG_PATTERN.sub(" ", text)
    text = html.unescape(text)
    return text


def strip_urls(text: str) -> str:
    """Remove http/https URLs."""
    return _URL_PATTERN.sub(" ", text)


def strip_cjk(text: str) -> str:
    """Remove CJK character blocks, replacing with space to preserve word boundaries."""
    return _CJK_PATTERN.sub(" ", text)


def strip_geometric_markers(text: str) -> str:
    """Remove Unicode geometric shapes used as Go board diagram annotations.

    Strips characters like ▲ △ ■ □ ● ○ ▼ ◆ ★ that appear in CJK SGF
    comments to mark stones/intersections in inline ASCII diagrams.
    Replaced with a single space so adjacent words don't run together.
    """
    return _GEOMETRIC_MARKER_PATTERN.sub(" ", text)


def normalize_fullwidth_punct(text: str) -> str:
    """Convert fullwidth ASCII punctuation (U+FF01-FF5E) to their ASCII equivalents.

    Handles "，" → ",", "。" → "." (already in CJK punct block), "：" → ":",
    etc. Common in Chinese-translated SGF prose. Uses NFKC normalization
    on the matching range only — does not touch other characters.
    """
    if not _FULLWIDTH_PUNCT_PATTERN.search(text):
        return text
    return _FULLWIDTH_PUNCT_PATTERN.sub(
        lambda m: unicodedata.normalize("NFKC", m.group(0)),
        text,
    )


def contains_vietnamese(text: str) -> bool:
    """Detect Vietnamese-script characters in a text snippet.

    Returns True if any precomposed Vietnamese diacritic or Đđ/Ơơ/Ưư
    appears. Used to flag SGF comments harvested from Vietnamese
    translations (which the English-only training corpus must exclude).
    """
    return bool(_VIETNAMESE_PATTERN.search(text))


def strip_vietnamese(text: str) -> str:
    """Remove Vietnamese-specific characters (replacing with space)."""
    return _VIETNAMESE_PATTERN.sub(" ", text)


def strip_boilerplate(text: str) -> str:
    """Remove common SGF comment boilerplate (numbered labels)."""
    return _NUMBERING_PATTERN.sub(" ", text)


def normalize_text(text: str) -> str:
    """NFKC normalize, lowercase, and collapse whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[^\S\n]{2,}")  # 2+ non-newline whitespace


# Machine-translation artifacts: slash-separated word pairs ("must/want", "work/feasible")
_SLASH_PAIR_PATTERN = re.compile(r"\b(\w+)/(\w+)\b")

# Known grammatical annotations from CJK→English machine translation
_MT_ANNOTATION_PATTERN = re.compile(
    r"\((?:possessive|classifier|aspect|particle|auxiliary|passive)\)",
    re.IGNORECASE,
)


def sanitize_for_training(text: str | None) -> str:
    """Sanitization for SFT training data.

    Removes web artifacts, CJK characters, and machine-translation noise
    to produce clean English teaching prose suitable for model fine-tuning.

    Pipeline:
        1. Normalize \\r\\n → \\n, strip lone \\r
        2. strip_html — remove tags, decode entities
        3. strip_urls — remove http/https URLs
        4. strip_cjk — remove CJK/Hangul/Kana character blocks
        5. strip_vietnamese — remove Vietnamese-specific diacritics
        6. strip_geometric_markers — remove Go-board diagram glyphs (▲ ■ ◯)
        7. normalize_fullwidth_punct — fullwidth → ASCII (， → ,)
        8. Strip slash-separated word pairs (keep first word)
        9. Strip machine-translation parenthetical annotations
        10. Collapse excessive whitespace (preserve paragraph breaks)
    """
    if not text:
        return ""
    result = text.replace("\r\n", "\n").replace("\r", "\n")
    result = strip_html(result)
    result = strip_urls(result)
    result = strip_cjk(result)
    result = strip_vietnamese(result)
    result = strip_geometric_markers(result)
    result = normalize_fullwidth_punct(result)
    result = _SLASH_PAIR_PATTERN.sub(r"\1", result)
    result = _MT_ANNOTATION_PATTERN.sub("", result)
    result = _MULTI_SPACE.sub(" ", result)
    result = _MULTI_NEWLINE.sub("\n\n", result)
    return result.strip()


def clean_comment_text(text: str | None) -> str:
    """Full cleaning pipeline for noisy SGF comment text.

    Pipeline:
        1. strip_html - remove tags, decode entities
        2. strip_urls - remove http/https URLs
        3. strip_cjk - remove CJK character blocks
        4. strip_boilerplate - remove numbered labels
        5. normalize_text - NFKC, lowercase, collapse whitespace

    Args:
        text: Raw SGF comment text (may contain HTML, CJK, URLs, etc.)

    Returns:
        Cleaned, normalized text suitable for intent matching or display.
    """
    if not text:
        return ""

    result = strip_html(text)
    result = strip_urls(result)
    result = strip_cjk(result)
    result = strip_boilerplate(result)
    result = normalize_text(result)
    return result


# ============================================================================
# SECTION 2: Collection Name Processing
# ============================================================================
# Functions for cleaning collection names, generating slugs, inferring metadata.

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
