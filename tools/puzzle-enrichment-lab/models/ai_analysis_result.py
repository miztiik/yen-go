"""AiAnalysisResult — structured output model for KataGo enrichment.

Task A.1.4: Single Pydantic model aggregating all enrichment outputs
for one puzzle. Supports JSON serialization, schema versioning, and
a factory method to build from CorrectMoveResult.

Schema version is bumped when the output format changes, enabling
forward-compatible parsing by downstream consumers.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

try:
    from models.validation import ConfidenceLevel, CorrectMoveResult, ValidationStatus
except ImportError:
    from .validation import ConfidenceLevel, CorrectMoveResult, ValidationStatus


# Bump this when the output schema changes
# v7: Added enrichment_tier (D3)
# v8: Added Phase B teaching fields — technique_tags, teaching_comments, hints (D37)
# v9: Added human_solution_confidence, ai_solution_validated (G-03)
# v10: Added teaching_signals payload (R-1), score_delta/wrong_move_policy/ownership_delta on RefutationEntry
AI_ANALYSIS_SCHEMA_VERSION: int = 10


def generate_trace_id() -> str:
    """Generate a 16-char hex trace_id matching pipeline format.

    Matches backend/puzzle_manager/core/trace_utils.py: uuid.uuid4().hex[:16]
    """
    return uuid.uuid4().hex[:16]


def generate_run_id() -> str:
    """Generate a run_id: YYYYMMDD-HHMMSS-xxxxxxxx.

    Format includes date + time + 8 random hex chars for uniqueness.
    Aligned with KataGo log naming convention (YYYYMMDD-HHMMSS-HEX).
    """
    now = datetime.now(UTC)
    return f"{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(4)}"


class EngineSnapshot(BaseModel):
    """Records which engine/model/settings produced the analysis."""
    model: str = Field(default="", description="Model filename (without path)")
    visits: int = Field(default=0, ge=0, description="Max visits used for analysis")
    config_hash: str = Field(default="", description="Hash of analysis config for reproducibility")


class MoveValidation(BaseModel):
    """Validation outcome for the puzzle's correct first move."""
    correct_move_gtp: str = Field(default="", description="GTP coordinate of the correct move")
    katago_top_move_gtp: str = Field(default="", description="GTP coordinate of KataGo's top move")
    status: ValidationStatus = Field(default=ValidationStatus.FLAGGED, description="accepted | flagged | rejected")
    katago_agrees: bool = Field(default=False, description="True if KataGo's top move matches correct move")
    correct_move_winrate: float = Field(default=0.0, ge=0.0, le=1.0, description="Winrate after correct move")
    correct_move_policy: float = Field(default=0.0, ge=0.0, le=1.0, description="Policy prior for correct move")
    validator_used: str = Field(default="", description="Which validator handled this puzzle (e.g. life_and_death, seki, tactical:ladder)")
    flags: list[str] = Field(default_factory=list, description="Diagnostic flags (e.g. center_position, ko_pending_a15)")


class RefutationEntry(BaseModel):
    """A single wrong-move refutation in the structured output.

    Maps from the internal Refutation model to the serialized output format.
    Phase A sets refutation_type='unclassified'; Phase B adds classification.
    """
    wrong_move: str = Field(default="", description="SGF coordinate of the wrong first move")
    refutation_pv: list[str] = Field(default_factory=list, description="Refutation PV (SGF coords, 2-4 moves)")
    refutation_branches: list[list[str]] = Field(
        default_factory=list,
        description="Alternative refutation branches (each branch is SGF coords)",
    )
    delta: float = Field(default=0.0, description="Winrate drop from initial (negative = bad for puzzle player)")
    score_delta: float = Field(default=0.0, description="Score delta: points lost for wrong move (negative = bad)")
    wrong_move_policy: float = Field(default=0.0, description="KataGo policy prior for the wrong move (how tempting it looks)")
    ownership_delta: float = Field(default=0.0, description="Max absolute ownership shift caused by the wrong move (R-1 signal)")
    refutation_depth: int = Field(default=1, ge=1, description="Number of moves in refutation PV")
    refutation_type: str = Field(default="unclassified", description="Technique classification (unclassified in Phase A)")


class DifficultySnapshot(BaseModel):
    """Difficulty estimation snapshot for the structured output.

    KataGo-signal fields (policy_prior_correct, visits_to_solve,
    trap_density) are PRIMARY signals for Tier 3 enrichment (D22,
    2026-03-02 review: D22 restored KataGo signals as 80% weight).

    Tier 2 (structural-only) enrichment sentinel values:
      - policy_prior_correct = -1.0  →  KataGo data unavailable
      - visits_to_solve      = -1    →  KataGo data unavailable
      - trap_density         = -1.0  →  KataGo data unavailable

    Consumers MUST check AiAnalysisResult.enrichment_tier or test for
    sentinel values before interpreting KataGo-signal fields (D3).
    """
    policy_prior_correct: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description=(
            "Raw policy prior for the correct move. "
            "Sentinel: -1.0 indicates Tier 2 (no KataGo analysis) — "
            "do not interpret as a real policy value (D3)."
        ),
    )
    visits_to_solve: int = Field(
        default=0, ge=-1,
        description=(
            "MCTS visits allocated to the correct move in the search tree (C1). "
            "Sentinel: -1 indicates Tier 2 (no KataGo analysis)."
        ),
    )
    trap_density: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description=(
            "Weighted share of wrong-move policy pointing at tempting traps. "
            "Sentinel: -1.0 indicates Tier 2 (no KataGo analysis)."
        ),
    )
    solution_depth: int = Field(
        default=0, ge=0,
        description="Number of moves in main-line solution tree",
    )
    branch_count: int = Field(
        default=0, ge=0,
        description="Branching points in correct solution tree (Phase R.3)",
    )
    local_candidate_count: int = Field(
        default=0, ge=0,
        description="Empty intersections near stones — positional ambiguity (Phase R.3)",
    )
    refutation_count: int = Field(
        default=0, ge=0,
        description="Number of plausible wrong first moves",
    )
    composite_score: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Weighted composite difficulty score (0-100)",
    )
    suggested_level: str = Field(
        default="unknown",
        description="Suggested Yen-Go level slug (novice..expert)",
    )
    suggested_level_id: int = Field(
        default=0,
        description="Numeric level ID from puzzle-levels.json",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW,
        description="Epistemic confidence in difficulty estimate",
    )
    policy_entropy: float = Field(
        default=-1.0,
        description="Policy entropy at puzzle root position (0-1 normalized). "
        "Sentinel -1.0 = unavailable. Higher = more ambiguous position.",
    )
    correct_move_rank: int = Field(
        default=-1,
        description="Rank of correct move in KataGo's policy network output (1=top). "
        "Sentinel -1 = unavailable. Lower = easier for AI.",
    )


class AiAnalysisResult(BaseModel):
    """Complete AI analysis output for a single puzzle.

    This is the structured output produced by the enrichment pipeline
    for each puzzle. It captures:
    - Which engine/model was used
    - Validation outcome (accepted/flagged/rejected)
    - Puzzle metadata context (tags, corner, move order)
    - Schema version for forward compatibility
    """
    puzzle_id: str = Field(default="", description="YENGO puzzle ID (GN property, or filename if GN absent)")
    trace_id: str = Field(default="", description="16-char hex trace ID for this puzzle (unique per enrichment run)")
    run_id: str = Field(default="", description="Batch run ID: YYYYMMDD-8charhex (shared across all puzzles in one batch)")
    source_file: str = Field(default="", description="Source SGF filename with extension (for traceability when GN is not set)")
    schema_version: int = Field(default=AI_ANALYSIS_SCHEMA_VERSION, description="Output schema version")
    engine: EngineSnapshot = Field(default_factory=EngineSnapshot, description="Engine/model used")
    validation: MoveValidation = Field(default_factory=MoveValidation, description="Correct move validation result")
    refutations: list[RefutationEntry] = Field(default_factory=list, description="Wrong-move refutations (A.2)")
    difficulty: DifficultySnapshot = Field(default_factory=DifficultySnapshot, description="Difficulty estimation (A.3)")
    tags: list[int] = Field(default_factory=list, description="Numeric tag IDs from puzzle YT property")
    tag_names: list[str] = Field(default_factory=list, description="Human-readable tag names resolved from config/tags.json")
    corner: str = Field(default="TL", description="YC property (TL, TR, BL, BR, C, E)")
    move_order: str = Field(default="strict", description="YO property (strict, flexible, miai)")
    suggested_level_name: str = Field(default="", description="Human-readable level name (e.g. 'Beginner')")
    suggested_level_range: str = Field(default="", description="Rank range for the suggested level (e.g. '25k\u201321k')")
    status_label: str = Field(default="", description="Human-readable validation status (accepted/flagged/rejected)")
    enrichment_tier: int = Field(
        default=3, ge=1, le=3,
        description=(
            "D26 enrichment tier: "
            "1=Bare (no KataGo data, stone-pattern only), "
            "2=Structural (KataGo position scan OR legacy v2 migration; "
            "    disambiguate via status field: FLAGGED=partial enrichment, ACCEPTED=legacy), "
            "3=Full (complete KataGo analysis with solution tree validation). "
            "Sentinel values (-1.0) for KataGo-specific fields in tier 1/2."
        ),
    )

    # --- Phase B: Teaching enrichment fields (v8, D37) ---
    technique_tags: list[str] = Field(
        default_factory=list,
        description=(
            "Technique tag slugs detected from KataGo analysis (Phase B.5). "
            "Sorted by TAG_PRIORITY (highest-priority first). "
            "Empty list = Phase B not yet run."
        ),
    )
    teaching_comments: dict[str, str | dict | int] = Field(
        default_factory=dict,
        description=(
            "Teaching explanations generated from technique + analysis (Phase B.4). "
            "Keys: 'correct_comment' (str), 'wrong_comments' (dict[str,str]), "
            "'summary' (str), 'hc_level' (int: 0|2|3). "
            "Empty dict = Phase B not yet run."
        ),
    )
    hints: list[str] = Field(
        default_factory=list,
        description=(
            "3-tier progressive hints for YH property (Phase B.6). "
            "Index 0=technique, 1=reasoning, 2=coordinate ({!xy} tokens). "
            "Empty list = Phase B not yet run."
        ),
    )

    # --- A3: Per-phase wall-clock timing (seconds) ---
    phase_timings: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Wall-clock seconds per enrichment phase (A3). "
            "Keys: parse, query_build, analysis, tree_validation, "
            "refutation, difficulty, teaching, total. "
            "Empty dict = timing not captured."
        ),
    )

    # --- S3-G4: AI Correctness level (DD-4) ---
    ac_level: int = Field(
        default=0, ge=0, le=3,
        description=(
            "AI Correctness level (S3-G4, DD-4). "
            "0=untouched, 1=enriched, 2=ai_solved, 3=verified. "
            "Flows to YQ property as ac:N."
        ),
    )

    # --- S3-G11: Goal inference ---
    goal: str = Field(
        default="unknown",
        description=(
            "Inferred puzzle goal (S3-G11, DD-8). "
            "Values: kill, live, ko, capture, unknown."
        ),
    )
    goal_confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW,
        description=(
            "Goal inference confidence (S3-G11). "
            "Values: high, medium, low."
        ),
    )
    goal_confidence_reason: str = Field(
        default="",
        description=(
            "Why goal confidence was set to this level (D1). "
            "Values: 'ko_context_high_delta', 'score_delta_kill', 'ownership_variance', etc."
        ),
    )

    # --- G-03: Human solution confidence + AI validated flag (DD-10) ---
    human_solution_confidence: str | None = Field(
        default=None,
        description=(
            "Confidence in human's original solution when AI disagrees (DD-10, G-03). "
            "Values: 'strong', 'weak', 'losing', None (AI agrees / not applicable). "
            "Only set on has-solution path."
        ),
    )
    ai_solution_validated: bool = Field(
        default=False,
        description=(
            "True if AI agrees with the existing human solution (G-03). "
            "Only meaningful on has-solution path."
        ),
    )

    # --- Observability fields (DD-11) ---
    co_correct_detected: bool = Field(
        default=False,
        description=(
            "True if co-correct (multiple correct first moves) detected (DD-7). "
        ),
    )
    queries_used: int = Field(
        default=0, ge=0,
        description="Total engine queries consumed by AI-Solve for this puzzle.",
    )
    tree_truncated: bool = Field(
        default=False,
        description="True if solution tree was truncated (budget or depth exhausted).",
    )
    collection: str = Field(
        default="",
        description="Collection slug from YL property (for per-collection tracking).",
    )
    original_level: str = Field(
        default="",
        description="Original YG level slug from the SGF (before enrichment re-grades it).",
    )
    ai_top_move_winrate: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Winrate of KataGo's top move (for disagreement delta calculation).",
    )

    # --- Enrichment quality level (T52) ---
    enrichment_quality_level: int = Field(
        default=3, ge=1, le=3,
        description=(
            "Enrichment quality level based on which stages completed: "
            "1=stone-pattern only (parse+structural), "
            "2=partial (analysis ran but some stages degraded), "
            "3=full (all stages completed successfully)."
        ),
    )

    # --- T61: Per-move accuracy (stretch) ---
    per_move_accuracy: float | None = Field(
        default=None,
        description=(
            "Per-move accuracy metric: 100 × 0.75^weighted_ptloss. "
            "Higher = easier puzzle (correct move has low policy loss). "
            "None if not computed (no refutation data)."
        ),
    )

    # --- Stage 10: Enriched SGF output ---
    enriched_sgf: str | None = Field(
        default=None,
        description="Enriched SGF text produced by sgf_enricher (Stage 10). None if not yet built or failed.",
    )

    # --- R-1: Teaching signal payload ---
    teaching_signals: dict | None = Field(
        default=None,
        description="Structured KataGo-derived teaching signals for LLM consumption (schema v10).",
    )

    @classmethod
    def from_validation(
        cls,
        puzzle_id: str,
        correct_move_result: CorrectMoveResult,
        model_name: str,
        visits: int,
        config_hash: str,
        tags: list[int] | None = None,
        tag_names: list[str] | None = None,
        corner: str = "TL",
        move_order: str = "strict",
        source_file: str = "",
        trace_id: str = "",
        run_id: str = "",
    ) -> AiAnalysisResult:
        """Build AiAnalysisResult from a CorrectMoveResult.

        Args:
            puzzle_id: YENGO puzzle ID (from GN property or filename fallback).
            correct_move_result: Output from validate_correct_move().
            model_name: KataGo model filename.
            visits: Max visits used.
            config_hash: Hash of analysis config.
            tags: Numeric tag IDs.
            tag_names: Human-readable tag names (resolved from config/tags.json).
            corner: YC property value.
            move_order: YO property value.
            source_file: Source SGF filename with extension.
            trace_id: 16-char hex trace ID for this puzzle.
            run_id: Batch run ID (YYYYMMDD-8charhex).

        Returns:
            Fully populated AiAnalysisResult.
        """
        return cls(
            puzzle_id=puzzle_id,
            trace_id=trace_id,
            run_id=run_id,
            source_file=source_file,
            schema_version=AI_ANALYSIS_SCHEMA_VERSION,
            engine=EngineSnapshot(
                model=model_name,
                visits=visits,
                config_hash=config_hash,
            ),
            validation=MoveValidation(
                correct_move_gtp=correct_move_result.correct_move_gtp,
                katago_top_move_gtp=correct_move_result.katago_top_move,
                status=correct_move_result.status,
                katago_agrees=correct_move_result.katago_agrees,
                correct_move_winrate=correct_move_result.correct_move_winrate,
                correct_move_policy=correct_move_result.correct_move_policy,
                validator_used=correct_move_result.validator_used,
                flags=correct_move_result.flags,
            ),
            tags=tags or [],
            tag_names=tag_names or [],
            corner=corner,
            move_order=move_order,
            status_label=correct_move_result.status.value,
        )


# ---------------------------------------------------------------------------
# E3: Schema migration utilities
# ---------------------------------------------------------------------------


def migrate_v2_to_v3(result_dict: dict) -> dict:
    """Upgrade a v2 AiAnalysisResult dict (no DifficultySnapshot) to v3.

    Schema history:
      v2: No ``difficulty`` field — difficulty was reported as a flat scalar.
      v3: ``difficulty`` became a ``DifficultySnapshot`` sub-object.
      v6: Current stable schema (adds refutations, tree validation).
      v7: Added ``enrichment_tier`` (D3, 2026-03-02 review).
      v8: Added Phase B fields — ``technique_tags``, ``teaching_comments``, ``hints`` (D37).

    This utility is the first step in a migration chain.  After calling
    this function, the dict is at v3 shape and can be parsed by
    ``AiAnalysisResult.model_validate()``.

    Mixed-version result sets (e.g. a batch where some puzzles were
    enriched with the old tool and some with the current one) should run
    all dicts through this function before validation::

        results = [migrate_v2_to_v3(r) for r in raw_dicts
                   if r.get("schema_version", 2) < 3]

    Args:
        result_dict: Raw dict from JSON, must have ``schema_version`` < 3
                     (or absent, which also means v2).

    Returns:
        Copy of *result_dict* with a populated ``difficulty`` sub-object
        and ``schema_version`` bumped to 3.

    Raises:
        ValueError: If ``schema_version`` >= 3 (already migrated).
    """
    sv = result_dict.get("schema_version", 2)
    if sv >= 3:
        raise ValueError(
            f"migrate_v2_to_v3: dict is already at schema_version {sv}. "
            "Nothing to migrate."
        )

    updated = dict(result_dict)

    # v2 stored a flat ``composite_score`` at the top level; v3 wraps it.
    composite = updated.pop("composite_score", 0.0)
    suggested_level = updated.pop("suggested_level", "unknown")
    confidence = updated.pop("confidence", "low")

    updated.setdefault("difficulty", {
        # KataGo signals unavailable for migrated v2 records — use sentinels
        "policy_prior_correct": -1.0,
        "visits_to_solve": -1,
        "trap_density": -1.0,
        "solution_depth": 0,
        "branch_count": 0,
        "local_candidate_count": 0,
        "refutation_count": 0,
        "composite_score": composite,
        "suggested_level": suggested_level,
        "suggested_level_id": 0,
        "confidence": confidence,
    })

    # Populate enrichment_tier sentinel: v2 records had no KataGo signals
    updated.setdefault("enrichment_tier", 2)
    updated["schema_version"] = 3

    return updated
