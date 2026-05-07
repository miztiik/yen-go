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

from fastapi import APIRouter, HTTPException, Query

from tools.yengo_dashboard.server.models import (
    CleanPreviewResponse,
    CleanRequest,
    RollbackPreviewResponse,
    RollbackRequest,
    RunSnapshot,
    VacuumDbPreviewResponse,
    VacuumDbRequest,
)
from tools.yengo_dashboard.server.pipeline_runner import (
    PipelineCommandError,
    PipelineRunner,
)
from tools.yengo_dashboard.server.run_controller import RunBusyError, RunController


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

    return router
