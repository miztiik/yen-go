"""Backward-compatibility re-export.

G10: Renamed to difficulty_estimate.py to match class name.
This file re-exports for any code still importing by old module name.
"""

from .difficulty_estimate import DifficultyEstimate

__all__ = ["DifficultyEstimate"]
