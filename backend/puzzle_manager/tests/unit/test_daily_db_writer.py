"""Unit tests for daily/db_writer.py — inject and prune functions."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.puzzle_manager.core.db_builder import build_search_db
from backend.puzzle_manager.core.db_models import PuzzleEntry
from backend.puzzle_manager.daily.db_writer import (
    inject_daily_schedule,
    prune_daily_window,
)
from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.daily import (
    DailyChallenge,
    PuzzleRef,
    StandardDaily,
)


@pytest.fixture
def daily_db(tmp_path: Path) -> Path:
    """Create a minimal yengo-search.db with the daily tables and some puzzles."""
    db_path = tmp_path / "yengo-search.db"
    entries = [
        PuzzleEntry(content_hash=f"{i:016x}", batch="0001", level_id=120, tag_ids=[], collection_ids=[])
        for i in range(10)
    ]
    build_search_db(entries, [], db_path)
    return db_path


def _make_challenge(date_str: str, puzzle_hashes: list[str] | None = None) -> DailyChallenge:
    """Create a minimal DailyChallenge for testing."""
    if puzzle_hashes is None:
        puzzle_hashes = [f"{i:016x}" for i in range(3)]

    refs = [PuzzleRef(level="beginner", path=f"0001/{h}") for h in puzzle_hashes]
    return DailyChallenge(
        date=date_str,
        standard=StandardDaily(puzzles=refs, total=len(refs)),
        technique_of_day="life-and-death",
    )


@pytest.mark.unit
class TestInjectDailySchedule:
    """Tests for inject_daily_schedule()."""

    def test_inject_single_challenge(self, daily_db: Path) -> None:
        challenge = _make_challenge("2026-03-15")
        count = inject_daily_schedule(daily_db, [challenge])
        assert count == 1

        conn = sqlite3.connect(str(daily_db))
        row = conn.execute("SELECT * FROM daily_schedule WHERE date = '2026-03-15'").fetchone()
        conn.close()
        assert row is not None

    def test_inject_writes_puzzle_rows(self, daily_db: Path) -> None:
        challenge = _make_challenge("2026-03-15")
        inject_daily_schedule(daily_db, [challenge])

        conn = sqlite3.connect(str(daily_db))
        rows = conn.execute(
            "SELECT * FROM daily_puzzles WHERE date = '2026-03-15'"
        ).fetchall()
        conn.close()
        assert len(rows) == 3

    def test_inject_is_idempotent(self, daily_db: Path) -> None:
        challenge = _make_challenge("2026-03-15")
        inject_daily_schedule(daily_db, [challenge])
        inject_daily_schedule(daily_db, [challenge])

        conn = sqlite3.connect(str(daily_db))
        rows = conn.execute(
            "SELECT * FROM daily_schedule WHERE date = '2026-03-15'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_inject_empty_list_returns_zero(self, daily_db: Path) -> None:
        assert inject_daily_schedule(daily_db, []) == 0

    def test_inject_multiple_dates(self, daily_db: Path) -> None:
        challenges = [
            _make_challenge("2026-03-15"),
            _make_challenge("2026-03-16"),
        ]
        count = inject_daily_schedule(daily_db, challenges)
        assert count == 2

    def test_inject_raises_on_bad_db(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "nonexistent.db"
        bad_path.write_text("not a database")
        challenge = _make_challenge("2026-03-15")
        with pytest.raises(DailyGenerationError):
            inject_daily_schedule(bad_path, [challenge])


@pytest.mark.unit
class TestPruneDailyWindow:
    """Tests for prune_daily_window()."""

    def test_prune_removes_old_dates(self, daily_db: Path) -> None:
        old_date = (date.today() - timedelta(days=200)).isoformat()
        challenge = _make_challenge(old_date)
        inject_daily_schedule(daily_db, [challenge])

        deleted = prune_daily_window(daily_db, rolling_window_days=90)
        assert deleted == 1

    def test_prune_keeps_recent_dates(self, daily_db: Path) -> None:
        recent_date = date.today().isoformat()
        challenge = _make_challenge(recent_date)
        inject_daily_schedule(daily_db, [challenge])

        deleted = prune_daily_window(daily_db, rolling_window_days=90)
        assert deleted == 0

    def test_prune_never_removes_today(self, daily_db: Path) -> None:
        today = date.today().isoformat()
        challenge = _make_challenge(today)
        inject_daily_schedule(daily_db, [challenge])

        deleted = prune_daily_window(daily_db, rolling_window_days=0)
        # Even with 0-day window, today is never pruned (C6 constraint)
        assert deleted == 0

    def test_prune_returns_zero_when_no_expired(self, daily_db: Path) -> None:
        deleted = prune_daily_window(daily_db, rolling_window_days=90)
        assert deleted == 0
