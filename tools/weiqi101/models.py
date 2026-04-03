"""
Data models for 101weiqi puzzle data.

Represents the `qqdata` JSON object extracted from 101weiqi HTML pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    board_size: int
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

        Handles both standard `prepos` and fallback `psm.prepos` for
        setup stones.
        """
        puzzle_id = data.get("publicid") or data.get("id", 0)
        board_size = data.get("boardsize", 19)
        first_hand = data.get("firsthand", 1)

        # Some sources use blackfirst boolean instead of firsthand int
        if "blackfirst" in data and "firsthand" not in data:
            first_hand = 1 if data["blackfirst"] else 2

        level_name = data.get("levelname", "")
        type_name = data.get("qtypename", "")
        type_id = data.get("qtype", 0)

        # Setup stones: try prepos first, fallback to psm.prepos
        prepos = data.get("prepos", [[], []])
        if (not prepos or prepos == [[], []]) and "psm" in data:
            psm = data["psm"]
            if isinstance(psm, dict) and "prepos" in psm:
                prepos = psm["prepos"]

        black_stones = prepos[0] if len(prepos) > 0 and isinstance(prepos[0], list) else []
        white_stones = prepos[1] if len(prepos) > 1 and isinstance(prepos[1], list) else []

        # Solution tree
        andata = data.get("andata", {})
        solution_nodes: dict[int, SolutionNode] = {}
        for key, value in andata.items():
            try:
                node_id = int(key)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, dict):
                continue
            solution_nodes[node_id] = SolutionNode(
                node_id=node_id,
                coordinate=value.get("pt", ""),
                is_correct=value.get("o", 0) == 1,
                is_failure=value.get("f", 0) == 1,
                comment=str(value.get("c", "")).strip(),
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
