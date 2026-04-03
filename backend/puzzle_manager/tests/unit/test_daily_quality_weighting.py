"""Unit tests for D1: Quality-weighted daily challenge selection.

Tests:
- Pool filtering by min_quality and excluded_content_types
- Quality-weighted selection favors higher quality puzzles
- Determinism: same seed + same pool → same output
- DB-based pool loading (integration-level with tmp_path)
- Edge cases: all low-quality, empty categories, missing q/ct fields
"""

from datetime import datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.daily.generator import DailyGenerator
from backend.puzzle_manager.daily.standard import (
    _load_selection_weights,
    _weighted_sample,
    generate_standard_daily,
)
from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.config import DailyConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compact_entry(
    idx: int,
    level_id: int = 120,
    quality: int = 3,
    ct: int = 2,
    tags: list[int] | None = None,
) -> dict:
    """Create a compact puzzle entry with quality and content-type fields."""
    return {
        "p": f"0001/{idx:016x}",
        "l": level_id,
        "t": tags or [],
        "c": [],
        "x": [1, 2, 10, 1],
        "q": quality,
        "ct": ct,
    }


def _make_pool(size: int = 100, quality: int = 3, ct: int = 2) -> list[dict]:
    """Create a pool of compact entries with uniform quality and content-type."""
    level_ids = [120, 130, 140, 150, 160, 210]
    return [
        _make_compact_entry(i, level_id=level_ids[i % len(level_ids)], quality=quality, ct=ct)
        for i in range(size)
    ]


def _make_mixed_quality_pool(size: int = 200) -> list[dict]:
    """Create a pool with varied quality levels (1-5) and content types."""
    level_ids = [120, 130, 140, 150, 160, 210]
    pool = []
    for i in range(size):
        q = (i % 5) + 1  # Cycles 1,2,3,4,5
        ct = 2 if q >= 2 else 3  # q=1 → training, rest → practice
        pool.append(
            _make_compact_entry(i, level_id=level_ids[i % len(level_ids)], quality=q, ct=ct)
        )
    return pool


# ---------------------------------------------------------------------------
# Pool Filtering Tests
# ---------------------------------------------------------------------------


class TestPoolFiltering:
    """Tests for quality and content-type filtering in _load_puzzle_pool."""

    def test_default_config_excludes_training(self) -> None:
        """Default DailyConfig excludes ct=3 (training) puzzles."""
        config = DailyConfig()
        assert config.excluded_content_types == [3]
        assert config.min_quality == 2

    def test_pool_filter_removes_low_quality(self) -> None:
        """Puzzles below min_quality should be filtered out."""
        pool = [
            _make_compact_entry(0, quality=1),  # excluded (below min_quality=2)
            _make_compact_entry(1, quality=2),  # included
            _make_compact_entry(2, quality=3),  # included
            _make_compact_entry(3, quality=5),  # included
        ]
        min_quality = 2
        excluded_ct: set[int] = set()

        filtered = [
            p for p in pool
            if p.get("q", 1) >= min_quality
            and p.get("ct", 2) not in excluded_ct
        ]

        assert len(filtered) == 3
        assert all(p["q"] >= 2 for p in filtered)

    def test_pool_filter_removes_training(self) -> None:
        """Puzzles with ct=3 (training) should be filtered out."""
        pool = [
            _make_compact_entry(0, ct=1),  # curated — included
            _make_compact_entry(1, ct=2),  # practice — included
            _make_compact_entry(2, ct=3),  # training — excluded
        ]
        min_quality = 1
        excluded_ct = {3}

        filtered = [
            p for p in pool
            if p.get("q", 1) >= min_quality
            and p.get("ct", 2) not in excluded_ct
        ]

        assert len(filtered) == 2
        assert all(p["ct"] != 3 for p in filtered)

    def test_missing_q_defaults_to_1(self) -> None:
        """Entries without 'q' field default to q=1 (excluded at min_quality=2)."""
        pool = [
            {"p": "0001/aaa", "l": 120, "t": [], "c": [], "x": [1, 0, 5, 1]},  # no q, ct
            _make_compact_entry(1, quality=3),
        ]
        min_quality = 2
        excluded_ct: set[int] = set()

        filtered = [
            p for p in pool
            if p.get("q", 1) >= min_quality
            and p.get("ct", 2) not in excluded_ct
        ]

        assert len(filtered) == 1
        assert filtered[0]["q"] == 3

    def test_missing_ct_defaults_to_2(self) -> None:
        """Entries without 'ct' field default to ct=2 (practice, not excluded)."""
        pool = [
            {"p": "0001/aaa", "l": 120, "t": [], "c": [], "x": [1, 0, 5, 1], "q": 3},
        ]
        excluded_ct = {3}

        filtered = [
            p for p in pool
            if p.get("q", 1) >= 1
            and p.get("ct", 2) not in excluded_ct
        ]

        assert len(filtered) == 1

    def test_all_below_quality_returns_empty(self) -> None:
        """If all puzzles are below min_quality, filtered pool is empty."""
        pool = _make_pool(50, quality=1)
        min_quality = 2

        filtered = [p for p in pool if p.get("q", 1) >= min_quality]

        assert len(filtered) == 0


# ---------------------------------------------------------------------------
# Quality-Weighted Selection Tests
# ---------------------------------------------------------------------------


class TestQualityWeightedSelection:
    """Tests for quality-weighted puzzle selection."""

    def test_selection_weights_loaded(self) -> None:
        """Selection weights should load from config or use defaults."""
        weights = _load_selection_weights()
        assert isinstance(weights, dict)
        assert 1 in weights
        assert 5 in weights
        assert weights[5] > weights[1]  # Premium > unverified

    def test_weighted_sample_returns_correct_count(self) -> None:
        """_weighted_sample should return at most k unique puzzles."""
        from random import Random
        rng = Random(42)
        pool = _make_pool(50, quality=3)
        exclude: set[str] = set()

        result = _weighted_sample(rng, pool, 5, exclude)

        assert len(result) == 5
        paths = [p["p"] for p in result]
        assert len(set(paths)) == 5  # all unique

    def test_weighted_sample_no_duplicates(self) -> None:
        """Selected puzzles should not duplicate already-excluded IDs."""
        from random import Random
        rng = Random(42)
        pool = _make_pool(20, quality=3)
        exclude = {pool[0]["p"], pool[1]["p"]}  # Pre-exclude first two

        result = _weighted_sample(rng, pool, 5, exclude)

        result_paths = {p["p"] for p in result}
        assert pool[0]["p"] not in result_paths
        assert pool[1]["p"] not in result_paths

    def test_weighted_sample_empty_pool(self) -> None:
        """Empty pool should return empty list."""
        from random import Random
        rng = Random(42)
        result = _weighted_sample(rng, [], 5, set())
        assert result == []

    def test_weighted_sample_pool_smaller_than_k(self) -> None:
        """If pool has fewer than k items, return all available."""
        from random import Random
        rng = Random(42)
        pool = _make_pool(3, quality=4)
        result = _weighted_sample(rng, pool, 10, set())
        assert len(result) == 3

    def test_weighted_selection_favors_high_quality(self) -> None:
        """Over many samples, high-quality puzzles should appear more often.

        Creates pool with 50% q=1 (weight 0.1) and 50% q=5 (weight 3.0).
        Statistical expectation: q=5 selected ~97% of the time for k=1.
        """
        from random import Random

        pool = (
            [_make_compact_entry(i, quality=1, level_id=140) for i in range(50)]
            + [_make_compact_entry(i + 50, quality=5, level_id=140) for i in range(50)]
        )

        high_quality_count = 0
        trials = 200

        for trial in range(trials):
            rng = Random(trial)
            result = _weighted_sample(rng, pool, 1, set())
            if result and result[0]["q"] == 5:
                high_quality_count += 1

        # q=5 weight (3.0) is 30x q=1 weight (0.1). With 50/50 split,
        # expected proportion of q=5 selections ≈ 3.0/(3.0+0.1) ≈ 96.8%
        # Allow margin: at least 80% should be high quality
        assert high_quality_count >= 0.80 * trials, (
            f"Expected ≥80% q=5 selections, got {high_quality_count}/{trials}"
        )


# ---------------------------------------------------------------------------
# Determinism Tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Tests for deterministic daily generation."""

    def test_same_date_same_pool_same_result(self) -> None:
        """Same date and pool must produce identical puzzles."""
        config = DailyConfig()
        date = datetime(2026, 3, 15)
        pool = _make_mixed_quality_pool(200)

        result1 = generate_standard_daily(date, pool, config)
        result2 = generate_standard_daily(date, pool, config)

        ids1 = [p.id for p in result1.puzzles]
        ids2 = [p.id for p in result2.puzzles]
        assert ids1 == ids2

    def test_different_dates_different_result(self) -> None:
        """Different dates should (almost certainly) produce different puzzles."""
        config = DailyConfig()
        pool = _make_mixed_quality_pool(200)

        result1 = generate_standard_daily(datetime(2026, 3, 15), pool, config)
        result2 = generate_standard_daily(datetime(2026, 3, 16), pool, config)

        ids1 = [p.id for p in result1.puzzles]
        ids2 = [p.id for p in result2.puzzles]
        # They could theoretically match, but with 200 puzzles it's virtually impossible
        assert ids1 != ids2

    def test_sorted_pool_ensures_determinism(self) -> None:
        """Pool sorted by compact path 'p' should ensure identical selection
        regardless of original load order."""
        config = DailyConfig()
        date = datetime(2026, 3, 15)
        pool = _make_mixed_quality_pool(100)

        # Reverse the pool order
        reversed_pool = list(reversed(pool))

        # Sort both by 'p' (as _load_puzzle_pool does)
        pool_sorted = sorted(pool, key=lambda p: p.get("p", ""))
        reversed_sorted = sorted(reversed_pool, key=lambda p: p.get("p", ""))

        result1 = generate_standard_daily(date, pool_sorted, config)
        result2 = generate_standard_daily(date, reversed_sorted, config)

        ids1 = [p.id for p in result1.puzzles]
        ids2 = [p.id for p in result2.puzzles]
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# Standard Daily Integration Tests
# ---------------------------------------------------------------------------


class TestStandardDailyQualityIntegration:
    """Integration tests for standard daily with quality-weighted selection."""

    def test_standard_daily_with_quality_pool(self) -> None:
        """Standard daily generation works with quality-enriched compact entries."""
        config = DailyConfig()
        date = datetime(2026, 3, 1)
        pool = _make_mixed_quality_pool(200)

        # Filter pool as _load_puzzle_pool would
        filtered = [
            p for p in pool
            if p.get("q", 1) >= config.min_quality
            and p.get("ct", 2) not in set(config.excluded_content_types)
        ]

        result = generate_standard_daily(date, filtered, config)

        assert result is not None
        assert len(result.puzzles) > 0
        assert result.total == len(result.puzzles)

    def test_all_puzzles_in_core_set_have_refs(self) -> None:
        """Core 5 puzzles (1 beginner + 2 intermediate + 2 advanced) should be present."""
        config = DailyConfig()
        date = datetime(2026, 3, 1)

        # Create pool with entries in all categories
        pool = (
            [_make_compact_entry(i, level_id=120, quality=3) for i in range(30)]  # beginner
            + [_make_compact_entry(i + 30, level_id=140, quality=4) for i in range(30)]  # intermediate
            + [_make_compact_entry(i + 60, level_id=160, quality=5) for i in range(30)]  # advanced
        )

        result = generate_standard_daily(date, pool, config)

        # Should have at least 5 puzzles (core distribution)
        assert len(result.puzzles) >= 5


# ---------------------------------------------------------------------------
# DB Pool Loading Tests
# ---------------------------------------------------------------------------


class TestDBPoolLoading:
    """Tests for loading puzzle pool from yengo-search.db."""

    @staticmethod
    def _build_db(output_dir: Path, entries: list | None = None) -> Path:
        """Build a test search DB."""
        from backend.puzzle_manager.core.db_builder import build_search_db
        from backend.puzzle_manager.core.db_models import PuzzleEntry

        if entries is None:
            entries = []
            for lvl_offset, level_id in enumerate([120, 140, 160]):
                for i in range(10):
                    idx = lvl_offset * 10 + i
                    entries.append(
                        PuzzleEntry(
                            content_hash=f"hash{idx:04d}abcdef01",
                            batch="0001",
                            level_id=level_id,
                            quality=3 + lvl_offset,
                            content_type=2,
                            cx_depth=1,
                            cx_refutations=1,
                            cx_solution_len=5,
                            cx_unique_resp=1,
                            tag_ids=[10],
                            collection_ids=[],
                        )
                    )

        db_path = output_dir / "yengo-search.db"
        build_search_db(entries=entries, collections=[], output_path=db_path)
        return db_path

    def test_load_pool_from_db(self, tmp_path: Path) -> None:
        """Pool should load entries from yengo-search.db."""
        self._build_db(tmp_path)
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")

        pool = generator._load_puzzle_pool()

        assert len(pool) == 30  # 10 per level × 3 levels

    def test_load_pool_filters_by_quality(self, tmp_path: Path) -> None:
        """Pool loader should exclude puzzles below min_quality."""
        from backend.puzzle_manager.core.db_models import PuzzleEntry

        entries = [
            PuzzleEntry(
                content_hash=f"hashq{i:04d}abcdef01",
                batch="0001",
                level_id=120,
                quality=1 if i < 5 else 3,
                content_type=2,
                cx_depth=1, cx_refutations=1, cx_solution_len=5, cx_unique_resp=1,
                tag_ids=[10], collection_ids=[],
            )
            for i in range(10)
        ]
        self._build_db(tmp_path, entries)
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")

        pool = generator._load_puzzle_pool()

        # min_quality=2 by default, so q=1 entries excluded
        assert len(pool) == 5
        assert all(p["q"] >= 2 for p in pool)

    def test_load_pool_filters_by_content_type(self, tmp_path: Path) -> None:
        """Pool loader should exclude training (ct=3) puzzles."""
        from backend.puzzle_manager.core.db_models import PuzzleEntry

        entries = [
            PuzzleEntry(
                content_hash=f"hashc{i:04d}abcdef01",
                batch="0001",
                level_id=140,
                quality=3,
                content_type=2 if i < 5 else 3,
                cx_depth=1, cx_refutations=1, cx_solution_len=5, cx_unique_resp=1,
                tag_ids=[10], collection_ids=[],
            )
            for i in range(10)
        ]
        self._build_db(tmp_path, entries)
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")

        pool = generator._load_puzzle_pool()

        assert len(pool) == 5
        assert all(p["ct"] != 3 for p in pool)

    def test_load_pool_sorted_by_path(self, tmp_path: Path) -> None:
        """Pool should be sorted by compact path for deterministic ordering."""
        self._build_db(tmp_path)
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")

        pool = generator._load_puzzle_pool()

        paths = [p["p"] for p in pool]
        assert paths == sorted(paths)

    def test_no_db_raises_on_missing(self, tmp_path: Path) -> None:
        """Missing yengo-search.db should raise DailyGenerationError."""
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")
        with pytest.raises(DailyGenerationError):
            generator._load_puzzle_pool()
