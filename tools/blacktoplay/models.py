"""
Data models for BlackToPlay (BTP) puzzle data.

Defines typed dataclasses for BTP API responses and intermediate
representations used during puzzle processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BTPCorrectMove:
    """A correct move parsed from a BTP node's correct_moves field.

    Attributes:
        coord: 2-char BTP coordinate (e.g. "cd").
        response: 2-char auto-response coordinate, or "-" if none.
        child_node_id: String ID of the child node this move leads to.
        is_terminal: True if marked 'T' (puzzle complete after this).
    """

    coord: str
    response: str
    child_node_id: str
    is_terminal: bool


@dataclass
class BTPWrongMove:
    """A wrong move derived from the wrong_moves encoding.

    Attributes:
        coord: 2-char BTP coordinate string.
    """

    coord: str


@dataclass
class BTPNode:
    """A single node in the BTP solution tree.

    Parsed from the semicolon-delimited node format:
    ``id;parent;ko;correct_moves;wrong_moves;standard_response;move_categories``

    Attributes:
        node_id: Unique node identifier (0 = root).
        parent_id: Parent node ID (-1 for root).
        ko_point: Ko point coordinate or empty string.
        correct_moves: List of correct move definitions.
        wrong_moves: List of wrong moves (explicit incorrect responses).
        standard_response: Default response move if not in correct/wrong list.
        move_categories: Category annotations for moves.
        raw: Original raw string for debugging.
    """

    node_id: str = ""
    parent_id: str = ""
    ko_point: str = ""
    correct_moves: list[BTPCorrectMove] = field(default_factory=list)
    wrong_moves: list[BTPWrongMove] = field(default_factory=list)
    standard_response: str = ""
    move_categories: str = ""
    raw: str = ""


@dataclass
class BTPPuzzle:
    """Complete BTP puzzle data as returned by load_data.php.

    Attributes:
        puzzle_id: Unique BTP puzzle ID.
        puzzle_type: 0=Classic, 1=AI, 2=Endgame.
        board_size: Full board size from API (e.g., 19).
        viewport_size: Visible viewport size for hash decoding (e.g., 7 or 9).
        position_hash: Base-59 encoded board position hash.
        to_play: "B" or "W" — who makes the first correct move.
        rating: BTP difficulty rating (0–3000).
        nodes: Raw node strings from the API.
        tags: Pipe-delimited tag string (2-char encoded tags).
        categories: Category letter(s) (A–O).
        title: Puzzle title (if any).
        author: Puzzle author (if any).
        comment: Puzzle comment (if any).
        raw_data: Original API response dict for debugging.
    """

    puzzle_id: str = ""
    puzzle_type: int = 0
    board_size: int = 19
    viewport_size: int = 9
    position_hash: str = ""
    to_play: str = "B"
    rating: int = 0
    nodes: list[str] = field(default_factory=list)
    tags: str = ""
    categories: str = ""
    title: str = ""
    author: str = ""
    comment: str = ""
    raw_data: dict = field(default_factory=dict)


@dataclass
class BTPListItem:
    """Minimal puzzle data from load_list.php.

    Attributes:
        puzzle_id: BTP puzzle ID (alphanumeric string).
        puzzle_type: 0=Classic, 1=AI, 2=Endgame.
        rating: BTP difficulty rating.
    """

    puzzle_id: str
    puzzle_type: int
    rating: int = 0
