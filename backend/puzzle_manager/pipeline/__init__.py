"""
Pipeline module for orchestrating stages.

Provides PipelineCoordinator for running the 3-stage pipeline.
"""

from backend.puzzle_manager.pipeline.cleanup import cleanup_old_files
from backend.puzzle_manager.pipeline.coordinator import PipelineCoordinator
from backend.puzzle_manager.pipeline.executor import StageExecutor
from backend.puzzle_manager.pipeline.prerequisites import check_prerequisites

__all__ = [
    "PipelineCoordinator",
    "StageExecutor",
    "check_prerequisites",
    "cleanup_old_files",
]
