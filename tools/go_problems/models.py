"""
Pydantic data models for GoProblems API responses.

Provides typed models for the goproblems.com API v2 responses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GoProblemsRank(BaseModel):
    """Rank information from GoProblems API."""

    value: int | None = None
    unit: str | None = None  # "kyu" or "dan"
    exact: bool = False


class GoProblemsRating(BaseModel):
    """Rating/quality information from GoProblems API."""

    stars: float = 0.0
    votes: int = 0


class GoProblemsCollection(BaseModel):
    """Collection membership reference from GoProblems API."""

    id: int
    name: str


class GoProblemsDetail(BaseModel):
    """Full puzzle detail from /api/v2/problems/{id}.

    Contains the raw SGF content plus metadata used for
    enrichment and filtering.
    """

    id: int
    sgf: str = ""
    genre: str | None = None  # "life and death", "tesuji", etc.
    rank: GoProblemsRank | None = None
    problemLevel: int | None = None  # 1-50+ difficulty scale
    rating: GoProblemsRating | None = None
    isCanon: bool = False
    playerColor: str | None = "black"  # None in some legacy puzzles
    collections: list[GoProblemsCollection] | None = None
    source: str | None = None


class GoProblemsListItem(BaseModel):
    """Minimal puzzle data from list endpoint."""

    id: int


class GoProblemsListResponse(BaseModel):
    """Paginated list response from /api/v2/problems."""

    count: int = 0
    next: str | None = None
    previous: str | None = None
    results: list[GoProblemsListItem] = Field(default_factory=list)
