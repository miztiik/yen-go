"""Per-external-source SQLite ingest state database.

One ``.yengo-ingest.sqlite`` file lives co-located with each external source at
``<source.path>/.yengo-ingest.sqlite``. It owns content-aware skip, resume, and
rename detection for that single source.

Schema reference: ``config/schemas/db-source-ingest.schema.json``
Design doc:       ``docs/architecture/backend/source-ingest-db.md``

This module is the single writer/reader. Adapters consume it; ``IngestStage``
opens it (passing ``run_id``); ``core/`` has no reverse dependency on adapters.

Key properties:
- WAL journal mode + 5s busy timeout for safe concurrent reads.
- Tier-3 always-rehash skip policy (no mtime trust); ``mtime_ns`` and
  ``size_bytes`` are stored for diagnostics, not skip decisions.
- Rename detection by ``content_hash`` with most-recent-``run_id`` tiebreak.
- No denormalized counters; progress is a live ``GROUP BY status`` query.
- Schema versioning via ``meta.schema_version`` + a migrator chain.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CURRENT_SCHEMA_VERSION: int = 1
INGEST_DB_FORMAT: str = "yengo-source-ingest"
DB_FILENAME: str = ".yengo-ingest.sqlite"
BUSY_TIMEOUT_MS: int = 5000


class FileStatus(IntEnum):
    """Status codes stored in ``files.status``."""

    INGESTED = 0
    SKIPPED = 1
    FAILED = 2


# --------------------------------------------------------------------------- #
# Schema (v1)
# --------------------------------------------------------------------------- #

_SCHEMA_SQL_V1 = """\
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS files (
    rel_path     TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    size_bytes   INTEGER NOT NULL,
    mtime_ns     INTEGER NOT NULL,
    status       INTEGER NOT NULL,
    skip_reason  TEXT,
    run_id       TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_files_hash   ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_files_run    ON files(run_id);
"""


# --------------------------------------------------------------------------- #
# Migration chain
# --------------------------------------------------------------------------- #
#
# To add a v2:
#   1. Define ``_SCHEMA_SQL_V2`` (or a delta DDL).
#   2. Add ``def _migrate_v1_to_v2(conn): ...``.
#   3. Register in ``_MIGRATIONS``.
#   4. Bump ``CURRENT_SCHEMA_VERSION``.
#   5. Update ``config/schemas/db-source-ingest.schema.json``.
#

_MIGRATIONS: dict[int, "callable"] = {
    # from_version: callable(conn) -> None  (advances to from_version + 1)
}


# --------------------------------------------------------------------------- #
# Public dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FileRecord:
    """One row from the ``files`` table."""

    rel_path: str
    content_hash: str
    size_bytes: int
    mtime_ns: int
    status: FileStatus
    skip_reason: str | None
    run_id: str


@dataclass(frozen=True)
class IngestProgress:
    """Live progress snapshot derived from ``GROUP BY status``."""

    ingested: int
    skipped: int
    failed: int

    @property
    def total(self) -> int:
        return self.ingested + self.skipped + self.failed


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class SourceIngestDBError(Exception):
    """Base error for the source ingest DB."""


class SchemaVersionError(SourceIngestDBError):
    """Raised when the on-disk schema version is newer than this code knows."""


class SourceIdMismatchError(SourceIngestDBError):
    """Raised when opening with a source_id different from the stored one."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def db_path_for_source(source_path: Path) -> Path:
    """Return the canonical SQLite path for a source root.

    The DB sits *inside* the source directory so it travels with the data.
    """
    return Path(source_path) / DB_FILENAME


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# SourceIngestDB
# --------------------------------------------------------------------------- #


class SourceIngestDB:
    """Per-source ingest state database.

    Use :meth:`open` to create or attach. Always close explicitly (or use as a
    context manager). ``run_id`` is required at open time so every row written
    during the session can be tagged consistently.
    """

    # ------------------------------------------------------------------ #
    # Construction / connection lifecycle
    # ------------------------------------------------------------------ #

    def __init__(self, conn: sqlite3.Connection, *, source_id: str, run_id: str, db_path: Path) -> None:
        self._conn = conn
        self._source_id = source_id
        self._run_id = run_id
        self._db_path = db_path
        self._closed = False

    @classmethod
    def open(
        cls,
        source_path: Path | str,
        *,
        source_id: str,
        run_id: str,
    ) -> "SourceIngestDB":
        """Open (creating if needed) the DB at ``<source_path>/.yengo-ingest.sqlite``.

        Args:
            source_path: External source root directory. Created if missing.
            source_id: Source identifier from sources.json. Validated against
                ``meta.source_id`` if the DB already exists.
            run_id: Current pipeline run identifier. Tagged on every row written
                during this session and stored in ``meta.last_run_id``.

        Raises:
            SchemaVersionError: If the DB schema is newer than this code.
            SourceIdMismatchError: If ``source_id`` doesn't match the stored value.
        """
        source_dir = Path(source_path)
        source_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_path_for_source(source_dir)

        is_new = not db_path.exists()
        conn = sqlite3.connect(
            str(db_path),
            timeout=BUSY_TIMEOUT_MS / 1000,
            isolation_level=None,  # we drive transactions explicitly
            check_same_thread=False,
        )
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")

        if is_new:
            cls._initialize(conn, source_id=source_id, run_id=run_id)
        else:
            cls._validate_and_migrate(conn, source_id=source_id)
            cls._touch_run(conn, run_id=run_id)

        return cls(conn, source_id=source_id, run_id=run_id, db_path=db_path)

    # Allow use as a context manager.
    def __enter__(self) -> "SourceIngestDB":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._conn.commit()
        finally:
            self._conn.close()
            self._closed = True

    # ------------------------------------------------------------------ #
    # Schema bootstrap & migration
    # ------------------------------------------------------------------ #

    @staticmethod
    def _initialize(conn: sqlite3.Connection, *, source_id: str, run_id: str) -> None:
        """Create schema + meta rows on a fresh DB."""
        with conn:  # implicit BEGIN/COMMIT
            conn.executescript(_SCHEMA_SQL_V1)
            now = _utc_now_iso()
            conn.executemany(
                "INSERT INTO meta(key, value) VALUES (?, ?)",
                [
                    ("schema_version", str(CURRENT_SCHEMA_VERSION)),
                    ("ingest_db_format", INGEST_DB_FORMAT),
                    ("source_id", source_id),
                    ("created_run_id", run_id),
                    ("last_run_id", run_id),
                    ("last_run_at", now),
                ],
            )
        logger.info(
            "Initialized source ingest DB: source_id=%s run_id=%s", source_id, run_id
        )

    @staticmethod
    def _validate_and_migrate(conn: sqlite3.Connection, *, source_id: str) -> None:
        """Validate format/source binding and apply any pending migrations."""
        rows = dict(conn.execute("SELECT key, value FROM meta").fetchall())

        fmt = rows.get("ingest_db_format")
        if fmt != INGEST_DB_FORMAT:
            raise SourceIngestDBError(
                f"Unexpected ingest_db_format: {fmt!r} (expected {INGEST_DB_FORMAT!r})"
            )

        stored_source = rows.get("source_id")
        if stored_source and stored_source != source_id:
            raise SourceIdMismatchError(
                f"DB belongs to source_id={stored_source!r}, "
                f"but caller passed source_id={source_id!r}"
            )

        try:
            on_disk_version = int(rows.get("schema_version", "0"))
        except ValueError as exc:
            raise SourceIngestDBError(
                f"Invalid schema_version in meta: {rows.get('schema_version')!r}"
            ) from exc

        if on_disk_version > CURRENT_SCHEMA_VERSION:
            raise SchemaVersionError(
                f"DB schema version {on_disk_version} is newer than supported "
                f"({CURRENT_SCHEMA_VERSION}). Upgrade puzzle_manager."
            )

        # Apply migrations in order.
        while on_disk_version < CURRENT_SCHEMA_VERSION:
            migrator = _MIGRATIONS.get(on_disk_version)
            if migrator is None:
                raise SourceIngestDBError(
                    f"No migrator registered for schema v{on_disk_version} "
                    f"-> v{on_disk_version + 1}"
                )
            logger.info(
                "Migrating source ingest DB schema: v%d -> v%d",
                on_disk_version,
                on_disk_version + 1,
            )
            with conn:
                migrator(conn)
                on_disk_version += 1
                conn.execute(
                    "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                    (str(on_disk_version),),
                )

    @staticmethod
    def _touch_run(conn: sqlite3.Connection, *, run_id: str) -> None:
        """Update last_run_id / last_run_at on open."""
        with conn:
            conn.executemany(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [
                    ("last_run_id", run_id),
                    ("last_run_at", _utc_now_iso()),
                ],
            )

    # ------------------------------------------------------------------ #
    # Public properties
    # ------------------------------------------------------------------ #

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def schema_version(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------ #
    # Row CRUD
    # ------------------------------------------------------------------ #

    def upsert(
        self,
        *,
        rel_path: str,
        content_hash: str,
        size_bytes: int,
        mtime_ns: int,
        status: FileStatus = FileStatus.INGESTED,
        skip_reason: str | None = None,
    ) -> None:
        """Insert or replace a row, tagging with the session's ``run_id``."""
        self._conn.execute(
            "INSERT INTO files "
            "(rel_path, content_hash, size_bytes, mtime_ns, status, skip_reason, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(rel_path) DO UPDATE SET "
            "  content_hash = excluded.content_hash, "
            "  size_bytes   = excluded.size_bytes, "
            "  mtime_ns     = excluded.mtime_ns, "
            "  status       = excluded.status, "
            "  skip_reason  = excluded.skip_reason, "
            "  run_id       = excluded.run_id",
            (
                rel_path,
                content_hash,
                int(size_bytes),
                int(mtime_ns),
                int(status),
                skip_reason,
                self._run_id,
            ),
        )

    def upsert_many(self, records: Iterator["FileRecord"]) -> int:
        """Bulk upsert; returns count written. Caller controls transaction."""
        rows = [
            (
                r.rel_path,
                r.content_hash,
                int(r.size_bytes),
                int(r.mtime_ns),
                int(r.status),
                r.skip_reason,
                self._run_id,
            )
            for r in records
        ]
        self._conn.executemany(
            "INSERT INTO files "
            "(rel_path, content_hash, size_bytes, mtime_ns, status, skip_reason, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(rel_path) DO UPDATE SET "
            "  content_hash = excluded.content_hash, "
            "  size_bytes   = excluded.size_bytes, "
            "  mtime_ns     = excluded.mtime_ns, "
            "  status       = excluded.status, "
            "  skip_reason  = excluded.skip_reason, "
            "  run_id       = excluded.run_id",
            rows,
        )
        return len(rows)

    def find_by_path(self, rel_path: str) -> FileRecord | None:
        row = self._conn.execute(
            "SELECT rel_path, content_hash, size_bytes, mtime_ns, status, skip_reason, run_id "
            "FROM files WHERE rel_path = ?",
            (rel_path,),
        ).fetchone()
        return _row_to_record(row) if row else None

    def find_by_hash(self, content_hash: str) -> list[FileRecord]:
        """All rows with this content hash (typically 0 or 1, occasionally 2+ for copies)."""
        rows = self._conn.execute(
            "SELECT rel_path, content_hash, size_bytes, mtime_ns, status, skip_reason, run_id "
            "FROM files WHERE content_hash = ?",
            (content_hash,),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def rename(self, *, old_rel_path: str, new_rel_path: str) -> bool:
        """Update rel_path in place; tag with current run_id. Returns True if a row moved."""
        cur = self._conn.execute(
            "UPDATE files SET rel_path = ?, run_id = ? WHERE rel_path = ?",
            (new_rel_path, self._run_id, old_rel_path),
        )
        return cur.rowcount > 0

    def delete(self, rel_path: str) -> bool:
        cur = self._conn.execute("DELETE FROM files WHERE rel_path = ?", (rel_path,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    # Aggregates
    # ------------------------------------------------------------------ #

    def progress(self) -> IngestProgress:
        """Live status counts via indexed GROUP BY (sub-ms even at 100k rows)."""
        counts = {0: 0, 1: 0, 2: 0}
        for status, n in self._conn.execute(
            "SELECT status, COUNT(*) FROM files GROUP BY status"
        ):
            if status in counts:
                counts[status] = n
        return IngestProgress(
            ingested=counts[FileStatus.INGESTED],
            skipped=counts[FileStatus.SKIPPED],
            failed=counts[FileStatus.FAILED],
        )

    def total_files(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------ #
    # Transactions & maintenance
    # ------------------------------------------------------------------ #

    def commit(self) -> None:
        self._conn.commit()

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def vacuum(self) -> None:
        """Reclaim space; safe to run between batches."""
        self._conn.execute("VACUUM")

    @staticmethod
    def wipe(source_path: Path | str) -> bool:
        """Delete the SQLite (and WAL/SHM sidecars) for a source. Idempotent.

        Returns True if any artifact was removed.
        """
        source_dir = Path(source_path)
        base = db_path_for_source(source_dir)
        removed = False
        for suffix in ("", "-wal", "-shm", "-journal"):
            target = base.with_name(base.name + suffix) if suffix else base
            if target.exists():
                try:
                    target.unlink()
                    removed = True
                except OSError as exc:
                    logger.warning("Failed to remove %s: %s", target, exc)
        if removed:
            logger.info("Wiped source ingest DB at %s", base)
        return removed


# --------------------------------------------------------------------------- #
# Legacy AdapterCheckpoint migrator (one-shot, idempotent)
# --------------------------------------------------------------------------- #


def migrate_legacy_checkpoint(
    source_path: Path | str,
    *,
    source_id: str,
    run_id: str,
) -> bool:
    """Migrate a legacy ``<source_id>_checkpoint.json`` to the new SourceIngestDB.

    Behavior (all idempotent):

    1. If ``.yengo-ingest.sqlite`` already exists for this source -> no-op.
    2. Else if ``.pm-runtime/state/<source_id>_checkpoint.json`` exists -> read
       its ``total_processed`` / ``total_failed`` counters, create the new DB,
       seed ``meta`` with the historical counts, then delete the JSON.
       No per-file rows are migrated (the next ingest walk will populate them
       on hash verification).
    3. Else -> no-op.

    Returns True if a migration was performed.
    """
    from backend.puzzle_manager.paths import get_pm_state_dir

    src_dir = Path(source_path)
    new_db = db_path_for_source(src_dir)
    if new_db.exists():
        return False

    legacy = get_pm_state_dir() / f"{source_id}_checkpoint.json"
    if not legacy.exists():
        return False

    # Read legacy counters defensively; treat any read error as "no historical data".
    legacy_data: dict = {}
    try:
        import json as _json
        legacy_data = _json.loads(legacy.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not parse legacy checkpoint %s: %s", legacy, exc)

    total_processed = int(legacy_data.get("total_processed") or 0)
    total_failed = int(legacy_data.get("total_failed") or 0)

    # Create the new DB by opening + closing it; seed extra meta keys.
    with SourceIngestDB.open(src_dir, source_id=source_id, run_id=run_id) as db:
        db._conn.executemany(  # noqa: SLF001 - intentional one-shot internal write
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            [
                ("legacy_total_processed", str(total_processed)),
                ("legacy_total_failed", str(total_failed)),
                ("legacy_migrated_at", _utc_now_iso()),
            ],
        )
        db.commit()

    try:
        legacy.unlink()
    except OSError as exc:
        logger.warning("Migrated legacy checkpoint but could not delete %s: %s", legacy, exc)

    logger.info(
        "Migrated legacy checkpoint for '%s' (processed=%d, failed=%d) -> %s",
        source_id,
        total_processed,
        total_failed,
        new_db,
    )
    return True


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _row_to_record(row: tuple) -> FileRecord:
    return FileRecord(
        rel_path=row[0],
        content_hash=row[1],
        size_bytes=int(row[2]),
        mtime_ns=int(row[3]),
        status=FileStatus(int(row[4])),
        skip_reason=row[5],
        run_id=row[6],
    )
