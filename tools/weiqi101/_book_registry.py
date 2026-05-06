"""
Auto-registry of 101weiqi books seen by the receiver.

Records every book whose puzzles have been captured, with full label
provenance (raw CJK + visible/extension-translated + library-translated
English). Acts as a staging area before manual promotion into
``config/collections.json`` — we never mutate the schema-validated
collections file from runtime code.

Companion to ``_book_slug_mapping.json`` (curated id→slug) and
``resolve_label`` in :mod:`tools.weiqi101.receiver`.

File: ``tools/weiqi101/_auto_book_registry.json``
Schema::

    {
      "version": "1.0",
      "description": "Auto-generated registry of 101weiqi books captured at runtime.",
      "books": {
        "<book_id>": {
          "book_id":         <int>,
          "slug":            "<curated-slug-or-fallback>",
          "name_raw":        "<original CJK from page/manifest>",
          "name_visible":    "<browser-translated text from <title>>",
          "name_english":    "<library-translated English>",
          "label_source":    "visible|translated|fallback|empty",
          "first_seen":      "<UTC ISO8601>",
          "last_seen":       "<UTC ISO8601>",
          "captured_count":  <int>,
          "chapters_seen":   ["<english chapter slug>", ...]
        }
      }
    }

The file is rewritten atomically on every update via
``tools.core.atomic_write``. Concurrent registrations are serialised by
a process-level :class:`threading.Lock`.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.core.atomic_write import atomic_write_text

logger = logging.getLogger("101weiqi.book_registry")

REGISTRY_PATH = Path(__file__).parent / "_auto_book_registry.json"

_lock = threading.Lock()


def _load() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {
            "version": "1.0",
            "description": (
                "Auto-generated registry of 101weiqi books captured at "
                "runtime. Promote curated entries into "
                "config/collections.json manually."
            ),
            "books": {},
        }
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "[REGISTRY] failed to read %s; starting fresh",
            REGISTRY_PATH.name,
            exc_info=True,
        )
        return {"version": "1.0", "books": {}}


def _save(data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    atomic_write_text(REGISTRY_PATH, text + "\n")


def register_book(
    book_id: int | str,
    *,
    slug: str,
    name_raw: str = "",
    name_visible: str = "",
    name_english: str = "",
    label_source: str = "fallback",
    chapter_english: str | None = None,
) -> None:
    """Record (or update) a book entry on each successful capture.

    Cheap to call on every capture: keeps min(first_seen) and max(last_seen),
    increments ``captured_count`` by 1, and unions ``chapter_english``
    into ``chapters_seen``. Writes are serialised by a module-level lock.

    Args:
        book_id: Numeric book ID (accepts int or str; stored as str key).
        slug: YL slug used for this book (curated or fallback form).
        name_raw: Original CJK book name as it appears on the page.
        name_visible: Whatever the browser DOM showed at capture time
            (may be the extension-translated English label or still CJK).
        name_english: Library-translated English form.
        label_source: One of ``visible|translated|fallback|empty`` —
            mirrors the value returned by :func:`resolve_label`.
        chapter_english: English chapter slug captured for this puzzle,
            or ``None`` when not in a chapter context.
    """
    if not book_id:
        return
    key = str(book_id)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with _lock:
        data = _load()
        books = data.setdefault("books", {})
        entry = books.get(key)
        if entry is None:
            entry = {
                "book_id": int(book_id) if str(book_id).isdigit() else book_id,
                "slug": slug,
                "name_raw": name_raw,
                "name_visible": name_visible,
                "name_english": name_english,
                "label_source": label_source,
                "first_seen": now,
                "last_seen": now,
                "captured_count": 0,
                "chapters_seen": [],
            }
            books[key] = entry
            logger.info(
                "[REGISTRY] new book id=%s slug=%s english=%r src=%s",
                key, slug, name_english or name_visible or name_raw,
                label_source,
            )

        # Update mutable fields. Prefer non-empty newer values so the
        # registry self-heals as better translations land.
        if name_raw and not entry.get("name_raw"):
            entry["name_raw"] = name_raw
        if name_visible and (
            not entry.get("name_visible")
            or entry.get("label_source") in ("fallback", "empty")
        ):
            entry["name_visible"] = name_visible
        if name_english and (
            not entry.get("name_english")
            or label_source in ("visible", "translated")
        ):
            entry["name_english"] = name_english
        if label_source and label_source != "empty":
            entry["label_source"] = label_source
        entry["last_seen"] = now
        entry["captured_count"] = int(entry.get("captured_count", 0)) + 1

        if chapter_english:
            chapters = entry.setdefault("chapters_seen", [])
            if chapter_english not in chapters:
                chapters.append(chapter_english)

        _save(data)
