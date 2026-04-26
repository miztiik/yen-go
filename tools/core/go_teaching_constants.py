"""Shared Go teaching vocabulary and constants.

Canonical definitions for marker patterns, technique vocabulary, and
explanation keywords used by both the yen-sei SFT pipeline and the
llm-teaching-agent (now tools/oshie/).

These constants were originally defined in multiple places
(yen_sei/config.py, yen_sei/selector.py, oshie). This
module is the single source of truth.
"""

from __future__ import annotations

import re

# ── Marker-only comment patterns ─────────────────────────────────────
# Comments that indicate correctness but have zero teaching value.
# Canonical superset — used consistently across all pipeline stages.
MARKER_ONLY_PATTERNS = frozenset({
    "correct", "correct.", "wrong", "wrong.", "right", "right.",
    "+", "good", "good move", "bad", "bad move",
    "also correct", "also correct.", "incorrect", "incorrect.",
    "yes", "no", "best", "best.",
    "failure", "failure.", "success", "success.",
})

# ── Go technique vocabulary ──────────────────────────────────────────
# Used for technique identification scoring, hint generation, and
# comment quality classification.
GO_TECHNIQUES = frozenset({
    "net", "geta", "ladder", "shicho", "snapback", "ko", "seki",
    "tesuji", "life", "death", "kill", "capture", "connect", "cut",
    "eye", "liberty", "liberties", "atari", "shortage", "semeai",
    "throw-in", "squeeze", "placement", "hane", "descent", "clamp",
    "wedge", "peep", "bamboo", "tiger", "empty triangle", "ponnuki",
    "alive", "dead", "unconditionally", "approach", "invasion",
    "shape", "joseki", "proverb", "sacrifice", "damezumari",
    "nakade", "bent four", "bulky five", "rabbity six",
    "false eye", "double atari", "under the stones",
})

# Pre-compiled regex — sorted by length descending for longest-match-first.
GO_TECHNIQUE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(GO_TECHNIQUES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# ── Explanation keywords ─────────────────────────────────────────────
# Indicate teaching reasoning in comments.
EXPLANATION_KEYWORDS = frozenset({
    "because", "since", "therefore", "if", "then", "after",
    "result", "instead", "however", "otherwise", "this way",
    "notice", "remember", "important", "key", "must", "should",
    "works", "fails", "cannot", "now", "leads to", "forces",
})
