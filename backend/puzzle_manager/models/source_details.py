"""Theme 6a: per-source detail wire contract.

Wire contract for ``source-status SOURCE_ID --details --json``. Joins:
  - the per-source ingest DB summary (already produced by ``source-status``),
  - the most recent run-state JSONs scoped to this source (via
    ``config_snapshot.source_id``),
  - the most recent failures from those runs (each row carries the run_id
    and stage so the UI can deep-link),
  - a verbatim echo of the source's ``sources.json`` config block.

This module describes what the cockpit receives — the cockpit forwards it
unchanged as ``{raw: SourceDetails}`` per principle #6 (presentation-only).
``first_seen_run`` / ``last_seen_run`` are *not* surfaced here; if needed
later they can be added to ``RecentRunSummary`` without breaking the
contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecentRunSummary(BaseModel):
    """One row of the per-source recent-runs list (max 10)."""

    run_id: str
    started_at: str | None
    completed_at: str | None
    status: str
    ingested: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)


class RecentFailureSummary(BaseModel):
    """One row of the per-source recent-failures list (max 10)."""

    run_id: str
    item_id: str = Field(..., description="Puzzle/file identifier from Failure.item_id.")
    stage: str
    error_type: str
    error_message: str
    timestamp: str | None


class SummaryCounts(BaseModel):
    """Aggregate counts for the source. Mirrors the existing AdapterRow buckets."""

    ingested: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failed: int = Field(ge=0)
    total: int = Field(ge=0)


class SourceDetails(BaseModel):
    """Theme 6a: full per-source detail payload.

    The ``config`` field is intentionally typed as ``dict[str, Any]`` —
    schemas vary per adapter kind, and the cockpit's schema-driven form
    (Theme 7) consumes it directly without re-validation.
    """

    id: str
    adapter: str
    summary: SummaryCounts
    recent_runs: list[RecentRunSummary] = Field(default_factory=list)
    recent_failures: list[RecentFailureSummary] = Field(default_factory=list)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Verbatim echo of the source's `sources.json` config block.",
    )
