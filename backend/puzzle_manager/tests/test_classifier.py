"""Unit tests for classifier module."""


from backend.puzzle_manager.core.classifier import (
    LEVEL_NAMES,
    classify_difficulty,
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
