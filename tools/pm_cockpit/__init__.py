"""pm_cockpit — localhost browser UI for the puzzle_manager pipeline.

Presentation layer only. All domain logic lives in ``backend/puzzle_manager``.
The cockpit either subprocesses the puzzle_manager CLI or reads its on-disk
artifacts (SQLite, JSON state files, log files) as raw data.

See ``tools/pm_cockpit/PLAN.md`` for the architectural rationale.
"""

from __future__ import annotations

__version__ = "0.1.0"
