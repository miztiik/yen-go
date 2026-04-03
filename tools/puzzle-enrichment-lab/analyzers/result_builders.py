"""Result assembly helpers for the enrichment pipeline.

Extracted from enrich_single.py — pure functions that build output
models from internal pipeline state.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

try:
    from models.ai_analysis_result import (
        AiAnalysisResult,
        DifficultySnapshot,
        MoveValidation,
        RefutationEntry,
    )
    from models.validation import ValidationStatus

    from analyzers.config_lookup import resolve_level_info as _resolve_level_info
    from analyzers.hint_generator import generate_hints
    from analyzers.teaching_comments import generate_teaching_comments
    from analyzers.technique_classifier import classify_techniques, get_all_detectors, run_detectors
except ImportError:
    from ..analyzers.config_lookup import resolve_level_info as _resolve_level_info
    from ..analyzers.hint_generator import generate_hints
    from ..analyzers.teaching_comments import generate_teaching_comments
    from ..analyzers.technique_classifier import (
        classify_techniques,
        get_all_detectors,
        run_detectors,
    )
    from ..models.ai_analysis_result import (
        AiAnalysisResult,
        DifficultySnapshot,
        MoveValidation,
        RefutationEntry,
    )
    from ..models.validation import ValidationStatus

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.difficulty_estimate import DifficultyEstimate
    from models.position import Position
    from models.refutation_result import RefutationResult


def build_refutation_entries(
    refutation_result: RefutationResult,
) -> list[RefutationEntry]:
    """Map internal Refutation models to output RefutationEntry models."""
    entries = []
    for ref in refutation_result.refutations:
        entries.append(
            RefutationEntry(
                wrong_move=ref.wrong_move,
                refutation_pv=ref.refutation_sequence,
                refutation_branches=ref.refutation_branches,
                delta=ref.winrate_delta,
                score_delta=ref.score_delta,
                wrong_move_policy=ref.wrong_move_policy,
                ownership_delta=ref.ownership_delta,
                refutation_depth=ref.refutation_depth,
                refutation_type=ref.refutation_type,
            )
        )
    return entries


def build_difficulty_snapshot(
    estimate: DifficultyEstimate,
) -> DifficultySnapshot:
    """Map internal DifficultyEstimate to output DifficultySnapshot."""
    return DifficultySnapshot(
        policy_prior_correct=estimate.policy_prior,
        visits_to_solve=estimate.visits_to_solve or 0,
        trap_density=estimate.trap_density or 0.0,
        solution_depth=estimate.solution_depth,
        branch_count=estimate.branch_count,
        local_candidate_count=estimate.local_candidate_count,
        refutation_count=estimate.refutation_count,
        composite_score=estimate.raw_difficulty_score,
        suggested_level=estimate.estimated_level,
        suggested_level_id=estimate.estimated_level_id,
        confidence=estimate.confidence,
    )


def compute_config_hash(config: EnrichmentConfig) -> str:
    """Compute a short hash of enrichment config for reproducibility tracking."""
    config_json = config.model_dump_json(exclude_none=True)
    return hashlib.sha256(config_json.encode()).hexdigest()[:12]


def make_error_result(
    error_msg: str,
    puzzle_id: str = "",
    source_file: str = "",
    trace_id: str = "",
    run_id: str = "",
) -> AiAnalysisResult:
    """Build an error-state AiAnalysisResult for pipeline failures."""
    return AiAnalysisResult(
        puzzle_id=puzzle_id,
        trace_id=trace_id,
        run_id=run_id,
        source_file=source_file,
        validation=MoveValidation(
            status=ValidationStatus.REJECTED,
            flags=[f"error: {error_msg}"],
        ),
    )


def build_partial_result(
    *,
    puzzle_id: str,
    config: EnrichmentConfig,
    difficulty_estimate: DifficultyEstimate | None,
    scan_response: AnalysisResponse | None,
    source_file: str,
    trace_id: str,
    run_id: str,
    tags: list[int],
    corner: str,
    move_order: str,
    board_size: int,
    enrichment_tier: int,
    position: Position | None = None,
) -> AiAnalysisResult:
    """Build a partial AiAnalysisResult for tier-1 or tier-2 enrichment.

    DD-6: Runs difficulty(policy_only) + technique_classifier + hint_generator.
    Teaching comments only if technique tags non-empty (RC-11).
    No solution tree injection (RC-8). ac_level=0 for partial (RC-12).

    Uses typed ``run_detectors()`` when position and scan_response are available,
    falls back to legacy ``classify_techniques()`` for null-analysis cases.
    """
    validation = MoveValidation(
        status=ValidationStatus.FLAGGED,
        flags=["partial_enrichment:no_solution_tree"],
    )

    result = AiAnalysisResult(
        puzzle_id=puzzle_id,
        trace_id=trace_id,
        run_id=run_id,
        source_file=source_file,
        validation=validation,
        enrichment_tier=enrichment_tier,
        ac_level=0,
        tags=tags,
        corner=corner,
        move_order=move_order,
    )

    # Difficulty
    if difficulty_estimate:
        result.difficulty = build_difficulty_snapshot(difficulty_estimate)

    # Technique classification — prefer typed detectors when position is available
    analysis_dict = result.model_dump()
    if position is not None and scan_response is not None:
        detectors = get_all_detectors()
        detection_results = run_detectors(
            position, scan_response, None, config, detectors=detectors,
        )
        result.technique_tags = [r.tag_slug for r in detection_results]
    else:
        # Fallback for null-analysis cases (tier-1 error recovery)
        result.technique_tags = classify_techniques(analysis_dict, board_size=board_size)

    # Hints (only if scan data available)
    if scan_response:
        result.hints = generate_hints(analysis_dict, result.technique_tags, board_size=board_size)

    # Teaching comments (DD-6/RC-11: only if technique tags detected)
    if result.technique_tags:
        result.teaching_comments = generate_teaching_comments(
            analysis_dict, result.technique_tags
        )

    # Level info
    if result.difficulty and result.difficulty.suggested_level_id > 0:
        level_name, level_range = _resolve_level_info(result.difficulty.suggested_level_id)
        result.suggested_level_name = level_name
        result.suggested_level_range = level_range

    return result
