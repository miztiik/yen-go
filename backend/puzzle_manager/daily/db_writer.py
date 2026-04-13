"""Pure persistence module for daily challenge data.

Writes daily schedule and puzzle rows to yengo-search.db.
Takes (db_path, data) → writes rows. No generator imports.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.daily import DailyChallenge, PuzzleRef

logger = logging.getLogger("puzzle_manager.daily")

# Section constants (RK-2 mitigation)
SECTION_STANDARD = "standard"
SECTION_TIMED_BLITZ = "timed_blitz"
SECTION_TIMED_SPRINT = "timed_sprint"
SECTION_TIMED_ENDURANCE = "timed_endurance"
SECTION_BY_TAG = "by_tag"

# Map timed set names to section constants
_TIMED_SECTION_MAP: dict[str, str] = {
    "blitz": SECTION_TIMED_BLITZ,
    "sprint": SECTION_TIMED_SPRINT,
    "endurance": SECTION_TIMED_ENDURANCE,
}


def _extract_content_hash(puzzle_ref_path: str) -> str:
    """Extract content_hash from a PuzzleRef path like 'sgf/0001/abc123.sgf'."""
    filename = puzzle_ref_path.rsplit("/", 1)[-1]
    if filename.endswith(".sgf"):
        return filename[:-4]
    return filename


def inject_daily_schedule(
    db_path: Path,
    challenges: list[DailyChallenge],
) -> int:
    """Write daily schedule and puzzle rows to yengo-search.db.

    Uses INSERT OR REPLACE for idempotent writes. Safe to call
    from both publish post-step and CLI daily command.

    Args:
        db_path: Path to yengo-search.db.
        challenges: List of DailyChallenge objects to persist.

    Returns:
        Number of daily_schedule rows written.

    Raises:
        DailyGenerationError: On any database error.
    """
    if not challenges:
        return 0

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("PRAGMA foreign_keys=ON")

            with conn:
                for challenge in challenges:
                    _insert_challenge(conn, challenge)

        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise DailyGenerationError(
            f"Failed to write daily schedule to {db_path}: {exc}"
        ) from exc

    logger.info("Injected %d daily schedule(s) into %s", len(challenges), db_path.name)
    return len(challenges)


def _insert_challenge(conn: sqlite3.Connection, challenge: DailyChallenge) -> None:
    """Insert a single DailyChallenge into daily_schedule + daily_puzzles."""
    date_str = challenge.date
    generated_at = challenge.generated_at.isoformat()

    # Build attrs JSON for extensibility
    attrs: dict = {}
    if challenge.config_used:
        attrs["config_snapshot"] = challenge.config_used.model_dump()

    conn.execute(
        "INSERT OR REPLACE INTO daily_schedule "
        "(date, version, generated_at, technique_of_day, attrs) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            date_str,
            challenge.version,
            generated_at,
            challenge.technique_of_day,
            json.dumps(attrs),
        ),
    )

    # Clear any existing puzzle rows for this date (idempotent replace)
    conn.execute("DELETE FROM daily_puzzles WHERE date = ?", (date_str,))

    # Insert standard puzzles
    _insert_puzzle_refs(
        conn, date_str, SECTION_STANDARD, challenge.standard.puzzles
    )

    # Insert timed puzzles
    for timed_set in challenge.timed.sets:
        section = _TIMED_SECTION_MAP.get(
            timed_set.name.lower(),
            f"timed_{timed_set.set_number}",
        )
        _insert_puzzle_refs(conn, date_str, section, timed_set.puzzles)

    # Insert by_tag puzzles
    for _tag_name, tag_challenge in challenge.by_tag.items():
        _insert_puzzle_refs(
            conn, date_str, SECTION_BY_TAG, tag_challenge.puzzles
        )


def _insert_puzzle_refs(
    conn: sqlite3.Connection,
    date_str: str,
    section: str,
    puzzle_refs: list[PuzzleRef],
) -> None:
    """Insert puzzle references for a section."""
    rows = []
    for position, ref in enumerate(puzzle_refs):
        content_hash = _extract_content_hash(ref.path)
        rows.append((date_str, content_hash, section, position))

    if rows:
        conn.executemany(
            "INSERT OR IGNORE INTO daily_puzzles "
            "(date, content_hash, section, position) VALUES (?, ?, ?, ?)",
            rows,
        )


def prune_daily_window(
    db_path: Path,
    rolling_window_days: int,
) -> int:
    """Remove daily schedule rows older than the rolling window.

    Constraint C6: Current date and future dates are NEVER pruned.
    Only dates strictly before (today - rolling_window_days) are removed.

    Args:
        db_path: Path to yengo-search.db.
        rolling_window_days: Number of days to retain.

    Returns:
        Number of daily_schedule rows deleted.

    Raises:
        DailyGenerationError: On any database error.
    """
    today = date.today()
    cutoff = (today - timedelta(days=rolling_window_days)).isoformat()
    today_str = today.isoformat()

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("PRAGMA foreign_keys=ON")

            with conn:
                # Delete puzzle rows first (FK constraint)
                conn.execute(
                    "DELETE FROM daily_puzzles WHERE date < ? AND date < ?",
                    (cutoff, today_str),
                )
                cursor = conn.execute(
                    "DELETE FROM daily_schedule WHERE date < ? AND date < ?",
                    (cutoff, today_str),
                )
                deleted = cursor.rowcount

        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise DailyGenerationError(
            f"Failed to prune daily window in {db_path}: {exc}"
        ) from exc

    if deleted > 0:
        logger.info("Pruned %d expired daily schedule(s) from %s", deleted, db_path.name)
    return deleted
