"""
Pydantic models for OGS API responses.

Defines typed models for Online-Go.com puzzle API endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OGSPuzzleListItem(BaseModel):
    """Minimal puzzle data from list endpoint /api/v1/puzzles/?page=N."""

    id: int
    name: str
    created: str  # ISO 8601 datetime
    modified: str  # ISO 8601 datetime


class OGSPuzzleList(BaseModel):
    """Paginated list response from /api/v1/puzzles/.

    Attributes:
        count: Total puzzle count across all pages
        next: URL for next page (null on last page)
        previous: URL for previous page (null on first page)
        results: List of puzzle summaries
    """

    count: int = Field(..., ge=0, description="Total puzzle count")
    next: str | None = Field(None, description="URL for next page")
    previous: str | None = Field(None, description="URL for previous page")
    results: list[OGSPuzzleListItem] = Field(default_factory=list)


class OGSOwner(BaseModel):
    """Puzzle owner/author information."""

    id: int
    username: str
    country: str = "un"


class OGSCollection(BaseModel):
    """Collection the puzzle belongs to (from OGS API top-level 'collection' field).

    Only captures id and name; other fields (owner, rating, etc.) are ignored.
    """

    id: int
    name: str


class OGSInitialState(BaseModel):
    """Initial board position with stone placements.

    Stones are encoded as concatenated 2-letter coordinate pairs.
    Example: "bchcdccc" = ["bc", "hc", "dc", "cc"] = 4 stones
    """

    white: str = ""
    black: str = ""


class OGSMark(BaseModel):
    """Single board markup annotation from OGS move tree.

    OGS marks have (x, y) coordinates and a ``marks`` dict describing
    the visual type — letter labels, triangles, squares, circles, or crosses.

    Attributes:
        x: Column (0-indexed)
        y: Row (0-indexed)
        marks: Dict of mark type to value. Keys: ``letter`` (str),
               ``triangle`` (bool), ``square`` (bool), ``circle`` (bool),
               ``cross`` (bool).
    """

    x: int = Field(..., ge=0, le=18)
    y: int = Field(..., ge=0, le=18)
    marks: dict[str, str | bool] = Field(default_factory=dict)


class OGSMoveNode(BaseModel):
    """Single node in the move tree (recursive structure).

    Attributes:
        x: Column (0-indexed), -1 for root node
        y: Row (0-indexed), -1 for root node
        branches: Child nodes (variations)
        correct_answer: True if this move leads to correct solution
        wrong_answer: True if this move is explicitly wrong
        text: Optional comment/explanation text
        marks: Board markup annotations (labels, triangles, squares, etc.)
    """

    x: int = Field(..., ge=-1, le=18)
    y: int = Field(..., ge=-1, le=18)
    branches: list[OGSMoveNode] = Field(default_factory=list)
    correct_answer: bool = False
    wrong_answer: bool = False
    text: str | None = None
    marks: list[OGSMark] = Field(default_factory=list)


class OGSPuzzle(BaseModel):
    """Puzzle data nested within detail response."""

    mode: str = "puzzle"
    puzzle_type: str  # life_and_death, tesuji, fuseki, joseki, endgame
    width: int = Field(..., ge=1, le=100)
    height: int = Field(..., ge=1, le=100)
    initial_state: OGSInitialState = Field(default_factory=OGSInitialState)
    initial_player: str = "black"
    move_tree: OGSMoveNode = Field(default_factory=lambda: OGSMoveNode(x=-1, y=-1))
    puzzle_rank: int | None = None
    puzzle_description: str | None = None


class OGSPuzzleDetail(BaseModel):
    """Full puzzle detail from /api/v1/puzzles/{id}/.

    Attributes:
        id: Unique puzzle ID
        name: Puzzle title
        owner: Author information
        created: Creation timestamp
        modified: Last modification timestamp
        puzzle: Nested puzzle content (board, moves)
        has_solution: Whether puzzle has verified solution (API metadata - UNRELIABLE!)
        type: Puzzle type (derived from puzzle.puzzle_type)
    """

    id: int
    name: str
    owner: OGSOwner
    created: str
    modified: str
    puzzle: OGSPuzzle
    has_solution: bool = False  # WARNING: This field is unreliable!
    collection: OGSCollection | None = None

    @property
    def type(self) -> str:
        """Get puzzle type from nested puzzle data."""
        return self.puzzle.puzzle_type

    @property
    def puzzle_description(self) -> str | None:
        """Get puzzle description from nested puzzle data."""
        return self.puzzle.puzzle_description
