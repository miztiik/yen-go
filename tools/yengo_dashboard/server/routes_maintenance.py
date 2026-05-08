"""Long-running maintenance routes for yengo_dashboard.

These wrap mutating ``puzzle_manager`` subcommands that can take many seconds
to minutes (``clean``, ``rollback``, ``vacuum-db``). They route through
``RunController`` so the cockpit's single-active-run guard naturally
serializes them against ``run`` and against each other — the operator
cannot accidentally launch ``clean`` while ``rollback`` is in flight.

Live output flows through the same SSE stream as ``/api/run`` —
clients subscribe to ``/api/run/{handle}/events`` regardless of which
subcommand spawned the run. ``RunSnapshot.command`` carries the full argv
so the UI can identify which subcommand the active run is.

Endpoints
---------

- ``POST /api/clean``             — ``clean [--target T] [--retention-days N] [--dry-run [BOOL]]``
- ``POST /api/rollback``          — ``rollback --run-id ID --reason TEXT [--dry-run] [--yes] [--verify]``
- ``POST /api/vacuum-db``         — ``vacuum-db [--rebuild] [--dry-run]``
- ``GET  /api/clean/preview``     — synchronous ``clean --dry-run --json`` passthrough
- ``GET  /api/rollback/preview``  — synchronous ``rollback --dry-run --json`` passthrough
- ``GET  /api/vacuum-db/preview`` — synchronous ``vacuum-db --dry-run --json`` passthrough

The preview endpoints are GET (idempotent, cacheable, safe). They run
synchronously instead of through ``RunController`` because dry-run is
fast and the operator wants the impact summary inline before deciding
whether to commit. The mutating POSTs above remain async-via-SSE.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query

from tools.yengo_dashboard.server.models import (
    AdapterConfigAddRequest,
    AdapterConfigBootstrapRequest,
    AdapterConfigBootstrapResponse,
    AdapterConfigCloneRequest,
    AdapterConfigMutationResponse,
    AdapterConfigRemoveRequest,
    AdapterConfigUpdateRequest,
    PipelineConfigSetRequest,
    PipelineConfigSetResponse,
    PipelineConfigShowResponse,
    DailyListResponse,
    DailyStatusResponse,
    DailyPreviewResponse,
    DailyCancelRequest,
    DailyCancelResponse,
    DailyBackfillRequest,
    DailyBackfillResponse,
    CleanPreviewResponse,
    CleanRequest,
    InventoryMutationApplyResponse,
    InventoryMutationPreviewResponse,
    InventoryMutationRequest,
    RollbackPreviewResponse,
    RollbackRequest,
    RunSnapshot,
    SourceIngestStateResetPreviewResponse,
    SourceIngestStateResetResultResponse,
    VacuumDbPreviewResponse,
    VacuumDbRequest,
)
from tools.yengo_dashboard.server.pipeline_runner import (
    PipelineCommandError,
    PipelineRunner,
)
from tools.yengo_dashboard.server.run_controller import RunBusyError, RunController


_ADAPTER_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _build_clean_args(req: CleanRequest) -> list[str]:
    args = ["clean"]
    if req.target is not None:
        args += ["--target", req.target]
    if req.retention_days is not None:
        args += ["--retention-days", str(req.retention_days)]
    if req.dry_run is not None:
        # ``--dry-run`` accepts an optional BOOL; when None we omit the flag
        # so the CLI's per-target default applies (true for puzzles-collection).
        args += ["--dry-run", "true" if req.dry_run else "false"]
    return args


def _build_rollback_args(req: RollbackRequest) -> list[str]:
    # Per Theme 17, only run-id rollback is supported. RollbackRequest pins
    # run_id as required so Pydantic catches missing values before we get here.
    args = ["rollback", "--reason", req.reason, "--run-id", req.run_id]
    if req.dry_run:
        args.append("--dry-run")
    if req.yes:
        args.append("--yes")
    if req.verify:
        args.append("--verify")
    return args


def _build_vacuum_args(req: VacuumDbRequest) -> list[str]:
    args = ["vacuum-db"]
    if req.rebuild:
        args.append("--rebuild")
    if req.dry_run:
        args.append("--dry-run")
    return args


def _start_or_409(controller: RunController, args: list[str]) -> RunSnapshot:
    try:
        snap = controller.start(args)
    except RunBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunSnapshot(**snap)


def build_maintenance_router(
    *,
    controller: RunController,
    runner: PipelineRunner,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["maintenance"])

    @router.post("/clean", response_model=RunSnapshot, status_code=202)
    def clean(body: CleanRequest) -> RunSnapshot:
        return _start_or_409(controller, _build_clean_args(body))

    @router.post("/rollback", response_model=RunSnapshot, status_code=202)
    def rollback(body: RollbackRequest) -> RunSnapshot:
        return _start_or_409(controller, _build_rollback_args(body))

    @router.post("/vacuum-db", response_model=RunSnapshot, status_code=202)
    def vacuum_db(body: VacuumDbRequest) -> RunSnapshot:
        return _start_or_409(controller, _build_vacuum_args(body))

    @router.get("/clean/preview", response_model=CleanPreviewResponse)
    def clean_preview(
        target: str | None = Query(
            default=None,
            description=(
                "--target: staging | state | logs | puzzles-collection | "
                "publish-logs. Omit for retention-based default."
            ),
        ),
        retention_days: int | None = Query(
            default=None, ge=0, description="--retention-days N. Omit for CLI default (45)."
        ),
    ) -> CleanPreviewResponse:
        try:
            payload = runner.clean_preview(
                target=target, retention_days=retention_days,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager clean --dry-run --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return CleanPreviewResponse(raw=payload)

    @router.get("/rollback/preview", response_model=RollbackPreviewResponse)
    def rollback_preview(
        run_id: str = Query(
            ..., min_length=1, description="--run-id ID. Required.",
        ),
        reason: str = Query(
            default="preview-only",
            description=(
                "--reason TEXT. The CLI requires a reason even in preview "
                "mode (it pre-validates the audit message that the real "
                "run will use); the dashboard supplies a placeholder when "
                "the operator has not yet entered one."
            ),
        ),
    ) -> RollbackPreviewResponse:
        try:
            payload = runner.rollback_preview(run_id=run_id, reason=reason)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager rollback --dry-run --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return RollbackPreviewResponse(raw=payload)

    @router.get("/vacuum-db/preview", response_model=VacuumDbPreviewResponse)
    def vacuum_db_preview(
        rebuild: bool = Query(
            default=False, description="--rebuild flag passthrough.",
        ),
    ) -> VacuumDbPreviewResponse:
        try:
            payload = runner.vacuum_db_preview(rebuild=rebuild)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager vacuum-db --dry-run --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return VacuumDbPreviewResponse(raw=payload)

    @router.post(
        "/inventory/preview",
        response_model=InventoryMutationPreviewResponse,
    )
    def inventory_preview(body: InventoryMutationRequest) -> InventoryMutationPreviewResponse:
        """Theme 14c3: synchronous dry-run preview for the modal's first step.

        Inventory ops are fast (single-digit seconds even on 9K puzzles), so
        the preview runs inline rather than through ``RunController``. The
        modal renders ``raw`` directly — schema is owned by the CLI.
        """
        try:
            payload = runner.inventory_mutation_preview(op=body.op)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"puzzle_manager inventory --{body.op} --dry-run --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return InventoryMutationPreviewResponse(raw=payload)

    @router.post(
        "/inventory/apply",
        response_model=InventoryMutationApplyResponse,
    )
    def inventory_apply(body: InventoryMutationRequest) -> InventoryMutationApplyResponse:
        """Theme 14c3: synchronous apply for the modal's commit step.

        The CLI takes ``PipelineLock`` internally; if a pipeline run is
        already in flight the subprocess exits non-zero and we surface that
        as 502 (operator should retry once the run frees the lock).
        """
        try:
            payload = runner.inventory_mutation_apply(op=body.op)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"puzzle_manager inventory --{body.op} --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return InventoryMutationApplyResponse(raw=payload)

    @router.get(
        "/adapters/{source_id}/ingest-state/preview",
        response_model=SourceIngestStateResetPreviewResponse,
    )
    def source_ingest_state_preview(
        source_id: str,
    ) -> SourceIngestStateResetPreviewResponse:
        """Theme 6b: synchronous dry-run preview for the reset modal.

        Mirrors the ``/api/inventory/preview`` two-stage pattern but lives on
        a per-source URL so deep-linking from the adapter detail page is
        natural. CLI failures (returncode 2 for unknown source / no path)
        surface as 400 so the UI shows the operator the actual stderr.
        """
        try:
            payload = runner.source_ingest_state_reset_preview(source_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "puzzle_manager source-ingest-state --reset --dry-run --json failed"
                    ),
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return SourceIngestStateResetPreviewResponse(raw=payload)

    @router.post(
        "/adapters/{source_id}/ingest-state/reset",
        response_model=SourceIngestStateResetResultResponse,
    )
    def source_ingest_state_apply(
        source_id: str,
    ) -> SourceIngestStateResetResultResponse:
        """Theme 6b: apply path for the per-source ingest-DB reset.

        The CLI removes the SQLite file (and WAL/SHM sidecars) atomically via
        :meth:`SourceIngestDB.wipe`. There's no pipeline lock for this op —
        a concurrent ingest run would either re-create the file fresh or
        fail open() naturally; either is acceptable since the operator
        explicitly chose the wipe.
        """
        try:
            payload = runner.source_ingest_state_reset_apply(source_id)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager source-ingest-state --reset --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return SourceIngestStateResetResultResponse(raw=payload)

    def _adapter_config_mutation(call):
        try:
            payload = call()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager adapter-config mutation failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterConfigMutationResponse(raw=payload)

    @router.post(
        "/adapter-config",
        response_model=AdapterConfigMutationResponse,
    )
    def adapter_config_add(
        body: AdapterConfigAddRequest,
    ) -> AdapterConfigMutationResponse:
        """Theme 7b: append a new source via ``adapter-config add``."""
        if not _ADAPTER_ID_RE.match(body.id):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "invalid source id",
                    "field": "id",
                    "pattern": _ADAPTER_ID_RE.pattern,
                    "value": body.id,
                },
            )
        return _adapter_config_mutation(lambda: runner.adapter_config_add(
            source_id=body.id, name=body.name,
            adapter=body.adapter, config=body.config,
        ))

    @router.post(
        "/adapter-config/{source_id}/clone",
        response_model=AdapterConfigMutationResponse,
    )
    def adapter_config_clone(
        source_id: str, body: AdapterConfigCloneRequest,
    ) -> AdapterConfigMutationResponse:
        """Theme 7b: clone a source via ``adapter-config clone``."""
        return _adapter_config_mutation(lambda: runner.adapter_config_clone(
            source_id=source_id, new_id=body.new_id, new_name=body.new_name,
        ))

    @router.post(
        "/adapter-config/{source_id}/update",
        response_model=AdapterConfigMutationResponse,
    )
    def adapter_config_update(
        source_id: str, body: AdapterConfigUpdateRequest,
    ) -> AdapterConfigMutationResponse:
        """Theme 7b: patch a source via ``adapter-config update``."""
        return _adapter_config_mutation(lambda: runner.adapter_config_update(
            source_id=source_id, set_pairs=body.set_pairs, name=body.name,
        ))

    @router.post(
        "/adapter-config/{source_id}/remove",
        response_model=AdapterConfigMutationResponse,
    )
    def adapter_config_remove(
        source_id: str, body: AdapterConfigRemoveRequest,
    ) -> AdapterConfigMutationResponse:
        """Theme 7b: delete a source via ``adapter-config remove``."""
        return _adapter_config_mutation(lambda: runner.adapter_config_remove(
            source_id=source_id, force=body.force,
        ))

    @router.post(
        "/adapter-config/bootstrap",
        response_model=AdapterConfigBootstrapResponse,
    )
    def adapter_config_bootstrap(
        body: AdapterConfigBootstrapRequest,
    ) -> AdapterConfigBootstrapResponse:
        """Theme 7c: bootstrap-wizard preview/apply for a source folder."""
        try:
            payload = runner.adapter_config_bootstrap(
                from_folder=body.from_folder, adapter=body.adapter,
                id_prefix=body.id_prefix, dry_run=body.dry_run,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager adapter-config bootstrap failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterConfigBootstrapResponse(raw=payload)

    @router.get(
        "/pipeline-config",
        response_model=PipelineConfigShowResponse,
    )
    def pipeline_config_show() -> PipelineConfigShowResponse:
        """Theme 7d: read pipeline.json via ``pipeline-config show``."""
        try:
            payload = runner.pipeline_config_show()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager pipeline-config show failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return PipelineConfigShowResponse(raw=payload)

    @router.post(
        "/pipeline-config",
        response_model=PipelineConfigSetResponse,
    )
    def pipeline_config_set(
        body: PipelineConfigSetRequest,
    ) -> PipelineConfigSetResponse:
        """Theme 7d: dotted KEY=VALUE mutation of pipeline.json."""
        try:
            payload = runner.pipeline_config_set(
                set_pairs=body.set_pairs, force=body.force,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "puzzle_manager pipeline-config set failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return PipelineConfigSetResponse(raw=payload)

    @router.get(
        "/daily/list",
        response_model=DailyListResponse,
    )
    def daily_list(
        from_date: str | None = Query(default=None, alias="from"),
        to_date: str | None = Query(default=None, alias="to"),
    ) -> DailyListResponse:
        """Theme 8a: read daily_schedule rows in [from, to]."""
        try:
            payload = runner.daily_list(from_date=from_date, to_date=to_date)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager daily-list failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return DailyListResponse(raw=payload)

    @router.get(
        "/daily/status",
        response_model=DailyStatusResponse,
    )
    def daily_status(
        window_days: int = Query(default=30, ge=1, le=365),
        stale_days: int = Query(default=14, ge=0, le=365),
    ) -> DailyStatusResponse:
        """Theme 8a: rolling-window health summary."""
        try:
            payload = runner.daily_status(
                window_days=window_days, stale_days=stale_days,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager daily-status failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return DailyStatusResponse(raw=payload)

    @router.get(
        "/daily/preview",
        response_model=DailyPreviewResponse,
    )
    def daily_preview(date: str = Query(...)) -> DailyPreviewResponse:
        """Theme 8b: read-only what-would-be-generated for ``date``."""
        try:
            payload = runner.daily_preview(date=date)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager daily-preview failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return DailyPreviewResponse(raw=payload)

    def _daily_cancel_call(req: DailyCancelRequest, *, dry_run: bool) -> dict:
        try:
            return runner.daily_cancel(
                date=req.date, from_date=req.from_date, to_date=req.to_date,
                dry_run=dry_run, force=req.force,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400 if exc.returncode == 2 else 502,
                detail={
                    "message": "puzzle_manager daily-cancel failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc

    @router.post(
        "/daily/cancel/preview",
        response_model=DailyCancelResponse,
    )
    def daily_cancel_preview(req: DailyCancelRequest) -> DailyCancelResponse:
        """Theme 8c: dry-run preview of cancel deletes."""
        return DailyCancelResponse(raw=_daily_cancel_call(req, dry_run=True))

    @router.post(
        "/daily/cancel/apply",
        response_model=DailyCancelResponse,
    )
    def daily_cancel_apply(req: DailyCancelRequest) -> DailyCancelResponse:
        """Theme 8c: apply (deletes daily_schedule + daily_puzzles rows)."""
        return DailyCancelResponse(raw=_daily_cancel_call(req, dry_run=False))

    def _daily_backfill_call(req: DailyBackfillRequest, *, dry_run: bool) -> dict:
        try:
            return runner.daily_backfill(
                window_days=req.window_days, dry_run=dry_run, force=req.force,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=400 if exc.returncode == 2 else 502,
                detail={
                    "message": "puzzle_manager daily-backfill failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc

    @router.post(
        "/daily/backfill/preview",
        response_model=DailyBackfillResponse,
    )
    def daily_backfill_preview(
        req: DailyBackfillRequest,
    ) -> DailyBackfillResponse:
        """Theme 8d: enumerate missing dates without writing."""
        return DailyBackfillResponse(raw=_daily_backfill_call(req, dry_run=True))

    @router.post(
        "/daily/backfill/apply",
        response_model=DailyBackfillResponse,
    )
    def daily_backfill_apply(
        req: DailyBackfillRequest,
    ) -> DailyBackfillResponse:
        """Theme 8d: generate each missing date inside one PipelineLock."""
        return DailyBackfillResponse(
            raw=_daily_backfill_call(req, dry_run=False),
        )

    return router
