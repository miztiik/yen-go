"""Integration tests for daily challenge generation from yengo-search.db.

Validates that the daily generator can load puzzles from the SQLite
search database.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.core.db_builder import build_search_db
from backend.puzzle_manager.core.db_models import PuzzleEntry
from backend.puzzle_manager.daily.generator import DailyGenerator
from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.config import DailyConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_puzzle_entries(count: int = 30, level_id: int = 120) -> list[PuzzleEntry]:
    """Create test PuzzleEntry objects spread across levels."""
    levels = [110, 120, 130, 140, 150, 160]
    entries = []
    for i in range(count):
        lvl = levels[i % len(levels)] if level_id == 120 else level_id
        entries.append(
            PuzzleEntry(
                content_hash=f"hash{i:04d}abcdef01",
                batch="0001",
                level_id=lvl,
                quality=3,
                content_type=2,
                cx_depth=1,
                cx_refutations=1,
                cx_solution_len=5,
                cx_unique_resp=1,
                tag_ids=[10, 20] if i % 3 == 0 else [10],
                collection_ids=[],
            )
        )
    return entries


def _build_test_db(output_dir: Path, entries: list[PuzzleEntry] | None = None) -> Path:
    """Build a test yengo-search.db in the given directory."""
    if entries is None:
        entries = _make_puzzle_entries(40)
    db_path = output_dir / "yengo-search.db"
    version_info = build_search_db(
        entries=entries,
        collections=[],
        output_path=db_path,
    )
    # Write db-version.json alongside
    version_path = output_dir / "db-version.json"
    version_path.write_text(json.dumps(version_info.to_dict()), encoding="utf-8")
    return db_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDailyFromDb:
    """Tests that daily generator reads from yengo-search.db."""

    def test_load_pool_from_db(self, tmp_path: Path) -> None:
        """_load_puzzle_pool should return entries from the DB."""
        entries = _make_puzzle_entries(10)
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=1)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 10
        # Each entry should have compact-entry keys
        for p in pool:
            assert "p" in p
            assert "l" in p
            assert "t" in p
            assert "q" in p

    def test_pool_quality_filter(self, tmp_path: Path) -> None:
        """Pool should exclude puzzles below min_quality."""
        entries = [
            PuzzleEntry(
                content_hash="lowquality00000a",
                batch="0001",
                level_id=120,
                quality=1,
                tag_ids=[10],
            ),
            PuzzleEntry(
                content_hash="highquality0000b",
                batch="0001",
                level_id=120,
                quality=3,
                tag_ids=[10],
            ),
        ]
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=2)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 1
        assert pool[0]["q"] == 3

    def test_pool_content_type_filter(self, tmp_path: Path) -> None:
        """Pool should exclude training content type (3)."""
        entries = [
            PuzzleEntry(
                content_hash="training0000000a",
                batch="0001",
                level_id=120,
                quality=3,
                content_type=3,
                tag_ids=[10],
            ),
            PuzzleEntry(
                content_hash="standard0000000b",
                batch="0001",
                level_id=120,
                quality=3,
                content_type=2,
                tag_ids=[10],
            ),
        ]
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=1, excluded_content_types=[3])
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 1
        assert pool[0]["ct"] == 2

    def test_pool_compact_path_format(self, tmp_path: Path) -> None:
        """Pool entries should have batch/hash compact path."""
        entries = [
            PuzzleEntry(
                content_hash="abc123def4567890",
                batch="0002",
                level_id=130,
                quality=3,
                tag_ids=[],
            ),
        ]
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=1)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 1
        assert pool[0]["p"] == "0002/abc123def4567890"

    def test_pool_tag_ids_loaded(self, tmp_path: Path) -> None:
        """Pool entries should include resolved tag IDs."""
        entries = [
            PuzzleEntry(
                content_hash="tagtest000000001",
                batch="0001",
                level_id=120,
                quality=3,
                tag_ids=[5, 10, 20],
            ),
        ]
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=1)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 1
        assert pool[0]["t"] == [5, 10, 20]

    def test_generate_daily_from_db(self, tmp_path: Path) -> None:
        """Full daily generation should work with DB as puzzle source."""
        entries = _make_puzzle_entries(60)
        _build_test_db(tmp_path, entries)

        config = DailyConfig(
            min_quality=1,
            standard_puzzle_count=5,
            timed_set_count=1,
            timed_puzzles_per_set=5,
            tag_puzzle_count=5,
        )
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)

        date = datetime(2026, 3, 15)
        result = gen.generate(start_date=date)

        assert len(result.challenges) == 1
        challenge = result.challenges[0]
        assert challenge.date == "2026-03-15"

        # Persist to DB (generator no longer writes on its own)
        from backend.puzzle_manager.daily.db_writer import inject_daily_schedule
        inject_daily_schedule(tmp_path / "yengo-search.db", result.challenges)

        # Verify daily was injected into DB
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "yengo-search.db"))
        row = conn.execute("SELECT * FROM daily_schedule WHERE date = '2026-03-15'").fetchone()
        conn.close()
        assert row is not None

    def test_empty_db_returns_no_pool(self, tmp_path: Path) -> None:
        """Empty DB should return empty pool."""
        _build_test_db(tmp_path, entries=[])

        config = DailyConfig(min_quality=1)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert pool == []

    def test_no_db_raises_on_missing(self, tmp_path: Path) -> None:
        """Missing DB should raise DailyGenerationError."""
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db")
        with pytest.raises(DailyGenerationError):
            gen._load_puzzle_pool()

    def test_db_loads_successfully(self, tmp_path: Path) -> None:
        """DB should load puzzles when present."""
        # Create DB with known entries
        entries = _make_puzzle_entries(5, level_id=130)
        _build_test_db(tmp_path, entries)

        config = DailyConfig(min_quality=1)
        gen = DailyGenerator(db_path=tmp_path / "yengo-search.db", config=config)
        pool = gen._load_puzzle_pool()

        assert len(pool) == 5
