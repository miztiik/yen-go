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

- ``POST /api/clean``      — ``clean [--target T] [--retention-days N] [--dry-run [BOOL]]``
- ``POST /api/rollback``   — ``rollback (--run-id ID | --puzzle-id ID...) [--reason TEXT] …``
- ``POST /api/vacuum-db``  — ``vacuum-db [--rebuild] [--dry-run]``
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tools.yengo_dashboard.server.models import (
    CleanRequest,
    RollbackRequest,
    RunSnapshot,
    VacuumDbRequest,
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
    if (req.run_id is None) == (not req.puzzle_ids):
        # Mirrors the CLI's mutually-exclusive group requirement. We fail
        # fast at the cockpit boundary so the operator gets a 400 instead of
        # a generic non-zero CLI exit.
        raise HTTPException(
            status_code=400,
            detail="exactly one of 'run_id' or 'puzzle_ids' must be provided",
        )
    args = ["rollback", "--reason", req.reason]
    if req.run_id is not None:
        args += ["--run-id", req.run_id]
    else:
        args += ["--puzzle-id", *req.puzzle_ids]  # type: ignore[misc]
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


def build_maintenance_router(*, controller: RunController) -> APIRouter:
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

    return router
