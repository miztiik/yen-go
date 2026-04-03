from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.core.db_models import (
    CollectionMeta,
    DbVersionInfo,
    PuzzleEntry,
    generate_db_version,
)

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """\
CREATE TABLE puzzles (
    content_hash    TEXT PRIMARY KEY,
    batch           TEXT NOT NULL,
    level_id        INTEGER NOT NULL,
    quality         INTEGER NOT NULL DEFAULT 0,
    content_type    INTEGER NOT NULL DEFAULT 2,
    cx_depth        INTEGER NOT NULL DEFAULT 0,
    cx_refutations  INTEGER NOT NULL DEFAULT 0,
    cx_solution_len INTEGER NOT NULL DEFAULT 0,
    cx_unique_resp  INTEGER NOT NULL DEFAULT 0,
    ac              INTEGER NOT NULL DEFAULT 0,
    attrs           TEXT DEFAULT '{}'
);

CREATE TABLE puzzle_tags (
    content_hash    TEXT NOT NULL REFERENCES puzzles(content_hash),
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (content_hash, tag_id)
);

CREATE TABLE puzzle_collections (
    content_hash    TEXT NOT NULL REFERENCES puzzles(content_hash),
    collection_id   INTEGER NOT NULL,
    sequence_number INTEGER,
    chapter         TEXT DEFAULT '',
    PRIMARY KEY (content_hash, collection_id)
);

CREATE TABLE collections (
    collection_id   INTEGER PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    category        TEXT,
    puzzle_count    INTEGER DEFAULT 0,
    attrs           TEXT DEFAULT '{}'
);

CREATE VIRTUAL TABLE collections_fts USING fts5(
    name, slug,
    content='collections',
    content_rowid='collection_id'
);

CREATE INDEX idx_puzzles_level    ON puzzles(level_id);
CREATE INDEX idx_puzzles_quality  ON puzzles(quality);
CREATE INDEX idx_puzzles_ctype    ON puzzles(content_type);
CREATE INDEX idx_puzzles_depth    ON puzzles(cx_depth);
CREATE INDEX idx_puzzles_ac       ON puzzles(ac);
CREATE INDEX idx_tags_tag         ON puzzle_tags(tag_id);
CREATE INDEX idx_tags_hash        ON puzzle_tags(content_hash);
CREATE INDEX idx_cols_col         ON puzzle_collections(collection_id);
CREATE INDEX idx_cols_hash        ON puzzle_collections(content_hash);

CREATE TABLE daily_schedule (
    date             TEXT PRIMARY KEY,
    version          TEXT NOT NULL DEFAULT '3.0',
    generated_at     TEXT NOT NULL,
    technique_of_day TEXT DEFAULT '',
    attrs            TEXT DEFAULT '{}'
);

CREATE TABLE daily_puzzles (
    date         TEXT NOT NULL REFERENCES daily_schedule(date),
    content_hash TEXT NOT NULL REFERENCES puzzles(content_hash),
    section      TEXT NOT NULL,
    position     INTEGER NOT NULL,
    PRIMARY KEY (date, content_hash, section)
);

CREATE INDEX idx_daily_puzzles_date ON daily_puzzles(date);
CREATE INDEX idx_daily_puzzles_hash ON daily_puzzles(content_hash);
"""


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def _insert_puzzles(conn: sqlite3.Connection, entries: list[PuzzleEntry]) -> None:
    conn.executemany(
        "INSERT INTO puzzles "
        "(content_hash, batch, level_id, quality, content_type, "
        "cx_depth, cx_refutations, cx_solution_len, cx_unique_resp, ac, attrs) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                e.content_hash,
                e.batch,
                e.level_id,
                e.quality,
                e.content_type,
                e.cx_depth,
                e.cx_refutations,
                e.cx_solution_len,
                e.cx_unique_resp,
                e.ac,
                json.dumps(e.attrs),
            )
            for e in entries
        ],
    )


def _insert_tags(conn: sqlite3.Connection, entries: list[PuzzleEntry]) -> None:
    rows = [
        (e.content_hash, tag_id)
        for e in entries
        for tag_id in e.tag_ids
    ]
    if rows:
        conn.executemany(
            "INSERT INTO puzzle_tags (content_hash, tag_id) VALUES (?, ?)",
            rows,
        )


def _insert_puzzle_collections(
    conn: sqlite3.Connection,
    entries: list[PuzzleEntry],
    sequence_map: dict[tuple[str, int], int] | None,
    chapter_map: dict[tuple[str, int], str] | None = None,
) -> None:
    rows = [
        (
            e.content_hash,
            col_id,
            sequence_map.get((e.content_hash, col_id)) if sequence_map else None,
            chapter_map.get((e.content_hash, col_id), "") if chapter_map else "",
        )
        for e in entries
        for col_id in e.collection_ids
    ]
    if rows:
        conn.executemany(
            "INSERT INTO puzzle_collections "
            "(content_hash, collection_id, sequence_number, chapter) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )


def _insert_collections(
    conn: sqlite3.Connection,
    collections: list[CollectionMeta],
) -> None:
    conn.executemany(
        "INSERT INTO collections "
        "(collection_id, slug, name, category, puzzle_count, attrs) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                c.collection_id,
                c.slug,
                c.name,
                c.category,
                c.puzzle_count,
                json.dumps(c.attrs),
            )
            for c in collections
        ],
    )
    # Populate FTS5 index (include named chapter strings for searchability)
    conn.executemany(
        "INSERT INTO collections_fts (rowid, name, slug) VALUES (?, ?, ?)",
        [
            (
                c.collection_id,
                _fts_name_with_chapters(c.name, c.attrs),
                c.slug,
            )
            for c in collections
        ],
    )


def _fts_name_with_chapters(name: str, attrs: dict) -> str:
    """Append named chapter strings to collection name for FTS indexing.

    Integer-only chapters (e.g. "1", "3") are excluded from search text
    since they carry no semantic meaning. Named chapters like "seki" or
    "making-life" are appended as space-separated, hyphen-to-space
    converted tokens.
    """
    chapters = attrs.get("chapters", [])
    named = [ch.replace("-", " ") for ch in chapters if not ch.isdigit()]
    if not named:
        return name
    return f"{name} {' '.join(named)}"


def build_search_db(
    entries: list[PuzzleEntry],
    collections: list[CollectionMeta],
    output_path: Path,
    *,
    sequence_map: dict[tuple[str, int], int] | None = None,
    chapter_map: dict[tuple[str, int], str] | None = None,
    generated_at: str | None = None,
) -> DbVersionInfo:
    """Generate ``yengo-search.db`` with full schema.

    Parameters
    ----------
    entries:
        Puzzle rows to insert.
    collections:
        Collection catalog rows.
    output_path:
        Destination ``.db`` file path.
    sequence_map:
        Optional mapping of ``(content_hash, collection_id)`` to
        ``sequence_number`` for ordered collections.
    chapter_map:
        Optional mapping of ``(content_hash, collection_id)`` to
        chapter string from the YL property.
    generated_at:
        Optional ISO-8601 timestamp for deterministic builds. When
        omitted, defaults to ``datetime.now(UTC)``.

    Returns
    -------
    DbVersionInfo with puzzle count and generated version string.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Building search DB at %s (%d puzzles, %d collections)",
                output_path, len(entries), len(collections))

    conn = sqlite3.connect(output_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        _create_schema(conn)

        with conn:
            _insert_puzzles(conn, entries)
            _insert_tags(conn, entries)
            _insert_puzzle_collections(conn, entries, sequence_map, chapter_map)
            _insert_collections(conn, collections)
            # Compute puzzle_count from actual puzzle_collections rows (RC-4: same transaction)
            conn.execute(
                "UPDATE collections SET puzzle_count = "
                "(SELECT COUNT(*) FROM puzzle_collections "
                "WHERE collection_id = collections.collection_id)"
            )

        # Switch to DELETE journal mode for read-only distribution
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
    finally:
        conn.close()

    content_hashes = [e.content_hash for e in entries]
    version = generate_db_version(content_hashes)
    info = DbVersionInfo(
        db_version=version,
        puzzle_count=len(entries),
        generated_at=generated_at or datetime.now(UTC).isoformat(),
    )

    logger.info("Search DB built: version=%s, puzzles=%d", version, len(entries))
    return info
