"""Tier 1.5: Keyword co-occurrence matcher for Go puzzle objectives.

Detects Go-specific verbs and side indicators via regex, bridging
the gap between exact alias matching (Tier 1) and semantic
similarity (Tier 2). Requires both a verb and a side to fire
(except for side-neutral objectives like seki).

Confidence: 0.7 (lower than exact=1.0, higher than typical
semantic threshold of 0.65).
"""

from __future__ import annotations

import re

from .config_loader import load_objectives
from .models import IntentResult, MatchTier, Objective

# Side detection (full words only, no abbreviations to avoid false positives)
_SIDE_BLACK = re.compile(r"\bblack\b")
_SIDE_WHITE = re.compile(r"\bwhite\b")

# Verb groups mapped to objective types.
# Each pattern matches Go-specific verb forms.
_VERB_GROUPS: dict[str, re.Pattern] = {
    "PLAY": re.compile(r"\b(?:play|move|turn)\b"),
    "LIVE": re.compile(r"\b(?:live|lives?|survive|survives?|alive|make\s+life|two\s+eyes)\b"),
    "KILL": re.compile(r"\b(?:kill|kills?|attack|attacks?|dead|destroy|destroys?)\b"),
    "ESCAPE": re.compile(r"\b(?:escape|escapes?|flee|flees?|break\s+out|connect\s+out)\b"),
    "CAPTURE": re.compile(r"\b(?:capture|captures?|take|takes?)\b"),
    "CONNECT": re.compile(r"\b(?:connect|connects?|join|joins?|link|links?)\b"),
    "CUT": re.compile(r"\b(?:cut|cuts?|separate|separates?|disconnect|disconnects?)\b"),
    "WIN_SEMEAI": re.compile(r"\b(?:semeai|capturing\s+race|liberty\s+race)\b"),
    "WIN_KO": re.compile(r"\bko\b"),
    "SEKI": re.compile(r"\bseki\b|\bmutual\s+life\b"),
    "FIND_TESUJI": re.compile(r"\btesuji\b"),
    "FIND_BEST_MOVE": re.compile(r"\b(?:endgame|yose)\b"),
}

# Side-neutral objectives (match without requiring a side keyword)
_SIDELESS_OBJECTIVES = {"SEKI"}

# Destructive verbs: when side follows the verb, the side is the
# TARGET (opponent) and the actor is the opposite side.
_DESTRUCTIVE_VERBS = {"KILL", "CAPTURE"}

# Mapping from (verb_group, actor_side) -> objective_id
_OBJECTIVE_MAP: dict[tuple[str, str | None], str] = {
    ("PLAY", "BLACK"): "MOVE.BLACK.PLAY",
    ("PLAY", "WHITE"): "MOVE.WHITE.PLAY",
    ("LIVE", "BLACK"): "LIFE_AND_DEATH.BLACK.LIVE",
    ("LIVE", "WHITE"): "LIFE_AND_DEATH.WHITE.LIVE",
    ("KILL", "BLACK"): "LIFE_AND_DEATH.BLACK.KILL",
    ("KILL", "WHITE"): "LIFE_AND_DEATH.WHITE.KILL",
    ("ESCAPE", "BLACK"): "LIFE_AND_DEATH.BLACK.ESCAPE",
    ("ESCAPE", "WHITE"): "LIFE_AND_DEATH.WHITE.ESCAPE",
    ("CAPTURE", "BLACK"): "CAPTURE.BLACK",
    ("CAPTURE", "WHITE"): "CAPTURE.WHITE",
    ("CONNECT", "BLACK"): "SHAPE.BLACK.CONNECT",
    ("CONNECT", "WHITE"): "SHAPE.WHITE.CONNECT",
    ("CUT", "BLACK"): "SHAPE.BLACK.CUT",
    ("CUT", "WHITE"): "SHAPE.WHITE.CUT",
    ("WIN_SEMEAI", "BLACK"): "FIGHT.BLACK.WIN_SEMEAI",
    ("WIN_SEMEAI", "WHITE"): "FIGHT.WHITE.WIN_SEMEAI",
    ("WIN_KO", "BLACK"): "FIGHT.BLACK.WIN_KO",
    ("WIN_KO", "WHITE"): "FIGHT.WHITE.WIN_KO",
    ("SEKI", None): "FIGHT.SEKI",
    ("FIND_TESUJI", "BLACK"): "TESUJI.BLACK",
    ("FIND_TESUJI", "WHITE"): "TESUJI.WHITE",
    ("FIND_BEST_MOVE", "BLACK"): "ENDGAME.BLACK",
    ("FIND_BEST_MOVE", "WHITE"): "ENDGAME.WHITE",
}

# Keyword match confidence (between exact=1.0 and semantic threshold=0.65)
_CONFIDENCE = 0.7


class KeywordMatcher:
    """Keyword co-occurrence matcher for Go puzzle objectives.

    Detects Go verbs + side indicators in cleaned text and maps
    to the most likely objective. No ML dependency required.
    """

    def __init__(self, objectives: tuple[Objective, ...] | None = None):
        if objectives is None:
            objectives = load_objectives()
        self._obj_by_id: dict[str, Objective] = {
            obj.objective_id: obj for obj in objectives
        }

    def match(self, cleaned_text: str, raw_text: str = "") -> IntentResult | None:
        """Try keyword-based match against cleaned text.

        Strategy:
        1. Find Go-specific verbs in text
        2. For sideless verbs (seki), match immediately
        3. Find side indicators (black/white)
        4. For destructive verbs, infer actor from target position
        5. Map (verb, side) to objective

        Args:
            cleaned_text: Pre-cleaned, normalized text.
            raw_text: Original unprocessed text (for result metadata).

        Returns:
            IntentResult with confidence=0.7 if matched, None otherwise.
        """
        if not cleaned_text:
            return None

        # Find all verb matches with positions
        verb_matches: list[tuple[str, int]] = []
        for group, pattern in _VERB_GROUPS.items():
            m = pattern.search(cleaned_text)
            if m:
                verb_matches.append((group, m.start()))

        if not verb_matches:
            return None

        # Sort by position (earliest verb wins)
        verb_matches.sort(key=lambda v: v[1])

        # Handle sideless objectives first (seki, mutual life)
        for verb_group, _ in verb_matches:
            if verb_group in _SIDELESS_OBJECTIVES:
                key = (verb_group, None)
                obj_id = _OBJECTIVE_MAP.get(key)
                if obj_id:
                    return self._make_result(obj_id, cleaned_text, raw_text)

        # Detect sides
        black_m = _SIDE_BLACK.search(cleaned_text)
        white_m = _SIDE_WHITE.search(cleaned_text)

        if not black_m and not white_m:
            return None

        # Try each verb in order
        for verb_group, verb_pos in verb_matches:
            if verb_group in _SIDELESS_OBJECTIVES:
                continue

            side = self._resolve_actor(
                verb_group, verb_pos, black_m, white_m
            )
            if side is None:
                continue

            obj_id = _OBJECTIVE_MAP.get((verb_group, side))
            if obj_id:
                return self._make_result(obj_id, cleaned_text, raw_text)

        return None

    def _resolve_actor(
        self,
        verb_group: str,
        verb_pos: int,
        black_m: re.Match | None,
        white_m: re.Match | None,
    ) -> str | None:
        """Determine actor side based on verb-side positions.

        For destructive verbs (kill, capture), if the side appears
        AFTER the verb, it's the target: the actor is the opposite.
        """
        candidates: list[tuple[str, int]] = []
        if black_m:
            candidates.append(("BLACK", black_m.start()))
        if white_m:
            candidates.append(("WHITE", white_m.start()))

        if not candidates:
            return None

        # Pick the side nearest to the verb
        candidates.sort(key=lambda c: abs(c[1] - verb_pos))
        nearest_side, side_pos = candidates[0]

        # For destructive verbs, invert if side follows verb
        if verb_group in _DESTRUCTIVE_VERBS and side_pos > verb_pos:
            return "WHITE" if nearest_side == "BLACK" else "BLACK"

        return nearest_side

    def _make_result(
        self, obj_id: str, cleaned_text: str, raw_text: str
    ) -> IntentResult | None:
        """Build IntentResult for a keyword match."""
        obj = self._obj_by_id.get(obj_id)
        if obj is None:
            return None
        return IntentResult(
            objective_id=obj_id,
            objective=obj,
            matched_alias=None,
            confidence=_CONFIDENCE,
            match_tier=MatchTier.KEYWORD,
            cleaned_text=cleaned_text,
            raw_text=raw_text,
        )
