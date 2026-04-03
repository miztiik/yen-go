"""
Level mapping for OGS puzzles.

Maps OGS puzzle_rank to YenGo level slugs using puzzle-levels.json.
Ported from backend/puzzle_manager/adapters/ogs/converter.py.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("ogs.levels")


@dataclass
class LevelDefinition:
    """Level definition from puzzle-levels.json with parsed rank boundaries."""
    id: int
    slug: str
    min_kyu: int  # Negative for dan (e.g., -3 = 3d)
    max_kyu: int  # Negative for dan (e.g., -9 = 9d)


def _parse_go_rank(rank_str: str) -> int:
    """Parse Go rank string to numeric value.

    Kyu ranks are positive (30k = 30, 1k = 1).
    Dan ranks are negative (1d = -1, 9d = -9).

    Args:
        rank_str: Rank like "30k", "6k", "1d", "9d"

    Returns:
        Numeric rank (positive for kyu, negative for dan)

    Examples:
        >>> _parse_go_rank("30k")
        30
        >>> _parse_go_rank("6k")
        6
        >>> _parse_go_rank("1d")
        -1
        >>> _parse_go_rank("9d")
        -9
    """
    rank_str = rank_str.strip().lower()
    if rank_str.endswith("k"):
        return int(rank_str[:-1])
    elif rank_str.endswith("d"):
        return -int(rank_str[:-1])
    else:
        raise ValueError(f"Invalid rank format: {rank_str}")


def _ogs_rank_to_go_rank(ogs_rank: int) -> int:
    """Convert OGS puzzle_rank to Go rank (kyu/dan scale).

    OGS rank scale: lower = stronger (0 = pro, 40+ = beginner).
    Formula: go_rank ≈ 30 - ogs_rank

    Args:
        ogs_rank: OGS puzzle_rank value (0-50+)

    Returns:
        Go rank (positive for kyu, negative for dan)

    Examples:
        >>> _ogs_rank_to_go_rank(24)  # 6 kyu
        6
        >>> _ogs_rank_to_go_rank(30)  # 0 = 1d boundary
        0
        >>> _ogs_rank_to_go_rank(40)  # 30k beginner
        30
        >>> _ogs_rank_to_go_rank(5)   # Strong dan
        -5
    """
    # OGS rank 30 ≈ 1k/1d boundary (go_rank = 0)
    # Lower OGS = stronger = more negative go_rank
    return 30 - ogs_rank


class LevelMapper:
    """Maps OGS puzzle_rank to YenGo level slugs.

    Derives all mapping from puzzle-levels.json alone using rankRange fields.
    No hardcoded mapping in adapter config files.

    Algorithm:
    1. Load levels with rankRange from puzzle-levels.json
    2. Parse rankRange min/max to numeric Go ranks
    3. Convert OGS puzzle_rank to Go rank (formula: 30 - ogs_rank)
    4. Find level whose rankRange contains the Go rank
    """

    def __init__(self, levels_path: Path | None = None):
        """Initialize level mapper.

        Args:
            levels_path: Path to puzzle-levels.json. If None, uses default.

        Raises:
            FileNotFoundError: If config file not found.
            ValueError: If rankRange is missing or invalid.
        """
        if levels_path is None:
            levels_path = self._get_default_levels_path()

        self._levels: list[LevelDefinition] = []
        self._load_levels(levels_path)

    def _get_default_levels_path(self) -> Path:
        """Get default path to puzzle-levels.json."""
        # tools/ogs/levels.py -> config/puzzle-levels.json
        return Path(__file__).parent.parent.parent / "config" / "puzzle-levels.json"

    def _load_levels(self, levels_path: Path) -> None:
        """Load and parse level definitions from puzzle-levels.json."""
        if not levels_path.exists():
            logger.warning(f"Level config not found: {levels_path}")
            return

        with open(levels_path, encoding="utf-8") as f:
            levels_data = json.load(f)

        for level in levels_data.get("levels", []):
            level_id = level.get("id")
            slug = level.get("slug", "")
            rank_range = level.get("rankRange", {})

            if not rank_range or "min" not in rank_range or "max" not in rank_range:
                logger.warning(f"Level {slug} missing rankRange, skipping")
                continue

            try:
                # Parse rank strings to numeric values
                # Note: min_kyu is the weaker boundary (higher number for kyu)
                # max_kyu is the stronger boundary (lower number for kyu, or dan)
                min_kyu = _parse_go_rank(rank_range["min"])
                max_kyu = _parse_go_rank(rank_range["max"])

                self._levels.append(LevelDefinition(
                    id=level_id,
                    slug=slug,
                    min_kyu=min_kyu,
                    max_kyu=max_kyu,
                ))
            except ValueError as e:
                logger.warning(f"Failed to parse rankRange for {slug}: {e}")
                continue

        # Sort by min_kyu descending (weakest/highest kyu first)
        self._levels.sort(key=lambda lvl: lvl.min_kyu, reverse=True)

        logger.debug(f"Loaded {len(self._levels)} level definitions from puzzle-levels.json")

    def map_rank(self, puzzle_rank: int) -> str:
        """Map OGS puzzle_rank to YenGo level slug.

        Args:
            puzzle_rank: OGS rank value (0-50+)

        Returns:
            YenGo level slug (e.g., "beginner", "intermediate")
        """
        go_rank = _ogs_rank_to_go_rank(puzzle_rank)

        for level in self._levels:
            # Check if go_rank falls within this level's range
            # min_kyu is weaker (higher kyu), max_kyu is stronger (lower kyu/dan)
            if level.max_kyu <= go_rank <= level.min_kyu:
                return level.slug

        # Handle gap at go_rank=0 (1k/1d boundary)
        # This falls between advanced (max=1k=1) and low-dan (min=1d=-1)
        # Assign to low-dan since it represents dan-level ability
        if go_rank == 0:
            return "low-dan"

        # Fallback: if above all ranges (very weak), use novice
        # If below all ranges (very strong), use expert
        if go_rank > 0:
            # Positive = kyu, find weakest level
            return self._levels[0].slug if self._levels else "novice"
        else:
            # Negative = dan, find strongest level
            return self._levels[-1].slug if self._levels else "expert"


# Global singleton instance
_mapper: LevelMapper | None = None


def get_level_mapper() -> LevelMapper:
    """Get the global LevelMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = LevelMapper()
    return _mapper


def map_puzzle_rank_to_level(puzzle_rank: int) -> str:
    """Convenience function to map puzzle rank to level slug.

    Args:
        puzzle_rank: OGS puzzle_rank value (0-50)

    Returns:
        YenGo level slug
    """
    return get_level_mapper().map_rank(puzzle_rank)
