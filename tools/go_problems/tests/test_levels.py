"""Tests for GoProblems rank-to-level mapping."""

from tools.go_problems.levels import (
    DEFAULT_LEVEL,
    PROBLEM_LEVEL_RANGES,
    LevelMapper,
    map_rank_to_level,
)


class TestMapRankToLevel:
    """Tests for rank -> level mapping."""

    def test_kyu_beginner(self):
        rank = {"value": 25, "unit": "kyu"}
        level = map_rank_to_level(rank)
        assert level == "beginner"

    def test_kyu_intermediate(self):
        rank = {"value": 15, "unit": "kyu"}
        level = map_rank_to_level(rank)
        assert level == "intermediate"

    def test_dan_low(self):
        rank = {"value": 1, "unit": "dan"}
        level = map_rank_to_level(rank)
        assert level == "low-dan"

    def test_dan_high(self):
        rank = {"value": 5, "unit": "dan"}
        level = map_rank_to_level(rank)
        assert level == "high-dan"

    def test_none_rank_returns_default(self):
        level = map_rank_to_level(None)
        assert level == DEFAULT_LEVEL

    def test_none_rank_with_problem_level_fallback(self):
        level = map_rank_to_level(None, problem_level=5)
        assert level == "novice"

    def test_problem_level_beginner(self):
        level = map_rank_to_level(None, problem_level=10)
        assert level == "beginner"

    def test_problem_level_expert(self):
        level = map_rank_to_level(None, problem_level=50)
        assert level == "expert"

    def test_empty_rank_dict(self):
        rank = {}
        level = map_rank_to_level(rank)
        assert level == DEFAULT_LEVEL

    def test_rank_missing_value(self):
        rank = {"unit": "kyu"}
        level = map_rank_to_level(rank)
        assert level == DEFAULT_LEVEL

    def test_rank_missing_unit(self):
        rank = {"value": 15}
        level = map_rank_to_level(rank)
        assert level == DEFAULT_LEVEL

    def test_both_none_returns_default(self):
        level = map_rank_to_level(None, None)
        assert level == DEFAULT_LEVEL


class TestLevelMapper:
    """Tests for LevelMapper class."""

    def test_rank_to_level_by_string(self):
        mapper = LevelMapper()
        assert mapper.rank_to_level("15k") == "intermediate"

    def test_rank_to_level_by_value_unit(self):
        mapper = LevelMapper()
        assert mapper.rank_to_level(value=15, unit="kyu") == "intermediate"

    def test_invalid_rank_string(self):
        mapper = LevelMapper()
        assert mapper.rank_to_level("invalid") == DEFAULT_LEVEL

    def test_problem_level_mapping(self):
        mapper = LevelMapper()
        assert mapper.problem_level_to_yengo(1) == "novice"
        assert mapper.problem_level_to_yengo(20) == "intermediate"
        assert mapper.problem_level_to_yengo(50) == "expert"

    def test_out_of_range_kyu(self):
        mapper = LevelMapper()
        assert mapper.rank_to_level("35k") == "novice"

    def test_out_of_range_dan(self):
        mapper = LevelMapper()
        assert mapper.rank_to_level("10d") == "expert"


class TestProblemLevelRanges:
    """Tests for problem level range completeness."""

    def test_ranges_cover_1_to_49(self):
        """All integers from 1-49 should map to some level."""
        mapper = LevelMapper()
        for i in range(1, 50):
            level = mapper.problem_level_to_yengo(i)
            assert level != DEFAULT_LEVEL or i in range(19, 25), f"Level {i} returned default"

    def test_ranges_are_contiguous(self):
        """Ranges should not have gaps."""
        for i in range(len(PROBLEM_LEVEL_RANGES) - 1):
            current_max = PROBLEM_LEVEL_RANGES[i][1]
            next_min = PROBLEM_LEVEL_RANGES[i + 1][0]
            assert next_min == current_max + 1, (
                f"Gap between ranges: {current_max} -> {next_min}"
            )
