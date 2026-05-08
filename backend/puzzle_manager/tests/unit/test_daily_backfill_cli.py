"""Unit tests for ``daily-backfill`` (Theme 8d)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.puzzle_manager.cli import cmd_daily_backfill


def _seed_db(db_path: Path, dates: list[str]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE daily_schedule (
                date TEXT PRIMARY KEY, version TEXT NOT NULL DEFAULT '3.0',
                generated_at TEXT NOT NULL,
                technique_of_day TEXT DEFAULT '',
                attrs TEXT DEFAULT '{}'
            );
            CREATE TABLE daily_puzzles (
                date TEXT NOT NULL, content_hash TEXT NOT NULL,
                section TEXT NOT NULL, position INTEGER NOT NULL,
                PRIMARY KEY (date, content_hash, section)
            );
        """)
        for d in dates:
            conn.execute(
                "INSERT INTO daily_schedule (date, version, generated_at) "
                "VALUES (?, '3.0', '2026-05-01T00:00:00Z')", (d,),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr("backend.puzzle_manager.cli.get_output_dir",
                        lambda: out)
    return out


def _ns(**kw) -> argparse.Namespace:
    base = {"window_days": 7, "dry_run": True, "force": True, "json": True}
    base.update(kw)
    return argparse.Namespace(**base)


class TestDailyBackfill:
    def test_db_missing_emits_full_window_as_missing(
        self, output_dir, capsys,
    ) -> None:
        rc = cmd_daily_backfill(_ns())
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["db_exists"] is False
        assert len(out["missing_dates"]) == 7

    def test_dry_run_lists_only_gaps(self, output_dir, capsys) -> None:
        db = output_dir / "yengo-search.db"
        today = date.today()
        # Seed only the last 3 days; expect 4 missing in a 7-day window.
        seeded = [(today - timedelta(days=i)).isoformat() for i in (0, 1, 2)]
        _seed_db(db, seeded)
        rc = cmd_daily_backfill(_ns())
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert len(out["missing_dates"]) == 4
        assert out["generated_count"] == 0  # dry-run
        # Verify nothing was added.
        conn = sqlite3.connect(str(db))
        try:
            n = conn.execute("SELECT COUNT(*) FROM daily_schedule").fetchone()[0]
            assert n == 3
        finally:
            conn.close()

    def test_apply_generates_for_each_missing_date(
        self, output_dir, capsys,
    ) -> None:
        db = output_dir / "yengo-search.db"
        today = date.today()
        _seed_db(db, [(today - timedelta(days=i)).isoformat() for i in (0,)])

        challenge = MagicMock()
        result_obj = MagicMock(challenges=[challenge], failures=[])

        with patch("backend.puzzle_manager.cli.DailyGenerator") as gen_cls, \
             patch(
                 "backend.puzzle_manager.daily.db_writer.inject_daily_schedule"
             ) as inject:
            gen_cls.return_value.generate.return_value = result_obj
            rc = cmd_daily_backfill(_ns(dry_run=False))

        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        # 7-day window minus 1 seeded = 6 missing → 6 generate calls.
        assert out["generated_count"] == 6
        assert inject.call_count == 6
