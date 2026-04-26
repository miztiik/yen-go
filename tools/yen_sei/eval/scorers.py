"""Layer A (structural) and Layer B (grounded) scorers. Pure, deterministic, free."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from tools.core.go_teaching_constants import GO_TECHNIQUE_PATTERN
from tools.core.teaching_schema import parse_tagged_text

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
# Coords like "ab", "cg" embedded in prose. SGF coords are 2 lowercase a-s letters.
_SGF_COORD_RE = re.compile(r"\b[a-s]{2}\b")


@dataclass
class StructuralScore:
    parsed_ok: bool
    has_correct: bool
    has_wrong: bool
    n_hints: int
    n_chars_correct: int
    n_chars_wrong: int


@dataclass
class GroundedScore:
    mentions_correct_move: bool      # output references the actual correct SGF coord
    mentions_any_tag_technique: bool # output mentions ≥1 technique that's in puzzle tags
    no_off_board_coords: bool        # all SGF-coord tokens are inside puzzle's setup or correct path
    looks_english: bool              # ascii letter ratio sanity
    techniques_matched: list[str]
    correct_move_coord: str          # echoed for debugging


def _score_structural_tagged(generated: str) -> StructuralScore:
    """Score tagged text format (---CORRECT---/---WRONG---/---HINT---)."""
    try:
        correct, wrongs, hints = parse_tagged_text(generated)
    except ValueError:
        return StructuralScore(False, False, False, 0, 0, 0)

    wc_text = " ".join(wrongs)
    return StructuralScore(
        parsed_ok=True,
        has_correct=bool(correct.strip()),
        has_wrong=bool(wc_text.strip()),
        n_hints=len(hints),
        n_chars_correct=len(correct),
        n_chars_wrong=len(wc_text),
    )


def _score_structural_json(generated: str) -> StructuralScore | None:
    """Try to score as JSON format. Returns None if not JSON."""
    blob = _JSON_BLOCK_RE.search(generated or "")
    if not blob:
        return None
    try:
        obj = json.loads(blob.group(0))
    except json.JSONDecodeError:
        return None

    tc = obj.get("teaching_comments") or {}
    cc = (tc.get("correct_comment") or "").strip() if isinstance(tc, dict) else ""
    wc = tc.get("wrong_comments") if isinstance(tc, dict) else None
    if isinstance(wc, dict):
        wc_text = " ".join(str(v) for v in wc.values())
    elif isinstance(wc, list):
        wc_text = " ".join(str(v) for v in wc)
    else:
        wc_text = ""
    hints = obj.get("hints") or []
    return StructuralScore(
        parsed_ok=True,
        has_correct=bool(cc),
        has_wrong=bool(wc_text.strip()),
        n_hints=len(hints) if isinstance(hints, list) else 0,
        n_chars_correct=len(cc),
        n_chars_wrong=len(wc_text),
    )


def score_structural(generated: str) -> StructuralScore:
    """Layer A: did the model emit a parseable response with the right shape?

    Supports both JSON (backward compat) and tagged text (v3+) formats.
    Tries JSON first; falls back to tagged text.
    """
    # Try JSON first (backward compat with pre-v3 models)
    json_result = _score_structural_json(generated)
    if json_result is not None:
        return json_result

    # Try tagged text (v3+ format)
    return _score_structural_tagged(generated)


def _flatten_text(parsed_obj: dict) -> str:
    """Concatenate every string in the assistant JSON for prose-level checks."""
    out: list[str] = []

    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(parsed_obj)
    return " ".join(out)


def score_grounded(
    generated: str,
    correct_move_coord: str,
    puzzle_tags: list[str],
    setup_coords: list[str],
) -> GroundedScore:
    """Layer B: position-anchored objective checks against ground-truth metadata.

    Args:
        generated: model output (string; we extract any embedded JSON).
        correct_move_coord: SGF coord of the correct first move (e.g., "cg"). May be empty.
        puzzle_tags: technique tags from the puzzle metadata (e.g., ["ladder", "snapback"]).
        setup_coords: SGF coords of stones already on the board, used to detect
            mentions of phantom stones not in the puzzle.
    """
    blob = _JSON_BLOCK_RE.search(generated or "")
    parsed: dict = {}
    if blob:
        try:
            parsed = json.loads(blob.group(0))
        except json.JSONDecodeError:
            parsed = {}
    text = _flatten_text(parsed) if parsed else (generated or "")
    text_lower = text.lower()

    mentions_correct = bool(correct_move_coord) and (correct_move_coord.lower() in text_lower)

    # Tag-based technique match. Tags arrive as slugs ("life-and-death") and the
    # GO_TECHNIQUE_PATTERN matches words ("life", "death", "ladder", etc.).
    techniques_matched: list[str] = []
    tag_tokens: set[str] = set()
    for t in puzzle_tags:
        for piece in re.split(r"[-_,\s]+", t.lower()):
            if piece:
                tag_tokens.add(piece)
    for m in GO_TECHNIQUE_PATTERN.finditer(text_lower):
        word = m.group(1).lower()
        if word in tag_tokens and word not in techniques_matched:
            techniques_matched.append(word)
    mentions_tag_tech = bool(techniques_matched) or not tag_tokens  # vacuous if no tags

    # Off-board check: every 2-letter coord token in the prose should either be
    # the correct move or one of the existing setup stones. Allow a small false-positive
    # margin (English words like "ab", "do" can match) by only flagging if the
    # ratio of unknown coords is high.
    coord_set = {c.lower() for c in setup_coords if isinstance(c, str)}
    if correct_move_coord:
        coord_set.add(correct_move_coord.lower())
    found_coords = _SGF_COORD_RE.findall(text_lower)
    unknown = [c for c in found_coords if c not in coord_set]
    no_off_board = (len(unknown) <= max(1, len(found_coords) // 3))

    # English sanity: at least 60% letters when there's prose
    letters = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    looks_english = (letters / max(len(text), 1)) >= 0.6 if text else False

    return GroundedScore(
        mentions_correct_move=mentions_correct,
        mentions_any_tag_technique=mentions_tag_tech,
        no_off_board_coords=no_off_board,
        looks_english=looks_english,
        techniques_matched=techniques_matched,
        correct_move_coord=correct_move_coord,
    )


def to_dict(obj) -> dict:
    return asdict(obj)
