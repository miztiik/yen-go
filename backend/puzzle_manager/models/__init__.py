"""
Pydantic models for the puzzle manager.

This module provides data models for puzzles, configuration, and daily challenges.
"""

from backend.puzzle_manager.models.config import (
    AdapterConfig,
    BatchConfig,
    DailyConfig,
    OutputConfig,
    PipelineConfig,
    RetentionConfig,
    SourceConfig,
)
from backend.puzzle_manager.models.daily import (
    DailyChallenge,
    PuzzleRef,
    StandardDaily,
    TagChallenge,
    TimedChallenge,
    TimedSet,
)
from backend.puzzle_manager.models.enums import (
    BoardRegion,
    Corner,
    RunStatus,
    SkillLevel,
)
from backend.puzzle_manager.models.publish_log import (
    PublishLogEntry,
    PublishLogFile,
)
from backend.puzzle_manager.models.puzzle import Puzzle

__all__ = [
    # Enums
    "SkillLevel",
    "BoardRegion",
    "RunStatus",
    "Corner",
    # Puzzle
    "Puzzle",
    # Config
    "BatchConfig",
    "RetentionConfig",
    "DailyConfig",
    "OutputConfig",
    "AdapterConfig",
    "SourceConfig",
    "PipelineConfig",
    # Daily
    "PuzzleRef",
    "StandardDaily",
    "TimedSet",
    "TimedChallenge",
    "TagChallenge",
    "DailyChallenge",
    # Publish Log (core models)
    "PublishLogEntry",
    "PublishLogFile",
]
