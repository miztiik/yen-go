"""
Shared puzzle validation for all download tools.

Provides source-agnostic validation rules that any importer can use
by passing normalized values (board size, stone count, solution info).

Also includes SGF extraction helpers for importers that work with
raw SGF strings (syougo, t-dragon, tsumego_hero).

Design decisions (v2.0):
- min_solution_depth replaces require_solution + has_solution:
  depth >= 1 is equivalent to "solution exists". Single range
  [min_solution_depth, max_solution_depth] is the canonical form.
- min_stones replaces require_initial_stones:
  count is strictly more informative than presence. min_stones=2
  is the Go-valid minimum (attacker + defender).
- Config loaded from config/puzzle-validation.json when available,
  with hardcoded fallback defaults.

Usage:
    from tools.core.validation import validate_puzzle, PuzzleValidationConfig

    # Option 1: Pass extracted values directly
    result = validate_puzzle(
        board_width=9,
        board_height=9,
        stone_count=5,
        solution_depth=6,
    )

    # Option 2: Validate raw SGF string (extracts values automatically)
    result = validate_sgf_puzzle(sgf_content)

    if not result.is_valid:
        print(f"Rejected: {result.rejection_reason}")
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("tools.core.validation")


@dataclass
class PuzzleValidationResult:
    """Result of puzzle validation."""

    is_valid: bool
    rejection_reason: str | None = None

    @classmethod
    def valid(cls) -> PuzzleValidationResult:
        """Create a valid result."""
        return cls(is_valid=True)

    @classmethod
    def invalid(cls, reason: str) -> PuzzleValidationResult:
        """Create an invalid result with rejection reason."""
        return cls(is_valid=False, rejection_reason=reason)


@dataclass
class PuzzleValidationConfig:
    """Configuration for puzzle validation rules.

    Attributes:
        min_board_size: Minimum board dimension (width or height).
        max_board_size: Maximum board dimension (width or height).
        min_stones: Minimum total stones required on board (default: 2).
            Replaces the old require_initial_stones boolean.
            min_stones >= 1 implies stones must be present.
        min_solution_depth: Minimum solution depth (default: 1).
            Replaces the old require_solution boolean.
            min_solution_depth >= 1 implies a solution must exist.
            Set to 0 to allow puzzles without solutions.
        max_solution_depth: Maximum allowed solution depth (moves).
            Set to None to disable depth checking.
    """

    min_board_size: int = 5
    max_board_size: int = 19
    min_stones: int = 2
    min_solution_depth: int = 1
    max_solution_depth: int | None = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PuzzleValidationConfig:
        """Create config from dictionary (e.g., loaded from JSON).

        Supports both v2.0 (min_solution_depth, min_stones) and
        v1.0 (require_solution, require_initial_stones) fields
        for backward compatibility.

        Args:
            data: Dictionary with config values. Missing fields use defaults.

        Returns:
            PuzzleValidationConfig instance.
        """
        # Handle v1.0 backward compatibility
        min_solution_depth = data.get("min_solution_depth", None)
        if min_solution_depth is None:
            # Fall back to v1.0 require_solution
            require_solution = data.get("require_solution", True)
            min_solution_depth = 1 if require_solution else 0

        min_stones = data.get("min_stones", None)
        if min_stones is None:
            # Fall back to v1.0 require_initial_stones
            require_initial_stones = data.get("require_initial_stones", True)
            min_stones = 2 if require_initial_stones else 0

        return cls(
            min_board_size=data.get("min_board_dimension", data.get("min_board_size", 5)),
            max_board_size=data.get("max_board_dimension", data.get("max_board_size", 19)),
            min_stones=min_stones,
            min_solution_depth=min_solution_depth,
            max_solution_depth=data.get("max_solution_depth", 30),
        )

    def merge(self, overrides: dict[str, Any]) -> PuzzleValidationConfig:
        """Create new config with overrides applied.

        Args:
            overrides: Dictionary of config values to override.

        Returns:
            New PuzzleValidationConfig with overrides applied.
        """
        return PuzzleValidationConfig(
            min_board_size=overrides.get("min_board_size", self.min_board_size),
            max_board_size=overrides.get("max_board_size", self.max_board_size),
            min_stones=overrides.get("min_stones", self.min_stones),
            min_solution_depth=overrides.get("min_solution_depth", self.min_solution_depth),
            max_solution_depth=overrides.get("max_solution_depth", self.max_solution_depth),
        )


def _load_default_config() -> PuzzleValidationConfig:
    """Load default config from config/puzzle-validation.json.

    Walks up from this file to find the project root (contains config/).
    Falls back to hardcoded defaults if config file not found.

    Returns:
        PuzzleValidationConfig loaded from file or defaults.
    """
    config_rel_path = Path("config/puzzle-validation.json")
    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / config_rel_path
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug(f"Loaded validation config from {config_path}")
                return PuzzleValidationConfig.from_dict(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                break

    logger.debug("Using hardcoded default validation config")
    return PuzzleValidationConfig()


# Default config instance loaded from config/puzzle-validation.json
DEFAULT_CONFIG = _load_default_config()


def validate_puzzle(
    board_width: int,
    board_height: int,
    stone_count: int = 0,
    solution_depth: int | None = None,
    config: PuzzleValidationConfig | None = None,
) -> PuzzleValidationResult:
    """Validate a puzzle using source-agnostic rules.

    Each importer extracts these values from its own format and passes
    them here for universal validation.

    Validation checks (in order):
    1. Board width within [min_board_size, max_board_size]
    2. Board height within [min_board_size, max_board_size]
    3. Stone count >= min_stones (covers "stones present" check)
    4. Solution depth >= min_solution_depth (covers "solution exists" check)
    5. Solution depth <= max_solution_depth (if set)

    Args:
        board_width: Board width (columns).
        board_height: Board height (rows).
        stone_count: Total number of stones on board (black + white).
        solution_depth: Maximum depth of solution tree (moves), or None
            if unknown/not computed.
        config: Validation configuration. Uses DEFAULT_CONFIG if None.

    Returns:
        PuzzleValidationResult indicating pass/fail with reason.
    """
    if config is None:
        config = DEFAULT_CONFIG

    # 1. Board width in range
    if board_width < config.min_board_size:
        return PuzzleValidationResult.invalid(
            f"Board width {board_width} below minimum {config.min_board_size}"
        )
    if board_width > config.max_board_size:
        return PuzzleValidationResult.invalid(
            f"Board width {board_width} exceeds maximum {config.max_board_size}"
        )

    # 2. Board height in range
    if board_height < config.min_board_size:
        return PuzzleValidationResult.invalid(
            f"Board height {board_height} below minimum {config.min_board_size}"
        )
    if board_height > config.max_board_size:
        return PuzzleValidationResult.invalid(
            f"Board height {board_height} exceeds maximum {config.max_board_size}"
        )

    # 3. Minimum stone count (replaces require_initial_stones)
    if stone_count < config.min_stones:
        return PuzzleValidationResult.invalid(
            f"Only {stone_count} stone(s) on board, minimum is {config.min_stones}"
        )

    # 4. Solution depth range [min_solution_depth, max_solution_depth]
    effective_depth = solution_depth if solution_depth is not None else 0
    if config.min_solution_depth > 0 and effective_depth < config.min_solution_depth:
        return PuzzleValidationResult.invalid(
            f"Solution depth {effective_depth} below minimum {config.min_solution_depth}"
            if effective_depth > 0
            else "No solution found"
        )

    if (
        config.max_solution_depth is not None
        and solution_depth is not None
        and solution_depth > config.max_solution_depth
    ):
        return PuzzleValidationResult.invalid(
            f"Solution too deep ({solution_depth} moves, "
            f"max {config.max_solution_depth})"
        )

    return PuzzleValidationResult.valid()


# ---------------------------------------------------------------------------
# SGF extraction helpers
# ---------------------------------------------------------------------------
# For importers that work with raw SGF strings (syougo, t-dragon,
# tsumego_hero). These use simple regex to extract the normalized
# values without a full SGF parser.

# Matches SZ[19] or SZ[9]
_SZ_PATTERN = re.compile(r"SZ\[(\d+)\]")

# Matches individual stone coordinates within AB[] or AW[] properties
_STONE_COORD_PATTERN = re.compile(r"(?:AB|AW)(?:\[([a-s]{2})\])+")
_AB_AW_BLOCK_PATTERN = re.compile(r"(?:AB|AW)((?:\[[a-s]{2}\])+)")

# Matches move nodes like ;B[cd] or ;W[ef]
_MOVE_PATTERN = re.compile(r";[BW]\[[a-s]{2}\]")


def extract_board_size_from_sgf(sgf: str) -> int:
    """Extract board size from SGF SZ[] property.

    Args:
        sgf: Raw SGF string.

    Returns:
        Board size (defaults to 19 if SZ not found).
    """
    match = _SZ_PATTERN.search(sgf)
    return int(match.group(1)) if match else 19


def count_stones_in_sgf(sgf: str) -> int:
    """Count total initial stones (AB[] + AW[]) in an SGF string.

    Counts individual stone coordinates in all AB[] and AW[] properties.
    This replaces the old has_initial_stones_in_sgf() boolean check
    with an actual count, enabling min_stones validation.

    Args:
        sgf: Raw SGF string.

    Returns:
        Total number of initial stones (black + white).
    """
    total = 0
    for match in _AB_AW_BLOCK_PATTERN.finditer(sgf):
        coords_block = match.group(1)
        # Each coordinate is [xy] = 4 chars
        total += coords_block.count("][") + 1
    return total


def count_solution_moves_in_sgf(sgf: str) -> int:
    """Compute the maximum solution depth using tree parsing.

    This replaces the old regex-based flat count which incorrectly
    summed ALL move nodes across all branches (e.g., returning 44
    for puzzle 6405 whose longest path is only 15 moves).

    Falls back to the legacy regex count if tree parsing fails.

    Args:
        sgf: Raw SGF string.

    Returns:
        Maximum depth of any single path in the solution tree.
    """
    try:
        from tools.core.sgf_analysis import max_branch_depth
        from tools.core.sgf_parser import parse_sgf

        tree = parse_sgf(sgf)
        return max_branch_depth(tree.solution_tree)
    except Exception as e:
        logger.debug(
            f"Tree parser failed, falling back to regex count: {e}"
        )
        return len(_MOVE_PATTERN.findall(sgf))


def validate_sgf_puzzle(
    sgf: str,
    config: PuzzleValidationConfig | None = None,
) -> PuzzleValidationResult:
    """Validate a puzzle from its raw SGF string.

    Convenience wrapper that extracts values from SGF and validates
    in one call. Suitable for importers that have raw SGF content
    (syougo, t-dragon, tsumego_hero).

    Args:
        sgf: Raw SGF string.
        config: Validation configuration. Uses DEFAULT_CONFIG if None.

    Returns:
        PuzzleValidationResult indicating pass/fail with reason.
    """
    if not sgf or not sgf.strip():
        return PuzzleValidationResult.invalid("Empty SGF content")

    board_size = extract_board_size_from_sgf(sgf)
    stone_count = count_stones_in_sgf(sgf)
    move_count = count_solution_moves_in_sgf(sgf)

    return validate_puzzle(
        board_width=board_size,
        board_height=board_size,
        stone_count=stone_count,
        solution_depth=move_count,
        config=config,
    )


def validate_sgf_puzzle_from_tree(
    tree: object,
    config: PuzzleValidationConfig | None = None,
) -> PuzzleValidationResult:
    """Validate a puzzle from an already-parsed SgfTree.

    Avoids double-parsing for tools that already called ``parse_sgf()``.
    Accepts ``object`` type to avoid hard import dependency on sgf_parser.

    Args:
        tree: Parsed SgfTree object (from ``tools.core.sgf_parser.parse_sgf``).
        config: Validation configuration. Uses DEFAULT_CONFIG if None.

    Returns:
        PuzzleValidationResult indicating pass/fail with reason.
    """
    from tools.core.sgf_analysis import max_branch_depth

    board_size = getattr(tree, "board_size", 19)
    black_stones = getattr(tree, "black_stones", [])
    white_stones = getattr(tree, "white_stones", [])
    stone_count = len(black_stones) + len(white_stones)
    solution_tree = getattr(tree, "solution_tree", None)
    has_sol = bool(solution_tree and getattr(solution_tree, "children", []))
    depth = max_branch_depth(solution_tree) if has_sol and solution_tree else 0

    return validate_puzzle(
        board_width=board_size,
        board_height=board_size,
        stone_count=stone_count,
        solution_depth=depth,
        config=config,
    )
