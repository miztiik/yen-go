"""Stage-log read endpoints for yengo_dashboard.

The pipeline writes per-day, per-stage logs into ``.pm-runtime/logs/`` (e.g.
``2026-05-06-ingest.log``). The cockpit's Logs tab needs to list those files
and tail individual ones without spawning a CLI subprocess for every poll.
Per principle #6 these endpoints are pure file reads with no parsing or
domain interpretation; the UI shows raw lines as-is.

Safety: the filename in the path parameter is validated against a strict
regex AND the resolved path is asserted to live inside the logs dir. This
double check prevents both "..\\..\\secrets" path-traversal and weirder
attacks like an absolute-path symlink in the logs dir.
"""

from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from tools.yengo_dashboard.server.models import (
    StageLogFile,
    StageLogListResponse,
    StageLogTailResponse,
)
from tools.yengo_dashboard.server.state_reader import StateReader

# Filenames the pipeline emits into .pm-runtime/logs/. Conservative on purpose:
# alphanumerics, dot, dash, underscore, ending in .log. Anything else is a
# 404 — even if the file legitimately exists, we don't want this endpoint to
# become a generic file-read primitive.
_SAFE_LOG_NAME = re.compile(r"^[A-Za-z0-9._-]+\.log$")

# Cap the tail size so a 2 GB log can't OOM the response. The CLI rotates
# daily but a stuck publish stage has filled multi-hundred-MB files in the
# past, and the UI never needs more than a few thousand lines at once.
_MAX_TAIL_LINES = 5000
_DEFAULT_TAIL_LINES = 500


def _logs_dir(state_reader: StateReader) -> Path:
    return state_reader._runtime() / "logs"  # noqa: SLF001 (reader owns the path convention)


def build_logs_router(*, state_reader: StateReader) -> APIRouter:
    router = APIRouter(prefix="/api/logs", tags=["logs"])

    @router.get("/stage-files", response_model=StageLogListResponse)
    def list_stage_files() -> StageLogListResponse:
        logs_dir = _logs_dir(state_reader)
        rel = logs_dir.relative_to(state_reader.repo_root) if logs_dir.is_relative_to(state_reader.repo_root) else logs_dir
        if not logs_dir.is_dir():
            return StageLogListResponse(files=[], logs_dir=str(rel).replace("\\", "/"))
        rows: list[StageLogFile] = []
        for p in sorted(logs_dir.iterdir(), key=lambda x: x.name, reverse=True):
            if not p.is_file() or not _SAFE_LOG_NAME.match(p.name):
                continue
            stat = p.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            rows.append(
                StageLogFile(
                    name=p.name,
                    size_bytes=stat.st_size,
                    mtime_iso=mtime.isoformat(),
                )
            )
        return StageLogListResponse(files=rows, logs_dir=str(rel).replace("\\", "/"))

    @router.get("/stage-files/{name}", response_model=StageLogTailResponse)
    def tail_stage_file(
        name: str,
        lines: int = Query(default=_DEFAULT_TAIL_LINES, ge=1, le=_MAX_TAIL_LINES),
    ) -> StageLogTailResponse:
        if not _SAFE_LOG_NAME.match(name):
            # 404 (not 400) so this endpoint never confirms whether a name
            # would have been accepted on a different machine — the UI can't
            # tell apart "wrong name" vs "file just rolled".
            raise HTTPException(status_code=404, detail="log file not found")
        logs_dir = _logs_dir(state_reader).resolve()
        target = (logs_dir / name).resolve()
        # Two-level safety: the regex above already guarantees no separators,
        # but a misconfigured logs_dir could still contain symlinks. Reject
        # any path that resolves outside logs_dir.
        try:
            target.relative_to(logs_dir)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="log file not found") from exc
        if not target.is_file():
            raise HTTPException(status_code=404, detail="log file not found")

        # Streaming-friendly tail: deque caps memory at `lines` rows even
        # for huge files. The UI only needs the recent tail; offering "from
        # offset N" or "page back" is out of scope for now.
        total = 0
        tail: deque[str] = deque(maxlen=lines)
        with target.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                total += 1
                tail.append(raw.rstrip("\n"))
        return StageLogTailResponse(
            name=name,
            lines=list(tail),
            truncated=total > len(tail),
            total_lines=total,
        )

    return router
