"""Pydantic preview shapes for ``--dry-run --json`` output.

These models pin the JSON contract that destructive CLI subcommands emit
when invoked with both ``--dry-run`` and ``--json``. The dashboard renders
the impact summary in a Preview modal before the operator commits to the
real run.

Schema stability matters here: the dashboard's ``GET /api/{op}/preview``
endpoints surface this shape verbatim, and Theme 1 of the dashboard
enrichment plan pins the schema with backend tests. Any breaking change
must be coordinated with ``tools/yengo_dashboard/`` consumers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RollbackPreview(BaseModel):
    """``rollback --dry-run --json`` payload.

    Lists every puzzle the rollback would touch (capped at the CLI's
    ``max_batch_size`` — currently 10000). ``affected_runs`` always
    contains exactly one entry today (rollback only operates by run_id),
    but the field is plural to keep the contract stable if per-source
    rollback ever lands.
    """

    affected_puzzles: list[str] = Field(
        default_factory=list,
        description=(
            "Puzzle IDs (content_hash) that would be deleted. Order matches "
            "the publish-log scan order — not lexicographic."
        ),
    )
    affected_runs: list[str] = Field(
        default_factory=list,
        description="run_id values whose puzzles would be removed.",
    )
    puzzles_affected: int = Field(
        ...,
        ge=0,
        description="len(affected_puzzles); duplicated as a count for cheap rendering.",
    )
    reversible: bool = Field(
        ...,
        description=(
            "False — rollback deletes SGF files and rebuilds the search DB. "
            "The publish-log entries remain so the operator can re-run the "
            "ingest, but the original SGF bytes are gone unless backed up."
        ),
    )
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "Pre-execution errors (e.g., 'No publish log entries found for "
            "run_id=X', or batch-size cap exceeded). Empty on a clean preview."
        ),
    )


class VacuumDbPreview(BaseModel):
    """``vacuum-db --dry-run --json`` payload.

    Counts the orphan rows in ``yengo-content.db`` (rows whose
    ``content_hash`` no longer has a matching SGF on disk) and reports
    whether ``--rebuild`` was requested. ``freed_bytes_estimate`` is a
    rough estimate from row count × average row size — the actual freed
    space depends on SQLite page packing.
    """

    orphan_rows: int = Field(
        ..., ge=0, description="content_hash rows in yengo-content.db with no matching SGF."
    )
    on_disk_files: int = Field(
        ..., ge=0, description="Total SGF files found under output_dir/sgf/."
    )
    freed_bytes_estimate: int = Field(
        ...,
        ge=0,
        description=(
            "Rough estimate of bytes that would be freed by removing orphan "
            "rows. Sourced from row_count × estimated avg row size; do not "
            "use for capacity planning, only for operator orientation."
        ),
    )
    rebuild: bool = Field(
        ...,
        description=(
            "True if --rebuild was requested. When true, vacuum will also "
            "rebuild yengo-search.db from disk after orphan removal."
        ),
    )
    has_content_db: bool = Field(
        ..., description="False if yengo-content.db is missing — vacuum is a no-op."
    )


class CleanPreviewItem(BaseModel):
    """One entry in a ``CleanPreview.would_delete`` list."""

    path: str = Field(
        ...,
        description=(
            "Relative POSIX path from the project root. Forward slashes only. "
            "Mirrors the project-wide path serialization rule (see CLAUDE.md)."
        ),
    )
    bytes: int = Field(
        ..., ge=0, description="File size in bytes (from stat() at preview time)."
    )


class CleanPreview(BaseModel):
    """``clean --dry-run --json`` payload.

    The dashboard's Preview modal uses this to render an exact "what
    would be deleted" list before the operator commits the destructive
    run. ``would_delete`` is the authoritative enumeration; ``total_*``
    are convenience aggregates so the modal can render headline numbers
    without summing in JS.
    """

    target: str | None = Field(
        ...,
        description=(
            "The --target argument (None when running retention-based default "
            "cleanup of logs/state/failed/raw)."
        ),
    )
    retention_days: int = Field(
        ...,
        ge=0,
        description=(
            "Retention threshold in days. Used by the default cleanup and by "
            "the publish-logs target. Echoed back so the dashboard can show "
            "'older than N days' in the preview header."
        ),
    )
    would_delete: list[CleanPreviewItem] = Field(
        default_factory=list,
        description=(
            "Files that would be unlinked. Order is the natural enumeration "
            "order of the underlying scan (glob/rglob) — not lexicographic "
            "and not by size. The dashboard re-sorts as needed."
        ),
    )
    total_files: int = Field(
        ..., ge=0, description="len(would_delete); duplicated for cheap rendering."
    )
    total_bytes: int = Field(
        ..., ge=0, description="sum(item.bytes for item in would_delete)."
    )
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal scan warnings (e.g., a directory the scanner could not "
            "stat). Empty on a clean preview. Distinct from CLI errors which "
            "exit non-zero."
        ),
    )
