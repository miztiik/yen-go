"""
GoProblems rank to YenGo level mapping.

Maps GoProblems API rank (kyu/dan) and problemLevel to the YenGo 9-level
difficulty system using config/puzzle-levels.json.

Follows OGS levels.py singleton pattern.
Replicates backend/puzzle_manager/core/level_mapper.py logic without
importing from backend.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("go_problems.levels")


DEFAULT_LEVEL = "intermediate"

# Problem level (1-50+) to YenGo level mapping
# Used as fallback when rank is not available
PROBLEM_LEVEL_RANGES: list[tuple[int, int, str]] = [
    (1, 6, "novice"),
    (7, 12, "beginner"),
    (13, 18, "elementary"),
    (19, 24, "intermediate"),
    (25, 30, "upper-intermediate"),
    (31, 36, "advanced"),
    (37, 42, "low-dan"),
    (43, 48, "high-dan"),
    (49, 999, "expert"),
]


def _get_default_levels_path() -> Path:
    """Get the default path to puzzle-levels.json."""
    return Path(__file__).parent.parent.parent / "config" / "puzzle-levels.json"


@lru_cache(maxsize=1)
def _load_levels_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load and cache puzzle-levels.json configuration."""
    path = config_path or _get_default_levels_path()
    if not path.exists():
        logger.warning(f"Levels config not found: {path}")
        return {"levels": []}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in levels config: {e}")
        return {"levels": []}


def _parse_rank_string(rank_str: str) -> tuple[int, str]:
    """Parse a rank string like '15k' or '3d' into (value, unit).

    Args:
        rank_str: Rank string in format like "15k", "3d", "30kyu", "1dan"

    Returns:
        Tuple of (numeric_value, unit) where unit is "kyu" or "dan"

    Raises:
        ValueError: If rank string cannot be parsed.
    """
    rank_str = rank_str.strip().lower()
    match = re.match(r"^(\d+)\s*(k(?:yu)?|d(?:an)?)$", rank_str)
    if not match:
        raise ValueError(f"Cannot parse rank string: '{rank_str}'")

    value = int(match.group(1))
    unit_char = match.group(2)[0]
    unit = "kyu" if unit_char == "k" else "dan"
    return value, unit


def _build_rank_mappings(levels: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
    """Build rank -> level mapping from levels config."""
    mappings: dict[tuple[str, int], str] = {}

    for level in levels:
        slug = level["slug"]
        rank_range = level.get("rankRange", {})
        min_rank = rank_range.get("min", "")
        max_rank = rank_range.get("max", "")

        if not min_rank or not max_rank:
            continue

        try:
            min_val, min_unit = _parse_rank_string(min_rank)
            max_val, max_unit = _parse_rank_string(max_rank)
        except ValueError:
            continue

        if min_unit != max_unit:
            continue

        unit = min_unit
        if unit == "kyu":
            for val in range(min_val, max_val - 1, -1):
                mappings[(unit, val)] = slug
        else:
            for val in range(min_val, max_val + 1):
                mappings[(unit, val)] = slug

    return mappings


class LevelMapper:
    """Maps Go ranks to YenGo difficulty levels using puzzle-levels.json.

    Singleton pattern: use get_level_mapper() for the global instance.
    """

    def __init__(self, config_path: Path | None = None):
        config = _load_levels_config(config_path)
        self.levels: list[dict[str, Any]] = config.get("levels", [])
        self.rank_mappings = _build_rank_mappings(self.levels)

    def rank_to_level(
        self,
        rank_str: str | None = None,
        *,
        value: int | None = None,
        unit: str | None = None,
    ) -> str:
        """Map a Go rank to a YenGo level.

        Args:
            rank_str: Rank string like "15k", "3d"
            value: Numeric rank value (alternative to rank_str)
            unit: Rank unit "kyu" or "dan" (alternative to rank_str)

        Returns:
            YenGo level slug (e.g., "intermediate", "low-dan")
        """
        if rank_str:
            try:
                value, unit = _parse_rank_string(rank_str)
            except ValueError:
                return DEFAULT_LEVEL

        if value is None or unit is None:
            return DEFAULT_LEVEL

        unit = unit.lower()
        if unit not in ("kyu", "dan"):
            return DEFAULT_LEVEL

        key = (unit, value)
        if key in self.rank_mappings:
            return self.rank_mappings[key]

        return self._handle_out_of_range(value, unit)

    def _handle_out_of_range(self, value: int, unit: str) -> str:
        """Handle ranks outside the defined ranges."""
        if unit == "kyu":
            if value > 30:
                return "novice"
            elif value < 1:
                return "advanced"
        else:
            if value < 1:
                return "advanced"
            elif value > 9:
                return "expert"
        return DEFAULT_LEVEL

    def problem_level_to_yengo(self, problem_level: int) -> str:
        """Map a problem level (1-50+ scale) to YenGo level.

        Args:
            problem_level: Numeric difficulty (1=easiest, 50+=hardest)

        Returns:
            YenGo level slug
        """
        for min_val, max_val, level in PROBLEM_LEVEL_RANGES:
            if min_val <= problem_level <= max_val:
                return level
        if problem_level < 1:
            return "novice"
        return "expert"


# Singleton
_level_mapper: LevelMapper | None = None


def get_level_mapper() -> LevelMapper:
    """Get the global LevelMapper instance."""
    global _level_mapper
    if _level_mapper is None:
        _level_mapper = LevelMapper()
    return _level_mapper


def map_rank_to_level(
    rank: dict[str, Any] | None,
    problem_level: int | None = None,
) -> str:
    """Map GoProblems rank to YenGo level.

    Args:
        rank: Rank info dict with 'value' (int) and 'unit' ("kyu" or "dan")
        problem_level: Optional fallback problemLevel (1-50+ scale)

    Returns:
        YenGo level slug
    """
    mapper = get_level_mapper()

    if rank:
        unit = rank.get("unit", "kyu")
        value = rank.get("value")
        if value is not None and unit is not None:
            return mapper.rank_to_level(value=value, unit=unit)

    if problem_level is not None:
        return mapper.problem_level_to_yengo(problem_level)

    return DEFAULT_LEVEL
