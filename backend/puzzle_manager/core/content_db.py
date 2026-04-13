"""yengo-content.db — full SGF content + canonical position hash + solution fingerprint for duplicate detection."""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.core.sgf_parser import SolutionNode, parse_sgf
from backend.puzzle_manager.paths import rel_path

logger = logging.getLogger(__name__)

# Solution fingerprint algorithm version.
# Bump when serialization logic changes (e.g. adding ko-state awareness).
FINGERPRINT_VERSION: int = 1

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS sgf_files (
    content_hash          TEXT PRIMARY KEY,
    sgf_content           TEXT NOT NULL,
    position_hash         TEXT,
    solution_fingerprint  TEXT,
    fingerprint_version   INTEGER NOT NULL DEFAULT 1,
    board_size            INTEGER NOT NULL DEFAULT 19,
    black_stones          TEXT NOT NULL,
    white_stones          TEXT NOT NULL,
    first_player          TEXT NOT NULL DEFAULT 'B',
    stone_count           INTEGER NOT NULL DEFAULT 0,
    source                TEXT,
    created_at            TEXT,
    batch                 TEXT,
    collection_slug       TEXT
);

CREATE INDEX IF NOT EXISTS idx_sgf_position   ON sgf_files(position_hash);
CREATE INDEX IF NOT EXISTS idx_sgf_stones     ON sgf_files(board_size, stone_count);
CREATE INDEX IF NOT EXISTS idx_sgf_source     ON sgf_files(source);
"""

_RE_BOARD_SIZE = re.compile(r"SZ\[(\d+)\]")
_RE_BLACK_STONES = re.compile(r"AB(?:\[([a-s]{2})\])+")
_RE_WHITE_STONES = re.compile(r"AW(?:\[([a-s]{2})\])+")
_RE_FIRST_PLAYER = re.compile(r"PL\[(B|W)\]")
# Individual stone coordinate extraction within AB[...][...] and AW[...][...]
_RE_STONE_COORD = re.compile(r"\[([a-s]{2})\]")
_RE_COLLECTION_SLUG = re.compile(r"YL\[([^\]:,]+)")


def canonical_position_hash(
    board_size: int,
    black_stones: list[str],
    white_stones: list[str],
    first_player: str,
) -> str:
    """Position-based hash. Sorted AB/AW makes it parse-order independent."""
    b_sorted = ",".join(sorted(black_stones))
    w_sorted = ",".join(sorted(white_stones))
    canonical = f"SZ{board_size}:B[{b_sorted}]:W[{w_sorted}]:PL[{first_player}]"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _serialize_solution_node(node: SolutionNode) -> str:
    """Serialize a single SolutionNode to a canonical token.

    Format: {color}{move_sgf}{'!' if correct else '?'}
    Example: ``Bds!``, ``Wcs?``
    """
    from backend.puzzle_manager.core.primitives import Color

    color = node.color.value if node.color else "B"
    move = node.move.to_sgf() if node.move else ""
    flag = "!" if node.is_correct else "?"
    return f"{color}{move}{flag}"


def _serialize_tree(node: SolutionNode) -> str:
    """Recursively serialize the solution tree for fingerprinting.

    Rules:
    - Depth-first traversal
    - Children sorted lexicographically by their serialized token
    - Multiple children → parenthesized groups, sorted
    - Single child → no parens
    - Root node (no move) → only serialize children
    """
    if not node.children:
        return ""

    child_parts: list[str] = []
    for child in node.children:
        token = _serialize_solution_node(child)
        subtree = _serialize_tree(child)
        child_parts.append(token + subtree)

    child_parts.sort()

    if len(child_parts) == 1:
        return child_parts[0]
    return "".join(f"({part})" for part in child_parts)


def compute_solution_fingerprint(solution_tree: SolutionNode) -> str:
    """Compute a canonical fingerprint of the solution tree.

    The fingerprint is insensitive to comments, whitespace, YenGo properties,
    and SGF branch ordering. Only move coordinates, colors, and correctness
    flags contribute.

    Args:
        solution_tree: Root SolutionNode (from SGFGame.solution_tree).

    Returns:
        16-character lowercase hex SHA256 hash of the canonical serialization.
    """
    serialized = _serialize_tree(solution_tree)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _extract_stone_list(sgf_content: str, property_name: str) -> list[str]:
    """Extract all stone coordinates from an SGF property like AB or AW.

    Handles ``AB[pd][qd][rd]`` by finding the property token and then
    collecting all consecutive ``[xy]`` coordinate brackets.
    """
    pattern = re.compile(rf"{property_name}((?:\[[a-s]{{2}}\])+)")
    stones: list[str] = []
    for match in pattern.finditer(sgf_content):
        coords_block = match.group(1)
        stones.extend(_RE_STONE_COORD.findall(coords_block))
    return stones


def extract_position_data(sgf_content: str) -> dict[str, object]:
    """Parse SGF to extract board setup properties.

    Returns dict with keys: board_size, black_stones, white_stones,
    first_player, stone_count.
    """
    sz_match = _RE_BOARD_SIZE.search(sgf_content)
    board_size = int(sz_match.group(1)) if sz_match else 19

    black_stones = _extract_stone_list(sgf_content, "AB")
    white_stones = _extract_stone_list(sgf_content, "AW")

    pl_match = _RE_FIRST_PLAYER.search(sgf_content)
    first_player = pl_match.group(1) if pl_match else "B"

    stone_count = len(black_stones) + len(white_stones)

    return {
        "board_size": board_size,
        "black_stones": black_stones,
        "white_stones": white_stones,
        "first_player": first_player,
        "stone_count": stone_count,
    }


def _extract_collection_slug(sgf_content: str) -> str | None:
    """Extract first collection slug from YL[] property.

    Handles: no YL, YL with chapter/position suffix (``YL[slug:3/12]``),
    YL with comma-separated slugs (``YL[a,b]`` → ``"a"``).
    """
    match = _RE_COLLECTION_SLUG.search(sgf_content)
    return match.group(1) if match else None


def build_content_db(
    sgf_files: dict[str, str],
    output_path: Path,
    source: str | None = None,
    batch: str | None = None,
) -> None:
    """Generate yengo-content.db with full SGF + position hash.

    Args:
        sgf_files: Mapping of content_hash → sgf_content.
        output_path: Path for the resulting SQLite database file.
        source: Optional source tag applied to all entries.
        batch: Optional batch identifier (e.g. "0001") for all entries.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Building content DB at %s (%d SGFs)", output_path, len(sgf_files))

    now = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(str(output_path))
    try:
        conn.executescript(_SCHEMA_SQL)
        _ensure_batch_column(conn)
        _ensure_collection_slug_column(conn)
        _ensure_fingerprint_columns(conn)

        rows: list[tuple[str, str, str, str | None, int, int, str, str, str, int, str | None, str, str | None, str | None]] = []
        for content_hash, sgf_content in sgf_files.items():
            pos = extract_position_data(sgf_content)
            black: list[str] = pos["black_stones"]  # type: ignore[assignment]
            white: list[str] = pos["white_stones"]  # type: ignore[assignment]
            board_size: int = pos["board_size"]  # type: ignore[assignment]
            first_player: str = pos["first_player"]  # type: ignore[assignment]
            stone_count: int = pos["stone_count"]  # type: ignore[assignment]

            position_hash = canonical_position_hash(
                board_size, black, white, first_player,
            )

            # Compute solution fingerprint from parsed tree
            sol_fp: str | None = None
            try:
                game = parse_sgf(sgf_content)
                sol_fp = compute_solution_fingerprint(game.solution_tree)
            except Exception:
                logger.debug("Could not compute solution fingerprint for %s", content_hash)

            collection_slug = _extract_collection_slug(sgf_content)

            rows.append((
                content_hash,
                sgf_content,
                position_hash,
                sol_fp,
                FINGERPRINT_VERSION,
                board_size,
                ",".join(sorted(black)),
                ",".join(sorted(white)),
                first_player,
                stone_count,
                source,
                now,
                batch,
                collection_slug,
            ))

        conn.executemany(
            "INSERT OR REPLACE INTO sgf_files "
            "(content_hash, sgf_content, position_hash, solution_fingerprint, fingerprint_version, "
            "board_size, black_stones, white_stones, first_player, stone_count, source, created_at, "
            "batch, collection_slug) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()

        conn.execute("ANALYZE")
        conn.execute("VACUUM")
        logger.info("Content DB complete — %d rows written", len(rows))
    finally:
        conn.close()


def read_all_entries(db_path: Path) -> list[dict[str, object]]:
    """Read all entries from yengo-content.db for incremental publish merge.

    Returns list of dicts with keys: content_hash, sgf_content, position_hash,
    board_size, source, batch, solution_fingerprint, fingerprint_version.
    """
    if not db_path.exists():
        logger.info("Content DB not found at %s, returning empty list", rel_path(db_path))
        return []

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        # Check if fingerprint columns exist (handles pre-fingerprint databases)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
        has_fp = "solution_fingerprint" in cols

        if has_fp:
            rows = conn.execute(
                "SELECT content_hash, sgf_content, position_hash, board_size, source, batch, "
                "solution_fingerprint, fingerprint_version "
                "FROM sgf_files ORDER BY content_hash"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT content_hash, sgf_content, position_hash, board_size, source, batch "
                "FROM sgf_files ORDER BY content_hash"
            ).fetchall()

        return [
            {
                "content_hash": r[0],
                "sgf_content": r[1],
                "position_hash": r[2],
                "board_size": r[3],
                "source": r[4],
                "batch": r[5],
                **({"solution_fingerprint": r[6], "fingerprint_version": r[7]} if has_fp else {}),
            }
            for r in rows
        ]
    finally:
        conn.close()


def delete_entries(db_path: Path, content_hashes: list[str]) -> int:
    """Delete entries from content DB by content_hash.

    Returns number of rows deleted.
    """
    if not db_path.exists() or not content_hashes:
        return 0

    conn = sqlite3.connect(str(db_path))
    try:
        placeholders = ",".join("?" for _ in content_hashes)
        cursor = conn.execute(
            f"DELETE FROM sgf_files WHERE content_hash IN ({placeholders})",
            content_hashes,
        )
        conn.commit()
        deleted = cursor.rowcount
        logger.info("Deleted %d entries from content DB", deleted)
        return deleted
    finally:
        conn.close()


def vacuum_orphans(db_path: Path, published_hashes: set[str]) -> int:
    """Remove orphaned entries from content DB.

    Deletes rows whose content_hash is NOT in the published_hashes set.
    Returns number of orphaned rows removed.
    """
    if not db_path.exists():
        return 0

    conn = sqlite3.connect(str(db_path))
    try:
        all_hashes = [r[0] for r in conn.execute("SELECT content_hash FROM sgf_files").fetchall()]
        orphans = [h for h in all_hashes if h not in published_hashes]
        if not orphans:
            logger.info("No orphaned entries found in content DB")
            return 0

        placeholders = ",".join("?" for _ in orphans)
        conn.execute(f"DELETE FROM sgf_files WHERE content_hash IN ({placeholders})", orphans)
        conn.commit()
        conn.execute("VACUUM")
        logger.info("Removed %d orphaned entries from content DB", len(orphans))
        return len(orphans)
    finally:
        conn.close()


def _ensure_batch_column(conn: sqlite3.Connection) -> None:
    """Add batch column to existing content DB if missing (schema migration)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
    if "batch" not in cols:
        conn.execute("ALTER TABLE sgf_files ADD COLUMN batch TEXT")
        logger.info("Migrated content DB schema: added batch column")


def _ensure_collection_slug_column(conn: sqlite3.Connection) -> None:
    """Add collection_slug column and index to existing content DB if missing (schema migration)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
    if "collection_slug" not in cols:
        conn.execute("ALTER TABLE sgf_files ADD COLUMN collection_slug TEXT")
        logger.info("Migrated content DB schema: added collection_slug column")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sgf_collection ON sgf_files(collection_slug)"
    )


def _ensure_fingerprint_columns(conn: sqlite3.Connection) -> None:
    """Add solution_fingerprint and fingerprint_version columns if missing (schema migration)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sgf_files)")}
    if "solution_fingerprint" not in cols:
        conn.execute("ALTER TABLE sgf_files ADD COLUMN solution_fingerprint TEXT")
        logger.info("Migrated content DB schema: added solution_fingerprint column")
    if "fingerprint_version" not in cols:
        conn.execute(
            "ALTER TABLE sgf_files ADD COLUMN fingerprint_version INTEGER NOT NULL DEFAULT 1"
        )
        logger.info("Migrated content DB schema: added fingerprint_version column")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sgf_pos_sol ON sgf_files(position_hash, solution_fingerprint)"
    )


def backfill_batch_column(db_path: Path, sgf_dir: Path) -> int:
    """Backfill batch column for existing yengo-content.db entries from filesystem.

    Scans sgf_dir for batch directories and updates rows with NULL batch.

    Returns number of rows updated.
    """
    if not db_path.exists() or not sgf_dir.exists():
        return 0

    # Build hash→batch index from filesystem (one pass)
    hash_to_batch: dict[str, str] = {}
    for batch_dir in sorted(sgf_dir.iterdir()):
        if batch_dir.is_dir():
            for sgf_file in batch_dir.glob("*.sgf"):
                hash_to_batch[sgf_file.stem] = batch_dir.name

    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_batch_column(conn)
        nulls = conn.execute(
            "SELECT content_hash FROM sgf_files WHERE batch IS NULL"
        ).fetchall()
        updated = 0
        for (ch,) in nulls:
            batch = hash_to_batch.get(ch)
            if batch:
                conn.execute(
                    "UPDATE sgf_files SET batch = ? WHERE content_hash = ?",
                    (batch, ch),
                )
                updated += 1
        conn.commit()
        logger.info("Backfilled batch column for %d/%d entries", updated, len(nulls))
        return updated
    finally:
        conn.close()
