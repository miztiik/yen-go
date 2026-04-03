"""
Daily challenge models for the puzzle manager.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.puzzle_manager.core.datetime_utils import utc_now
from backend.puzzle_manager.models.config import DailyConfig


class PuzzleRef(BaseModel):
    """Reference to a puzzle in daily challenges.

    Spec 119: id is excluded from JSON serialization.
    The puzzle ID is extractable from path: path.split('/').pop().replace('.sgf', '')
    """

    id: str = Field(default="", exclude=True, description="Puzzle ID (internal use, excluded from JSON)")
    level: str = Field(..., description="Level name")
    path: str = Field(..., description="SGF file path")


class StandardDaily(BaseModel):
    """Standard daily challenge (30 puzzles)."""

    puzzles: list[PuzzleRef] = Field(default_factory=list, description="Puzzle references")
    total: int = Field(0, description="Total count")
    technique_of_day: str | None = Field(None, description="Featured technique")
    distribution: dict[str, int] = Field(default_factory=dict, description="Count per level")


class TimedSet(BaseModel):
    """A single timed challenge set."""

    set_number: int = Field(1, ge=1, description="Set index (1-based)")
    name: str = Field("", description="Set name (e.g., 'Blitz', 'Sprint')")
    time_limit_seconds: int = Field(180, ge=0, description="Time limit in seconds")
    puzzles: list[PuzzleRef] = Field(default_factory=list, description="Puzzle references")
    difficulty: str = Field("", description="Difficulty level (easy, medium, hard)")


class TimedChallenge(BaseModel):
    """Timed challenge configuration."""

    sets: list[TimedSet] = Field(default_factory=list, description="Challenge sets")
    set_count: int = Field(3, description="Number of sets")
    puzzles_per_set: int = Field(50, description="Puzzles per set")
    suggested_durations: list[int] = Field(
        default_factory=lambda: [180, 300, 600, 900],
        description="Duration options (seconds)",
    )
    scoring: dict[str, int] = Field(
        default_factory=lambda: {
            "novice": 5,
            "beginner": 10,
            "elementary": 15,
            "intermediate": 25,
            "upper-intermediate": 35,
            "advanced": 50,
            "low-dan": 70,
            "high-dan": 90,
            "expert": 120,
        },
        description="Points per level",
    )



class TagChallenge(BaseModel):
    """Challenge for a specific technique tag."""

    puzzles: list[PuzzleRef] = Field(default_factory=list, description="Puzzle references")
    total: int = Field(0, description="Total count")
    tag: str = Field("", description="Tag/technique name")
    tag_display_name: str = Field("", description="Display name for tag")
    tag_description: str = Field("", description="Description for tag")



class DailyChallenge(BaseModel):
    """Complete daily challenge output."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    generated_at: datetime = Field(default_factory=utc_now, description="Generation timestamp")
    version: str = Field("2.2", description="Format version")
    standard: StandardDaily = Field(default_factory=StandardDaily, description="Standard 30-puzzle set")  # type: ignore[arg-type]
    timed: TimedChallenge = Field(default_factory=TimedChallenge, description="Timed challenge sets")  # type: ignore[arg-type]
    by_tag: dict[str, TagChallenge] = Field(default_factory=dict, description="Per-tag challenges")
    weekly_ref: str = Field("", description="Week reference (YYYY-Www)")
    config_used: DailyConfig | None = Field(None, description="Config snapshot")
    technique_of_day: str = Field("", description="Featured technique of the day at root level")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date": "2026-01-28",
                    "generated_at": "2026-01-28T00:00:00Z",
                    "version": "2.1",
                    "weekly_ref": "2026-W05",
                    "technique_of_day": "snapback",
                }
            ]
        }
    }



