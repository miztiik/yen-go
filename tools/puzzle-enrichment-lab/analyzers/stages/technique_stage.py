"""Technique classification stage — detect technique tags from analysis.

Isolated from TeachingStage for SRP: this stage only classifies techniques.
Uses the 28 individual TechniqueDetector classes via run_detectors() dispatcher.
Error policy: DEGRADE (teaching enrichment is optional).
"""
from __future__ import annotations

import logging

try:
    from analyzers.stages.protocols import EnrichmentStage, ErrorPolicy, PipelineContext
    from analyzers.technique_classifier import (
        TAG_PRIORITY,
        get_all_detectors,
        run_detectors,
    )
except ImportError:
    from ..stages.protocols import ErrorPolicy, PipelineContext
    from ..technique_classifier import (
        TAG_PRIORITY,
        get_all_detectors,
        run_detectors,
    )

logger = logging.getLogger(__name__)


class TechniqueStage:
    """Classify puzzle techniques from analysis data.

    Uses the 28 individual TechniqueDetector classes registered in
    technique_classifier.get_all_detectors(). Passes typed Position,
    AnalysisResponse, and SolutionNode objects (not dicts).
    """

    @property
    def name(self) -> str:
        return "technique_classification"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.DEGRADE

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        result = ctx.result
        config = ctx.config

        # Get typed objects for detector dispatch (CRA-4 fix)
        position = ctx.position
        analysis = ctx.response
        solution_tree = None  # Solution tree not on ctx; detectors handle None

        # Run all 28 detectors via typed dispatcher
        detectors = get_all_detectors()
        detection_results = run_detectors(
            position=position,
            analysis=analysis,
            solution_tree=solution_tree,
            config=config,
            detectors=detectors,
        )

        # Store full detection results on context (T8: stop discarding evidence)
        ctx.detection_results = detection_results

        # Extract tag slugs from positive detections, sorted by priority
        tags = sorted(
            [dr.tag_slug for dr in detection_results],
            key=lambda t: TAG_PRIORITY.get(t, 99),
        )
        result.technique_tags = tags

        logger.info(
            "technique_classification",
            extra={
                "stage": "technique_classification",
                "technique_tags": tags,
                "detector_count": len(detectors),
                "positive_count": len(detection_results),
            },
        )
        return ctx
