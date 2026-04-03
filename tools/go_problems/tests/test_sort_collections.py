"""
Tests for GoProblems collection sorting (sort_collections).

Tests scoring engine, tier assignment, Bayesian rating, size multiplier,
JSONL I/O, API-only scoring, and end-to-end sort_and_rank.
"""

import json
from pathlib import Path

import pytest

from tools.go_problems.sort_collections import (
    WEIGHT_CANON,
    WEIGHT_CONTENT,
    WEIGHT_CONTENT_API_ONLY,
    WEIGHT_ENGAGEMENT,
    WEIGHT_GROUP_BONUS,
    WEIGHT_QUALITY,
    ScoredCollection,
    assign_tiers,
    compute_bayesian_rating,
    compute_global_stats,
    compute_size_multiplier,
    read_collections,
    score_collection,
    score_collection_api_only,
    sort_and_rank,
    write_sorted_collections,
)

# ==============================
# Helpers
# ==============================

def _make_metadata() -> dict:
    return {"type": "metadata", "total_collections": 0}


def _make_collection(
    coll_id: int,
    name: str,
    puzzle_count: int = 50,
    avg_stars: float = 4.0,
    avg_votes: float = 10.0,
    rated_count: int = 10,
    canon_count: int = 5,
    canon_ratio: float = 0.5,
    group: str = "",
    enriched: bool = True,
    description: str = "",
) -> dict:
    return {
        "type": "collection",
        "id": coll_id,
        "name": name,
        "puzzle_count": puzzle_count,
        "group": group,
        "description": description,
        "enriched": enriched,
        "stats": {
            "puzzle_count": puzzle_count,
            "avg_stars": avg_stars,
            "avg_votes": avg_votes,
            "rated_puzzle_count": rated_count,
            "canon_count": canon_count,
            "canon_ratio": canon_ratio,
            "avg_rank": 15.0,
            "ranked_puzzle_count": puzzle_count,
        },
        "genre_distribution": {"life and death": puzzle_count},
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")


# ==============================
# Bayesian Rating Tests
# ==============================

class TestBayesianRating:
    def test_high_confidence(self) -> None:
        """Collection with many ratings stays near its own average."""
        result = compute_bayesian_rating(
            avg_stars=5.0, rated_count=100,
            global_mean=3.0, prior_strength=10,
        )
        assert result > 4.5

    def test_low_confidence_pulled_to_mean(self) -> None:
        """Collection with few ratings pulled toward global mean."""
        result = compute_bayesian_rating(
            avg_stars=5.0, rated_count=1,
            global_mean=3.0, prior_strength=10,
        )
        assert result < 4.0

    def test_zero_ratings(self) -> None:
        """Zero ratings returns global mean."""
        result = compute_bayesian_rating(
            avg_stars=0.0, rated_count=0,
            global_mean=3.5, prior_strength=10,
        )
        assert result == pytest.approx(3.5)


# ==============================
# Size Multiplier Tests
# ==============================

class TestSizeMultiplier:
    def test_tiny(self) -> None:
        assert compute_size_multiplier(1) == 0.3
        assert compute_size_multiplier(2) == 0.3

    def test_small(self) -> None:
        assert compute_size_multiplier(3) == 0.5
        assert compute_size_multiplier(4) == 0.5

    def test_medium(self) -> None:
        assert compute_size_multiplier(5) == 0.8
        assert compute_size_multiplier(9) == 0.8

    def test_large(self) -> None:
        assert compute_size_multiplier(10) == 1.0
        assert compute_size_multiplier(100) == 1.0


# ==============================
# Global Stats Tests
# ==============================

class TestGlobalStats:
    def test_basic_stats(self) -> None:
        collections = [
            _make_collection(1, "A", avg_stars=4.0, avg_votes=20.0, rated_count=10),
            _make_collection(2, "B", avg_stars=3.0, avg_votes=5.0, rated_count=5),
            _make_collection(3, "C", avg_stars=5.0, avg_votes=100.0, rated_count=20),
        ]
        stats = compute_global_stats(collections)
        assert stats["max_avg_votes"] == 100.0
        assert stats["max_puzzle_count"] == 50.0
        assert stats["median_rated_count"] == 10.0
        assert 3.0 < stats["weighted_mean_stars"] < 5.0

    def test_empty_collections(self) -> None:
        stats = compute_global_stats([])
        assert stats["max_avg_votes"] == 1.0
        assert stats["max_puzzle_count"] == 1.0


# ==============================
# Score Collection Tests
# ==============================

class TestScoreCollection:
    def test_perfect_collection(self) -> None:
        """High stars, high votes, high canon, many puzzles -> high score."""
        global_stats = {
            "median_rated_count": 5.0,
            "weighted_mean_stars": 3.0,
            "max_avg_votes": 100.0,
            "max_puzzle_count": 200.0,
        }
        coll = _make_collection(
            1, "Perfect",
            puzzle_count=200, avg_stars=5.0, avg_votes=100.0,
            rated_count=100, canon_count=200, canon_ratio=1.0,
        )
        scored = score_collection(coll, global_stats)
        assert scored.priority_score > 0.8

    def test_poor_collection(self) -> None:
        """Low stats, few puzzles -> low score."""
        global_stats = {
            "median_rated_count": 5.0,
            "weighted_mean_stars": 3.0,
            "max_avg_votes": 100.0,
            "max_puzzle_count": 200.0,
        }
        coll = _make_collection(
            2, "Poor",
            puzzle_count=2, avg_stars=1.5, avg_votes=1.0,
            rated_count=1, canon_count=0, canon_ratio=0.0,
        )
        scored = score_collection(coll, global_stats)
        assert scored.priority_score < 0.2

    def test_score_clamped_to_0_1(self) -> None:
        global_stats = {
            "median_rated_count": 1.0,
            "weighted_mean_stars": 3.0,
            "max_avg_votes": 1.0,
            "max_puzzle_count": 1.0,
        }
        coll = _make_collection(1, "X", puzzle_count=1000)
        scored = score_collection(coll, global_stats)
        assert 0.0 <= scored.priority_score <= 1.0

    def test_weights_sum_to_one(self) -> None:
        total = WEIGHT_QUALITY + WEIGHT_ENGAGEMENT + WEIGHT_CANON + WEIGHT_CONTENT
        assert total == pytest.approx(1.0)


# ==============================
# Tier Assignment Tests
# ==============================

class TestAssignTiers:
    def test_tier_distribution(self) -> None:
        """10 collections -> 1 premier, 2 curated, 3 community, 4 unvetted."""
        scored = [
            ScoredCollection(record={}, priority_score=1.0 - i * 0.1, bayesian_rating=0.0)
            for i in range(10)
        ]
        assign_tiers(scored)
        tiers = [s.quality_tier for s in scored]
        assert tiers[0] == "premier"       # top 10%
        assert tiers[1] == "curated"       # 10-30%
        assert tiers[2] == "curated"
        assert tiers[3] == "community"     # 30-60%
        assert tiers[6] == "unvetted"      # bottom 40%
        assert tiers[9] == "unvetted"

    def test_empty_list(self) -> None:
        scored: list[ScoredCollection] = []
        assign_tiers(scored)  # Should not raise

    def test_single_collection(self) -> None:
        """A single collection gets percentile 1/1 = 1.0 which maps to unvetted."""
        scored = [ScoredCollection(record={}, priority_score=0.5, bayesian_rating=3.0)]
        assign_tiers(scored)
        # 1/1 = 1.0, which is > 0.60 -> unvetted
        assert scored[0].quality_tier == "unvetted"


# ==============================
# JSONL I/O Tests
# ==============================

class TestReadCollections:
    def test_reads_valid_jsonl(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "test.jsonl"
        _write_jsonl(jsonl, [
            _make_metadata(),
            _make_collection(1, "Alpha"),
            _make_collection(2, "Beta"),
        ])
        metadata, collections = read_collections(jsonl)
        assert metadata["type"] == "metadata"
        assert len(collections) == 2

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_collections(tmp_path / "missing.jsonl")

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.jsonl"
        f.write_text("", encoding="utf-8")
        with pytest.raises(ValueError):
            read_collections(f)

    def test_no_metadata_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.jsonl"
        f.write_text(json.dumps({"type": "collection"}), encoding="utf-8")
        with pytest.raises(ValueError, match="metadata"):
            read_collections(f)


class TestWriteSortedCollections:
    def test_writes_enriched_jsonl(self, tmp_path: Path) -> None:
        output = tmp_path / "sorted.jsonl"
        metadata = {"type": "metadata", "source": "test"}
        scored = [
            ScoredCollection(
                record=_make_collection(1, "Top"),
                priority_score=0.9, bayesian_rating=4.5,
                sort_rank=1, quality_tier="premier",
            ),
        ]
        write_sorted_collections(output, metadata, scored)

        lines = output.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        meta = json.loads(lines[0])
        assert "sorted_at" in meta
        assert meta["total_collections"] == 1

        coll = json.loads(lines[1])
        assert coll["sort_rank"] == 1
        assert coll["priority_score"] == 0.9
        assert coll["quality_tier"] == "premier"


# ==============================
# End-to-End Tests
# ==============================

class TestSortAndRank:
    def test_sorts_by_score(self) -> None:
        collections = [
            _make_collection(1, "Low", avg_stars=1.0, avg_votes=1.0, rated_count=1, canon_ratio=0.0),
            _make_collection(2, "High", avg_stars=5.0, avg_votes=50.0, rated_count=50, canon_ratio=1.0),
        ]
        scored = sort_and_rank(collections)

        assert scored[0].record["id"] == 2  # High should be first
        assert scored[1].record["id"] == 1
        assert scored[0].sort_rank == 1
        assert scored[1].sort_rank == 2
        assert scored[0].priority_score >= scored[1].priority_score

    def test_empty_returns_empty(self) -> None:
        scored = sort_and_rank([])
        assert scored == []

    def test_tiers_assigned(self) -> None:
        # Create 20 collections with varying quality
        collections = [
            _make_collection(
                i, f"Collection {i}",
                avg_stars=1.0 + i * 0.2,
                avg_votes=float(i),
                rated_count=i,
                canon_ratio=i / 20.0,
            )
            for i in range(1, 21)
        ]
        scored = sort_and_rank(collections)
        tiers = {s.quality_tier for s in scored}
        assert "premier" in tiers
        assert "unvetted" in tiers


# ==============================
# API-Only Scoring Tests
# ==============================

class TestApiOnlyScoring:
    """Tests for score_collection_api_only and dispatch logic."""

    def _global_stats(self) -> dict:
        return {
            "median_rated_count": 5.0,
            "weighted_mean_stars": 3.0,
            "max_avg_votes": 100.0,
            "max_puzzle_count": 3000.0,
        }

    def test_style_scores_higher_than_collection(self) -> None:
        """Style group gets higher group bonus than Collection group."""
        gs = self._global_stats()
        style_coll = _make_collection(
            1, "Style Set", puzzle_count=100, rated_count=0,
            enriched=False, group="Style",
        )
        user_coll = _make_collection(
            2, "User Set", puzzle_count=100, rated_count=0,
            enriched=False, group="Collection",
        )
        style_scored = score_collection_api_only(style_coll, gs)
        user_scored = score_collection_api_only(user_coll, gs)
        assert style_scored.priority_score > user_scored.priority_score

    def test_larger_collection_scores_higher(self) -> None:
        """More puzzles -> higher content score."""
        gs = self._global_stats()
        large = _make_collection(
            1, "Large", puzzle_count=500, rated_count=0,
            enriched=False, group="Style",
        )
        small = _make_collection(
            2, "Small", puzzle_count=10, rated_count=0,
            enriched=False, group="Style",
        )
        large_scored = score_collection_api_only(large, gs)
        small_scored = score_collection_api_only(small, gs)
        assert large_scored.priority_score > small_scored.priority_score

    def test_bayesian_rating_is_zero(self) -> None:
        """API-only scoring sets bayesian_rating to 0.0 (no star data)."""
        gs = self._global_stats()
        coll = _make_collection(
            1, "Test", puzzle_count=50, rated_count=0,
            enriched=False, group="Style",
        )
        scored = score_collection_api_only(coll, gs)
        assert scored.bayesian_rating == 0.0

    def test_score_clamped_to_0_1(self) -> None:
        gs = self._global_stats()
        gs["max_puzzle_count"] = 1.0  # Force extreme normalization
        coll = _make_collection(
            1, "X", puzzle_count=5000, rated_count=0,
            enriched=False, group="Style",
        )
        scored = score_collection_api_only(coll, gs)
        assert 0.0 <= scored.priority_score <= 1.0

    def test_api_only_weights_sum_to_one(self) -> None:
        total = WEIGHT_CONTENT_API_ONLY + WEIGHT_GROUP_BONUS
        assert total == pytest.approx(1.0)

    def test_unknown_group_gets_default_bonus(self) -> None:
        """Missing or unknown group field gets GROUP_DEFAULT_BONUS."""
        gs = self._global_stats()
        no_group = _make_collection(
            1, "No Group", puzzle_count=100, rated_count=0,
            enriched=False, group="",
        )
        style = _make_collection(
            2, "Style", puzzle_count=100, rated_count=0,
            enriched=False, group="Style",
        )
        no_group_scored = score_collection_api_only(no_group, gs)
        style_scored = score_collection_api_only(style, gs)
        assert style_scored.priority_score > no_group_scored.priority_score

    def test_dispatch_to_api_only(self) -> None:
        """score_collection dispatches to API-only when not enriched and no ratings."""
        gs = self._global_stats()
        coll = _make_collection(
            1, "API Only", puzzle_count=100, rated_count=0,
            enriched=False, group="Style",
        )
        scored = score_collection(coll, gs)
        assert scored.bayesian_rating == 0.0  # Marker of API-only path
        assert scored.priority_score > 0

    def test_enriched_uses_full_formula(self) -> None:
        """Enriched collections use the full 4-component formula."""
        gs = self._global_stats()
        coll = _make_collection(
            1, "Enriched", puzzle_count=100, avg_stars=4.5,
            avg_votes=50.0, rated_count=50, canon_ratio=0.8,
            enriched=True, group="Style",
        )
        scored = score_collection(coll, gs)
        assert scored.bayesian_rating > 0  # Full formula computes this


# ==============================
# Mixed Scoring Tests
# ==============================

class TestMixedScoring:
    """Tests for sorting a mix of enriched and API-only collections."""

    def test_mixed_sort_and_rank(self) -> None:
        """Mix of enriched and API-only collections are ranked together."""
        collections = [
            _make_collection(
                1, "Enriched High", puzzle_count=200,
                avg_stars=5.0, avg_votes=100.0, rated_count=100,
                canon_ratio=0.9, enriched=True, group="Style",
            ),
            _make_collection(
                2, "API Only Large", puzzle_count=2000,
                rated_count=0, enriched=False, group="Style",
            ),
            _make_collection(
                3, "API Only Small", puzzle_count=10,
                rated_count=0, enriched=False, group="Collection",
            ),
        ]
        scored = sort_and_rank(collections)
        assert len(scored) == 3
        # All should have valid scores
        for s in scored:
            assert 0.0 <= s.priority_score <= 1.0
            assert s.sort_rank > 0

    def test_metadata_includes_enrichment_counts(self, tmp_path: Path) -> None:
        """write_sorted_collections metadata includes enriched/api_only counts."""
        output = tmp_path / "sorted.jsonl"
        metadata = {"type": "metadata"}
        scored = [
            ScoredCollection(
                record=_make_collection(1, "E", enriched=True),
                priority_score=0.9, bayesian_rating=4.0,
                sort_rank=1, quality_tier="premier",
            ),
            ScoredCollection(
                record=_make_collection(2, "A", enriched=False),
                priority_score=0.5, bayesian_rating=0.0,
                sort_rank=2, quality_tier="curated",
            ),
        ]
        write_sorted_collections(output, metadata, scored)

        lines = output.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        assert meta["enriched_count"] == 1
        assert meta["api_only_count"] == 1
        assert "enriched" in meta["scoring_weights"]
        assert "api_only" in meta["scoring_weights"]
