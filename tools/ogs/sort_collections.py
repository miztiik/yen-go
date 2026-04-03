"""
OGS Collections Sorter

Reads an OGS collections JSONL file (produced by explore_collections.py),
computes a composite priority score for each collection, and outputs
a re-sorted JSONL with additional computed fields.

Added fields per collection:
    sort_rank:       int   (1 = highest priority)
    priority_score:  float (0.0-1.0, rounded to 6 decimal places)
    quality_tier:    str   ("premier" | "curated" | "community" | "unvetted")
    bayesian_rating: float (confidence-adjusted rating, rounded to 4 decimals)
    solve_rate:      float | null (solved/attempted, or null if no attempts)

Sorting rationale informed by professional Go player guidance:
    - Cho Chikun (9p): quality over quantity; well-vetted classical collections
      are superior to random user problems.
    - Lee Changho (9p): community engagement is a reliable quality signal;
      professional-authored collections have better pedagogical structure.

Usage:
    python -m tools.ogs.sort_collections --input external-sources/ogs/20260211-203516-collections.jsonl
    python -m tools.ogs.sort_collections -i <file> -o <output-file>
    python -m tools.ogs.sort_collections -i <file> -v
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.core.paths import rel_path
from tools.ogs.config import get_project_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Scoring Configuration
# ============================================================================

# Component weights
WEIGHT_RATING = 0.30        # Bayesian-adjusted rating quality
WEIGHT_ENGAGEMENT = 0.35    # Views + solve quality
WEIGHT_CONTENT = 0.20       # Puzzle count (log-scaled)

# Engagement sub-weights
ENGAGEMENT_VIEW_WEIGHT = 0.6
ENGAGEMENT_SOLVE_WEIGHT = 0.4

# Size multiplier thresholds: (min_puzzle_count, multiplier)
SIZE_THRESHOLDS: list[tuple[int, float]] = [
    (3, 0.3),     # < 3 puzzles: heavy penalty
    (5, 0.5),     # < 5 puzzles: moderate penalty
    (10, 0.8),    # < 10 puzzles: light penalty
]
# >= 10 puzzles: no penalty (1.0)

# Quality tier percentile boundaries (cumulative fraction, tier name)
TIER_THRESHOLDS: list[tuple[float, str]] = [
    (0.10, "premier"),      # Top 10%
    (0.30, "curated"),      # Top 10-30%
    (0.60, "community"),    # Top 30-60%
    (1.00, "unvetted"),     # Bottom 40%
]


# ============================================================================
# Data Model
# ============================================================================

@dataclass
class ScoredCollection:
    """A collection with computed priority fields."""
    record: dict[str, Any]
    priority_score: float
    bayesian_rating: float
    solve_rate: float | None
    sort_rank: int = 0
    quality_tier: str = "unvetted"


# ============================================================================
# JSONL I/O
# ============================================================================

def read_collections(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read JSONL file, returning (metadata_dict, list_of_collection_dicts).

    Line 1 is the metadata record (type == "metadata").
    Lines 2+ are collection records (type == "collection").

    Args:
        input_path: Path to the input JSONL file.

    Returns:
        Tuple of (metadata dict, list of collection dicts).

    Raises:
        FileNotFoundError: If input file does not exist.
        ValueError: If first line is not a metadata record.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Input file is empty: {input_path}")

    metadata = json.loads(lines[0])
    if metadata.get("type") != "metadata":
        raise ValueError(
            f"First line must be a metadata record (type=metadata), "
            f"got type={metadata.get('type')!r}"
        )

    collections = []
    skipped = 0
    for i, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            logger.warning(f"Skipping malformed JSON at line {i}: {line[:80]!r}")
            skipped += 1
            continue
        if record.get("type") == "collection":
            collections.append(record)

    if skipped:
        logger.warning(f"Skipped {skipped} malformed line(s)")

    logger.info(f"Read {len(collections)} collections from {rel_path(input_path)}")
    return metadata, collections


def write_sorted_collections(
    output_path: Path,
    metadata: dict[str, Any],
    scored: list[ScoredCollection],
) -> None:
    """Write sorted collections to JSONL with enriched metadata.

    Line 1: Updated metadata with sorting provenance.
    Lines 2+: Collection records sorted by priority_score descending,
              each enriched with sort_rank, priority_score, quality_tier,
              bayesian_rating, and solve_rate.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute tier distribution
    tier_counts: dict[str, int] = {}
    for s in scored:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1

    # Enrich metadata with sorting provenance
    metadata_out = dict(metadata)
    metadata_out["sorted_at"] = datetime.now(UTC).isoformat()
    metadata_out["sorted_by"] = "priority_score"
    metadata_out["total_collections"] = len(scored)
    metadata_out["scoring_weights"] = {
        "rating": WEIGHT_RATING,
        "engagement": WEIGHT_ENGAGEMENT,
        "content": WEIGHT_CONTENT,
    }
    metadata_out["tier_distribution"] = tier_counts

    with open(output_path, "w", encoding="utf-8") as f:
        # Write metadata line
        f.write(json.dumps(metadata_out, ensure_ascii=False))
        f.write("\n")

        # Write sorted collections with added fields
        for s in scored:
            record = dict(s.record)
            record["sort_rank"] = s.sort_rank
            record["priority_score"] = s.priority_score
            record["quality_tier"] = s.quality_tier
            record["bayesian_rating"] = s.bayesian_rating
            record["solve_rate"] = s.solve_rate
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")

    logger.info(f"Wrote {len(scored)} sorted collections to {rel_path(output_path)}")


# ============================================================================
# Scoring Engine
# ============================================================================

def compute_global_stats(collections: list[dict[str, Any]]) -> dict[str, float]:
    """Compute global statistics needed for normalization.

    Returns dict with keys:
        median_rating_count: Prior strength (C) for Bayesian formula
        weighted_mean_rating: Global mean (m) for Bayesian formula
        max_view_count: For log-scale normalization
        max_puzzle_count: For log-scale normalization
    """
    rating_counts = [c["stats"]["rating_count"] for c in collections]
    max_view = max((c["stats"]["view_count"] for c in collections), default=1)
    max_puzzles = max((c["stats"]["puzzle_count"] for c in collections), default=1)

    # Median rating count as Bayesian prior strength
    median_rc = statistics.median(rating_counts) if rating_counts else 1.0

    # Weighted mean rating (only collections with ratings)
    weighted_sum = 0.0
    weight_total = 0
    for c in collections:
        rc = c["stats"]["rating_count"]
        if rc > 0:
            weighted_sum += c["stats"]["rating"] * rc
            weight_total += rc
    weighted_mean = weighted_sum / weight_total if weight_total > 0 else 3.0

    stats = {
        "median_rating_count": float(median_rc),
        "weighted_mean_rating": weighted_mean,
        "max_view_count": float(max(max_view, 1)),
        "max_puzzle_count": float(max(max_puzzles, 1)),
    }

    logger.info(
        f"Global stats: median_rating_count={stats['median_rating_count']:.1f}, "
        f"weighted_mean_rating={stats['weighted_mean_rating']:.4f}, "
        f"max_views={stats['max_view_count']:.0f}, "
        f"max_puzzles={stats['max_puzzle_count']:.0f}"
    )
    return stats


def compute_bayesian_rating(
    rating: float,
    rating_count: int,
    global_mean: float,
    prior_strength: float,
) -> float:
    """Compute Bayesian average rating.

    Formula: (rating * rating_count + m * C) / (rating_count + C)

    Pulls collections with few ratings toward the global mean,
    preventing a single 5-star rating from dominating.
    """
    return (rating * rating_count + global_mean * prior_strength) / (
        rating_count + prior_strength
    )


def compute_size_multiplier(puzzle_count: int) -> float:
    """Return penalty multiplier for small collections.

    puzzle_count < 3:  0.3
    puzzle_count < 5:  0.5
    puzzle_count < 10: 0.8
    otherwise:         1.0
    """
    for threshold, multiplier in SIZE_THRESHOLDS:
        if puzzle_count < threshold:
            return multiplier
    return 1.0


def score_collection(
    record: dict[str, Any],
    global_stats: dict[str, float],
) -> ScoredCollection:
    """Compute priority score for a single collection.

    Components:
        1. bayesian_rating_norm (0-1): Bayesian-adjusted rating, linearly normalized
        2. engagement_norm (0-1): weighted view_score + solve_rate
        3. content_norm (0-1): log2(puzzle_count) / log2(max_puzzle_count)

    Final: weighted_sum * size_multiplier, clamped to [0.0, 1.0]
    """
    stats = record["stats"]
    puzzle_count = stats["puzzle_count"]
    view_count = stats["view_count"]
    solved_count = stats["solved_count"]
    attempt_count = stats["attempt_count"]
    rating = stats["rating"]
    rating_count = stats["rating_count"]

    # 1. Bayesian rating (confidence-adjusted)
    bayesian = compute_bayesian_rating(
        rating=rating,
        rating_count=rating_count,
        global_mean=global_stats["weighted_mean_rating"],
        prior_strength=global_stats["median_rating_count"],
    )
    # Normalize: OGS ratings are 0-5, Bayesian pulls toward ~4.3 mean
    # Use (bayesian - 1.0) / 4.0 to map 1-5 range to 0-1
    bayesian_norm = max(0.0, min(1.0, (bayesian - 1.0) / 4.0))

    # 2. Engagement score
    max_views = global_stats["max_view_count"]
    view_score = math.log10(view_count + 1) / math.log10(max_views + 1)

    if attempt_count > 0:
        # OGS solved_count can exceed attempt_count (solves counted per-puzzle,
        # attempts counted differently), so clamp to [0.0, 1.0]
        solve_rate = min(1.0, solved_count / attempt_count)
    else:
        solve_rate = None

    engagement = (
        ENGAGEMENT_VIEW_WEIGHT * view_score
        + ENGAGEMENT_SOLVE_WEIGHT * (solve_rate if solve_rate is not None else 0.0)
    )

    # 3. Content score (log-scaled puzzle count)
    max_puzzles = global_stats["max_puzzle_count"]
    content = math.log2(puzzle_count + 1) / math.log2(max_puzzles + 1)

    # Composite score
    raw_score = (
        WEIGHT_RATING * bayesian_norm
        + WEIGHT_ENGAGEMENT * engagement
        + WEIGHT_CONTENT * content
    )

    # Apply size penalty
    priority_score = raw_score * compute_size_multiplier(puzzle_count)
    priority_score = max(0.0, min(1.0, priority_score))

    return ScoredCollection(
        record=record,
        priority_score=round(priority_score, 6),
        bayesian_rating=round(bayesian, 4),
        solve_rate=round(solve_rate, 4) if solve_rate is not None else None,
    )


def assign_tiers(scored: list[ScoredCollection]) -> None:
    """Assign quality_tier based on percentile rank within the sorted list.

    Mutates in place. The list MUST already be sorted by priority_score descending.

    Top 10%:   "premier"
    Top 30%:   "curated"
    Top 60%:   "community"
    Bottom 40%: "unvetted"
    """
    n = len(scored)
    if n == 0:
        return

    for i, s in enumerate(scored):
        percentile = (i + 1) / n
        for threshold, tier in TIER_THRESHOLDS:
            if percentile <= threshold:
                s.quality_tier = tier
                break


def sort_and_rank(collections: list[dict[str, Any]]) -> list[ScoredCollection]:
    """Score, sort, and rank all collections.

    1. Compute global statistics
    2. Score each collection
    3. Sort by priority_score descending (tiebreak by view_count desc)
    4. Assign sort_rank (1-based)
    5. Assign quality_tier by percentile

    Returns:
        List of ScoredCollection objects, sorted and ranked.
    """
    if not collections:
        logger.warning("No collections to sort")
        return []

    # Compute global normalization stats
    global_stats = compute_global_stats(collections)

    # Score each collection
    scored = [score_collection(c, global_stats) for c in collections]

    # Sort: primary by score descending, secondary by view_count descending
    scored.sort(key=lambda s: (-s.priority_score, -s.record["stats"]["view_count"]))

    # Assign rank (1-based)
    for i, s in enumerate(scored, 1):
        s.sort_rank = i

    # Assign quality tiers
    assign_tiers(scored)

    # Log summary
    log_summary(scored)

    return scored


# ============================================================================
# Summary Logging
# ============================================================================

def log_summary(scored: list[ScoredCollection]) -> None:
    """Log summary statistics about the sorting results."""
    if not scored:
        logger.info("No collections to summarize")
        return

    n = len(scored)
    scores = [s.priority_score for s in scored]

    logger.info("")
    logger.info("=" * 60)
    logger.info("SORTING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total collections: {n}")
    logger.info("")

    # Score statistics
    logger.info(f"Priority scores:  min={min(scores):.6f}  max={max(scores):.6f}  "
                f"mean={statistics.mean(scores):.6f}  median={statistics.median(scores):.6f}")
    logger.info("")

    # Tier distribution
    tier_counts: dict[str, int] = {}
    for s in scored:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1

    logger.info("Tier Distribution:")
    logger.info(f"  {'Tier':<12} {'Count':>6}  {'%':>6}")
    logger.info(f"  {'-' * 12} {'-' * 6}  {'-' * 6}")
    for _, tier in TIER_THRESHOLDS:
        count = tier_counts.get(tier, 0)
        pct = count / n * 100
        logger.info(f"  {tier:<12} {count:>6}  {pct:>5.1f}%")
    logger.info("")

    # Top 5
    logger.info("Top 5 collections:")
    for s in scored[:5]:
        name = s.record["name"][:50]
        logger.info(
            f"  #{s.sort_rank:<4} score={s.priority_score:.4f}  "
            f"tier={s.quality_tier:<10} puzzles={s.record['stats']['puzzle_count']:<5} "
            f"views={s.record['stats']['view_count']:>10,}  {name}"
        )
    logger.info("")

    # Bottom 5
    logger.info("Bottom 5 collections:")
    for s in scored[-5:]:
        name = s.record["name"][:50]
        logger.info(
            f"  #{s.sort_rank:<4} score={s.priority_score:.4f}  "
            f"tier={s.quality_tier:<10} puzzles={s.record['stats']['puzzle_count']:<5} "
            f"views={s.record['stats']['view_count']:>10,}  {name}"
        )

    # Level distribution
    logger.info("")
    logger.info("Level distribution (all tiers):")
    level_counts: dict[str, int] = {}
    for s in scored:
        level = s.record.get("difficulty", {}).get("yengo_level", "unknown")
        level_counts[level] = level_counts.get(level, 0) + 1
    for level, count in sorted(level_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {level:<20} {count:>5}")

    logger.info("=" * 60)


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sort OGS puzzle collections by computed priority score"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input JSONL file (from explore_collections.py)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output JSONL file (default: <input-stem>-sorted.jsonl in same directory)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = get_project_root() / input_path

    output_path: Path | None = args.output
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}-sorted.jsonl"
    elif not output_path.is_absolute():
        output_path = get_project_root() / output_path

    logger.info("OGS Collections Sorter")
    logger.info("=" * 40)
    logger.info(f"Input:  {rel_path(input_path)}")
    logger.info(f"Output: {rel_path(output_path)}")
    logger.info("")

    # Read
    metadata, collections = read_collections(input_path)

    # Score, sort, rank
    scored = sort_and_rank(collections)

    # Write
    write_sorted_collections(output_path, metadata, scored)

    logger.info("")
    logger.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
