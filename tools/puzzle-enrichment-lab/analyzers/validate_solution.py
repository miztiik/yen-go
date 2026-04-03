"""Task A.1: Validate the correct first move against KataGo.

Takes the SGF's correct move, runs KataGo analysis, and checks
whether KataGo agrees it's the best (or near-best) move.
"""

from __future__ import annotations

import logging

try:
    from engine.local_subprocess import LocalEngine
    from models.analysis_request import AnalysisRequest
    from models.analysis_response import AnalysisResponse, sgf_to_gtp
    from models.position import Position
    from models.validation_result import ValidationResult
except ImportError:
    from ..engine.local_subprocess import LocalEngine
    from ..models.analysis_request import AnalysisRequest
    from ..models.analysis_response import sgf_to_gtp
    from ..models.position import Position
    from ..models.validation_result import ValidationResult

logger = logging.getLogger(__name__)


async def validate_solution(
    engine: LocalEngine,
    position: Position,
    correct_move_sgf: str,
    max_visits: int = 200,
    puzzle_id: str = "",
) -> ValidationResult:
    """Validate that the correct first move is indeed the best move.

    Args:
        engine: Running KataGo engine
        position: Initial board position
        correct_move_sgf: SGF coordinate of the correct move (e.g., "cg")
        max_visits: MCTS visits for analysis
        puzzle_id: Optional puzzle identifier

    Returns:
        ValidationResult with KataGo's assessment
    """
    correct_gtp = sgf_to_gtp(correct_move_sgf, position.board_size)

    # Step 1: Analyze the initial position (restricted to puzzle region)
    request = AnalysisRequest.with_puzzle_region(
        position=position,
        max_visits=max_visits,
        include_ownership=True,
        include_pv=True,
    )

    response = await engine.analyze(request)

    # Step 2: Find KataGo's top move and the correct move in results
    top = response.top_move
    correct_info = response.get_move(correct_gtp)

    if top is None:
        return ValidationResult(
            puzzle_id=puzzle_id,
            correct_move=correct_move_sgf,
            katago_agrees=False,
            katago_top_move="",
            confidence="low",
            flags=["no_analysis_result"],
        )

    top_sgf = top.sgf_coord
    katago_agrees = top.move.upper() == correct_gtp.upper()

    # If not top-1, check if it's in top-3
    top_3_moves = sorted(response.move_infos, key=lambda m: m.visits, reverse=True)[:3]
    in_top_3 = any(m.move.upper() == correct_gtp.upper() for m in top_3_moves)

    # Step 3: Determine confidence
    flags: list[str] = []
    confidence = "high"

    if correct_info is None:
        # Correct move not even in KataGo's candidate list
        confidence = "low"
        flags.append("correct_move_not_considered")
        correct_policy = 0.0
        correct_winrate = 0.0
    else:
        correct_policy = correct_info.policy_prior
        correct_winrate = correct_info.winrate

        if not katago_agrees and not in_top_3:
            confidence = "low"
            flags.append("not_in_top_3")
        elif not katago_agrees and in_top_3:
            confidence = "medium"

    # Check for special positions
    if correct_info and correct_info.winrate < 0.3:
        flags.append("low_winrate_suspicious")

    # Check for ko (multiple moves with similar high visit counts)
    if len(response.move_infos) >= 2:
        sorted_by_visits = sorted(response.move_infos, key=lambda m: m.visits, reverse=True)
        if sorted_by_visits[1].visits > sorted_by_visits[0].visits * 0.8:
            flags.append("ko_candidate")

    return ValidationResult(
        puzzle_id=puzzle_id,
        correct_move=correct_move_sgf,
        katago_agrees=katago_agrees,
        katago_top_move=top_sgf,
        katago_top_move_policy=top.policy_prior,
        correct_move_policy=correct_policy,
        correct_move_winrate=correct_winrate,
        visits_used=response.total_visits,
        confidence=confidence,
        flags=flags,
    )
