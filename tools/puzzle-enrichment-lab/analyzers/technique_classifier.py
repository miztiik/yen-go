"""Technique classifier — detect Go techniques from KataGo analysis.

Analyzes PV patterns, refutation structure, ownership, and policy distribution
to classify the primary technique(s) present in a tsumego puzzle.

Aligned with production hints.py TAG_PRIORITY and the 28-tag TECHNIQUE_HINTS dict.

Techniques detected:
  - Direct capture (PV depth 1-2, no ko, no sacrifice)
  - Ko (PV contains same-point recapture within window)
  - Ladder (diagonal or edge-chasing PV pattern)
  - Snapback (sacrifice stone, then immediate recapture of larger group)
  - Net / geta (surrounding pattern, no atari chain)
  - Throw-in (sacrifice on first/second line to reduce liberties)
  - Life-and-death (default for corner/side tsumego)
  - Seki (mutual life, ownership near zero)
  - Connection (PV connects separated groups)
  - Cutting (PV separates opponent groups)
  - Eye-shape (PV creates or destroys eyes)

Input: AiAnalysisResult (dict or Pydantic model)
Output: list[str] of technique tag slugs, sorted by priority
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from config import load_enrichment_config
from config.technique import TechniqueDetectionConfig
from models.detection import DetectionResult

from analyzers.detectors import TechniqueDetector

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_response import AnalysisResponse
    from models.position import Position
    from models.solve_result import SolutionNode

logger = logging.getLogger(__name__)


def _get_technique_config() -> TechniqueDetectionConfig:
    """Load technique detection thresholds from config (cached)."""
    cfg = load_enrichment_config()
    return cfg.technique_detection

# ---------------------------------------------------------------------------
# Priority groups — aligned with production hints.py TAG_PRIORITY
# ---------------------------------------------------------------------------

TAG_PRIORITY: dict[str, int] = {
    # Priority 1 (highest) — specific tactical patterns
    "net": 1,
    "snapback": 1,
    "squeeze": 1,
    "ladder": 1,
    "ko": 1,
    "seki": 1,
    "semeai": 1,
    "capture-race": 1,
    # Priority 2 — sacrifice patterns
    "throw-in": 2,
    "sacrifice": 2,
    "under-the-stones": 2,
    "life-and-death": 2,
    # Priority 3 — shape patterns
    "connection": 3,
    "cutting": 3,
    "shape": 3,
    "eye-shape": 3,
    "dead-shapes": 3,
    # Priority 4 (lowest) — broad categories
    "living": 4,
    "escape": 4,
    "corner": 4,
    "endgame": 4,
    "tesuji": 4,
    "atari": 4,
    "capture": 4,
    "surround": 4,
}


def classify_techniques(
    analysis: dict[str, Any],
    board_size: int = 19,
) -> list[str]:
    """Classify technique tags from AiAnalysisResult.

    .. deprecated::
        This function uses heuristic _detect_* helpers and is superseded by
        ``run_detectors()`` with the 28 typed detector classes.  Retained only
        because ``result_builders.py`` and existing tests still call it.
        Migrate callers to ``run_detectors()`` then delete this function and
        all ``_detect_*`` helpers below.

    Args:
        analysis: AiAnalysisResult as dict (parsed JSON or .model_dump())
        board_size: Board size for edge detection (P1.3 review fix).

    Returns:
        List of technique tag slugs sorted by TAG_PRIORITY (highest first).
        Always returns at least one tag (falls back to "life-and-death").
    """
    tags: set[str] = set()
    tc = _get_technique_config()

    # Extract data from analysis result
    validation = analysis.get("validation", {})
    refutations = analysis.get("refutations", [])
    difficulty = analysis.get("difficulty", {})
    existing_tags = analysis.get("tag_names", []) or analysis.get("tags", [])

    correct_move = validation.get("correct_move_gtp", "")
    validation.get("katago_agrees", False)
    validation.get("status", "")

    # --- Pattern detection ---

    # 1. Ko detection: check refutation PVs for recapture patterns
    ko_detected = _detect_ko(refutations)
    if ko_detected:
        tags.add("ko")
    logger.info("Technique %s: ko=%s", correct_move, ko_detected, extra={"stage": 9})

    # 2. Ladder detection: check PV for diagonal chase pattern
    ladder_detected = _detect_ladder(validation, refutations, tc)
    if ladder_detected:
        tags.add("ladder")
    logger.info("Technique %s: ladder=%s", correct_move, ladder_detected, extra={"stage": 9})

    # 3. Snapback detection: sacrifice then larger capture
    snapback_detected = _detect_snapback(validation, refutations, tc)
    if snapback_detected:
        tags.add("snapback")
    logger.info("Technique %s: snapback=%s", correct_move, snapback_detected, extra={"stage": 9})

    # 4. Throw-in detection: first-line sacrifice
    throwin_detected = _detect_throw_in(correct_move, validation, board_size=board_size, tc=tc)
    if throwin_detected:
        tags.add("throw-in")

    # 5. Seki detection: near-zero ownership delta
    seki_detected = _detect_seki(validation, refutations, tc)
    if seki_detected:
        tags.add("seki")

    # 6. Net/geta detection: surrounding without atari chain
    net_detected = _detect_net(validation, refutations, tc)
    if net_detected:
        tags.add("net")

    # 7. Direct capture: simple capturing move
    capture_detected = _detect_direct_capture(validation, difficulty, tc)
    if capture_detected:
        if not tags.intersection({"ko", "ladder", "snapback", "throw-in"}):
            tags.add("capture")

    # 8. Eye-shape: if existing tags mention eyes
    if any("eye" in t.lower() for t in existing_tags):
        tags.add("eye-shape")

    # 9. Connection/cutting from existing tags
    for t in existing_tags:
        normalized = t.lower().strip()
        if normalized in TAG_PRIORITY:
            tags.add(normalized)

    result = sorted(tags, key=lambda t: TAG_PRIORITY.get(t, 99))
    if not result:
        logger.warning(
            "No technique tags detected for move %s -- returning empty",
            correct_move,
            extra={"stage": 9},
        )
    else:
        logger.info(
            "Technique %s: tags=%s",
            correct_move, result,
            extra={"stage": 9},
        )

    # Sort by priority (lowest number = highest priority)
    return result


def _detect_ko(refutations: list[dict]) -> bool:
    """Detect ko by looking for recapture patterns in refutation PVs.

    Ko indicator: PV contains a move at position X, then later a move at
    the same position (recapture). Also checks for 'ko' in refutation type.
    """
    for ref in refutations:
        ref_type = ref.get("refutation_type", "")
        if "ko" in ref_type.lower():
            return True

        pv = ref.get("refutation_pv", [])
        if len(pv) >= 3:
            # Check for positional recapture (same coordinate appears twice)
            seen = set()
            for move in pv:
                if move in seen:
                    return True
                seen.add(move)
    return False


def _detect_ladder(
    validation: dict[str, Any],
    refutations: list[dict],
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect ladder by checking for diagonal chase patterns in PV.

    Ladder indicator: PV has ≥4 moves with consistent diagonal progression
    (each move adjacent diagonally to the previous).
    """
    if tc is None:
        tc = _get_technique_config()
    min_pv = tc.ladder.min_pv_length
    diag_ratio = tc.ladder.diagonal_ratio

    # Check correct move PV if available
    pv = validation.get("pv", [])
    if _is_diagonal_chase(pv, min_length=min_pv, diagonal_ratio=diag_ratio):
        return True

    # Check refutation PVs
    for ref in refutations:
        ref_pv = ref.get("refutation_pv", [])
        if _is_diagonal_chase(ref_pv, min_length=min_pv, diagonal_ratio=diag_ratio):
            return True
    return False


def _is_diagonal_chase(
    pv: list[str],
    min_length: int = 4,
    diagonal_ratio: float = 0.5,
) -> bool:
    """Check if PV shows a diagonal chase pattern (ladder-like)."""
    if len(pv) < min_length:
        return False

    gtp_coords = [_parse_gtp(m) for m in pv if m.lower() != "pass"]
    if len(gtp_coords) < min_length:
        return False

    diagonal_count = 0
    for i in range(1, len(gtp_coords)):
        if gtp_coords[i] is None or gtp_coords[i - 1] is None:
            continue
        r1, c1 = gtp_coords[i - 1]
        r2, c2 = gtp_coords[i]
        if abs(r2 - r1) == 1 and abs(c2 - c1) == 1:
            diagonal_count += 1

    # Config-driven diagonal ratio threshold
    return diagonal_count >= len(gtp_coords) * diagonal_ratio


def _detect_snapback(
    validation: dict[str, Any],
    refutations: list[dict],
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect snapback pattern.

    Snapback: a sequence where a stone is played to be captured, then
    the resulting position allows capturing a larger group. Typically
    shows as low policy on correct move (sacrifice) followed by high
    winrate swing.
    """
    if tc is None:
        tc = _get_technique_config()
    policy = validation.get("correct_move_policy", 0.0)
    winrate = validation.get("correct_move_winrate", 0.0)

    # Snapback signature: low policy (sacrifice looks bad) but high winrate (it works)
    if policy < tc.snapback.policy_threshold and winrate > tc.snapback.winrate_threshold:
        # Check if any refutation shows a large capture
        for ref in refutations:
            delta = abs(ref.get("delta", 0.0))
            if delta > tc.snapback.delta_threshold:
                return True
    return False


def _detect_throw_in(
    correct_move: str,
    validation: dict[str, Any],
    board_size: int = 19,
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect throw-in (sacrifice on first or second line).

    Throw-in: correct move is on the 1st or 2nd line of the board,
    typically a sacrifice to reduce liberties.

    P1.3 fix: Check ALL four edges, not just bottom/left.
    """
    if not correct_move:
        return False

    coords = _parse_gtp(correct_move)
    if coords is None:
        return False

    if tc is None:
        tc = _get_technique_config()
    edge = tc.throw_in.edge_lines

    row, col = coords
    # First or second line on ANY edge (config-driven edge_lines threshold)
    return (
        row <= edge
        or col <= edge
        or row >= board_size - (edge - 1)
        or col >= board_size - (edge - 1)
    )


def _detect_seki(
    validation: dict[str, Any],
    refutations: list[dict],
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect seki (mutual life) — typically no refutations and status accepted."""
    if tc is None:
        tc = _get_technique_config()
    if len(refutations) == 0:
        status = validation.get("status", "")
        if status == "accepted":
            winrate = validation.get("correct_move_winrate", 0.5)
            if tc.seki.winrate_low < winrate < tc.seki.winrate_high:
                return True
    return False


def _detect_net(
    validation: dict[str, Any],
    refutations: list[dict],
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect net/geta (surrounding pattern without atari chain).

    Net indicator: correct move is NOT adjacent to opponent stones (no atari),
    but still has high winrate (trapping move). Refutations show opponent
    cannot escape.
    """
    if tc is None:
        tc = _get_technique_config()
    policy = validation.get("correct_move_policy", 0.0)
    winrate = validation.get("correct_move_winrate", 0.5)

    if policy > tc.net.policy_threshold and winrate > tc.net.winrate_threshold:
        if len(refutations) >= tc.net.min_refutations:
            deltas = [abs(r.get("delta", 0.0)) for r in refutations]
            if deltas and max(deltas) - min(deltas) < tc.net.delta_spread:
                return True
    return False


def _detect_direct_capture(
    validation: dict[str, Any],
    difficulty: dict[str, Any],
    tc: TechniqueDetectionConfig | None = None,
) -> bool:
    """Detect direct capture (simple killing move).

    Direct capture: solution depth ≤ max_depth, high winrate, and the position
    is resolved quickly (few visits needed).
    """
    if tc is None:
        tc = _get_technique_config()
    depth = difficulty.get("solution_depth", 0)
    winrate = validation.get("correct_move_winrate", 0.0)
    visits = difficulty.get("visits_to_solve", 0)

    return (
        depth <= tc.direct_capture.max_depth
        and winrate > tc.direct_capture.winrate_threshold
        and visits < tc.direct_capture.max_visits
    )


def _parse_gtp(move: str) -> tuple[int, int] | None:
    """Parse GTP coordinate like 'C3' → (row=3, col=3).

    Returns (row, col) as 1-indexed integers, or None if unparseable.
    GTP columns: A=1, B=2, ..., H=8, J=9 (skipping I), ...
    GTP rows: numbered from bottom (1=bottom row).
    """
    if not move or move.lower() == "pass":
        return None

    m = re.match(r"^([A-HJ-T])(\d{1,2})$", move.upper())
    if not m:
        return None

    col_letter = m.group(1)
    row = int(m.group(2))

    # GTP skips 'I' — A=1, B=2, ..., H=8, J=9, K=10, ...
    col = ord(col_letter) - ord("A") + 1
    if col_letter >= "J":
        col -= 1  # Adjust for skipped 'I'

    return (row, col)


# ---------------------------------------------------------------------------
# Detector-based dispatcher (v2 infrastructure)
# ---------------------------------------------------------------------------

# All 28 detector classes — lazy-imported to avoid circular imports
_ALL_DETECTOR_CLASSES: list[type] | None = None


def _load_detector_classes() -> list[type]:
    """Import all 28 detector classes (lazy, cached)."""
    global _ALL_DETECTOR_CLASSES
    if _ALL_DETECTOR_CLASSES is not None:
        return _ALL_DETECTOR_CLASSES

    from analyzers.detectors.capture_race_detector import CaptureRaceDetector
    from analyzers.detectors.clamp_detector import ClampDetector
    from analyzers.detectors.connect_and_die_detector import ConnectAndDieDetector
    from analyzers.detectors.connection_detector import ConnectionDetector
    from analyzers.detectors.corner_detector import CornerDetector
    from analyzers.detectors.cutting_detector import CuttingDetector
    from analyzers.detectors.dead_shapes_detector import DeadShapesDetector
    from analyzers.detectors.double_atari_detector import DoubleAtariDetector
    from analyzers.detectors.endgame_detector import EndgameDetector
    from analyzers.detectors.escape_detector import EscapeDetector
    from analyzers.detectors.eye_shape_detector import EyeShapeDetector
    from analyzers.detectors.fuseki_detector import FusekiDetector
    from analyzers.detectors.joseki_detector import JosekiDetector
    from analyzers.detectors.ko_detector import KoDetector
    from analyzers.detectors.ladder_detector import LadderDetector
    from analyzers.detectors.liberty_shortage_detector import LibertyShortageDetector
    from analyzers.detectors.life_and_death_detector import LifeAndDeathDetector
    from analyzers.detectors.living_detector import LivingDetector
    from analyzers.detectors.nakade_detector import NakadeDetector
    from analyzers.detectors.net_detector import NetDetector
    from analyzers.detectors.sacrifice_detector import SacrificeDetector
    from analyzers.detectors.seki_detector import SekiDetector
    from analyzers.detectors.shape_detector import ShapeDetector
    from analyzers.detectors.snapback_detector import SnapbackDetector
    from analyzers.detectors.tesuji_detector import TesujiDetector
    from analyzers.detectors.throw_in_detector import ThrowInDetector
    from analyzers.detectors.under_the_stones_detector import UnderTheStonesDetector
    from analyzers.detectors.vital_point_detector import VitalPointDetector

    _ALL_DETECTOR_CLASSES = [
        LifeAndDeathDetector, KoDetector, LadderDetector, SnapbackDetector,
        CaptureRaceDetector, ConnectionDetector, CuttingDetector,
        ThrowInDetector, NetDetector, SekiDetector, NakadeDetector,
        DoubleAtariDetector, SacrificeDetector, EscapeDetector,
        EyeShapeDetector, VitalPointDetector, LibertyShortageDetector,
        DeadShapesDetector, ClampDetector, LivingDetector,
        CornerDetector, ShapeDetector, EndgameDetector, TesujiDetector,
        UnderTheStonesDetector, ConnectAndDieDetector,
        JosekiDetector, FusekiDetector,
    ]
    return _ALL_DETECTOR_CLASSES


def get_all_detectors() -> list[TechniqueDetector]:
    """Instantiate and return all 28 technique detectors."""
    return [cls() for cls in _load_detector_classes()]


# Registry of detector instances — populated by register_detector()
_registered_detectors: list[TechniqueDetector] = []


def register_detector(detector: TechniqueDetector) -> None:
    """Register a technique detector for use by run_detectors()."""
    _registered_detectors.append(detector)


def clear_detectors() -> None:
    """Clear all registered detectors (useful for testing)."""
    _registered_detectors.clear()


def run_detectors(
    position: Position,
    analysis: AnalysisResponse,
    solution_tree: SolutionNode | None,
    config: EnrichmentConfig,
    detectors: list[TechniqueDetector] | None = None,
) -> list[DetectionResult]:
    """Run all technique detectors and return positive results.

    Args:
        position: Board position to analyze.
        analysis: KataGo analysis response.
        solution_tree: Solved move tree (may be None).
        config: Enrichment configuration with thresholds.
        detectors: Explicit list of detectors. If None, uses registered
                   detectors from register_detector() calls.

    Returns:
        List of DetectionResult where detected=True, sorted by tag_slug.
    """
    active = detectors if detectors is not None else _registered_detectors
    results: list[DetectionResult] = []
    for detector in active:
        try:
            result = detector.detect(position, analysis, solution_tree, config)
            if result.detected:
                results.append(result)
        except Exception:
            logger.warning(
                "Detector %s raised an exception — skipping",
                type(detector).__name__,
                exc_info=True,
                extra={"stage": 9},
            )
    # Deduplicate by tag_slug, keeping highest confidence
    best: dict[str, DetectionResult] = {}
    for r in results:
        if r.tag_slug not in best or r.confidence > best[r.tag_slug].confidence:
            best[r.tag_slug] = r
    return sorted(best.values(), key=lambda r: r.tag_slug)
