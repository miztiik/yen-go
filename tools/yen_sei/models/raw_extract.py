"""RawExtract: harvest output schema.

Represents one parsed SGF file with all its comments extracted.
This is the intermediate format between raw SGFs and training data.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SolutionNode(BaseModel):
    """A single node in the solution tree with its comment."""

    move: str = Field(description="SGF coordinate (e.g., 'dg')")
    color: str = Field(pattern=r"^[BW]$", description="'B' or 'W'")
    comment: str = Field(default="", description="Raw C[] text from this node")
    is_correct: bool = Field(description="Whether this move is on the correct path")
    children_count: int = Field(default=0, ge=0)


class RawExtract(BaseModel):
    """One parsed SGF with all comments extracted.

    Output of the harvest stage. Input to the refine stage.
    """

    source: str = Field(description="Source identifier: 'ogs', 'goproblems', 'gogameguru'")
    tier: str = Field(default="bronze", description="Curation tier: 'gold', 'silver', or 'bronze'")
    file_path: str = Field(description="SGF filename (e.g., 'gold_goproblems_6840.sgf')")
    board_size: int = Field(ge=5, le=19)
    player_to_move: str = Field(pattern=r"^[BW]$")
    setup_black: list[str] = Field(default_factory=list, description="SGF coords for black stones")
    setup_white: list[str] = Field(default_factory=list, description="SGF coords for white stones")
    root_comment: str = Field(default="", description="C[] at the root node")
    solution_nodes: list[SolutionNode] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    level: str = Field(default="", description="Difficulty level if known")
    collection: str = Field(default="", description="Collection name if known")
    total_comment_chars: int = Field(
        default=0,
        ge=0,
        description="Sum of all comment lengths (root + nodes). Pre-computed for fast filtering.",
    )
