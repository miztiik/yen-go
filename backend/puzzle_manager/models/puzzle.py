"""
Puzzle model for the puzzle manager.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.puzzle_manager.core.constants import MAX_BOARD_SIZE, MIN_BOARD_SIZE
from backend.puzzle_manager.core.datetime_utils import utc_now
from backend.puzzle_manager.models.enums import BoardRegion, SkillLevel


class Puzzle(BaseModel):
    """Represents a Go tsumego puzzle with metadata."""

    # Required fields
    id: str = Field(..., description="Unique identifier (16-char hex hash)")
    sgf_path: str = Field(..., description="Relative path to SGF file")
    source_id: str = Field(..., description="Source adapter identifier")
    level: SkillLevel = Field(..., description="Difficulty level (1-9)")
    tags: list[str] = Field(default_factory=list, description="Technique tags")
    board_size: int = Field(..., description="Board size (5–19)")
    created_at: datetime = Field(default_factory=utc_now)

    # Optional fields
    source_link: str | None = Field(None, description="Original URL/reference")
    region: BoardRegion | None = Field(None, description="Active region of board")
    updated_at: datetime | None = Field(None)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate puzzle ID format (16 hex characters)."""
        if len(v) != 16:
            raise ValueError(f"ID must be 16 characters, got {len(v)}")
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("ID must be hex characters only")
        return v.lower()

    @field_validator("board_size")
    @classmethod
    def validate_board_size(cls, v: int) -> int:
        """Validate board size (5–19 inclusive)."""
        if not (MIN_BOARD_SIZE <= v <= MAX_BOARD_SIZE):
            raise ValueError(
                f"Board size must be {MIN_BOARD_SIZE}–{MAX_BOARD_SIZE}, got {v}"
            )
        return v

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: int | str | SkillLevel) -> SkillLevel:
        """Validate and convert level."""
        if isinstance(v, SkillLevel):
            return v
        if isinstance(v, str):
            return SkillLevel.from_name(v)
        if isinstance(v, int):
            if not 1 <= v <= 9:
                raise ValueError(f"Level must be 1-9, got {v}")
            return SkillLevel(v)
        raise ValueError(f"Invalid level type: {type(v)}")

    model_config = {
        "use_enum_values": False,
        "validate_assignment": True,
    }

    def get_level_name(self) -> str:
        """Get human-readable level name."""
        return self.level.to_name()
