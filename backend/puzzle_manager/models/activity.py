"""Unified activity-feed aggregation (Theme 13a).

Merges three on-disk event sources into a single timeline so the dashboard
can answer "what happened in the last hour?" without forcing the operator
to fuse pipeline runs, audit trail, and publish events by hand:

1. ``state/runs/*.json``        → ``kind=run`` (one event per terminal run)
2. ``ops_dir/audit.jsonl``      → ``kind=maintenance`` (cleanup, publish ops)
3. ``ops_dir/publish-log/*.jsonl`` → ``kind=publish`` (one event per run, not
   per puzzle — puzzle-granularity is already searchable via ``publish-log
   search``).

Pure read-side: this module never writes. Every event already exists on
disk; we just union, sort by ``ts`` desc, and trim.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

EventKind = Literal["run", "maintenance", "publish"]
_VALID_KINDS: frozenset[str] = frozenset({"run", "maintenance", "publish"})


class ActivityEvent(BaseModel):
    """One row in the unified activity feed.

    Wire contract for ``activity --json``. Item-level details live behind
    ``details_ref`` so consumers can drill into the canonical view (run →
    Pipeline tab, publish → Logs/Audit, maintenance → audit row) without
    forcing the activity payload to carry full sub-records.
    """

    ts: str = Field(..., description="ISO-8601 event timestamp (UTC).")
    kind: EventKind = Field(..., description="Event family.")
    actor: str = Field(
        ...,
        description="Originator: 'cli', 'github-actions', 'dashboard', or 'unknown'.",
    )
    subject_id: str = Field(
        ...,
        description="Best-effort stable id (run_id, puzzle_id, source_id, ...).",
    )
    summary: str = Field(..., description="Human one-liner suitable for a feed row.")
    details_ref: dict = Field(
        default_factory=dict,
        description="Pointer to canonical record: {file, run_id, ...}.",
    )


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _read_run_events(runs_dir: Path) -> list[ActivityEvent]:
    """One event per terminal run; status-driven summary."""
    events: list[ActivityEvent] = []
    if not runs_dir.is_dir():
        return events
    for path in runs_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        run_id = data.get("run_id") or path.stem
        status = (data.get("status") or "unknown").lower()
        # Prefer completed_at when present so the row lands at the moment
        # the run actually finished; fall back to started_at for in-flight
        # runs so they still appear in the timeline.
        ts = data.get("completed_at") or data.get("started_at")
        if not ts:
            continue
        failure_count = len(data.get("failures") or [])
        if status == "failed":
            summary = f"run {run_id} failed ({failure_count} failures)"
        elif status == "completed":
            summary = f"run {run_id} completed"
        elif status == "running":
            summary = f"run {run_id} in flight"
        else:
            summary = f"run {run_id} {status}"
        events.append(ActivityEvent(
            ts=ts, kind="run", actor="cli", subject_id=run_id,
            summary=summary,
            details_ref={"file": path.name, "run_id": run_id},
        ))
    return events


def _read_audit_events(audit_file: Path) -> list[ActivityEvent]:
    """One event per audit.jsonl line. Source for cleanup/publish ops."""
    events: list[ActivityEvent] = []
    if not audit_file.is_file():
        return events
    try:
        text = audit_file.read_text(encoding="utf-8")
    except OSError:
        return events
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = row.get("timestamp")
        if not ts:
            continue
        operation = row.get("operation", "?")
        target = row.get("target", "?")
        details = row.get("details") or {}
        # Best-effort subject id; falls back to target so feed rows are
        # never blank.
        subject = (
            details.get("run_id")
            or details.get("source")
            or target
        )
        events.append(ActivityEvent(
            ts=ts, kind="maintenance", actor="cli", subject_id=str(subject),
            summary=f"{operation} → {target}",
            details_ref={"file": audit_file.name, "operation": operation},
        ))
    return events


def _read_publish_events(publish_log_dir: Path) -> list[ActivityEvent]:
    """One event per (date, run_id) — aggregates per-puzzle entries.

    Per-puzzle granularity already lives in ``publish-log search``; here we
    only need to know "run X published N puzzles on day Y" so the operator
    can spot publish bursts in the timeline.
    """
    events: list[ActivityEvent] = []
    if not publish_log_dir.is_dir():
        return events
    for path in sorted(publish_log_dir.glob("*.jsonl")):
        date = path.stem  # YYYY-MM-DD
        per_run: dict[str, dict] = defaultdict(lambda: {"count": 0, "source": None})
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            run_id = row.get("run_id")
            if not run_id:
                continue
            agg = per_run[run_id]
            agg["count"] += 1
            agg["source"] = agg["source"] or row.get("source_id")
        # Anchor at end-of-day so multiple publish events cluster after the
        # run-completion event from the same day.
        ts = f"{date}T23:59:59+00:00"
        for run_id, agg in per_run.items():
            src = agg["source"] or "?"
            events.append(ActivityEvent(
                ts=ts, kind="publish", actor="cli", subject_id=run_id,
                summary=f"published {agg['count']} puzzle(s) from {src}",
                details_ref={"file": path.name, "run_id": run_id, "date": date},
            ))
    return events


def compute_activity(
    *,
    runs_dir: Path,
    audit_file: Path,
    publish_log_dir: Path,
    from_ts: str | None = None,
    to_ts: str | None = None,
    kinds: list[str] | None = None,
    limit: int = 100,
) -> list[ActivityEvent]:
    """Merge all event sources, filter, and return newest-first.

    Args:
        runs_dir: ``.pm-runtime/state/runs/``.
        audit_file: ``yengo-puzzle-collections/.../audit.jsonl``.
        publish_log_dir: ``yengo-puzzle-collections/.../publish-log/``.
        from_ts / to_ts: Inclusive ISO-8601 bounds; either may be None.
        kinds: Allowlist of event kinds; None = all.
        limit: Maximum events to return after filtering.

    Returns:
        Newest-first list of :class:`ActivityEvent`, length ≤ ``limit``.
    """
    if kinds:
        bad = [k for k in kinds if k not in _VALID_KINDS]
        if bad:
            raise ValueError(f"unknown kinds: {bad}; valid: {sorted(_VALID_KINDS)}")
    kinds_set = set(kinds) if kinds else None

    events: list[ActivityEvent] = []
    events.extend(_read_run_events(runs_dir))
    events.extend(_read_audit_events(audit_file))
    events.extend(_read_publish_events(publish_log_dir))

    lo = _parse_ts(from_ts)
    hi = _parse_ts(to_ts)

    def _keep(ev: ActivityEvent) -> bool:
        if kinds_set and ev.kind not in kinds_set:
            return False
        if lo is not None or hi is not None:
            ets = _parse_ts(ev.ts)
            if ets is None:
                return False
            if lo is not None and ets < lo:
                return False
            if hi is not None and ets > hi:
                return False
        return True

    filtered = [e for e in events if _keep(e)]
    filtered.sort(key=lambda e: e.ts, reverse=True)
    return filtered[:limit]
