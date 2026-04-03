"""
Enumeration types for the puzzle manager.
"""

from enum import Enum, IntEnum


class SkillLevel(IntEnum):
    """Difficulty level for puzzles (1-9 scale)."""

    NOVICE = 1  # 30k+
    BEGINNER = 2  # 25k-20k
    ELEMENTARY = 3  # 20k-15k
    INTERMEDIATE = 4  # 15k-10k
    UPPER_INTERMEDIATE = 5  # 10k-5k
    ADVANCED = 6  # 5k-1d
    LOW_DAN = 7  # 1d-3d
    HIGH_DAN = 8  # 3d-5d
    EXPERT = 9  # 5d+

    @classmethod
    def from_name(cls, name: str) -> "SkillLevel":
        """Get SkillLevel from config key name.

        Args:
            name: Config key like "beginner", "upper-intermediate".

        Returns:
            Corresponding SkillLevel.

        Raises:
            ValueError: If name is not recognized.
        """
        name_map = {
            "novice": cls.NOVICE,
            "beginner": cls.BEGINNER,
            "elementary": cls.ELEMENTARY,
            "intermediate": cls.INTERMEDIATE,
            "upper-intermediate": cls.UPPER_INTERMEDIATE,
            "advanced": cls.ADVANCED,
            "low-dan": cls.LOW_DAN,
            "high-dan": cls.HIGH_DAN,
            "expert": cls.EXPERT,
        }
        normalized = name.lower().replace("_", "-")
        if normalized not in name_map:
            raise ValueError(f"Unknown skill level: {name}")
        return name_map[normalized]

    def to_name(self) -> str:
        """Get config key name for this level.

        Returns:
            Config key like "beginner", "upper-intermediate".
        """
        name_map = {
            self.NOVICE: "novice",
            self.BEGINNER: "beginner",
            self.ELEMENTARY: "elementary",
            self.INTERMEDIATE: "intermediate",
            self.UPPER_INTERMEDIATE: "upper-intermediate",
            self.ADVANCED: "advanced",
            self.LOW_DAN: "low-dan",
            self.HIGH_DAN: "high-dan",
            self.EXPERT: "expert",
        }
        return name_map[self]


class BoardRegion(str, Enum):
    """Region of the board where puzzle is focused."""

    CORNER = "corner"
    SIDE = "side"
    CENTER = "center"
    WHOLE_BOARD = "whole-board"


class Corner(str, Enum):
    """Board corner identifiers."""

    TOP_LEFT = "TL"
    TOP_RIGHT = "TR"
    BOTTOM_LEFT = "BL"
    BOTTOM_RIGHT = "BR"


class RunStatus(str, Enum):
    """Pipeline run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Stage not in requested stages (spec-043)


class StageStatus(str, Enum):
    """Pipeline stage status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
