"""HTTP routes for config-lock observation and release.

The pipeline auto-locks ``config/`` while a run is in flight to keep operators
from editing JSON underneath a running stage. If a process dies hard, the lock
can be left orphaned. These two endpoints let the cockpit surface that state
and (with explicit operator action) release it — without re-implementing any
of the underlying lock semantics, which live in ``puzzle_manager``.

Endpoints
---------

- ``GET  /api/lock``         — passthrough of ``config-lock status --json``
- ``POST /api/lock/release`` — wrap ``config-lock release [--force]``
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tools.pm_cockpit.server.models import (
    LockReleaseRequest,
    LockReleaseResponse,
    LockStatusResponse,
)
from tools.pm_cockpit.server.pipeline_runner import PipelineCommandError, PipelineRunner


def build_lock_router(*, runner: PipelineRunner) -> APIRouter:
    router = APIRouter(prefix="/api/lock", tags=["lock"])

    @router.get("", response_model=LockStatusResponse)
    def get_lock_status(_request: Request) -> LockStatusResponse:
        try:
            payload = runner.lock_status()
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager config-lock status --json failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                },
            ) from exc
        return LockStatusResponse(raw=payload)

    @router.post("/release", response_model=LockReleaseResponse)
    def release_lock(body: LockReleaseRequest) -> LockReleaseResponse:
        # Release never raises — non-zero exit is a legitimate "could not
        # release" answer that the UI surfaces as-is. The cockpit must not
        # decide what that means; the operator does.
        result = runner.lock_release(force=body.force)
        return LockReleaseResponse(**result)

    return router
