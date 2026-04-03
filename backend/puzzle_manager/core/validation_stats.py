"""
Validation statistics collector for puzzle validation.

Tracks validation outcomes and provides summary statistics.
Separated from PuzzleValidator per SRP (spec-108 SA1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .puzzle_validator import ValidationResult


@dataclass
class ValidationStatsCollector:
    """Collects and aggregates puzzle validation statistics.

    Tracks validation outcomes with breakdown by rejection reason.
    Note: This class is NOT thread-safe. For concurrent use, external
    synchronization is required.

    Usage:
        collector = ValidationStatsCollector()

        for puzzle in puzzles:
            result = validator.validate(puzzle)
            collector.record(result)

        logger.info(collector.log_summary())
    """

    _total: int = field(default=0, init=False)
    _valid: int = field(default=0, init=False)
    _by_reason: dict[str, int] = field(default_factory=dict, init=False)

    def record(self, result: ValidationResult) -> None:
        """Record a validation result.

        Args:
            result: ValidationResult from PuzzleValidator.validate()
        """
        self._total += 1

        if result.is_valid:
            self._valid += 1
        else:
            reason = result.rejection_reason or "Unknown"
            self._by_reason[reason] = self._by_reason.get(reason, 0) + 1

    def get_summary(self) -> dict:
        """Get summary statistics as dictionary.

        Returns:
            Dictionary with keys:
                - total: Total puzzles validated
                - valid: Count of valid puzzles
                - invalid: Count of invalid puzzles
                - by_reason: Breakdown of rejections by reason
        """
        return {
            "total": self._total,
            "valid": self._valid,
            "invalid": self._total - self._valid,
            "by_reason": dict(self._by_reason),
        }

    @property
    def acceptance_rate(self) -> float:
        """Calculate acceptance rate as percentage.

        Returns:
            Percentage of valid puzzles (0.0 to 100.0).
            Returns 0.0 if no puzzles have been recorded.
        """
        if self._total == 0:
            return 0.0
        return (self._valid / self._total) * 100.0

    def reset(self) -> None:
        """Reset all statistics to zero."""
        self._total = 0
        self._valid = 0
        self._by_reason.clear()

    def log_summary(self) -> str:
        """Generate human-readable summary for logging.

        Returns:
            Multi-line string with statistics summary.
        """
        lines = [
            f"Total: {self._total}",
            f"Valid: {self._valid}",
            f"Invalid: {self._total - self._valid}",
            f"Acceptance Rate: {self.acceptance_rate:.1f}%",
        ]

        if self._by_reason:
            lines.append("Rejections by reason:")
            for reason, count in sorted(self._by_reason.items()):
                lines.append(f"  {reason}: {count}")

        return "\n".join(lines)
