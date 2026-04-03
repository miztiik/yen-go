"""Tests for tools.core.validation — puzzle validation v2.0.

Covers:
- PuzzleValidationConfig: defaults, from_dict (v1 & v2 compat), merge
- validate_puzzle: board size, min_stones, solution depth range
- SGF extraction: count_stones_in_sgf, extract_board_size_from_sgf
- validate_sgf_puzzle: end-to-end from raw SGF string
"""

from __future__ import annotations

from tools.core.validation import (
    DEFAULT_CONFIG,
    PuzzleValidationConfig,
    count_solution_moves_in_sgf,
    count_stones_in_sgf,
    extract_board_size_from_sgf,
    validate_puzzle,
    validate_sgf_puzzle,
)

# ==========================================================================
# PuzzleValidationConfig
# ==========================================================================


class TestPuzzleValidationConfigDefaults:
    """Verify default field values match v2.0 expectations."""

    def test_default_min_board_size(self) -> None:
        config = PuzzleValidationConfig()
        assert config.min_board_size == 5

    def test_default_max_board_size(self) -> None:
        config = PuzzleValidationConfig()
        assert config.max_board_size == 19

    def test_default_min_stones(self) -> None:
        config = PuzzleValidationConfig()
        assert config.min_stones == 2

    def test_default_min_solution_depth(self) -> None:
        config = PuzzleValidationConfig()
        assert config.min_solution_depth == 1

    def test_default_max_solution_depth(self) -> None:
        config = PuzzleValidationConfig()
        assert config.max_solution_depth == 30


class TestPuzzleValidationConfigFromDict:
    """from_dict with v2.0 and v1.0 backward-compatible fields."""

    def test_v2_fields(self) -> None:
        data = {
            "min_board_dimension": 7,
            "max_board_dimension": 13,
            "min_stones": 3,
            "min_solution_depth": 2,
            "max_solution_depth": 20,
        }
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_board_size == 7
        assert config.max_board_size == 13
        assert config.min_stones == 3
        assert config.min_solution_depth == 2
        assert config.max_solution_depth == 20

    def test_v1_require_solution_true(self) -> None:
        """v1.0 require_solution=True maps to min_solution_depth=1."""
        data = {"require_solution": True}
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_solution_depth == 1

    def test_v1_require_solution_false(self) -> None:
        """v1.0 require_solution=False maps to min_solution_depth=0."""
        data = {"require_solution": False}
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_solution_depth == 0

    def test_v1_require_initial_stones_true(self) -> None:
        """v1.0 require_initial_stones=True maps to min_stones=2."""
        data = {"require_initial_stones": True}
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_stones == 2

    def test_v1_require_initial_stones_false(self) -> None:
        """v1.0 require_initial_stones=False maps to min_stones=0."""
        data = {"require_initial_stones": False}
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_stones == 0

    def test_v2_takes_precedence_over_v1(self) -> None:
        """When both v2 and v1 fields present, v2 wins."""
        data = {
            "min_solution_depth": 3,
            "require_solution": False,
            "min_stones": 5,
            "require_initial_stones": False,
        }
        config = PuzzleValidationConfig.from_dict(data)
        assert config.min_solution_depth == 3
        assert config.min_stones == 5

    def test_empty_dict_uses_defaults(self) -> None:
        config = PuzzleValidationConfig.from_dict({})
        assert config.min_solution_depth == 1
        assert config.min_stones == 2
        assert config.min_board_size == 5
        assert config.max_board_size == 19

    def test_min_board_size_alias(self) -> None:
        """min_board_size is accepted as alias for min_board_dimension."""
        config = PuzzleValidationConfig.from_dict({"min_board_size": 7})
        assert config.min_board_size == 7

    def test_max_board_size_alias(self) -> None:
        """max_board_size is accepted as alias for max_board_dimension."""
        config = PuzzleValidationConfig.from_dict({"max_board_size": 13})
        assert config.max_board_size == 13


class TestPuzzleValidationConfigMerge:
    """merge() creates new config with selected overrides."""

    def test_merge_single_field(self) -> None:
        base = PuzzleValidationConfig()
        merged = base.merge({"min_stones": 5})
        assert merged.min_stones == 5
        assert merged.min_board_size == base.min_board_size
        assert merged.max_solution_depth == base.max_solution_depth

    def test_merge_multiple_fields(self) -> None:
        base = PuzzleValidationConfig()
        merged = base.merge({"min_stones": 0, "min_solution_depth": 0})
        assert merged.min_stones == 0
        assert merged.min_solution_depth == 0

    def test_merge_returns_new_instance(self) -> None:
        base = PuzzleValidationConfig()
        merged = base.merge({"min_stones": 10})
        assert base.min_stones == 2  # unchanged
        assert merged is not base

    def test_merge_empty_overrides(self) -> None:
        base = PuzzleValidationConfig(min_stones=3, min_solution_depth=4)
        merged = base.merge({})
        assert merged.min_stones == 3
        assert merged.min_solution_depth == 4


# ==========================================================================
# validate_puzzle
# ==========================================================================


class TestValidatePuzzleBoardSize:
    """Board dimension checks."""

    def test_valid_standard_board(self) -> None:
        result = validate_puzzle(board_width=19, board_height=19, stone_count=10, solution_depth=5)
        assert result.is_valid

    def test_valid_9x9(self) -> None:
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=3)
        assert result.is_valid

    def test_valid_minimum_board(self) -> None:
        result = validate_puzzle(board_width=5, board_height=5, stone_count=2, solution_depth=1)
        assert result.is_valid

    def test_board_too_small(self) -> None:
        result = validate_puzzle(board_width=4, board_height=4, stone_count=4, solution_depth=2)
        assert not result.is_valid
        assert "below minimum" in result.rejection_reason

    def test_board_too_large(self) -> None:
        result = validate_puzzle(board_width=21, board_height=21, stone_count=10, solution_depth=2)
        assert not result.is_valid
        assert "exceeds maximum" in result.rejection_reason

    def test_width_too_small_height_ok(self) -> None:
        result = validate_puzzle(board_width=3, board_height=19, stone_count=5, solution_depth=2)
        assert not result.is_valid
        assert "width" in result.rejection_reason.lower()

    def test_width_ok_height_too_small(self) -> None:
        result = validate_puzzle(board_width=9, board_height=4, stone_count=5, solution_depth=2)
        assert not result.is_valid
        assert "height" in result.rejection_reason.lower()


class TestValidatePuzzleMinStones:
    """min_stones check (replaces require_initial_stones)."""

    def test_default_requires_2_stones(self) -> None:
        result = validate_puzzle(board_width=9, board_height=9, stone_count=1, solution_depth=3)
        assert not result.is_valid
        assert "minimum is 2" in result.rejection_reason

    def test_exactly_2_stones_passes(self) -> None:
        result = validate_puzzle(board_width=9, board_height=9, stone_count=2, solution_depth=3)
        assert result.is_valid

    def test_zero_stones_rejected(self) -> None:
        result = validate_puzzle(board_width=9, board_height=9, stone_count=0, solution_depth=3)
        assert not result.is_valid

    def test_min_stones_override_to_zero(self) -> None:
        """When min_stones=0, even 0 stones is acceptable."""
        config = PuzzleValidationConfig(min_stones=0)
        result = validate_puzzle(board_width=9, board_height=9, stone_count=0, solution_depth=3, config=config)
        assert result.is_valid

    def test_min_stones_override_higher(self) -> None:
        """Custom min_stones=5 rejects puzzles with only 3 stones."""
        config = PuzzleValidationConfig(min_stones=5)
        result = validate_puzzle(board_width=9, board_height=9, stone_count=3, solution_depth=3, config=config)
        assert not result.is_valid
        assert "minimum is 5" in result.rejection_reason


class TestValidatePuzzleSolutionDepth:
    """Solution depth range [min_solution_depth, max_solution_depth]."""

    def test_default_requires_depth_1(self) -> None:
        """Default min_solution_depth=1: depth 0 = no solution → rejected."""
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=0)
        assert not result.is_valid
        assert "no solution" in result.rejection_reason.lower()

    def test_depth_1_passes_by_default(self) -> None:
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=1)
        assert result.is_valid

    def test_none_depth_treated_as_zero(self) -> None:
        """solution_depth=None is treated as 0 for min_solution_depth check."""
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=None)
        assert not result.is_valid

    def test_depth_exceeds_max(self) -> None:
        result = validate_puzzle(board_width=19, board_height=19, stone_count=10, solution_depth=35)
        assert not result.is_valid
        assert "too deep" in result.rejection_reason.lower()

    def test_depth_at_max_passes(self) -> None:
        result = validate_puzzle(board_width=19, board_height=19, stone_count=10, solution_depth=30)
        assert result.is_valid

    def test_no_max_depth_check_when_none(self) -> None:
        """max_solution_depth=None disables the upper bound check."""
        config = PuzzleValidationConfig(max_solution_depth=None)
        result = validate_puzzle(board_width=19, board_height=19, stone_count=10, solution_depth=100, config=config)
        assert result.is_valid

    def test_min_solution_depth_zero_allows_no_solution(self) -> None:
        """min_solution_depth=0 allows puzzles without solutions (OGS use case)."""
        config = PuzzleValidationConfig(min_solution_depth=0)
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=0, config=config)
        assert result.is_valid

    def test_custom_min_depth(self) -> None:
        """min_solution_depth=3 rejects depth-2 puzzles."""
        config = PuzzleValidationConfig(min_solution_depth=3)
        result = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=2, config=config)
        assert not result.is_valid
        assert "below minimum" in result.rejection_reason


class TestValidatePuzzleUseDefaultConfig:
    """validate_puzzle uses DEFAULT_CONFIG when no config passed."""

    def test_uses_default_config(self) -> None:
        """Should produce same result as explicitly passing DEFAULT_CONFIG."""
        r1 = validate_puzzle(board_width=9, board_height=9, stone_count=5, solution_depth=3)
        r2 = validate_puzzle(
            board_width=9, board_height=9, stone_count=5, solution_depth=3,
            config=DEFAULT_CONFIG,
        )
        assert r1.is_valid == r2.is_valid


# ==========================================================================
# SGF extraction helpers
# ==========================================================================


class TestExtractBoardSize:
    def test_standard_19(self) -> None:
        assert extract_board_size_from_sgf("(;GM[1]SZ[19]AB[cd])") == 19

    def test_9x9(self) -> None:
        assert extract_board_size_from_sgf("(;GM[1]SZ[9])") == 9

    def test_missing_sz_defaults_19(self) -> None:
        assert extract_board_size_from_sgf("(;GM[1]AB[cd])") == 19

    def test_5x5(self) -> None:
        assert extract_board_size_from_sgf("(;SZ[5])") == 5


class TestCountStones:
    def test_single_black_stone(self) -> None:
        assert count_stones_in_sgf("(;AB[cd])") == 1

    def test_multiple_black_stones(self) -> None:
        assert count_stones_in_sgf("(;AB[cd][ef][gh])") == 3

    def test_black_and_white(self) -> None:
        assert count_stones_in_sgf("(;AB[cd][ef]AW[gh][ij])") == 4

    def test_no_stones(self) -> None:
        assert count_stones_in_sgf("(;GM[1]SZ[9])") == 0

    def test_single_stone_each(self) -> None:
        assert count_stones_in_sgf("(;AB[dd]AW[pp])") == 2


class TestCountSolutionMoves:
    def test_simple_sequence(self) -> None:
        sgf = "(;SZ[9]AB[cd]AW[dd](;B[ce];W[de]))"
        depth = count_solution_moves_in_sgf(sgf)
        assert depth >= 1  # At least one move

    def test_no_moves(self) -> None:
        sgf = "(;SZ[9]AB[cd]AW[dd])"
        depth = count_solution_moves_in_sgf(sgf)
        assert depth == 0


# ==========================================================================
# validate_sgf_puzzle (end-to-end)
# ==========================================================================


class TestValidateSgfPuzzle:
    """Integration tests for validate_sgf_puzzle."""

    def test_valid_puzzle(self) -> None:
        sgf = "(;GM[1]FF[4]SZ[9]AB[cd][ce]AW[dd][de](;B[cf];W[df];B[cg]))"
        result = validate_sgf_puzzle(sgf)
        assert result.is_valid

    def test_empty_sgf(self) -> None:
        result = validate_sgf_puzzle("")
        assert not result.is_valid
        assert "empty" in result.rejection_reason.lower()

    def test_whitespace_only(self) -> None:
        result = validate_sgf_puzzle("   ")
        assert not result.is_valid

    def test_no_stones(self) -> None:
        sgf = "(;GM[1]SZ[9](;B[cd]))"
        result = validate_sgf_puzzle(sgf)
        assert not result.is_valid
        assert "stone" in result.rejection_reason.lower()

    def test_one_stone_below_default_min(self) -> None:
        sgf = "(;GM[1]SZ[9]AB[cd](;B[ce]))"
        result = validate_sgf_puzzle(sgf)
        assert not result.is_valid
        assert "minimum is 2" in result.rejection_reason

    def test_custom_config_min_stones_0(self) -> None:
        """Passing min_stones=0 config allows puzzle with 0 stones."""
        config = PuzzleValidationConfig(min_stones=0)
        sgf = "(;GM[1]SZ[9](;B[cd]))"
        result = validate_sgf_puzzle(sgf, config=config)
        assert result.is_valid

    def test_board_too_small(self) -> None:
        sgf = "(;GM[1]SZ[3]AB[aa][ab]AW[ba][bb](;B[ac]))"
        result = validate_sgf_puzzle(sgf)
        assert not result.is_valid
        assert "below minimum" in result.rejection_reason


# ==========================================================================
# DEFAULT_CONFIG loaded from config file
# ==========================================================================


class TestDefaultConfig:
    """Verify DEFAULT_CONFIG is loaded from config/puzzle-validation.json."""

    def test_default_config_is_loaded(self) -> None:
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, PuzzleValidationConfig)

    def test_default_config_min_stones(self) -> None:
        assert DEFAULT_CONFIG.min_stones == 2

    def test_default_config_min_solution_depth(self) -> None:
        assert DEFAULT_CONFIG.min_solution_depth == 1

    def test_default_config_max_solution_depth(self) -> None:
        assert DEFAULT_CONFIG.max_solution_depth == 30

    def test_default_config_board_range(self) -> None:
        assert DEFAULT_CONFIG.min_board_size == 5
        assert DEFAULT_CONFIG.max_board_size == 19
