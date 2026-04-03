"""EnrichmentRunState — mutable state carrier for the enrichment pipeline.

Replaces 9 bare ``_*`` variable declarations in ``enrich_single_puzzle()``
with a single ``@dataclass`` instance (MH-3).

Fields mirror the original variable names (without leading underscores).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class EnrichmentRunState:
    """Mutable state accumulated during a single-puzzle enrichment run.

    All fields have safe defaults matching the original bare declarations.
    """

    # G-01/G-02: AC decision matrix tracking
    has_solution_path: bool = False
    position_only_path: bool = False
    ai_solve_failed: bool = False
    solution_tree_completeness: Any = None
    budget_exhausted: bool = False
    queries_used: int = 0
    co_correct_detected: bool = False

    # G-03: Human solution confidence + AI validated tracking
    human_solution_confidence: str | None = None
    ai_solution_validated: bool = False

    # Flow-through variables: set by code-path functions, read by downstream steps
    correct_move_gtp: str | None = None
    correct_move_sgf: str | None = None
    solution_moves: list[str] | None = None

    # Optional progress callback (zero overhead when None)
    notify_fn: Callable[[str, dict], Awaitable[None]] | None = None

    # Pre-analysis from solve path (forwarded to AnalyzeStage to avoid duplicate query)
    pre_analysis: Any = None
