"""101weiqi corpus inventory.

Scans every SGF under the configured 101weiqi output directory, extracts
the trailing puzzle id from each filename, and writes two artifacts:

  * ``inventory.json`` — counts and overlap percentages, no pid lists.
  * ``unique-sgf.txt`` — one POSIX-relative path per unique pid, sorted by
    pid ascending. Tie-breaker for which path "wins" when a pid appears in
    multiple locations: ``books > qday > sgf``, then lexicographic.

Both artifacts are derived/runtime data: regenerable, gitignored.

Triggers:
  * CLI:  ``python -m tools.weiqi101 inventory --refresh``
  * HTTP: ``GET /inventory/refresh`` (receiver)
  * Hook: receiver startup (only if ``inventory.json`` is missing) and
    after each ``session_summary`` capture event (throttled).

A single in-process lock guards generation so overlapping triggers fold
into one scan.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from tools.weiqi101.config import (
    LOGS_SUBDIR,
    QDAY_SUBDIR,
    SGF_SUBDIR,
    get_output_dir,
)
from tools.weiqi101.pid_extract import pid_from_filename

logger = logging.getLogger(__name__)

INVENTORY_FILENAME = "inventory.json"
UNIQUE_SGF_FILENAME = "unique-sgf.txt"
SCHEMA_VERSION = 1

# Directories scanned for SGFs. Order encodes the tie-breaker used by
# ``unique-sgf.txt`` when a pid lives in multiple places.
_LOCATION_PRIORITY: tuple[str, ...] = ("books", QDAY_SUBDIR, SGF_SUBDIR)

# Throttle: minimum seconds between auto-triggered refreshes. Manual
# refreshes via the CLI/HTTP endpoint are never throttled, only serialised
# by the lock below.
AUTO_REFRESH_MIN_INTERVAL_SEC = 30 * 60

# Skip these subdirectories during the SGF walk — they never contain SGFs.
_SKIP_SUBDIRS = frozenset({LOGS_SUBDIR, "__pycache__", "archive"})


# ---------------------------------------------------------------------------
# Concurrency primitives
# ---------------------------------------------------------------------------

_scan_lock = threading.Lock()
_scan_state: dict[str, Any] = {
    "running": False,
    "scan_id": None,
    "started_at": None,
    "last_finished_at": 0.0,  # epoch seconds; 0 == never
}


def is_running() -> bool:
    return bool(_scan_state["running"])


def current_scan_info() -> dict[str, Any] | None:
    """Return ``{scan_id, started_at}`` if a scan is in flight, else ``None``."""
    if not _scan_state["running"]:
        return None
    return {
        "scan_id": _scan_state["scan_id"],
        "started_at": _scan_state["started_at"],
    }


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


@dataclass
class _Bucket:
    files: int = 0
    pids: set[int] = field(default_factory=set)


def _categorise(rel_parts: tuple[str, ...]) -> str | None:
    """Return ``books`` / ``qday`` / ``sgf`` for the given relative path,
    or ``None`` if the file is outside any tracked location.
    """
    if not rel_parts:
        return None
    head = rel_parts[0]
    if head in _LOCATION_PRIORITY:
        return head
    return None


def _location_rank(location: str) -> int:
    try:
        return _LOCATION_PRIORITY.index(location)
    except ValueError:
        return len(_LOCATION_PRIORITY)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan(root: Path) -> dict[str, Any]:
    """Walk ``root`` and build the inventory payload + unique-sgf list.

    Returns a dict with two keys:
      * ``inventory``: payload to be JSON-serialised to ``inventory.json``.
      * ``unique_sgf_lines``: list[str] for ``unique-sgf.txt`` (no trailing
        newlines, header line included).
    """
    root = root.resolve()
    started = time.monotonic()

    # pid -> (location, posix_relpath); winner picked by location rank then path.
    winners: dict[int, tuple[str, str]] = {}
    location_buckets: dict[str, _Bucket] = {
        loc: _Bucket() for loc in _LOCATION_PRIORITY
    }
    # Per-book stats: keyed by directory name under books/.
    book_buckets: dict[str, _Bucket] = {}

    total_files = 0
    unparsable = 0

    for path in _iter_sgfs(root):
        rel = path.relative_to(root)
        rel_parts = rel.parts
        location = _categorise(rel_parts)
        if location is None:
            continue

        total_files += 1
        pid = pid_from_filename(path.name)
        if pid is None:
            unparsable += 1
            continue

        bucket = location_buckets[location]
        bucket.files += 1
        bucket.pids.add(pid)

        if location == "books" and len(rel_parts) >= 2:
            book_dir = rel_parts[1]
            bb = book_buckets.setdefault(book_dir, _Bucket())
            bb.files += 1
            bb.pids.add(pid)

        rel_posix = PurePosixPath(*rel_parts).as_posix()
        prev = winners.get(pid)
        if prev is None:
            winners[pid] = (location, rel_posix)
        else:
            prev_loc, prev_path = prev
            if (_location_rank(location), rel_posix) < (
                _location_rank(prev_loc),
                prev_path,
            ):
                winners[pid] = (location, rel_posix)

    duration_ms = int((time.monotonic() - started) * 1000)

    unique_pids = len(winners)
    parsed_files = total_files - unparsable
    duplicate_files = max(parsed_files - unique_pids, 0)
    overlap_pct = (duplicate_files / parsed_files * 100.0) if parsed_files else 0.0

    locations_payload: dict[str, dict[str, Any]] = {}
    for loc in _LOCATION_PRIORITY:
        b = location_buckets[loc]
        elsewhere = set()
        for other_loc, other_b in location_buckets.items():
            if other_loc == loc:
                continue
            elsewhere |= other_b.pids
        shared = len(b.pids & elsewhere)
        shared_pct = (shared / len(b.pids) * 100.0) if b.pids else 0.0
        locations_payload[loc] = {
            "files": b.files,
            "unique_pids": len(b.pids),
            "shared_with_others_pct": round(shared_pct, 2),
        }

    # Per-book overlap is "pids in this book that also exist anywhere else
    # in the corpus" (other books, qday, or sgf/).
    books_payload: list[dict[str, Any]] = []
    all_pids = {pid for b in location_buckets.values() for pid in b.pids}
    for book_dir, bb in sorted(book_buckets.items()):
        # "elsewhere" = corpus minus the pids exclusive to this book.
        elsewhere_pids = all_pids - (bb.pids - _other_book_pids(book_buckets, book_dir))
        # Simpler reading: pids in this book that occur in some OTHER file.
        overlap_count = 0
        for pid in bb.pids:
            # Occurs elsewhere if it exists outside this book in books/, or
            # in qday/ or sgf/.
            in_other_books = any(
                pid in other_bb.pids
                for other_dir, other_bb in book_buckets.items()
                if other_dir != book_dir
            )
            in_qday = pid in location_buckets[QDAY_SUBDIR].pids
            in_sgf = pid in location_buckets[SGF_SUBDIR].pids
            if in_other_books or in_qday or in_sgf:
                overlap_count += 1
        overlap_pct_book = (
            overlap_count / len(bb.pids) * 100.0 if bb.pids else 0.0
        )
        book_id = _book_id_from_dir(book_dir)
        books_payload.append(
            {
                "book_id": book_id,
                "dir": book_dir,
                "files": bb.files,
                "unique_pids": len(bb.pids),
                "overlap_with_corpus_pct": round(overlap_pct_book, 2),
                "novel_pct": round(100.0 - overlap_pct_book, 2),
            }
        )
        # Silence the unused-variable warning while keeping the call shape
        # in case future use needs the full set.
        _ = elsewhere_pids

    inventory = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "scan_duration_ms": duration_ms,
        "root": PurePosixPath(*root.relative_to(root.anchor).parts).as_posix()
        if root.anchor
        else str(root),
        "totals": {
            "files": total_files,
            "files_unparsable": unparsable,
            "unique_pids": unique_pids,
            "duplicate_files": duplicate_files,
            "overlap_pct": round(overlap_pct, 2),
        },
        "locations": locations_payload,
        "books": books_payload,
    }

    header = (
        f"# unique-sgf v{SCHEMA_VERSION} "
        f"generated_at={inventory['generated_at']} "
        f"tiebreak={'>'.join(_LOCATION_PRIORITY)} "
        f"total={unique_pids}"
    )
    sorted_pids = sorted(winners.keys())
    lines = [header] + [winners[pid][1] for pid in sorted_pids]

    return {"inventory": inventory, "unique_sgf_lines": lines}


def _other_book_pids(buckets: dict[str, _Bucket], skip: str) -> set[int]:
    out: set[int] = set()
    for k, v in buckets.items():
        if k != skip:
            out |= v.pids
    return out


def _book_id_from_dir(dir_name: str) -> int | None:
    head, _, _ = dir_name.partition("-")
    if head.isdigit():
        return int(head)
    return None


def _iter_sgfs(root: Path):
    """Yield ``.sgf`` files under ``root``, skipping known noise subdirs."""
    if not root.exists():
        return
    stack: list[Path] = [root]
    while stack:
        cur = stack.pop()
        try:
            entries = list(cur.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in _SKIP_SUBDIRS:
                        continue
                    stack.append(entry)
                elif entry.is_file() and entry.suffix == ".sgf":
                    yield entry
            except OSError:
                continue


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def inventory_path(root: Path | None = None) -> Path:
    return _root(root) / INVENTORY_FILENAME


def unique_sgf_path(root: Path | None = None) -> Path:
    return _root(root) / UNIQUE_SGF_FILENAME


def _root(root: Path | None) -> Path:
    return Path(root) if root is not None else get_output_dir()


def write_outputs(payload: dict[str, Any], root: Path | None = None) -> None:
    target_root = _root(root)
    target_root.mkdir(parents=True, exist_ok=True)
    inv = payload["inventory"]
    lines: list[str] = payload["unique_sgf_lines"]

    inv_path = inventory_path(target_root)
    tmp_inv = inv_path.with_suffix(inv_path.suffix + ".tmp")
    tmp_inv.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp_inv.replace(inv_path)

    uniq_path = unique_sgf_path(target_root)
    tmp_uniq = uniq_path.with_suffix(uniq_path.suffix + ".tmp")
    tmp_uniq.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_uniq.replace(uniq_path)


def load_inventory(root: Path | None = None) -> dict[str, Any] | None:
    p = inventory_path(root)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Refresh orchestration
# ---------------------------------------------------------------------------


def _new_scan_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def refresh_blocking(root: Path | None = None) -> dict[str, Any]:
    """Run a scan synchronously (CLI path). Returns the inventory dict."""
    target = _root(root)
    with _scan_lock:
        scan_id = _new_scan_id()
        _scan_state.update(
            running=True, scan_id=scan_id, started_at=_now_iso()
        )
        try:
            payload = scan(target)
            write_outputs(payload, target)
        finally:
            _scan_state.update(
                running=False,
                scan_id=None,
                started_at=None,
                last_finished_at=time.monotonic(),
            )
        logger.info(
            "[INVENTORY] scan_id=%s files=%d unique=%d duration_ms=%d",
            scan_id,
            payload["inventory"]["totals"]["files"],
            payload["inventory"]["totals"]["unique_pids"],
            payload["inventory"]["scan_duration_ms"],
        )
        return payload["inventory"]


def trigger_async(root: Path | None = None) -> dict[str, Any]:
    """Start a refresh in a background thread.

    Returns ``{"scan_id", "started_at", "status": "started"}`` if launched,
    or ``{"scan_id", "started_at", "status": "already_running"}`` if a
    scan is already in flight (caller should map that to HTTP 409).
    """
    if _scan_state["running"]:
        return {
            "scan_id": _scan_state["scan_id"],
            "started_at": _scan_state["started_at"],
            "status": "already_running",
        }
    scan_id = _new_scan_id()
    started_at = _now_iso()
    # Pre-populate state so the immediate response is consistent with what
    # subsequent requests will see; the worker re-asserts under the lock.
    _scan_state.update(running=True, scan_id=scan_id, started_at=started_at)

    target = _root(root)

    def _worker() -> None:
        try:
            with _scan_lock:
                payload = scan(target)
                write_outputs(payload, target)
                logger.info(
                    "[INVENTORY] scan_id=%s files=%d unique=%d duration_ms=%d",
                    scan_id,
                    payload["inventory"]["totals"]["files"],
                    payload["inventory"]["totals"]["unique_pids"],
                    payload["inventory"]["scan_duration_ms"],
                )
        except Exception:  # pragma: no cover - defensive
            logger.exception("[INVENTORY] scan_id=%s failed", scan_id)
        finally:
            _scan_state.update(
                running=False,
                scan_id=None,
                started_at=None,
                last_finished_at=time.monotonic(),
            )

    threading.Thread(target=_worker, name=f"inventory-{scan_id}", daemon=True).start()
    return {"scan_id": scan_id, "started_at": started_at, "status": "started"}


def maybe_trigger_throttled(root: Path | None = None) -> dict[str, Any]:
    """Trigger a refresh unless one ran recently (within the throttle window).

    Returns ``{"status": "started"|"already_running"|"throttled"|"skipped"}``.
    """
    if _scan_state["running"]:
        return {"status": "already_running"}
    last = _scan_state["last_finished_at"]
    if last and (time.monotonic() - last) < AUTO_REFRESH_MIN_INTERVAL_SEC:
        return {"status": "throttled"}
    return trigger_async(root)


def trigger_on_startup_if_missing(root: Path | None = None) -> dict[str, Any]:
    """Receiver-startup hook: scan only if no inventory exists yet."""
    target = _root(root)
    if inventory_path(target).exists():
        return {"status": "skipped", "reason": "inventory_present"}
    return trigger_async(target)
