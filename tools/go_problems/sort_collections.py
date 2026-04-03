"""
GoProblems Collections Sorter

Reads a GoProblems collections JSONL file (from explore_collections.py),
computes a composite priority score for each collection, and outputs
a re-sorted JSONL with additional computed fields.

Added fields per collection:
    sort_rank:       int   (1 = highest priority)
    priority_score:  float (0.0-1.0, rounded to 6 decimal places)
    quality_tier:    str   ("premier" | "curated" | "community" | "unvetted")
    bayesian_rating: float (confidence-adjusted star rating, 4 decimals)

Supports two scoring modes:
    - Full (enriched): 4-component Bayesian formula using per-puzzle stats
    - API-only: content + group score when no per-puzzle stats available

Usage:
    python -m tools.go_problems.sort_collections -i <collections.jsonl>
    python -m tools.go_problems.sort_collections -i <file> -o <output>
    python -m tools.go_problems.sort_collections -i <file> -v
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
from tools.go_problems.config import get_project_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Scoring Configuration
# ============================================================================

# Component weights (adapted for GoProblems: no views/solves at collection level)
WEIGHT_QUALITY = 0.35       # Bayesian-adjusted star quality
WEIGHT_ENGAGEMENT = 0.25    # Vote engagement (proxy for popularity)
WEIGHT_CANON = 0.20         # Canon ratio (community vetting)
WEIGHT_CONTENT = 0.20       # Puzzle count (log-scaled)

# Size multiplier thresholds: (min_puzzle_count, multiplier)
SIZE_THRESHOLDS: list[tuple[int, float]] = [
    (3, 0.3),     # < 3 puzzles: heavy penalty
    (5, 0.5),     # < 5 puzzles: moderate penalty
    (10, 0.8),    # < 10 puzzles: light penalty
]
# >= 10 puzzles: no penalty (1.0)

# API-only scoring weights (no per-puzzle stats available)
WEIGHT_CONTENT_API_ONLY = 0.70   # Puzzle count (only reliable API signal)
WEIGHT_GROUP_BONUS = 0.30        # "Style" curation signal

# Group field bonuses (from Collections API "group" field)
GROUP_STYLE_BONUS = 0.8          # "Style" = curated/themed collections
GROUP_COLLECTION_BONUS = 0.3     # "Collection" = user-created
GROUP_DEFAULT_BONUS = 0.1        # Unknown or missing group

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
    Lines 2+: Collection records sorted by priority_score descending.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute tier distribution
    tier_counts: dict[str, int] = {}
    for s in scored:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1

    # Enrich metadata
    metadata_out = dict(metadata)
    metadata_out["sorted_at"] = datetime.now(UTC).isoformat()
    metadata_out["sorted_by"] = "priority_score"
    metadata_out["total_collections"] = len(scored)
    metadata_out["scoring_weights"] = {
        "enriched": {
            "quality": WEIGHT_QUALITY,
            "engagement": WEIGHT_ENGAGEMENT,
            "canon": WEIGHT_CANON,
            "content": WEIGHT_CONTENT,
        },
        "api_only": {
            "content": WEIGHT_CONTENT_API_ONLY,
            "group_bonus": WEIGHT_GROUP_BONUS,
        },
    }
    metadata_out["tier_distribution"] = tier_counts

    enriched_count = sum(
        1 for s in scored if s.record.get("enriched", False)
    )
    api_only_count = len(scored) - enriched_count
    metadata_out["enriched_count"] = enriched_count
    metadata_out["api_only_count"] = api_only_count

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata_out, ensure_ascii=False))
        f.write("\n")

        for s in scored:
            record = dict(s.record)
            record["sort_rank"] = s.sort_rank
            record["priority_score"] = s.priority_score
            record["quality_tier"] = s.quality_tier
            record["bayesian_rating"] = s.bayesian_rating
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")

    logger.info(f"Wrote {len(scored)} sorted collections to {rel_path(output_path)}")


# ============================================================================
# Scoring Engine
# ============================================================================

def compute_global_stats(collections: list[dict[str, Any]]) -> dict[str, float]:
    """Compute global statistics needed for normalization.

    Returns dict with keys:
        median_rated_count: Prior strength (C) for Bayesian formula
        weighted_mean_stars: Global mean (m) for Bayesian formula
        max_avg_votes: For log-scale normalization
        max_puzzle_count: For log-scale normalization
    """
    rated_counts = [
        c["stats"]["rated_puzzle_count"]
        for c in collections
        if c["stats"]["rated_puzzle_count"] > 0
    ]
    max_avg_votes = max(
        (c["stats"]["avg_votes"] for c in collections), default=1.0,
    )
    max_puzzles = max(
        (c["stats"]["puzzle_count"] for c in collections), default=1,
    )

    # Median rated puzzle count as Bayesian prior strength
    median_rc = statistics.median(rated_counts) if rated_counts else 1.0

    # Weighted mean star rating (only collections with ratings)
    weighted_sum = 0.0
    weight_total = 0
    for c in collections:
        rpc = c["stats"]["rated_puzzle_count"]
        if rpc > 0:
            weighted_sum += c["stats"]["avg_stars"] * rpc
            weight_total += rpc
    weighted_mean = weighted_sum / weight_total if weight_total > 0 else 3.0

    stats = {
        "median_rated_count": float(median_rc),
        "weighted_mean_stars": weighted_mean,
        "max_avg_votes": float(max(max_avg_votes, 1.0)),
        "max_puzzle_count": float(max(max_puzzles, 1)),
    }

    logger.info(
        f"Global stats: median_rated_count={stats['median_rated_count']:.1f}, "
        f"weighted_mean_stars={stats['weighted_mean_stars']:.4f}, "
        f"max_avg_votes={stats['max_avg_votes']:.1f}, "
        f"max_puzzles={stats['max_puzzle_count']:.0f}"
    )
    return stats


def compute_bayesian_rating(
    avg_stars: float,
    rated_count: int,
    global_mean: float,
    prior_strength: float,
) -> float:
    """Compute Bayesian average star rating.

    Formula: (avg_stars * rated_count + m * C) / (rated_count + C)

    Pulls collections with few ratings toward the global mean.
    """
    return (avg_stars * rated_count + global_mean * prior_strength) / (
        rated_count + prior_strength
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


def score_collection_api_only(
    record: dict[str, Any],
    global_stats: dict[str, float],
) -> ScoredCollection:
    """Score a collection using only API-available data (no per-puzzle stats).

    Used when enriched=False and rated_puzzle_count=0.

    Components:
        1. content_norm (70%): log2(puzzle_count) / log2(max)
        2. group_score (30%): Style=0.8, Collection=0.3, unknown=0.1

    Final: weighted_sum * size_multiplier, clamped to [0.0, 1.0]
    """
    stats = record.get("stats", {})
    puzzle_count = stats.get("puzzle_count", record.get("puzzle_count", 0))

    # 1. Content score (log-scaled puzzle count)
    max_puzzles = global_stats["max_puzzle_count"]
    content = math.log2(puzzle_count + 1) / math.log2(max_puzzles + 1)

    # 2. Group score (Style = curated/themed, Collection = user-created)
    group = record.get("group", "")
    if group == "Style":
        group_score = GROUP_STYLE_BONUS
    elif group == "Collection":
        group_score = GROUP_COLLECTION_BONUS
    else:
        group_score = GROUP_DEFAULT_BONUS

    # Composite score
    raw_score = (
        WEIGHT_CONTENT_API_ONLY * content
        + WEIGHT_GROUP_BONUS * group_score
    )

    # Apply size penalty
    priority_score = raw_score * compute_size_multiplier(puzzle_count)
    priority_score = max(0.0, min(1.0, priority_score))

    return ScoredCollection(
        record=record,
        priority_score=round(priority_score, 6),
        bayesian_rating=0.0,  # No star data available
    )


def score_collection(
    record: dict[str, Any],
    global_stats: dict[str, float],
) -> ScoredCollection:
    """Compute priority score for a single collection.

    Dispatches to score_collection_api_only() for non-enriched collections
    without per-puzzle stats. Uses the full 4-component formula for enriched
    collections.

    Components (full formula):
        1. bayesian_quality_norm (0-1): Bayesian-adjusted star rating
        2. engagement_norm (0-1): log-scaled avg_votes
        3. canon_ratio (0-1): canonical puzzle fraction
        4. content_norm (0-1): log2(puzzle_count) / log2(max)

    Final: weighted_sum * size_multiplier, clamped to [0.0, 1.0]
    """
    # Dispatch to API-only scoring when no per-puzzle stats are available
    is_enriched = record.get("enriched", False)
    rated_count = record.get("stats", {}).get("rated_puzzle_count", 0)

    if not is_enriched and rated_count == 0:
        return score_collection_api_only(record, global_stats)

    stats = record["stats"]
    puzzle_count = stats["puzzle_count"]
    avg_stars = stats["avg_stars"]
    avg_votes = stats["avg_votes"]
    rated_count = stats["rated_puzzle_count"]
    canon_ratio = stats.get("canon_ratio", 0.0)

    # 1. Bayesian quality (confidence-adjusted star rating)
    bayesian = compute_bayesian_rating(
        avg_stars=avg_stars,
        rated_count=rated_count,
        global_mean=global_stats["weighted_mean_stars"],
        prior_strength=global_stats["median_rated_count"],
    )
    # Normalize: stars are 0-5, map (1-5) range to (0-1)
    bayesian_norm = max(0.0, min(1.0, (bayesian - 1.0) / 4.0))

    # 2. Engagement score (log-scaled avg votes)
    max_avg_votes = global_stats["max_avg_votes"]
    engagement = math.log10(avg_votes + 1) / math.log10(max_avg_votes + 1)

    # 3. Canon ratio (already 0-1)
    canon = canon_ratio

    # 4. Content score (log-scaled puzzle count)
    max_puzzles = global_stats["max_puzzle_count"]
    content = math.log2(puzzle_count + 1) / math.log2(max_puzzles + 1)

    # Composite score
    raw_score = (
        WEIGHT_QUALITY * bayesian_norm
        + WEIGHT_ENGAGEMENT * engagement
        + WEIGHT_CANON * canon
        + WEIGHT_CONTENT * content
    )

    # Apply size penalty
    priority_score = raw_score * compute_size_multiplier(puzzle_count)
    priority_score = max(0.0, min(1.0, priority_score))

    return ScoredCollection(
        record=record,
        priority_score=round(priority_score, 6),
        bayesian_rating=round(bayesian, 4),
    )


def assign_tiers(scored: list[ScoredCollection]) -> None:
    """Assign quality_tier based on percentile rank.

    Mutates in place. List MUST be sorted by priority_score descending.

    Top 10%:    "premier"
    Top 30%:    "curated"
    Top 60%:    "community"
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
    3. Sort by priority_score descending (tiebreak by puzzle_count desc)
    4. Assign sort_rank (1-based)
    5. Assign quality_tier by percentile

    Returns:
        List of ScoredCollection objects, sorted and ranked.
    """
    if not collections:
        logger.warning("No collections to sort")
        return []

    global_stats = compute_global_stats(collections)

    scored = [score_collection(c, global_stats) for c in collections]

    # Sort: primary by score descending, secondary by puzzle_count descending
    scored.sort(
        key=lambda s: (-s.priority_score, -s.record["stats"]["puzzle_count"])
    )

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

    enriched_count = sum(
        1 for s in scored if s.record.get("enriched", False)
    )
    api_only_count = n - enriched_count
    logger.info(f"Scoring mode:  {enriched_count} enriched (full formula), "
                f"{api_only_count} API-only (content + group)")
    logger.info("")

    logger.info(
        f"Priority scores:  min={min(scores):.6f}  max={max(scores):.6f}  "
        f"mean={statistics.mean(scores):.6f}  median={statistics.median(scores):.6f}"
    )
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
            f"{name}"
        )
    logger.info("")

    # Genre distribution
    logger.info("Genre distribution (all tiers):")
    genre_counts: dict[str, int] = {}
    for s in scored:
        for genre, count in s.record.get("genre_distribution", {}).items():
            genre_counts[genre] = genre_counts.get(genre, 0) + count
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {genre:<25} {count:>5}")

    logger.info("=" * 60)


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sort GoProblems collections by computed priority score",
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
        help="Output JSONL file (default: <input-stem>-sorted.jsonl)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_root = get_project_root()

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = project_root / input_path

    output_path: Path | None = args.output
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}-sorted.jsonl"
    elif not output_path.is_absolute():
        output_path = project_root / output_path

    logger.info("GoProblems Collections Sorter")
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
