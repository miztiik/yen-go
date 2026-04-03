"""Query stage — backward-compatibility wrapper.

The implementation has moved to analyze_stage.py.  This module re-exports
AnalyzeStage as QueryStage so that existing imports keep working.
"""

from __future__ import annotations

try:
    from analyzers.stages.analyze_stage import AnalyzeStage
except ImportError:
    from .analyze_stage import AnalyzeStage

# Backward-compatible alias
QueryStage = AnalyzeStage

__all__ = ["QueryStage"]

