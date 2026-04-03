"""
Level mapping: 101weiqi levelname → YenGo level slug.

Maps Chinese kyu/dan notation (e.g., "13K+", "3D") to YenGo's
9-level system using config/puzzle-levels.json.

Applies calibration offsets from _local_levels_mapping.json to compensate
for inflated Chinese kyu ratings (~10 stones weaker than international).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tools.core.paths import get_project_root

logger = logging.getLogger("101weiqi.levels")

# Rank ranges for each YenGo level (kyu positive, dan negative)
# e.g., 30k = 30, 1d = -1, 9d = -9
_LEVEL_RANGES: list[tuple[str, int, int]] = [
    ("novice", 26, 30),
    ("beginner", 21, 25),
    ("elementary", 16, 20),
    ("intermediate", 11, 15),
    ("upper-intermediate", 6, 10),
    ("advanced", 1, 5),
    ("low-dan", -3, -1),
    ("high-dan", -6, -4),
    ("expert", -9, -7),
]


@lru_cache(maxsize=1)
def _load_calibration() -> tuple[int, int]:
    """Load kyu/dan calibration offsets from _local_levels_mapping.json.

    Returns:
        Tuple of (kyu_offset, dan_offset). Defaults to (0, 0) if file missing.
    """
    config_path = Path(__file__).parent / "_local_levels_mapping.json"
    if not config_path.exists():
        return (0, 0)
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        cal = data.get("calibration", {})
        return (cal.get("kyu_offset", 0), cal.get("dan_offset", 0))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load calibration config: {e}")
        return (0, 0)


@dataclass
class LevelDefinition:
    """A YenGo difficulty level."""

    level_id: int
    slug: str
    name: str


@lru_cache(maxsize=1)
def _load_level_definitions() -> list[LevelDefinition]:
    """Load level definitions from config/puzzle-levels.json."""
    config_path = get_project_root() / "config" / "puzzle-levels.json"
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    levels = []
    for item in data.get("levels", []):
        levels.append(
            LevelDefinition(
                level_id=item["id"],
                slug=item["slug"],
                name=item["name"],
            )
        )
    return levels


def _parse_rank_string(rank_str: str) -> int | None:
    """Parse a rank string to a numeric value.

    Kyu ranks are positive (30k=30, 1k=1).
    Dan ranks are negative (1d=-1, 9d=-9).
    Professional ranks are treated as dan (1p=-7, 9p=-9 capped at expert).

    Args:
        rank_str: e.g., "13K+", "3D", "1P", "5k"

    Returns:
        Numeric rank or None if unparseable.
    """
    if not rank_str:
        return None

    # Strip common suffixes and whitespace
    cleaned = rank_str.strip().upper().rstrip("+")

    # Match patterns like "13K", "3D", "1P"
    m = re.match(r"^(\d+)\s*([KDP])$", cleaned)
    if not m:
        return None

    number = int(m.group(1))
    rank_type = m.group(2)

    if rank_type == "K":
        return number  # Kyu: positive
    elif rank_type == "D":
        return -number  # Dan: negative
    elif rank_type == "P":
        # Professional: map to expert range
        return max(-9, -6 - number)  # 1P→-7, 2P→-8, 3P+→-9

    return None


def map_level(level_name: str) -> str | None:
    """Map a 101weiqi levelname to a YenGo level slug.

    Applies calibration offsets from _local_levels_mapping.json:
    - kyu_offset: added to kyu ranks (e.g., 15K + 10 = 25K → beginner)
    - dan_offset: added to dan ranks (magnitude; e.g., 0 means no change)

    Args:
        level_name: Chinese rank string, e.g., "13K+", "3D"

    Returns:
        Level slug (e.g., "beginner") or None if unmappable.
    """
    rank = _parse_rank_string(level_name)
    if rank is None:
        logger.debug(f"Cannot parse level: '{level_name}'")
        return None

    # Apply calibration offsets
    kyu_offset, dan_offset = _load_calibration()
    if rank > 0:
        # Kyu: higher number = weaker; add offset to correct inflation
        calibrated = min(rank + kyu_offset, 30)
    else:
        # Dan: more negative = stronger; subtract offset from magnitude
        calibrated = rank - dan_offset  # e.g., -3 - 0 = -3 (no change)
        calibrated = max(calibrated, -9)  # clamp to expert ceiling

    for slug, low, high in _LEVEL_RANGES:
        if low <= calibrated <= high:
            if calibrated != rank:
                logger.debug(
                    f"Level '{level_name}' (rank={rank}, calibrated={calibrated}) → '{slug}'"
                )
            else:
                logger.debug(f"Level '{level_name}' (rank={rank}) → '{slug}'")
            return slug

    logger.warning(f"Level '{level_name}' (rank={rank}, calibrated={calibrated}) outside known ranges")
    return None
