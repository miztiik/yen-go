"""
audit_capture: forensic check for "missing puzzle" reports.

Given a publicid (and optionally a since-timestamp), classify what
actually happened across three layers of evidence:

  1. SGF file on disk (under external-sources/101weiqi/books/*/sgf/)
     -- if present, the puzzle WAS saved (any FE "Aborted" warning
     was cosmetic).
  2. Receiver server log (under external-sources/101weiqi/logs/
     *.jsonl) -- looks for [CAPTURE-RECV], [SAVED], [CAPTURE-SKIP],
     [CAPTURE-RETRY], [TIMING] lines mentioning the pid.
  3. Per-book capture log (books/{id}/capture-log.jsonl) -- structured
     events: puzzle_skipped, puzzle_retry, puzzle_reroute,
     session_paused, session_summary.

Output is a single classification per pid:
  - SAVED          : SGF on disk + at least one [SAVED] log line.
  - SAVED_NO_LOG   : SGF on disk but no log evidence (old log rotated).
  - LOST_FE        : no SGF, no [CAPTURE-RECV]; userscript never POSTed
                     (FE bug; the case E1/E3 fix targets).
  - LOST_BE        : [CAPTURE-RECV] present but no [SAVED]; receiver
                     received the POST but did not write the file.
  - SKIPPED_GATE   : [CAPTURE-SKIP] for this pid; readiness gate refused.
  - UNKNOWN        : nothing found (wrong pid, or evidence purged).

Usage:
  python -m tools.weiqi101.audit_capture --pid 28566
  python -m tools.weiqi101.audit_capture --pid 28566 --since 2026-05-02T18:00:00Z
  python -m tools.weiqi101.audit_capture --pid 28566 --book-id 42
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from tools.weiqi101.config import get_output_dir


@dataclass
class Evidence:
    pid: int
    sgf_paths: list[Path] = field(default_factory=list)
    receiver_lines: list[str] = field(default_factory=list)
    capture_log_events: list[dict] = field(default_factory=list)

    @property
    def has_capture_recv(self) -> bool:
        return any("[CAPTURE-RECV]" in line for line in self.receiver_lines)

    @property
    def has_saved(self) -> bool:
        return any("[SAVED]" in line for line in self.receiver_lines)

    @property
    def has_capture_skip(self) -> bool:
        return any("[CAPTURE-SKIP]" in line for line in self.receiver_lines)


def _iter_sgfs_for_pid(books_dir: Path, pid: int) -> list[Path]:
    """Return every SGF file whose name ends with `_{pid}.sgf`.

    Naming convention: ch{NN}_{PPP}_{slug}_{pid}.sgf or
    {GGGG}_{slug}_{PPP}_{pid}.sgf -- pid is always the LAST underscore-
    delimited segment before .sgf.
    """
    if not books_dir.exists():
        return []
    suffix = f"_{pid}.sgf"
    return sorted(p for p in books_dir.rglob(f"*{suffix}") if p.is_file())


def _scan_receiver_logs(
    logs_dir: Path,
    pid: int,
    since: datetime | None = None,
) -> list[str]:
    """Return console-formatted lines mentioning the pid in JSONL log files."""
    if not logs_dir.exists():
        return []
    pid_str = str(pid)
    # Pre-compile patterns we care about so we don't false-match a
    # different number that happens to contain the pid digits.
    interesting = re.compile(r"\[(CAPTURE-RECV|SAVED|PROGRESS|CAPTURE-SKIP|CAPTURE-RETRY|TIMING|DIAG)\]")
    pid_field = re.compile(rf"\bpid={pid_str}\b|\bpuzzle_id\s*=\s*{pid_str}\b")
    out: list[str] = []
    for log_file in sorted(logs_dir.glob("*.jsonl")):
        try:
            with log_file.open(encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw or pid_str not in raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg = str(rec.get("message", ""))
                    if not interesting.search(msg) or not pid_field.search(msg):
                        continue
                    if since is not None:
                        ts_raw = rec.get("timestamp") or rec.get("time")
                        if ts_raw and _parse_ts(ts_raw) < since:
                            continue
                    out.append(f"{log_file.name}: {msg}")
        except OSError:
            continue
    return out


def _scan_capture_logs(
    books_dir: Path,
    pid: int,
    book_id: int | None,
    since: datetime | None,
) -> list[dict]:
    """Return capture-log.jsonl events that name the pid."""
    if not books_dir.exists():
        return []
    book_dirs: list[Path]
    if book_id is not None:
        book_dirs = [d for d in books_dir.iterdir() if d.is_dir() and str(book_id) in d.name]
    else:
        book_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
    out: list[dict] = []
    for bd in book_dirs:
        cap_log = bd / "capture-log.jsonl"
        if not cap_log.exists():
            continue
        try:
            with cap_log.open(encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not _record_mentions_pid(rec, pid):
                        continue
                    if since is not None:
                        ts_raw = rec.get("timestamp") or rec.get("captured_at")
                        if ts_raw and _parse_ts(ts_raw) < since:
                            continue
                    rec["_book_dir"] = bd.name
                    out.append(rec)
        except OSError:
            continue
    return out


def _record_mentions_pid(rec: dict, pid: int) -> bool:
    candidates = (
        rec.get("puzzle_id"),
        rec.get("pid"),
        rec.get("expected_pid"),
        (rec.get("detail") or {}).get("pid"),
        (rec.get("detail") or {}).get("expected_pid"),
        (rec.get("detail") or {}).get("puzzle_id"),
    )
    for c in candidates:
        try:
            if c is not None and int(c) == pid:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _parse_ts(raw: str) -> datetime:
    """Best-effort ISO 8601 parse; falls back to epoch on failure."""
    try:
        # Handle trailing Z that fromisoformat doesn't accept on <3.11 stricter forms.
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


def classify(ev: Evidence) -> str:
    if ev.sgf_paths and ev.has_saved:
        return "SAVED"
    if ev.sgf_paths and not ev.has_saved:
        return "SAVED_NO_LOG"
    if ev.has_capture_skip:
        return "SKIPPED_GATE"
    if ev.has_capture_recv and not ev.has_saved:
        return "LOST_BE"
    if not ev.has_capture_recv and not ev.sgf_paths:
        # Nothing in the receiver log AND no SGF.
        if ev.capture_log_events:
            return "LOST_FE"  # at least the FE knew about it
        return "UNKNOWN"
    return "UNKNOWN"


def gather(pid: int, output_dir: Path, since: datetime | None, book_id: int | None) -> Evidence:
    books_dir = output_dir / "books"
    logs_dir = output_dir / "logs"
    return Evidence(
        pid=pid,
        sgf_paths=_iter_sgfs_for_pid(books_dir, pid),
        receiver_lines=_scan_receiver_logs(logs_dir, pid, since=since),
        capture_log_events=_scan_capture_logs(books_dir, pid, book_id=book_id, since=since),
    )


def render(ev: Evidence, verdict: str) -> str:
    lines: list[str] = []
    lines.append(f"pid={ev.pid}  verdict={verdict}")
    lines.append("")
    lines.append(f"SGF files on disk ({len(ev.sgf_paths)}):")
    for p in ev.sgf_paths or ["(none)"]:
        lines.append(f"  {p}")
    lines.append("")
    lines.append(f"Receiver log lines ({len(ev.receiver_lines)}):")
    for line in ev.receiver_lines or ["(none)"]:
        lines.append(f"  {line}")
    lines.append("")
    lines.append(f"capture-log events ({len(ev.capture_log_events)}):")
    for rec in ev.capture_log_events or [{"_": "(none)"}]:
        if rec.get("_") == "(none)":
            lines.append("  (none)")
            continue
        ts = rec.get("timestamp") or rec.get("captured_at") or "?"
        kind = rec.get("event_type") or rec.get("event") or rec.get("kind") or "?"
        bd = rec.get("_book_dir", "?")
        lines.append(f"  [{ts}] {bd}  {kind}  {json.dumps(rec.get('detail') or {}, sort_keys=True)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252, which chokes on the emoji /
    # CJK that surface in receiver log lines. Reconfigure to UTF-8 with
    # a replace-on-error strategy so the audit always prints SOMETHING.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="audit_capture",
        description="Classify a 'missing puzzle' report across SGF / receiver-log / capture-log evidence.",
    )
    parser.add_argument("--pid", type=int, required=True, help="publicid to investigate")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO 8601 timestamp; ignore evidence older than this (e.g. 2026-05-02T18:00:00Z)",
    )
    parser.add_argument(
        "--book-id",
        type=int,
        default=None,
        help="Restrict capture-log scan to this book (faster on large repos)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override 101weiqi output dir (default: external-sources/101weiqi)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human report.",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir or get_output_dir()
    since = _parse_ts(args.since) if args.since else None

    ev = gather(args.pid, output_dir, since=since, book_id=args.book_id)
    verdict = classify(ev)

    if args.json:
        print(json.dumps({
            "pid": ev.pid,
            "verdict": verdict,
            "sgf_paths": [str(p) for p in ev.sgf_paths],
            "receiver_lines": ev.receiver_lines,
            "capture_log_events": ev.capture_log_events,
        }, default=str, indent=2))
    else:
        print(render(ev, verdict))

    return 0 if verdict in ("SAVED", "SAVED_NO_LOG") else 1


if __name__ == "__main__":
    sys.exit(main())
