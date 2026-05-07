"""Pydantic schemas for cockpit HTTP responses.

These types describe the JSON the cockpit sends to the browser. They MUST stay
in sync with the JSON the puzzle_manager CLI emits — the cockpit is a thin
projection of CLI output, not a re-interpretation of pipeline state.

Per principle #6 (presentation-only boundary), this module never derives new
domain meanings; it only mirrors the named buckets that the CLI already
produces (``ingested``, ``skipped``, ``failed``, ``total`` from
``source-status --json``; etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """``GET /api/health`` payload."""

    ok: bool = Field(..., description="Always true when the server can respond.")
    version: str = Field(..., description="yengo_dashboard semver.")
    uptime_s: float = Field(..., ge=0.0, description="Wall-clock seconds since process start.")


class AdapterRow(BaseModel):
    """One per-source row, mirroring ``puzzle_manager source-status --json``.

    Field meanings are owned by the pipeline. See
    ``backend.puzzle_manager.cli.cmd_source_status`` for the source of truth.
    """

    id: str
    adapter: str
    source_root: str | None
    db_path: str | None
    db_exists: bool
    schema_version: int | None
    ingested: int
    skipped: int
    failed: int
    total: int
    db_size_bytes: int | None
    db_mtime: str | None
    error: str | None


class AdaptersResponse(BaseModel):
    """``GET /api/adapters`` payload."""

    sources: list[AdapterRow]
    active_adapter: str | None = Field(
        default=None,
        description=(
            "ID of the currently-active adapter from sources.json, or null. "
            "The pipeline rejects --source mismatches without --source-override."
        ),
    )


class InventoryResponse(BaseModel):
    """``GET /api/inventory`` payload.

    Pure passthrough of the backend's ``inventory.json`` snapshot. The
    cockpit never opens ``yengo-search.db`` directly — that file is owned
    by the pipeline and Windows file-lock contention with vacuum/clean was
    the original motivation for the snapshot pattern. Field names mirror
    the snapshot keys verbatim.
    """

    db_path: str | None = Field(
        ..., description="POSIX-relative path to yengo-search.db, or null if missing."
    )
    db_exists: bool
    snapshot_exists: bool = Field(
        default=False,
        description=(
            "True iff inventory.json is present. False on fresh checkouts "
            "or pre-snapshot pipeline versions — counts will all be zero."
        ),
    )
    snapshot_path: str | None = Field(
        default=None,
        description="POSIX-relative path to inventory.json (whether or not it exists).",
    )
    advice: str | None = Field(
        default=None,
        description=(
            "Operator-facing hint, populated only when snapshot_exists is "
            "false (e.g., 'Run vacuum-db to generate inventory.json')."
        ),
    )
    puzzles_total: int
    collections_total: int
    daily_schedule_total: int
    by_level_id: dict[str, int] = Field(
        default_factory=dict,
        description="puzzles count keyed by level_id (string for JSON-key safety).",
    )
    by_content_type: dict[str, int] = Field(
        default_factory=dict,
        description="puzzles count keyed by content_type (1/2/3).",
    )
    by_collection_category: dict[str, int] = Field(
        default_factory=dict,
        description="collections count keyed by category (author/technique/...).",
    )
    schema_version: int | None = Field(
        default=None,
        description="DB schema version from db-version.json, or null if file missing.",
    )
    db_version: str | None = Field(
        default=None,
        description="DB version timestamp from db-version.json, or null if file missing.",
    )


class RunStageRow(BaseModel):
    """One stage row inside a run state file. Mirrors pipeline state schema."""

    name: str
    status: str
    started_at: str | None
    completed_at: str | None
    processed_count: int
    failed_count: int
    skipped_count: int


class RunSummary(BaseModel):
    """One run, summarised. Heavy fields (batches, file_results, config_snapshot)
    are intentionally omitted — the cockpit list view only needs the header."""

    run_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    stages: list[RunStageRow]
    failure_count: int = Field(..., description="len(state['failures']).")
    state_file: str = Field(
        ..., description="POSIX-relative path to the source JSON state file."
    )


class RunsResponse(BaseModel):
    """``GET /api/runs`` payload."""

    runs: list[RunSummary]
    total: int = Field(..., description="Total run files on disk before any limit.")


class RunStartRequest(BaseModel):
    """``POST /api/run`` body. Mirrors ``puzzle_manager run`` flags 1:1.

    Field semantics are owned by the pipeline. The cockpit only forwards.
    """

    source: str | None = Field(
        default=None,
        description="--source SOURCE_ID. None means 'use active_adapter'.",
    )
    stage: str | None = Field(
        default=None,
        description="--stage {ingest,analyze,publish}. None means full pipeline.",
    )
    fresh: bool = Field(default=False, description="--fresh")
    dry_run: bool = Field(default=False, description="--dry-run")
    source_override: bool = Field(default=False, description="--source-override")
    no_enrichment: bool = Field(default=False, description="--no-enrichment")


class RunSnapshot(BaseModel):
    """Snapshot of the active or last-known cockpit-managed run.

    This is the cockpit's view of the subprocess — distinct from the
    pipeline's run-state JSON files (which live in
    ``.pm-runtime/state/runs/`` and are surfaced via ``/api/runs``).
    """

    handle: str
    command: list[str]
    cwd: str
    started_at: str
    status: str  # one of: starting | running | completed | failed | cancelled
    pid: int | None
    exit_code: int | None
    completed_at: str | None
    line_count: int
    cancel_requested: bool


class ActiveRunResponse(BaseModel):
    """``GET /api/run/active`` payload. ``active`` is null when no run has run."""

    active: RunSnapshot | None = None


class RunTailLine(BaseModel):
    """One captured stdout/stderr line from a running cockpit subprocess."""

    ts: str
    stream: str  # "stdout" | "stderr"
    text: str
    seq: int


class RunTailResponse(BaseModel):
    """``GET /api/run/{handle}/tail`` payload — last N lines of a run.

    Returned alongside the current snapshot so a single poll gives the
    maintenance card both progress (lines) and terminal state (status,
    exit_code) without a second round-trip.
    """

    handle: str
    status: str
    exit_code: int | None
    line_count: int
    lines: list[RunTailLine]


class LockStatusResponse(BaseModel):
    """``GET /api/lock`` payload — passthrough of ``config-lock status --json``.

    The CLI owns the schema; the cockpit accepts a free-form dict so changes
    in the CLI don't need a coordinated cockpit release.
    """

    raw: dict = Field(..., description="Verbatim CLI JSON output.")


class LockReleaseRequest(BaseModel):
    """``POST /api/lock/release`` body. ``force`` maps to ``--force``."""

    force: bool = Field(
        default=False,
        description="--force: release even when held by a different process.",
    )


class LockReleaseResponse(BaseModel):
    """``POST /api/lock/release`` payload.

    Mirrors what the CLI actually emits (it does not produce JSON on release).
    The cockpit captures both streams and the exit code so the UI can show
    the operator the same thing they would see at a terminal.
    """

    ok: bool = Field(..., description="True iff CLI exit code was 0.")
    returncode: int
    stdout: str
    stderr: str


# ---------------- Phase 3: maintenance -----------------------------------
#
# These mutate pipeline state via long-running subcommands. They flow through
# ``RunController`` so the cockpit's single-active-run guard naturally
# serializes them against ``run`` and against each other (no concurrent
# clean-while-rolling-back footguns).


class CleanRequest(BaseModel):
    """``POST /api/clean`` body. Mirrors ``puzzle_manager clean`` flags 1:1."""

    target: str | None = Field(
        default=None,
        description=(
            "--target: staging | state | logs | puzzles-collection | "
            "publish-logs. None = retention-based cleanup."
        ),
    )
    retention_days: int | None = Field(
        default=None,
        description="--retention-days N. None = CLI default (45).",
        ge=0,
    )
    dry_run: bool | None = Field(
        default=None,
        description=(
            "--dry-run [BOOL]. None = pass nothing (CLI default — defaults "
            "to true for puzzles-collection target). True/False = pass "
            "explicit value."
        ),
    )


class RollbackRequest(BaseModel):
    """``POST /api/rollback`` body. Mirrors ``puzzle_manager rollback`` flags.

    Per-puzzle rollback was removed in Theme 17 of the dashboard enrichment
    plan: the CLI never implemented a ``RollbackManager.rollback_by_puzzle``
    method, so the prior ``--puzzle-id`` argparse surface was dead UI that
    rejected every invocation at runtime. The cockpit now exposes only the
    real, working surface — rollback by run.

    A ``reason`` is required for the audit trail; the cockpit refuses to
    forward an empty reason rather than letting the CLI fail with a vague
    message.
    """

    run_id: str = Field(
        ...,
        description="--run-id ID. Roll back all puzzles from this pipeline run.",
        min_length=1,
    )
    reason: str = Field(
        ...,
        description="--reason TEXT. Required for audit trail.",
        min_length=1,
    )
    dry_run: bool = Field(default=False, description="--dry-run")
    yes: bool = Field(
        default=False,
        description="--yes/-y. Skip confirmation prompt for large rollbacks.",
    )
    verify: bool = Field(default=False, description="--verify")


class VacuumDbRequest(BaseModel):
    """``POST /api/vacuum-db`` body. Mirrors ``puzzle_manager vacuum-db`` flags."""

    rebuild: bool = Field(
        default=False,
        description="--rebuild: also rebuild yengo-search.db from disk.",
    )
    dry_run: bool = Field(default=False, description="--dry-run")


# ---------------- Phase 3: short-running adapter + log lookups -----------


class EnableAdapterRequest(BaseModel):
    """``POST /api/adapter/enable`` body."""

    adapter_id: str = Field(..., min_length=1, description="ADAPTER_ID positional arg.")
    force: bool = Field(default=False, description="--force/-f: override config lock.")


class DisableAdapterRequest(BaseModel):
    """``POST /api/adapter/disable`` body. Clears the active adapter."""

    force: bool = Field(default=False, description="--force/-f: override config lock.")


class CliInvocationResponse(BaseModel):
    """Generic short-CLI passthrough payload.

    Used by adapter enable/disable (and any future short, non-JSON CLI
    wrappers). The cockpit forwards stdout, stderr, and exit code without
    interpretation — non-zero is a legitimate outcome the UI must show.
    """

    ok: bool = Field(..., description="True iff CLI exit code was 0.")
    returncode: int
    stdout: str
    stderr: str


class PublishLogSearchResponse(BaseModel):
    """``GET /api/publish-log/search`` payload — verbatim CLI JSON.

    The CLI owns the result shape; the cockpit accepts a free-form payload
    (list or dict) so the publish-log schema can evolve without a coordinated
    release.
    """

    raw: object = Field(..., description="Parsed CLI JSON (--format json).")


class StageLogFile(BaseModel):
    """One entry in ``GET /api/logs/stage-files``."""

    name: str = Field(..., description="Filename only — no path. e.g. '2026-05-06-ingest.log'.")
    size_bytes: int = Field(..., ge=0)
    mtime_iso: str = Field(..., description="UTC ISO-8601 modification time.")


class StageLogListResponse(BaseModel):
    """``GET /api/logs/stage-files`` payload."""

    files: list[StageLogFile] = Field(default_factory=list)
    logs_dir: str = Field(..., description="POSIX path to .pm-runtime/logs (relative to repo root).")


class StageLogTailResponse(BaseModel):
    """``GET /api/logs/stage-files/{name}`` payload."""

    name: str
    lines: list[str] = Field(default_factory=list)
    truncated: bool = Field(..., description="True if the file had more lines than requested.")
    total_lines: int = Field(..., ge=0)
