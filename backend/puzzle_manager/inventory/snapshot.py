"""Atomic JSON snapshot of yengo-search.db counts for presentation tools.

Why this exists: yengo_dashboard (a presentation-only dashboard) needs the same
counts the published SQLite DB exposes, but reading the live DB while the
pipeline rewrites it (vacuum-db, rollback, publish, clean) causes Windows
file-lock collisions (WinError 5/32). The fix is a clean read/write split:
the backend writes inventory.json after every state mutation; the cockpit
(or any other read-only consumer) reads JSON only and never opens the DB.

The JSON shape mirrors ``tools.yengo_dashboard.server.models.InventoryResponse``
plus is the canonical, language-agnostic snapshot contract — anything that
needs counts should consume this file rather than running its own SQL.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

INVENTORY_SNAPSHOT_FILENAME = "inventory.json"


def write_inventory_snapshot(output_dir: Path) -> Path | None:
    """Write ``inventory.json`` next to ``yengo-search.db`` atomically.

    Returns the snapshot path on success, or ``None`` when no search DB is
    published yet (fresh checkout, mid-bootstrap). Read failures or write
    failures bubble up — callers handle them with the existing
    path-shortened error wrapper in ``cli._shorten_paths``.
    """
    db = output_dir / "yengo-search.db"
    snapshot = output_dir / INVENTORY_SNAPSHOT_FILENAME
    if not db.exists():
        return None

    uri = f"file:{db.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        puzzles_total = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
        collections_total = conn.execute(
            "SELECT COUNT(*) FROM collections"
        ).fetchone()[0]
        daily_total = conn.execute(
            "SELECT COUNT(*) FROM daily_schedule"
        ).fetchone()[0]
        by_level = {
            str(level_id): n
            for level_id, n in conn.execute(
                "SELECT level_id, COUNT(*) FROM puzzles "
                "GROUP BY level_id ORDER BY level_id"
            ).fetchall()
        }
        by_ct = {
            str(ct): n
            for ct, n in conn.execute(
                "SELECT content_type, COUNT(*) FROM puzzles "
                "GROUP BY content_type ORDER BY content_type"
            ).fetchall()
        }
        by_cat = {
            str(cat or "uncategorised"): n
            for cat, n in conn.execute(
                "SELECT category, COUNT(*) FROM collections "
                "GROUP BY category ORDER BY category"
            ).fetchall()
        }
    finally:
        conn.close()

    schema_version, db_version = _read_db_version(output_dir)
    payload = {
        "puzzles_total": int(puzzles_total),
        "collections_total": int(collections_total),
        "daily_schedule_total": int(daily_total),
        "by_level_id": by_level,
        "by_content_type": by_ct,
        "by_collection_category": by_cat,
        "schema_version": schema_version,
        "db_version": db_version,
    }
    tmp = snapshot.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(str(tmp), str(snapshot))
    logger.info(
        "Inventory snapshot written: %d puzzles, %d collections",
        puzzles_total,
        collections_total,
    )
    return snapshot


def _read_db_version(output_dir: Path) -> tuple[int | None, str | None]:
    """Read ``schema_version`` + ``db_version`` from db-version.json if present."""
    path = output_dir / "db-version.json"
    if not path.exists():
        return (None, None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return (None, None)
    sv = data.get("schema_version")
    dv = data.get("db_version")
    return (
        int(sv) if isinstance(sv, int | str) and str(sv).isdigit() else None,
        str(dv) if dv is not None else None,
    )
