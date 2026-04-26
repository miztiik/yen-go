"""Inner-content normalization for SFT teaching targets.

Pure functions that strip noise *inside* `---CORRECT---` / `---WRONG---`
section bodies before they reach `format_tagged_text`. The delimiters
themselves are already enforced by `tools/core/teaching_schema.py` and
must not be touched here.

Three concerns, all deterministic (no LLM):

1. **Boilerplate stripping** — `Correct! `, `**-> ...**`, `#Correct!`,
   SGF-leakage syntax `(;Correct)`, diagram headers `1 diagram (;Wrong)`,
   redundant `RIGHT`/`WRONG` words. The section delimiter already conveys
   correctness; repeating it in the body is pure noise the model has to
   learn around.

2. **CN→EN translation marker stripping** — patterns like `(completed)`,
   `(question)`, `(adverb marker)` are artefacts of word-by-word machine
   translation from Chinese. We strip the markers but keep the
   surrounding text; the polish stage (P0-3, separate work) will rewrite
   the broken English itself.

3. **Coordinate / ordinal-move stripping** — the system prompt forbids
   coordinates and `Black 1 / White 2` ordinals; ~30% of raw targets
   violate this. Either we strip these from targets or we relax the
   prompt. We strip (see IMPROVEMENT_PLAN.md §1.1 P0-2 Option A).

This module is **idempotent** — running it twice produces the same
result as running it once. All public functions are pure (no I/O, no
state) so they are trivially unit-testable.

See also:
- [IMPROVEMENT_PLAN.md §1.1 P0-1, P0-2](../IMPROVEMENT_PLAN.md)
- `tools/core/teaching_schema.py::format_tagged_text` — final delimiter formatter.
"""

from __future__ import annotations

import re

from tools.core.text_cleaner import (
    contains_vietnamese,
    normalize_fullwidth_punct,
    strip_geometric_markers,
)

# Re-export so callers (audit, polish) have a single import surface.
__all__ = [
    "broken_english_score",
    "contains_vietnamese",
    "has_coordinate_leak",
    "normalize_section_body",
]

# ── 1. Boilerplate prefixes / suffixes ──────────────────────────────────
# Patterns that repeat what the section delimiter already says.
# Stripped at the START of a section body.
_LEADING_BOILERPLATE = re.compile(
    r"^\s*("
    r"(?:correct|wrong|incorrect|right|good|bad)\s*[!:.\-—]+\s*"  # "Correct!", "Wrong:", etc.
    r"|##+\s*(?:correct|wrong|incorrect)\s*[!:.\-—]?\s*"          # "## Correct"
    r"|#\s*(?:correct|wrong|incorrect)\s*[!:.\-—]?\s*"            # "#Correct!"
    r"|\(;\s*(?:correct|wrong|incorrect)\s*\)\s*"                 # "(;Correct)"
    r"|\d+\s+diagram\s*\(\s*;\s*[^)]*\)\s*"                       # "1 diagram (;Wrong)"
    r"|diagram\s+\d+\s*\(\s*;\s*[^)]*\)\s*"                       # "diagram 2 (;Correct)"
    r"|reference\s+\d+\s*[.:\-—]?\s*"                             # "reference 1."
    r"|correct\s+solution\s+\d+\s*[.:\-—]?\s*"                    # "correct solution 1."
    r")+",
    re.IGNORECASE,
)

# Trailing markdown emphasis blocks (e.g. "**-> Black is alive.**")
# We keep the inner text but drop the wrapping/arrow markup.
_MARKDOWN_ARROW_BLOCK = re.compile(
    r"\*\*\s*-+>\s*(.+?)\s*\*\*",
    re.DOTALL,
)

# Trailing markers like "RIGHT" / "WRONG" appended at end of body
_TRAILING_VERDICT = re.compile(
    r"\s*(?:RIGHT|WRONG|CORRECT|INCORRECT)\s*$",
)

# Standalone " #Correct!" / " #Incorrect!" marker tokens anywhere in body
_HASH_VERDICT = re.compile(
    r"\s*#\s*(?:correct|wrong|incorrect)\s*[!:.\-—]?\s*",
    re.IGNORECASE,
)

# ── 2. CN→EN translation artefacts ──────────────────────────────────────
# Markers that machine translators emit when they can't render a CN
# grammatical particle. The surrounding sentence is usually still
# (barely) parseable; we drop only the marker.
_CN_MARKER = re.compile(
    r"\s*\(\s*("
    r"completed|question|adverb marker|particle|measure word|"
    r"perfective|aspect marker|topic marker|sentence-final"
    r")\s*\)\s*",
    re.IGNORECASE,
)

# ── 3. Coordinate / ordinal-move references ─────────────────────────────
# SGF-style 2-letter coordinates as standalone tokens (e.g. "cd", "rs").
# We require they appear as a whole word AND are surrounded by typical
# move-context punctuation/words to avoid false positives on ordinary
# 2-letter words like "to", "in", "of", "at", "by", "is".
# Strategy: only strip when bracketed by `{!...}` (yengo coordinate hint)
# or in obvious patterns like "at cd point", "play cd", etc.
_COORD_HINT_TOKEN = re.compile(r"\{!?[a-s]{2}\}")          # "{!cg}" or "{cg}"
_AT_COORD = re.compile(r"\bat\s+([a-s]{2})\s+(?:point|place)\b", re.IGNORECASE)
_PLAY_COORD = re.compile(r"\bplay(?:s|ed)?\s+(?:at\s+)?([a-s]{2})\b", re.IGNORECASE)

# Western board coordinates (e.g. "D17", "T19", "d19"). Skip the I column (Go convention).
# Case-insensitive: Asian SGF translations sometimes lowercase the column letter.
_WESTERN_COORD = re.compile(r"\b([A-HJ-Ta-hj-t])(\d{1,2})\b")

# Ordinal move references: "Black 1", "White 2", "B 3", "W 4 5".
_ORDINAL_MOVE = re.compile(
    r"\b(?:black|white|[bw])\s+\d+(?:\s*[,;]\s*\d+)*\b",
    re.IGNORECASE,
)

# A/B miai-style placeholder references — "A", "B", "C" capital letters
# referring to marked board points. Only strip when followed by typical
# move-reference language to avoid eating real prose.
_AB_PLACEHOLDER = re.compile(
    r"\b(?:point\s+)?[A-D](?:\s*[,;]\s*[A-D])+\b",
)

# ── 4. Whitespace normalization ─────────────────────────────────────────
_MULTI_WS = re.compile(r"[ \t\u00a0]+")
_MULTI_NL = re.compile(r"\n{3,}")
_LEAD_TRAIL_NL = re.compile(r"^\s+|\s+$")


def normalize_section_body(text: str) -> str:
    """Normalize a single ``---CORRECT---`` or ``---WRONG---`` body.

    Idempotent. Returns empty string if nothing meaningful remains.

    Args:
        text: Raw section body (may contain markdown, SGF-leakage syntax,
            CN→EN markers, coordinate references, etc.).

    Returns:
        Cleaned text. Empty string if the body collapses to noise.
    """
    if not text:
        return ""

    out = text

    # 0. Unicode-script noise: board-marker glyphs (▲ ■ ◯) and fullwidth
    #    punctuation (， → ,). Delegated to tools.core.text_cleaner.
    out = strip_geometric_markers(out)
    out = normalize_fullwidth_punct(out)

    # 1. Boilerplate prefix ("Correct!", "## Correct", "(;Wrong)", etc.)
    out = _LEADING_BOILERPLATE.sub("", out)

    # 2. Markdown arrow blocks: keep inner text, drop wrapper.
    out = _MARKDOWN_ARROW_BLOCK.sub(r"\1", out)

    # 3. Hash verdict tokens anywhere (e.g. "#Correct!").
    out = _HASH_VERDICT.sub(" ", out)

    # 4. CN→EN translation markers.
    out = _CN_MARKER.sub(" ", out)

    # 5. Coordinate-hint tokens like "{!cg}".
    out = _COORD_HINT_TOKEN.sub("", out)

    # 6. "at <coord> point" → "at the vital point" (preserve flow).
    out = _AT_COORD.sub("at the vital point", out)
    out = _PLAY_COORD.sub("play here", out)

    # 7. Standalone Western coordinates "D17", "T19" → "this point".
    out = _WESTERN_COORD.sub("this point", out)

    # 8. Ordinal move references "Black 1", "W 4 5".
    #    Drop them entirely — the surrounding sentence usually still flows.
    out = _ORDINAL_MOVE.sub("", out)

    # 9. "A, B miai" / "point A B" placeholder refs.
    out = _AB_PLACEHOLDER.sub("the marked points", out)

    # 10. Trailing RIGHT/WRONG/CORRECT marker (verdict shouting).
    out = _TRAILING_VERDICT.sub("", out)

    # 11. Whitespace cleanup.
    out = _MULTI_WS.sub(" ", out)
    out = _MULTI_NL.sub("\n\n", out)
    out = _LEAD_TRAIL_NL.sub("", out)

    # Punctuation tidy-up after substitutions.
    out = re.sub(r"\s+([,;.!?])", r"\1", out)
    out = re.sub(r"\(\s*\)", "", out)        # empty parens
    out = re.sub(r",\s*,", ",", out)         # double commas
    out = re.sub(r"\.\s*\.", ".", out)       # double periods
    out = out.strip(" \t\n,;:")

    # If after all that we have less than 4 chars of substance, drop.
    if len(out) < 4:
        return ""

    return out


def has_coordinate_leak(text: str) -> bool:
    """Cheap detector: does this text still contain coordinate refs?

    Used by the audit script (P2-1) to count remaining leaks after
    normalization.

    Args:
        text: Any string (typically an assembled assistant response).

    Returns:
        True if any coordinate / ordinal-move pattern matches.
    """
    if not text:
        return False
    if _COORD_HINT_TOKEN.search(text):
        return True
    if _AT_COORD.search(text):
        return True
    if _PLAY_COORD.search(text):
        return True
    if _WESTERN_COORD.search(text):
        return True
    if _ORDINAL_MOVE.search(text):
        return True
    return False


# ── CN→EN broken-English detector (used by audit + polish stage) ────────
# These are the unmistakable smoking guns of word-by-word CN→EN MT.
_BROKEN_EN_MARKERS = [
    re.compile(r"\(\s*completed\s*\)", re.IGNORECASE),
    re.compile(r"\(\s*question\s*\)", re.IGNORECASE),
    re.compile(r"\(\s*adverb\s+marker\s*\)", re.IGNORECASE),
    re.compile(r"\bobtain\s+more\s+more\b", re.IGNORECASE),
    re.compile(r"\bnot\s+what\b", re.IGNORECASE),
    re.compile(r"\bwon\s*'?\s*t\s+work\b", re.IGNORECASE),
    re.compile(r"\benter\s+work\b", re.IGNORECASE),
    re.compile(r",\s*[a-z]+\s+[a-z]+\s+[a-z]+\s+[a-z]+\s+[a-z]+\s+[a-z]+\s+[a-z]+\s+[a-z]+,", re.IGNORECASE),  # 8+ word run with no punctuation
]


def broken_english_score(text: str) -> int:
    """Count broken-English markers. >=2 = almost certainly MT garbage."""
    if not text:
        return 0
    return sum(1 for p in _BROKEN_EN_MARKERS if p.search(text))
