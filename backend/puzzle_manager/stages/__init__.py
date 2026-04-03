"""
Pipeline stages module.

Provides StageRunner protocol and stage implementations (ingest, analyze, publish).
"""

from backend.puzzle_manager.stages.analyze import AnalyzeStage
from backend.puzzle_manager.stages.ingest import IngestStage
from backend.puzzle_manager.stages.protocol import StageContext, StageResult, StageRunner
from backend.puzzle_manager.stages.publish import PublishStage

__all__ = [
    "StageRunner",
    "StageContext",
    "StageResult",
    "IngestStage",
    "AnalyzeStage",
    "PublishStage",
]
