"""Pydantic shapes for ``source-ingest-state`` (Theme 6b).

Wire contracts for per-source ``.yengo-ingest.sqlite`` inspection and reset.
The dashboard's adapter-detail view consumes these to render the Ingest-state
tile and to power the typed-confirm reset flow without re-encoding the
SQLite layout in JS.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IngestStateStatus = Literal["healthy", "stale", "empty", "missing"]


class FailedIngestRow(BaseModel):
    """One row from ``files`` with status=FAILED."""

    rel_path: str
    skip_reason: str | None = None
    run_id: str
    content_hash: str


class SourceIngestState(BaseModel):
    """Read-only snapshot of a per-source ingest DB."""

    source_id: str
    db_path: str | None = Field(
        None,
        description="POSIX-relative path to the .yengo-ingest.sqlite file.",
    )
    db_exists: bool
    status: IngestStateStatus
    rows: int = Field(0, ge=0)
    ingested: int = Field(0, ge=0)
    skipped: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    last_modified: str | None = Field(
        None, description="ISO8601 UTC mtime of the SQLite file."
    )
    last_run_id: str | None = None
    failed_rows: list[FailedIngestRow] = Field(
        default_factory=list,
        description="Sample of failed rows (capped, newest-first).",
    )


class SourceIngestResetPreview(BaseModel):
    """Returned by ``source-ingest-state ID --reset --dry-run --json``."""

    source_id: str
    would_delete_path: str | None
    db_exists: bool
    row_count_lost: int = Field(0, ge=0)
    failed_rows_lost: int = Field(0, ge=0)
    requires_full_reingest: bool = True


class SourceIngestResetResult(BaseModel):
    """Returned by ``source-ingest-state ID --reset --json`` (apply path)."""

    source_id: str
    deleted_path: str | None
    removed: bool
    rows_lost: int = Field(0, ge=0)
