"""Backfill English chapter/book labels in already-saved book.json.

When a book was discovered before server-side label translation was wired
into ``/book/manifest``, the consolidated ``book.json`` (or its retired
predecessors ``manifest.json`` / ``book-index.json``) may still contain
raw CJK chapter names (e.g. ``死活入門(1)``). This script re-translates
those fields in place using the same ``resolve_label`` pipeline the
receiver now uses at write-time.

Behavior:
    * Idempotent — running twice produces the same output.
    * Preserves the original CJK in ``*_raw`` fields for traceability.
    * Dry-run by default; pass ``--apply`` to write changes.

Usage::

    python -m tools.weiqi101.translate_book_manifest --book-dir external-sources/101weiqi/books/1054-...
    python -m tools.weiqi101.translate_book_manifest --book-dir external-sources/101weiqi/books/1054-... --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import book_state
from .receiver import resolve_label


def _translate_chapter(ch: dict, *, ctx: str) -> bool:
    """Mutate one chapter dict in place. Returns True if it changed."""
    raw = ch.get("name") or ""
    if not raw:
        return False
    label = resolve_label(ch.get("name_visible"), ch.get("name_raw") or raw, context=ctx)
    new_name = label["display"] if label["english"] else raw
    new_raw = label["raw"] or raw
    changed = (
        ch.get("name") != new_name
        or ch.get("name_raw") != new_raw
        or ch.get("name_english") != label["english"]
    )
    ch["name_raw"] = new_raw
    if label["english"]:
        ch["name"] = new_name
        ch["name_english"] = label["english"]
    ch["name_label_source"] = label["source"]
    return changed


def backfill(book_dir: Path, *, apply: bool) -> int:
    data = book_state.load(book_dir)
    if not data:
        print(f"[ERR] no book.json at {book_dir}", file=sys.stderr)
        return 2

    book_id = data.get("book_id", 0)
    book_name = data.get("book_name", "")
    changed = 0

    # Book-level
    book_label = resolve_label(
        data.get("book_name_visible"),
        data.get("book_name_raw") or book_name,
        context=f"backfill book={book_id}",
    )
    if book_label["english"]:
        if data.get("book_name") != book_label["display"]:
            data["book_name"] = book_label["display"]
            changed += 1
        data["book_name_raw"] = book_label["raw"] or book_name
        data["book_name_english"] = book_label["english"]

    # Chapter-level
    chapters = data.get("chapters", []) or []
    for ch in chapters:
        if _translate_chapter(
            ch, ctx=f"backfill book={book_id} ch={ch.get('chapter_number')}",
        ):
            changed += 1

    # Mirror translated chapter names into positions[]
    ch_name_by_num = {
        ch.get("chapter_number"): ch.get("name", "")
        for ch in chapters
        if ch.get("chapter_number") is not None
    }
    pos_changed = 0
    for pos in data.get("positions", []) or []:
        new_name = ch_name_by_num.get(
            pos.get("chapter_number"), pos.get("chapter_name"),
        )
        if new_name and pos.get("chapter_name") != new_name:
            pos["chapter_name"] = new_name
            pos_changed += 1

    print(f"[INFO] book {book_id} '{data.get('book_name')}'")
    print(f"  fields changed:    {changed}")
    print(f"  positions updated: {pos_changed}")
    if not apply:
        print("[DRY-RUN] no files written. Pass --apply to persist.")
        return 0

    book_state.save(book_dir, data)
    print(f"[WRITE] {book_dir / book_state.BOOK_STATE_FILENAME}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--book-dir", required=True, type=Path,
                    help="Path to the book directory (e.g. external-sources/101weiqi/books/1054-...)")
    ap.add_argument("--apply", action="store_true",
                    help="Actually write changes (default is dry-run)")
    args = ap.parse_args()
    return backfill(args.book_dir, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
