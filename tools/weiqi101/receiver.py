"""
Local HTTP receiver for browser-captured 101weiqi puzzle data.

Bolt-on module: receives qqdata JSON from a Tampermonkey userscript
running in the user's real browser, processes it through the existing
weiqi101 pipeline (validate → enrich → convert → save), and returns
status to the browser.

This module has ZERO external dependencies beyond stdlib + existing
weiqi101 modules. Remove this file + browser/ dir to fully uninstall.

Usage:
    python -m tools.weiqi101 receive                         # Start on :8101
    python -m tools.weiqi101 receive --port 8102              # Custom port
    python -m tools.weiqi101 receive --book-id 197            # Pre-load book queue
    python -m tools.weiqi101 import-jsonl dump.jsonl          # Offline import
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import signal
import threading
import time
from collections import deque
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from . import _local_collections_mapping, _local_intent_mapping
from . import book_state
from . import coverage as coverage_mod
from .checkpoint import WeiQiCheckpoint, load_checkpoint, save_checkpoint
from .complexity import compute_complexity
from .config import (
    DEFAULT_BATCH_SIZE,
    RECEIVER_HOST,
    RECEIVER_MAX_BODY,
    RECEIVER_PORT,
    get_output_dir,
)
from .index import add_book_to_index, load_puzzle_ids, sort_index
from .pid_extract import pid_from_filename
from .models import PuzzleData
from .converter import convert_puzzle_to_sgf
from .storage import parse_qday_url, save_puzzle, save_puzzle_qday

from tools.core.logging import EventType, StructuredLogger
from tools.core.paths import rel_path
from .validator import validate_puzzle

logger = logging.getLogger("101weiqi.receiver")

# Lazy module-level translator for CJK→English fallback when the userscript
# (or browser translation extension) fails to provide a romanised label.
#
# The actual implementation lives in tools.weiqi101.services.labels — these
# names are re-exported here for backwards compatibility with existing
# imports (`from tools.weiqi101.receiver import resolve_label`, etc.).
from tools.weiqi101.services.labels import (  # noqa: E402
    has_cjk as _has_cjk,
    get_translator as _get_translator,
    slugify_ascii as _slugify_ascii,
    resolve_label,
)



# ---------------------------------------------------------------------------
# Identity helpers — see /memories/repo/weiqi101-browser-capture.md
# ---------------------------------------------------------------------------

def _compute_content_hash(puzzle: PuzzleData) -> str:
    """Stable per-puzzle identity from canonical board + solution tree.

    Recorded in capture-log.jsonl as ``content_hash`` for cross-session
    drift analysis. NOT YET used for dedup — pid is still authoritative
    for now (see Option A discussion in chat history). When/if we flip,
    this is the key.

    Hash inputs (in order):
      - sorted black stones (deterministic regardless of ingest order)
      - sorted white stones
      - first_hand (1=B, 2=W) — same board, opposite color = different puzzle
      - canonical solution tree (sorted by node_id; coord+correct+failure+children)
    """
    nodes = []
    for nid in sorted(puzzle.solution_nodes.keys()):
        n = puzzle.solution_nodes[nid]
        nodes.append([
            nid, n.coordinate, int(bool(n.is_correct)),
            int(bool(n.is_failure)), sorted(n.children or []),
        ])
    payload = {
        "b": sorted(puzzle.black_stones),
        "w": sorted(puzzle.white_stones),
        "fh": int(puzzle.first_hand),
        "sn": nodes,
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _extract_url_pid(url: str | None) -> int | None:
    """Pull the pid from a 101weiqi URL (`/q/{pid}/` or `/book/{b}/{c}/{pid}/`)."""
    if not url:
        return None
    m = re.search(r"/q/(\d+)/?", url) or re.search(r"/book/\d+/\d+/(\d+)/?", url)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Core pipeline: qqdata dict → saved SGF
# ---------------------------------------------------------------------------

def process_qqdata(
    qqdata: dict[str, Any],
    output_dir: Path,
    known_ids: set[int],
    checkpoint: WeiQiCheckpoint,
    batch_size: int = DEFAULT_BATCH_SIZE,
    *,
    match_collections: bool = True,
    resolve_intent: bool = True,
    url: str | None = None,
    page_books: list[dict] | None = None,
    book_dir: Path | None = None,
) -> dict[str, Any]:
    """Process a single qqdata payload through the full pipeline.

    This is the same logic as orchestrator._process_html minus the HTML
    extraction step (the browser already extracted qqdata for us).

    If the URL is a /qday/ URL, the puzzle is saved under qday/YYYY/MM/DD-N.sgf
    instead of the normal batch directory.

    Returns:
        Dict with keys: status ("ok"|"skipped"|"error"), puzzle_id, message.
        Error responses also include ``permanent: bool`` — True when the
        failure won't resolve on retry (validation rejection on parsed
        qqdata), False for transient failures (parse/save errors).
        Clients (e.g. browser userscript) use this to decide whether to
        skip the pid in future walks vs leave it retryable.
    """
    # Parse
    try:
        puzzle = PuzzleData.from_qqdata(qqdata)
    except Exception as e:
        return {
            "status": "error", "puzzle_id": None,
            "message": f"parse: {e}", "permanent": False,
        }

    # Dedup
    if puzzle.puzzle_id in known_ids:
        return {"status": "skipped", "puzzle_id": puzzle.puzzle_id, "message": "duplicate"}

    # Validate
    error = validate_puzzle(puzzle)
    if error:
        return {
            "status": "error", "puzzle_id": puzzle.puzzle_id,
            "message": f"validation: {error}", "permanent": True,
        }

    # Enrichment: complexity (YX)
    cx = compute_complexity(puzzle.solution_nodes)
    yx_string = cx.to_yx_string() if cx.total_nodes > 0 else None

    # Enrichment: intent (root C[])
    root_comment: str | None = None
    if resolve_intent:
        root_comment = _local_intent_mapping.resolve_intent(
            puzzle.type_name, puzzle.player_to_move,
        )

    # Enrichment: collection (YL[] — books only)
    # Only actual book membership goes into YL. Category-based slugs
    # (life-and-death, tesuji-problems) and hardcoded entries
    # (101weiqi-daily) are NOT added — YL is strictly book membership.
    collection_entries: list[str] | None = None

    # Book membership from qqdata.bookinfos (usually empty)
    collection_entries = _local_collections_mapping.enrich_collections_from_bookinfos(
        collection_entries, puzzle.bookinfos,
    )

    # Book membership from DOM-scraped page_books (primary source)
    if page_books:
        collection_entries = _local_collections_mapping.enrich_collections_from_bookinfos(
            collection_entries, page_books,
        )

    # Detect qday URL for special storage routing
    qday_info = parse_qday_url(url)

    # Save
    try:
        if book_dir:
            # Book capture: save directly to book dir, skip batch entirely.
            # The caller (_save_to_book_dir) handles writing the file.
            sgf_content = convert_puzzle_to_sgf(
                puzzle,
                root_comment=root_comment,
                collection_entries=collection_entries,
                yx_string=yx_string,
            )
            known_ids.add(puzzle.puzzle_id)
            return {
                "status": "ok",
                "puzzle_id": puzzle.puzzle_id,
                "message": "",
                "_sgf_content": sgf_content,
                # Identity fields for capture-log enrichment (see memory note
                # "Capture-log v2 schema"). All four are recorded; pid is
                # still the active dedup key.
                "_identity": {
                    "qqdata_publicid": qqdata.get("publicid"),
                    "qqdata_id": qqdata.get("id"),
                    "url_pid": _extract_url_pid(url),
                    "content_hash": _compute_content_hash(puzzle),
                },
                "meta": {
                    "level": puzzle.level_name,
                    "type": puzzle.type_name,
                    "vote": puzzle.vote_score,
                    "ok": puzzle.correct_count,
                    "wrong": puzzle.wrong_count,
                    "hasbook": puzzle.hasbook,
                    "stones": len(puzzle.black_stones) + len(puzzle.white_stones),
                    "page_books": page_books or [],
                },
            }
        elif qday_info:
            year, month, day, number = qday_info

            file_path = save_puzzle_qday(
                puzzle=puzzle,
                output_dir=output_dir,
                year=year,
                month=month,
                day=day,
                number=number,
                root_comment=root_comment,
                collection_entries=collection_entries,
                yx_string=yx_string,
            )
        else:
            file_path, _batch_num = save_puzzle(
                puzzle=puzzle,
                output_dir=output_dir,
                batch_size=batch_size,
                checkpoint=checkpoint,
                root_comment=root_comment,
                collection_entries=collection_entries,
                yx_string=yx_string,
            )
            checkpoint.record_success(batch_size)

        known_ids.add(puzzle.puzzle_id)
        save_checkpoint(checkpoint, output_dir)

        return {
            "status": "ok",
            "puzzle_id": puzzle.puzzle_id,
            "message": rel_path(file_path),
            "meta": {
                "level": puzzle.level_name,
                "type": puzzle.type_name,
                "vote": puzzle.vote_score,
                "ok": puzzle.correct_count,
                "wrong": puzzle.wrong_count,
                "hasbook": puzzle.hasbook,
                "stones": len(puzzle.black_stones) + len(puzzle.white_stones),
                "page_books": page_books or [],
            },
        }
    except Exception as e:
        return {
            "status": "error", "puzzle_id": puzzle.puzzle_id,
            "message": f"save: {e}", "permanent": False,
        }


# ---------------------------------------------------------------------------
# Book state reconciliation — sync book.json with disk reality
# ---------------------------------------------------------------------------
#
# Per-book state lives in a single ``book.json`` (schema v4) — see
# ``tools.weiqi101.book_state``. The previous trio of ``manifest.json``,
# ``book-index.json``, and ``discovery_checkpoint.json`` was retired
# 2026-04-24; this module never reads or writes those files anymore.

def _book_state_recount(state_data: dict[str, Any]) -> None:
    """Recompute stats + per-chapter counters from current positions."""
    positions = state_data.get("positions") or []
    pid_status = {p["pid"]: p["status"] for p in positions if "pid" in p}
    captured = sum(1 for s in pid_status.values() if s == "captured")
    external = sum(1 for s in pid_status.values() if s == "external")
    pending = sum(1 for s in pid_status.values() if s == "pending")
    last_captured_pos = 0
    for p in positions:
        if p.get("status") == "captured":
            last_captured_pos = max(last_captured_pos, int(p.get("pos", 0) or 0))

    chapters = state_data.get("chapters") or []
    all_ch_pids: set[int] = set()
    for ch in chapters:
        ch_num = ch.get("chapter_number", 0)
        ch_pids = [
            p["pid"] for p in positions
            if p.get("chapter_number") == ch_num
            and p.get("chapter_position", 0) > 0
        ]
        all_ch_pids.update(ch_pids)
        ch["total"] = len(ch.get("puzzle_ids", []) or []) or len(ch_pids)
        ch["captured"] = sum(
            1 for pid in ch_pids if pid_status.get(pid) == "captured"
        )
        ch["external"] = sum(
            1 for pid in ch_pids if pid_status.get(pid) == "external"
        )
        ch["pending"] = sum(
            1 for pid in ch_pids if pid_status.get(pid) == "pending"
        )

    stats = state_data.setdefault("stats", {})
    stats["total_positions"] = len(positions)
    stats["captured"] = captured
    stats["external"] = external
    stats["pending"] = pending
    stats["last_captured_position"] = last_captured_pos
    stats["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats["puzzle_counts"] = {
        "chapter_total": sum(
            len(ch.get("puzzle_ids", []) or []) for ch in chapters
        ),
        "chapter_unique": len(all_ch_pids),
        "chapters": len(chapters),
    }


def reconcile_book_index(
    book_dir: Path, *, dry_run: bool = False,
) -> dict[str, Any]:
    """Reconcile ``book.json`` positions with actual SGF files on disk.

    Pid-keyed (schema v5 invariant). For each SGF in ``sgf/``:
    - Extract pid from filename (last underscore-delimited token).
    - Find the matching entry in ``positions[]`` by pid.
    - If found, mark captured and set the filename.
    - If not found, the file is an orphan (no manifest entry).

    Also collapses any duplicate-pid entries that may have been created
    by the pre-v5 pos-first matcher race.

    Idempotent: safe to run multiple times.
    """
    # Hold the per-book lock for the whole RMW so a concurrent capture
    # or manifest POST can't interleave its own load → save against ours.
    with book_state.book_lock(book_dir):
        return _reconcile_book_index_locked(book_dir, dry_run=dry_run)


def _reconcile_book_index_locked(
    book_dir: Path, *, dry_run: bool = False,
) -> dict[str, Any]:
    state_data = book_state.load(book_dir)
    if not state_data:
        return {"error": f"No book.json in {book_dir.name}"}

    # Pre-dedupe so subsequent pid lookups are unambiguous.
    duplicates_removed = book_state.dedupe_positions(state_data)

    positions = state_data.get("positions") or []
    if not positions:
        return {"error": f"Empty positions in {book_dir.name}"}

    pid_map: dict[int, dict[str, Any]] = {}
    for entry in positions:
        pid = entry.get("pid")
        if isinstance(pid, int):
            pid_map[pid] = entry

    sgf_dir = book_dir / "sgf"
    if not sgf_dir.exists():
        return {"error": f"No sgf/ directory in {book_dir.name}"}

    # disk_files items: (pid, filename). Filename schemas (book mode):
    #   ch{NN}_{pos}_{slug}_{pid}.sgf  (chapter mode)
    #   {pos}_{slug}_{pid}.sgf         (legacy pos mode)
    # Pid extraction is delegated to pid_from_filename so all callers
    # share one canonical rule.
    disk_files: list[tuple[int, str]] = []
    for f in sorted(sgf_dir.iterdir()):
        if f.suffix != ".sgf":
            continue
        pid = pid_from_filename(f.name)
        if pid is None:
            continue
        disk_files.append((pid, f.name))

    newly_captured = 0
    already_correct = 0
    orphan_files: list[str] = []

    for pid, filename in disk_files:
        entry = pid_map.get(pid)
        if entry is None:
            orphan_files.append(filename)
            continue
        if entry.get("status") == "captured":
            already_correct += 1
            if entry.get("file") != filename:
                entry["file"] = filename
            continue
        newly_captured += 1
        entry["status"] = "captured"
        entry["file"] = filename
        entry.pop("ref", None)

    _book_state_recount(state_data)
    summary = {
        "book_dir": book_dir.name,
        "total_positions": len(state_data.get("positions") or []),
        "disk_files": len(disk_files),
        "newly_captured": newly_captured,
        "updated_pids": 0,  # legacy field — pid-keyed reconcile never rewrites pids
        "already_correct": already_correct,
        "orphan_files": len(orphan_files),
        "duplicates_removed": duplicates_removed,
        "final_captured": state_data["stats"]["captured"],
        "final_external": state_data["stats"]["external"],
        "final_pending": state_data["stats"]["pending"],
    }
    if not dry_run:
        book_state.save(book_dir, state_data)

    return summary


# ---------------------------------------------------------------------------
# Telemetry — detailed per-event tracking with timestamps
# ---------------------------------------------------------------------------

class _TelemetryEvent:
    """A single telemetry event."""

    __slots__ = ("ts", "ts_epoch", "puzzle_id", "status", "message", "duration_ms", "url")

    def __init__(
        self,
        puzzle_id: int | None,
        status: str,
        message: str,
        duration_ms: float,
        url: str | None = None,
    ):
        now = datetime.now(UTC)
        self.ts = now.isoformat()
        # Epoch seconds for cheap rolling-window arithmetic. Kept
        # alongside the ISO string (which is what JSON consumers see)
        # so the deque stays the single source of truth.
        self.ts_epoch = now.timestamp()
        self.puzzle_id = puzzle_id
        self.status = status
        self.message = message
        self.duration_ms = round(duration_ms, 1)
        self.url = url

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "ts": self.ts,
            "puzzle_id": self.puzzle_id,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }
        if self.url:
            d["url"] = self.url
        return d


class Telemetry:
    """Thread-safe telemetry collector with summary statistics.

    Tracks every capture event with timestamp, duration, status, and
    error details.  Provides summary stats and a recent-event window
    for the /telemetry endpoint.
    """

    MAX_RECENT = 200  # keep last N events in memory

    def __init__(self, slog: StructuredLogger | None = None) -> None:
        self._lock = threading.Lock()
        self._slog = slog
        self._events: deque[_TelemetryEvent] = deque(maxlen=self.MAX_RECENT)
        self._counts: dict[str, int] = {"ok": 0, "skipped": 0, "error": 0}
        self._total_duration_ms: float = 0.0
        self._started_at: str = datetime.now(UTC).isoformat()
        self._error_details: deque[dict] = deque(maxlen=50)  # last 50 errors
        self._last_ok_at: str | None = None
        self._last_error_at: str | None = None
        self._book_id: int | None = None
        self._book_name: str | None = None

    @staticmethod
    def _format_meta_str(meta: dict[str, Any] | None) -> str:
        """Format metadata dict as a human-readable suffix string.

        Produces the same format previously inlined in the ok branch,
        e.g. `` level=13K+ type=life-and-death vote=3 ... books=[197:Cho Chikun 101]``
        """
        if not meta:
            return ""
        parts = (
            f" level={meta.get('level', '')} type={meta.get('type', '')}"
            f" vote={meta.get('vote', 0)} ok={meta.get('ok', 0)}"
            f" wrong={meta.get('wrong', 0)}"
            f" hasbook={meta.get('hasbook', False)}"
            f" stones={meta.get('stones', 0)}"
        )
        page_books = meta.get("page_books", [])
        if page_books:
            book_summary = ",".join(
                f"{b.get('book_id', '?')}:{b.get('name', '')[:20]}"
                for b in page_books
            )
            parts += f" books=[{book_summary}]"
        return parts

    @staticmethod
    def _sanitize_meta_for_slog(meta: dict[str, Any] | None) -> dict[str, Any]:
        """Rename metadata keys that would collide with logger method params."""
        if not meta:
            return {}

        safe_meta = dict(meta)

        # StructuredLogger.event(level=...) expects a numeric log level.
        # Puzzle metadata also uses "level" for rank labels like "13K+".
        # Passing this through as-is can crash request handling.
        if "level" in safe_meta:
            safe_meta["puzzle_level"] = safe_meta.pop("level")

        return safe_meta

    @staticmethod
    def _format_ctx_str(meta: dict[str, Any] | None) -> str:
        """Format ctx_* book/chapter/section keys as a human-readable suffix."""
        if not meta:
            return ""
        parts: list[str] = []
        bid = meta.get("ctx_book_id")
        bname = meta.get("ctx_book_name")
        if bid:
            label = f"book={bid}"
            if bname:
                label += f" '{bname}'"
            parts.append(label)
        ch_num = meta.get("ctx_chapter_number")
        ch_name = meta.get("ctx_chapter_name")
        if ch_num:
            label = f"ch{ch_num}"
            if ch_name:
                label += f" '{ch_name}'"
            parts.append(label)
        sec_id = meta.get("ctx_section_id")
        sec_name = meta.get("ctx_section_name")
        if sec_id:
            label = f"sec={sec_id}"
            if sec_name:
                label += f" '{sec_name}'"
            parts.append(label)
        ch_pos = meta.get("ctx_chapter_position")
        if ch_pos:
            parts.append(f"ch_pos={ch_pos}")
        sec_pos = meta.get("ctx_section_position")
        if sec_pos:
            parts.append(f"sec_pos={sec_pos}")
        gpos = meta.get("ctx_global_position")
        if gpos:
            parts.append(f"gpos={gpos}")
        # `existing=<book>/<file>` shows where a duplicate pid is
        # already stored on disk — answers "is the SKIP legitimate?"
        # without the operator having to grep the filesystem.
        existing = meta.get("ctx_existing")
        if existing:
            parts.append(f"existing={existing}")
        return (" " + " ".join(parts)) if parts else ""

    def record(
        self,
        puzzle_id: int | None,
        status: str,
        message: str,
        duration_ms: float,
        url: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        event = _TelemetryEvent(puzzle_id, status, message, duration_ms, url)
        with self._lock:
            self._events.append(event)
            self._counts[status] = self._counts.get(status, 0) + 1
            self._total_duration_ms += duration_ms
            if status == "ok":
                self._last_ok_at = event.ts
            elif status == "error":
                self._last_error_at = event.ts
                self._error_details.append({
                    "ts": event.ts,
                    "puzzle_id": puzzle_id,
                    "message": message,
                })

        # Persistent audit trail — human-readable message (backward
        # compatible with backfill.py regex) + structured event data
        # for future consumers.
        total = self._counts["ok"] + self._counts["skipped"] + self._counts["error"]

        # Telemetry lines are forensic detail only — demoted to DEBUG
        # so the operator-facing console shows the verb-prefixed
        # [SAVED]/[CAPTURE-SKIP]/[CAPTURE-RECV] lines instead. JSONL
        # event log is unaffected (event_data is still recorded for
        # post-mortem analysis via /telemetry endpoint).
        if status == "ok":
            meta_str = self._format_meta_str(meta)
            safe_meta = self._sanitize_meta_for_slog(meta)
            human_msg = (
                f"[TELEM] event={total} OK puzzle={puzzle_id} "
                f"duration={duration_ms:.0f}ms path={message}{meta_str}"
            )
            if self._slog:
                self._slog.event(
                    EventType.ITEM_SAVE,
                    human_msg,
                    level=logging.DEBUG,
                    puzzle_id=puzzle_id,
                    duration_ms=round(duration_ms, 1),
                    path=message,
                    **safe_meta,
                )
            else:
                logger.debug(human_msg)
        elif status == "skipped":
            ctx_str = self._format_ctx_str(meta)
            human_msg = (
                f"[TELEM] event={total} SKIP puzzle={puzzle_id} "
                f"reason={message} duration={duration_ms:.0f}ms{ctx_str}"
            )
            if self._slog:
                safe_meta = self._sanitize_meta_for_slog(meta)
                self._slog.event(
                    EventType.ITEM_SKIP,
                    human_msg,
                    level=logging.DEBUG,
                    puzzle_id=puzzle_id,
                    reason=message,
                    duration_ms=round(duration_ms, 1),
                    url=url,
                    **safe_meta,
                )
            else:
                logger.debug(human_msg)
        else:
            human_msg = (
                f"[TELEM] event={total} ERROR puzzle={puzzle_id} "
                f"error={message} duration={duration_ms:.0f}ms"
            )
            # Errors stay at WARNING — they're real signal, not noise.
            if self._slog:
                self._slog.event(
                    EventType.ITEM_ERROR,
                    human_msg,
                    level=logging.WARNING,
                    puzzle_id=puzzle_id,
                    error=message,
                    duration_ms=round(duration_ms, 1),
                )
            else:
                logger.warning(human_msg)

    def set_book(self, book_id: int | None, book_name: str | None) -> None:
        with self._lock:
            self._book_id = book_id
            self._book_name = book_name

    # Rolling-window throughput windows (seconds). 5 min answers "is it
    # stuck right now?"; 15 min smooths over CAPTCHA pauses, chapter
    # transitions, and the every-35-puzzle session breaks.
    ROLLING_WINDOWS_S: tuple[int, ...] = (300, 900)

    def rolling_rate(
        self,
        window_s: int,
        status: str = "ok",
        now_epoch: float | None = None,
    ) -> tuple[int, float]:
        """Return ``(count, per_minute)`` for events of ``status`` within the
        last ``window_s`` seconds.

        Reads the existing ``_events`` deque — no extra state. Bounded
        by ``MAX_RECENT``: at saturation the count is a lower bound, so
        the rate is conservative (never overstates throughput).
        """
        if now_epoch is None:
            now_epoch = time.time()
        cutoff = now_epoch - window_s
        with self._lock:
            count = sum(
                1 for e in self._events
                if e.status == status and e.ts_epoch >= cutoff
            )
        per_min = (count * 60.0 / window_s) if window_s > 0 else 0.0
        return count, round(per_min, 2)

    def rolling_rates(
        self, now_epoch: float | None = None
    ) -> dict[str, dict[str, float | int]]:
        """Return ``{"5m": {"count": N, "per_min": X}, "15m": {...}}``."""
        if now_epoch is None:
            now_epoch = time.time()
        out: dict[str, dict[str, float | int]] = {}
        for window_s in self.ROLLING_WINDOWS_S:
            count, per_min = self.rolling_rate(window_s, now_epoch=now_epoch)
            label = f"{window_s // 60}m"
            out[label] = {"count": count, "per_min": per_min}
        return out

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = sum(self._counts.values())
            avg_ms = (self._total_duration_ms / total) if total > 0 else 0
            events_snapshot = [e.to_dict() for e in self._events]
            errors_snapshot = list(self._error_details)
            counts_snapshot = dict(self._counts)
            book_id = self._book_id
            book_name = self._book_name
            started_at = self._started_at
            last_ok = self._last_ok_at
            last_err = self._last_error_at
        # Compute rates outside the lock — rolling_rate takes its own.
        rates = self.rolling_rates()
        return {
            "started_at": started_at,
            "book_id": book_id,
            "book_name": book_name,
            "counts": counts_snapshot,
            "total_processed": total,
            "avg_duration_ms": round(avg_ms, 1),
            "last_ok_at": last_ok,
            "last_error_at": last_err,
            "ok_per_min_5m": rates["5m"]["per_min"],
            "ok_per_min_15m": rates["15m"]["per_min"],
            "window_ok_count_5m": rates["5m"]["count"],
            "window_ok_count_15m": rates["15m"]["count"],
            "recent_errors": errors_snapshot,
            "recent_events": events_snapshot,
        }


# ---------------------------------------------------------------------------
# Puzzle Queue — server-driven navigation for book downloads
# ---------------------------------------------------------------------------

class PuzzleQueue:
    """Thread-safe ordered puzzle ID queue with progress tracking.

    Supports two modes:
    - Book mode (Option A): Load IDs from book-ids.jsonl via /queue/book
    - Manual mode (Option B): Load arbitrary IDs via /queue/ids
    """

    def __init__(self, known_ids: set[int] | None = None) -> None:
        self._lock = threading.Lock()
        self._ids: list[int] = []
        self._pending: deque[int] = deque()
        self._visited: set[int] = set()
        self._skipped_known: set[int] = set()      # already downloaded before queue load
        self._book_id: int | None = None
        self._book_name: str | None = None
        self._source: str | None = None             # "book" or "manual"
        self._loaded_at: str | None = None
        self._active = False

    def load_book(
        self,
        book_id: int,
        output_dir: Path,
        known_ids: set[int],
    ) -> dict[str, Any]:
        """Load puzzle IDs for a book from book-ids.jsonl.

        Filters out IDs already in known_ids (already downloaded).
        Returns summary dict for the response.
        """
        jsonl_path = output_dir / "book-ids.jsonl"
        if not jsonl_path.exists():
            return {"error": f"book-ids.jsonl not found at {output_dir}"}

        # Find the book entry
        book_entry = None
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if int(entry.get("book_id", -1)) == book_id:
                    book_entry = entry
                    break

        if book_entry is None:
            return {"error": f"Book {book_id} not found in book-ids.jsonl"}

        # Extract IDs — support both flat and chapter formats
        all_ids: list[int] = []
        chapters = book_entry.get("chapters")
        if chapters:
            for ch in chapters:
                all_ids.extend(ch.get("puzzle_ids", []))
        else:
            all_ids = book_entry.get("puzzle_ids", [])

        if not all_ids:
            return {"error": f"Book {book_id} has no puzzle IDs"}

        book_name = book_entry.get("book_name_en") or book_entry.get("book_name", "")
        skipped_known = {pid for pid in all_ids if pid in known_ids}
        pending = [pid for pid in all_ids if pid not in known_ids]

        with self._lock:
            self._ids = all_ids
            self._pending = deque(pending)
            self._visited = set()
            self._skipped_known = skipped_known
            self._book_id = book_id
            self._book_name = book_name
            self._source = "book"
            self._loaded_at = datetime.now(UTC).isoformat()
            self._active = True

        logger.info(
            f"[QUEUE] Loaded book {book_id} '{book_name}': "
            f"{len(all_ids)} total, {len(pending)} pending, "
            f"{len(skipped_known)} already downloaded"
        )

        return {
            "status": "ok",
            "book_id": book_id,
            "book_name": book_name,
            "total_ids": len(all_ids),
            "pending": len(pending),
            "already_downloaded": len(skipped_known),
        }

    def load_ids(self, ids: list[int], known_ids: set[int], label: str = "manual") -> dict[str, Any]:
        """Load arbitrary puzzle IDs into the queue.

        Returns summary dict for the response.
        """
        if not ids:
            return {"error": "Empty ID list"}

        skipped_known = {pid for pid in ids if pid in known_ids}
        pending = [pid for pid in ids if pid not in known_ids]

        with self._lock:
            self._ids = ids
            self._pending = deque(pending)
            self._visited = set()
            self._skipped_known = skipped_known
            self._book_id = None
            self._book_name = None
            self._source = label
            self._loaded_at = datetime.now(UTC).isoformat()
            self._active = True

        logger.info(
            f"[QUEUE] Loaded {len(ids)} IDs (source={label}): "
            f"{len(pending)} pending, {len(skipped_known)} already downloaded"
        )

        return {
            "status": "ok",
            "source": label,
            "total_ids": len(ids),
            "pending": len(pending),
            "already_downloaded": len(skipped_known),
        }

    def next_url(self) -> dict[str, Any]:
        """Pop the next puzzle ID from the queue.

        Returns dict with url+puzzle_id, or done/inactive status.
        """
        with self._lock:
            if not self._active:
                return {"status": "inactive", "message": "No queue loaded"}
            if not self._pending:
                return {
                    "status": "done",
                    "message": "Queue complete",
                    "total": len(self._ids),
                    "visited": len(self._visited),
                    "skipped_known": len(self._skipped_known),
                }
            pid = self._pending.popleft()
            self._visited.add(pid)
            remaining = len(self._pending)

        logger.debug(f"[QUEUE] Next: puzzle {pid} ({remaining} remaining)")

        return {
            "status": "ok",
            "puzzle_id": pid,
            "url": f"https://www.101weiqi.com/q/{pid}/",
            "remaining": remaining,
            "visited": len(self._visited),
            "total": len(self._ids),
        }

    def mark_done(self, puzzle_id: int) -> None:
        """Mark a puzzle ID as visited (called after capture). Informational only.

        No-op if the puzzle was never part of this queue's loaded id set.
        This matters now that the receiver maintains a dict of queues
        keyed by book_id (multi-book mode): /capture iterates every
        queue and calls mark_done, but only the queue that actually
        owns the puzzle should have its `visited` set grow.
        """
        with self._lock:
            if puzzle_id in self._visited:
                return
            if self._ids and puzzle_id not in self._ids:
                return
            self._visited.add(puzzle_id)

    def stop(self) -> dict[str, Any]:
        """Deactivate the queue."""
        with self._lock:
            self._active = False
            return {
                "status": "stopped",
                "visited": len(self._visited),
                "remaining": len(self._pending),
            }

    def status(self) -> dict[str, Any]:
        """Return current queue state."""
        with self._lock:
            return {
                "active": self._active,
                "source": self._source,
                "book_id": self._book_id,
                "book_name": self._book_name,
                "loaded_at": self._loaded_at,
                "total_ids": len(self._ids),
                "pending": len(self._pending),
                "visited": len(self._visited),
                "already_downloaded": len(self._skipped_known),
                "progress_pct": round(
                    len(self._visited) / len(self._ids) * 100, 1
                ) if self._ids else 0,
            }


# ---------------------------------------------------------------------------
# JSONL import (offline / batch mode)
# ---------------------------------------------------------------------------

def import_jsonl(
    jsonl_path: Path,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    *,
    match_collections: bool = True,
    resolve_intent: bool = True,
) -> dict[str, int]:
    """Import captured puzzle data from a JSONL file.

    Each line must be a JSON object with at least a "qqdata" key.

    Returns:
        Dict with counts: ok, skipped, error
    """
    known_ids = load_puzzle_ids(output_dir)
    checkpoint = load_checkpoint(output_dir) or WeiQiCheckpoint(source_mode="browser-capture")
    counts = {"ok": 0, "skipped": 0, "error": 0}

    with open(jsonl_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: invalid JSON: {e}")
                counts["error"] += 1
                continue

            qqdata = record.get("qqdata") or record
            result = process_qqdata(
                qqdata=qqdata,
                output_dir=output_dir,
                known_ids=known_ids,
                checkpoint=checkpoint,
                batch_size=batch_size,
                match_collections=match_collections,
                resolve_intent=resolve_intent,
            )
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1

            pid = result.get("puzzle_id", "?")
            if status == "ok":
                logger.info(f"Line {line_num}: OK puzzle {pid} → {result['message']}")
            elif status == "skipped":
                logger.debug(f"Line {line_num}: SKIP puzzle {pid}")
            else:
                logger.warning(f"Line {line_num}: ERROR puzzle {pid}: {result['message']}")

    sort_index(output_dir)
    save_checkpoint(checkpoint, output_dir)
    return counts


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class _ReceiverState:
    """Shared mutable state for the HTTP handler."""

    def __init__(
        self,
        output_dir: Path,
        batch_size: int,
        *,
        match_collections: bool = True,
        resolve_intent: bool = True,
    ):
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.match_collections = match_collections
        self.resolve_intent = resolve_intent
        self.known_ids = load_puzzle_ids(output_dir)
        self.checkpoint = load_checkpoint(output_dir) or WeiQiCheckpoint(
            source_mode="browser-capture",
        )
        self.lock = threading.Lock()
        self.stats = {"ok": 0, "skipped": 0, "error": 0}
        self._slog = StructuredLogger(logging.getLogger("101weiqi.receiver"))
        self.telemetry = Telemetry(slog=self._slog)
        # Multi-book queue support (v5.40.0): one PuzzleQueue per
        # book_id key. The string "default" is the legacy single-book
        # bucket used when callers don't pass an explicit book_id
        # (existing CLI / single-tab userscript flows continue to work
        # unchanged). New callers that pass ?book_id=... or include
        # `book_id` in the POST body get their own isolated queue, so
        # two browser profiles can drive two different books in
        # parallel against the same receiver.
        self.default_queue_key = "default"
        self.queues: dict[str, PuzzleQueue] = {}

    @property
    def queue(self) -> "PuzzleQueue":
        """Legacy alias for the default queue (lazy-created).

        Preserved so existing callers (`state.queue.mark_done(...)`,
        CLI shutdown summary, pre-load on startup) keep working.
        New code should call `_resolve_queue(book_id)` instead.
        """
        q = self.queues.get(self.default_queue_key)
        if q is None:
            q = PuzzleQueue()
            self.queues[self.default_queue_key] = q
        return q

    def _resolve_queue(self, book_id: int | str | None) -> "PuzzleQueue":
        """Return (or lazily create) the queue for ``book_id``.

        ``None`` / empty falls back to the legacy default queue so old
        clients keep operating on a single shared bucket.
        """
        key = self.default_queue_key if book_id in (None, "", 0) else str(book_id)
        q = self.queues.get(key)
        if q is None:
            q = PuzzleQueue()
            self.queues[key] = q
        return q

    def all_queue_statuses(self) -> dict[str, dict[str, Any]]:
        """Snapshot of every active (or previously loaded) queue."""
        return {key: q.status() for key, q in self.queues.items()}

    def _lookup_pid_location(
        self, puzzle_id: int, *, prefer_book_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Find where ``puzzle_id`` is already stored on disk.

        Scans ``books/*/book.json`` for a position with matching pid and
        ``status in {captured, external}``. Returns the first hit as
        ``{"book_dir": str, "pos": int, "file": str | None}`` or None.

        Used to enrich duplicate-SKIP telemetry so each line self-documents
        the existing copy without the operator having to grep the disk.
        ``prefer_book_id`` makes the active book win when the same pid
        appears in multiple books.
        """
        books_dir = self.output_dir / "books"
        if not books_dir.is_dir():
            return None

        prefer_dir: Path | None = None
        if prefer_book_id is not None:
            prefer_dir = book_state.find_book_dir(books_dir, prefer_book_id)

        candidates: list[Path] = []
        if prefer_dir is not None:
            candidates.append(prefer_dir / book_state.BOOK_STATE_FILENAME)
        for p in books_dir.glob("*/book.json"):
            if prefer_dir is None or p.parent != prefer_dir:
                candidates.append(p)

        for state_path in candidates:
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for pos in data.get("positions") or []:
                if (
                    pos.get("pid") == puzzle_id
                    and pos.get("status") in ("captured", "external")
                ):
                    return {
                        "book_dir": state_path.parent.name,
                        "pos": pos.get("pos"),
                        "file": pos.get("file"),
                    }
        return None

    def process(
        self, qqdata: dict, url: str | None = None,
        page_books: list[dict] | None = None,
        book_dir: Path | None = None,
        book_ctx: dict[str, Any] | None = None,
    ) -> dict:
        t0 = time.monotonic()
        t_lock_acquired = None
        t_processed = None
        with self.lock:
            t_lock_acquired = time.monotonic()
            result = process_qqdata(
                qqdata=qqdata,
                output_dir=self.output_dir,
                known_ids=self.known_ids,
                checkpoint=self.checkpoint,
                batch_size=self.batch_size,
                match_collections=self.match_collections,
                resolve_intent=self.resolve_intent,
                url=url,
                page_books=page_books,
                book_dir=book_dir,
            )
            t_processed = time.monotonic()
            status = result["status"]
            self.stats[status] = self.stats.get(status, 0) + 1
        result["_timings"] = {
            "process_enter": t0,
            "lock_acquired": t_lock_acquired,
            "process_done": t_processed,
        }
        duration_ms = (time.monotonic() - t0) * 1000
        # Merge book_ctx into meta so SKIP/ERROR/OK telemetry lines all
        # show book/chapter/section/position diagnostics. The key collisions
        # are namespaced (book_id, book_name, chapter_*, section_*,
        # global_position) so they can't clash with puzzle meta keys.
        meta = dict(result.get("meta") or {})
        if book_ctx:
            for key in (
                "book_id", "book_name",
                "chapter_number", "chapter_name", "chapter_position",
                "section_id", "section_name", "section_position",
                "global_position",
            ):
                if key in book_ctx and book_ctx[key] not in (None, "", 0):
                    meta[f"ctx_{key}"] = book_ctx[key]

        # On a duplicate SKIP, look up where the existing copy lives so
        # the telemetry line can answer "is the SKIP legitimate?" by
        # itself. Also fills in `gpos=` from book.json (the userscript
        # doesn't always know the global position for chapter mode).
        pid_for_lookup = result.get("puzzle_id")
        if (
            status == "skipped"
            and result.get("message") == "duplicate"
            and isinstance(pid_for_lookup, int)
        ):
            try:
                loc = self._lookup_pid_location(
                    pid_for_lookup,
                    prefer_book_id=(book_ctx or {}).get("book_id"),
                )
            except Exception:
                loc = None
            if loc:
                fname = loc.get("file") or "?"
                meta["ctx_existing"] = f"{loc['book_dir']}/{fname}"
                if loc.get("pos") and "ctx_global_position" not in meta:
                    meta["ctx_global_position"] = loc["pos"]

        self.telemetry.record(
            puzzle_id=result.get("puzzle_id"),
            status=status,
            message=result.get("message", ""),
            duration_ms=duration_ms,
            url=url,
            meta=meta,
        )
        # Mark in every queue that owns this pid. With multi-book mode
        # we don't know which book the capture belongs to from the
        # capture path alone (book_ctx routes the file write, not the
        # queue), so we let each queue decide via its own mark_done
        # (now a no-op when the pid isn't in that queue's loaded ids).
        pid = result.get("puzzle_id")
        if pid is not None:
            for q in self.queues.values():
                q.mark_done(pid)
        return result


def _make_handler(state: _ReceiverState) -> type:
    """Create an HTTP request handler class bound to shared state."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "weiqi101-receiver/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            logger.debug(fmt, *args)

        def _send_json(self, code: int, data: dict) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict | None:
            """Read and parse a JSON body. Returns None and sends error if invalid."""
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > RECEIVER_MAX_BODY:
                # Drain the request body before responding. If we send
                # a response while the client is still uploading, the
                # OS closes our half of the socket and the in-flight
                # data triggers a TCP RST — Firefox/GM_xmlhttpRequest
                # report this as `onerror` ("Server unreachable") with
                # no useful diagnostics, masking the real 413. Reading
                # the body in chunks lets the upload complete cleanly
                # so the JSON error reaches the browser.
                logger.warning(
                    f"[POST-413] path={self.path} "
                    f"content_length={content_length} exceeds "
                    f"RECEIVER_MAX_BODY={RECEIVER_MAX_BODY}; draining"
                )
                remaining = content_length
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                self._send_json(413, {
                    "error": "payload too large",
                    "content_length": content_length,
                    "max_body": RECEIVER_MAX_BODY,
                })
                return None
            if content_length == 0:
                self._send_json(400, {"error": "empty body"})
                return None
            raw = self.rfile.read(content_length)
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                self._send_json(400, {"error": f"invalid JSON: {e}"})
                return None

        def do_OPTIONS(self) -> None:
            """Handle CORS preflight."""
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _book_id_param(self) -> str | None:
            """Extract ``?book_id=...`` from the request URL.

            Returns ``None`` when not present so callers can fall back
            to the legacy default queue. The value is treated as a
            string key throughout (queues dict is ``dict[str, ...]``).
            """
            try:
                qs = parse_qs(urlparse(self.path).query)
            except Exception:  # pragma: no cover - defensive
                return None
            vals = qs.get("book_id")
            if not vals:
                return None
            v = (vals[0] or "").strip()
            return v or None

        def do_GET(self) -> None:
            # Strip the query string for routing — the handlers
            # consult `_book_id_param()` themselves when they need it.
            route = urlparse(self.path).path
            if route == "/health":
                self._send_json(200, {"status": "ok", "service": "weiqi101-receiver"})
            elif route == "/status":
                self._send_json(200, {
                    "stats": state.stats,
                    "known_count": len(state.known_ids),
                    "checkpoint_downloaded": state.checkpoint.puzzles_downloaded,
                    # Legacy single-queue field (kept for back-compat
                    # with any existing dashboards / scripts).
                    "queue": state.queue.status(),
                    # Multi-book view (v5.40.0): every active or
                    # previously loaded queue, keyed by book_id
                    # ("default" is the legacy bucket).
                    "queues": state.all_queue_statuses(),
                })
            elif route == "/next":
                result = state._resolve_queue(self._book_id_param()).next_url()
                self._send_json(200, result)
            elif route == "/queue/status":
                self._send_json(200, state._resolve_queue(self._book_id_param()).status())
            elif route == "/queue/stop":
                result = state._resolve_queue(self._book_id_param()).stop()
                logger.info(f"[SESSION-END]   {result}")
                self._send_json(200, result)
            elif route == "/telemetry":
                self._send_json(200, state.telemetry.summary())
            elif route == "/books":
                self._handle_list_books()
            elif route.startswith("/book/") and route.endswith("/manifest"):
                self._handle_get_book_manifest()
            elif route.startswith("/book/") and route.endswith("/discovery"):
                self._handle_get_book_discovery()
            elif route == "/inventory":
                self._handle_get_inventory()
            elif route == "/inventory/refresh":
                self._handle_inventory_refresh()
            elif route == "/inventory/unique-sgf":
                self._handle_get_unique_sgf()
            elif route == "/coverage":
                self._handle_get_coverage_all()
            elif route.startswith("/coverage/"):
                self._handle_get_coverage_one(route)
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            # Wrap every POST so an unhandled handler exception cannot
            # silently drop the connection. With ThreadingHTTPServer
            # the handler runs in its own thread; without this guard a
            # raised exception kills the thread, RSTs the socket, and
            # the browser sees `onerror` ("Server unreachable") with
            # no clue why. Surface the traceback to the operator AND
            # send a 500 so the userscript can show the real error.
            t0 = time.monotonic()
            try:
                # Route on the path component only; query string is
                # consumed by handlers that need it (e.g. ?book_id=).
                route = urlparse(self.path).path
                if route == "/capture":
                    self._handle_capture()
                elif route == "/queue/book":
                    self._handle_queue_book()
                elif route == "/queue/ids":
                    self._handle_queue_ids()
                elif route == "/book/manifest":
                    self._handle_post_book_manifest()
                elif route == "/book/discovery/progress":
                    self._handle_post_discovery_progress()
                elif route == "/book/log/event":
                    self._handle_post_log_event()
                elif route == "/probe":
                    self._handle_probe()
                else:
                    self._send_json(404, {"error": "not found"})
            except Exception:
                elapsed_ms = (time.monotonic() - t0) * 1000
                # Inline the traceback into the log message itself.
                # `logger.exception()` relies on the configured formatter
                # to render `exc_info` — some setups (or aggressive
                # console buffering) swallow it. `traceback.format_exc()`
                # gives us the full string regardless of formatter, so
                # the operator sees the bug right next to the header.
                import traceback as _tb
                tb_text = _tb.format_exc()
                logger.error(
                    f"[POST-CRASH] path={self.path} "
                    f"after {elapsed_ms:.0f}ms — handler raised\n{tb_text}"
                )
                # Best-effort 500. If headers were already sent the
                # browser still sees a broken response, but at least
                # the traceback is in the operator's log.
                try:
                    self._send_json(500, {
                        "error": "handler exception (see receiver log)",
                    })
                except Exception:
                    pass
            else:
                elapsed_ms = (time.monotonic() - t0) * 1000
                if elapsed_ms > 2000:
                    # Slow handlers are the other failure mode (browser
                    # tab gets backgrounded, OS tears the socket down).
                    # Surface them so we know which endpoint to optimise.
                    logger.warning(
                        f"[POST-SLOW] path={self.path} "
                        f"took {elapsed_ms:.0f}ms"
                    )

        def _handle_capture(self) -> None:
            t_arrived = time.monotonic()
            payload = self._read_json_body()
            if payload is None:
                return

            # Accept either {qqdata: {...}} or raw qqdata dict
            qqdata = payload.get("qqdata") or payload
            if not isinstance(qqdata, dict):
                self._send_json(400, {"error": "qqdata must be a JSON object"})
                return

            url = payload.get("url")
            page_books = payload.get("_page_books") or []

            # Ensure the active book capture's book is in page_books for
            # YL enrichment — the "Included in" section may not render
            # when navigating during automated capture.
            book_ctx = payload.get("_book_context")
            if book_ctx and book_ctx.get("book_id"):
                ctx_id = book_ctx["book_id"]
                if not any(
                    (b.get("book_id") or b.get("id")) == ctx_id
                    for b in page_books
                ):
                    page_books.append({
                        "book_id": ctx_id,
                        "name": book_ctx.get("book_name", ""),
                    })

            # Resolve book_dir so process_qqdata skips batch save entirely
            book_dir = None
            if book_ctx and book_ctx.get("book_id"):
                book_dir = self._resolve_book_dir(book_ctx)

            # First-line acknowledgement: "we received a payload for
            # book=X Ch.Y pos.Z pid=W". Pairs with the [SAVED]/[CAPTURE-SKIP]
            # line that follows so the operator sees both arrival and
            # outcome in chronological order.
            #
            # Note: a previous version of this line included `stones=N`
            # but read `qqdata.get("black_stones")` — a key that does
            # NOT exist on raw qqdata (stones are derived inside
            # `PuzzleData.from_qqdata` by decoding `content`/`prepos`).
            # That field was always 0 and was dropped in v5.39.0.
            if book_ctx and book_ctx.get("book_id"):
                logger.info(
                    f"[CAPTURE-RECV]  book={book_ctx.get('book_id')} "
                    f"Ch.{book_ctx.get('chapter_number', '?')} "
                    f"pos.{book_ctx.get('chapter_position', '?')} "
                    f"pid={book_ctx.get('puzzle_id', '?')}"
                )

            result = state.process(
                qqdata, url=url, page_books=page_books or None,
                book_dir=book_dir, book_ctx=book_ctx,
            )
            code = 200 if result["status"] in ("ok", "skipped") else 422

            # Diagnostic logging on errors to surface qqdata structure changes
            if result["status"] == "error":
                prepos = qqdata.get("prepos", "MISSING")
                logger.warning(
                    f"[DIAG] Error capture: keys={sorted(qqdata.keys())} "
                    f"boardsize={qqdata.get('boardsize', 'MISSING')} "
                    f"lu={qqdata.get('lu', 'MISSING')} "
                    f"prepos_type={type(prepos).__name__} "
                    f"prepos_len={len(prepos) if isinstance(prepos, list) else 'N/A'}"
                )

            # Book-specific storage: write SGF content to book dir
            t_save_start = time.monotonic()
            if book_ctx and result["status"] == "ok" and result.get("_sgf_content"):
                provenance = payload.get("_capture_provenance")
                capture_meta = payload.get("_capture_meta") or {}
                self._save_to_book_dir(
                    book_ctx, result,
                    provenance=provenance,
                    capture_meta=capture_meta,
                )
            t_save_done = time.monotonic()

            # Strip internal fields before sending response
            timings = result.pop("_timings", None) or {}
            result.pop("_sgf_content", None)
            result.pop("_identity", None)
            self._send_json(code, result)
            t_response_sent = time.monotonic()

            # Stage timing log — one line per /capture so we can see
            # exactly where the ~10s observed by the userscript goes.
            # Stages:
            #   read_body  = body parse + book_dir resolve
            #   lock_wait  = time blocked on state.lock (the suspected
            #                serialization choke point)
            #   process    = process_qqdata under the lock
            #   save       = _save_to_book_dir (file write + index +
            #                book.json update + capture-log append)
            #   respond    = _send_json
            #   total      = arrived → response sent (compare to
            #                userscript-side backend_ms in PROBE log)
            try:
                t_proc_enter = timings.get("process_enter", t_save_start)
                t_lock_acquired = timings.get("lock_acquired", t_proc_enter)
                t_process_done = timings.get("process_done", t_save_start)
                logger.info(
                    "[TIMING]        "
                    f"read_body={(t_proc_enter - t_arrived) * 1000:.0f}ms "
                    f"lock_wait={(t_lock_acquired - t_proc_enter) * 1000:.0f}ms "
                    f"process={(t_process_done - t_lock_acquired) * 1000:.0f}ms "
                    f"save={(t_save_done - t_save_start) * 1000:.0f}ms "
                    f"respond={(t_response_sent - t_save_done) * 1000:.0f}ms "
                    f"total={(t_response_sent - t_arrived) * 1000:.0f}ms "
                    f"status={result.get('status')} "
                    f"pid={result.get('puzzle_id')}"
                )
            except Exception:
                logger.debug("[TIMING] log failed", exc_info=True)

        def _resolve_book_dir(self, book_ctx: dict[str, Any]) -> Path:
            """Resolve (or create) the book's directory under books/."""
            book_id = book_ctx.get("book_id")
            book_name = book_ctx.get("book_name", "")
            books_dir = state.output_dir / "books"
            return book_state.find_book_dir(books_dir, book_id) or \
                book_state.resolve_book_dir(books_dir, book_id, book_name)

        def _save_to_book_dir(
            self,
            book_ctx: dict[str, Any],
            result: dict[str, Any],
            *,
            provenance: dict[str, Any] | None = None,
            capture_meta: dict[str, Any] | None = None,
        ) -> None:
            """Write SGF content directly to the book's directory.

            Naming: ``{global_pos}_{chapter_label}_{chapter_pos}_{puzzle_id}.sgf``
            where ``chapter_label`` is an ASCII English slug derived from
            the userscript's visible label (browser-translated) when
            available, falling back to ``ChineseTranslator`` and finally to
            the zero-padded chapter number. Filenames never contain CJK
            — raw CJK is preserved in ``capture-log.jsonl`` and
            ``book-index.json``.

            Examples:
              0042_escape-stones_012_9247.sgf  → chapter resolved to English
              0001_02_001_28957.sgf            → no English available, fell back
            """
            global_pos = book_ctx.get("global_position", 0)
            chapter_num = book_ctx.get("chapter_number", 0)
            # ``chapter_name`` is the legacy single field (may be CJK).
            # ``chapter_name_visible`` is the userscript-supplied label
            # after the browser translation extension has run; it may be
            # English or still CJK depending on extension timing.
            chapter_name_raw = (
                book_ctx.get("chapter_name_raw")
                or book_ctx.get("chapter_name")
                or ""
            )
            chapter_name_visible = (
                book_ctx.get("chapter_name_visible")
                or book_ctx.get("chapter_name")
                or ""
            )
            chapter_pos = book_ctx.get("chapter_position", 0)
            puzzle_id = book_ctx.get("puzzle_id") or result.get("puzzle_id")
            sgf_content = result["_sgf_content"]

            book_dir = self._resolve_book_dir(book_ctx)
            sgf_dir = book_dir / "sgf"
            sgf_dir.mkdir(parents=True, exist_ok=True)

            # Resolve English chapter slug (visible → translate → number).
            label = resolve_label(
                chapter_name_visible,
                chapter_name_raw,
                context=f"book={book_ctx.get('book_id')} ch={chapter_num}",
            )
            ch_label = label["slug"] or str(chapter_num).zfill(2)

            # Naming rule:
            #   chapter mode (capture_mode == 'chapter' AND chapter_num > 0):
            #     ch{NN}_{PPP}_{slug}_{pid}.sgf       e.g. ch01_005_life-and-death-introductory-1_9538.sgf
            #   legacy fallback (no chapter context):
            #     {GGGG}_{slug}_{PPP}_{pid}.sgf       e.g. 0042_escape-stones_012_9247.sgf
            capture_mode = (book_ctx.get("capture_mode") or "").lower()
            if capture_mode == "chapter" and chapter_num > 0:
                padded_ch = f"ch{str(chapter_num).zfill(2)}"
                padded_chpos = str(chapter_pos).zfill(3)
                dest_name = f"{padded_ch}_{padded_chpos}_{ch_label}_{puzzle_id}.sgf"
            else:
                padded_pos = str(global_pos).zfill(4)
                padded_chpos = str(chapter_pos).zfill(3)
                dest_name = f"{padded_pos}_{ch_label}_{padded_chpos}_{puzzle_id}.sgf"
            dest_path = sgf_dir / dest_name

            dest_path.write_text(sgf_content, encoding="utf-8")
            # Persist to global sgf-index.txt so known_ids survives
            # server restarts without scanning individual book.json files.
            add_book_to_index(state.output_dir, book_dir.name, dest_name, puzzle_id)
            # Unified verb-prefix log shape. [SAVED] is paired with the
            # earlier [CAPTURE-RECV] line and the following [PROGRESS]
            # line so the operator can scan three-line bursts per
            # successful save. `recovered=true` is set when the browser
            # signalled this capture followed a publicid_unsettled retry.
            # `gate=observer|poll|timeout` (v5.39.0+) shows which path
            # opened the readiness gate — use to audit how often the
            # MutationObserver fast-path is doing the work.
            recovered = bool((capture_meta or {}).get("recovered"))
            attempts = (capture_meta or {}).get("attempts")
            gate_source = (capture_meta or {}).get("gate_source")
            recovery_tail = ""
            if recovered:
                recovery_tail = " recovered=true"
                if attempts:
                    recovery_tail += f" attempts={attempts}"
            if gate_source:
                recovery_tail += f" gate={gate_source}"
            logger.info(
                f"[SAVED]         book={book_ctx.get('book_id')} "
                f"Ch.{chapter_num} pos.{chapter_pos} pid={puzzle_id} "
                f"file={dest_path.name} chapter='{label['display']}' "
                f"src={label['source']}{recovery_tail}"
            )
            # Per-book progress: rebuild from disk so the count survives
            # across receiver restarts and resumes. Cheap (single dir scan).
            # Append rolling-window throughput so the operator sees the
            # trend in-line on the console; same string lands in the
            # JSONL audit log via the file handler attached to `logger`.
            try:
                saved_now = sum(1 for _ in sgf_dir.glob("*.sgf"))
                book_data = book_state.load(book_dir)
                total = book_data.get("total_puzzles") or len(
                    book_data.get("puzzle_ids", [])
                ) or 0
                rates = state.telemetry.rolling_rates()
                rate_str = (
                    f" rate={rates['5m']['per_min']}/min(5m) "
                    f"{rates['15m']['per_min']}/min(15m)"
                )
                if total:
                    pct = (saved_now * 100.0) / total
                    logger.info(
                        f"[PROGRESS]      book={book_ctx.get('book_id')} "
                        f"saved={saved_now}/{total} ({pct:.0f}%){rate_str}"
                    )
                else:
                    logger.info(
                        f"[PROGRESS]      book={book_ctx.get('book_id')} "
                        f"saved={saved_now}{rate_str}"
                    )
            except Exception:
                logger.debug("[PROGRESS] computation failed", exc_info=True)

            # Auto-register this book in the runtime book registry so
            # downstream tooling has full provenance for the YL slug
            # (raw zh, browser-visible, library-translated English).
            try:
                from . import _book_registry, _local_collections_mapping
                book_id = book_ctx.get("book_id")
                if book_id:
                    book_label = resolve_label(
                        book_ctx.get("book_name_visible") or book_ctx.get("book_name"),
                        book_ctx.get("book_name_raw") or book_ctx.get("book_name"),
                        context=f"book={book_id}",
                    )
                    book_slug = (
                        _local_collections_mapping.resolve_book_slug(
                            book_id, book_name=book_label["display"],
                        )
                        or f"101weiqi-book-{book_id}"
                    )
                    _book_registry.register_book(
                        book_id,
                        slug=book_slug,
                        name_raw=book_label["raw"],
                        name_visible=book_ctx.get("book_name_visible") or "",
                        name_english=book_label["english"],
                        label_source=book_label["source"],
                        chapter_english=label["english"] or None,
                    )
            except Exception:
                logger.debug(
                    "[REGISTRY] auto-register failed", exc_info=True,
                )

            # Append to per-book capture log. Preserve raw CJK + English
            # forms so downstream tooling and a future cleanup pass have
            # full provenance.
            #
            # Schema note: every row in capture-log.jsonl now carries an
            # `event_type` discriminator so puzzle captures, discovery
            # progress, and capture-mode lifecycle events all live in
            # the same file. Existing rows written before this change
            # have no `event_type` and are interpreted as
            # "puzzle_captured" by readers.
            log_path = book_dir / "capture-log.jsonl"
            identity = result.get("_identity") or {}
            entry = {
                "event_type": "puzzle_captured",
                "puzzle_id": puzzle_id,
                # v2 identity fields (2026-04-24): all four candidate IDs
                # so future drift analysis is cheap. content_hash is
                # recorded but not yet used for dedup.
                "qqdata_publicid": identity.get("qqdata_publicid"),
                "qqdata_id": identity.get("qqdata_id"),
                "url_pid": identity.get("url_pid"),
                "content_hash": identity.get("content_hash"),
                "global_position": global_pos,
                # chapter_id is the durable site identifier; chapter_number
                # is our 1-based ordering within the book. Both recorded
                # so cross-session drift can be detected even when the
                # site reorders chapters.
                "chapter_id": book_ctx.get("chapter_id") or 0,
                "chapter_number": chapter_num,
                "chapter_name": label["display"],
                "chapter_name_raw": label["raw"],
                "chapter_name_english": label["english"],
                "chapter_label_source": label["source"],
                "chapter_position": chapter_pos,
                "file": dest_name,
                "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            # Multi-layer reconciliation provenance (added 2026-04-25).
            # Records which page-fact layers (qqdata / url / dom-visible)
            # agreed on the pid, which conflicted, which book/chapter
            # source was selected, and whether the capture drifted from
            # the active book target. Optional — older clients omit it.
            if provenance:
                entry["capture_provenance"] = provenance
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Update book.json positions[] to reflect this capture.
            # ``book.json`` is the single source of truth (schema v5).
            #
            # Pid-keyed match (schema v5 invariant): pid is the natural
            # key in positions[]. Match strictly by pid; never silently
            # rewrite the pid of an entry to "fix" a stale global_pos
            # sent by the browser. If no entry exists for this pid, we
            # append one — manifest discovery may have lagged the
            # capture, or the chapter is yet to be re-fetched.
            try:
                with book_state.book_lock(book_dir):
                    state_data = book_state.load(book_dir)
                    if state_data:
                        book_state.apply_capture(
                            state_data,
                            pid=puzzle_id,
                            file=dest_name,
                            chapter_number=chapter_num,
                            chapter_position=chapter_pos,
                            chapter_name=label["display"],
                        )
                        # Defensive: dedupe in case prior runs (pre-v5) left
                        # duplicate pid entries from the old pos-first matcher.
                        book_state.dedupe_positions(state_data)
                        _book_state_recount(state_data)
                        book_state.save_async(book_dir, state_data)
            except Exception:
                logger.warning(
                    "[BOOK] Failed to update book.json",
                    exc_info=True,
                )

        def _generate_positions(
            self, book_dir: Path, manifest: dict[str, Any],
        ) -> tuple[list[dict[str, Any]], dict[str, int]]:
            """Build the positions[] array for ``book.json`` from a manifest.

            Walks chapters in chapter_number order, assigns a 1-based
            global ``pos`` across the deduplicated chapter union, and sets
            initial status from disk + global index + cross-book scan.

            Returns ``(positions, counts)`` so the caller can fold them
            into the consolidated book.json — no separate file is written.
            """
            chapters = manifest.get("chapters", [])

            sorted_chapters = sorted(
                chapters, key=lambda c: c.get("chapter_number", 0),
            )
            canonical_pids: list[int] = []
            ch_lookup: dict[int, dict[str, Any]] = {}
            seen: set[int] = set()
            for ch in sorted_chapters:
                ch_num = ch.get("chapter_number", 0)
                ch_name = ch.get("name", "")
                for idx, pid in enumerate(ch.get("puzzle_ids", [])):
                    if pid in seen:
                        continue
                    seen.add(pid)
                    canonical_pids.append(pid)
                    ch_lookup[pid] = {
                        "chapter_number": ch_num,
                        "chapter_name": ch_name,
                        "chapter_position": idx + 1,
                    }

            if not canonical_pids:
                return [], {"captured": 0, "external": 0, "pending": 0}

            # Already-captured files in our own sgf/
            sgf_dir = book_dir / "sgf"
            disk_pids: dict[int, str] = {}
            if sgf_dir.exists():
                for f in sgf_dir.iterdir():
                    if f.suffix == ".sgf":
                        parts = f.stem.rsplit("_", 1)
                        if len(parts) == 2:
                            try:
                                disk_pids[int(parts[1])] = f.name
                            except ValueError:
                                pass

            # Global sgf-index for external refs (qday etc.)
            from .index import INDEX_FILENAME
            from tools.core.index import load_index
            index_entries = load_index(state.output_dir / INDEX_FILENAME)
            global_pid_paths: dict[int, str] = {}
            for entry in index_entries:
                if ":" in entry:
                    path_part, _, pid_str = entry.rpartition(":")
                    try:
                        global_pid_paths[int(pid_str)] = path_part
                    except ValueError:
                        pass
                else:
                    filename = (
                        entry.rsplit("/", 1)[-1] if "/" in entry else entry
                    )
                    stem = filename.replace(".sgf", "")
                    try:
                        global_pid_paths[int(stem)] = entry
                    except ValueError:
                        pass

            # Cross-book scan — pids captured under other books'
            # sgf/ dirs (e.g. via a different book's chapter sweep).
            books_root = state.output_dir / "books"
            if books_root.is_dir():
                for other_book_dir in books_root.iterdir():
                    if not other_book_dir.is_dir():
                        continue
                    if other_book_dir.resolve() == book_dir.resolve():
                        continue
                    other_sgf_dir = other_book_dir / "sgf"
                    if not other_sgf_dir.is_dir():
                        continue
                    for f in other_sgf_dir.iterdir():
                        if f.suffix != ".sgf":
                            continue
                        try:
                            other_pid = int(f.stem.rsplit("_", 1)[-1])
                        except ValueError:
                            continue
                        if other_pid in global_pid_paths:
                            continue
                        rel = f.relative_to(state.output_dir).as_posix()
                        global_pid_paths[other_pid] = rel

            positions: list[dict[str, Any]] = []
            counts = {"captured": 0, "external": 0, "pending": 0}
            for i, pid in enumerate(canonical_pids):
                pos = i + 1
                ch = ch_lookup.get(pid, {})
                entry: dict[str, Any] = {
                    "pos": pos,
                    "pid": pid,
                    "chapter_name": ch.get("chapter_name", ""),
                    "chapter_number": ch.get("chapter_number", 0),
                    "chapter_position": ch.get("chapter_position", 0),
                }
                if pid in disk_pids:
                    entry["status"] = "captured"
                    entry["file"] = disk_pids[pid]
                    counts["captured"] += 1
                elif pid in global_pid_paths:
                    entry["status"] = "external"
                    entry["ref"] = global_pid_paths[pid]
                    counts["external"] += 1
                elif pid in state.known_ids:
                    entry["status"] = "external"
                    entry["ref"] = "global"
                    counts["external"] += 1
                else:
                    entry["status"] = "pending"
                    counts["pending"] += 1
                positions.append(entry)
            return positions, counts

        def _handle_queue_book(self) -> None:
            """POST /queue/book — Load a book's puzzle IDs into the queue.

            Body: {"book_id": 197}
            """
            payload = self._read_json_body()
            if payload is None:
                return

            book_id = payload.get("book_id")
            if not isinstance(book_id, int):
                self._send_json(400, {"error": "book_id must be an integer"})
                return

            # Use the base output dir for book-ids.jsonl lookup
            base_dir = get_output_dir(None)
            # Multi-book mode: each book_id gets its own queue. The
            # default queue is left untouched so single-book legacy
            # callers and CLI pre-load remain unaffected.
            queue = state._resolve_queue(book_id)
            result = queue.load_book(
                book_id=book_id,
                output_dir=base_dir,
                known_ids=state.known_ids,
            )

            if "error" in result:
                self._send_json(404, result)
            else:
                # Update telemetry with book context
                state.telemetry.set_book(
                    result.get("book_id"),
                    result.get("book_name"),
                )
                self._send_json(200, result)

        def _handle_queue_ids(self) -> None:
            """POST /queue/ids — Load arbitrary puzzle IDs into the queue.

            Body: {"ids": [1001, 1002, 1003], "label": "custom-batch"}
            """
            payload = self._read_json_body()
            if payload is None:
                return

            ids = payload.get("ids")
            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                self._send_json(400, {"error": "ids must be an array of integers"})
                return

            label = payload.get("label", "manual")
            # Optional book_id key for multi-book mode; falls back to
            # the legacy default queue when absent.
            queue_key = payload.get("book_id")
            queue = state._resolve_queue(queue_key)
            result = queue.load_ids(
                ids=ids,
                known_ids=state.known_ids,
                label=str(label),
            )

            if "error" in result:
                self._send_json(400, result)
            else:
                state.telemetry.set_book(None, None)
                self._send_json(200, result)

        def _handle_list_books(self) -> None:
            """GET /books — List books from books-catalog.jsonl with download progress.

            Query params:
              - refresh=1 — rebuild catalog from inputs AND re-read
                ``sgf-index.txt`` into ``state.known_ids`` so external
                downloads (e.g. another tool) are reflected without
                restarting the receiver.
            """
            from . import catalog as catalog_mod
            from .index import load_puzzle_ids

            qs = parse_qs(urlparse(self.path).query)
            refresh = qs.get("refresh", ["0"])[0] in ("1", "true", "yes")

            if refresh:
                with state.lock:
                    catalog_mod.rebuild_books_catalog(state.output_dir)
                    state.known_ids = load_puzzle_ids(state.output_dir)
                logger.info("[BOOKS] /books?refresh=1 — catalog rebuilt and known_ids reloaded")

            entries = catalog_mod.load_catalog(state.output_dir)
            if not entries:
                self._send_json(200, {
                    "books": [],
                    "message": (
                        "No books-catalog.jsonl found. Run: "
                        "python -m tools.weiqi101 rebuild-catalog"
                    ),
                })
                return

            # Re-resolve puzzle counts from book-ids.jsonl so per-book
            # downloaded/remaining stays accurate without bloating the
            # catalog with all puzzle IDs.
            jsonl_path = state.output_dir / catalog_mod.BOOK_IDS_FILE
            id_lookup: dict[int, list[int]] = {}
            if jsonl_path.exists():
                with jsonl_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            raw = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        bid = int(raw.get("book_id", 0))
                        chapters = raw.get("chapters") or []
                        if chapters:
                            ids: list[int] = []
                            for ch in chapters:
                                ids.extend(ch.get("puzzle_ids") or [])
                        else:
                            ids = list(raw.get("puzzle_ids") or [])
                        id_lookup[bid] = ids

            books = []
            for entry in entries:
                bid = int(entry["book_id"])
                ids = id_lookup.get(bid, [])
                done = sum(1 for pid in ids if pid in state.known_ids)
                total = len(ids) or int(entry.get("puzzle_count", 0))
                books.append({
                    "book_id": bid,
                    "name": entry.get("name", ""),
                    "name_cn": entry.get("name_cn", ""),
                    "total": total,
                    "downloaded": done,
                    "remaining": max(total - done, 0),
                    "complete": done == total and total > 0,
                    "difficulty": entry.get("difficulty", ""),
                    "consensus_tier": entry.get("consensus_tier", "unrated"),
                    "review_stale": bool(entry.get("review_stale", False)),
                    "go_advisor_tier": entry.get("go_advisor_tier"),
                    "go_advisor_note": entry.get("go_advisor_note"),
                    "modern_player_tier": entry.get("modern_player_tier"),
                    "modern_player_target": entry.get("modern_player_target"),
                    "tags": entry.get("tags", []),
                    "sharer": entry.get("sharer", ""),
                })

            # Sort: incomplete-first, then by tier, then by remaining desc.
            tier_rank = catalog_mod.TIER_VALUES
            books.sort(key=lambda b: (
                b["complete"],
                tier_rank.get(b["consensus_tier"], 99),
                -b["remaining"],
            ))

            logger.info(f"[BOOKS] Listed {len(books)} books from {catalog_mod.CATALOG_FILE}")
            self._send_json(200, {"books": books})

        def _handle_post_book_manifest(self) -> None:
            """POST /book/manifest — Store a book manifest from browser discovery."""
            payload = self._read_json_body()
            if payload is None:
                return

            book_id = payload.get("book_id")
            if not isinstance(book_id, int):
                self._send_json(400, {"error": "book_id must be an integer"})
                return

            book_name = payload.get("book_name", "")

            # Reuse existing book directory if one exists for this book_id;
            # otherwise compute a fresh slug-based path. Both helpers live
            # in book_state so all call sites stay consistent.
            books_dir = state.output_dir / "books"
            book_dir = book_state.find_book_dir(books_dir, book_id) or \
                book_state.resolve_book_dir(books_dir, book_id, book_name)

            book_dir.mkdir(parents=True, exist_ok=True)
            sgf_dir = book_dir / "sgf"
            sgf_dir.mkdir(exist_ok=True)

            # ----------------------------------------------------------
            # Server-side label translation
            # ----------------------------------------------------------
            # Discovery is scraped from the chapter page DOM at a moment
            # when the browser translation extension may not yet have
            # rewritten the text. Rather than racing the extension in the
            # userscript, we resolve every label on the receiver using
            # the same `resolve_label` pipeline used for SGF filenames.
            # The raw CJK is preserved alongside the English form so a
            # future re-translation pass is loss-free.
            book_label = resolve_label(
                payload.get("book_name_visible"),
                payload.get("book_name_raw") or book_name,
                context=f"manifest book={book_id}",
            )
            # Promote the English label as the canonical book_name and
            # keep the original CJK in `book_name_raw`.
            if book_label["english"]:
                payload["book_name_raw"] = book_label["raw"] or book_name
                payload["book_name"] = book_label["display"]
                payload["book_name_english"] = book_label["english"]
            else:
                payload.setdefault("book_name_raw", book_name)

            # Translate every chapter's `name` field. We mutate in place
            # so downstream consumers (`_generate_book_index`, the
            # userscript's `puzzle_chapter_lookup`) see English text.
            for ch in payload.get("chapters", []) or []:
                raw_name = ch.get("name") or ""
                if not raw_name:
                    continue
                ch_label = resolve_label(
                    ch.get("name_visible"),
                    raw_name,
                    context=(
                        f"manifest book={book_id} "
                        f"ch={ch.get('chapter_number')}"
                    ),
                )
                ch["name_raw"] = ch_label["raw"] or raw_name
                if ch_label["english"]:
                    ch["name"] = ch_label["display"]
                    ch["name_english"] = ch_label["english"]
                ch["name_label_source"] = ch_label["source"]

            # Fold the manifest into the consolidated book.json (schema v4).
            # Single source of truth — no separate manifest.json file.
            # Hold the per-book lock across the entire RMW so a concurrent
            # /book/discovery/progress or /capture cannot interleave a
            # competing save and tear the file.
            with book_state.book_lock(book_dir):
                self._fold_manifest_locked(book_dir, payload, book_id)

            total_pids = sum(
                len(ch.get("puzzle_ids", []))
                for ch in payload.get("chapters", [])
            )
            rel = (
                book_dir / book_state.BOOK_STATE_FILENAME
            ).relative_to(state.output_dir).as_posix()
            is_partial = bool(payload.get("partial"))
            logger.info(
                f"[BOOK] book.json saved: {rel} "
                f"({len(payload.get('chapters', []))} chapters, "
                f"{total_pids} puzzle IDs"
                f"{', partial' if is_partial else ''})"
            )
            self._send_json(200, {
                "status": "ok",
                "path": rel,
                "partial": is_partial,
                "book_id": book_id,
                "book_dir": book_dir.name,
            })

        def _fold_manifest_locked(
            self,
            book_dir: Path,
            payload: dict[str, Any],
            book_id: int,
        ) -> None:
            """RMW body of ``_handle_post_book_manifest``. Caller holds book_lock."""
            state_data = book_state.load(book_dir)
            if not state_data:
                state_data = book_state.initialize(
                    book_id,
                    book_name=payload.get("book_name", ""),
                    book_name_raw=payload.get("book_name_raw", ""),
                    book_name_english=payload.get("book_name_english"),
                    book_name_visible=payload.get("book_name_visible"),
                    book_difficulty=payload.get("book_difficulty"),
                )
            else:
                # Update identity fields with whatever the userscript sent.
                for k in (
                    "book_name", "book_name_raw", "book_name_english",
                    "book_name_visible", "book_slug", "book_difficulty",
                ):
                    if payload.get(k) is not None:
                        state_data[k] = payload[k]

            # Partial vs final manifest:
            # - partial=true (interleaved discovery↔capture, v5.38.0+)
            #   merges chapters by chapter_id so server-managed skip
            #   state on later chapters is preserved, and leaves
            #   discovery.status="in_progress" so a later partial or
            #   final POST can land cleanly.
            # - partial=false (legacy / final) replaces chapters
            #   wholesale and marks discovery complete.
            is_partial = bool(payload.get("partial"))

            if is_partial:
                # Merge new chapter records into the existing list by
                # chapter_id. The userscript may send only the chapters
                # discovered in the latest pass (typical interleaved
                # flow) or the full accumulated list — both work.
                # Server-managed skip fields on chapters absent from
                # the payload are preserved.
                existing_by_id: dict[Any, dict[str, Any]] = {
                    ch.get("chapter_id"): ch
                    for ch in (state_data.get("chapters") or [])
                    if isinstance(ch, dict) and ch.get("chapter_id") is not None
                }
                incoming = [
                    c for c in payload.get("chapters", [])
                    if isinstance(c, dict)
                ]
                # Apply merge_discovery_state ONLY to the incoming
                # chapters (it preserves skip fields by chapter_id).
                merged_view = book_state.merge_discovery_state(
                    state_data,
                    {
                        "book_id": book_id,
                        "book_name": payload.get("book_name", ""),
                        "phase": "chapter_puzzles",
                        "chapters": incoming,
                    },
                )
                merged_incoming_by_id = {
                    ch.get("chapter_id"): ch
                    for ch in merged_view.get("chapters", [])
                    if isinstance(ch, dict) and ch.get("chapter_id") is not None
                }
                # Overlay incoming on top of existing.
                for cid, ch in merged_incoming_by_id.items():
                    existing_by_id[cid] = ch
                # Preserve overall ordering by chapter_number when known.
                state_data["chapters"] = sorted(
                    existing_by_id.values(),
                    key=lambda c: c.get("chapter_number") or 0,
                )
                disc = state_data.setdefault("discovery", {})
                disc["status"] = "in_progress"
                disc["phase"] = "chapter_puzzles"
            else:
                # Replace chapters wholesale (manifest carries the full list).
                state_data["chapters"] = [
                    book_state._normalize_chapter(c)
                    for c in payload.get("chapters", []) if isinstance(c, dict)
                ]
                # Mark discovery complete.
                disc = state_data.setdefault("discovery", {})
                disc["status"] = "complete"
                disc["phase"] = "done"
                disc["completed_at"] = datetime.now(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                )

            # Build positions[] from chapters and seed status from disk +
            # global index + cross-book scan. For partial manifests we
            # pass the merged chapter list (which includes any chapters
            # known from prior partial POSTs) so positions stay valid.
            positions_payload = (
                {"chapters": state_data.get("chapters", [])}
                if is_partial else payload
            )
            positions, _counts = self._generate_positions(
                book_dir, positions_payload,
            )
            # Carry forward any prior captured/external state by pid
            # (schema v5 invariant: pid is the natural key). The freshly
            # computed list is seeded only from disk + global index;
            # carry_forward preserves any state set by per-capture
            # handlers since the last manifest rebuild.
            state_data["positions"] = book_state.carry_forward_capture_state(
                state_data, positions,
            )
            # Defensive dedupe — guards against legacy book.json files
            # that may have duplicate-pid entries from pre-v5 races.
            book_state.dedupe_positions(state_data)
            _book_state_recount(state_data)
            book_state.save(book_dir, state_data)

        def _handle_get_coverage_all(self) -> None:
            """GET /coverage — Coverage summary for every downloaded book.

            Read-only; safe under ThreadingHTTPServer concurrency. The
            master ``book-ids.jsonl`` is mtime-cached; per-book
            ``book.json`` reads use ``book_state.load`` which already
            handles in-flight writes from the capture path.

            Query params:
              - include_pending=1 — count ``pending`` positions as present.
            """
            qs = parse_qs(urlparse(self.path).query)
            include_pending = qs.get(
                "include_pending", ["0"],
            )[0] in ("1", "true", "yes")
            try:
                reports = coverage_mod.list_coverage(
                    state.output_dir, include_pending=include_pending,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("[COVERAGE] /coverage failed")
                self._send_json(500, {"error": str(exc)})
                return
            self._send_json(200, {
                "books": [r.to_dict(include_ids=False) for r in reports],
                "include_pending": include_pending,
            })

        def _handle_get_coverage_one(self, route: str) -> None:
            """GET /coverage/{book_id} — Detailed coverage for one book.

            Includes ``missing_ids`` and ``extra_ids`` so the caller can
            persist them if they choose; the server itself never writes
            anything for this route.

            Query params:
              - include_pending=1 — count ``pending`` positions as present.
              - ids=0           — omit missing_ids/extra_ids from response.
            """
            m = re.match(r"^/coverage/(\d+)$", route)
            if not m:
                self._send_json(400, {"error": "invalid path"})
                return
            book_id = int(m.group(1))
            qs = parse_qs(urlparse(self.path).query)
            include_pending = qs.get(
                "include_pending", ["0"],
            )[0] in ("1", "true", "yes")
            include_ids = qs.get("ids", ["1"])[0] not in ("0", "false", "no")
            try:
                report = coverage_mod.compute_coverage(
                    book_id, state.output_dir,
                    include_pending=include_pending,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("[COVERAGE] /coverage/%s failed", book_id)
                self._send_json(500, {"error": str(exc)})
                return
            code = 404 if report.status == "error" else 200
            self._send_json(code, report.to_dict(include_ids=include_ids))

        def _handle_get_book_manifest(self) -> None:
            """GET /book/{id}/manifest — Return stored book manifest + known IDs.

            Reads the consolidated ``book.json`` and projects the legacy
            manifest wire shape so the userscript stays unchanged.
            """
            m = re.match(r"^/book/(\d+)/manifest$", self.path)
            if not m:
                self._send_json(400, {"error": "Invalid path"})
                return

            book_id = int(m.group(1))
            books_dir = state.output_dir / "books"
            if not books_dir.exists():
                self._send_json(404, {"error": "No books directory"})
                return

            book_dir = book_state.find_book_dir(books_dir, book_id)
            if book_dir is None:
                self._send_json(404, {"error": f"No book dir for {book_id}"})
                return
            data = book_state.load(book_dir)
            if not data or not data.get("chapters"):
                self._send_json(
                    404, {"error": f"No manifest for book {book_id}"},
                )
                return

            manifest = book_state.project_manifest_view(data)

            # Collect all puzzle IDs the manifest knows about.
            all_ids = book_state.all_pids(data)

            # Authoritative known set: positions in book.json marked
            # captured/external + any sgf/ files on disk + cross-book scan.
            known_ids: set[int] = book_state.known_pids(data)

            sgf_dir = book_dir / "sgf"
            if sgf_dir.exists():
                for f in sgf_dir.iterdir():
                    if f.suffix == ".sgf":
                        pid = pid_from_filename(f.name)
                        if pid is not None:
                            known_ids.add(pid)

            # Cross-book: pids captured under other books' sgf/ since
            # receiver startup. Promote into the receiver-wide cache so
            # subsequent /capture dedup benefits even for puzzles outside
            # this book's manifest.
            cross_book_ids: set[int] = set()
            for other in books_dir.iterdir():
                if not other.is_dir():
                    continue
                other_sgf = other / "sgf"
                if not other_sgf.is_dir():
                    continue
                for f in other_sgf.iterdir():
                    if f.suffix != ".sgf":
                        continue
                    pid = pid_from_filename(f.name)
                    if pid is not None:
                        cross_book_ids.add(pid)
            state.known_ids.update(cross_book_ids)
            known_ids.update(pid for pid in all_ids if pid in state.known_ids)

            manifest["known_ids"] = sorted(known_ids)
            manifest["capture_stats"] = {
                "total": len(all_ids),
                "known": len(known_ids),
                "remaining": len(all_ids - known_ids),
            }

            # Pre-capture chapter audit: per-chapter breakdown of
            # captured vs remaining vs dom_missing puzzles.
            #
            # `dom_missing` pids (live chapter listing no longer renders
            # them \u2014 see book_state.apply_dom_missing) are folded into
            # `known_ids` above so the userscript skips them on resume,
            # and so `remaining` here means "remaining-capturable" rather
            # than "manifest minus disk". We surface the dom_missing
            # count separately so operators can see the difference.
            dom_missing_set = book_state.dom_missing_pids(data)
            chapter_audit: list[dict[str, Any]] = []
            for ch in data.get("chapters", []):
                ch_pids = set(ch.get("puzzle_ids", []))
                ch_known = ch_pids & known_ids
                ch_dom_missing = sorted(ch_pids & dom_missing_set)
                ch_remaining = sorted(ch_pids - known_ids)
                chapter_audit.append({
                    "chapter_number": ch.get("chapter_number"),
                    "chapter_name": ch.get("name", ""),
                    "total": len(ch_pids),
                    # `captured` here = anything in known_ids that isn't
                    # dom_missing (covers captured + external + disk-scan).
                    "captured": len(ch_known) - len(ch_dom_missing),
                    "dom_missing": len(ch_dom_missing),
                    "dom_missing_pids": ch_dom_missing,
                    "remaining": len(ch_remaining),
                    "remaining_pids": ch_remaining,
                })
            manifest["chapter_audit"] = chapter_audit

            # Log chapters with remaining puzzles for operator visibility.
            for ca in chapter_audit:
                if ca["remaining"] > 0 or ca["dom_missing"] > 0:
                    pids_preview = ca["remaining_pids"][:10]
                    ellipsis = "..." if len(ca["remaining_pids"]) > 10 else ""
                    dm_suffix = (
                        f", {ca['dom_missing']} dom_missing"
                        if ca["dom_missing"] else ""
                    )
                    logger.info(
                        f"[AUDIT]         book={book_id} "
                        f"Ch.{ca['chapter_number']}: "
                        f"\"{ca['chapter_name']}\" \u2014 "
                        f"{ca['total']} total, "
                        f"{ca['captured']} captured{dm_suffix}, "
                        f"{ca['remaining']} remaining "
                        f"(pids: {pids_preview}{ellipsis})"
                    )

            self._send_json(200, manifest)

        def _handle_post_discovery_progress(self) -> None:
            """POST /book/discovery/progress — Log discovery progress to JSONL."""
            payload = self._read_json_body()
            if payload is None:
                return

            book_id = payload.get("book_id")
            phase = payload.get("phase", "unknown")
            step = payload.get("step", "")
            detail = payload.get("detail", {}) or {}

            # Build a richer human-readable message that surfaces chapter,
            # page and counts so the console reflects what the JSONL captures.
            extras: list[str] = []
            ch_idx = detail.get("chapter_idx")
            ch_name = detail.get("chapter_name")
            if ch_idx is not None:
                # chapter_idx is 0-based in the userscript; show 1-based.
                label = f"ch{int(ch_idx) + 1}"
                if ch_name:
                    label += f" '{ch_name}'"
                extras.append(label)
            section_id = detail.get("section_id")
            if section_id:
                extras.append(f"section={section_id}")
            page = detail.get("page")
            max_page = detail.get("max_page")
            if page is not None and max_page is not None:
                extras.append(f"page={page}/{max_page}")
            elif page is not None:
                extras.append(f"page={page}")
            ids_on_page = detail.get("ids_on_page")
            if ids_on_page is not None:
                extras.append(f"got={ids_on_page}")
            ids_in_chapter = detail.get("ids_in_chapter")
            total_ids = detail.get("total_ids")
            if ids_in_chapter is not None:
                extras.append(f"ch_total={ids_in_chapter}")
            if total_ids is not None:
                extras.append(f"total={total_ids}")
            chapter_count = detail.get("chapter_count")
            if chapter_count is not None:
                extras.append(f"chapters={chapter_count}")
            book_name = detail.get("book_name")
            if book_name and step == "discovery_started":
                extras.append(f"name='{book_name}'")

            extra_str = (" " + " ".join(extras)) if extras else ""
            human_msg = (
                f"[BOOK-DISCOVER] book={book_id} phase={phase} step={step}"
                f"{extra_str}"
            )

            if state._slog:
                # Strip keys that would collide with the explicit kwargs
                # we pass to StructuredLogger.event() (and with its own
                # positional parameters event_type/message/level).
                _reserved = {
                    "event_type", "message", "level",
                    "book_id", "phase", "step",
                }
                safe_detail = {
                    k: v for k, v in detail.items() if k not in _reserved
                }
                state._slog.event(
                    EventType.PROGRESS,
                    human_msg,
                    book_id=book_id,
                    phase=phase,
                    step=step,
                    **safe_detail,
                )
            else:
                logger.info(human_msg)

            # Mirror discovery progress into the per-book capture-log so
            # the full lifecycle (discovery → capture → skips → done)
            # is visible in one file. We MUST create the book dir on
            # demand: the very first event of a session (`discovery_started`)
            # fires before any checkpoint is saved, so the dir doesn't
            # exist yet. Without this mkdir the first — and most useful
            # — telemetry line was silently dropped (Bug A, 2026-04-24).
            try:
                if book_id is not None:
                    book_dir = self._resolve_book_dir({
                        "book_id": int(book_id),
                        "book_name": detail.get("book_name") or "",
                    })
                    book_dir.mkdir(parents=True, exist_ok=True)
                    log_path = book_dir / "capture-log.jsonl"
                    log_entry = {
                        "event_type": f"discovery_{step}" if step else "discovery_event",
                        "phase": phase,
                        "step": step,
                        "recorded_at": datetime.now(UTC).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        "book_id": book_id,
                        "detail": detail,
                    }
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(log_entry, ensure_ascii=False) + "\n"
                        )
            except Exception:
                logger.debug(
                    "[BOOK-LOG] failed to mirror discovery event "
                    "to capture-log.jsonl",
                    exc_info=True,
                )

            # Also save partial discovery state to disk for checkpoint/restart
            if payload.get("discovery_state"):
                self._save_discovery_checkpoint(book_id, payload["discovery_state"])

            # ----------------------------------------------------------
            # Empty-chapter detection (Option 3, schema v5).
            #
            # When the userscript emits ``chapter_empty_attempt`` we
            # bump a per-chapter counter; after EMPTY_ATTEMPT_THRESHOLD
            # cross-run attempts the chapter is auto-flagged
            # ``skip_status="auto_empty"``. The userscript then honours
            # the flag and stops re-visiting the empty chapter.
            # ----------------------------------------------------------
            chapter_skip_states: list[dict[str, Any]] = []
            if step == "chapter_empty_attempt" and book_id is not None:
                try:
                    book_dir = self._resolve_book_dir({
                        "book_id": int(book_id),
                        "book_name": detail.get("book_name") or "",
                    })
                    with book_state.book_lock(book_dir):
                        state_data = book_state.load(book_dir)
                        if state_data:
                            ch, just_skipped = book_state.record_empty_attempt(
                                state_data,
                                chapter_id=detail.get("chapter_id"),
                                chapter_number=detail.get("chapter_number"),
                            )
                            if ch is not None:
                                book_state.save(book_dir, state_data)
                                if just_skipped:
                                    # Append a structured skip_marked event.
                                    skip_entry = {
                                        "event_type": "chapter_skip_marked",
                                        "recorded_at": datetime.now(UTC).strftime(
                                            "%Y-%m-%dT%H:%M:%SZ",
                                        ),
                                        "book_id": book_id,
                                        "detail": {
                                            "chapter_id": ch.get("chapter_id"),
                                            "chapter_number": ch.get(
                                                "chapter_number",
                                            ),
                                            "chapter_name": ch.get("name"),
                                            "skip_status": ch.get("skip_status"),
                                            "skip_reason": ch.get("skip_reason"),
                                            "empty_attempts": ch.get(
                                                "empty_attempts", 0,
                                            ),
                                        },
                                    }
                                    with open(
                                        book_dir / "capture-log.jsonl",
                                        "a",
                                        encoding="utf-8",
                                    ) as f:
                                        f.write(
                                            json.dumps(
                                                skip_entry, ensure_ascii=False,
                                            ) + "\n",
                                        )
                                    logger.info(
                                        "[BOOK-SKIP] book=%s chapter=%s flagged "
                                        "auto_empty after %s attempts",
                                        book_id,
                                        ch.get("chapter_number"),
                                        ch.get("empty_attempts"),
                                    )
                            chapter_skip_states = book_state.chapter_skip_states(
                                state_data,
                            )
                except Exception:
                    logger.debug(
                        "[BOOK-SKIP] failed to record empty attempt",
                        exc_info=True,
                    )

            # Always echo the current skip-state map so the userscript can
            # merge it into its in-memory bookDiscovery (the manual
            # `skip-chapter` CLI also flips flags, and the userscript has
            # no other way to find out within a session).
            if not chapter_skip_states and book_id is not None:
                try:
                    book_dir = self._resolve_book_dir({
                        "book_id": int(book_id),
                        "book_name": detail.get("book_name") or "",
                    })
                    state_data = book_state.load(book_dir)
                    if state_data:
                        chapter_skip_states = book_state.chapter_skip_states(
                            state_data,
                        )
                except Exception:
                    pass

            self._send_json(
                200,
                {"status": "ok", "chapter_skip_states": chapter_skip_states},
            )

        def _handle_probe(self) -> None:
            """POST /probe — fire-and-forget capture telemetry sink.

            Single line per puzzle, JSONL-shaped, written to the same
            structured log as everything else. Always 200 — telemetry
            failures must never affect the userscript.
            """
            payload = self._read_json_body() or {}
            stage = payload.get("stage") or "unknown"
            try:
                logger.info(
                    "[PROBE] stage=%s %s",
                    stage,
                    json.dumps(
                        {k: v for k, v in payload.items() if k != "stage"},
                        ensure_ascii=False, sort_keys=True,
                    ),
                )
            except Exception:
                pass
            self._send_json(200, {"status": "ok"})

        def _handle_post_log_event(self) -> None:
            """POST /book/log/event — userscript-side lifecycle event.

            Used for capture-mode lifecycle (paused, resumed, jumped,
            session_break, chapter_skipped) so the per-book
            ``capture-log.jsonl`` reflects the full timeline rather
            than only the moments a puzzle was saved.

            Expected payload::

                {
                    "book_id": 1054,
                    "book_name": "...",            # optional, for dir lookup
                    "event_type": "session_paused",
                    "detail": { ... arbitrary ... }
                }

            Always returns 200 even on failure so a slow logger never
            blocks the userscript's main loop.
            """
            payload = self._read_json_body() or {}
            book_id = payload.get("book_id")
            event_type = payload.get("event_type") or "unknown_event"
            detail = payload.get("detail", {}) or {}

            # Build a unified, scannable log prefix for puzzle-scoped
            # events (skip / retry / lifecycle). Every such line shares
            # the shape: `book=<id> Ch.<n> pos.<n> pid=<n>`. Missing
            # parts are omitted so non-puzzle events stay terse.
            def _puzzle_prefix(d: dict[str, Any]) -> str:
                parts = [f"book={book_id}"]
                ch = d.get("chapter_number")
                if ch is not None:
                    parts.append(f"Ch.{ch}")
                pos = d.get("chapter_position") or d.get("position")
                if pos is not None:
                    parts.append(f"pos.{pos}")
                pid = d.get("pid") or d.get("puzzle_id")
                if pid is not None:
                    parts.append(f"pid={pid}")
                return " ".join(parts)

            if event_type == "puzzle_skipped":
                reason = detail.get("reason") or "unknown"
                ids = detail.get("ids") or {}
                attempts = detail.get("attempts")
                attempts_str = f" attempts={attempts}" if attempts else ""
                human_msg = (
                    f"[CAPTURE-SKIP]  {_puzzle_prefix(detail)} reason={reason}"
                    f"{attempts_str} "
                    f"data={ids.get('dataPid')} settled={ids.get('settledPid')} "
                    f"expected={ids.get('expectedPid')}"
                )
            elif event_type == "puzzle_retry":
                human_msg = (
                    f"[CAPTURE-RETRY] {_puzzle_prefix(detail)} "
                    f"reason={detail.get('reason')} "
                    f"attempt={detail.get('attempt')}"
                )
            elif event_type == "puzzle_dom_missing":
                # Capture-time bulk-prune: a manifest pid that the live
                # chapter listing no longer renders. Persist to book.json
                # via apply_dom_missing so subsequent audits subtract
                # these from `remaining` and the userscript skips them
                # on resume. See book_state.apply_dom_missing for the
                # status priority rules (real captures still win).
                page = detail.get("page")
                visible = detail.get("visible_count")
                reason = detail.get("reason") or "absent_from_listing"
                human_msg = (
                    f"[DOM-MISSING]   {_puzzle_prefix(detail)} "
                    f"reason={reason} "
                    f"page={page} visible={visible}"
                )
            elif event_type == "chapter_mode_skipped":
                # Browser advanced past N already-captured puzzles in
                # the current chapter cursor — not a chapter-level skip.
                # Distinct prefix so it doesn't read like [CHAPTER-SKIP].
                human_msg = (
                    f"[CURSOR-ADVANCE] book={book_id} "
                    f"skipped={detail.get('skipped')} "
                    f"new_index={detail.get('new_index')}"
                )
            elif event_type == "session_paused":
                human_msg = f"[SESSION-PAUSE]  book={book_id}"
            elif event_type == "session_resumed":
                human_msg = f"[SESSION-RESUME] book={book_id}"
            elif event_type == "session_summary":
                captured = detail.get("captured", 0)
                skipped = detail.get("skipped", 0)
                errors = detail.get("errors", 0)
                duration_s = (detail.get("duration_ms", 0) or 0) / 1000
                human_msg = (
                    f"[SESSION-SUMMARY] book={book_id} "
                    f"captured={captured} skipped={skipped} "
                    f"errors={errors} duration={duration_s:.0f}s"
                )
                # Best-effort: kick a corpus inventory refresh so the
                # /inventory snapshot stays current. Throttled and
                # non-blocking; failures are logged by the worker.
                try:
                    from . import inventory as inv_mod
                    inv_mod.maybe_trigger_throttled(state.output_dir)
                except Exception:
                    logger.exception("[INVENTORY] post-session trigger failed")
            else:
                human_msg = f"[BOOK-EVENT]    book={book_id} event={event_type}"
            if state._slog:
                # Strip keys that collide with StructuredLogger.event() positional args.
                safe_detail = {
                    k: v for k, v in detail.items()
                    if k not in {"event_type", "message", "level"}
                }
                state._slog.event(
                    EventType.PROGRESS,
                    human_msg,
                    book_id=book_id,
                    book_event=event_type,
                    **safe_detail,
                )
            else:
                logger.info(human_msg)

            try:
                if book_id is not None:
                    book_dir = self._resolve_book_dir({
                        "book_id": int(book_id),
                        "book_name": payload.get("book_name") or "",
                    })
                    if book_dir.exists():
                        log_path = book_dir / "capture-log.jsonl"
                        log_entry = {
                            "event_type": event_type,
                            "recorded_at": datetime.now(UTC).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            "book_id": book_id,
                            "detail": detail,
                        }
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps(log_entry, ensure_ascii=False) + "\n"
                            )

                        # puzzle_dom_missing also mutates book.json so
                        # subsequent /manifest requests reflect the
                        # prune. Done synchronously here \u2014 the prune
                        # batches are small (\u226410 pids per page) and
                        # write-through keeps the audit-trail honest.
                        if event_type == "puzzle_dom_missing":
                            try:
                                pid = detail.get("pid")
                                if isinstance(pid, int):
                                    with book_state.book_lock(book_dir):
                                        data = book_state.load(book_dir)
                                        book_state.apply_dom_missing(
                                            data,
                                            pid=pid,
                                            chapter_number=detail.get(
                                                "chapter_number",
                                            ),
                                            chapter_position=detail.get(
                                                "chapter_position",
                                            ),
                                            chapter_name=detail.get(
                                                "chapter_name",
                                            ),
                                            reason=detail.get("reason"),
                                        )
                                        book_state.save(book_dir, data)
                            except Exception:
                                logger.warning(
                                    "[DOM-MISSING] failed to persist "
                                    f"book={book_id} pid={detail.get('pid')}",
                                    exc_info=True,
                                )
            except Exception:
                logger.debug(
                    "[BOOK-LOG] failed to write lifecycle event",
                    exc_info=True,
                )

            self._send_json(200, {"status": "ok"})

        def _save_discovery_checkpoint(
            self, book_id: int | None, discovery_state: dict[str, Any]
        ) -> None:
            """Persist partial discovery state into the consolidated book.json."""
            if not book_id:
                return
            books_dir = state.output_dir / "books"
            book_dir = book_state.find_book_dir(books_dir, book_id)
            if book_dir is None:
                book_name = discovery_state.get("book_name", "")
                book_dir = book_state.resolve_book_dir(
                    books_dir, book_id, book_name,
                )
            book_dir.mkdir(parents=True, exist_ok=True)
            with book_state.book_lock(book_dir):
                data = book_state.load(book_dir)
                merged = book_state.merge_discovery_state(data, discovery_state)
                book_state.save(book_dir, merged)

        def _handle_get_book_discovery(self) -> None:
            """GET /book/{id}/discovery — Return existing discovery state.

            Wire format (unchanged for the userscript)::

                { "status": "complete", "manifest": {...} }
                { "status": "partial",  "checkpoint": {...} }
                { "status": "none" }

            All three branches are projected from the consolidated
            ``book.json`` (schema v4).
            """
            m = re.match(r"^/book/(\d+)/discovery$", self.path)
            if not m:
                self._send_json(400, {"error": "Invalid path"})
                return

            book_id = int(m.group(1))
            books_dir = state.output_dir / "books"
            book_dir_path = (
                book_state.find_book_dir(books_dir, book_id)
                if books_dir.exists() else None
            )
            data = book_state.load(book_dir_path) if book_dir_path else {}

            disc_status = (data.get("discovery") or {}).get("status", "none")

            if disc_status == "complete" and data.get("chapters"):
                manifest_data = book_state.project_manifest_view(data)
                all_ids = book_state.all_pids(data)
                stats = data.get("stats") or {}
                known_set = book_state.known_pids(data)
                manifest_data["known_ids"] = sorted(known_set)
                manifest_data["capture_stats"] = {
                    "total": stats.get(
                        "total_positions", len(all_ids),
                    ),
                    "captured": stats.get("captured", 0),
                    "external": stats.get("external", 0),
                    "remaining": stats.get("pending", len(all_ids)),
                }
                self._send_json(200, {
                    "status": "complete",
                    "manifest": manifest_data,
                })
                return

            if disc_status == "in_progress" and data.get("chapters"):
                checkpoint_data = book_state.project_discovery_view(data)
                self._send_json(200, {
                    "status": "partial",
                    "checkpoint": checkpoint_data or {},
                })
                return

            self._send_json(200, {"status": "none"})

        # ----- Inventory endpoints -------------------------------------
        # Read-only snapshot of the corpus dedup view; computed by
        # ``tools.weiqi101.inventory``. All three are GET-only so they
        # can be invoked from the address bar (no curl needed).

        def _handle_get_inventory(self) -> None:
            from . import inventory as inv_mod

            inv = inv_mod.load_inventory(state.output_dir)
            if inv is None:
                running = inv_mod.current_scan_info()
                if running is not None:
                    self._send_json(202, {
                        "status": "scanning",
                        **running,
                        "message": (
                            "No inventory yet; a scan is in flight. "
                            "Retry shortly."
                        ),
                    })
                    return
                self._send_json(404, {
                    "error": "no inventory yet",
                    "hint": "GET /inventory/refresh to generate one",
                })
                return
            self._send_json(200, inv)

        def _handle_inventory_refresh(self) -> None:
            from . import inventory as inv_mod

            result = inv_mod.trigger_async(state.output_dir)
            code = 409 if result["status"] == "already_running" else 202
            self._send_json(code, result)

        def _handle_get_unique_sgf(self) -> None:
            from . import inventory as inv_mod

            path = inv_mod.unique_sgf_path(state.output_dir)
            if not path.exists():
                self._send_json(404, {
                    "error": "no unique-sgf.txt yet",
                    "hint": "GET /inventory/refresh to generate one",
                })
                return
            try:
                body = path.read_bytes()
            except OSError as e:
                self._send_json(500, {"error": f"read failed: {e}"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run_receiver(
    output_dir: Path,
    host: str = RECEIVER_HOST,
    port: int = RECEIVER_PORT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    *,
    match_collections: bool = True,
    resolve_intent: bool = True,
    book_id: int | None = None,
) -> None:
    """Start the local HTTP receiver server.

    Runs until Ctrl+C. Saves checkpoint on shutdown.

    Args:
        book_id: If provided, pre-load this book's puzzle IDs into
            the queue at startup (reads from book-ids.jsonl).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    from .config import get_sgf_dir
    get_sgf_dir(output_dir).mkdir(parents=True, exist_ok=True)

    state = _ReceiverState(
        output_dir,
        batch_size,
        match_collections=match_collections,
        resolve_intent=resolve_intent,
    )

    # Pre-load book queue if requested
    if book_id is not None:
        base_dir = get_output_dir(None)
        result = state.queue.load_book(
            book_id=book_id,
            output_dir=base_dir,
            known_ids=state.known_ids,
        )
        if "error" in result:
            logger.error(f"Failed to load book {book_id}: {result['error']}")
            print(f"Error: {result['error']}")
            print("Continuing without queue. You can load a book via POST /queue/book")
        else:
            state.telemetry.set_book(book_id, result.get("book_name"))
            print(f"  Queue:    Book {book_id} — {result['pending']} pending "
                  f"({result['already_downloaded']} already downloaded)")

    handler_cls = _make_handler(state)
    # ThreadingHTTPServer: each request runs in its own daemon thread so
    # a slow handler (e.g. /capture doing dedup glob + SGF write +
    # checkpoint save) cannot block accept(). Without this, browser
    # retries during a still-processing handler hit the listen backlog
    # and surfaced as `onerror` ("Server unreachable") in the userscript
    # even though /health was fine. Shared state is guarded by
    # _ReceiverState.lock; per-book file writes assume one capture tab
    # at a time (current operational model).
    server = ThreadingHTTPServer((host, port), handler_cls)
    server.daemon_threads = True

    stop = threading.Event()

    def _shutdown(sig: int, frame: object) -> None:
        if stop.is_set():
            return  # Already shutting down, ignore repeated Ctrl+C
        logger.info("Shutting down receiver...")
        stop.set()
        # Run shutdown in a thread so signal handler returns immediately
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, _shutdown)

    logger.info(f"Receiver listening on http://{host}:{port}/")
    logger.info(f"Output: {rel_path(output_dir)}")
    logger.info(f"Known puzzles: {len(state.known_ids)}")
    print(f"\n{'=' * 60}")
    print(f"101weiqi Browser Capture Receiver")
    print(f"{'=' * 60}")
    print(f"  Listening: http://{host}:{port}/")
    print(f"  Output:    {rel_path(output_dir)}")
    print(f"  Known:     {len(state.known_ids)} puzzles")
    print(f"  Endpoints:")
    print(f"    POST /capture       — receive puzzle qqdata")
    print(f"    POST /queue/book    — load book IDs into queue")
    print(f"    POST /queue/ids     — load arbitrary IDs into queue")
    print(f"    GET  /books         — list available books + progress")
    print(f"    GET  /next          — get next puzzle URL from queue")
    print(f"    GET  /queue/status  — queue progress")
    print(f"    GET  /queue/stop    — stop the queue")
    print(f"    GET  /status        — download stats + queue summary")
    print(f"    GET  /telemetry     — detailed event log + timing")
    print(f"    GET  /inventory     — corpus dedup snapshot (JSON)")
    print(f"    GET  /inventory/refresh — kick a background rescan")
    print(f"    GET  /inventory/unique-sgf — unique-pid winners (text)")
    print(f"    GET  /health        — health check")
    print(f"{'=' * 60}")
    print("Press Ctrl+C to stop.\n")

    # Startup hook: generate inventory.json on first start. Subsequent
    # restarts skip this (operator can hit /inventory/refresh on demand).
    try:
        from . import inventory as inv_mod
        startup_result = inv_mod.trigger_on_startup_if_missing(state.output_dir)
        if startup_result.get("status") == "started":
            logger.info(
                "[INVENTORY] background scan started scan_id=%s",
                startup_result.get("scan_id"),
            )
    except Exception:
        logger.exception("[INVENTORY] startup trigger failed")

    try:
        server.serve_forever()
    finally:
        sort_index(output_dir)
        save_checkpoint(state.checkpoint, output_dir)
        # Final telemetry summary
        telem = state.telemetry.summary()
        logger.info(
            f"[TELEM] Session complete: "
            f"{telem['counts']} total={telem['total_processed']} "
            f"avg={telem['avg_duration_ms']}ms"
        )
        print(f"\nFinal stats: {state.stats}")
        print(f"Queue: {state.queue.status()}")
        logger.info(f"Receiver stopped. Stats: {state.stats}")
