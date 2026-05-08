"""Read-only HTTP endpoints for yengo_dashboard.

These never mutate state. Per principle #6, they either:
  - Subprocess the puzzle_manager CLI for any interpretation-heavy data, or
  - Return raw rows from SQLite/JSON state files for pure data passthrough.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query, Request

from tools.yengo_dashboard import __version__
from tools.yengo_dashboard.server.models import (
    ActivityResponse,
    AdaptersResponse,
    AdapterConfigListResponse,
    AdapterConfigShowResponse,
    AdapterConfigValidateResponse,
    FailuresSummaryResponse,
    HealthResponse,
    InventoryCheckResponse,
    InventoryResponse,
    LevelsListResponse,
    OpsCatalogResponse,
    RunsResponse,
    PuzzleInfoResponse,
    RunsDiffResponse,
    RuntimeInfoResponse,
    SourceDetailsResponse,
    SourceIngestStateResponse,
    TagsListResponse,
)
from tools.yengo_dashboard.server.pipeline_runner import PipelineCommandError, PipelineRunner
from tools.yengo_dashboard.server.state_reader import StateReader


def build_read_router(
    *,
    started_at: float,
    runner: PipelineRunner,
    state_reader: StateReader,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["read"])

    # In-process TTL cache for /api/adapters. The underlying CLI invocation
    # spawns a Python subprocess (~300-600ms cold). Cockpit polls every 3s
    # and tab switches re-query. A 2s TTL means at most one subprocess per
    # ~2s window regardless of poll/tab pressure, while keeping data fresh.
    _adapters_cache: dict = {"ts": 0.0, "payload": None}
    _ADAPTERS_TTL_S = 2.0

    @router.get("/health", response_model=HealthResponse)
    def health(_request: Request) -> HealthResponse:
        return HealthResponse(
            ok=True,
            version=__version__,
            uptime_s=round(time.monotonic() - started_at, 3),
        )

    @router.get("/adapters", response_model=AdaptersResponse)
    def adapters(_request: Request) -> AdaptersResponse:
        now = time.monotonic()
        cached = _adapters_cache["payload"]
        if cached is not None and (now - _adapters_cache["ts"]) < _ADAPTERS_TTL_S:
            return AdaptersResponse.model_validate(cached)
        try:
            payload = runner.source_status()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager source-status --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        _adapters_cache["payload"] = payload
        _adapters_cache["ts"] = now
        # Pydantic validates the shape we promised; mismatches surface as 500
        # so we notice when the CLI contract drifts.
        return AdaptersResponse.model_validate(payload)

    @router.get("/inventory", response_model=InventoryResponse)
    def inventory(_request: Request) -> InventoryResponse:
        return InventoryResponse.model_validate(state_reader.read_inventory())

    @router.get("/runs", response_model=RunsResponse)
    def runs(
        _request: Request,
        limit: int = Query(50, ge=0, le=500),
    ) -> RunsResponse:
        return RunsResponse.model_validate(state_reader.read_runs(limit=limit))

    @router.get("/runs/diff", response_model=RunsDiffResponse)
    def runs_diff(
        _request: Request,
        run_a: str = Query(..., min_length=1),
        run_b: str = Query(..., min_length=1),
        max_samples: int = Query(20, ge=0, le=500),
    ) -> RunsDiffResponse:
        """Theme 9: read-only set diff over published puzzle IDs + stats Δ."""
        try:
            payload = runner.runs_diff(
                run_a=run_a, run_b=run_b, max_samples=max_samples,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager runs-diff failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return RunsDiffResponse(raw=payload)

    @router.get("/puzzle/{puzzle_id}", response_model=PuzzleInfoResponse)
    def puzzle_info(
        _request: Request,
        puzzle_id: str,
    ) -> PuzzleInfoResponse:
        """Theme 10: read-only puzzle ID join (publish-log + SGF + daily + audit)."""
        try:
            payload = runner.puzzle_info(puzzle_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager puzzle-info failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return PuzzleInfoResponse(raw=payload)

    @router.get("/status/failures-summary", response_model=FailuresSummaryResponse)
    def failures_summary(
        _request: Request,
        last: int = Query(10, ge=1, le=200),
    ) -> FailuresSummaryResponse:
        """Theme 2b: passthrough of ``status --failures-summary --json``.

        Pipeline tab renders the resulting groups above the History list.
        """
        try:
            payload = runner.failures_summary(last=last)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager status --failures-summary failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return FailuresSummaryResponse(raw=payload)

    @router.get("/activity", response_model=ActivityResponse)
    def activity(
        _request: Request,
        from_ts: str | None = Query(default=None, alias="from"),
        to_ts: str | None = Query(default=None, alias="to"),
        kinds: str | None = Query(
            default=None,
            description="Comma-separated subset of {run,maintenance,publish}.",
        ),
        limit: int = Query(100, ge=1, le=1000),
    ) -> ActivityResponse:
        """Theme 13b: passthrough of ``activity --json``.

        Activity tab merges run/audit/publish-log events into a single
        timeline. Errors propagate as 400 so the UI can surface CLI stderr.
        """
        kind_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
        try:
            payload = runner.activity(
                from_ts=from_ts,
                to_ts=to_ts,
                kinds=kind_list,
                limit=limit,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager activity --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return ActivityResponse(raw=payload)

    @router.get("/runtime-info", response_model=RuntimeInfoResponse)
    def runtime_info(_request: Request) -> RuntimeInfoResponse:
        """Theme 3b: passthrough of ``runtime-info --json``.

        System dialog Footprint tab + Operations Clean per-target estimates
        consume this. Errors propagate as 400 so the UI can surface the CLI
        stderr instead of a generic 5xx.
        """
        try:
            payload = runner.runtime_info()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager runtime-info failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return RuntimeInfoResponse(raw=payload)

    @router.get("/inventory/check", response_model=InventoryCheckResponse)
    def inventory_check(_request: Request) -> InventoryCheckResponse:
        """Theme 14b: passthrough of ``inventory --check --json``.

        Library tab renders a green/amber/rose health badge from
        ``raw.ok`` and an issues table from ``raw.issues``. The CLI
        exits 1 when issues are present — not a failure for our
        purposes — so the runner tolerates returncode 0 and 1.
        """
        try:
            payload = runner.inventory_check()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager inventory --check --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return InventoryCheckResponse(raw=payload)

    @router.get("/ops/catalog", response_model=OpsCatalogResponse)
    def ops_catalog(_request: Request) -> OpsCatalogResponse:
        """Theme 16b: passthrough of ``ops catalog --json``.

        Operations page consumes this to drive section grouping (maintenance
        / destructive / diagnostic) and decoration (preview button gate,
        typed-confirm trigger via the ``destructive`` section). Per principle
        #6 the catalog is the single source of truth — re-classifying an op
        on the backend reshapes the UI without a coordinated cockpit release.
        """
        try:
            payload = runner.ops_catalog()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager ops catalog --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return OpsCatalogResponse(raw=payload)

    @router.get("/tags", response_model=TagsListResponse)
    def tags_list(_request: Request) -> TagsListResponse:
        """Theme 5: passthrough of ``tags list --with-usage --json``."""
        try:
            payload = runner.tags_list(with_usage=True)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager tags list --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return TagsListResponse(raw=payload)

    @router.get("/levels", response_model=LevelsListResponse)
    def levels_list(_request: Request) -> LevelsListResponse:
        """Theme 5: passthrough of ``levels list --with-usage --json``."""
        try:
            payload = runner.levels_list(with_usage=True)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager levels list --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return LevelsListResponse(raw=payload)

    @router.get("/adapters/{source_id}/details", response_model=SourceDetailsResponse)
    def source_details(_request: Request, source_id: str) -> SourceDetailsResponse:
        """Theme 6a: passthrough of ``source-status --source ID --details --json``.

        Adapter detail SPA route consumes this for summary tile + recent-runs +
        recent-failures + config echo. Errors propagate as 400 so the UI can
        surface the CLI stderr (e.g., unknown source ID).
        """
        try:
            payload = runner.source_details(source_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager source-status --details failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return SourceDetailsResponse(raw=payload)

    @router.get(
        "/adapters/{source_id}/ingest-state",
        response_model=SourceIngestStateResponse,
    )
    def source_ingest_state(_request: Request, source_id: str) -> SourceIngestStateResponse:
        """Theme 6b: passthrough of ``source-ingest-state ID --json``.

        Adapter detail SPA route's "Ingest state" tile consumes this. CLI
        returncode 2 (unknown source / no path) maps to 400 so the UI can
        surface the actual error message.
        """
        try:
            payload = runner.source_ingest_state(source_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager source-ingest-state --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return SourceIngestStateResponse(raw=payload)

    @router.get("/adapter-config", response_model=AdapterConfigListResponse)
    def adapter_config_list(_request: Request) -> AdapterConfigListResponse:
        """Theme 7a: passthrough of ``adapter-config list --json``.

        Adapters page (List pane) consumes this. Returns ``{active_adapter, sources}``
        with each source augmented with derived ``active`` + ``path_exists`` flags
        so the table can render those columns without a second round-trip.
        """
        try:
            payload = runner.adapter_config_list()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager adapter-config list --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterConfigListResponse(raw=payload)

    @router.get("/adapter-config/validate", response_model=AdapterConfigValidateResponse)
    def adapter_config_validate(_request: Request) -> AdapterConfigValidateResponse:
        """Theme 7a: passthrough of ``adapter-config validate-all --json``.

        Adapters page renders the per-source OK/FAIL badges from this report.
        Health pill aggregates ``ok`` across all rows.
        """
        try:
            payload = runner.adapter_config_validate_all()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager adapter-config validate-all --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterConfigValidateResponse(raw=payload)

    @router.get(
        "/adapter-config/{source_id}", response_model=AdapterConfigShowResponse,
    )
    def adapter_config_show(_request: Request, source_id: str) -> AdapterConfigShowResponse:
        """Theme 7a: passthrough of ``adapter-config show ID --json``.

        Adapter Detail page's "Configuration" tab and the future Edit form
        consume this — the schema fragment lets the form render schema-driven
        fields without re-encoding the schema in JS (cockpit principle #6).
        """
        try:
            payload = runner.adapter_config_show(source_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager adapter-config show --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterConfigShowResponse(raw=payload)

    return router
