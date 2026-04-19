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

import json
import logging
import signal
import threading
import time
from collections import deque
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from . import _local_collections_mapping, _local_intent_mapping
from .checkpoint import WeiQiCheckpoint, load_checkpoint, save_checkpoint
from .complexity import compute_complexity
from .config import (
    DEFAULT_BATCH_SIZE,
    RECEIVER_HOST,
    RECEIVER_MAX_BODY,
    RECEIVER_PORT,
    get_output_dir,
)
from .index import load_puzzle_ids, sort_index
from .models import PuzzleData
from .storage import parse_qday_url, save_puzzle, save_puzzle_qday

from tools.core.logging import EventType, StructuredLogger
from tools.core.paths import rel_path
from .validator import validate_puzzle

logger = logging.getLogger("101weiqi.receiver")


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
) -> dict[str, Any]:
    """Process a single qqdata payload through the full pipeline.

    This is the same logic as orchestrator._process_html minus the HTML
    extraction step (the browser already extracted qqdata for us).

    If the URL is a /qday/ URL, the puzzle is saved under qday/YYYY/MM/DD-N.sgf
    instead of the normal batch directory.

    Returns:
        Dict with keys: status ("ok"|"skipped"|"error"), puzzle_id, message
    """
    # Parse
    try:
        puzzle = PuzzleData.from_qqdata(qqdata)
    except Exception as e:
        return {"status": "error", "puzzle_id": None, "message": f"parse: {e}"}

    # Dedup
    if puzzle.puzzle_id in known_ids:
        return {"status": "skipped", "puzzle_id": puzzle.puzzle_id, "message": "duplicate"}

    # Validate
    error = validate_puzzle(puzzle)
    if error:
        return {"status": "error", "puzzle_id": puzzle.puzzle_id, "message": f"validation: {error}"}

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
        if qday_info:
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
        return {"status": "error", "puzzle_id": puzzle.puzzle_id, "message": f"save: {e}"}


# ---------------------------------------------------------------------------
# Telemetry — detailed per-event tracking with timestamps
# ---------------------------------------------------------------------------

class _TelemetryEvent:
    """A single telemetry event."""

    __slots__ = ("ts", "puzzle_id", "status", "message", "duration_ms", "url")

    def __init__(
        self,
        puzzle_id: int | None,
        status: str,
        message: str,
        duration_ms: float,
        url: str | None = None,
    ):
        self.ts = datetime.now(UTC).isoformat()
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

        if status == "ok":
            meta_str = self._format_meta_str(meta)
            safe_meta = self._sanitize_meta_for_slog(meta)
            human_msg = (
                f"[TELEM] #{total} OK puzzle={puzzle_id} "
                f"duration={duration_ms:.0f}ms path={message}{meta_str}"
            )
            if self._slog:
                self._slog.event(
                    EventType.ITEM_SAVE,
                    human_msg,
                    puzzle_id=puzzle_id,
                    duration_ms=round(duration_ms, 1),
                    path=message,
                    **safe_meta,
                )
            else:
                logger.info(human_msg)
        elif status == "skipped":
            human_msg = (
                f"[TELEM] #{total} SKIP puzzle={puzzle_id} "
                f"reason={message} duration={duration_ms:.0f}ms"
            )
            if self._slog:
                self._slog.event(
                    EventType.ITEM_SKIP,
                    human_msg,
                    puzzle_id=puzzle_id,
                    reason=message,
                    duration_ms=round(duration_ms, 1),
                )
            else:
                logger.info(human_msg)
        else:
            human_msg = (
                f"[TELEM] #{total} ERROR puzzle={puzzle_id} "
                f"error={message} duration={duration_ms:.0f}ms"
            )
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

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = sum(self._counts.values())
            avg_ms = (self._total_duration_ms / total) if total > 0 else 0
            return {
                "started_at": self._started_at,
                "book_id": self._book_id,
                "book_name": self._book_name,
                "counts": dict(self._counts),
                "total_processed": total,
                "avg_duration_ms": round(avg_ms, 1),
                "last_ok_at": self._last_ok_at,
                "last_error_at": self._last_error_at,
                "recent_errors": list(self._error_details),
                "recent_events": [e.to_dict() for e in self._events],
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
        """Mark a puzzle ID as visited (called after capture). Informational only."""
        with self._lock:
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
        self.queue = PuzzleQueue()

    def process(self, qqdata: dict, url: str | None = None, page_books: list[dict] | None = None) -> dict:
        t0 = time.monotonic()
        with self.lock:
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
            )
            status = result["status"]
            self.stats[status] = self.stats.get(status, 0) + 1
        duration_ms = (time.monotonic() - t0) * 1000
        self.telemetry.record(
            puzzle_id=result.get("puzzle_id"),
            status=status,
            message=result.get("message", ""),
            duration_ms=duration_ms,
            url=url,
            meta=result.get("meta"),
        )
        # Mark in queue if active
        pid = result.get("puzzle_id")
        if pid is not None:
            self.queue.mark_done(pid)
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
                self._send_json(413, {"error": "payload too large"})
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

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "service": "weiqi101-receiver"})
            elif self.path == "/status":
                self._send_json(200, {
                    "stats": state.stats,
                    "known_count": len(state.known_ids),
                    "checkpoint_downloaded": state.checkpoint.puzzles_downloaded,
                    "queue": state.queue.status(),
                })
            elif self.path == "/next":
                result = state.queue.next_url()
                self._send_json(200, result)
            elif self.path == "/queue/status":
                self._send_json(200, state.queue.status())
            elif self.path == "/queue/stop":
                result = state.queue.stop()
                logger.info(f"[QUEUE] Stopped: {result}")
                self._send_json(200, result)
            elif self.path == "/telemetry":
                self._send_json(200, state.telemetry.summary())
            elif self.path == "/books":
                self._handle_list_books()
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path == "/capture":
                self._handle_capture()
            elif self.path == "/queue/book":
                self._handle_queue_book()
            elif self.path == "/queue/ids":
                self._handle_queue_ids()
            else:
                self._send_json(404, {"error": "not found"})

        def _handle_capture(self) -> None:
            payload = self._read_json_body()
            if payload is None:
                return

            # Accept either {qqdata: {...}} or raw qqdata dict
            qqdata = payload.get("qqdata") or payload
            if not isinstance(qqdata, dict):
                self._send_json(400, {"error": "qqdata must be a JSON object"})
                return

            url = payload.get("url")
            page_books = payload.get("_page_books")
            result = state.process(qqdata, url=url, page_books=page_books)
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

            self._send_json(code, result)

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
            result = state.queue.load_book(
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
            result = state.queue.load_ids(
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
            """GET /books — List available books from book-ids.jsonl with download progress."""
            jsonl_path = state.output_dir / "book-ids.jsonl"
            if not jsonl_path.exists():
                self._send_json(200, {
                    "books": [],
                    "message": "No book-ids.jsonl found. Run: python -m tools.weiqi101 discover-book-ids --book-id N",
                })
                return

            books = []
            with jsonl_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    book_id = int(entry.get("book_id", 0))

                    # Count total puzzle IDs
                    chapters = entry.get("chapters")
                    if chapters:
                        all_ids = []
                        for ch in chapters:
                            all_ids.extend(ch.get("puzzle_ids", []))
                    else:
                        all_ids = entry.get("puzzle_ids", [])

                    # Count how many are already downloaded
                    done = sum(1 for pid in all_ids if pid in state.known_ids)

                    books.append({
                        "book_id": book_id,
                        "name": entry.get("book_name_en") or entry.get("book_name", ""),
                        "name_cn": entry.get("book_name", ""),
                        "total": len(all_ids),
                        "downloaded": done,
                        "remaining": len(all_ids) - done,
                        "complete": done == len(all_ids) and len(all_ids) > 0,
                        "difficulty": entry.get("difficulty", ""),
                    })

            # Sort: incomplete first, then by remaining desc
            books.sort(key=lambda b: (b["complete"], -b["remaining"]))

            logger.info(f"[BOOKS] Listed {len(books)} books from book-ids.jsonl")
            self._send_json(200, {"books": books})

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
    server = HTTPServer((host, port), handler_cls)

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
    logger.info(f"Output: {output_dir}")
    logger.info(f"Known puzzles: {len(state.known_ids)}")
    print(f"\n{'=' * 60}")
    print(f"101weiqi Browser Capture Receiver")
    print(f"{'=' * 60}")
    print(f"  Listening: http://{host}:{port}/")
    print(f"  Output:    {output_dir}")
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
    print(f"    GET  /health        — health check")
    print(f"{'=' * 60}")
    print("Press Ctrl+C to stop.\n")

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
