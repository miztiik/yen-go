"""
Centralized puzzle validator for the puzzle manager.

Provides consistent validation across all adapters with configurable rules
loaded from config/puzzle-validation.json (single source of truth, no
hardcoded fallbacks):
- Board dimensions within configured range
- Required solution path existence
- Minimum stone count
- Maximum solution depth

Usage:
    from backend.puzzle_manager.core.puzzle_validator import (
        PuzzleValidator,
        PuzzleData,
    )

    validator = PuzzleValidator()  # Uses config/puzzle-validation.json
    result = validator.validate(puzzle_data)
    if not result:
        print(f"Rejected: {result.rejection_reason}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ValidationConfig:
    """Configuration for puzzle validation rules.

    Attributes:
        min_board_dimension: Minimum allowed board dimension (default: 5)
        max_board_dimension: Maximum allowed board dimension (default: 19)
        min_stones: Minimum total stones required (default: 2)
        min_solution_depth: Minimum solution depth required (default: 1).
            Replaces the old require_solution boolean.
            min_solution_depth >= 1 implies a solution must exist.
            Set to 0 to allow puzzles without solutions.
        max_solution_depth: Maximum allowed solution depth (default: 30)
    """
    min_board_dimension: int = 5
    max_board_dimension: int = 19
    min_stones: int = 2
    min_solution_depth: int = 1
    max_solution_depth: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationConfig:
        """Create config from dictionary (JSON).

        Supports both v2.0 (min_solution_depth, min_stones) and v1.0
        (require_solution, require_initial_stones) fields for backward
        compatibility.

        Args:
            data: Dictionary with config values.

        Returns:
            ValidationConfig instance.
        """
        # Handle v1.0 backward compatibility: require_solution -> min_solution_depth
        min_solution_depth = data.get("min_solution_depth", None)
        if min_solution_depth is None:
            require_solution = data.get("require_solution", True)
            min_solution_depth = 1 if require_solution else 0

        # Handle v1.0 backward compatibility: require_initial_stones -> min_stones
        min_stones = data.get("min_stones", None)
        if min_stones is None:
            require_initial_stones = data.get("require_initial_stones", True)
            min_stones = 2 if require_initial_stones else 0

        return cls(
            min_board_dimension=data["min_board_dimension"],
            max_board_dimension=data["max_board_dimension"],
            min_stones=min_stones,
            min_solution_depth=min_solution_depth,
            max_solution_depth=data["max_solution_depth"],
        )

    def merge(self, overrides: dict[str, Any]) -> ValidationConfig:
        """Create new config with overrides applied.

        Args:
            overrides: Dictionary of config values to override.

        Returns:
            New ValidationConfig with overrides applied.
        """
        return ValidationConfig(
            min_board_dimension=overrides.get("min_board_dimension", self.min_board_dimension),
            max_board_dimension=overrides.get("max_board_dimension", self.max_board_dimension),
            min_stones=overrides.get("min_stones", self.min_stones),
            min_solution_depth=overrides.get("min_solution_depth", self.min_solution_depth),
            max_solution_depth=overrides.get("max_solution_depth", self.max_solution_depth),
        )


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PuzzleData:
    """Adapter-agnostic puzzle data for validation.

    Coordinates are (x, y) tuples where:
    - x: column (0-indexed from left)
    - y: row (0-indexed from top)

    Attributes:
        board_width: Board width (5-19)
        board_height: Board height (5-19)
        black_stones: List of (x, y) positions for black stones
        white_stones: List of (x, y) positions for white stones
        has_solution: Whether puzzle has at least one solution path
        solution_depth: Number of moves in deepest solution path (None if unknown)
        player_to_move: "B" for Black, "W" for White, None if unspecified
    """
    board_width: int
    board_height: int
    black_stones: list[tuple[int, int]]
    white_stones: list[tuple[int, int]]
    has_solution: bool
    solution_depth: int | None = None
    player_to_move: str | None = None

    @property
    def total_stones(self) -> int:
        """Total number of stones on board."""
        return len(self.black_stones) + len(self.white_stones)

    @property
    def is_square(self) -> bool:
        """Whether board is square."""
        return self.board_width == self.board_height


@dataclass
class ValidationResult:
    """Result of puzzle validation.

    Attributes:
        is_valid: Whether puzzle passed all validation checks
        rejection_reason: Human-readable reason for rejection (if invalid)
        warnings: Non-blocking quality warnings
    """
    is_valid: bool
    rejection_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def valid(cls, warnings: list[str] | None = None) -> ValidationResult:
        """Create a passing validation result.

        Args:
            warnings: Optional list of non-blocking warnings.

        Returns:
            ValidationResult with is_valid=True.
        """
        return cls(is_valid=True, rejection_reason=None, warnings=warnings or [])

    @classmethod
    def invalid(cls, reason: str) -> ValidationResult:
        """Create a failing validation result.

        Args:
            reason: Human-readable rejection message.

        Returns:
            ValidationResult with is_valid=False.
        """
        return cls(is_valid=False, rejection_reason=reason, warnings=[])

    def __bool__(self) -> bool:
        """Allow using result in boolean context.

        Returns:
            True if valid, False otherwise.
        """
        return self.is_valid


# =============================================================================
# Rejection Reasons
# =============================================================================


class RejectionReason(IntEnum):
    """Standardized puzzle rejection reasons.

    Uses IntEnum with 100-increments for ordering flexibility.
    This allows inserting new rules between existing ones
    (e.g., 150 between BOARD_TOO_SMALL and BOARD_TOO_LARGE).

    Validation order follows numeric order (100 → 200 → ...).
    """

    # Board dimension rules (100-199)
    BOARD_TOO_SMALL = 100
    BOARD_TOO_LARGE = 200

    # Stone rules (300-399)
    INSUFFICIENT_STONES = 300

    # Solution rules (400-499)
    NO_SOLUTION = 400
    SOLUTION_TOO_SHALLOW = 450
    SOLUTION_TOO_DEEP = 500

    # Structure rules (600+)
    INVALID_STRUCTURE = 600

    def message(self, **kwargs: Any) -> str:
        """Generate human-readable message for this reason.

        Args:
            **kwargs: Values to format into message template.

        Returns:
            Formatted rejection message.
        """
        messages = {
            RejectionReason.BOARD_TOO_SMALL: "Board {dimension} {value} is below minimum {min}",
            RejectionReason.BOARD_TOO_LARGE: "Board {dimension} {value} is above maximum {max}",
            RejectionReason.NO_SOLUTION: "Puzzle has no solution",
            RejectionReason.SOLUTION_TOO_SHALLOW: "Solution depth {depth} is below minimum {min}",
            RejectionReason.INSUFFICIENT_STONES: "Only {count} stone(s) on board, minimum is {min}",
            RejectionReason.SOLUTION_TOO_DEEP: "Solution depth {depth} exceeds maximum {max}",
            RejectionReason.INVALID_STRUCTURE: "Invalid puzzle structure: {detail}",
        }
        return messages[self].format(**kwargs)


# =============================================================================
# Validator
# =============================================================================


class PuzzleValidator:
    """Centralized puzzle validator.

    Validates puzzles against configurable rules:
    - Board dimensions within allowed range
    - Non-square boards allowed if dimensions valid
    - Required solution path
    - Minimum stone count
    - Maximum solution depth

    Example:
        validator = PuzzleValidator()  # Uses default config

        puzzle = PuzzleData(
            board_width=9,
            board_height=9,
            black_stones=[(2, 2), (3, 3)],
            white_stones=[(4, 4)],
            has_solution=True,
            solution_depth=5,
        )

        result = validator.validate(puzzle)
        if not result:
            print(f"Rejected: {result.rejection_reason}")
    """

    # Default config path relative to project root
    _DEFAULT_CONFIG_PATH = Path("config/puzzle-validation.json")

    def __init__(self, config: ValidationConfig | None = None) -> None:
        """Initialize validator with config.

        Args:
            config: Validation config. If None, loads from config/puzzle-validation.json.
        """
        if config is not None:
            self._config = config
        else:
            self._config = self.load_default_config()

    @property
    def config(self) -> ValidationConfig:
        """Current validation configuration."""
        return self._config

    def configure(self, overrides: dict[str, Any]) -> PuzzleValidator:
        """Apply configuration overrides.

        Args:
            overrides: Dictionary of config values to override.

        Returns:
            Self for method chaining.
        """
        self._config = self._config.merge(overrides)
        return self

    def validate(self, puzzle: PuzzleData) -> ValidationResult:
        """Validate a puzzle against configured rules.

        Checks are performed in order:
        1. Board width range
        2. Board height range
        3. Stone count >= min_stones
        4. Solution depth >= min_solution_depth (replaces has_solution check)
        5. Solution depth <= max_solution_depth

        Args:
            puzzle: Puzzle data to validate.

        Returns:
            ValidationResult with pass/fail status and rejection reason.
        """
        # Check board width
        if puzzle.board_width < self._config.min_board_dimension:
            return ValidationResult.invalid(
                RejectionReason.BOARD_TOO_SMALL.message(
                    dimension="width",
                    value=puzzle.board_width,
                    min=self._config.min_board_dimension,
                )
            )

        if puzzle.board_width > self._config.max_board_dimension:
            return ValidationResult.invalid(
                RejectionReason.BOARD_TOO_LARGE.message(
                    dimension="width",
                    value=puzzle.board_width,
                    max=self._config.max_board_dimension,
                )
            )

        # Check board height
        if puzzle.board_height < self._config.min_board_dimension:
            return ValidationResult.invalid(
                RejectionReason.BOARD_TOO_SMALL.message(
                    dimension="height",
                    value=puzzle.board_height,
                    min=self._config.min_board_dimension,
                )
            )

        if puzzle.board_height > self._config.max_board_dimension:
            return ValidationResult.invalid(
                RejectionReason.BOARD_TOO_LARGE.message(
                    dimension="height",
                    value=puzzle.board_height,
                    max=self._config.max_board_dimension,
                )
            )

        # Check stone count
        if puzzle.total_stones < self._config.min_stones:
            return ValidationResult.invalid(
                RejectionReason.INSUFFICIENT_STONES.message(
                    count=puzzle.total_stones,
                    min=self._config.min_stones,
                )
            )

        # Check solution existence and depth range
        # When min_solution_depth > 0, puzzles must have a solution.
        # has_solution is the source's assertion — respect it independently of depth.
        if self._config.min_solution_depth > 0:
            # Reject if source explicitly says no solution
            if not puzzle.has_solution:
                return ValidationResult.invalid(
                    RejectionReason.NO_SOLUTION.message()
                )
            # When solution_depth is None and has_solution is True, the depth is
            # genuinely unknown (not zero) — skip the minimum depth check.
            if puzzle.solution_depth is not None and puzzle.solution_depth < self._config.min_solution_depth:
                return ValidationResult.invalid(
                    RejectionReason.SOLUTION_TOO_SHALLOW.message(
                        depth=puzzle.solution_depth,
                        min=self._config.min_solution_depth,
                    )
                )

        if (
            puzzle.solution_depth is not None
            and puzzle.solution_depth > self._config.max_solution_depth
        ):
            return ValidationResult.invalid(
                RejectionReason.SOLUTION_TOO_DEEP.message(
                    depth=puzzle.solution_depth,
                    max=self._config.max_solution_depth,
                )
            )

        # All checks passed
        warnings = []
        if puzzle.total_stones == self._config.min_stones:
            warnings.append(f"Low stone count: {puzzle.total_stones}")

        return ValidationResult.valid(warnings=warnings if warnings else None)

    @classmethod
    def load_default_config(cls) -> ValidationConfig:
        """Load default validation config from config/puzzle-validation.json.

        Raises FileNotFoundError if config file not found.

        Returns:
            ValidationConfig loaded from file.
        """
        # Try to find config file relative to project root
        # Walk up from this file to find project root (contains config/)
        current = Path(__file__).resolve()
        for parent in current.parents:
            config_path = parent / cls._DEFAULT_CONFIG_PATH
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        data = json.load(f)
                    logger.debug(f"Loaded validation config from {config_path.as_posix()}")
                    return ValidationConfig.from_dict(data)
                except (json.JSONDecodeError, OSError) as e:
                    raise FileNotFoundError(
                        f"Failed to load config from {config_path.as_posix()}: {e}"
                    ) from e

        raise FileNotFoundError(
            f"Required config not found: {cls._DEFAULT_CONFIG_PATH}"
        )


# =============================================================================
# Convenience Functions
# =============================================================================


def validate_puzzle(
    puzzle: PuzzleData,
    config: ValidationConfig | None = None,
) -> ValidationResult:
    """Validate a puzzle (stateless convenience function).

    Args:
        puzzle: Puzzle data to validate.
        config: Optional config override.

    Returns:
        ValidationResult with pass/fail status.
    """
    validator = PuzzleValidator(config)
    return validator.validate(puzzle)


# =============================================================================
# SGF Validation Convenience
# =============================================================================


def _max_solution_depth(game: Any) -> int:
    """Count the maximum solution depth in an SGF game tree.

    Walks the solution_tree (SolutionNode) to find the longest branch.
    The root SolutionNode is a container — its children are the actual
    first moves, so the depth count starts from those children.

    Args:
        game: Parsed SGFGame object from sgf_parser

    Returns:
        Maximum depth of any branch in the solution tree (0 if none).
    """

    def _recurse(node: Any) -> int:
        if not node.children:
            return 0
        return 1 + max(_recurse(child) for child in node.children)

    try:
        return _recurse(game.solution_tree)
    except Exception:
        return 0


def validate_sgf(
    sgf_content: str,
    config: ValidationConfig | None = None,
) -> ValidationResult:
    """Validate raw SGF content against centralized puzzle rules.

    Parses the SGF string to extract board size, stone counts, and solution
    depth, then validates via PuzzleValidator. This eliminates the need for
    each adapter to implement its own SGF-to-PuzzleData conversion.

    On parse failure, returns an invalid result with ``sgf_parse_error``
    rejection reason (fail-fast — if we cannot parse the SGF, we cannot
    validate it, and it will likely fail downstream).

    Args:
        sgf_content: Raw SGF string content.
        config: Optional validation config override.

    Returns:
        ValidationResult with pass/fail status and rejection reason.
    """
    # Lazy import to avoid circular dependency at module load time.
    from backend.puzzle_manager.core.sgf_parser import parse_sgf

    if not sgf_content or not sgf_content.strip():
        return ValidationResult.invalid("sgf_parse_error: empty SGF content")

    try:
        game = parse_sgf(sgf_content)
    except Exception as e:
        logger.warning("SGF parse failure during validation: %s", e)
        return ValidationResult.invalid(f"sgf_parse_error: {e}")

    board_size = game.board_size
    black_stones = [(p.x, p.y) for p in game.black_stones]
    white_stones = [(p.x, p.y) for p in game.white_stones]
    solution_depth = _max_solution_depth(game)

    puzzle_data = PuzzleData(
        board_width=board_size,
        board_height=board_size,
        black_stones=black_stones,
        white_stones=white_stones,
        has_solution=solution_depth > 0,
        solution_depth=solution_depth,
    )

    validator = PuzzleValidator(config)
    return validator.validate(puzzle_data)


__all__ = [
    "PuzzleValidator",
    "PuzzleData",
    "ValidationConfig",
    "ValidationResult",
    "RejectionReason",
    "validate_puzzle",
    "validate_sgf",
]
