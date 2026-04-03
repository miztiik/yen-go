"""
Move alternation detection for Go/Tsumego puzzles.

Detects whether a sequence of moves properly alternates between players (B/W),
which is required by Go rules. Same-color consecutive moves in a solution
indicate miai (alternative solutions) that should be SGF variations, not
sequential moves.

This module is adapter-agnostic and can be used by:
- PuzzleValidator: Automatic validation for all adapters
- Adapters: Upstream detection to create proper SGF variations
- Enrichment: Enhanced move order flexibility detection

Spec 117: Solution Move Alternation Detection

Example:
    from backend.puzzle_manager.core.move_alternation import (
        MoveAlternationDetector,
        MoveAlternationResult,
    )

    detector = MoveAlternationDetector()

    # Properly alternating sequence
    result = detector.analyze([("B", "aa"), ("W", "bb"), ("B", "cc")])
    assert result == MoveAlternationResult.ALTERNATING

    # Miai pattern - same color consecutive (should be variations)
    result = detector.analyze([("B", "aa"), ("B", "bb")])
    assert result == MoveAlternationResult.MIAI
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class MoveAlternationResult(Enum):
    """Result of move alternation analysis.

    Values:
        ALTERNATING: Moves properly alternate between B/W (valid sequence)
        MIAI: All moves are same color - indicates alternative solutions
        NON_ALTERNATING: Mixed pattern with some same-color consecutive moves
        SINGLE_MOVE: Only one move in sequence (trivially valid)
        EMPTY: No moves to analyze
        INVALID: Malformed move data
    """
    ALTERNATING = auto()      # B-W-B-W... or W-B-W-B... (valid)
    MIAI = auto()             # B-B-B or W-W-W (all same = alternative solutions)
    NON_ALTERNATING = auto()  # Mixed pattern with errors
    SINGLE_MOVE = auto()      # Only one move (trivially valid)
    EMPTY = auto()            # No moves
    INVALID = auto()          # Malformed data


@dataclass
class MoveAlternationAnalysis:
    """Detailed analysis of move alternation.

    Attributes:
        result: Classification of the move sequence
        move_count: Total number of moves analyzed
        colors: List of colors in sequence order
        violation_indices: Indices where alternation is violated (0-based)
        is_valid_sequence: Whether this represents a valid Go move sequence
        is_miai: Whether this represents alternative solutions (all same color)
    """
    result: MoveAlternationResult
    move_count: int
    colors: list[str]
    violation_indices: list[int]

    @property
    def is_valid_sequence(self) -> bool:
        """Whether this is a valid alternating sequence.

        Single moves and properly alternating sequences are valid.
        Miai patterns are NOT valid as sequential moves (should be variations).
        """
        return self.result in (
            MoveAlternationResult.ALTERNATING,
            MoveAlternationResult.SINGLE_MOVE,
            MoveAlternationResult.EMPTY,
        )

    @property
    def is_miai(self) -> bool:
        """Whether this represents miai (alternative solutions).

        True when all moves are the same color, indicating the source
        provided multiple first-move options rather than a sequence.
        """
        return self.result == MoveAlternationResult.MIAI

    @property
    def first_violation_index(self) -> int | None:
        """Index of first alternation violation, or None if valid."""
        return self.violation_indices[0] if self.violation_indices else None


class MoveAlternationDetector:
    """Detects move alternation patterns in puzzle solutions.

    Go rules require players to alternate turns. When a puzzle solution
    contains consecutive moves by the same player, it typically indicates:

    1. **Miai**: Multiple equally correct first moves (alternative solutions)
       - Should be represented as SGF variations: (;B[aa])(;B[bb])
       - NOT as sequential moves: ;B[aa];B[bb]

    2. **Data Error**: Corrupted or incorrectly parsed solution data

    This detector analyzes move sequences and classifies them to enable:
    - Validation: Reject puzzles with invalid sequences
    - Conversion: Transform miai into proper SGF variations
    - Enrichment: Detect move order flexibility

    Example:
        detector = MoveAlternationDetector()

        # Check a move sequence
        analysis = detector.analyze_detailed([("B", "aa"), ("B", "bb")])
        if analysis.is_miai:
            # Convert to SGF variations instead of sequential
            pass
    """

    def analyze(
        self,
        moves: Sequence[tuple[str, str] | list],
    ) -> MoveAlternationResult:
        """Analyze move sequence for alternation pattern.

        Args:
            moves: Sequence of moves, each as (color, coord) or [color, coord, ...]
                   Color must be "B" or "W".

        Returns:
            MoveAlternationResult classification.

        Example:
            >>> detector = MoveAlternationDetector()
            >>> detector.analyze([("B", "aa"), ("W", "bb")])
            MoveAlternationResult.ALTERNATING
            >>> detector.analyze([("B", "aa"), ("B", "bb")])
            MoveAlternationResult.MIAI
        """
        return self.analyze_detailed(moves).result

    def analyze_detailed(
        self,
        moves: Sequence[tuple[str, str] | list],
    ) -> MoveAlternationAnalysis:
        """Analyze move sequence with detailed results.

        Args:
            moves: Sequence of moves, each as (color, coord) or [color, coord, ...]
                   Color must be "B" or "W".

        Returns:
            MoveAlternationAnalysis with full details.

        Example:
            >>> detector = MoveAlternationDetector()
            >>> analysis = detector.analyze_detailed([("B", "aa"), ("B", "bb"), ("B", "cc")])
            >>> analysis.is_miai
            True
            >>> analysis.colors
            ['B', 'B', 'B']
        """
        # Handle empty sequence
        if not moves:
            return MoveAlternationAnalysis(
                result=MoveAlternationResult.EMPTY,
                move_count=0,
                colors=[],
                violation_indices=[],
            )

        # Extract colors from moves
        colors: list[str] = []
        for move in moves:
            try:
                if isinstance(move, (list, tuple)) and len(move) >= 2:
                    color = move[0]
                    if color in ("B", "W"):
                        colors.append(color)
                    else:
                        # Invalid color
                        return MoveAlternationAnalysis(
                            result=MoveAlternationResult.INVALID,
                            move_count=len(moves),
                            colors=[],
                            violation_indices=[],
                        )
                else:
                    return MoveAlternationAnalysis(
                        result=MoveAlternationResult.INVALID,
                        move_count=len(moves),
                        colors=[],
                        violation_indices=[],
                    )
            except (TypeError, IndexError):
                return MoveAlternationAnalysis(
                    result=MoveAlternationResult.INVALID,
                    move_count=len(moves),
                    colors=[],
                    violation_indices=[],
                )

        # Single move is trivially valid
        if len(colors) == 1:
            return MoveAlternationAnalysis(
                result=MoveAlternationResult.SINGLE_MOVE,
                move_count=1,
                colors=colors,
                violation_indices=[],
            )

        # Find violation indices (where color[i] == color[i-1])
        violations: list[int] = []
        for i in range(1, len(colors)):
            if colors[i] == colors[i - 1]:
                violations.append(i)

        # Classify based on violations
        if not violations:
            # No violations = properly alternating
            return MoveAlternationAnalysis(
                result=MoveAlternationResult.ALTERNATING,
                move_count=len(colors),
                colors=colors,
                violation_indices=[],
            )

        # Check if ALL moves are the same color (miai pattern)
        first_color = colors[0]
        if all(c == first_color for c in colors):
            return MoveAlternationAnalysis(
                result=MoveAlternationResult.MIAI,
                move_count=len(colors),
                colors=colors,
                violation_indices=violations,
            )

        # Mixed pattern - some same-color consecutive moves
        return MoveAlternationAnalysis(
            result=MoveAlternationResult.NON_ALTERNATING,
            move_count=len(colors),
            colors=colors,
            violation_indices=violations,
        )

    def is_valid_sequence(
        self,
        moves: Sequence[tuple[str, str] | list],
    ) -> bool:
        """Check if moves form a valid alternating sequence.

        Convenience method for quick validation.

        Args:
            moves: Sequence of moves.

        Returns:
            True if sequence properly alternates or is single/empty.
            False for miai, non-alternating, or invalid sequences.
        """
        return self.analyze_detailed(moves).is_valid_sequence

    def is_miai(
        self,
        moves: Sequence[tuple[str, str] | list],
    ) -> bool:
        """Check if moves represent miai (alternative solutions).

        Convenience method for adapter conversion logic.

        Args:
            moves: Sequence of moves.

        Returns:
            True if all moves are same color (miai pattern).
        """
        return self.analyze_detailed(moves).is_miai


# Module exports
__all__ = [
    "MoveAlternationDetector",
    "MoveAlternationResult",
    "MoveAlternationAnalysis",
]
