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
