"""
Text cleaning utilities for SGF comments.

Functions for cleaning noisy SGF comment text: strip HTML tags, decode HTML
entities, remove URLs, remove boilerplate labels, and normalize whitespace.

Consciously duplicated from tools/core/text_cleaner.py per CLAUDE.md guidelines:
- The backend pipeline will be rewritten in the future
- Keeping tools/ independent from backend/
- No circular dependencies between tools and backend

Used by:
  - stages/analyze.py: Clean root_comment before preservation
  - core/correctness.py: Clean comment before correctness inference

Dependencies: stdlib only (html, re, unicodedata)
"""

from __future__ import annotations

import html
import re
import unicodedata

# HTML tags pattern
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Whitespace pattern for collapsing
_WHITESPACE_PATTERN = re.compile(r"\s+")

# URLs (http/https) commonly embedded in SGF comments from online sources
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

# Numbered problem/question/exercise labels (noise in training sets)
_NUMBERING_PATTERN = re.compile(
    r"\b(?:question|problem|exercise|puzzle)\s*#?\s*\d+\.?",
    re.IGNORECASE,
)


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities.

    Handles common patterns from online sources:
    - <h1>, <b>, <p>, <br>, etc.
    - HTML entities: &amp;, &gt;, &lt;, &#NNN;, etc.

    Args:
        text: Raw text possibly containing HTML.

    Returns:
        Text with HTML tags removed and entities decoded.

    Example:
        >>> strip_html("<h1>Wrong</h1> &amp; bad")
        ' Wrong  & bad'
    """
    text = _HTML_TAG_PATTERN.sub(" ", text)
    text = html.unescape(text)
    return text


def strip_urls(text: str) -> str:
    """Remove http/https URLs.

    Args:
        text: Text possibly containing URLs.

    Returns:
        Text with URLs replaced by spaces.

    Example:
        >>> strip_urls("See https://example.com for details")
        'See  for details'
    """
    return _URL_PATTERN.sub(" ", text)


def strip_boilerplate(text: str) -> str:
    """Remove common SGF comment boilerplate (numbered labels).

    Removes patterns like:
    - "Question #1"
    - "Problem 42."
    - "Exercise 5"
    - "Puzzle #123"

    Args:
        text: Text possibly containing boilerplate.

    Returns:
        Text with boilerplate labels removed.

    Example:
        >>> strip_boilerplate("Problem #1. Black to play")
        " Black to play"
    """
    return _NUMBERING_PATTERN.sub(" ", text)


def normalize_text(text: str) -> str:
    """NFKC normalize, lowercase, and collapse whitespace.

    Args:
        text: Text to normalize.

    Returns:
        Normalized text (NFKC, lowercase, single spaces, stripped).

    Example:
        >>> normalize_text("  Hello   WORLD  ")
        'hello world'
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def clean_comment_text(text: str | None) -> str:
    """Full cleaning pipeline for noisy SGF comment text.

    Pipeline:
        1. strip_html - remove tags, decode entities
        2. strip_urls - remove http/https URLs
        3. strip_boilerplate - remove numbered labels
        4. normalize_text - NFKC, lowercase, collapse whitespace

    Note: CJK stripping is applied during output serialization
    (via clean_for_correctness / standardize_move_comment) rather than here.
    The backend's ko detection (core/enrichment/ko.py) uses CJK ko terms
    on the parsed SGFGame object before output.

    Args:
        text: Raw SGF comment text (may contain HTML, URLs, etc.)

    Returns:
        Cleaned, normalized text suitable for correctness inference or display.
        Empty string if input is None or empty.

    Example:
        >>> clean_comment_text("<h1>Wrong</h1> Problem #1. http://x.com Bad move!")
        'bad move!'
    """
    if not text:
        return ""

    result = strip_html(text)
    result = strip_urls(result)
    result = strip_boilerplate(result)
    result = normalize_text(result)
    return result


def clean_for_correctness(text: str | None) -> str:
    """Clean comment text for correctness inference.

    Lighter cleaning than clean_comment_text - only strips HTML and normalizes
    whitespace, but preserves case and boilerplate. This ensures prefix matching
    in correctness inference works reliably.

    Also strips CJK characters from the output (ko detection runs on the
    parsed game object before output serialization, so no conflict).

    Args:
        text: Raw SGF comment text.

    Returns:
        HTML-cleaned text with whitespace normalized but case preserved.

    Example:
        >>> clean_for_correctness("<h1>Wrong</h1> move")
        'Wrong move'
    """
    if not text:
        return ""

    result = strip_html(text)
    result = strip_cjk(result)
    result = _WHITESPACE_PATTERN.sub(" ", result)
    return result.strip()


# ---------------------------------------------------------------------------
# CJK stripping
# ---------------------------------------------------------------------------

# CJK Unicode ranges to strip from output comments.
# Ko detection runs on the parsed SGFGame object (before output), so stripping
# CJK from the serialized SGF comments does not affect ko detection.
_CJK_PATTERN = re.compile(
    "["
    "\u4E00-\u9FFF"   # CJK Unified Ideographs
    "\u30A0-\u30FF"   # Katakana
    "\u3040-\u309F"   # Hiragana
    "\uAC00-\uD7AF"   # Hangul Syllables
    "\u3300-\u33FF"   # CJK Compatibility
    "\uFE30-\uFE4F"   # CJK Compatibility Forms
    "\u3000-\u303F"   # CJK Symbols and Punctuation
    "]+"
)


def strip_cjk(text: str) -> str:
    """Remove CJK characters from text.

    Strips CJK Unified Ideographs, Katakana, Hiragana, Hangul Syllables,
    CJK Compatibility, CJK Compatibility Forms, and CJK Symbols/Punctuation.

    Args:
        text: Text possibly containing CJK characters.

    Returns:
        Text with CJK characters removed.

    Examples:
        >>> strip_cjk("Black コウ ko")
        'Black  ko'
        >>> strip_cjk("コウ")
        ''
        >>> strip_cjk("hello world")
        'hello world'
    """
    return _CJK_PATTERN.sub("", text)


def _is_cjk_remnant(text: str) -> bool:
    """Check if text is meaningless remnant after CJK character removal.

    After stripping CJK characters, comments that were predominantly CJK
    leave behind orphaned numbers, single letters, and punctuation that
    made sense only alongside the removed text.

    Example: "흑 9까지 계속 단수로 몰아떨구려해도 백10에서 막혀버립니다."
    becomes " 9    10 ." — meaningless without the Korean context.

    A text is considered a CJK remnant if it contains no word with 2+
    consecutive alphabetic characters.

    Args:
        text: Text that has already been through strip_cjk().

    Returns:
        True if the text is incoherent CJK remnant, False if it contains
        meaningful English/Latin content.

    Examples:
        >>> _is_cjk_remnant("9    10 .")
        True
        >>> _is_cjk_remnant("A  B , C D   .")
        True
        >>> _is_cjk_remnant("White escapes via ladder")
        False
        >>> _is_cjk_remnant("ko fight")
        False
        >>> _is_cjk_remnant("")
        True
    """
    if not text or not text.strip():
        return True

    for word in text.split():
        # Strip edge punctuation to isolate the core token
        core = word.strip(".,;:!?()[]{}\"'-\u2014\u2013/\\")
        if len(core) >= 2 and core.isalpha():
            return False
    return True


# ---------------------------------------------------------------------------
# Move comment standardization
# ---------------------------------------------------------------------------

# Signals that indicate "correct" move (prefix match, case-insensitive)
_CORRECT_SIGNALS = re.compile(
    r"^(?:correct|right|ok|good|\+)[\s!.;:—\-]*",
    re.IGNORECASE,
)

# Signals that indicate "wrong" move (prefix match, case-insensitive)
_WRONG_SIGNALS = re.compile(
    r"^(?:wrong|incorrect|bad|fail(?:ure)?|no)[\s!.;:—\-]*",
    re.IGNORECASE,
)


def is_teaching_comment(comment: str | None) -> bool:
    """Check if a comment contains teaching content beyond correctness markers.

    Strips known correctness signal prefixes (Correct!, Wrong, +, RIGHT, etc.)
    and checks if any meaningful text remains. Used to distinguish genuine
    teaching comments from bare correctness labels.

    Comment level semantics (for hc in YQ):
      - hc:0 = no comments at all
      - hc:1 = correctness markers only (e.g., "Correct!", "Wrong", "+")
      - hc:2 = genuine teaching text (e.g., "Wrong — White escapes via ladder")

    This function returns True only for hc:2 level comments.

    Args:
        comment: The raw move comment (may be None or empty).

    Returns:
        True if the comment has teaching content beyond correctness markers.

    Examples:
        >>> is_teaching_comment("Correct!")
        False
        >>> is_teaching_comment("Wrong")
        False
        >>> is_teaching_comment("+")
        False
        >>> is_teaching_comment("Correct! Good tesuji here")
        True
        >>> is_teaching_comment("Only ko.")
        True
        >>> is_teaching_comment("Wrong — White escapes via ladder")
        True
        >>> is_teaching_comment(None)
        False
    """
    if not comment:
        return False

    # Strip noise first, then CJK (same pipeline as standardize_move_comment)
    cleaned = strip_html(comment)
    cleaned = strip_urls(cleaned)
    cleaned = strip_boilerplate(cleaned)
    cleaned = strip_cjk(cleaned)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    if not cleaned or _is_cjk_remnant(cleaned):
        return False

    # Try to strip correctness signal prefix
    for pattern in (_CORRECT_SIGNALS, _WRONG_SIGNALS):
        match = pattern.match(cleaned)
        if match:
            suffix = cleaned[match.end():].strip()
            # Strip separator characters that follow the label
            suffix = suffix.lstrip(";:—-–").strip()
            return bool(suffix)

    # No correctness signal found — the comment IS teaching content
    # (e.g., "Only ko.", "This creates two eyes")
    return True


def standardize_move_comment(
    comment: str | None,
    is_correct: bool,
) -> str:
    """Standardize a move comment to start with 'Correct' or 'Wrong'.

    Rules:
    1. If comment has a known correctness signal prefix, replace it with
       'Correct' or 'Wrong' and preserve any pedagogical suffix.
    2. If comment has no signal but is_correct is known, prepend the label.
    3. If comment is empty, return just 'Correct' or 'Wrong'.
    4. After CJK stripping, if remaining text is empty, return label only.

    Uses ' — ' (em-dash with spaces) as separator between label and suffix.

    Args:
        comment: The raw move comment (may be None or empty).
        is_correct: Whether the move is correct.

    Returns:
        Standardized comment string.

    Examples:
        >>> standardize_move_comment("RIGHT — good tesuji", True)
        'Correct — good tesuji'
        >>> standardize_move_comment("Incorrect; leads to ko", False)
        'Wrong — leads to ko'
        >>> standardize_move_comment("+", True)
        'Correct'
        >>> standardize_move_comment("", True)
        'Correct'
        >>> standardize_move_comment("Threatens the corner", True)
        'Correct — Threatens the corner'
    """
    label = "Correct" if is_correct else "Wrong"

    if not comment:
        return label

    # Strip HTML, URLs, boilerplate noise, then CJK
    cleaned = strip_html(comment)
    cleaned = strip_urls(cleaned)
    cleaned = strip_boilerplate(cleaned)
    cleaned = strip_cjk(cleaned)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    if not cleaned or _is_cjk_remnant(cleaned):
        return label

    # Try to match and replace a correctness signal prefix
    if is_correct:
        match = _CORRECT_SIGNALS.match(cleaned)
    else:
        match = _WRONG_SIGNALS.match(cleaned)

    if match:
        # Also check the opposite signal in case is_correct disagrees
        suffix = cleaned[match.end():].strip()
        if suffix:
            # Normalize separator to em-dash
            suffix = suffix.lstrip(";:—-–").strip()
            if suffix and not _is_cjk_remnant(suffix):
                return f"{label} \u2014 {suffix}"
        return label

    # Check if the opposite signal is present (comment says one thing,
    # is_correct says another — trust is_correct, replace signal)
    opposite = _WRONG_SIGNALS if is_correct else _CORRECT_SIGNALS
    opp_match = opposite.match(cleaned)
    if opp_match:
        suffix = cleaned[opp_match.end():].strip()
        if suffix:
            suffix = suffix.lstrip(";:—-–").strip()
            if suffix and not _is_cjk_remnant(suffix):
                return f"{label} \u2014 {suffix}"
        return label

    # No signal found — prepend label before existing text
    if _is_cjk_remnant(cleaned):
        return label
    return f"{label} \u2014 {cleaned}"
