"""Unit tests for classifier module."""


from backend.puzzle_manager.core.classifier import (
    LEVEL_NAMES,
    classify_difficulty,
    resolve_level_from_collections,
)
from backend.puzzle_manager.core.sgf_parser import parse_sgf


class TestLevelNames:
    """Tests for level name constants."""

    def test_all_nine_levels_defined(self) -> None:
        """All 9 levels should be defined."""
        assert len(LEVEL_NAMES) == 9

    def test_level_names_are_strings(self) -> None:
        """All level names should be strings."""
        for level, name in LEVEL_NAMES.items():
            assert isinstance(level, int)
            assert isinstance(name, str)
            assert 1 <= level <= 9

    def test_expected_level_names(self) -> None:
        """Level names should match specification."""
        assert LEVEL_NAMES[1] == "novice"
        assert LEVEL_NAMES[5] == "upper-intermediate"
        assert LEVEL_NAMES[9] == "expert"


class TestClassifyDifficulty:
    """Tests for difficulty classification."""

    def test_simple_puzzle_classifies(self) -> None:
        """Simple puzzle should be classified."""
        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)
        level = classify_difficulty(game)

        assert isinstance(level, int)
        assert 1 <= level <= 9

    def test_classification_returns_int(self) -> None:
        """Classification should return integer level."""
        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc]AW[dd]
        ;B[cd];W[ce];B[de])"""
        game = parse_sgf(sgf)
        level = classify_difficulty(game)

        assert isinstance(level, int)

    def test_level_in_valid_range(self) -> None:
        """Classification level should be 1-9."""
        sgf = """(;GM[1]FF[4]SZ[19]
        PL[B]AB[aa][ab][ac][ba][bb]AW[bc][bd][ca][cb][cc]
        ;B[ad];W[ae];B[af];W[ag];B[ah])"""
        game = parse_sgf(sgf)
        level = classify_difficulty(game)

        assert 1 <= level <= 9


class TestClassificationConsistency:
    """Tests for classification consistency."""

    def test_same_puzzle_same_level(self) -> None:
        """Same puzzle should always classify to same level."""
        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        level1 = classify_difficulty(game)
        level2 = classify_difficulty(game)

        assert level1 == level2


class TestResolveLevelFromCollections:
    """Tests for collection-based level override."""

    # Fixture: a level_hint_map resembling real config
    HINT_MAP = {
        "novice-essentials": "novice",
        "beginner-essentials": "beginner",
        "elementary-essentials": "elementary",
        "intermediate-essentials": "intermediate",
        "upper-intermediate-essentials": "upper-intermediate",
        "advanced-essentials": "advanced",
        "low-dan-essentials": "low-dan",
        "high-dan-essentials": "high-dan",
        "expert-essentials": "expert",
        "cho-chikun-life-death-elementary": "elementary",
        "cho-chikun-life-death-intermediate": "intermediate",
        "cho-chikun-life-death-advanced": "advanced",
    }

    def test_single_collection_with_hint(self) -> None:
        """Puzzle in one level-bearing collection gets that level."""
        result = resolve_level_from_collections(
            ["beginner-essentials"],
            self.HINT_MAP,
        )
        assert result == (2, "beginner")

    def test_no_collection_hint(self) -> None:
        """Puzzle in collections without hints returns None."""
        result = resolve_level_from_collections(
            ["capture-problems", "ko-problems"],
            self.HINT_MAP,
        )
        assert result is None

    def test_empty_collections(self) -> None:
        """Empty collections list returns None."""
        result = resolve_level_from_collections([], self.HINT_MAP)
        assert result is None

    def test_empty_hint_map(self) -> None:
        """Empty hint map returns None."""
        result = resolve_level_from_collections(
            ["beginner-essentials"], {}
        )
        assert result is None

    def test_mixed_collections_one_hint(self) -> None:
        """Puzzle in multiple collections, only one with hint."""
        result = resolve_level_from_collections(
            ["capture-problems", "elementary-essentials", "ko-problems"],
            self.HINT_MAP,
        )
        assert result == (3, "elementary")

    def test_conflict_lower_level_wins(self) -> None:
        """When multiple level hints conflict, lowest (easiest) wins."""
        result = resolve_level_from_collections(
            ["beginner-essentials", "intermediate-essentials"],
            self.HINT_MAP,
        )
        # beginner (2) < intermediate (4) → beginner wins
        assert result == (2, "beginner")

    def test_conflict_with_author_and_graded(self) -> None:
        """Author collection + graded essentials → lowest wins."""
        result = resolve_level_from_collections(
            ["cho-chikun-life-death-advanced", "elementary-essentials"],
            self.HINT_MAP,
        )
        # elementary (3) < advanced (6) → elementary wins
        assert result == (3, "elementary")

    def test_same_level_multiple_collections(self) -> None:
        """Multiple collections with same level — no conflict."""
        hint_map = {
            "beginner-essentials": "beginner",
            "graded-go-problems-beginners-1": "beginner",
        }
        result = resolve_level_from_collections(
            ["beginner-essentials", "graded-go-problems-beginners-1"],
            hint_map,
        )
        assert result == (2, "beginner")

    def test_all_nine_levels_resolve(self) -> None:
        """Each of the 9 level slugs resolves correctly."""
        for slug, hint in self.HINT_MAP.items():
            if "essentials" in slug:
                result = resolve_level_from_collections(
                    [slug], self.HINT_MAP
                )
                assert result is not None
                level_num, level_slug = result
                assert level_slug == hint
                assert 1 <= level_num <= 9

    def test_heuristic_override_logged(self) -> None:
        """When heuristic disagrees, collection still wins."""
        # heuristic says intermediate (4), collection says beginner (2)
        result = resolve_level_from_collections(
            ["beginner-essentials"],
            self.HINT_MAP,
            puzzle_id="test-puzzle",
            heuristic_level=4,
        )
        assert result == (2, "beginner")

    def test_heuristic_agrees_no_change(self) -> None:
        """When heuristic agrees with collection, same result."""
        result = resolve_level_from_collections(
            ["beginner-essentials"],
            self.HINT_MAP,
            puzzle_id="test-puzzle",
            heuristic_level=2,
        )
        assert result == (2, "beginner")
