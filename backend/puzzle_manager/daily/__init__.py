"""
Daily challenge generation module.

Provides generators for different daily challenge types.
"""

from backend.puzzle_manager.daily.by_tag import generate_tag_challenge
from backend.puzzle_manager.daily.db_writer import (
    SECTION_BY_TAG,
    SECTION_STANDARD,
    SECTION_TIMED_BLITZ,
    SECTION_TIMED_ENDURANCE,
    SECTION_TIMED_SPRINT,
    inject_daily_schedule,
    prune_daily_window,
)
from backend.puzzle_manager.daily.generator import DailyGenerator, GenerationResult
from backend.puzzle_manager.daily.standard import generate_standard_daily
from backend.puzzle_manager.daily.timed import generate_timed_challenge

__all__ = [
    "DailyGenerator",
    "GenerationResult",
    "generate_standard_daily",
    "generate_timed_challenge",
    "generate_tag_challenge",
    "inject_daily_schedule",
    "prune_daily_window",
    "SECTION_STANDARD",
    "SECTION_TIMED_BLITZ",
    "SECTION_TIMED_SPRINT",
    "SECTION_TIMED_ENDURANCE",
    "SECTION_BY_TAG",
]
