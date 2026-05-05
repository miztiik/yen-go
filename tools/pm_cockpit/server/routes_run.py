"""Mutating + streaming HTTP routes for pm_cockpit.

These endpoints wrap ``RunController`` (a thin subprocess manager) and the
``puzzle_manager config-lock`` CLI. Per principle #6, the cockpit never
decides what the pipeline's exit code or output mean — it forwards bytes,
process state, and OS signals.

Endpoints
---------

- ``GET  /api/run/active``               — current cockpit-managed run snapshot
- ``POST /api/run``                      — spawn a new run (409 if one is active)
- ``POST /api/run/{handle}/cancel``      — SIGTERM the run (idempotent if terminal)
- ``GET  /api/run/{handle}/events``      — SSE stream: line | status | end events
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from tools.pm_cockpit.server.models import (
    ActiveRunResponse,
    RunSnapshot,
    RunStartRequest,
    RunTailLine,
    RunTailResponse,
)
from tools.pm_cockpit.server.run_controller import (
    NoSuchRunError,
    RunBusyError,
    RunController,
)


def _build_args(req: RunStartRequest) -> list[str]:
    """Translate a ``RunStartRequest`` to the argv tail for ``puzzle_manager``.

    Order doesn't matter to argparse, but we keep ``run`` first and flags in
    a stable order so subprocess command lines are easy to read in logs.
    """
    args: list[str] = ["run"]
    if req.source is not None:
        args += ["--source", req.source]
        if req.source_override:
            args.append("--source-override")
    if req.stage is not None:
        args += ["--stage", req.stage]
    if req.fresh:
        args.append("--fresh")
    if req.dry_run:
        args.append("--dry-run")
    if req.no_enrichment:
        args.append("--no-enrichment")
    return args


def build_run_router(*, controller: RunController) -> APIRouter:
    router = APIRouter(prefix="/api/run", tags=["run"])

    @router.get("/active", response_model=ActiveRunResponse)
    def active(_request: Request) -> ActiveRunResponse:
        snap = controller.active()
        return ActiveRunResponse(active=RunSnapshot(**snap) if snap else None)

    @router.post("", response_model=RunSnapshot, status_code=202)
    def start_run(body: RunStartRequest) -> RunSnapshot:
        args = _build_args(body)
        try:
            snap = controller.start(args)
        except RunBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RunSnapshot(**snap)

    @router.post("/{handle}/cancel", response_model=RunSnapshot, status_code=202)
    def cancel_run(handle: str) -> RunSnapshot:
        try:
            snap = controller.cancel(handle)
        except NoSuchRunError as exc:
            raise HTTPException(status_code=404, detail=f"unknown handle: {handle}") from exc
        return RunSnapshot(**snap)

    @router.get("/{handle}/tail", response_model=RunTailResponse)
    def tail_run(
        handle: str,
        n: int = Query(default=8, ge=1, le=200, description="Number of trailing lines to return."),
    ) -> RunTailResponse:
        # The controller retains exactly one run; reject mismatched handles
        # rather than silently returning an empty list.
        snap = controller.active()
        if snap is None or snap["handle"] != handle:
            raise HTTPException(status_code=404, detail=f"unknown handle: {handle}")
        lines = controller.tail()[-n:]
        return RunTailResponse(
            handle=handle,
            status=snap["status"],
            exit_code=snap["exit_code"],
            line_count=snap["line_count"],
            lines=[
                RunTailLine(ts=ln.ts, stream=ln.stream, text=ln.text, seq=ln.seq)
                for ln in lines
            ],
        )

    @router.get("/{handle}/events")
    async def stream_events(handle: str, request: Request) -> StreamingResponse:
        # Verify the handle matches the active or last-known run. We do NOT
        # support streaming arbitrary historical handles — the controller
        # only retains one run at a time.
        snap = controller.active()
        if snap is None or snap["handle"] != handle:
            raise HTTPException(status_code=404, detail=f"unknown handle: {handle}")

        loop = asyncio.get_running_loop()
        sub, backlog = controller.subscribe(loop)

        async def event_source() -> AsyncIterator[bytes]:
            try:
                # Replay the tail buffer so the client doesn't miss lines that
                # already arrived before the SSE was opened.
                for line in backlog:
                    yield _sse(
                        "line",
                        {"ts": line.ts, "stream": line.stream, "text": line.text, "seq": line.seq},
                    )
                while True:
                    if await request.is_disconnected():
                        return
                    try:
                        kind, payload = await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        # Heartbeat keeps proxies/load balancers from killing
                        # an idle stream. Comment lines are valid SSE no-ops.
                        yield b": keepalive\n\n"
                        continue
                    if kind == "line":
                        yield _sse(
                            "line",
                            {
                                "ts": payload.ts,
                                "stream": payload.stream,
                                "text": payload.text,
                                "seq": payload.seq,
                            },
                        )
                    elif kind == "status":
                        yield _sse("status", payload)
                    elif kind == "end":
                        yield _sse("end", {})
                        return
            finally:
                controller.unsubscribe(sub)

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={
                # Disable buffering on intermediaries (uvicorn doesn't, but
                # any reverse proxy a user puts in front needs the hint).
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return router


def _sse(event: str, data: dict) -> bytes:
    """Format a single SSE frame. Uses default JSON separators for compactness."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n".encode("utf-8")
