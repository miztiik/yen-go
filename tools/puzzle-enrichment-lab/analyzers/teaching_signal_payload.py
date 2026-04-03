"""Teaching signal payload builder — structured event for LLM consumption.

Computes R-1 derived signals from existing KataGo analysis data and
packages them into a structured dict on PipelineContext.teaching_signals.

Option B: Rich Payload — includes correct_move, position, and wrong_moves
sections with config-driven instructiveness gate and seki exception.

Consumers: Future LLM teaching pipeline, eval analysis tooling, diagnostics.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

try:
    from analyzers.estimate_difficulty import (
        compute_log_policy_score,
        compute_position_closeness,
        compute_score_lead_rank,
    )
except ImportError:
    from ..analyzers.estimate_difficulty import (
        compute_log_policy_score,
        compute_position_closeness,
        compute_score_lead_rank,
    )

if TYPE_CHECKING:
    from config.teaching import TeachingSignalConfig
    from models.ai_analysis_result import AiAnalysisResult
    from models.analysis_response import AnalysisResponse

logger = logging.getLogger(__name__)


def build_teaching_signal_payload(
    response: AnalysisResponse | None,
    correct_move_gtp: str,
    policy_entropy: float,
    correct_move_rank: int,
    result: AiAnalysisResult | None = None,
    board_size: int = 19,
    config: TeachingSignalConfig | None = None,
) -> dict:
    """Build structured teaching signal payload from KataGo analysis data.

    All signals are derived from existing data — zero new KataGo queries.
    Implements Option B rich payload with correct_move, position,
    and wrong_moves sections. Config-driven thresholds gate which
    wrong moves qualify as instructive (RC-1, RC-2, RC-3).

    Args:
        response: KataGo analysis response for the root position.
        correct_move_gtp: GTP coordinate of the correct first move.
        policy_entropy: Pre-computed policy entropy.
        correct_move_rank: Pre-computed correct move rank.
        result: AiAnalysisResult with populated refutations.
        board_size: Board size for SGF↔GTP conversion (fixes hardcode).
        config: TeachingSignalConfig with thresholds. None uses defaults.

    Returns:
        Dict with keys: version, correct_move, position, wrong_moves.
    """
    # Resolve thresholds from config or use defaults
    max_wrong_moves = 3
    instructiveness_threshold = 0.05
    seki_closeness_threshold = 0.9
    ownership_delta_threshold = 0.3
    if config is not None:
        max_wrong_moves = config.max_wrong_moves
        instructiveness_threshold = config.instructiveness_threshold
        seki_closeness_threshold = config.seki_closeness_threshold
        ownership_delta_threshold = config.ownership_delta_threshold

    # Position-level signals
    root_winrate = 0.5
    root_score = 0.0
    position_closeness = 0.5
    if response is not None:
        root_winrate = response.root_winrate
        root_score = response.root_score
        position_closeness = compute_position_closeness(root_winrate)

    # Correct move signals
    log_policy_correct = 0.0
    score_lead_rank_correct = 0.5
    play_selection_value = 0.0
    correct_move_sgf = ""
    correct_move = correct_move_gtp.upper() if correct_move_gtp else ""
    if response is not None:
        for m in response.move_infos:
            if m.move.upper() == correct_move:
                log_policy_correct = compute_log_policy_score(m.policy_prior)
                score_lead_rank_correct = compute_score_lead_rank(
                    response.move_infos, correct_move_gtp,
                )
                play_selection_value = getattr(m, "play_selection_value", 0.0)
                break
        # Convert GTP to SGF for correct move
        try:
            from models.analysis_response import gtp_to_sgf
            correct_move_sgf = gtp_to_sgf(correct_move_gtp, board_size)
        except (ImportError, Exception):
            pass

    payload: dict = {
        "version": 1,
        "correct_move": {
            "move_gtp": correct_move_gtp,
            "move_sgf": correct_move_sgf,
            "log_policy_score": round(log_policy_correct, 4),
            "score_lead_rank": round(score_lead_rank_correct, 4),
            "play_selection_value": round(play_selection_value, 4),
        },
        "position": {
            "root_winrate": round(root_winrate, 4),
            "root_score": round(root_score, 2),
            "position_closeness": round(position_closeness, 4),
            "policy_entropy": round(policy_entropy, 4),
            "correct_move_rank": correct_move_rank,
        },
        "wrong_moves": [],
    }

    # Wrong move signals from populated refutations
    if result and result.refutations:
        try:
            from models.analysis_response import sgf_to_gtp
        except ImportError:
            from ..models.analysis_response import sgf_to_gtp

        for ref_entry in result.refutations[:max_wrong_moves]:
            wrong_gtp = sgf_to_gtp(ref_entry.wrong_move, board_size)

            # RC-2: Instructiveness gate — abs(delta) must exceed threshold
            delta_abs = abs(ref_entry.delta)
            seki_exception = False
            instructive = delta_abs >= instructiveness_threshold

            # RC-1: Seki exception — high position_closeness bypasses threshold
            if not instructive and position_closeness > seki_closeness_threshold:
                seki_exception = True
                instructive = True

            # Compute log_policy and score_lead_rank for wrong move
            wrong_log_policy = 0.0
            wrong_score_lead_rank = 0.5
            if response is not None:
                for m in response.move_infos:
                    if m.move.upper() == wrong_gtp.upper():
                        wrong_log_policy = compute_log_policy_score(m.policy_prior)
                        wrong_score_lead_rank = compute_score_lead_rank(
                            response.move_infos, wrong_gtp,
                        )
                        break

            wrong_signal: dict = {
                "move_gtp": wrong_gtp,
                "move_sgf": ref_entry.wrong_move,
                "log_policy": round(wrong_log_policy, 4),
                "score_lead_rank": round(wrong_score_lead_rank, 4),
                "delta": round(ref_entry.delta, 4),
                "score_delta": round(ref_entry.score_delta, 2),
                "wrong_move_policy": round(ref_entry.wrong_move_policy, 4),
                "refutation_depth": ref_entry.refutation_depth,
                "refutation_pv": ref_entry.refutation_pv,
                "refutation_type": ref_entry.refutation_type,
                "instructive": instructive,
                "seki_exception": seki_exception,
            }

            # RC-3: Conditional ownership — only emit when above threshold
            if ref_entry.ownership_delta > ownership_delta_threshold:
                wrong_signal["ownership_delta_max"] = round(ref_entry.ownership_delta, 4)

            payload["wrong_moves"].append(wrong_signal)

    return payload
