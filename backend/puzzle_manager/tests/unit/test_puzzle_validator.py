"""
Unit tests for PuzzleValidator.

Tests follow TDD approach - written before implementation.
Covers all validation rules defined in spec.md FR-001 to FR-009.
"""


import pytest

from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleData,
    PuzzleValidator,
    RejectionReason,
    ValidationConfig,
    ValidationResult,
    validate_puzzle,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_puzzle() -> PuzzleData:
    """A valid 9x9 puzzle with solution."""
    return PuzzleData(
        board_width=9,
        board_height=9,
        black_stones=[(2, 2), (3, 3), (4, 2)],
        white_stones=[(2, 3), (3, 4)],
        has_solution=True,
        solution_depth=8,
        player_to_move="B",
    )


@pytest.fixture
def validator() -> PuzzleValidator:
    """Validator with default config."""
    return PuzzleValidator()


# =============================================================================
# T004: Valid square board (9×9) passes validation
# =============================================================================


class TestValidSquareBoard:
    """T004: Valid square board passes validation."""

    def test_9x9_board_passes(self, validator: PuzzleValidator) -> None:
        """9x9 board with valid puzzle data passes validation."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True
        assert result.rejection_reason is None

    def test_19x19_board_passes(self, validator: PuzzleValidator) -> None:
        """19x19 standard board passes validation."""
        puzzle = PuzzleData(
            board_width=19,
            board_height=19,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=10,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True

    def test_5x5_minimum_board_passes(self, validator: PuzzleValidator) -> None:
        """5x5 minimum board passes validation (boundary)."""
        puzzle = PuzzleData(
            board_width=5,
            board_height=5,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=3,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T005: Valid non-square board (7×9) passes validation
# =============================================================================


class TestValidNonSquareBoard:
    """T005: Non-square boards are accepted if dimensions valid."""

    def test_7x9_non_square_passes(self, validator: PuzzleValidator) -> None:
        """7x9 partial board passes validation."""
        puzzle = PuzzleData(
            board_width=7,
            board_height=9,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True
        assert result.rejection_reason is None

    def test_9x7_non_square_passes(self, validator: PuzzleValidator) -> None:
        """9x7 partial board passes validation."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=7,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True

    def test_11x13_non_square_passes(self, validator: PuzzleValidator) -> None:
        """11x13 partial board passes validation."""
        puzzle = PuzzleData(
            board_width=11,
            board_height=13,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=8,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T006: Board width below minimum (4×9) is rejected
# =============================================================================


class TestBoardWidthBelowMinimum:
    """T006: Board width below minimum is rejected with clear message."""

    def test_width_4_rejected(self, validator: PuzzleValidator) -> None:
        """4x9 board rejected - width too small."""
        puzzle = PuzzleData(
            board_width=4,
            board_height=9,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "4" in result.rejection_reason
        assert "below minimum" in result.rejection_reason.lower() or "minimum" in result.rejection_reason.lower()

    def test_width_1_rejected(self, validator: PuzzleValidator) -> None:
        """1x9 board rejected - width too small."""
        puzzle = PuzzleData(
            board_width=1,
            board_height=9,
            black_stones=[(0, 1)],
            white_stones=[(0, 2)],
            has_solution=True,
            solution_depth=2,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False


# =============================================================================
# T007: Board height below minimum (9×4) is rejected
# =============================================================================


class TestBoardHeightBelowMinimum:
    """T007: Board height below minimum is rejected with clear message."""

    def test_height_4_rejected(self, validator: PuzzleValidator) -> None:
        """9x4 board rejected - height too small."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=4,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "4" in result.rejection_reason
        assert "height" in result.rejection_reason.lower() or "dimension" in result.rejection_reason.lower()

    def test_height_3_rejected(self, validator: PuzzleValidator) -> None:
        """9x3 board rejected - height too small."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=3,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 1)],
            has_solution=True,
            solution_depth=3,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False


# =============================================================================
# T008: Board dimension above maximum (20×19) is rejected
# =============================================================================


class TestBoardDimensionAboveMaximum:
    """T008: Board dimension above maximum is rejected."""

    def test_width_20_rejected(self, validator: PuzzleValidator) -> None:
        """20x19 board rejected - width too large."""
        puzzle = PuzzleData(
            board_width=20,
            board_height=19,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "20" in result.rejection_reason

    def test_height_25_rejected(self, validator: PuzzleValidator) -> None:
        """19x25 board rejected - height too large."""
        puzzle = PuzzleData(
            board_width=19,
            board_height=25,
            black_stones=[(1, 1), (2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=5,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "25" in result.rejection_reason


# =============================================================================
# T009: Puzzle without solution is rejected when min_solution_depth >= 1
# =============================================================================


class TestSolutionRequired:
    """T009: Puzzles without solution are rejected when required."""

    def test_no_solution_rejected(self, validator: PuzzleValidator) -> None:
        """Puzzle with has_solution=False is rejected."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=False,
            solution_depth=None,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "no solution" in result.rejection_reason.lower()


# =============================================================================
# T009a: Puzzle without solution is ACCEPTED when min_solution_depth=0
# =============================================================================


class TestSolutionNotRequired:
    """T009a: Puzzles without solution accepted when depth requirement is 0."""

    def test_no_solution_accepted_when_min_depth_zero(self) -> None:
        """Puzzle with has_solution=False is accepted when min_solution_depth=0."""
        config = ValidationConfig(min_solution_depth=0)
        validator = PuzzleValidator(config)

        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=False,
            solution_depth=None,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T010: Puzzle with insufficient stones (1 stone) is rejected
# =============================================================================


class TestInsufficientStones:
    """T010: Puzzles with too few stones are rejected."""

    def test_one_stone_rejected(self, validator: PuzzleValidator) -> None:
        """Puzzle with only 1 stone is rejected."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2)],
            white_stones=[],
            has_solution=True,
            solution_depth=1,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "1" in result.rejection_reason
        assert "stone" in result.rejection_reason.lower()

    def test_zero_stones_rejected(self, validator: PuzzleValidator) -> None:
        """Puzzle with no stones is rejected."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[],
            white_stones=[],
            has_solution=True,
            solution_depth=1,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False

    def test_two_stones_passes(self, validator: PuzzleValidator) -> None:
        """Puzzle with exactly 2 stones passes (boundary)."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2)],
            white_stones=[(3, 3)],
            has_solution=True,
            solution_depth=3,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T011: Puzzle with solution depth exceeding max is rejected
# =============================================================================


class TestSolutionDepthExceedsMax:
    """T011: Puzzles with solution depth exceeding max are rejected."""

    def test_depth_35_rejected_default_max_30(self, validator: PuzzleValidator) -> None:
        """Solution depth 35 exceeds default max 30."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=35,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "35" in result.rejection_reason
        assert "depth" in result.rejection_reason.lower() or "exceeds" in result.rejection_reason.lower()

    def test_depth_100_rejected(self, validator: PuzzleValidator) -> None:
        """Very deep solution is rejected."""
        puzzle = PuzzleData(
            board_width=19,
            board_height=19,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=100,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False


# =============================================================================
# T012: Boundary condition - solution depth exactly equals max is accepted
# =============================================================================


class TestSolutionDepthBoundary:
    """T012: Solution depth at exactly max is accepted (inclusive)."""

    def test_depth_30_accepted_default_max_30(self, validator: PuzzleValidator) -> None:
        """Solution depth 30 equals default max 30 - should pass."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=30,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True

    def test_depth_none_accepted(self, validator: PuzzleValidator) -> None:
        """Solution depth None (unknown) is accepted."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=None,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T013: ValidationConfig.from_dict() parses JSON correctly
# =============================================================================


class TestValidationConfigFromDict:
    """T013: ValidationConfig parses dictionary (JSON) correctly."""

    def test_from_dict_all_fields(self) -> None:
        """from_dict parses all fields correctly."""
        data = {
            "min_board_dimension": 7,
            "max_board_dimension": 13,
            "min_solution_depth": 0,
            "min_stones": 3,
            "max_solution_depth": 20,
        }
        config = ValidationConfig.from_dict(data)
        assert config.min_board_dimension == 7
        assert config.max_board_dimension == 13
        assert config.min_solution_depth == 0
        assert config.min_stones == 3
        assert config.max_solution_depth == 20

    def test_from_dict_missing_required_key_raises(self) -> None:
        """from_dict raises KeyError when required v2 keys are missing."""
        with pytest.raises(KeyError):
            ValidationConfig.from_dict({"max_solution_depth": 12})

    def test_from_dict_empty_raises(self) -> None:
        """from_dict with empty dict raises KeyError."""
        with pytest.raises(KeyError):
            ValidationConfig.from_dict({})

    def test_from_dict_v1_backward_compat(self) -> None:
        """from_dict maps v1.0 require_solution to min_solution_depth."""
        base = {"min_board_dimension": 5, "max_board_dimension": 19, "max_solution_depth": 30}
        data = {**base, "require_solution": False}
        config = ValidationConfig.from_dict(data)
        assert config.min_solution_depth == 0

        data_true = {**base, "require_solution": True}
        config_true = ValidationConfig.from_dict(data_true)
        assert config_true.min_solution_depth == 1

    def test_from_dict_v1_require_initial_stones_false(self) -> None:
        """from_dict maps v1.0 require_initial_stones=False to min_stones=0."""
        base = {"min_board_dimension": 5, "max_board_dimension": 19, "max_solution_depth": 30}
        data = {**base, "require_initial_stones": False}
        config = ValidationConfig.from_dict(data)
        assert config.min_stones == 0

    def test_from_dict_v1_require_initial_stones_true(self) -> None:
        """from_dict maps v1.0 require_initial_stones=True to min_stones=2."""
        base = {"min_board_dimension": 5, "max_board_dimension": 19, "max_solution_depth": 30}
        data = {**base, "require_initial_stones": True}
        config = ValidationConfig.from_dict(data)
        assert config.min_stones == 2

    def test_from_dict_v2_takes_precedence_over_v1(self) -> None:
        """v2.0 fields take precedence over v1.0 fields when both present."""
        data = {
            "min_board_dimension": 5,
            "max_board_dimension": 19,
            "max_solution_depth": 30,
            "require_solution": True,
            "min_solution_depth": 3,
            "require_initial_stones": False,
            "min_stones": 5,
        }
        config = ValidationConfig.from_dict(data)
        # v2.0 values should be used
        assert config.min_solution_depth == 3
        assert config.min_stones == 5


# =============================================================================
# T014: ValidationConfig.merge() applies overrides correctly
# =============================================================================


class TestValidationConfigMerge:
    """T014: ValidationConfig.merge() applies overrides correctly."""

    def test_merge_partial_overrides(self) -> None:
        """merge applies only specified overrides."""
        base = ValidationConfig(
            min_board_dimension=5,
            max_board_dimension=19,
            min_solution_depth=1,
            min_stones=2,
            max_solution_depth=30,
        )
        overrides = {"max_solution_depth": 12, "min_stones": 3}
        merged = base.merge(overrides)

        # Overridden
        assert merged.max_solution_depth == 12
        assert merged.min_stones == 3
        # Unchanged
        assert merged.min_board_dimension == 5
        assert merged.max_board_dimension == 19
        assert merged.min_solution_depth == 1

    def test_merge_empty_overrides(self) -> None:
        """merge with empty dict returns equivalent config."""
        base = ValidationConfig(max_solution_depth=15)
        merged = base.merge({})
        assert merged.max_solution_depth == 15
        assert merged.min_board_dimension == base.min_board_dimension

    def test_merge_returns_new_instance(self) -> None:
        """merge returns a new config instance, not mutating original."""
        base = ValidationConfig(max_solution_depth=30)
        merged = base.merge({"max_solution_depth": 12})
        assert base.max_solution_depth == 30  # original unchanged
        assert merged.max_solution_depth == 12  # new instance


# =============================================================================
# T039-T040: Config override tests for max_depth
# =============================================================================


class TestConfigOverrides:
    """T039-T041: Tests for per-source config overrides."""

    def test_max_depth_12_rejects_15_move_solution(self) -> None:
        """T039: Validator with max_depth=12 rejects 15-move solution."""
        config = ValidationConfig(max_solution_depth=12)
        validator = PuzzleValidator(config)

        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=15,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "15" in result.rejection_reason

    def test_max_depth_30_accepts_15_move_solution(self) -> None:
        """T040: Validator with max_depth=30 accepts 15-move solution."""
        config = ValidationConfig(max_solution_depth=30)
        validator = PuzzleValidator(config)

        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=15,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True


# =============================================================================
# T041: Verify adapter uses defaults when no config override
# =============================================================================


class TestAdapterDefaults:
    """T041: Test that adapter without explicit config uses defaults."""

    def test_adapter_uses_default_config_values(self) -> None:
        """Adapter without override uses puzzle-validation.json defaults."""
        # Create validator without any overrides
        validator = PuzzleValidator()
        config = validator.config

        # Verify defaults from puzzle-validation.json are loaded
        assert config.min_board_dimension == 5
        assert config.max_board_dimension == 19
        assert config.min_solution_depth == 1
        assert config.min_stones == 2
        assert config.max_solution_depth == 30

    def test_adapter_with_empty_override_uses_defaults(self) -> None:
        """Adapter with empty override dict still uses defaults."""
        validator = PuzzleValidator()
        validator.configure({})
        config = validator.config

        # Empty override should not change defaults
        assert config.min_board_dimension == 5
        assert config.max_solution_depth == 30


# =============================================================================
# T045: Minimal adapter integration pattern
# =============================================================================


class TestMinimalAdapterPattern:
    """T045: Example test showing minimal adapter integration."""

    def test_adapter_integration_pattern(self) -> None:
        """Demonstrates how an adapter uses PuzzleValidator."""
        # Step 1: Create validator (adapter __init__)
        validator = PuzzleValidator()

        # Step 2: Optionally configure with adapter-specific overrides
        validator.configure({"max_solution_depth": 20})

        # Step 3: Convert adapter-specific data to PuzzleData
        puzzle_data = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=10,
        )

        # Step 4: Validate
        result = validator.validate(puzzle_data)

        # Step 5: Check result
        if result:
            # Proceed with valid puzzle
            assert result.is_valid is True
        else:
            # Skip invalid puzzle with reason
            assert result.rejection_reason is not None


# =============================================================================
# ValidationResult tests
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_factory(self) -> None:
        """valid() creates a passing result."""
        result = ValidationResult.valid()
        assert result.is_valid is True
        assert result.rejection_reason is None
        assert result.warnings == []

    def test_valid_with_warnings(self) -> None:
        """valid() can include warnings."""
        result = ValidationResult.valid(warnings=["Low stone count"])
        assert result.is_valid is True
        assert "Low stone count" in result.warnings

    def test_invalid_factory(self) -> None:
        """invalid() creates a failing result."""
        result = ValidationResult.invalid("Board too small")
        assert result.is_valid is False
        assert result.rejection_reason == "Board too small"

    def test_bool_conversion_valid(self) -> None:
        """Valid result is truthy."""
        result = ValidationResult.valid()
        assert bool(result) is True
        assert result  # Can use in if statement

    def test_bool_conversion_invalid(self) -> None:
        """Invalid result is falsy."""
        result = ValidationResult.invalid("Error")
        assert bool(result) is False
        if not result:
            pass  # Can use in if statement


# =============================================================================
# PuzzleData tests
# =============================================================================


class TestPuzzleData:
    """Tests for PuzzleData dataclass."""

    def test_total_stones_property(self) -> None:
        """total_stones returns sum of black and white stones."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(1, 1), (2, 2), (3, 3)],
            white_stones=[(4, 4), (5, 5)],
            has_solution=True,
        )
        assert puzzle.total_stones == 5

    def test_is_square_true(self) -> None:
        """is_square returns True for square boards."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(1, 1)],
            white_stones=[(2, 2)],
            has_solution=True,
        )
        assert puzzle.is_square is True

    def test_is_square_false(self) -> None:
        """is_square returns False for non-square boards."""
        puzzle = PuzzleData(
            board_width=7,
            board_height=9,
            black_stones=[(1, 1)],
            white_stones=[(2, 2)],
            has_solution=True,
        )
        assert puzzle.is_square is False


# =============================================================================
# validate_puzzle convenience function
# =============================================================================


class TestValidatePuzzleFunction:
    """Tests for validate_puzzle() convenience function."""

    def test_validate_puzzle_with_defaults(self) -> None:
        """validate_puzzle uses default config."""
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=5,
        )
        result = validate_puzzle(puzzle)
        assert result.is_valid is True

    def test_validate_puzzle_with_custom_config(self) -> None:
        """validate_puzzle accepts custom config."""
        config = ValidationConfig(max_solution_depth=10)
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=15,
        )
        result = validate_puzzle(puzzle, config)
        assert result.is_valid is False


# =============================================================================
# T048: ValidationStatsCollector Tests
# =============================================================================


class TestValidationStatsCollector:
    """T048-T053: Tests for ValidationStatsCollector."""

    def test_initial_state_empty(self) -> None:
        """T048: New collector has zero counts."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        stats = collector.get_summary()

        assert stats["total"] == 0
        assert stats["valid"] == 0
        assert stats["invalid"] == 0
        assert stats["by_reason"] == {}

    def test_record_valid_increments_valid_count(self) -> None:
        """Valid puzzle increments valid counter."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        result = ValidationResult.valid()

        collector.record(result)
        stats = collector.get_summary()

        assert stats["total"] == 1
        assert stats["valid"] == 1
        assert stats["invalid"] == 0

    def test_record_invalid_increments_reason_count(self) -> None:
        """Invalid puzzle increments invalid counter and reason breakdown."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        result = ValidationResult.invalid("Board too small")

        collector.record(result)
        stats = collector.get_summary()

        assert stats["total"] == 1
        assert stats["valid"] == 0
        assert stats["invalid"] == 1
        assert stats["by_reason"]["Board too small"] == 1

    def test_multiple_rejections_by_reason(self) -> None:
        """Multiple rejections are tracked by reason."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()

        # Record various rejections
        collector.record(ValidationResult.invalid("Board too small"))
        collector.record(ValidationResult.invalid("Board too small"))
        collector.record(ValidationResult.invalid("No solution"))
        collector.record(ValidationResult.valid())

        stats = collector.get_summary()

        assert stats["total"] == 4
        assert stats["valid"] == 1
        assert stats["invalid"] == 3
        assert stats["by_reason"]["Board too small"] == 2
        assert stats["by_reason"]["No solution"] == 1

    def test_acceptance_rate_calculation(self) -> None:
        """acceptance_rate returns correct percentage."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()

        collector.record(ValidationResult.valid())
        collector.record(ValidationResult.valid())
        collector.record(ValidationResult.invalid("Too small"))
        collector.record(ValidationResult.invalid("No solution"))

        assert collector.acceptance_rate == 50.0

    def test_acceptance_rate_zero_total(self) -> None:
        """acceptance_rate returns 0.0 when no puzzles recorded."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        assert collector.acceptance_rate == 0.0

    def test_reset_clears_all_stats(self) -> None:
        """reset() clears all collected statistics."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        collector.record(ValidationResult.valid())
        collector.record(ValidationResult.invalid("Error"))

        collector.reset()
        stats = collector.get_summary()

        assert stats["total"] == 0
        assert stats["valid"] == 0
        assert stats["by_reason"] == {}

    def test_log_summary_returns_formatted_string(self) -> None:
        """log_summary() returns human-readable summary."""
        from backend.puzzle_manager.core.validation_stats import (
            ValidationStatsCollector,
        )

        collector = ValidationStatsCollector()
        collector.record(ValidationResult.valid())
        collector.record(ValidationResult.invalid("Board too small"))

        summary = collector.log_summary()

        assert "Total: 2" in summary
        assert "Valid: 1" in summary
        assert "Invalid: 1" in summary
        assert "Board too small: 1" in summary


# =============================================================================
# Tests for SOLUTION_TOO_SHALLOW rejection (v2.0)
# =============================================================================


class TestSolutionTooShallow:
    """Puzzles with solution depth below min_solution_depth are rejected."""

    def test_depth_below_min_rejected(self) -> None:
        """Puzzle with depth 1 rejected when min_solution_depth=3."""
        config = ValidationConfig(min_solution_depth=3)
        validator = PuzzleValidator(config)
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=1,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "below minimum" in result.rejection_reason.lower()

    def test_depth_at_min_passes(self) -> None:
        """Puzzle with depth 3 passes when min_solution_depth=3."""
        config = ValidationConfig(min_solution_depth=3)
        validator = PuzzleValidator(config)
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=3,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is True

    def test_no_solution_vs_shallow(self) -> None:
        """Depth=0 with has_solution=False gives NO_SOLUTION, not SHALLOW."""
        config = ValidationConfig(min_solution_depth=3)
        validator = PuzzleValidator(config)
        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=False,
            solution_depth=0,
        )
        result = validator.validate(puzzle)
        assert result.is_valid is False
        assert "no solution" in result.rejection_reason.lower()

    def test_rejection_reason_enum_value(self) -> None:
        """SOLUTION_TOO_SHALLOW has correct enum value."""
        assert RejectionReason.SOLUTION_TOO_SHALLOW == 450


# =============================================================================
# validate_sgf convenience function tests
# =============================================================================


class TestValidateSgf:
    """Tests for the centralized validate_sgf convenience function.

    This function replaces the duplicated _validate_sgf methods that
    existed in GoProblems, Kisvadim, URL, and TravisGK adapters.
    """

    def test_valid_sgf_passes(self) -> None:
        """Valid SGF with solution tree passes validation."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        sgf = (
            "(;GM[1]FF[4]SZ[9]"
            "AB[cd][ce][cf]AW[dd][de][df]"
            "(;B[cg];W[dg];B[ch]))"
        )
        result = validate_sgf(sgf)
        assert result.is_valid is True
        assert result.rejection_reason is None

    def test_no_solution_rejected(self) -> None:
        """SGF without solution moves is rejected."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        sgf = "(;GM[1]FF[4]SZ[9]AB[cd][ce]AW[dd][de])"
        result = validate_sgf(sgf)
        assert result.is_valid is False
        assert "solution" in result.rejection_reason.lower()

    def test_no_stones_rejected(self) -> None:
        """SGF with no initial stones is rejected (below min_stones)."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        sgf = "(;GM[1]FF[4]SZ[9](;B[cd]))"
        result = validate_sgf(sgf)
        assert result.is_valid is False
        assert "stone" in result.rejection_reason.lower()

    def test_unparseable_sgf_rejected(self) -> None:
        """Malformed SGF that cannot be parsed is rejected (not silently accepted)."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        result = validate_sgf("not valid sgf at all")
        assert result.is_valid is False
        assert "sgf_parse_error" in result.rejection_reason

    def test_empty_sgf_rejected(self) -> None:
        """Empty string is rejected with sgf_parse_error."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        result = validate_sgf("")
        assert result.is_valid is False
        assert "sgf_parse_error" in result.rejection_reason

    def test_whitespace_only_sgf_rejected(self) -> None:
        """Whitespace-only string is rejected."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        result = validate_sgf("   \n  ")
        assert result.is_valid is False
        assert "sgf_parse_error" in result.rejection_reason

    def test_custom_config_override(self) -> None:
        """Custom ValidationConfig is respected."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        # SGF with a 5x5 board — passes with default (min=5), fails with min=7
        sgf = "(;GM[1]FF[4]SZ[5]AB[bb][bc]AW[cb][cc](;B[ba]))"
        result_default = validate_sgf(sgf)
        assert result_default.is_valid is True

        strict_config = ValidationConfig(min_board_dimension=7)
        result_strict = validate_sgf(sgf, config=strict_config)
        assert result_strict.is_valid is False
        assert "board" in result_strict.rejection_reason.lower()

    def test_solution_depth_computed_correctly(self) -> None:
        """Solution depth is correctly measured from the tree."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        # 3-move deep solution tree
        sgf = (
            "(;GM[1]FF[4]SZ[9]"
            "AB[cd][ce][cf]AW[dd][de][df]"
            "(;B[cg];W[dg];B[ch]))"
        )
        # max_solution_depth=2 should reject a 3-deep tree
        shallow_config = ValidationConfig(max_solution_depth=2)
        result = validate_sgf(sgf, config=shallow_config)
        assert result.is_valid is False
        assert "depth" in result.rejection_reason.lower()

    def test_returns_validation_result_type(self) -> None:
        """validate_sgf returns a ValidationResult instance."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        sgf = "(;GM[1]FF[4]SZ[9]AB[cd][ce]AW[dd][de](;B[cf]))"
        result = validate_sgf(sgf)
        assert isinstance(result, ValidationResult)

    def test_bool_behavior(self) -> None:
        """ValidationResult supports bool() — True for valid, False for invalid."""
        from backend.puzzle_manager.core.puzzle_validator import validate_sgf

        valid_sgf = "(;GM[1]FF[4]SZ[9]AB[cd][ce]AW[dd][de](;B[cf]))"
        assert bool(validate_sgf(valid_sgf)) is True

        invalid_sgf = "garbage"
        assert bool(validate_sgf(invalid_sgf)) is False
