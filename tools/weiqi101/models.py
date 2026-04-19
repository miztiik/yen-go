"""
Data models for 101weiqi puzzle data.

Represents the `qqdata` JSON object extracted from 101weiqi HTML pages.

Decode chain (from production JS: ca3b6e99...js):
  QipanAPI.buildTimu101 → test123(qqdata) → test202(encoded, key)

  test123 decodes these fields if ru is 1 or 2:
    content, ok_answers, change_answers, fail_answers, clone_pos, clone_prepos

  XOR key derivation:
    base = atob("MTAx") = "101"
    suffix = ru + 1                    (2 for ru=1, 3 for ru=2)
    key = base + suffix + suffix + suffix  ("101222" or "101333")

  test202(encoded, key):
    1. base64 decode the encoded string
    2. XOR each byte with key (cycling)
    3. JSON.parse the result

  buildInitGameData reads: { ab: qqdata.content[0], aw: qqdata.content[1] }

  The `content` field has the COMPLETE canonical board position.
  The `prepos` field is only a PARTIAL subset (5-8 stones vs 20+).
  The `c` field is a TRANSFORMED position (flipped coords) — not used by the site.
  The `andata` (solution tree) is NOT encoded — plain JSON.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("101weiqi.models")


def _derive_xor_key(ru: int) -> bytes:
    """Derive XOR key from qqdata.ru field.

    Mirrors the site's JS: key = "101" + str(ru+1) * 3
      ru=1 → "101222"
      ru=2 → "101333"
    """
    suffix = str(ru + 1)
    return ("101" + suffix * 3).encode("ascii")


def _xor_decode(encoded: str, key: bytes) -> str | None:
    """Base64-decode then XOR-decrypt with cycling key.

    Mirrors the site's test202() function exactly.
    """
    try:
        raw = base64.b64decode(encoded)
        decoded = bytes(
            b ^ key[i % len(key)]
            for i, b in enumerate(raw)
        )
        return decoded.decode("ascii")
    except Exception as e:
        logger.debug(f"XOR decode failed: {e}")
        return None


def _decode_field(encoded: str, ru: int) -> Any | None:
    """Decode a single XOR-encoded qqdata field to its JSON value.

    Generic decoder: base64 → XOR with ru-dependent key → JSON.parse.
    Returns the parsed JSON value (list, dict, etc.) or None on failure.
    """
    key = _derive_xor_key(ru)
    text = _xor_decode(encoded, key)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.debug(f"Failed to parse decoded field: {e}")
        return None


# Fields that test123 decodes when ru is 1 or 2
_ENCODED_FIELDS = (
    "content", "ok_answers", "change_answers",
    "fail_answers", "clone_pos", "clone_prepos",
)


def decode_qqdata_fields(data: dict[str, Any]) -> None:
    """Decode all XOR-encoded fields in a qqdata dict (in-place).

    Mirrors the site's test123(): decodes content, ok_answers,
    change_answers, fail_answers, clone_pos, clone_prepos when ru is 1 or 2.
    Skips fields that are already decoded (non-string) or absent.
    """
    ru = data.get("ru")
    if ru not in (1, 2):
        return
    for field_name in _ENCODED_FIELDS:
        value = data.get(field_name)
        if isinstance(value, str) and len(value) > 10:
            decoded = _decode_field(value, ru)
            if decoded is not None:
                data[field_name] = decoded


def decode_content_field(
    encoded: str, ru: int
) -> tuple[list[str], list[str]] | None:
    """Decode the qqdata `content` field to get full board position.

    Uses the same algorithm as the site's JS (test123 → test202):
      base64 → XOR with ru-dependent key → JSON.parse

    Args:
        encoded: Base64-encoded content string from qqdata.
        ru: The qqdata.ru value (1=puzzle /q/, 2=chessmanual).

    Returns:
        Tuple of (black_stones, white_stones) or None on failure.
    """
    result = _decode_field(encoded, ru)
    if (
        isinstance(result, list)
        and len(result) >= 2
        and isinstance(result[0], list)
        and isinstance(result[1], list)
    ):
        return result[0], result[1]
    return None


@dataclass
class SolutionNode:
    """A node in the puzzle solution tree."""

    node_id: int
    coordinate: str  # SGF coordinate (e.g., "pd")
    is_correct: bool
    is_failure: bool
    comment: str
    children: list[int] = field(default_factory=list)


@dataclass
class PuzzleData:
    """Parsed 101weiqi puzzle data from qqdata JSON.

    Fields map directly to the qqdata JSON structure with
    Python-friendly names.
    """

    puzzle_id: int
    board_size: int | None
    first_hand: int  # 1=black, 2=white
    level_name: str  # Chinese rank string, e.g., "13K+"
    type_name: str   # Chinese category, e.g., "死活题"
    type_id: int     # Numeric type ID
    black_stones: list[str]  # SGF coordinate list
    white_stones: list[str]  # SGF coordinate list
    solution_nodes: dict[int, SolutionNode]
    vote_score: float
    correct_count: int
    wrong_count: int

    # Optional enrichment fields from qqdata
    bookinfos: list[dict] = field(default_factory=list)
    leiid: int = 0       # Collection/series ID
    taotaiid: int = 0    # Elimination series ID
    hasbook: bool = False  # Whether puzzle is part of a book

    @property
    def player_to_move(self) -> str:
        """Return 'B' or 'W' based on first_hand."""
        return "B" if self.first_hand == 1 else "W"

    @property
    def total_answers(self) -> int:
        return self.correct_count + self.wrong_count

    @classmethod
    def from_qqdata(cls, data: dict[str, Any]) -> PuzzleData:
        """Parse qqdata JSON dict into PuzzleData.

        Stone extraction priority:
          1. content field already decoded (array) — from browser capture
          2. content field encoded (string) — decode with ru-dependent key
          3. prepos / psm.prepos fallback (partial subset)
        """
        # Decode all XOR-encoded fields (content, ok_answers, etc.)
        # Work on a shallow copy to avoid mutating the caller's dict.
        data = dict(data)
        decode_qqdata_fields(data)

        puzzle_id = data.get("publicid") or data.get("id", 0)
        board_size = data.get("boardsize") or data.get("lu")  # lu = 路 (lines)
        first_hand = data.get("firsthand", 1)

        # Some sources use blackfirst boolean instead of firsthand int
        if "blackfirst" in data and "firsthand" not in data:
            first_hand = 1 if data["blackfirst"] else 2

        level_name = data.get("levelname", "")
        type_name = data.get("qtypename", "")
        type_id = data.get("qtype", 0)

        # Setup stones: decode `content` field (complete canonical position)
        # The site's JS (test123) decodes content in-place before board init.
        # In browser capture, content may already be decoded to an array.
        # In direct download / import-jsonl, it's still an encoded string.
        black_stones: list[str] = []
        white_stones: list[str] = []

        content = data.get("content")
        if isinstance(content, list) and len(content) >= 2:
            # Already decoded (browser capture sends decoded arrays)
            black_stones = content[0] if isinstance(content[0], list) else []
            white_stones = content[1] if isinstance(content[1], list) else []
        elif isinstance(content, str) and len(content) > 10:
            # Encoded string — decode with ru-dependent XOR key
            ru = data.get("ru", 1)
            decoded = decode_content_field(content, ru)
            if decoded:
                black_stones, white_stones = decoded
            else:
                logger.warning(
                    f"Failed to decode content field for puzzle {puzzle_id} "
                    f"(ru={ru}, content_len={len(content)})"
                )

        if not black_stones and not white_stones:
            # Fallback: prepos (partial subset, better than nothing)
            prepos = data.get("prepos", [[], []])
            if (not prepos or prepos == [[], []]) and "psm" in data:
                psm = data["psm"]
                if isinstance(psm, dict) and "prepos" in psm:
                    prepos = psm["prepos"]
            black_stones = prepos[0] if len(prepos) > 0 and isinstance(prepos[0], list) else []
            white_stones = prepos[1] if len(prepos) > 1 and isinstance(prepos[1], list) else []

        # Solution tree (andata is NOT encoded — plain JSON)
        andata = data.get("andata", {})
        solution_nodes: dict[int, SolutionNode] = {}
        for key, value in andata.items():
            try:
                node_id = int(key)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, dict):
                continue
            # Comment text: prefer "tip" (教学提示), fall back to "c" only
            # if it's a non-numeric string.  In live data "c" is often 0
            # (a flag), while "tip" carries the actual Chinese comment.
            raw_tip = value.get("tip", "")
            if isinstance(raw_tip, str) and raw_tip.strip():
                comment = raw_tip.strip()
            else:
                raw_c = value.get("c", "")
                if isinstance(raw_c, str) and raw_c.strip():
                    comment = raw_c.strip()
                else:
                    comment = ""
            solution_nodes[node_id] = SolutionNode(
                node_id=node_id,
                coordinate=value.get("pt", ""),
                is_correct=value.get("o", 0) == 1,
                is_failure=value.get("f", 0) == 1,
                comment=comment,
                children=value.get("subs", []),
            )

        # Community stats
        task_result = data.get("taskresult", {})
        if not isinstance(task_result, dict):
            task_result = {}
        correct_count = task_result.get("ok_total", 0)
        wrong_count = task_result.get("fail_total", 0)
        vote_score = data.get("vote", 0.0) or 0.0

        return cls(
            puzzle_id=puzzle_id,
            board_size=board_size,
            first_hand=first_hand,
            level_name=level_name,
            type_name=type_name,
            type_id=type_id,
            black_stones=black_stones,
            white_stones=white_stones,
            solution_nodes=solution_nodes,
            vote_score=vote_score,
            correct_count=correct_count,
            wrong_count=wrong_count,
            bookinfos=data.get("bookinfos", []) or [],
            leiid=data.get("leiid", 0) or 0,
            taotaiid=data.get("taotaiid", 0) or 0,
            hasbook=bool(data.get("hasbook", False)),
        )
