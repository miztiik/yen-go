"""Read-only HTTP endpoints for pm_cockpit.

These never mutate state. Per principle #6, they either:
  - Subprocess the puzzle_manager CLI for any interpretation-heavy data, or
  - Return raw rows from SQLite/JSON state files for pure data passthrough.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query, Request

from tools.pm_cockpit import __version__
from tools.pm_cockpit.server.models import (
    AdaptersResponse,
    HealthResponse,
    InventoryResponse,
    RunsResponse,
)
from tools.pm_cockpit.server.pipeline_runner import PipelineCommandError, PipelineRunner
from tools.pm_cockpit.server.state_reader import StateReader


def build_read_router(
    *,
    started_at: float,
    runner: PipelineRunner,
    state_reader: StateReader,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["read"])

    @router.get("/health", response_model=HealthResponse)
    def health(_request: Request) -> HealthResponse:
        return HealthResponse(
            ok=True,
            version=__version__,
            uptime_s=round(time.monotonic() - started_at, 3),
        )

    @router.get("/adapters", response_model=AdaptersResponse)
    def adapters(_request: Request) -> AdaptersResponse:
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

    return router
