"""
Standard daily challenge generator.

Generates a standard set of puzzles per day (default: 30) using deterministic
date-based selection. Starts with a core distribution (1 beginner, 2 intermediate,
2 advanced) then top-fills to ``config.puzzles_per_day`` from the full pool.

Quality-weighted selection (D1): Puzzles with higher quality scores are more
likely to be selected via ``selection_weight`` from ``puzzle-quality.json``.
"""

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from random import Random

from backend.puzzle_manager.daily._helpers import (
    date_seed as _date_seed,
)
from backend.puzzle_manager.daily._helpers import (
    get_level_numeric_categories as _get_level_numeric_categories,
)
from backend.puzzle_manager.daily._helpers import (
    to_puzzle_ref as _to_puzzle_ref,
)
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.models.daily import PuzzleRef, StandardDaily

logger = logging.getLogger("puzzle_manager.daily.standard")


# ---------------------------------------------------------------------------
# Quality-weighted selection helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_selection_weights() -> dict[int, float]:
    """Load quality → selection_weight mapping from config/puzzle-quality.json.

    Returns:
        Dict mapping quality level (1-5) to selection weight (float).
        Falls back to hardcoded defaults if config cannot be loaded.
    """
    defaults = {1: 0.1, 2: 0.5, 3: 1.0, 4: 2.0, 5: 3.0}
    try:
        config_path = Path(__file__).resolve().parents[3] / "config" / "puzzle-quality.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        levels = data.get("levels", {})
        weights = {}
        for key, info in levels.items():
            try:
                weights[int(key)] = float(info.get("selection_weight", defaults.get(int(key), 1.0)))
            except (ValueError, TypeError):
                continue
        if weights:
            return weights
    except (OSError, json.JSONDecodeError) as e:
        logger.debug(f"Could not load selection weights from config: {e}")
    return defaults


def _weighted_sample(
    rng: Random,
    pool: Sequence[dict],
    k: int,
    exclude_ids: set[str],
) -> list[dict]:
    """Select up to k unique puzzles from pool using quality-weighted sampling.

    Args:
        rng: Seeded Random instance for deterministic selection.
        pool: Available puzzles (must have 'q' and 'p' fields).
        k: Number of puzzles to select.
        exclude_ids: Set of compact paths already selected (to avoid duplicates).

    Returns:
        List of selected puzzle dicts (length <= k).
    """
    if not pool:
        return []

    selection_weights = _load_selection_weights()
    available = [p for p in pool if p.get("p", "") not in exclude_ids]
    selected: list[dict] = []

    for _ in range(k):
        if not available:
            break
        weights = [selection_weights.get(p.get("q", 1), 0.5) for p in available]
        chosen = rng.choices(available, weights=weights, k=1)[0]
        selected.append(chosen)
        chosen_id = chosen.get("p", "")
        exclude_ids.add(chosen_id)
        available = [p for p in available if p.get("p", "") != chosen_id]

    return selected


def generate_standard_daily(
    date: datetime,
    pool: Sequence[dict],
    config: DailyConfig,
) -> StandardDaily:
    """Generate standard daily challenge with quality-weighted selection.

    Selects puzzles using deterministic date-based seed with weighted sampling:
    higher-quality puzzles (q=4-5) are preferred over basic ones (q=1-2).
    Weights are loaded from ``config/puzzle-quality.json`` ``selection_weight``.

    Distribution: 1 beginner, 2 intermediate, 2 advanced, then top-fill.

    Args:
        date: Date for the challenge
        pool: Available puzzle pool (pre-filtered by quality/content-type)
        config: Daily configuration

    Returns:
        StandardDaily challenge
    """
    # Group puzzles by level category
    beginners = [p for p in pool if _is_beginner(p)]
    intermediate = [p for p in pool if _is_intermediate(p)]
    advanced = [p for p in pool if _is_advanced(p)]

    logger.debug(
        f"Pool sizes: beginners={len(beginners)}, "
        f"intermediate={len(intermediate)}, advanced={len(advanced)}"
    )

    # Generate deterministic seed from date
    seed = _date_seed(date, "standard")
    rng = Random(seed)

    # Track selected puzzle IDs for deduplication
    seen_ids: set[str] = set()
    puzzles: list[PuzzleRef] = []

    # 1 beginner (quality-weighted)
    beginner_picks = _weighted_sample(rng, beginners, 1, seen_ids)
    puzzles.extend(_to_puzzle_ref(p) for p in beginner_picks)

    # 2 intermediate (quality-weighted)
    intermediate_picks = _weighted_sample(rng, intermediate, 2, seen_ids)
    puzzles.extend(_to_puzzle_ref(p) for p in intermediate_picks)

    # 2 advanced (quality-weighted)
    advanced_picks = _weighted_sample(rng, advanced, 2, seen_ids)
    puzzles.extend(_to_puzzle_ref(p) for p in advanced_picks)

    # Top-fill to target count from the full pool (quality-weighted)
    target_count = config.puzzles_per_day
    remaining = target_count - len(puzzles)

    if remaining > 0:
        top_fill = _weighted_sample(rng, list(pool), remaining, seen_ids)
        puzzles.extend(_to_puzzle_ref(p) for p in top_fill)

    if len(pool) < target_count:
        logger.warning(
            f"Standard daily: {len(pool)} puzzles (target: {target_count}) - insufficient pool"
        )

    # Limit to target count
    final_puzzles = puzzles[:target_count]

    # Compute actual distribution from selected puzzles (T032)
    distribution: dict[str, int] = {}
    for p in final_puzzles:
        level = p.level or "unknown"
        distribution[level] = distribution.get(level, 0) + 1

    # Log if we didn't reach target
    if len(final_puzzles) < target_count:
        logger.warning(
            f"Standard daily: {len(final_puzzles)} puzzles (target: {target_count}) - insufficient pool"
        )

    return StandardDaily(
        puzzles=final_puzzles,
        total=len(final_puzzles),  # T031: Set total = len(puzzles)
        distribution=distribution,  # T032: Computed distribution
    )


def _is_beginner(puzzle: dict) -> bool:
    """Check if puzzle is beginner level (IDs 110-130: novice, beginner, elementary)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        beginner_ids, _, _ = _get_level_numeric_categories()
        return level_id in beginner_ids
    return False


def _is_intermediate(puzzle: dict) -> bool:
    """Check if puzzle is intermediate level (IDs 140-150: intermediate, upper-intermediate)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        _, intermediate_ids, _ = _get_level_numeric_categories()
        return level_id in intermediate_ids
    return False


def _is_advanced(puzzle: dict) -> bool:
    """Check if puzzle is advanced level (IDs 160-230: advanced, low-dan, high-dan, expert)."""
    level_id = puzzle.get("l")
    if level_id is not None and level_id != 0:
        _, _, advanced_ids = _get_level_numeric_categories()
        return level_id in advanced_ids
    return False
