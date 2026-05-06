"""
One-shot cleanup: rewrite CJK chapter labels in book SGF filenames to
English, and atomically update ``book.json`` + ``capture-log.jsonl``
to match. Optionally renames the book directory itself.

Default is dry-run; pass ``--apply`` to actually mutate the filesystem.

Usage::

    # Preview changes for book 34103 (most common case)
    python -m tools.weiqi101.cleanup_book_filenames --book-id 34103

    # Apply
    python -m tools.weiqi101.cleanup_book_filenames --book-id 34103 --apply

    # Also rename the parent directory (CJK -> english slug)
    python -m tools.weiqi101.cleanup_book_filenames --book-id 34103 --apply --rename-dir

Safety:
- Refuses to overwrite an existing destination filename.
- Does not touch ``sgf-index.txt`` (book SGFs are not tracked there;
  verified for the current corpus).
- Records every rename in a JSON sidecar (``cleanup-report.json``)
  inside the book directory.

This script is **idempotent** for already-migrated files (anything
whose chapter portion is pure ASCII is left alone).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.weiqi101.config import get_output_dir
from tools.weiqi101.receiver import resolve_label, _has_cjk

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cleanup")


def _book_dir_for(book_id: int) -> Path:
    """Find ``books/{book_id}-*/`` under the configured output dir."""
    books_root = get_output_dir() / "books"
    if not books_root.exists():
        raise FileNotFoundError(f"Books root not found: {books_root}")
    prefix = f"{book_id}-"
    for entry in books_root.iterdir():
        if entry.is_dir() and entry.name.startswith(prefix):
            return entry
    raise FileNotFoundError(f"No directory matching {prefix}* in {books_root}")


_FILENAME_RE = re.compile(
    r"^(?P<gpos>\d+)_(?P<chap>.+?)_(?P<chpos>\d+)_(?P<pid>\d+)\.sgf$"
)


def _new_chapter_slug(chap_raw: str) -> tuple[str, str, str]:
    """Return ``(new_slug, source, display)`` for a raw chapter token.

    If ``chap_raw`` is already pure ASCII the original is returned
    unchanged with ``source='already-ascii'``. Otherwise the receiver's
    ``resolve_label`` pipeline is reused so the script and runtime stay
    consistent.
    """
    if not _has_cjk(chap_raw):
        return chap_raw, "already-ascii", chap_raw
    label = resolve_label("", chap_raw, context="cleanup")
    return label["slug"] or chap_raw, label["source"], label["display"]


def plan_renames(book_dir: Path) -> list[dict[str, Any]]:
    """Build the rename plan for every SGF in ``book_dir/sgf/``."""
    sgf_dir = book_dir / "sgf"
    if not sgf_dir.exists():
        raise FileNotFoundError(f"sgf/ not found under {book_dir}")

    plan: list[dict[str, Any]] = []
    for f in sorted(sgf_dir.iterdir()):
        if f.suffix != ".sgf":
            continue
        m = _FILENAME_RE.match(f.name)
        if not m:
            logger.warning("Skipping unparseable filename: %s", f.name)
            continue
        chap_raw = m.group("chap")
        new_chap, source, display = _new_chapter_slug(chap_raw)
        if new_chap == chap_raw:
            continue  # already ascii or no translation available
        new_name = f"{m.group('gpos')}_{new_chap}_{m.group('chpos')}_{m.group('pid')}.sgf"
        plan.append({
            "old": f.name,
            "new": new_name,
            "chapter_raw": chap_raw,
            "chapter_english": display,
            "label_source": source,
            "puzzle_id": int(m.group("pid")),
        })
    return plan


def apply_renames(book_dir: Path, plan: list[dict[str, Any]]) -> int:
    """Rename SGF files on disk and refuse to clobber existing names."""
    sgf_dir = book_dir / "sgf"
    n = 0
    for item in plan:
        src = sgf_dir / item["old"]
        dst = sgf_dir / item["new"]
        if not src.exists():
            logger.warning("Source missing, skipping: %s", item["old"])
            continue
        if dst.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing file: {dst.name}"
            )
        src.rename(dst)
        n += 1
    return n


def update_book_index(
    book_dir: Path, plan: list[dict[str, Any]],
) -> int:
    """Rewrite ``positions[*].file`` and ``chapters[*].name`` in book.json."""
    from tools.weiqi101 import book_state

    data = book_state.load(book_dir)
    if not data:
        logger.info("No book.json — skipping")
        return 0

    rename_by_old = {item["old"]: item["new"] for item in plan}
    chapter_english_by_raw = {
        item["chapter_raw"]: item["chapter_english"] for item in plan
    }

    n = 0
    for pos in data.get("positions", []):
        old = pos.get("file")
        if old and old in rename_by_old:
            pos["file"] = rename_by_old[old]
            n += 1
        # Translate chapter_name in the position record too.
        ch_raw = pos.get("chapter_name")
        if ch_raw and ch_raw in chapter_english_by_raw:
            pos["chapter_name_raw"] = ch_raw
            pos["chapter_name"] = chapter_english_by_raw[ch_raw]

    for ch in data.get("chapters", []):
        ch_raw = ch.get("name")
        if ch_raw and ch_raw in chapter_english_by_raw:
            ch["name_raw"] = ch_raw
            ch["name"] = chapter_english_by_raw[ch_raw]

    book_state.save(book_dir, data)
    return n


def update_capture_log(
    book_dir: Path, plan: list[dict[str, Any]],
) -> int:
    """Rewrite ``file`` and ``chapter_name`` fields in the JSONL log."""
    path = book_dir / "capture-log.jsonl"
    if not path.exists():
        logger.info("No capture-log.jsonl — skipping")
        return 0

    rename_by_old = {item["old"]: item["new"] for item in plan}
    chapter_english_by_raw = {
        item["chapter_raw"]: item["chapter_english"] for item in plan
    }

    out_lines: list[str] = []
    n = 0
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                out_lines.append(raw)
                continue
            old = entry.get("file")
            if old and old in rename_by_old:
                entry["file"] = rename_by_old[old]
                n += 1
            ch_raw = entry.get("chapter_name")
            if ch_raw and ch_raw in chapter_english_by_raw:
                entry.setdefault("chapter_name_raw", ch_raw)
                entry["chapter_name"] = chapter_english_by_raw[ch_raw]
                entry.setdefault(
                    "chapter_name_english", chapter_english_by_raw[ch_raw],
                )
            out_lines.append(json.dumps(entry, ensure_ascii=False))

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return n


def write_report(
    book_dir: Path, plan: list[dict[str, Any]], applied: bool,
) -> Path:
    report = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": applied,
        "renames": plan,
        "total_planned": len(plan),
    }
    report_path = book_dir / "cleanup-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path


def maybe_rename_dir(book_dir: Path, *, apply: bool) -> Path:
    """Rename the book directory from ``{id}-{cjk}`` to ``{id}-{english}``.

    Uses the book name embedded in ``book.json`` if available;
    falls back to a stable token if no English translation is found.
    """
    from tools.weiqi101 import book_state

    data = book_state.load(book_dir)
    if not data:
        return book_dir
    raw_name = data.get("book_name_raw") or data.get("book_name", "")
    label = resolve_label("", raw_name, context=f"dir={book_dir.name}")
    english_slug = label["slug"]
    if not english_slug:
        logger.info(
            "No English translation for book name %r — leaving dir as-is",
            raw_name,
        )
        return book_dir
    book_id = book_dir.name.split("-", 1)[0]
    new_name = f"{book_id}-{english_slug}"
    if new_name == book_dir.name:
        return book_dir
    new_path = book_dir.parent / new_name
    if new_path.exists():
        logger.warning("Target dir already exists: %s", new_path.name)
        return book_dir
    logger.info(
        "%s rename dir: %s -> %s",
        "APPLY" if apply else "DRY-RUN",
        book_dir.name, new_name,
    )
    if apply:
        book_dir.rename(new_path)
        return new_path
    return book_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite CJK chapter labels in book SGF filenames to English."
        ),
    )
    parser.add_argument(
        "--book-id", type=int, required=True,
        help="Numeric 101weiqi book ID (e.g. 34103)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually mutate filesystem (default: dry-run)",
    )
    parser.add_argument(
        "--rename-dir", action="store_true",
        help="Also rename the parent {id}-{cjk}/ directory to {id}-{english}/",
    )
    args = parser.parse_args()

    book_dir = _book_dir_for(args.book_id)
    logger.info("Book dir: %s", book_dir)

    plan = plan_renames(book_dir)
    logger.info("Planned renames: %d", len(plan))
    for item in plan[:5]:
        logger.info(
            "  %s  ->  %s  [%s]",
            item["old"], item["new"], item["label_source"],
        )
    if len(plan) > 5:
        logger.info("  ... and %d more", len(plan) - 5)

    if not plan:
        logger.info("Nothing to do.")
        return 0

    if not args.apply:
        write_report(book_dir, plan, applied=False)
        logger.info(
            "DRY-RUN. Re-run with --apply to mutate. "
            "Report written to cleanup-report.json",
        )
        return 0

    n_files = apply_renames(book_dir, plan)
    n_index = update_book_index(book_dir, plan)
    n_log = update_capture_log(book_dir, plan)
    write_report(book_dir, plan, applied=True)
    logger.info(
        "Applied: %d files renamed, %d book-index entries, %d log entries",
        n_files, n_index, n_log,
    )

    if args.rename_dir:
        maybe_rename_dir(book_dir, apply=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
