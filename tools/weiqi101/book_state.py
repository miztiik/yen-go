"""
Single authoritative per-book state file: ``book.json`` (schema v4).

This module replaces three files that previously lived side-by-side
in each ``books/{id}-{slug}/`` directory:

  - ``manifest.json``               (chapter list + puzzle IDs)
  - ``book-index.json``             (per-position status + counts)
  - ``discovery_checkpoint.json``   (in-progress discovery state)

Everything except the append-only ``capture-log.jsonl`` is now stored
in ``book.json``. The receiver, indexer, and CLI tools all read and
write through this module.

Schema (v4)::

    {
      "schema_version": 4,
      "book_id": int,
      "book_name": str,                # English (display) form
      "book_name_raw": str,            # original CJK
      "book_name_visible": str | null, # browser-translated label, if any
      "book_name_english": str | null,
      "book_slug": str | null,
      "book_difficulty": str | null,

      "discovery": {
        "status": "in_progress" | "complete" | "none",
        "phase":  "chapters" | "chapter_puzzles" | "done" | null,
        "current_chapter_idx": int,
        "current_page": int,
        "started_at": iso | null,
        "completed_at": iso | null
      },

      # Chapters: full discovery records merged with per-chapter index counts.
      # Replaces both manifest.chapters[] and book-index.chapters[].
      "chapters": [
        {
          "chapter_id": int, "chapter_number": int,
          "name": str, "name_raw": str, "name_english": str | null,
          "name_label_source": str | null,
                    # Counts (rolled in from former book-index.chapters[]):
                    "total": int, "captured": int, "external": int, "pending": int,
                    # Legacy optional metadata: per-chapter qindex map. Disabled by
                    # default and only persisted when YENGO_WEIQI101_ENABLE_PUZZLE_POSITIONS=1.
                    "puzzle_positions": {pid_str: pos_int},
                    "scraped_pages": [...], "max_page_seen": int,
                    "parent_chapter_id": int | null, "sections": [...],
                    "puzzle_ids": [...]
        }
      ],

      # Per-position status (was book-index.positions[]).
      "positions": [...],

      "stats": {
        "total_positions": int,
        "captured": int, "external": int, "pending": int,
        "last_captured_position": int,
        "last_updated": iso,
        "puzzle_counts": {
          "chapter_total": int,
          "chapter_unique": int,
          "chapters": int
        }
      },

      "updated_at": iso
    }

The wire format consumed by the userscript (``GET /book/{id}/manifest``,
``GET /book/{id}/discovery``) is unchanged — projection helpers in this
module reconstitute the legacy shapes from ``book.json``.
"""

from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("101weiqi.book_state")

SCHEMA_VERSION = 5
PUZZLE_POSITIONS_ENV_VAR = "YENGO_WEIQI101_ENABLE_PUZZLE_POSITIONS"

CHAPTER_KEY_ORDER = (
    "chapter_id",
    "chapter_number",
    "name",
    "declared_count",
    "skip_status",
    "skip_reason",
    "total",
    "captured",
    "external",
    "pending",
    "site_chapter_number",
    "puzzle_positions",
    "scraped_pages",
    "max_page_seen",
    "name_raw",
    "name_english",
    "name_label_source",
    "skip_marked_at",
    "empty_attempts",
    "last_attempt_at",
    "parent_chapter_id",
    "sections",
    "puzzle_ids",
)

# How many independent empty page-1 renders are tolerated before a chapter
# is auto-flagged as `skip_status="auto_empty"`. The userscript
# emits the empty-attempt event; the receiver enforces this counter.
EMPTY_ATTEMPT_THRESHOLD = 3

# Minimum gap between two events that may both increment the counter.
# Without this, a single broken session could burn a chapter in one go
# (the userscript may retry the same empty page several times within
# seconds). 5 minutes is enough to require a fresh navigation cycle.
EMPTY_ATTEMPT_COOLDOWN_SECONDS = 5 * 60
BOOK_STATE_FILENAME = "book.json"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _puzzle_positions_enabled() -> bool:
    """Return whether legacy chapter qindex maps should be persisted."""
    raw = os.getenv(PUZZLE_POSITIONS_ENV_VAR, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Disk I/O
# ---------------------------------------------------------------------------

def find_book_dir(books_root: Path, book_id: int) -> Path | None:
    """Return the ``books/{id}-*/`` directory for a given book, if it exists."""
    if not books_root.is_dir():
        return None
    prefix = f"{book_id}-"
    for d in books_root.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            return d
    return None


def resolve_book_dir(
    books_root: Path, book_id: int, book_name: str = "",
) -> Path:
    """Find the existing book dir, or compute the new path (NOT created)."""
    existing = find_book_dir(books_root, book_id)
    if existing is not None:
        return existing
    slug = re.sub(
        r"[^a-z0-9\u4e00-\u9fff]+", "-", book_name.lower(),
    ).strip("-") or "unknown"
    return books_root / f"{book_id}-{slug}"


def load(book_dir: Path) -> dict[str, Any]:
    """Load ``book.json``; return ``{}`` if missing or unreadable.

    A ``UnicodeDecodeError`` indicates a torn write — typically two
    threads racing on the same tmp file (see ``book_lock`` /
    https://docs.python.org/3/library/os.html#os.replace). The corrupt
    file is rotated aside as ``book.json.corrupt-<utc-iso>`` so an
    operator (or an offline rebuilder) can inspect or recover it,
    and ``{}`` is returned. Returning ``{}`` here would otherwise be
    silent total state loss.

    Read-after-write consistency: if a background ``save_async`` has
    been queued but not yet flushed to disk, returns a deep copy of
    the in-memory snapshot. Disk reads are skipped in that case so
    callers never observe a stale on-disk version.
    """
    cached = _peek_pending(book_dir)
    if cached is not None:
        return copy.deepcopy(cached)
    path = book_dir / BOOK_STATE_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        quarantine = path.with_name(f"{BOOK_STATE_FILENAME}.corrupt-{ts}")
        try:
            path.replace(quarantine)
            logger.error(
                "[BOOK-STATE] %s is corrupt (%s); quarantined to %s. "
                "Returning empty state — caller will rebuild.",
                path, type(e).__name__, quarantine.name,
            )
        except OSError as move_err:
            logger.error(
                "[BOOK-STATE] %s is corrupt (%s) but quarantine failed: %s. "
                "Returning empty state.",
                path, type(e).__name__, move_err,
            )
        return {}
    except OSError:
        return {}


def save(book_dir: Path, data: dict[str, Any]) -> None:
    """Atomically write ``book.json`` with compact-positions formatting.

    Uses a tmp filename that is unique per (pid, thread) so that even
    in the absence of a per-book lock, two writers cannot share the
    same tmp file and produce a torn replace target. Callers in
    multi-threaded contexts (e.g. the HTTP receiver) MUST also wrap
    the load → mutate → save sequence in ``with book_lock(book_dir):``
    to prevent lost-update races.
    """
    book_dir.mkdir(parents=True, exist_ok=True)
    data.setdefault("schema_version", SCHEMA_VERSION)
    data["updated_at"] = _now_iso()
    text = _serialize(data)
    path = book_dir / BOOK_STATE_FILENAME
    tmp = path.with_name(
        f"{BOOK_STATE_FILENAME}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    finally:
        # If write_text succeeded but replace failed, leave tmp behind for
        # diagnostics. If replace succeeded, tmp no longer exists.
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Per-book write lock
# ---------------------------------------------------------------------------
#
# ``book.json`` is mutated by multiple HTTP handlers running concurrently
# under ThreadingHTTPServer (see receiver.py). Without a lock, two
# threads can interleave their load → mutate → save sequences and:
#   1. Tear writes by sharing a tmp filename (now mitigated by unique
#      tmp names in ``save()``), AND
#   2. Lose updates: both load the same state, mutate disjoint parts,
#      then both save — second writer silently drops the first's work.
#
# A per-book ``threading.Lock`` keyed on the book directory closes both
# windows. Acquired via ``with book_lock(book_dir):`` around the full
# RMW sequence. The registry itself is guarded by a coarse meta-lock,
# but contention there is negligible (one map lookup per request).
#
# Single-process scope is intentional: the receiver is single-process
# by design. Cross-process coordination would need flock/portalocker.

_locks_guard = threading.Lock()
_book_locks: dict[Path, threading.Lock] = {}


def _lock_for(book_dir: Path) -> threading.Lock:
    key = book_dir.resolve() if book_dir.is_absolute() else book_dir
    with _locks_guard:
        lock = _book_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _book_locks[key] = lock
        return lock


@contextmanager
def book_lock(book_dir: Path) -> Iterator[None]:
    """Serialize all read-modify-write access to ``book_dir/book.json``.

    Wrap the FULL ``load → mutate → save`` sequence in this context
    manager. Read-only ``load()`` calls do not require the lock
    (``os.replace`` makes the swap atomic at the filesystem level), but
    nothing breaks if you take it.
    """
    lock = _lock_for(book_dir)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# Background save (added 2026-05-02)
# ---------------------------------------------------------------------------
#
# The HTTP capture handler holds the user-visible request thread for
# the entire ``load → apply_capture → save`` sequence. The disk save
# (atomic tmp+rename) is the largest blocking step on that path —
# typically 50-200 ms, but spikes higher under disk contention. Moving
# the write to a per-book worker thread lets the handler return ~one
# RTT sooner without risking lost-update or read-after-write bugs:
#
#   - ``save_async`` deep-copies the caller's dict so background
#     serialization can't race with caller-side mutation.
#   - The cached snapshot is the source of truth until the disk write
#     lands, so ``load()`` returns it (deep-copied) when present.
#   - A single-worker executor PER BOOK preserves write ordering for
#     that book; different books proceed in parallel.
#   - ``flush(book_dir)`` blocks for callers that need on-disk state
#     (e.g. external tooling reading book.json directly).

_save_executors_guard = threading.Lock()
_save_executors: dict[Path, concurrent.futures.ThreadPoolExecutor] = {}
_pending_state: dict[Path, dict[str, Any]] = {}
_pending_futures: dict[Path, list[concurrent.futures.Future]] = {}


def _normkey(book_dir: Path) -> Path:
    return book_dir.resolve() if book_dir.is_absolute() else book_dir


def _executor_for(book_dir: Path) -> concurrent.futures.ThreadPoolExecutor:
    key = _normkey(book_dir)
    with _save_executors_guard:
        ex = _save_executors.get(key)
        if ex is None:
            ex = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"book-save-{key.name}",
            )
            _save_executors[key] = ex
        return ex


def _peek_pending(book_dir: Path) -> dict[str, Any] | None:
    key = _normkey(book_dir)
    with _save_executors_guard:
        return _pending_state.get(key)


def save_async(book_dir: Path, data: dict[str, Any]) -> concurrent.futures.Future:
    """Queue ``book.json`` write on a per-book worker thread.

    A deep copy is taken immediately so the caller can keep mutating
    the input dict without affecting serialization. The snapshot is
    cached so subsequent ``load(book_dir)`` calls observe it before
    the disk write lands.
    """
    key = _normkey(book_dir)
    snapshot = copy.deepcopy(data)
    with _save_executors_guard:
        _pending_state[key] = snapshot
        _pending_futures.setdefault(key, [])
    ex = _executor_for(book_dir)
    fut = ex.submit(_save_and_clear, book_dir, snapshot)
    with _save_executors_guard:
        _pending_futures[key].append(fut)
    return fut


def _save_and_clear(book_dir: Path, snapshot: dict[str, Any]) -> None:
    try:
        save(book_dir, snapshot)
    except Exception:
        logger.warning("[BOOK-STATE] background save failed", exc_info=True)
    finally:
        key = _normkey(book_dir)
        with _save_executors_guard:
            if _pending_state.get(key) is snapshot:
                _pending_state.pop(key, None)
            _pending_futures[key] = [
                f for f in _pending_futures.get(key, []) if not f.done()
            ]


def flush(book_dir: Path, *, timeout: float = 10.0) -> None:
    """Block until queued saves for this book complete."""
    key = _normkey(book_dir)
    with _save_executors_guard:
        futures = list(_pending_futures.get(key, []))
    for f in futures:
        try:
            f.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logger.warning(
                "[BOOK-STATE] flush timeout for %s after %.1fs",
                book_dir, timeout,
            )
        except Exception:
            logger.warning(
                "[BOOK-STATE] background save raised", exc_info=True,
            )


def _serialize(data: dict[str, Any]) -> str:
    """Pretty JSON with one-line-per-chapter and one-line-per-position.

    Both ``chapters`` and ``positions`` are rendered as compact single-line
    JSON entries inside their arrays. This keeps diffs scannable (one line
    changes per chapter or per position) without ballooning the file
    vertically as books grow.
    """
    raw_chapters = data.pop("chapters", [])
    chapters = [
        _normalize_chapter(ch) if isinstance(ch, dict) else ch
        for ch in raw_chapters
    ]
    positions = data.pop("positions", [])
    try:
        body = json.dumps(data, ensure_ascii=False, indent=2).rstrip()
        assert body.endswith("}"), "expected trailing brace from json.dumps"
        body = body[:-1].rstrip()
        if chapters:
            ch_lines = [
                "    " + json.dumps(c, ensure_ascii=False) for c in chapters
            ]
            chapters_block = (
                '  "chapters": [\n' + ",\n".join(ch_lines) + "\n  ]"
            )
        else:
            chapters_block = '  "chapters": []'
        if positions:
            pos_lines = [
                "    " + json.dumps(p, ensure_ascii=False) for p in positions
            ]
            positions_block = (
                '  "positions": [\n' + ",\n".join(pos_lines) + "\n  ]"
            )
        else:
            positions_block = '  "positions": []'
        return (
            body + ",\n" + chapters_block + ",\n" + positions_block + "\n}\n"
        )
    finally:
        # Always restore — caller's dict isn't meant to be mutated.
        data["chapters"] = raw_chapters
        data["positions"] = positions


# ---------------------------------------------------------------------------
# Section helpers (read-modify-write convenience)
# ---------------------------------------------------------------------------

def initialize(
    book_id: int,
    book_name: str = "",
    *,
    book_name_raw: str = "",
    book_name_english: str | None = None,
    book_name_visible: str | None = None,
    book_slug: str | None = None,
    book_difficulty: str | None = None,
) -> dict[str, Any]:
    """Build a fresh book.json skeleton for a brand-new book directory."""
    return {
        "schema_version": SCHEMA_VERSION,
        "book_id": book_id,
        "book_name": book_name,
        "book_name_raw": book_name_raw or book_name,
        "book_name_visible": book_name_visible,
        "book_name_english": book_name_english,
        "book_slug": book_slug,
        "book_difficulty": book_difficulty,
        "discovery": {
            "status": "none",
            "phase": None,
            "current_chapter_idx": 0,
            "current_page": 1,
            "started_at": None,
            "completed_at": None,
        },
        "chapters": [],
        "positions": [],
        "stats": {
            "total_positions": 0,
            "captured": 0,
            "external": 0,
            "pending": 0,
            "last_captured_position": 0,
            "last_updated": _now_iso(),
            "puzzle_counts": {
                "chapter_total": 0,
                "chapter_unique": 0,
                "chapters": 0,
            },
        },
        "updated_at": _now_iso(),
    }


def _normalize_chapter(ch: dict[str, Any]) -> dict[str, Any]:
    """Sort puzzle_positions by value and ensure forward-compat slots exist."""
    out = dict(ch)
    pp = ch.get("puzzle_positions") or {}
    if _puzzle_positions_enabled():
        try:
            out["puzzle_positions"] = {
                pid: int(pos)
                for pid, pos in sorted(pp.items(), key=lambda kv: int(kv[1]))
            }
        except (TypeError, ValueError):
            out["puzzle_positions"] = dict(pp)
    else:
        out.pop("puzzle_positions", None)
    out.setdefault("parent_chapter_id", None)
    out.setdefault("sections", [])
    out.setdefault("scraped_pages", [])
    out.setdefault("max_page_seen", 0)
    out.setdefault("total", len(out.get("puzzle_ids", [])))
    out.setdefault("captured", 0)
    out.setdefault("external", 0)
    out.setdefault("pending", out["total"])
    # Skip-state slots (schema v5). Forward-compat: chapters serialized
    # under v4 simply default to "never skipped" / 0 attempts.
    out.setdefault("skip_status", None)         # None | "auto_empty" | "manual"
    out.setdefault("skip_reason", None)         # freeform string
    out.setdefault("skip_marked_at", None)      # ISO8601
    out.setdefault("empty_attempts", 0)         # int
    out.setdefault("last_attempt_at", None)     # ISO8601

    ordered: dict[str, Any] = {}
    for key in CHAPTER_KEY_ORDER:
        if key == "puzzle_ids":
            continue
        if key in out:
            ordered[key] = out[key]

    for key, value in out.items():
        if key not in ordered and key != "puzzle_ids":
            ordered[key] = value

    if "puzzle_ids" in out:
        ordered["puzzle_ids"] = out["puzzle_ids"]
    return ordered


def merge_discovery_state(
    data: dict[str, Any], discovery_state: dict[str, Any],
) -> dict[str, Any]:
    """Merge an in-progress discovery checkpoint into ``data``.

    The userscript posts a flat checkpoint with chapter records and
    progress counters. We project it into the ``discovery`` section
    plus ``chapters`` / book-level identity fields.
    """
    out = dict(data) if data else initialize(
        discovery_state.get("book_id", 0),
        discovery_state.get("book_name", ""),
    )

    # Identity
    if discovery_state.get("book_id") is not None:
        out["book_id"] = discovery_state["book_id"]
    if discovery_state.get("book_name"):
        out.setdefault("book_name", discovery_state["book_name"])
        out.setdefault("book_name_raw", discovery_state["book_name"])
    if discovery_state.get("difficulty"):
        out["book_difficulty"] = discovery_state["difficulty"]

    # Discovery progress section
    disc = dict(out.get("discovery") or {})
    phase = discovery_state.get("phase")
    disc["phase"] = phase
    disc["current_chapter_idx"] = discovery_state.get(
        "current_chapter_idx", disc.get("current_chapter_idx", 0),
    )
    disc["current_page"] = discovery_state.get(
        "current_page", disc.get("current_page", 1),
    )
    if discovery_state.get("started_at") and not disc.get("started_at"):
        disc["started_at"] = discovery_state["started_at"]
    disc["status"] = "in_progress" if phase != "done" else "complete"
    if disc["status"] == "complete" and not disc.get("completed_at"):
        disc["completed_at"] = _now_iso()
    out["discovery"] = disc

    # Chapter records — replace wholesale, the userscript always sends
    # the full list (it accumulates client-side). Server-managed skip
    # fields are NOT in the userscript payload; preserve them by
    # carrying forward from the previous on-disk record (matched by
    # chapter_id).
    prior_skip_by_id: dict[Any, dict[str, Any]] = {}
    for prev in (data or {}).get("chapters") or []:
        cid = prev.get("chapter_id")
        if cid is None:
            continue
        prior_skip_by_id[cid] = {
            "skip_status": prev.get("skip_status"),
            "skip_reason": prev.get("skip_reason"),
            "skip_marked_at": prev.get("skip_marked_at"),
            "empty_attempts": prev.get("empty_attempts", 0),
            "last_attempt_at": prev.get("last_attempt_at"),
        }

    chapters_in = discovery_state.get("chapters") or []
    merged_chapters = []
    for raw in chapters_in:
        if not isinstance(raw, dict):
            continue
        cid = raw.get("chapter_id")
        if cid in prior_skip_by_id:
            # Don't let the client clobber server-managed skip state.
            for k, v in prior_skip_by_id[cid].items():
                raw.setdefault(k, v)
                if v is not None or k == "empty_attempts":
                    raw[k] = v
        merged_chapters.append(_normalize_chapter(raw))
    out["chapters"] = merged_chapters

    return out


# -- Skip-state helpers (schema v5) -----------------------------------

def _find_chapter(
    data: dict[str, Any], *, chapter_id: Any = None, chapter_number: Any = None,
) -> dict[str, Any] | None:
    """Locate a chapter dict by id or 1-based chapter_number."""
    for ch in data.get("chapters") or []:
        if chapter_id is not None and ch.get("chapter_id") == chapter_id:
            return ch
        if (
            chapter_number is not None
            and ch.get("chapter_number") == chapter_number
        ):
            return ch
    return None


def mark_skip(
    data: dict[str, Any],
    *,
    chapter_id: Any = None,
    chapter_number: Any = None,
    status: str = "manual",
    reason: str | None = None,
) -> dict[str, Any] | None:
    """Flag a chapter as skipped. Returns the mutated chapter dict or None.

    ``status`` should be ``"manual"`` or ``"auto_empty"``.
    """
    if status not in ("manual", "auto_empty"):
        raise ValueError(f"invalid skip status: {status!r}")
    ch = _find_chapter(
        data, chapter_id=chapter_id, chapter_number=chapter_number,
    )
    if ch is None:
        return None
    ch["skip_status"] = status
    ch["skip_reason"] = reason
    ch["skip_marked_at"] = _now_iso()
    return ch


def clear_skip(
    data: dict[str, Any],
    *,
    chapter_id: Any = None,
    chapter_number: Any = None,
) -> dict[str, Any] | None:
    """Clear the skip flag and reset the empty-attempt counter."""
    ch = _find_chapter(
        data, chapter_id=chapter_id, chapter_number=chapter_number,
    )
    if ch is None:
        return None
    ch["skip_status"] = None
    ch["skip_reason"] = None
    ch["skip_marked_at"] = None
    ch["empty_attempts"] = 0
    ch["last_attempt_at"] = None
    return ch


def record_empty_attempt(
    data: dict[str, Any],
    *,
    chapter_id: Any = None,
    chapter_number: Any = None,
    threshold: int = EMPTY_ATTEMPT_THRESHOLD,
    cooldown_seconds: int = EMPTY_ATTEMPT_COOLDOWN_SECONDS,
) -> tuple[dict[str, Any] | None, bool]:
    """Increment the empty-attempt counter for a chapter.

    The cooldown guard prevents a single bad browser session from
    burning a chapter: increments closer than ``cooldown_seconds`` to
    the previous one are recorded but do NOT bump the counter.

    Returns ``(chapter_dict, just_auto_skipped)``. ``just_auto_skipped``
    is True only on the transition from "not skipped" to "auto_empty",
    so callers can emit a one-shot ``chapter_skip_marked`` event.
    """
    ch = _find_chapter(
        data, chapter_id=chapter_id, chapter_number=chapter_number,
    )
    if ch is None:
        return None, False

    now = datetime.now(UTC)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    last = ch.get("last_attempt_at")
    bump = True
    if last:
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC,
            )
            if (now - last_dt).total_seconds() < cooldown_seconds:
                bump = False
        except ValueError:
            pass  # malformed timestamp — count this attempt

    ch["last_attempt_at"] = now_iso
    if not bump:
        return ch, False

    ch["empty_attempts"] = int(ch.get("empty_attempts", 0)) + 1
    just_skipped = False
    if (
        ch["empty_attempts"] >= threshold
        and ch.get("skip_status") is None
    ):
        ch["skip_status"] = "auto_empty"
        ch["skip_reason"] = (
            f"auto: {ch['empty_attempts']} empty page-1 renders"
        )
        ch["skip_marked_at"] = now_iso
        just_skipped = True
    return ch, just_skipped


def chapter_skip_states(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Compact list of per-chapter skip state for echoing to the userscript."""
    out = []
    for ch in data.get("chapters") or []:
        out.append({
            "chapter_id": ch.get("chapter_id"),
            "chapter_number": ch.get("chapter_number"),
            "skip_status": ch.get("skip_status"),
            "skip_reason": ch.get("skip_reason"),
            "empty_attempts": ch.get("empty_attempts", 0),
        })
    return out


def project_manifest_view(data: dict[str, Any]) -> dict[str, Any]:
    """Return the dict shape the userscript expects from ``/book/manifest``.

    Mirrors the legacy ``manifest.json`` layout (the wire format must
    not change), built from the consolidated ``book.json``.
    """
    if not data:
        return {}
    out = {
        "book_id": data.get("book_id"),
        "book_name": data.get("book_name"),
        "book_name_raw": data.get("book_name_raw"),
        "book_name_visible": data.get("book_name_visible"),
        "book_name_english": data.get("book_name_english"),
        "book_slug": data.get("book_slug"),
        "book_difficulty": data.get("book_difficulty"),
        "chapters": [
            {k: v for k, v in ch.items()
             if k not in {"total", "captured", "external", "pending"}}
            for ch in data.get("chapters", [])
        ],
        "discovered_at": (data.get("discovery") or {}).get("completed_at"),
    }
    return out


def project_discovery_view(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return the legacy ``discovery_checkpoint.json`` shape for the userscript.

    Returns ``None`` when discovery has never been started for the book.
    """
    if not data:
        return None
    disc = data.get("discovery") or {}
    if not disc or disc.get("status") == "none":
        return None
    return {
        "book_id": data.get("book_id"),
        "book_name": data.get("book_name"),
        "difficulty": data.get("book_difficulty"),
        "phase": disc.get("phase"),
        "current_chapter_idx": disc.get("current_chapter_idx", 0),
        "current_page": disc.get("current_page", 1),
        "started_at": disc.get("started_at"),
        "chapters": data.get("chapters", []),
    }


def known_pids(data: dict[str, Any]) -> set[int]:
    """Pids already captured locally, known via external/global routes, OR
    flagged as ``dom_missing`` (manifest entries the live chapter listing
    no longer exposes).

    Used to seed the userscript's resume-skip set so we don't keep
    re-attempting upstream-deleted puzzles. The capture-vs-dom_missing
    breakdown is visible separately via :func:`dom_missing_pids` and the
    chapter audit.
    """
    out: set[int] = set()
    for pos in data.get("positions") or []:
        if pos.get("status") in ("captured", "external", "dom_missing"):
            pid = pos.get("pid")
            if isinstance(pid, int):
                out.add(pid)
    return out


def dom_missing_pids(data: dict[str, Any]) -> set[int]:
    """Pids the live site no longer renders (recorded by capture-time
    DOM bulk-prune). Strict subset of :func:`known_pids` — these are
    counted separately in audit so operators can see that ``remaining``
    really means ``remaining_capturable``.
    """
    out: set[int] = set()
    for pos in data.get("positions") or []:
        if pos.get("status") == "dom_missing":
            pid = pos.get("pid")
            if isinstance(pid, int):
                out.add(pid)
    return out


def all_pids(data: dict[str, Any]) -> set[int]:
    """Every pid the book knows about (from chapter puzzle_ids)."""
    out: set[int] = set()
    for ch in data.get("chapters") or []:
        for pid in ch.get("puzzle_ids", []) or []:
            if isinstance(pid, int):
                out.add(pid)
    return out


# ---------------------------------------------------------------------------
# Pid-keyed positions[] helpers (schema v5 invariant)
# ---------------------------------------------------------------------------
#
# `positions[]` MUST contain at most one entry per pid. `pid` is the
# natural key; `pos` is a recomputable view (sequential 1..N derived
# from chapter ordering). Capture/external/pending status is keyed by
# pid, so upstream chapter reorderings do not corrupt local state.
#
# Status priority (highest wins on dedup): captured > external > pending.

# Status priority for dedupe / carry-forward. Higher wins.
#   captured     — SGF on disk in this book
#   external     — SGF on disk in some other book (cross-book dedup)
#   dom_missing  — manifest entry that the live chapter listing doesn't
#                  render (likely deleted upstream). Treated as terminal
#                  for capture purposes (don't keep retrying), but a
#                  later real capture will overwrite it.
#   pending      — default; not yet attempted.
_STATUS_PRIORITY = {
    "captured": 4,
    "external": 3,
    "dom_missing": 2,
    "pending": 1,
}


def _status_rank(entry: dict[str, Any]) -> int:
    return _STATUS_PRIORITY.get(entry.get("status"), 0)


def dedupe_positions(data: dict[str, Any]) -> int:
    """Collapse ``positions[]`` to one entry per pid. Returns # removed.

    When duplicates exist, keeps the entry with the highest status
    priority (captured > external > pending); on ties, keeps the first
    one encountered. The resulting list preserves the relative order of
    surviving entries (sorted by `pos`).
    """
    positions = data.get("positions") or []
    if not positions:
        return 0
    by_pid: dict[int, dict[str, Any]] = {}
    for entry in positions:
        pid = entry.get("pid")
        if not isinstance(pid, int):
            continue
        prev = by_pid.get(pid)
        if prev is None or _status_rank(entry) > _status_rank(prev):
            by_pid[pid] = entry
    deduped = sorted(
        by_pid.values(), key=lambda e: int(e.get("pos") or 0),
    )
    removed = len(positions) - len(deduped)
    data["positions"] = deduped
    return removed


def apply_capture(
    data: dict[str, Any],
    *,
    pid: int,
    file: str,
    chapter_number: int | None = None,
    chapter_position: int | None = None,
    chapter_name: str | None = None,
) -> dict[str, Any] | None:
    """Mark `pid` as captured in ``positions[]``. Pid-keyed; never rewrites pid.

    If an entry for `pid` exists, updates `status`, `file`, drops `ref`,
    and fills missing chapter fields. If no entry exists (e.g. capture
    arrived before manifest discovered the chapter), appends a new
    minimal entry with `pos = max(pos)+1`.

    Returns the mutated/created entry, or None if `pid` is invalid.
    """
    if not isinstance(pid, int):
        return None
    positions = data.setdefault("positions", [])
    target: dict[str, Any] | None = None
    for entry in positions:
        if entry.get("pid") == pid:
            target = entry
            break
    if target is None:
        next_pos = (
            max((int(e.get("pos") or 0) for e in positions), default=0) + 1
        )
        target = {
            "pos": next_pos,
            "pid": pid,
            "chapter_name": chapter_name or "",
            "chapter_number": int(chapter_number or 0),
            "chapter_position": int(chapter_position or 0),
        }
        positions.append(target)
    target["status"] = "captured"
    target["file"] = file
    target.pop("ref", None)
    # Backfill chapter context only when missing — never overwrite a
    # value already established by manifest discovery (which is the
    # source of truth for chapter coordinates).
    if chapter_name and not target.get("chapter_name"):
        target["chapter_name"] = chapter_name
    if chapter_number and not target.get("chapter_number"):
        target["chapter_number"] = int(chapter_number)
    if chapter_position and not target.get("chapter_position"):
        target["chapter_position"] = int(chapter_position)
    return target


def apply_dom_missing(
    data: dict[str, Any],
    *,
    pid: int,
    chapter_number: int | None = None,
    chapter_position: int | None = None,
    chapter_name: str | None = None,
    reason: str | None = None,
) -> dict[str, Any] | None:
    """Mark `pid` as ``dom_missing`` in ``positions[]``.

    Called when capture-time bulk-prune (in the userscript) detects a
    manifest pid that the live chapter listing no longer renders.
    Idempotent: if `pid` is already ``captured`` or ``external`` we
    leave it untouched (real data wins). Otherwise upserts a
    ``dom_missing`` entry, stamping ``dom_missing_reason`` /
    ``dom_missing_at`` for audit.

    Returns the mutated/created entry, or None if `pid` is invalid.
    """
    if not isinstance(pid, int):
        return None
    positions = data.setdefault("positions", [])
    target: dict[str, Any] | None = None
    for entry in positions:
        if entry.get("pid") == pid:
            target = entry
            break
    if target is None:
        next_pos = (
            max((int(e.get("pos") or 0) for e in positions), default=0) + 1
        )
        target = {
            "pos": next_pos,
            "pid": pid,
            "chapter_name": chapter_name or "",
            "chapter_number": int(chapter_number or 0),
            "chapter_position": int(chapter_position or 0),
        }
        positions.append(target)
    # Don't downgrade real captures: a captured/external pid stays as-is.
    if target.get("status") in ("captured", "external"):
        return target
    target["status"] = "dom_missing"
    if reason:
        target["dom_missing_reason"] = reason
    target["dom_missing_at"] = _now_iso()
    # Backfill chapter context only when missing.
    if chapter_name and not target.get("chapter_name"):
        target["chapter_name"] = chapter_name
    if chapter_number and not target.get("chapter_number"):
        target["chapter_number"] = int(chapter_number)
    if chapter_position and not target.get("chapter_position"):
        target["chapter_position"] = int(chapter_position)
    return target


def carry_forward_capture_state(
    data: dict[str, Any],
    new_positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Overlay captured/external state from ``data["positions"]`` by pid.

    Used after a manifest rebuild that recomputes chapter ordering. The
    new canonical positions list (`new_positions`) carries fresh
    `pos`/`chapter_*` values; this function preserves any prior
    captured `status`/`file` (or external `ref`) by matching on pid,
    so upstream reorderings never demote a captured puzzle back to
    pending.

    Returns the merged list (same length and pid set as `new_positions`).
    Pids in the old `positions[]` that no longer appear in
    `new_positions` (e.g. removed from the chapter) are dropped — the
    SGF on disk is preserved either way.
    """
    old_by_pid: dict[int, dict[str, Any]] = {}
    for entry in data.get("positions") or []:
        pid = entry.get("pid")
        if isinstance(pid, int):
            # Last write wins on duplicates with same pid; dedupe later.
            old_by_pid[pid] = entry

    merged: list[dict[str, Any]] = []
    for new_entry in new_positions:
        pid = new_entry.get("pid")
        if not isinstance(pid, int):
            merged.append(new_entry)
            continue
        old = old_by_pid.get(pid)
        if old is None:
            merged.append(new_entry)
            continue
        # Carry forward: captured/external trumps the freshly-computed
        # status (which is seeded only from disk + global index).
        old_status = old.get("status")
        new_status = new_entry.get("status")
        if _STATUS_PRIORITY.get(old_status, 0) > _STATUS_PRIORITY.get(
            new_status, 0,
        ):
            new_entry["status"] = old_status
            if old_status == "captured" and old.get("file"):
                new_entry["file"] = old["file"]
                new_entry.pop("ref", None)
            elif old_status == "external" and old.get("ref"):
                new_entry["ref"] = old["ref"]
                new_entry.pop("file", None)
            elif old_status == "dom_missing":
                if old.get("dom_missing_reason"):
                    new_entry["dom_missing_reason"] = old["dom_missing_reason"]
                if old.get("dom_missing_at"):
                    new_entry["dom_missing_at"] = old["dom_missing_at"]
        merged.append(new_entry)
    return merged
