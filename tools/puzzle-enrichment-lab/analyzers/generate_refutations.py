"""Task A.2: Generate wrong-move refutations (config-driven).

Finds the most tempting wrong first moves (high policy, but losing)
and generates their refutation sequences.

A.2.1 — identify_candidates(): Filter and rank candidate wrong moves
A.2.2 — generate_single_refutation(): Generate refutation for one wrong move
A.2.2 — generate_refutations(): Orchestrate full refutation pipeline

All thresholds loaded from config/katago-enrichment.json via config package.
"""

from __future__ import annotations

import logging
import math

try:
    from config import EnrichmentConfig, load_enrichment_config
    from engine.local_subprocess import LocalEngine
    from models.analysis_request import AnalysisRequest
    from models.analysis_response import AnalysisResponse, MoveAnalysis, gtp_to_sgf, sgf_to_gtp
    from models.position import Color, Position
    from models.refutation_result import Refutation, RefutationResult
except ImportError:
    from ..config import EnrichmentConfig, load_enrichment_config
    from ..engine.local_subprocess import LocalEngine
    from ..models.analysis_request import AnalysisRequest
    from ..models.analysis_response import AnalysisResponse, MoveAnalysis, gtp_to_sgf, sgf_to_gtp
    from ..models.position import Position
    from ..models.refutation_result import Refutation, RefutationResult

logger = logging.getLogger(__name__)


def compute_ownership_delta(
    root_ownership: list[float] | None,
    move_ownership: list[list[float]] | list[float] | None,
    board_size: int = 19,
) -> float:
    """Compute max ownership flip between root and after-move positions (PI-1).

    Ownership delta captures how much board control changes from playing
    a move. A large delta indicates the move dramatically shifts group
    status (e.g., alive → dead), making it a "teaching refutation" even
    if winrate delta is small.

    Args:
        root_ownership: Flat ownership array from initial position (board_size²).
        move_ownership: Per-move ownership from MoveAnalysis. May be a flat
            list or a nested list.
        board_size: Board size for bounds checking.

    Returns:
        Maximum absolute ownership change across all intersections.
        Returns 0.0 when ownership data is unavailable.
    """
    if root_ownership is None or move_ownership is None:
        return 0.0

    # Flatten if nested
    flat_move: list[float]
    if move_ownership and isinstance(move_ownership[0], list):
        flat_move = [v for row in move_ownership for v in row]
    else:
        flat_move = list(move_ownership)  # type: ignore[arg-type]

    expected = board_size * board_size
    if len(root_ownership) < expected or len(flat_move) < expected:
        return 0.0

    max_delta = 0.0
    for i in range(expected):
        delta = abs(root_ownership[i] - flat_move[i])
        if delta > max_delta:
            max_delta = delta
    return max_delta


def _enrich_curated_policy(
    curated_refutations: list[Refutation],
    initial_analysis: AnalysisResponse | None,
    board_size: int,
) -> None:
    """Enrich curated refutations with KataGo signals from initial analysis.

    Curated wrong branches from SGF don't have neural-net data (policy,
    winrate).  When the initial KataGo analysis is available, look up each
    curated move's policy prior AND winrate to enable accurate trap_density
    computation.  Without winrate enrichment the trap_density numerator
    (sum |winrate_delta| * policy) stays zero even when policy is non-zero.

    Mutates refutations in-place.
    """
    if initial_analysis is None or not initial_analysis.move_infos:
        return

    # Build GTP→signal lookups from initial analysis
    policy_lookup: dict[str, float] = {}
    winrate_lookup: dict[str, float] = {}
    score_lookup: dict[str, float] = {}
    for mi in initial_analysis.move_infos:
        key = mi.move.upper()
        policy_lookup[key] = mi.policy_prior
        winrate_lookup[key] = mi.winrate
        score_lookup[key] = mi.score_lead

    root_wr = initial_analysis.root_winrate
    root_score = initial_analysis.root_score
    enriched_policy = 0
    enriched_winrate = 0
    enriched_score = 0

    for ref in curated_refutations:
        gtp_coord = sgf_to_gtp(ref.wrong_move, board_size)
        gtp_key = gtp_coord.upper() if gtp_coord else ""

        # Enrich policy prior
        if ref.wrong_move_policy < 1e-9:
            prior = policy_lookup.get(gtp_key, 0.0)
            if prior > 0:
                ref.wrong_move_policy = prior
                enriched_policy += 1

        # Enrich winrate delta (needed for trap_density numerator)
        if abs(ref.winrate_delta) < 1e-9 and abs(ref.winrate_after_wrong) < 1e-9:
            wr = winrate_lookup.get(gtp_key)
            if wr is not None:
                ref.winrate_after_wrong = wr
                ref.winrate_delta = wr - root_wr  # negative = bad move
                enriched_winrate += 1

        # Enrich score delta (for score-based trap density)
        if abs(ref.score_delta) < 1e-9:
            sl = score_lookup.get(gtp_key)
            if sl is not None:
                ref.score_delta = sl - root_score
                enriched_score += 1

    if enriched_policy or enriched_winrate or enriched_score:
        logger.info(
            "Enriched curated refutations: %d/%d policy, %d/%d winrate, %d/%d score",
            enriched_policy, len(curated_refutations),
            enriched_winrate, len(curated_refutations),
            enriched_score, len(curated_refutations),
        )


# ---------------------------------------------------------------------------
# A.2.1 — Identify candidate wrong moves
# ---------------------------------------------------------------------------


def _calculate_effective_noise(
    overrides_cfg: object,
    board_size: int,
) -> float:
    """Compute effective Dirichlet noise from config and board size.

    When noise_scaling == "board_scaled", scales the base noise by
    reference_area / board_area so smaller boards get proportionally
    higher noise (PI-5).  Otherwise returns the fixed wide_root_noise.
    """
    noise = overrides_cfg.wide_root_noise  # type: ignore[attr-defined]
    if overrides_cfg.noise_scaling == "board_scaled":  # type: ignore[attr-defined]
        board_area = max(1, board_size * board_size)
        noise = (
            overrides_cfg.noise_base  # type: ignore[attr-defined]
            * overrides_cfg.noise_reference_area  # type: ignore[attr-defined]
            / board_area
        )
    return noise


def identify_candidates(
    analysis: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig | None = None,
    nearby_moves: list[str] | None = None,
    board_size: int = 19,
) -> list[MoveAnalysis]:
    """Identify candidate wrong moves from initial analysis.

    Filters out the correct move and pass, applies policy threshold,
    optionally filters by spatial locality (Chebyshev distance from stones),
    sorts by policy descending (most tempting first), and caps at
    candidate_max_count from config.

    Args:
        analysis: KataGo analysis of the initial position.
        correct_move_gtp: GTP coordinate of the correct first move.
        config: Enrichment config (loads default if None).
        nearby_moves: If provided, only candidates whose GTP coord is in this
            set are kept (spatial locality filter, Phase R.1.3).
        board_size: Board size for ownership delta calculation (default 19).

    Returns:
        List of MoveAnalysis for candidate wrong moves, sorted by
        policy_prior descending, capped at candidate_max_count.
    """
    if config is None:
        config = load_enrichment_config()

    min_policy = config.refutations.candidate_min_policy
    max_count = config.refutations.candidate_max_count

    # Build nearby_moves lookup set (case-insensitive GTP matching)
    nearby_set: set[str] | None = None
    if nearby_moves is not None:
        nearby_set = {m.upper() for m in nearby_moves}

    candidates = [
        m for m in analysis.move_infos
        if m.move.upper() != correct_move_gtp.upper()
        and m.move.lower() != "pass"
        and m.policy_prior >= min_policy
        and (nearby_set is None or m.move.upper() in nearby_set)
    ]

    # T16B: Temperature-weighted scoring (KaTrain-style)
    scoring = config.refutations.candidate_scoring
    root_score = analysis.root_score
    ownership_weight = config.refutations.ownership_delta_weight
    root_ownership = analysis.ownership

    if scoring.mode == "temperature" and root_score != 0.0:
        temperature = scoring.temperature
        # RC-4 fix: use typed dict instead of monkey-patching MoveAnalysis
        temp_scores: dict[str, float] = {}
        for m in candidates:
            points_lost = max(0.0, root_score - m.score_lead) if root_score > 0 else max(0.0, m.score_lead - root_score)
            weight = math.exp(-temperature * points_lost)
            base_score = m.policy_prior * weight

            # PI-1: Ownership delta composite scoring
            if ownership_weight > 0 and root_ownership is not None:
                own_delta = compute_ownership_delta(root_ownership, m.ownership, board_size)
                wr_delta = abs(m.winrate - analysis.root_winrate)
                composite = wr_delta * (1 - ownership_weight) + own_delta * ownership_weight
                base_score *= (1 + composite)

            temp_scores[m.move] = base_score
        candidates.sort(key=lambda m: temp_scores.get(m.move, m.policy_prior), reverse=True)
    else:
        # Legacy: sort by policy descending (most tempting wrong moves first)
        # PI-1: If ownership weight > 0, boost candidates with high ownership delta
        if ownership_weight > 0 and root_ownership is not None:
            own_scores: dict[str, float] = {}
            for m in candidates:
                own_delta = compute_ownership_delta(root_ownership, m.ownership, board_size)
                wr_delta = abs(m.winrate - analysis.root_winrate)
                composite = wr_delta * (1 - ownership_weight) + own_delta * ownership_weight
                own_scores[m.move] = m.policy_prior * (1 + composite)
            candidates.sort(key=lambda m: own_scores.get(m.move, m.policy_prior), reverse=True)
        else:
            candidates.sort(key=lambda m: m.policy_prior, reverse=True)

    # PI-3: Score-delta rescue — re-include moves excluded by min_policy
    # if their score-lead delta is large enough (feature-gated).
    # NOTE: Rescue is dormant when candidate_min_policy=0.0 (production default)
    # because all moves satisfy policy >= 0.0 and skip the rescue path.
    # Two config changes needed to activate: score_delta_enabled=True AND min_policy > 0.
    rescued_count = 0
    if config.refutations.score_delta_enabled:
        candidate_moves = {m.move.upper() for m in candidates}
        threshold = config.refutations.score_delta_threshold
        root_score_val = analysis.root_score
        for m in analysis.move_infos:
            if m.move.upper() in candidate_moves:
                continue
            if m.move.upper() == correct_move_gtp.upper():
                continue
            if m.move.lower() == "pass":
                continue
            if nearby_set is not None and m.move.upper() not in nearby_set:
                continue
            if m.policy_prior >= min_policy:
                continue  # already would have been included
            if abs(root_score_val - m.score_lead) >= threshold:
                candidates.append(m)
                candidate_moves.add(m.move.upper())
                rescued_count += 1
        if rescued_count:
            logger.debug(
                "PI-3: Score-delta rescue included %d additional candidate(s) "
                "(threshold=%.1f)",
                rescued_count, threshold,
            )

    result = candidates[:max_count]

    filtered_count = len(analysis.move_infos) - len(candidates) - 1  # -1 for correct move
    logger.debug(
        f"Identified {len(result)} candidate wrong moves "
        f"(from {len(analysis.move_infos)} total, "
        f"min_policy={min_policy}, max={max_count}"
        f"{f', locality_filtered={filtered_count}' if nearby_set else ''})"
    )

    return result


# ---------------------------------------------------------------------------
# A.2.2 — Generate refutation for a single wrong move
# ---------------------------------------------------------------------------


async def generate_single_refutation(
    engine: LocalEngine,
    position: Position,
    wrong_move_gtp: str,
    wrong_move_policy: float,
    initial_winrate: float,
    config: EnrichmentConfig | None = None,
    ko_type: str = "none",
    initial_score: float = 0.0,
    allowed_moves: list[str] | None = None,
    override_settings: dict[str, int | float | str | bool] | None = None,
    root_ownership: list[float] | None = None,
) -> Refutation | None:
    """Generate refutation sequence for a single wrong move.

    Args:
        engine: Running KataGo engine.
        position: Initial board position.
        wrong_move_gtp: GTP coordinate of the wrong move to refute.
        wrong_move_policy: Policy prior of the wrong move.
        initial_winrate: Puzzle player's winrate at the initial position.
        config: Enrichment config (loads default if None).
        ko_type: Ko context for delta threshold adjustment (Q14).
        initial_score: Puzzle player's score lead at the initial position.
        allowed_moves: T17 — restrict refutation analysis to puzzle region.
        override_settings: T18 — per-query KataGo config overrides.
        root_ownership: R-1 — root position ownership for ownership_delta computation.

    Returns:
        Refutation with PV and depth, or None if delta too small.
    """
    if config is None:
        config = load_enrichment_config()

    delta_threshold = config.refutations.delta_threshold
    # Q14: Ko-aware delta threshold — ko puzzles have oscillating winrates
    # where standard delta is too aggressive. Use teaching.ko_delta_threshold.
    if ko_type in ("direct", "approach") and config.teaching:
        delta_threshold = config.teaching.ko_delta_threshold
        logger.info(
            "Refutation %s: ko-aware threshold=%.3f (ko_type=%s)",
            wrong_move_gtp, delta_threshold, ko_type,
        )
    refutation_visits = config.refutations.refutation_visits
    refutation_cfg = config.refutations

    # PI-6: Forced minimum visits for low-policy candidates
    effective_refutation_visits = refutation_visits
    if (
        refutation_cfg.forced_min_visits_formula
        and wrong_move_policy > 0
    ):
        forced_visits = int(math.sqrt(
            refutation_cfg.forced_visits_k * wrong_move_policy * refutation_visits
        ))
        if forced_visits > effective_refutation_visits:
            effective_refutation_visits = forced_visits
            logger.debug(
                "PI-6: Forced min visits for %s: policy=%.4f, k=%.1f, "
                "base=%d → forced=%d",
                wrong_move_gtp, wrong_move_policy,
                refutation_cfg.forced_visits_k, refutation_visits, forced_visits,
            )

    logger.info(
        "Refutation %s: baseline_wr=%.3f, policy=%.4f, "
        "delta_threshold=%.3f, visits=%d",
        wrong_move_gtp, initial_winrate, wrong_move_policy,
        delta_threshold, effective_refutation_visits,
    )

    player = position.player_to_move

    # Play the wrong move and analyze from opponent's perspective
    request = AnalysisRequest(
        position=position,
        max_visits=effective_refutation_visits,
        include_ownership=True,
        include_pv=True,
        moves=[[player.value, wrong_move_gtp]],
        allowed_moves=allowed_moves,
        override_settings=override_settings,
    )

    after_wrong = await engine.analyze(request)

    # The opponent's best response is the refutation
    opp_best = after_wrong.top_move
    if opp_best is None:
        logger.debug(f"No opponent response for wrong move {wrong_move_gtp}")
        return None

    # PI-12: Best-resistance line generation
    # Evaluate top N alternative opponent responses and select the one
    # that maximizes punishment (highest winrate delta for the refutation)
    if (
        config.refutations.best_resistance_enabled
        and len(after_wrong.move_infos) > 1
    ):
        max_candidates = config.refutations.best_resistance_max_candidates
        sorted_opp_responses = sorted(
            after_wrong.move_infos, key=lambda m: m.visits, reverse=True,
        )[:max_candidates]
        best_punishment = abs(1.0 - opp_best.winrate - initial_winrate)
        best_response = opp_best
        for alt_resp in sorted_opp_responses[1:]:  # Skip first (already opp_best)
            alt_punishment = abs(1.0 - alt_resp.winrate - initial_winrate)
            if alt_punishment > best_punishment:
                best_punishment = alt_punishment
                best_response = alt_resp
                logger.debug(
                    "PI-12: Best-resistance for %s: %s → %s "
                    "(punishment %.3f > %.3f)",
                    wrong_move_gtp, opp_best.move, alt_resp.move,
                    alt_punishment, abs(1.0 - opp_best.winrate - initial_winrate),
                )
        if best_response is not opp_best:
            logger.info(
                "PI-12: Best-resistance override for %s: %s → %s",
                wrong_move_gtp, opp_best.move, best_response.move,
            )
            opp_best = best_response

    # Under SIDETOMOVE: after the puzzle player's wrong move, it becomes the
    # opponent's turn. KataGo reports opp_best.winrate from the OPPONENT's
    # perspective (high = good for opponent = bad for puzzle player).
    # Flipping via (1.0 - wr) converts to the puzzle player's perspective,
    # so winrate_delta correctly measures how much the wrong move hurt.
    winrate_after = 1.0 - opp_best.winrate
    winrate_delta = winrate_after - initial_winrate

    # Only include if the move actually loses enough (delta exceeds threshold)
    # Score-based fallback: when winrate delta is too small (all moves "win")
    # but score_lead delta shows this move is clearly worse, still generate
    # the refutation.  This handles chase/capture puzzles where every move
    # captures eventually but only one move is optimal.
    score_after = -opp_best.score_lead
    score_delta = score_after - initial_score

    is_score_based = False
    if abs(winrate_delta) < delta_threshold:
        # PI-3: Score-lead delta as complementary refutation filter
        sd_cfg = config.refutations
        if (
            sd_cfg.score_delta_enabled
            and abs(score_delta) >= sd_cfg.score_delta_threshold
        ):
            is_score_based = True
            logger.info(
                "Refutation %s: winrate delta %.3f below threshold %.3f, "
                "but score delta %.1f exceeds score threshold %.1f — "
                "generating score-delta refutation (PI-3)",
                wrong_move_gtp, winrate_delta, delta_threshold,
                score_delta, sd_cfg.score_delta_threshold,
            )
        else:
            sb_cfg = config.refutations.suboptimal_branches
            if (
                sb_cfg.enabled
                and abs(score_delta) >= sb_cfg.score_delta_threshold
            ):
                is_score_based = True
                logger.info(
                    "Refutation %s: winrate delta %.3f below threshold %.3f, "
                    "but score delta %.1f exceeds score threshold %.1f — "
                    "generating score-based refutation",
                    wrong_move_gtp, winrate_delta, delta_threshold,
                    score_delta, sb_cfg.score_delta_threshold,
                )
            else:
                logger.debug(
                    "Skipping %s: winrate delta %.3f below threshold %.3f"
                    "%s",
                    wrong_move_gtp, winrate_delta, delta_threshold,
                    f" (score delta {score_delta:.1f} also below "
                    f"{sb_cfg.score_delta_threshold if sb_cfg.enabled else 'N/A'})" if sb_cfg.enabled else "",
                )
                return None

    # Build refutation PV branches (opponent's response + continuation)
    # P0.4: Use configurable PV cap instead of hardcoded 4
    board_size = position.board_size
    sb_pv_cap = config.refutations.suboptimal_branches.max_pv_depth if is_score_based else None
    pv_cap = sb_pv_cap or config.refutations.max_pv_length
    branch_limit = min(3, len(after_wrong.move_infos))
    sorted_responses = sorted(after_wrong.move_infos, key=lambda m: m.visits, reverse=True)
    pv_branches: list[list[str]] = []

    for response_move in sorted_responses[:branch_limit]:
        if response_move.move.lower() == "pass":
            continue
        branch: list[str] = []
        if response_move.pv:
            for gtp_move in response_move.pv[:pv_cap]:
                sgf_coord = gtp_to_sgf(gtp_move, board_size)
                if sgf_coord:
                    branch.append(sgf_coord)
        else:
            sgf_coord = gtp_to_sgf(response_move.move, board_size)
            if sgf_coord:
                branch.append(sgf_coord)
        if branch:
            pv_branches.append(branch)

    # Backward-compatible primary branch for consumers that still read refutation_sequence
    pv_sgf: list[str] = pv_branches[0] if pv_branches else []

    # Refutation depth = deepest branch depth
    refutation_depth = max((len(branch) for branch in pv_branches), default=(len(pv_sgf) if pv_sgf else 1))

    logger.debug(
        f"Refutation for {wrong_move_gtp}: "
        f"PV={pv_sgf}, depth={refutation_depth}, "
        f"delta={winrate_delta:.3f}"
    )

    # Compute score delta: flip from opponent perspective to puzzle player
    # (already computed above for score-based fallback check)

    # T18B: Tenuki detection — flag when PV response is far from wrong move
    tenuki_flagged = False
    if config.refutations.tenuki_rejection.enabled and opp_best.move:
        wrong_sgf = gtp_to_sgf(wrong_move_gtp, board_size)
        pv_response_sgf = gtp_to_sgf(opp_best.move, board_size)
        if wrong_sgf and pv_response_sgf and len(wrong_sgf) >= 2 and len(pv_response_sgf) >= 2:
            wx, wy = ord(wrong_sgf[0]) - ord('a'), ord(wrong_sgf[1]) - ord('a')
            px, py = ord(pv_response_sgf[0]) - ord('a'), ord(pv_response_sgf[1]) - ord('a')
            manhattan = abs(wx - px) + abs(wy - py)
            if manhattan > config.refutations.tenuki_rejection.manhattan_threshold:
                tenuki_flagged = True
                logger.info(
                    "Tenuki flagged: %s → %s (manhattan=%d, threshold=%.1f)",
                    wrong_move_gtp, opp_best.move, manhattan,
                    config.refutations.tenuki_rejection.manhattan_threshold,
                )

    # R-1: Compute ownership delta (max absolute ownership shift) for teaching signals
    own_delta = 0.0
    if root_ownership is not None and after_wrong.ownership:
        own_delta = compute_ownership_delta(
            root_ownership, after_wrong.ownership, position.board_size,
        )

    return Refutation(
        wrong_move=gtp_to_sgf(wrong_move_gtp, board_size),
        wrong_move_policy=wrong_move_policy,
        refutation_sequence=pv_sgf,
        refutation_branches=pv_branches,
        winrate_after_wrong=winrate_after,
        winrate_delta=winrate_delta,
        score_delta=score_delta,
        refutation_depth=refutation_depth,
        refutation_type="score_based" if is_score_based else "unclassified",
        tenuki_flagged=tenuki_flagged,
        ownership_delta=own_delta,
    )


# ---------------------------------------------------------------------------
# A.2.2 — Orchestrator: full refutation pipeline
# ---------------------------------------------------------------------------


async def generate_refutations(
    engine: LocalEngine,
    position: Position,
    correct_move_gtp: str,
    initial_analysis: AnalysisResponse | None = None,
    config: EnrichmentConfig | None = None,
    max_visits: int | None = None,
    puzzle_id: str = "",
    nearby_moves: list[str] | None = None,
    curated_wrongs: list[dict] | None = None,
    entropy_roi: object | None = None,
) -> RefutationResult:
    """Generate refutation sequences for plausible wrong first moves.

    Orchestrates: identify_candidates → generate_single_refutation for each
    → sort by policy → cap at refutation_max_count.

    Args:
        engine: Running KataGo engine.
        position: Board position (framed if available, original otherwise).
        correct_move_gtp: GTP coordinate of the correct first move (excluded).
        initial_analysis: Reuse analysis from validate_correct_move (or None to re-analyze).
        config: Enrichment config (loads default if None).
        max_visits: Optional override for initial analysis visits.
        puzzle_id: Optional identifier.
        nearby_moves: GTP coords near stones for spatial locality filter (Phase R.1.3).
        curated_wrongs: Wrong branches from SGF (Phase R.2.1). Each dict has
            {"move": "ab" (SGF coord), "source": "WV[]", "comment": "Wrong."}.

    Returns:
        RefutationResult with wrong moves and refutation sequences.
    """
    if config is None:
        config = load_enrichment_config()

    refutation_visits = config.refutations.refutation_visits
    if max_visits is None:
        max_visits = refutation_visits

    # Phase R.2.1: Build curated refutations from SGF wrong branches
    curated_refutations: list[Refutation] = []
    curated_move_sgfs: set[str] = set()
    if curated_wrongs:
        for cw in curated_wrongs:
            sgf_coord = cw["move"]
            curated_move_sgfs.add(sgf_coord)
            curated_refutations.append(Refutation(
                wrong_move=sgf_coord,
                wrong_move_policy=0.0,  # Not available from SGF
                refutation_sequence=[],  # Curated doesn't have AI PV
                refutation_branches=[],
                winrate_after_wrong=0.0,
                winrate_delta=0.0,
                refutation_depth=1,
                refutation_type="curated",
            ))
        logger.info(
            f"Found {len(curated_refutations)} curated wrong branches for puzzle {puzzle_id}: "
            f"{[cw['move'] for cw in curated_wrongs]}"
        )

    # If curated wrongs already meet the refutation_max_count, skip AI generation
    max_refutations = config.refutations.refutation_max_count
    if len(curated_refutations) >= max_refutations:
        # Enrich curated moves with policy data before returning (Bug fix: trap_density=0)
        _enrich_curated_policy(
            curated_refutations[:max_refutations],
            initial_analysis,
            position.board_size,
        )
        logger.info(
            f"Curated wrongs ({len(curated_refutations)}) meet refutation_max_count "
            f"({max_refutations}) — skipping AI refutation generation for puzzle {puzzle_id}"
        )
        return RefutationResult(
            puzzle_id=puzzle_id,
            refutations=curated_refutations[:max_refutations],
            total_candidates_evaluated=0,
            visits_per_candidate=0,
        )

    # Step 1: Get initial analysis if not provided
    if initial_analysis is None:
        request = AnalysisRequest.with_puzzle_region(
            position=position,
            max_visits=max_visits,
            include_ownership=True,
            include_pv=True,
        )
        initial_analysis = await engine.analyze(request)

    initial_winrate = initial_analysis.root_winrate
    initial_score = initial_analysis.root_score

    # Enrich any curated refutations with policy data from the initial analysis
    if curated_refutations:
        _enrich_curated_policy(
            curated_refutations, initial_analysis, position.board_size,
        )

    # Step 2: Identify candidate wrong moves (with locality filter)
    candidates = identify_candidates(
        analysis=initial_analysis,
        correct_move_gtp=correct_move_gtp,
        config=config,
        nearby_moves=nearby_moves,
        board_size=position.board_size,
    )

    # PI-8: Diversified root candidate harvesting
    # After initial scan, run a secondary scan with higher noise to find
    # human-tempting wrong moves missed by the first pass
    if config.refutations.multi_pass_harvesting and initial_analysis is not None:
        overrides_cfg_early = config.refutations.refutation_overrides
        base_noise = _calculate_effective_noise(overrides_cfg_early, position.board_size)
        secondary_noise = base_noise * config.refutations.secondary_noise_multiplier
        secondary_request = AnalysisRequest.with_puzzle_region(
            position=position,
            max_visits=max_visits,
            include_ownership=True,
            include_pv=True,
            override_settings={
                "rootPolicyTemperature": overrides_cfg_early.root_policy_temperature,
                "rootFpuReductionMax": overrides_cfg_early.root_fpu_reduction_max,
                "wideRootNoise": secondary_noise,
            },
        )
        secondary_analysis = await engine.analyze(secondary_request)
        secondary_candidates = identify_candidates(
            analysis=secondary_analysis,
            correct_move_gtp=correct_move_gtp,
            config=config,
            nearby_moves=nearby_moves,
            board_size=position.board_size,
        )
        # Merge and deduplicate
        existing_moves = {m.move.upper() for m in candidates}
        new_from_secondary = 0
        for sc in secondary_candidates:
            if sc.move.upper() not in existing_moves:
                candidates.append(sc)
                existing_moves.add(sc.move.upper())
                new_from_secondary += 1
        if new_from_secondary:
            # Re-sort merged list by policy_prior before capping (RC-2).
            # Both passes share the same neural net policy priors, so
            # policy_prior is a fair cross-analysis ranking criterion.
            candidates.sort(key=lambda m: m.policy_prior, reverse=True)
            candidates = candidates[:config.refutations.candidate_max_count]
            logger.info(
                "PI-8: Multi-pass harvesting found %d new candidates "
                "(secondary noise=%.4f, total=%d)",
                new_from_secondary, secondary_noise, len(candidates),
            )

    if not candidates and not curated_refutations:
        return RefutationResult(
            puzzle_id=puzzle_id,
            refutations=[],
            total_candidates_evaluated=0,
            visits_per_candidate=refutation_visits,
        )

    # T17: Build puzzle-region allowMoves for refutation queries
    refutation_allowed_moves: list[str] | None = None
    if entropy_roi is not None:
        try:
            from analyzers.frame_adapter import get_allow_moves_with_fallback
            refutation_allowed_moves = get_allow_moves_with_fallback(
                position, entropy_roi=entropy_roi,
            )
        except Exception:
            refutation_allowed_moves = position.get_puzzle_region_moves(margin=2)
    else:
        region = position.get_puzzle_region_moves(margin=2)
        if region:
            refutation_allowed_moves = region

    # T18: Build override settings for refutation queries
    overrides_cfg = config.refutations.refutation_overrides
    # PI-5: Board-size-scaled Dirichlet noise
    effective_noise = _calculate_effective_noise(overrides_cfg, position.board_size)
    if overrides_cfg.noise_scaling == "board_scaled":
        logger.debug(
            "PI-5: Board-scaled noise: board_size=%d, area=%d, "
            "base=%.4f, ref_area=%d → effective_noise=%.4f",
            position.board_size, position.board_size ** 2,
            overrides_cfg.noise_base, overrides_cfg.noise_reference_area, effective_noise,
        )
    refutation_override_settings: dict[str, int | float | str | bool] = {
        "rootPolicyTemperature": overrides_cfg.root_policy_temperature,
        "rootFpuReductionMax": overrides_cfg.root_fpu_reduction_max,
        "wideRootNoise": effective_noise,
    }

    # Step 3: Generate refutation for each candidate (skip curated moves)
    refutations: list[Refutation] = []
    tenuki_rejected_count = 0
    for candidate in candidates:
        # Skip if this move is already covered by a curated wrong branch
        candidate_sgf = gtp_to_sgf(candidate.move, position.board_size)
        if candidate_sgf and candidate_sgf in curated_move_sgfs:
            logger.debug(
                f"Skipping AI refutation for {candidate.move} — "
                f"already in curated wrongs (SGF: {candidate_sgf})"
            )
            continue

        refutation = await generate_single_refutation(
            engine=engine,
            position=position,
            wrong_move_gtp=candidate.move,
            wrong_move_policy=candidate.policy_prior,
            initial_winrate=initial_winrate,
            config=config,
            initial_score=initial_score,
            allowed_moves=refutation_allowed_moves,
            override_settings=refutation_override_settings,
            root_ownership=initial_analysis.ownership if initial_analysis else None,
        )
        if refutation is not None:
            refutation.refutation_type = "ai_generated"
            if refutation.tenuki_flagged:
                tenuki_rejected_count += 1
            refutations.append(refutation)

    if tenuki_rejected_count > 0:
        logger.info(
            "Tenuki rejection: %d/%d refutations flagged for puzzle %s",
            tenuki_rejected_count, len(refutations), puzzle_id,
        )

    # Step 4: Merge curated + AI refutations. Curated first (trusted), then AI.
    all_refutations = curated_refutations + refutations
    all_refutations = all_refutations[:max_refutations]

    logger.info(
        f"Generated {len(all_refutations)} refutations for puzzle {puzzle_id} "
        f"({len(curated_refutations)} curated + {len(refutations)} AI, "
        f"from {len(candidates)} candidates)"
    )

    return RefutationResult(
        puzzle_id=puzzle_id,
        refutations=all_refutations,
        total_candidates_evaluated=len(candidates),
        visits_per_candidate=refutation_visits,
    )
