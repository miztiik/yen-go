"""
Pydantic models for TsumegoDragon API responses.

These models capture all fields from the Bubble.io API for metadata preservation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TDCategory(BaseModel):
    """TsumegoDragon puzzle category."""

    id: str = Field(alias="_id")
    name: str = Field(alias="Name")
    slug: str = Field(alias="Slug")
    description: str | None = Field(default=None, alias="Description")
    category_option: str | None = Field(default=None, alias="Category Option")
    tsumego_count: int = Field(alias="Tsumego Count")
    sort_index: int = Field(default=0, alias="Sort Index")
    beginner: bool = Field(default=False, alias="Beginner")
    created_by: str | None = Field(default=None, alias="Created By")
    created_date: str | None = Field(default=None, alias="Created Date")
    modified_date: str | None = Field(default=None, alias="Modified Date")
    adventure_image: str | None = Field(default=None, alias="Adventure Image")

    # Level counts
    level_0_count: int = Field(default=0, alias="Level 0 Count")
    level_1_count: int = Field(default=0, alias="Level 1 Count")
    level_2_count: int = Field(default=0, alias="Level 2 Count")
    level_3_count: int = Field(default=0, alias="Level 3 Count")
    level_4_count: int = Field(default=0, alias="Level 4 Count")
    level_5_count: int = Field(default=0, alias="Level 5 Count")
    level_6_count: int = Field(default=0, alias="Level 6 Count")
    level_7_count: int = Field(default=0, alias="Level 7 Count")
    level_8_count: int = Field(default=0, alias="Level 8 Count")

    model_config = {"populate_by_name": True, "extra": "allow"}


class TDPuzzle(BaseModel):
    """TsumegoDragon puzzle with SGF content."""

    id: str = Field(alias="_id")
    # sgf_text is Optional because some puzzles in the DB are incomplete
    # (missing SGF Text field). We validate this at the orchestrator level.
    sgf_text: str | None = Field(default=None, alias="SGF Text")
    category: str | None = Field(default=None, alias="Category")
    level: str | None = Field(default=None, alias="Level")
    level_sort_number: int | None = Field(default=None, alias="Level Sort Number")
    elo: int = Field(default=0, alias="ELO")
    solved: int = Field(default=0, alias="Solved")
    missed: int = Field(default=0, alias="Missed")
    slug: str | None = Field(default=None, alias="Slug")
    sgf_file: str | None = Field(default=None, alias="SGF File")
    created_by: str | None = Field(default=None, alias="Created By")
    created_date: str | None = Field(default=None, alias="Created Date")
    modified_date: str | None = Field(default=None, alias="Modified Date")
    liked_score: int | None = Field(default=None, alias="Liked Score")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_metadata(self) -> dict[str, Any]:
        """Convert to metadata dict preserving all fields."""
        # Use model_dump with by_alias=False to get Python names
        # But we want the original API names for preservation
        return self.model_dump(by_alias=True, exclude_none=False)


class TDCategoryResponse(BaseModel):
    """API response for category list."""

    cursor: int
    results: list[TDCategory]
    count: int
    remaining: int

    model_config = {"extra": "allow"}


class TDPuzzleResponse(BaseModel):
    """API response for puzzle list."""

    cursor: int
    results: list[TDPuzzle]
    count: int
    remaining: int

    model_config = {"extra": "allow"}


# Level mapping from TsumegoDragon to YenGo
LEVEL_MAPPING = {
    0: "novice",
    1: "beginner",
    2: "elementary",
    3: "intermediate",
    4: "upper-intermediate",
    5: "advanced",
    6: "low-dan",
    7: "high-dan",
    8: "expert",
}

# Category slug to YenGo tag mapping
CATEGORY_TAG_MAPPING = {
    "capture": [],  # Too broad — let tagger.py detect technique
    "ladder": ["ladder"],
    "net": ["net"],
    "loopko": ["ko"],
    "snapback": ["snapback"],
    "making-eyes": ["living", "eye-shape"],
    "taking-eyes": ["life-and-death", "eye-shape"],
    "corner-life--death": ["corner", "life-and-death"],
    "throw-in-tactic": ["throw-in"],
    "capture-race": ["capture-race"],
    "liberty-shortage": ["liberty-shortage"],
    "connecting": ["connection"],
    "disconnect": ["cutting"],
    "double-threatatari": ["double-atari"],
    "mutual-life": ["seki"],
    "three-point-eye": ["eye-shape"],
    "four-point-eye": ["eye-shape"],
    "five-point-eye": ["eye-shape"],
    "six-point-eye": ["eye-shape"],
    "nine-space-eye": ["eye-shape", "corner"],
    "connect--die": ["connection", "life-and-death"],
    "bonus-liberty": ["liberty-shortage"],
    "squeeze-tactic": ["liberty-shortage"],
    "vital-wedge": ["vital-point"],
    "bamboo-snapback": ["snapback"],
    "shape": ["shape"],
    "endgame-yose": ["endgame"],
    "opening-basics": [],
    "false-eye": ["eye-shape"],
    "discovered-cut": ["cutting"],
    "corner-pattern": ["corner"],
    "endgame-traps": ["endgame"],
    "eye-vs-no-eye": ["capture-race", "eye-shape"],
    "unsorted": [],
}

# Default categories to download (beginner-friendly)
DEFAULT_CATEGORIES = [
    "capture",
    "ladder",
    "net",
    "snapback",
    "connecting",
    "disconnect",
    "three-point-eye",
    "four-point-eye",
    "making-eyes",
    "taking-eyes",
]
