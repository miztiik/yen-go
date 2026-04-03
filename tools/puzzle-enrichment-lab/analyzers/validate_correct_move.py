"""Tag-aware correct move validation against KataGo analysis.

Task A.1.3: Validate correct move against KataGo with tag-aware dispatch.

Routes validation to specialized handlers based on puzzle tags:
- Life-and-death (10, 14): ownership-based thresholds
- Ko (12): delegated to ko_validation (A.1.5, stub here)
- Seki (16): combined 3-signal detection
- Tactical — ladder (34), net (36), snapback (30): PV pattern matching
- Capture-race (60): liberty-focused validation
- Connection/cutting (68, 70): group connectivity analysis
- Fallback: ownership-based (life-and-death)

All thresholds are loaded from config/katago-enrichment.json via config.py.
"""

from __future__ import annotations

import logging

try:
    from config import EnrichmentConfig, load_enrichment_config
    from models.analysis_response import AnalysisResponse
    from models.position import Color, Position
    from models.validation import CorrectMoveResult, ValidationStatus
except ImportError:
    from ..config import EnrichmentConfig, load_enrichment_config
    from ..models.analysis_response import AnalysisResponse
    from ..models.position import Color, Position
    from ..models.validation import CorrectMoveResult, ValidationStatus

logger = logging.getLogger(__name__)

# Re-export for backward compatibility — existing consumers can still
# ``from analyzers.validate_correct_move import ValidationStatus, CorrectMoveResult``
__all__ = ["ValidationStatus", "CorrectMoveResult"]


# ---------------------------------------------------------------------------
# Tag-aware dispatch table
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tag-ID lazy loader (B2 fix: config/tags.json is the single source of
# truth — integers must never be hardcoded in this module).
# ---------------------------------------------------------------------------

try:
    from analyzers.config_lookup import load_tag_slug_map
except ImportError:
    from ..analyzers.config_lookup import load_tag_slug_map

_TAG_CONSTS: dict | None = None


def _get_tag_consts() -> dict:
    """Return (and cache) all tag-ID constants needed by this module.

    Lazy-loads from config/tags.json on first call so that test code can
    call ``config.load_tag_ids(path=custom_path)`` before any validation
    to substitute a test fixture without patching module globals.
    """
    global _TAG_CONSTS
    if _TAG_CONSTS is not None:
        return _TAG_CONSTS

    slug_map = load_tag_slug_map()

    # Tactical tesuji slugs in tag-ID order (matches tags.json ordering).
    _tesuji_slugs = [
        "snapback", "double-atari", "ladder", "net", "throw-in",
        "clamp", "nakade", "connect-and-die", "under-the-stones",
        "liberty-shortage", "vital-point",
    ]
    tactical_slug: dict[int, str] = {slug_map[s]: s for s in _tesuji_slugs}

    _TAG_CONSTS = {
        "LIFE_AND_DEATH_IDS": frozenset({slug_map["life-and-death"], slug_map["living"]}),
        "KO_ID":              slug_map["ko"],
        "SEKI_ID":            slug_map["seki"],
        "CAPTURE_RACE_ID":    slug_map["capture-race"],
        "CONNECTION_IDS":     frozenset({slug_map["connection"], slug_map["cutting"]}),
        "TACTICAL_IDS":       frozenset(tactical_slug.keys()),
        "TACTICAL_SLUG":      tactical_slug,
    }
    return _TAG_CONSTS


def _dispatch_by_tags(tags: list[int]) -> str:
    """Determine which validator to use based on puzzle tags.

    Priority order (first match wins):
    1. Ko (12) — highest priority, overrides L&D
    2. Seki (16)
    3. Capture-race (60)
    4. Connection/cutting (68, 70)
    5. Tactical tesuji (30-50)
    6. Life-and-death (10, 14) — default for objective tags
    7. Fallback → life_and_death

    Returns:
        Validator name string: "ko", "seki", "capture_race",
        "connection", "tactical", "life_and_death"
    """
    tc = _get_tag_consts()
    tag_set = set(tags)

    # Priority 1: Ko
    if tc["KO_ID"] in tag_set:
        return "ko"

    # Priority 2: Seki
    if tc["SEKI_ID"] in tag_set:
        return "seki"

    # Priority 3: Capture-race
    if tc["CAPTURE_RACE_ID"] in tag_set:
        return "capture_race"

    # Priority 4: Connection/cutting
    if tag_set & tc["CONNECTION_IDS"]:
        return "connection"

    # Priority 5: Tactical tesuji
    if tag_set & tc["TACTICAL_IDS"]:
        return "tactical"

    # Priority 6: Life-and-death (or fallback)
    return "life_and_death"


# ---------------------------------------------------------------------------
# Core validation function (public API)
# ---------------------------------------------------------------------------


def validate_correct_move(
    response: AnalysisResponse,
    correct_move_gtp: str,
    tags: list[int],
    corner: str = "TL",
    move_order: str = "strict",
    all_correct_moves_gtp: list[str] | None = None,
    config: EnrichmentConfig | None = None,
    ko_type: str = "none",
    position: Position | None = None,
    source_tier: int = 0,
) -> CorrectMoveResult:
    """Validate the correct move against KataGo analysis using tag-aware dispatch.

    Args:
        response: KataGo analysis response for the position.
        correct_move_gtp: GTP coordinate of the correct move (e.g., "D1").
        tags: Numeric tag IDs from the puzzle's YT property.
        corner: YC property value (TL, TR, BL, BR, C, E).
        move_order: YO property (strict, flexible, miai).
        all_correct_moves_gtp: For miai puzzles, all correct moves.
        config: Enrichment config (loaded from file if None).
        ko_type: YK property value ("none", "direct", "approach").
        source_tier: Source quality tier (1-5, 0=unknown). Tier >= 4 softens
            REJECTED to FLAGGED for curated sources (D4).

    Returns:
        CorrectMoveResult with status, agreement, and diagnostic flags.
    """
    if config is None:
        config = load_enrichment_config()

    validator_name = _dispatch_by_tags(tags)
    logger.info(
        "Puzzle %s: dispatching to '%s' validator (tags=%s, ko_type=%s)",
        correct_move_gtp, validator_name, tags, ko_type,
    )

    # Miai handling: if move_order is "miai" and this isn't the top move,
    # check if ANY of the correct moves is highly ranked
    if move_order == "miai" and all_correct_moves_gtp:
        result = _validate_miai(
            response=response,
            correct_move_gtp=correct_move_gtp,
            all_correct_moves_gtp=all_correct_moves_gtp,
            config=config,
            corner=corner,
        )
        if result is not None:
            result.validator_used = f"miai+{validator_name}"
            return result

    # Dispatch to specialized validator
    if validator_name == "ko":
        # Full ko validation (A.1.5) — ko_type from YK property
        try:
            from analyzers.ko_validation import KoType, validate_ko
        except ImportError:
            from ..analyzers.ko_validation import KoType, validate_ko
        try:
            resolved_ko_type = KoType(ko_type)
        except ValueError:
            resolved_ko_type = KoType.DIRECT
        ko_result = validate_ko(
            response=response,
            correct_move_gtp=correct_move_gtp,
            ko_type=resolved_ko_type,
            config=config,
            position=position,
        )
        ko_result_obj = CorrectMoveResult(
            status=ko_result.status,
            katago_agrees=ko_result.katago_agrees,
            correct_move_gtp=ko_result.correct_move_gtp,
            katago_top_move=ko_result.katago_top_move,
            correct_move_winrate=ko_result.correct_move_winrate,
            correct_move_policy=ko_result.correct_move_policy,
            validator_used="ko",
            flags=ko_result.flags,
        )
        if source_tier >= config.validation.source_trust_min_tier and ko_result_obj.status == ValidationStatus.REJECTED:
            ko_result_obj.status = ValidationStatus.FLAGGED
            ko_result_obj.flags.append("source_trust_rescue")
        return ko_result_obj

    elif validator_name == "seki":
        result = _validate_seki(
            response=response,
            correct_move_gtp=correct_move_gtp,
            config=config,
        )
        result.validator_used = "seki"
        if source_tier >= config.validation.source_trust_min_tier and result.status == ValidationStatus.REJECTED:
            result.status = ValidationStatus.FLAGGED
            result.flags.append("source_trust_rescue")
        return result

    elif validator_name == "capture_race":
        result = _validate_capture_race(
            response=response,
            correct_move_gtp=correct_move_gtp,
            config=config,
        )
        result.validator_used = "capture_race"
        if source_tier >= config.validation.source_trust_min_tier and result.status == ValidationStatus.REJECTED:
            result.status = ValidationStatus.FLAGGED
            result.flags.append("source_trust_rescue")
        return result

    elif validator_name == "connection":
        result = _validate_connection(
            response=response,
            correct_move_gtp=correct_move_gtp,
            config=config,
        )
        result.validator_used = "connection"
        if source_tier >= config.validation.source_trust_min_tier and result.status == ValidationStatus.REJECTED:
            result.status = ValidationStatus.FLAGGED
            result.flags.append("source_trust_rescue")
        return result

    elif validator_name == "tactical":
        # Find the specific tactical tag for sub-dispatch
        tag_slug = "tactical"
        tslug = _get_tag_consts()["TACTICAL_SLUG"]
        for tid in tags:
            if tid in tslug:
                tag_slug = tslug[tid]
                break
        result = _validate_tactical(
            response=response,
            correct_move_gtp=correct_move_gtp,
            config=config,
            tag_slug=tag_slug,
        )
        result.validator_used = f"tactical:{tag_slug}"
        if source_tier >= config.validation.source_trust_min_tier and result.status == ValidationStatus.REJECTED:
            result.status = ValidationStatus.FLAGGED
            result.flags.append("source_trust_rescue")
        return result

    else:
        # Default: life-and-death ownership-based
        result = _validate_life_and_death(
            response=response,
            correct_move_gtp=correct_move_gtp,
            config=config,
            corner=corner,
            position=position,
        )
        result.validator_used = "life_and_death"
        # D4: Source trust post-processing — soften REJECTED→FLAGGED for curated sources
        if source_tier >= config.validation.source_trust_min_tier and result.status == ValidationStatus.REJECTED:
            result.status = ValidationStatus.FLAGGED
            result.flags.append("source_trust_rescue")
        return result


# ---------------------------------------------------------------------------
# Specialized validators
# ---------------------------------------------------------------------------


def _classify_move(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> tuple[bool, bool, float, float, int, int]:
    """Common classification: is correct move top? In top-N? Winrate? Policy? Rank? Visits?

    Returns:
        (is_top, in_top_n, correct_winrate, correct_policy, rank, correct_move_visits)
        rank is 1-based ordinal position among all moves sorted by visits.
        0 means the move was not found in analysis output.
        correct_move_visits: MCTS visits KataGo allocated to this move (C1 fix).
    """
    top = response.top_move
    if top is None:
        return False, False, 0.0, 0.0, 0, 0

    is_top = top.move.upper() == correct_move_gtp.upper()

    top_n = config.validation.rejected_not_in_top_n
    sorted_moves = sorted(response.move_infos, key=lambda m: m.visits, reverse=True)
    top_n_moves = sorted_moves[:top_n]
    in_top_n = any(m.move.upper() == correct_move_gtp.upper() for m in top_n_moves)

    # Compute 1-based rank
    rank = 0
    for i, m in enumerate(sorted_moves, 1):
        if m.move.upper() == correct_move_gtp.upper():
            rank = i
            break

    correct_info = response.get_move(correct_move_gtp)
    correct_winrate = correct_info.winrate if correct_info else 0.0
    correct_policy = correct_info.policy_prior if correct_info else 0.0
    correct_visits = correct_info.visits if correct_info else 0  # C1: per-move visit count

    logger.info(
        "Classify %s: is_top=%s, in_top_n=%s, winrate=%.3f, "
        "policy=%.3f, rank=%d, visits=%d",
        correct_move_gtp, is_top, in_top_n,
        correct_winrate, correct_policy, rank, correct_visits,
    )

    return is_top, in_top_n, correct_winrate, correct_policy, rank, correct_visits


def _build_diagnostic_flags(
    is_top: bool,
    in_top_n: bool,
    correct_winrate: float,
    rank: int,
    config: EnrichmentConfig,
    top_move_winrate: float = 0.0,
) -> list[str]:
    """Build diagnostic flags for any non-ACCEPTED outcome.

    Produces human-readable flags like ``rank:5``, ``winrate:0.644``,
    ``top_n:5``, and ``winrate_delta:-0.12`` so reviewers can triage
    flagged/rejected puzzles WITHOUT re-running analysis.
    """
    flags: list[str] = []
    top_n = config.validation.rejected_not_in_top_n

    if rank > 0:
        flags.append(f"rank:{rank}")
        # D2: Rank-band analytics flags for quality scoring
        if rank <= 3:
            flags.append("rank_band:top3")
        elif rank <= 10:
            flags.append("rank_band:top10")
        elif rank <= top_n:
            flags.append("rank_band:top20")
        else:
            flags.append("rank_band:outside_top20")
    else:
        flags.append("rank:unranked")
        flags.append("rank_band:unranked")

    flags.append(f"winrate:{correct_winrate:.3f}")
    flags.append(f"top_n:{top_n}")

    if top_move_winrate > 0.0 and not is_top:
        delta = correct_winrate - top_move_winrate
        flags.append(f"winrate_delta:{delta:+.3f}")

    return flags


def _status_from_classification(
    correct_winrate: float,
    config: EnrichmentConfig,
    correct_move_visits: int = 0,
    source_tier: int = 0,
) -> tuple[ValidationStatus, list[str]]:
    """Determine validation status from winrate and per-move visits.

    Rank is no longer used as a gating signal.  PUCT allocates visits
    based on the neural net's policy prior, which is systematically
    miscalibrated for tsumego — correct moves often rank low by visits
    despite being clearly correct by winrate.  Rank is preserved in
    quality scoring (qk) where it measures how "surprising" the puzzle is.

    D4: Source trust — puzzles from high-tier curated sources (tier >= 4)
    get REJECTED softened to FLAGGED, since curated collections have
    <0.1% error rate and AI disagreement is more likely a KataGo limitation.

    Decision tree (winrate + visits only):
      WR >= winrate_rescue_auto_accept (0.85)        → ACCEPTED
      WR >= flagged_value_high (0.70) + visits >= 50  → ACCEPTED
      WR >= flagged_value_high (0.70) + visits < 50   → FLAGGED (under-explored)
      WR >= flagged_value_low  (0.30)                 → FLAGGED (uncertain)
      WR <  flagged_value_low  (0.30)                 → REJECTED (or FLAGGED if trusted source)

    Returns:
        Tuple of (status, reason_flags).
    """
    v = config.validation
    min_visits = v.min_visits_for_accept

    if correct_winrate >= v.winrate_rescue_auto_accept:
        return ValidationStatus.ACCEPTED, []
    elif correct_winrate >= v.flagged_value_high:
        if correct_move_visits >= min_visits:
            return ValidationStatus.ACCEPTED, []
        else:
            return ValidationStatus.FLAGGED, ["reason:under_explored"]
    elif correct_winrate >= v.flagged_value_low:
        return ValidationStatus.FLAGGED, ["reason:uncertain_winrate"]
    else:
        # D4: Source trust — soften REJECTED to FLAGGED for curated sources
        if source_tier >= v.source_trust_min_tier:
            return ValidationStatus.FLAGGED, ["reason:low_winrate", "source_trust_rescue"]
        return ValidationStatus.REJECTED, ["reason:low_winrate"]


def _validate_life_and_death(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
    corner: str = "TL",
    position: Position | None = None,
) -> CorrectMoveResult:
    """Validate life-and-death puzzle using ownership thresholds.

    Center positions (YC=C) use reduced thresholds since ownership
    signals are weaker in the center.
    """
    is_top, in_top_n, winrate, policy, rank, correct_visits = _classify_move(response, correct_move_gtp, config)

    status, status_flags = _status_from_classification(winrate, config, correct_visits)
    logger.info(
        "Validate %s: status=%s, is_top=%s, in_top_n=%s, winrate=%.3f, "
        "flagged_high=%.2f, flagged_low=%.2f, flags=%s",
        correct_move_gtp, status.value, is_top, in_top_n, winrate,
        config.validation.flagged_value_high,
        config.validation.flagged_value_low,
        status_flags,
    )

    flags: list[str] = []

    # Adjust thresholds for center positions
    if corner == "C":
        flags.append("center_position")

    # Reuse status from classification (single call — DRY)
    flags.extend(status_flags)

    # Ownership-aware override for life-and-death validation (P1.1)
    # Uses ownership of stones of the side-to-move as local survival signal.
    correct_info = response.get_move(correct_move_gtp)
    ownership_grid = correct_info.ownership if correct_info else None
    if position and ownership_grid:
        target_stones = [s for s in position.stones if s.color == position.player_to_move]
        if target_stones:
            samples: list[float] = []
            grid_size = len(ownership_grid)
            for stone in target_stones:
                if 0 <= stone.y < grid_size and 0 <= stone.x < len(ownership_grid[stone.y]):
                    samples.append(float(ownership_grid[stone.y][stone.x]))

            if samples:
                signed_samples = samples
                if position.player_to_move == Color.WHITE:
                    signed_samples = [-v for v in samples]
                avg_signed = sum(signed_samples) / len(signed_samples)

                alive_threshold = config.ownership_thresholds.center_alive if corner == "C" else config.ownership_thresholds.alive
                if avg_signed >= alive_threshold:
                    flags.append(f"ownership_confirmed:{avg_signed:.3f}")
                    if status != ValidationStatus.ACCEPTED:
                        status = ValidationStatus.ACCEPTED
                        flags.append("ownership_rescue")
                elif status == ValidationStatus.ACCEPTED:
                    status = ValidationStatus.FLAGGED
                    flags.append(f"ownership_conflict:{avg_signed:.3f}")

    # Add diagnostic context for non-accepted outcomes
    if status != ValidationStatus.ACCEPTED:
        top_wr = response.top_move.winrate if response.top_move else 0.0
        flags.extend(_build_diagnostic_flags(is_top, in_top_n, winrate, rank, config, top_wr))

    top = response.top_move
    top_move_gtp = top.move if top else ""

    return CorrectMoveResult(
        status=status,
        katago_agrees=is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top_move_gtp,
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        correct_move_visits=correct_visits,
        flags=flags,
    )


def _validate_tactical(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
    tag_slug: str = "tactical",
) -> CorrectMoveResult:
    """Validate tactical puzzles (ladder, net, snapback, etc.) via PV patterns.

    For tactical puzzles, we check:
    1. Is the correct move the top move?
    2. Does the PV contain a multi-move forcing sequence?
    3. Is the winrate decisive (>0.7)?
    """
    is_top, in_top_n, winrate, policy, rank, correct_visits = _classify_move(response, correct_move_gtp, config)

    flags: list[str] = [f"tag:{tag_slug}"]

    # Check PV length — tactical puzzles should have a forcing sequence
    correct_info = response.get_move(correct_move_gtp)
    if correct_info and len(correct_info.pv) >= 3:
        flags.append("forcing_sequence")

    status, reasons = _status_from_classification(winrate, config, correct_visits)
    flags.extend(reasons)

    # Add diagnostic context for non-accepted outcomes
    if status != ValidationStatus.ACCEPTED:
        top_wr = response.top_move.winrate if response.top_move else 0.0
        flags.extend(_build_diagnostic_flags(is_top, in_top_n, winrate, rank, config, top_wr))

    top = response.top_move
    return CorrectMoveResult(
        status=status,
        katago_agrees=is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move if top else "",
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        correct_move_visits=correct_visits,
        flags=flags,
    )


def _validate_capture_race(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> CorrectMoveResult:
    """Validate capture-race (semeai) puzzles.

    Capture-race validation focuses on:
    1. Is the correct move top? (critical — capture races are timing-sensitive)
    2. Does winrate strongly favor attacker after the move?
    3. PV shows liberty reduction sequence.

    D6: Enhanced with ownership-based assessment — if the correct move's
    ownership grid shows clear group capture (high absolute ownership for
    both attacker and target groups), this strengthens the signal even at
    borderline winrates.
    """
    is_top, in_top_n, winrate, policy, rank, correct_visits = _classify_move(response, correct_move_gtp, config)

    flags: list[str] = ["capture_race"]

    # D6: Ownership-based semeai assessment
    correct_info = response.get_move(correct_move_gtp)
    ownership_grid = correct_info.ownership if correct_info else None
    if ownership_grid:
        # In a resolved capture race, ownership should be polarized:
        # high positive for one group, high negative for the other.
        polarized_count = 0
        total_occupied = 0
        for row in ownership_grid:
            for val in row:
                if abs(val) > 0.3:
                    total_occupied += 1
                    if abs(val) > 0.7:
                        polarized_count += 1
        if total_occupied > 0:
            polarization = polarized_count / total_occupied
            if polarization > 0.6:
                flags.append(f"semeai_ownership_polarized:{polarization:.2f}")

    # For capture races, timing matters more — stricter on needing top move.
    # Intentionally more conservative than _status_from_classification: a
    # move that would be ACCEPTED in a general context is FLAGGED here
    # because capture race move order is critical.
    if not is_top and in_top_n and winrate >= config.validation.flagged_value_high:
        # Close enough for a semeai
        status = ValidationStatus.FLAGGED
        flags.append("not_top_but_close")
    else:
        status, reasons = _status_from_classification(winrate, config, correct_visits)
        flags.extend(reasons)

    # Add diagnostic context for non-accepted outcomes
    if status != ValidationStatus.ACCEPTED:
        top_wr = response.top_move.winrate if response.top_move else 0.0
        flags.extend(_build_diagnostic_flags(is_top, in_top_n, winrate, rank, config, top_wr))

    top = response.top_move
    return CorrectMoveResult(
        status=status,
        katago_agrees=is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move if top else "",
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        correct_move_visits=correct_visits,
        flags=flags,
    )


def _validate_connection(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> CorrectMoveResult:
    """Validate connection/cutting puzzles.

    Connection puzzles are about group connectivity changes.
    Uses standard move ranking + winrate validation.
    """
    is_top, in_top_n, winrate, policy, rank, correct_visits = _classify_move(response, correct_move_gtp, config)

    flags: list[str] = ["connection"]
    status, reasons = _status_from_classification(winrate, config, correct_visits)
    flags.extend(reasons)

    # Add diagnostic context for non-accepted outcomes
    if status != ValidationStatus.ACCEPTED:
        top_wr = response.top_move.winrate if response.top_move else 0.0
        flags.extend(_build_diagnostic_flags(is_top, in_top_n, winrate, rank, config, top_wr))

    top = response.top_move
    return CorrectMoveResult(
        status=status,
        katago_agrees=is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move if top else "",
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        correct_move_visits=correct_visits,
        flags=flags,
    )


def _validate_seki(
    response: AnalysisResponse,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> CorrectMoveResult:
    """Validate seki (mutual life) puzzles using 3 combined signals.

    Seki signals:
    1. Ownership near 0 — neither player owns the region
    2. Neither player profits — score near 0
    3. Both groups survive — winrate near 0.5

    Thresholds from config:
    - Winrate: flagged_value_low < wr < flagged_value_high (no decisive winner)
    - Score: |score| < 5.0 (neither profits much)
    """
    is_top, in_top_n, winrate, policy, rank, correct_visits = _classify_move(response, correct_move_gtp, config)

    flags: list[str] = ["seki"]

    # Use config thresholds for seki winrate bounds
    seki_low = config.validation.flagged_value_low
    seki_high = config.validation.flagged_value_high

    # Seki-specific logic: check 3 signals
    seki_signals = 0

    # Signal 1: Winrate near 0.5 (both survive)
    if seki_low <= response.root_winrate <= seki_high:
        seki_signals += 1
        flags.append("seki_balanced_winrate")

    # Signal 2: Score near 0 (neither profits)
    # Q7: Wire seki score threshold to config
    seki_score_threshold = 5.0  # default
    if config.technique_detection and config.technique_detection.seki:
        seki_score_threshold = getattr(config.technique_detection.seki, "score_threshold", seki_score_threshold)
    if abs(response.root_score) < seki_score_threshold:
        seki_signals += 1
        flags.append("seki_low_score")

    # Signal 3: Correct move is reasonable (in top moves)
    if is_top or in_top_n:
        seki_signals += 1
        flags.append("seki_move_reasonable")

    # Seki judgment:
    # - 3 signals → accepted (strong seki evidence)
    # - 2 signals → accepted or flagged depending on move ranking
    # - 1 signal → flagged
    # - 0 signals → rejected (unless winrate rescue applies)
    if seki_signals >= 3:
        status = ValidationStatus.ACCEPTED
    elif seki_signals >= 2:
        status = ValidationStatus.ACCEPTED if is_top else ValidationStatus.FLAGGED
    elif seki_signals >= 1:
        status = ValidationStatus.FLAGGED
    elif winrate >= config.validation.winrate_rescue_auto_accept:
        # Winrate rescue auto-accept: no seki signals detected but the
        # correct move's per-move winrate is very high (≥ auto_accept
        # threshold).  Auto-accept rather than flag.
        status = ValidationStatus.ACCEPTED
        flags.append("seki_winrate_rescue_auto_accepted")
    elif winrate >= config.validation.flagged_value_high:
        # Winrate rescue: no seki signals detected but the correct move's
        # per-move winrate (from _classify_move) is confident. This is
        # different from response.root_winrate used for seki signals above —
        # root_winrate measures overall position; winrate here measures
        # the specific move's quality.  Rescue often applies when large
        # territory imbalances mask a local seki pattern.
        status = ValidationStatus.FLAGGED
        flags.append("seki_winrate_rescue")
    else:
        status = ValidationStatus.REJECTED
        flags.append("reason:seki_no_signals_low_winrate")

    # Add diagnostic context for non-accepted outcomes
    if status != ValidationStatus.ACCEPTED:
        top_wr = response.top_move.winrate if response.top_move else 0.0
        flags.extend(_build_diagnostic_flags(is_top, in_top_n, winrate, rank, config, top_wr))

    top = response.top_move
    return CorrectMoveResult(
        status=status,
        katago_agrees=is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move if top else "",
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        correct_move_visits=correct_visits,
        flags=flags,
    )


def _validate_miai(
    response: AnalysisResponse,
    correct_move_gtp: str,
    all_correct_moves_gtp: list[str],
    config: EnrichmentConfig,
    corner: str = "TL",
) -> CorrectMoveResult | None:
    """Validate a miai puzzle where multiple moves are equally correct.

    For miai, we accept the move if ANY of the correct moves is in
    top-N with good winrate. This handles the case where KataGo
    prefers one miai move over the other.

    Returns:
        CorrectMoveResult if miai validation produced a result,
        None to fall through to normal validation.
    """
    flags: list[str] = ["miai"]

    # Check if the specific correct move is in the analysis
    correct_info = response.get_move(correct_move_gtp)

    # Check if ANY correct move is top or in top-N
    top = response.top_move
    if top is None:
        return None

    top_n = config.validation.rejected_not_in_top_n
    sorted_moves = sorted(response.move_infos, key=lambda m: m.visits, reverse=True)
    top_n_coords = {m.move.upper() for m in sorted_moves[:top_n]}

    # Any correct move in top-N?
    any_correct_in_top_n = any(
        m.upper() in top_n_coords for m in all_correct_moves_gtp
    )

    # Any correct move is actual top?
    any_correct_is_top = any(
        m.upper() == top.move.upper() for m in all_correct_moves_gtp
    )

    if not any_correct_in_top_n:
        return None  # Fall through to normal validation

    # At least one correct move is well-ranked — check the specific one
    is_this_top = top.move.upper() == correct_move_gtp.upper()
    this_in_top_n = correct_move_gtp.upper() in top_n_coords

    winrate = correct_info.winrate if correct_info else 0.0
    policy = correct_info.policy_prior if correct_info else 0.0

    if is_this_top or this_in_top_n:
        # This specific move is also well-ranked
        status = ValidationStatus.ACCEPTED
    elif any_correct_is_top:
        # Another miai move is top — this one is equivalent
        status = ValidationStatus.ACCEPTED
        flags.append("miai_equivalent")
    else:
        # At least one is in top-N, accept with miai flag
        status = ValidationStatus.ACCEPTED
        flags.append("miai_alternative")

    return CorrectMoveResult(
        status=status,
        katago_agrees=is_this_top or any_correct_is_top,
        correct_move_gtp=correct_move_gtp,
        katago_top_move=top.move,
        correct_move_winrate=winrate,
        correct_move_policy=policy,
        flags=flags,
    )


# ---------------------------------------------------------------------------
# Phase R.4: Deep solution tree validation
# ---------------------------------------------------------------------------


def get_required_validation_depth(
    tags: list[int],
    estimated_level_id: int = 0,
    config: EnrichmentConfig | None = None,
) -> int:
    """Determine required validation depth based on Cho Chikun recommendations.

    Depth recommendations (Phase R.4, Plan 010 D41):
      - Minimum depth_base moves for ALL puzzles
      - Minimum depth_ko moves for ko-tagged puzzles
      - Minimum depth_intermediate moves for intermediate+ (level_id >= threshold)
      - Minimum depth_advanced moves for advanced+ (level_id >= threshold)

    Args:
        tags: Numeric tag IDs from puzzle.
        estimated_level_id: Numeric level ID (110=novice .. 230=expert).
        config: Enrichment config for tree_validation thresholds.

    Returns:
        Required validation depth (number of moves to validate).
    """
    if config is None:
        from config import load_enrichment_config
        config = load_enrichment_config()

    tv = config.tree_validation
    depth = tv.depth_base  # Minimum for all puzzles

    # Ko-tagged puzzles need deeper validation
    if _get_tag_consts()["KO_ID"] in set(tags):
        depth = max(depth, tv.depth_ko)

    # Intermediate+ (config-driven threshold)
    if estimated_level_id >= tv.level_intermediate_threshold:
        depth = max(depth, tv.depth_intermediate)

    # Advanced+ (config-driven threshold)
    if estimated_level_id >= tv.level_advanced_threshold:
        depth = max(depth, tv.depth_advanced)

    return depth


async def validate_solution_tree_depth(
    engine,  # LocalEngine (not typed to avoid circular import)
    position,  # Position
    solution_moves: list[str],
    board_size: int = 19,
    required_depth: int = 3,
    player_color: str = "B",
    config: EnrichmentConfig | None = None,
) -> tuple[int, str, float | None]:
    """Validate solution tree moves against KataGo's top choices (Phase R.4).

    Plays through the solution tree move by move, checking at each step
    whether KataGo's top-N moves include the expected correct move.

    Args:
        engine: Running KataGo engine (LocalEngine).
        position: Initial board position (unframed).
        solution_moves: SGF coordinates of the correct solution sequence.
        board_size: Board size for coordinate conversion.
        required_depth: Number of moves to validate.
        player_color: Starting player ("B" or "W").
        config: Enrichment config for tree_validation thresholds.

    Returns:
        Tuple of (validated_depth, status, unframed_root_winrate):
          - validated_depth: How many moves were successfully validated.
          - status: "pass" if all required moves validated,
                    "partial" if some validated,
                    "fail" if first move failed,
                    "not_validated" if engine unavailable or empty solution.
          - unframed_root_winrate: Root winrate from the first (depth-0)
              unframed query, or None if no query was made.
    """
    try:
        from models.analysis_request import AnalysisRequest
        from models.analysis_response import sgf_to_gtp
    except ImportError:
        from ..models.analysis_request import AnalysisRequest
        from ..models.analysis_response import sgf_to_gtp

    if not solution_moves or engine is None:
        return 0, "not_validated", None

    # Load tree_validation config for visits_per_depth and top_n_match
    if config is None:
        from config import load_enrichment_config
        config = load_enrichment_config()
    tv = config.tree_validation
    visits_per_depth = tv.visits_per_depth
    top_n = tv.top_n_match

    # T4B: Curated pruning config
    prune_cfg = config.validation.curated_pruning

    # Only validate up to the available solution depth
    moves_to_check = min(required_depth, len(solution_moves))
    validated = 0
    current_moves: list[list[str]] = []
    colors = ["B", "W"] if player_color == "B" else ["W", "B"]
    unframed_root_winrate: float | None = None

    for i in range(moves_to_check):
        expected_sgf = solution_moves[i]
        expected_gtp = sgf_to_gtp(expected_sgf, board_size)
        if not expected_gtp:
            break

        # Analyze the position after playing the moves so far
        try:
            request = AnalysisRequest(
                position=position,
                max_visits=visits_per_depth,
                include_ownership=True,
                include_pv=True,
                moves=current_moves,
            )
            response = await engine.analyze(request)
        except Exception as e:
            logger.warning(
                "Tree validation engine error at depth %d: %s",
                i + 1, e,
            )
            break

        # Capture the unframed root winrate from the first query (depth 0)
        if i == 0:
            unframed_root_winrate = response.root_winrate

        # T4B: Curated branch pruning — skip low-visit sub-branches at depth >= min_depth
        depth = i + 1
        if (
            prune_cfg.enabled
            and depth >= prune_cfg.min_depth
            and response.top_move is not None
        ):
            top_visits = response.top_move.visits
            expected_info = next(
                (m for m in response.move_infos if m.move.upper() == expected_gtp.upper()),
                None,
            )
            if expected_info is not None and top_visits > 0:
                visit_ratio = expected_info.visits / top_visits
                if visit_ratio < prune_cfg.min_visit_ratio:
                    if visit_ratio < prune_cfg.trap_threshold:
                        logger.info(
                            "T4B pruning: depth %d move %s has visit ratio %.4f < %.4f "
                            "(below trap threshold), skipping",
                            depth, expected_gtp, visit_ratio, prune_cfg.min_visit_ratio,
                        )
                        validated += 1
                        color = colors[i % 2]
                        current_moves.append([color, expected_gtp])
                        continue
                    else:
                        logger.info(
                            "T4B keeping tricky trap: depth %d move %s has visit ratio %.4f "
                            ">= trap threshold %.4f",
                            depth, expected_gtp, visit_ratio, prune_cfg.trap_threshold,
                        )

        # Check if expected move is in KataGo's top-N (config-driven)
        # P0.2 fix: Sort by visits (MCTS search result) not policy_prior
        # (neural net first guess). Tesuji with low policy but high visits
        # (e.g., sacrifice, throw-in) would be missed by policy sort.
        top_moves = [
            m.move.upper()
            for m in sorted(
                response.move_infos,
                key=lambda m: m.visits,
                reverse=True,
            )[:top_n]
        ]

        if expected_gtp.upper() in top_moves:
            validated += 1
            # Add this move to the sequence for next iteration
            color = colors[i % 2]
            current_moves.append([color, expected_gtp])
        else:
            logger.debug(
                "Tree validation: move %d (%s) not in KataGo top 3 %s",
                i + 1, expected_gtp, top_moves,
            )
            break

    # Determine status
    if validated >= moves_to_check:
        status = "pass"
    elif validated > 0:
        status = "partial"
    elif moves_to_check > 0:
        status = "fail"
    else:
        status = "not_validated"

    logger.info(
        "Tree validation: %d/%d moves validated (status=%s, required=%d)",
        validated, moves_to_check, status, required_depth,
    )

    return validated, status, unframed_root_winrate
