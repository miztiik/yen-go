"""Short-running admin routes for yengo_dashboard.

These wrap ``puzzle_manager`` subcommands that complete in well under a
second and have no streaming output worth surfacing live: setting/clearing
the active adapter and querying the publish-log audit trail. They go
straight through ``PipelineRunner`` (synchronous subprocess) rather than
``RunController`` (long-lived stream + busy-guard).

Adapter mutations DO NOT participate in the single-active-run guard. The
config-lock the CLI takes internally is the right serialization point —
it's what protects ``sources.json`` from concurrent edits whether the
edit comes from the cockpit or a terminal. ``--force/-f`` is forwarded so
the operator can break a stale lock without leaving the UI.

Endpoints
---------

- ``POST /api/adapter/enable``     — ``enable-adapter ADAPTER_ID [--force]``
- ``POST /api/adapter/disable``    — ``disable-adapter [--force]``
- ``GET  /api/publish-log/search`` — ``publish-log search --format json …``
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from tools.yengo_dashboard.server.models import (
    CliInvocationResponse,
    DisableAdapterRequest,
    EnableAdapterRequest,
    PublishLogSearchResponse,
)
from tools.yengo_dashboard.server.pipeline_runner import PipelineCommandError, PipelineRunner


def build_admin_router(*, runner: PipelineRunner) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["admin"])

    @router.post("/adapter/enable", response_model=CliInvocationResponse)
    def enable_adapter(body: EnableAdapterRequest) -> CliInvocationResponse:
        # Like lock_release: never raises on non-zero exit. The CLI's stderr
        # ("config locked", "unknown adapter id", etc.) is the operator-facing
        # answer and must reach the UI verbatim, not be hidden behind a 502.
        result = runner.enable_adapter(body.adapter_id, force=body.force)
        return CliInvocationResponse(**result)

    @router.post("/adapter/disable", response_model=CliInvocationResponse)
    def disable_adapter(body: DisableAdapterRequest) -> CliInvocationResponse:
        result = runner.disable_adapter(force=body.force)
        return CliInvocationResponse(**result)

    @router.get("/publish-log/search", response_model=PublishLogSearchResponse)
    def publish_log_search(
        run_id: str | None = Query(default=None),
        puzzle_id: str | None = Query(default=None),
        source: str | None = Query(default=None),
        trace_id: str | None = Query(default=None),
        date: str | None = Query(default=None, description="YYYY-MM-DD"),
        from_: str | None = Query(default=None, alias="from", description="YYYY-MM-DD"),
        to: str | None = Query(default=None, description="YYYY-MM-DD"),
        limit: int | None = Query(default=None, ge=1),
    ) -> PublishLogSearchResponse:
        params = {
            "run_id": run_id,
            "puzzle_id": puzzle_id,
            "source": source,
            "trace_id": trace_id,
            "date": date,
            "from": from_,
            "to": to,
            "limit": limit,
        }
        try:
            payload = runner.publish_log_search(params)
        except PipelineCommandError as exc:
            # The CLI rejects searches with no filter at all. Translate that
            # to 400 so the UI can show the operator a meaningful error
            # without round-tripping a generic 502. The CLI's hint message
            # ("Use one of: --run-id, ...") goes to stdout, not stderr, so
            # we surface both streams.
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "publish-log search failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return PublishLogSearchResponse(raw=payload)

    return router
