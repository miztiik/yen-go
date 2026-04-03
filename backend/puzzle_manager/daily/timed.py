"""
Timed challenge generator.

Generates time-limited puzzle sets for competitive play.
Uses compact {p, l, t, c, x} entry format.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from backend.puzzle_manager.daily._helpers import (
    date_seed as _date_seed,
)
from backend.puzzle_manager.daily._helpers import (
    get_level_numeric_categories as _get_level_numeric_categories,
)
from backend.puzzle_manager.daily._helpers import (
    puzzle_hash as _puzzle_hash_impl,
)
from backend.puzzle_manager.daily._helpers import (
    to_puzzle_ref as _to_puzzle_ref,
)
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.models.daily import PuzzleRef, TimedChallenge, TimedSet

logger = logging.getLogger("puzzle_manager.daily.timed")


def generate_timed_challenge(
    date: datetime,
    pool: Sequence[dict],
    config: DailyConfig,
) -> TimedChallenge:
    """Generate timed challenge for the day.

    Creates 3 timed sets:
    - Blitz (3 min): 5 easy puzzles
    - Sprint (10 min): 10 medium puzzles
    - Endurance (30 min): 20 mixed puzzles

    Args:
        date: Date for the challenge
        pool: Available puzzle pool
        config: Daily configuration

    Returns:
        TimedChallenge with multiple timed sets
    """
    seed = _date_seed(date, "timed")

    # Categorize puzzles by difficulty
    easy = [p for p in pool if _is_easy(p)]
    medium = [p for p in pool if _is_medium(p)]
    hard = [p for p in pool if _is_hard(p)]

    sets = []

    # Blitz set (3 min, 5 easy puzzles)
    blitz_target = 5
    blitz_puzzles = _select_puzzles(easy or pool, blitz_target, seed, "blitz")
    if len(blitz_puzzles) < blitz_target:
        logger.warning(
            f"Timed Blitz: {len(blitz_puzzles)} puzzles (target: {blitz_target}) - insufficient pool"
        )
    sets.append(TimedSet(
        set_number=1,  # T044: Sequential set number
        name="Blitz",
        time_limit_seconds=180,
        puzzles=blitz_puzzles,
        difficulty="easy",
    ))

    # Sprint set (10 min, 10 medium puzzles)
    sprint_target = 10
    sprint_puzzles = _select_puzzles(medium or pool, sprint_target, seed, "sprint")
    if len(sprint_puzzles) < sprint_target:
        logger.warning(
            f"Timed Sprint: {len(sprint_puzzles)} puzzles (target: {sprint_target}) - insufficient pool"
        )
    sets.append(TimedSet(
        set_number=2,  # T044: Sequential set number
        name="Sprint",
        time_limit_seconds=600,
        puzzles=sprint_puzzles,
        difficulty="medium",
    ))

    # Endurance set (30 min, 20 mixed puzzles)
    endurance_target = 20
    endurance_pool = (easy[:5] if easy else []) + \
                     (medium[:10] if medium else []) + \
                     (hard[:5] if hard else [])
    if not endurance_pool:
        endurance_pool = list(pool)[:20]
    endurance_puzzles = _select_puzzles(endurance_pool or pool, endurance_target, seed, "endurance")
    if len(endurance_puzzles) < endurance_target:
        logger.warning(
            f"Timed Endurance: {len(endurance_puzzles)} puzzles (target: {endurance_target}) - insufficient pool"
        )
    sets.append(TimedSet(
        set_number=3,  # T044: Sequential set number
        name="Endurance",
        time_limit_seconds=1800,
        puzzles=endurance_puzzles,
        difficulty="mixed",
    ))

    # T041-T042: Compute actual set_count and puzzles_per_set
    actual_set_count = len(sets)
    total_puzzles = sum(len(s.puzzles) for s in sets)
    actual_puzzles_per_set = total_puzzles // actual_set_count if actual_set_count > 0 else 0

    return TimedChallenge(
        sets=sets,
        set_count=actual_set_count,  # T041: Actual set count
        puzzles_per_set=actual_puzzles_per_set,  # T042: Computed average
    )


def _is_easy(puzzle: dict) -> bool:
    """Check if puzzle is easy (IDs < 140: novice, beginner, elementary)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        easy_ids, _, _ = _get_level_numeric_categories()
        return level_id in easy_ids
    return False


def _is_medium(puzzle: dict) -> bool:
    """Check if puzzle is medium (IDs 140-159: intermediate, upper-intermediate)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        _, medium_ids, _ = _get_level_numeric_categories()
        return level_id in medium_ids
    return False


def _is_hard(puzzle: dict) -> bool:
    """Check if puzzle is hard (IDs >= 160: advanced, low-dan, high-dan, expert)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        _, _, hard_ids = _get_level_numeric_categories()
        return level_id in hard_ids
    return False


def _select_puzzles(
    pool: Sequence[dict],
    count: int,
    seed: int,
    salt: str,
) -> list[PuzzleRef]:
    """Select puzzles deterministically from pool."""
    if not pool:
        return []

    ordered = sorted(pool, key=lambda p: _puzzle_hash_impl(p, seed, salt))

    seen: set[str] = set()
    selected: list[PuzzleRef] = []
    for puzzle in ordered:
        ref = _to_puzzle_ref(puzzle)
        if ref.id not in seen:
            seen.add(ref.id)
            selected.append(ref)
        if len(selected) >= count:
            break

    return selected
