"""AI-Solve data models (Phase 2, ai-solve-enrichment-plan-v3).

All models for the AI-Solve unified enrichment pipeline:
- QueryBudget: required budget tracker for tree construction
- SolutionNode: recursive tree node with completeness metrics
- TreeCompletenessMetrics: branch completion ratio
- MoveClassification: TE/BM/BM_HO/neutral with delta + policy
- SolvedMove: correct move with solution tree and confidence
- PositionAnalysis: complete position analysis
- BatchSummary: batch-level observability aggregate
- DisagreementRecord: structured JSONL disagreement record

This module does NOT import from backend/puzzle_manager/.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from models.validation import ConfidenceLevel

# --- Enums ---


class MoveQuality(str, Enum):
    """Move quality classification (DD-2)."""
    TE = "te"          # Correct (Δwr < T_good)
    BM = "bm"          # Wrong (Δwr > T_bad)
    BM_HO = "bm_ho"   # Blunder hotspot (Δwr > T_hotspot)
    NEUTRAL = "neutral"  # Between T_good and T_bad


class AiCorrectnessLevel(int, Enum):
    """AI Correctness (AC) levels (DD-4)."""
    UNTOUCHED = 0   # AI pipeline has NOT processed this puzzle
    ENRICHED = 1    # AI enriched metadata but existing solution used as-is
    AI_SOLVED = 2   # AI built or extended the solution tree
    VERIFIED = 3    # Human expert confirmed AI solution (out of scope for pipeline)


class HumanSolutionConfidence(str, Enum):
    """Human solution confidence when AI disagrees (DD-10)."""
    STRONG = "strong"   # AI agrees: human solution is correct
    WEAK = "weak"       # AI finds alternatives but human solution is acceptable
    LOSING = "losing"   # AI says human solution is a losing move


# --- QueryBudget ---


@dataclass
class QueryBudget:
    """Track engine query budget for tree construction (DD-3).

    Required parameter (not optional). Total queries are capped by
    max_total_tree_queries from config.
    """
    total: int
    used: int = 0

    def can_query(self) -> bool:
        """Return True if budget allows another query."""
        return self.used < self.total

    def consume(self, n: int = 1) -> None:
        """Consume n queries from the budget.

        Args:
            n: Number of queries to consume.

        Raises:
            ValueError: If n would exceed remaining budget.
        """
        if self.used + n > self.total:
            raise ValueError(
                f"Cannot consume {n} queries: {self.remaining} remaining "
                f"(used={self.used}, total={self.total})"
            )
        self.used += n

    @property
    def remaining(self) -> int:
        """Return remaining query budget."""
        return self.total - self.used

    def __repr__(self) -> str:
        return f"QueryBudget(used={self.used}/{self.total})"


# --- Tree completeness ---


class TreeCompletenessMetrics(BaseModel):
    """Branch completion metrics for a solution tree root (DD-3).

    Tracks how many attempted branches completed vs were truncated.
    """
    completed_branches: int = Field(
        default=0, ge=0,
        description="Number of branches that reached a stopping condition",
    )
    total_attempted_branches: int = Field(
        default=0, ge=0,
        description="Total branches attempted (completed + truncated)",
    )
    branches_pruned_by_depth_policy: int = Field(
        default=0, ge=0,
        description=(
            "Opponent branches pruned because the depth-adjusted policy threshold "
            "(branch_min_policy + depth_policy_scale * depth) exceeded the candidate's "
            "policy, but the flat branch_min_policy alone would have accepted it (L3)."
        ),
    )
    simulation_hits: int = Field(
        default=0, ge=0,
        description="Sibling branches resolved via Kawano simulation (KM-01)",
    )
    simulation_misses: int = Field(
        default=0, ge=0,
        description="Simulation attempts that failed verification (KM-01)",
    )
    simulation_collisions: int = Field(
        default=0, ge=0,
        description="Simulation skipped due to cached reply overlapping opponent move (KM-01)",
    )
    transposition_hits: int = Field(
        default=0, ge=0,
        description="Position cache hits within a single tree build (KM-02)",
    )
    forced_move_count: int = Field(
        default=0, ge=0,
        description="Player nodes resolved via forced-move fast-path (KM-03)",
    )
    max_resolved_depth: int = Field(
        default=0, ge=0,
        description="Deepest non-truncated branch in the solution tree (KM-04)",
    )

    def is_complete(self) -> bool:
        """Return True if all attempted branches completed."""
        if self.total_attempted_branches == 0:
            return True
        return self.completed_branches == self.total_attempted_branches

    @property
    def completion_ratio(self) -> float:
        """Return ratio of completed branches (0.0 to 1.0)."""
        if self.total_attempted_branches == 0:
            return 1.0
        return self.completed_branches / self.total_attempted_branches


# --- Solution tree ---


class SolutionNode(BaseModel):
    """Recursive solution tree node (DD-1, DD-3).

    Each node represents a move in the solution tree. Children
    represent opponent responses (branching) or player continuations.
    """
    move_gtp: str = Field(
        description="GTP-format move (e.g. 'C3', 'D4')",
    )
    color: str = Field(
        description="Player color: 'B' or 'W'",
    )
    winrate: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Winrate from puzzle player perspective after this move",
    )
    policy: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Policy prior for this move",
    )
    visits: int = Field(
        default=0, ge=0,
        description="MCTS visits for this analysis",
    )
    is_correct: bool = Field(
        default=False,
        description="True if this move is classified as correct (TE)",
    )
    truncated: bool = Field(
        default=False,
        description="True if this branch was truncated (budget/depth exhausted)",
    )
    children: list[SolutionNode] = Field(
        default_factory=list,
        description="Child nodes (opponent responses or continuations)",
    )
    tree_completeness: TreeCompletenessMetrics | None = Field(
        default=None,
        description="Completeness metrics (only set at tree root)",
    )
    comment: str = Field(
        default="",
        description="Teaching comment for this node",
    )

    model_config = {"arbitrary_types_allowed": True}


# --- Move classification ---


class MoveClassification(BaseModel):
    """Classification of a single candidate move (DD-2).

    Delta-based: no absolute winrate gates (DD-6).
    """
    move_gtp: str = Field(
        description="GTP-format move",
    )
    color: str = Field(
        description="Player color: 'B' or 'W'",
    )
    quality: MoveQuality = Field(
        description="TE / BM / BM_HO / neutral",
    )
    winrate: float = Field(
        ge=0.0, le=1.0,
        description="Winrate from puzzle player perspective",
    )
    delta: float = Field(
        description="Δwr from root (positive = better than root)",
    )
    policy: float = Field(
        ge=0.0, le=1.0,
        description="Policy prior for this move",
    )
    rank: int = Field(
        ge=0,
        description="Rank among all candidate moves (0 = best)",
    )
    score_lead: float = Field(
        default=0.0,
        description="Score lead from puzzle player perspective (S1-G15)",
    )


# --- Solved move ---


class SolvedMove(BaseModel):
    """A correct first move with its solution tree and confidence (DD-4).

    Represents one correct-root tree in the solution.
    """
    move_gtp: str = Field(
        description="GTP-format correct first move",
    )
    color: str = Field(
        description="Player color: 'B' or 'W'",
    )
    winrate: float = Field(
        ge=0.0, le=1.0,
        description="Winrate from puzzle player perspective",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH,
        description="Epistemic confidence in solved move",
    )
    solution_tree: SolutionNode | None = Field(
        default=None,
        description="Full recursive solution tree from this move",
    )


# --- Position analysis ---


class PositionAnalysis(BaseModel):
    """Complete position analysis result (DD-2, DD-7, DD-8).

    Contains all classified candidate moves, correct moves,
    and positional metadata from AI analysis.
    """
    puzzle_id: str = Field(
        description="Puzzle identifier",
    )
    root_winrate: float = Field(
        ge=0.0, le=1.0,
        description="Root position winrate from puzzle player perspective",
    )
    player_color: str = Field(
        description="Puzzle player color: 'B' or 'W'",
    )
    correct_moves: list[MoveClassification] = Field(
        default_factory=list,
        description="Moves classified as TE (correct)",
    )
    wrong_moves: list[MoveClassification] = Field(
        default_factory=list,
        description="Moves classified as BM or BM_HO (wrong)",
    )
    neutral_moves: list[MoveClassification] = Field(
        default_factory=list,
        description="Moves classified as neutral",
    )
    all_classifications: list[MoveClassification] = Field(
        default_factory=list,
        description="All classified candidate moves",
    )
    solved_moves: list[SolvedMove] = Field(
        default_factory=list,
        description="Correct moves with solution trees",
    )
    co_correct_detected: bool = Field(
        default=False,
        description="True if co-correct (multiple correct first moves) detected (DD-7)",
    )
    root_winrate_confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Root winrate confidence annotation (DD-6)",
    )
    root_winrate_confidence_reason: str = Field(
        default="",
        description="Why root winrate confidence was set (e.g. 'root_wr_low', 'root_wr_high')",
    )
    goal_confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Goal inference confidence (DD-8)",
    )
    goal_confidence_reason: str = Field(
        default="",
        description="Why goal confidence was set (e.g. 'ko_context', 'ownership_variance')",
    )
    ladder_suspected: bool = Field(
        default=False,
        description="True if ladder pattern suspected (DD-12)",
    )
    ai_solution_validated: bool = Field(
        default=False,
        description="True if AI agrees with existing human solution",
    )
    human_solution_confidence: HumanSolutionConfidence | None = Field(
        default=None,
        description="Confidence in human solution when AI disagrees (DD-10)",
    )
    ac_level: AiCorrectnessLevel = Field(
        default=AiCorrectnessLevel.UNTOUCHED,
        description="AI Correctness level (DD-4)",
    )
    queries_used: int = Field(
        default=0, ge=0,
        description="Total engine queries consumed",
    )
    original_level: str = Field(
        default="",
        description="Source/original level from SGF YG property before enrichment",
    )


# --- Batch summary ---


class BatchSummary(BaseModel):
    """Batch-level observability aggregate (DD-11).

    Emitted as structured JSON at INFO level after each batch.
    """
    batch_id: str = Field(
        description="Batch identifier (e.g. run_id or collection slug)",
    )
    total_puzzles: int = Field(
        default=0, ge=0,
        description="Total puzzles in batch",
    )
    position_only: int = Field(
        default=0, ge=0,
        description="Puzzles without existing solution",
    )
    has_solution: int = Field(
        default=0, ge=0,
        description="Puzzles with existing solution",
    )
    ac_0_count: int = Field(
        default=0, ge=0,
        description="Puzzles with ac:0 (untouched / errors)",
    )
    ac_1_count: int = Field(
        default=0, ge=0,
        description="Puzzles with ac:1 (enriched)",
    )
    ac_2_count: int = Field(
        default=0, ge=0,
        description="Puzzles with ac:2 (ai_solved)",
    )
    disagreements: int = Field(
        default=0, ge=0,
        description="AI vs human solution disagreements",
    )
    total_queries: int = Field(
        default=0, ge=0,
        description="Total engine queries consumed",
    )
    co_correct_count: int = Field(
        default=0, ge=0,
        description="Puzzles with co-correct detection",
    )
    truncated_trees: int = Field(
        default=0, ge=0,
        description="Puzzles with truncated solution trees",
    )
    errors: int = Field(
        default=0, ge=0,
        description="Processing errors",
    )
    collection: str = Field(
        default="",
        description="Collection slug (for per-collection disagreement tracking)",
    )
    disagreement_rate: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Disagreement rate (disagreements / has_solution)",
    )
    correct_move_ranks: list[int] = Field(
        default_factory=list,
        description="Per-puzzle correct move rank in KataGo's candidate list (G-6, AC-8)",
    )
    ownership_delta_used: int = Field(
        default=0, ge=0,
        description="PI-1: Puzzles where ownership delta reranked candidates (weight > 0)",
    )
    score_delta_rescues: int = Field(
        default=0, ge=0,
        description="PI-3: Candidates rescued by score delta filter",
    )
    opponent_response_emitted: int = Field(
        default=0, ge=0,
        description="PI-10: Puzzles where opponent-response was appended to wrong-move comment",
    )
    max_queries_per_puzzle: int = Field(
        default=0, ge=0,
        description="MH-7: Maximum engine queries consumed by any single puzzle in batch",
    )
    # T7: Entropy/rank aggregates for qk observability
    entropy_values: list[float] = Field(
        default_factory=list,
        description="T7: Per-puzzle policy entropy values collected in batch",
    )
    rank_values: list[int] = Field(
        default_factory=list,
        description="T7: Per-puzzle correct move ranks collected in batch",
    )
    goal_agreement_matches: int = Field(
        default=0, ge=0,
        description="T7: Puzzles where inferred goal matches existing metadata",
    )
    goal_agreement_mismatches: int = Field(
        default=0, ge=0,
        description="T7: Puzzles where inferred goal mismatches existing metadata",
    )
    goal_agreement_unknown: int = Field(
        default=0, ge=0,
        description="T7: Puzzles where goal agreement could not be determined",
    )
    frame_imbalance_count: int = Field(
        default=0, ge=0,
        description="Puzzles where frame-vs-unframed winrate delta > 0.5 (frame territory imbalance)",
    )
    tree_validation_overrides: int = Field(
        default=0, ge=0,
        description="Puzzles where REJECTED was upgraded to FLAGGED by tree-validation override (P1)",
    )


# --- Disagreement record ---


class DisagreementRecord(BaseModel):
    """Structured record for JSONL disagreement sink (DD-11).

    Written to .pm-runtime/logs/disagreements/{run_id}.jsonl.
    """
    puzzle_id: str = Field(
        description="Puzzle identifier",
    )
    run_id: str = Field(
        description="Pipeline run identifier",
    )
    collection: str = Field(
        default="",
        description="Collection slug",
    )
    human_move_gtp: str = Field(
        description="Human's chosen correct move (GTP format)",
    )
    ai_move_gtp: str = Field(
        description="AI's top correct move (GTP format)",
    )
    human_winrate: float = Field(
        ge=0.0, le=1.0,
        description="Winrate of human move from puzzle player perspective",
    )
    ai_winrate: float = Field(
        ge=0.0, le=1.0,
        description="Winrate of AI move from puzzle player perspective",
    )
    delta: float = Field(
        description="Winrate gap (ai_winrate - human_winrate)",
    )
    human_solution_confidence: HumanSolutionConfidence = Field(
        description="Classification of human solution quality",
    )
    level_slug: str = Field(
        default="",
        description="Puzzle level slug",
    )
    timestamp: str = Field(
        default="",
        description="ISO 8601 timestamp",
    )
