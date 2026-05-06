"""Master-vs-downloaded coverage for 101weiqi books.

Compares the *declared* puzzle inventory of a book (from the master
``book-ids.jsonl``) against the *actually present* puzzles recorded in
the downloaded ``books/{id}-*/book.json``.

Algorithm (pure set arithmetic):

    master_ids     = union of chapter[].puzzle_ids in book-ids.jsonl
    downloaded_ids = {pos.pid for pos in book.json positions
                      if pos.status != "pending"}
    missing        = master_ids - downloaded_ids
    extra          = downloaded_ids - master_ids
    coverage_pct   = 100 * |overlap| / |master_ids|

Concurrency: this module is read-only. The master file is parsed once
and cached by ``mtime``; reads use a module-level ``RLock``. Per-book
``book.json`` reads delegate to :func:`book_state.load`, which already
handles in-flight writes from the receiver's capture path.

By design, no files are written. ``missing_ids`` is included in the
returned report so a caller (CLI flag, server route) can opt to persist
it; the function itself never does.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import book_state

MASTER_FILENAME = "book-ids.jsonl"
BOOKS_SUBDIR = "books"

# Statuses in book.json positions[] that count as "present locally".
# "pending" means the puzzle is in the manifest but has not been
# captured (or seen as external) yet, so it is not present.
PRESENT_STATUSES: frozenset[str] = frozenset(
    {"captured", "external", "dom_missing"},
)


@dataclass
class CoverageReport:
    """Coverage of one book.

    Percentages are floats in 0..100 (or ``None`` when undefined,
    e.g. ``master_count == 0``). ``missing_ids`` and ``extra_ids`` are
    present so callers can opt to persist them; this module never
    writes them anywhere.
    """

    book_id: int
    book_name: str = ""
    status: str = "ok"  # ok | not-downloaded | not-in-master | error
    master_count: int = 0
    downloaded_count: int = 0
    overlap_count: int = 0
    missing_count: int = 0
    extra_count: int = 0
    missing_pct: float | None = None
    extra_pct: float | None = None
    coverage_pct: float | None = None
    missing_ids: list[int] = field(default_factory=list)
    extra_ids: list[int] = field(default_factory=list)
    error: str | None = None

    def to_dict(self, *, include_ids: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "book_id": self.book_id,
            "book_name": self.book_name,
            "status": self.status,
            "master_count": self.master_count,
            "downloaded_count": self.downloaded_count,
            "overlap_count": self.overlap_count,
            "missing_count": self.missing_count,
            "extra_count": self.extra_count,
            "missing_pct": self.missing_pct,
            "extra_pct": self.extra_pct,
            "coverage_pct": self.coverage_pct,
        }
        if self.error is not None:
            d["error"] = self.error
        if include_ids:
            d["missing_ids"] = self.missing_ids
            d["extra_ids"] = self.extra_ids
        return d


# ---------------------------------------------------------------------------
# Master index (book-ids.jsonl) — mtime-cached
# ---------------------------------------------------------------------------

_master_lock = threading.RLock()
_master_cache: dict[str, Any] = {"path": None, "mtime": None, "index": {}}


def _build_master_index(path: Path) -> dict[int, dict[str, Any]]:
    """Read ``book-ids.jsonl`` and index by ``book_id``."""
    index: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                bid = int(rec.get("book_id", -1))
            except (TypeError, ValueError):
                continue
            if bid < 0:
                continue
            index[bid] = rec
    return index


def _load_master(master_path: Path) -> dict[int, dict[str, Any]]:
    """Return ``{book_id: master_record}``, cached by ``mtime``."""
    with _master_lock:
        if not master_path.exists():
            _master_cache.update(path=str(master_path), mtime=None, index={})
            return {}
        mtime = master_path.stat().st_mtime
        if (
            _master_cache.get("path") == str(master_path)
            and _master_cache.get("mtime") == mtime
        ):
            return _master_cache["index"]  # type: ignore[return-value]
        index = _build_master_index(master_path)
        _master_cache.update(path=str(master_path), mtime=mtime, index=index)
        return index


def _master_ids(record: dict[str, Any]) -> set[int]:
    """Union of puzzle_ids across all chapters of one master record."""
    out: set[int] = set()
    for ch in record.get("chapters") or []:
        for pid in ch.get("puzzle_ids") or []:
            if isinstance(pid, int):
                out.add(pid)
    # Some legacy records may store IDs flat:
    if not out:
        for pid in record.get("puzzle_ids") or []:
            if isinstance(pid, int):
                out.add(pid)
    return out


def _downloaded_ids(
    book_data: dict[str, Any],
    *,
    include_pending: bool = False,
) -> set[int]:
    """Set of pids actually present in a downloaded ``book.json``.

    By default, ``pending`` positions are excluded (they are declared
    but not captured). Set ``include_pending=True`` to count them too.
    """
    out: set[int] = set()
    for pos in book_data.get("positions") or []:
        pid = pos.get("pid")
        if not isinstance(pid, int):
            continue
        status = pos.get("status") or "pending"
        if include_pending or status in PRESENT_STATUSES:
            out.add(pid)
    return out


def _pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_coverage(
    book_id: int,
    output_dir: Path,
    *,
    include_pending: bool = False,
) -> CoverageReport:
    """Compute coverage for one ``book_id``.

    Args:
        book_id: The 101weiqi book id (same key in master and local).
        output_dir: Directory containing ``book-ids.jsonl`` and ``books/``
            (typically ``external-sources/101weiqi``).
        include_pending: If True, count ``pending`` positions in the
            downloaded set. Default False — pending means "declared but
            not yet captured", which is exactly what coverage measures
            against.
    """
    master_path = output_dir / MASTER_FILENAME
    books_root = output_dir / BOOKS_SUBDIR

    master_index = _load_master(master_path)
    master_rec = master_index.get(book_id)

    book_dir = (
        book_state.find_book_dir(books_root, book_id)
        if books_root.is_dir()
        else None
    )

    # Both sides missing: nothing to report on.
    if master_rec is None and book_dir is None:
        return CoverageReport(
            book_id=book_id,
            status="error",
            error=f"book {book_id} not found in master or downloaded books",
        )

    book_name = ""
    if master_rec is not None:
        book_name = (
            master_rec.get("book_name_en")
            or master_rec.get("book_name")
            or ""
        )

    master_ids: set[int] = _master_ids(master_rec) if master_rec else set()
    downloaded_ids: set[int] = set()
    if book_dir is not None:
        try:
            book_data = book_state.load(book_dir)
        except OSError as exc:
            return CoverageReport(
                book_id=book_id,
                book_name=book_name,
                status="error",
                error=f"failed to read book.json: {exc}",
            )
        downloaded_ids = _downloaded_ids(
            book_data, include_pending=include_pending,
        )
        # Local book name fallback if master had nothing.
        if not book_name and book_data:
            book_name = (
                book_data.get("book_name_english")
                or book_data.get("book_name")
                or book_data.get("book_name_raw")
                or ""
            )

    if master_rec is None:
        status = "not-in-master"
    elif book_dir is None:
        status = "not-downloaded"
    else:
        status = "ok"

    overlap = master_ids & downloaded_ids
    missing = master_ids - downloaded_ids
    extra = downloaded_ids - master_ids

    return CoverageReport(
        book_id=book_id,
        book_name=book_name,
        status=status,
        master_count=len(master_ids),
        downloaded_count=len(downloaded_ids),
        overlap_count=len(overlap),
        missing_count=len(missing),
        extra_count=len(extra),
        missing_pct=_pct(len(missing), len(master_ids)),
        extra_pct=_pct(len(extra), len(downloaded_ids)),
        coverage_pct=_pct(len(overlap), len(master_ids)),
        missing_ids=sorted(missing),
        extra_ids=sorted(extra),
    )


def list_coverage(
    output_dir: Path,
    *,
    include_pending: bool = False,
    book_ids: Iterable[int] | None = None,
) -> list[CoverageReport]:
    """Compute coverage for many books.

    By default scans every downloaded book directory (``books/{id}-*``).
    Pass ``book_ids`` to restrict to specific ids.
    """
    if book_ids is not None:
        ids = list(book_ids)
    else:
        ids = []
        books_root = output_dir / BOOKS_SUBDIR
        if books_root.is_dir():
            for d in books_root.iterdir():
                if not d.is_dir():
                    continue
                prefix = d.name.split("-", 1)[0]
                if prefix.isdigit():
                    ids.append(int(prefix))
        ids.sort()

    return [
        compute_coverage(bid, output_dir, include_pending=include_pending)
        for bid in ids
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .config import get_output_dir

    parser = argparse.ArgumentParser(
        prog="python -m tools.weiqi101.coverage",
        description=(
            "Compare master book-ids.jsonl against downloaded book.json "
            "and report coverage percentages."
        ),
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--book-id", type=int, help="Single book id")
    grp.add_argument(
        "--all", action="store_true", help="Report all downloaded books",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to external-sources/101weiqi (via config.get_output_dir).",
    )
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Count 'pending' positions as present.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human summary.",
    )
    parser.add_argument(
        "--dump-missing",
        type=Path,
        default=None,
        help=(
            "Write missing puzzle ids per book to this JSON file (opt-in; "
            "no file is written by default)."
        ),
    )
    args = parser.parse_args(argv)

    out_dir = args.output_dir or get_output_dir(None)

    if args.book_id is not None:
        reports = [compute_coverage(
            args.book_id, out_dir, include_pending=args.include_pending,
        )]
    else:
        reports = list_coverage(out_dir, include_pending=args.include_pending)

    if args.json:
        print(json.dumps(
            [r.to_dict(include_ids=False) for r in reports],
            indent=2, ensure_ascii=False,
        ))
    else:
        import sys
        enc = (sys.stdout.encoding or "utf-8")
        for r in reports:
            cov = "n/a" if r.coverage_pct is None else f"{r.coverage_pct:5.1f}%"
            miss = "n/a" if r.missing_pct is None else f"{r.missing_pct:5.1f}%"
            line = (
                f"book {r.book_id:>6}  status={r.status:<14}  "
                f"master={r.master_count:>5}  local={r.downloaded_count:>5}  "
                f"coverage={cov}  missing={miss}  {r.book_name}"
            )
            # Be tolerant of legacy Windows code pages (cp1252) that
            # cannot encode CJK book names.
            print(line.encode(enc, errors="replace").decode(enc, errors="replace"))

    if args.dump_missing is not None:
        payload = {
            str(r.book_id): {
                "book_name": r.book_name,
                "missing_ids": r.missing_ids,
                "extra_ids": r.extra_ids,
            }
            for r in reports
        }
        args.dump_missing.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
