"""Stable identity hashing for capture-log retrospective enrichment.

Computes a normalized SHA256[:16] from raw SGF text, stripping volatile
properties (puzzle id, comments, hints, pipeline metadata) so the same
board+solution always produces the same hash regardless of pipeline tags.

This complements the runtime ``content_hash`` written by the receiver
(which uses canonical PuzzleData primitives) — the two hashes will not
match exactly, but both serve as cross-book dedup keys.
"""

from __future__ import annotations

import hashlib
import re

# Volatile SGF properties that must be stripped before hashing.
# Keep board content (AB/AW/B/W) + structural punctuation only.
_VOLATILE_PROPS = ("C", "GN", "YL", "YM", "YH", "YQ", "YX", "YT", "YG", "YV", "SO")

_STRIP_RE = re.compile(
    r"(?:" + "|".join(_VOLATILE_PROPS) + r")\[(?:[^\\\]]|\\.)*\]",
)
_WS_RE = re.compile(r"\s+")


def normalized_sgf_hash(sgf_text: str) -> str:
    """Compute SHA256[:16] of SGF text with volatile properties stripped."""
    s = _STRIP_RE.sub("", sgf_text)
    s = _WS_RE.sub("", s)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
