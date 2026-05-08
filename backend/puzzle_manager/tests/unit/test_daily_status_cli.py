"""Unit tests for ``daily-list`` / ``daily-status`` (Theme 8a)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.puzzle_manager.cli import cmd_daily_list, cmd_daily_status


def _seed_db(db_path: Path, dates: list[tuple[str, str, int]]) -> None:
    """Create yengo-search.db with daily_schedule + daily_puzzles rows.

    dates: list of (date_str, generated_at_iso, puzzle_count).
    """
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
        for d, gen_at, n in dates:
            conn.execute(
                "INSERT INTO daily_schedule (date, version, generated_at, "
                "technique_of_day, attrs) VALUES (?, '3.0', ?, ?, '{}')",
                (d, gen_at, f"tech-{d}"),
            )
            for i in range(n):
                conn.execute(
                    "INSERT INTO daily_puzzles VALUES (?, ?, ?, ?)",
                    (d, f"hash{d}{i}", "standard", i),
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
    base = {"json": True, "from_date": None, "to_date": None,
            "window_days": 30, "stale_days": 14}
    base.update(kw)
    return argparse.Namespace(**base)


class TestDailyList:
    def test_empty_when_db_missing(
        self, output_dir: Path, capsys,
    ) -> None:
        rc = cmd_daily_list(_ns())
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["db_exists"] is False
        assert out["rows"] == []

    def test_lists_seeded_rows(self, output_dir: Path, capsys) -> None:
        _seed_db(output_dir / "yengo-search.db", [
            ("2026-05-01", "2026-05-01T08:00:00+00:00", 30),
            ("2026-05-02", "2026-05-02T08:00:00+00:00", 30),
        ])
        rc = cmd_daily_list(_ns())
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert len(out["rows"]) == 2
        assert out["rows"][0]["date"] == "2026-05-01"
        assert out["rows"][0]["puzzle_count"] == 30
        assert out["rows"][0]["technique"] == "tech-2026-05-01"

    def test_date_range_filter(self, output_dir: Path, capsys) -> None:
        _seed_db(output_dir / "yengo-search.db", [
            ("2026-04-30", "2026-04-30T08:00:00+00:00", 1),
            ("2026-05-01", "2026-05-01T08:00:00+00:00", 1),
            ("2026-05-05", "2026-05-05T08:00:00+00:00", 1),
        ])
        rc = cmd_daily_list(_ns(from_date="2026-05-01", to_date="2026-05-04"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        ds = [r["date"] for r in out["rows"]]
        assert ds == ["2026-05-01"]


class TestDailyStatus:
    def _today(self) -> date:
        return date.today()

    def test_db_missing_reports_all_missing(
        self, output_dir: Path, capsys,
    ) -> None:
        rc = cmd_daily_status(_ns(window_days=5))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["db_exists"] is False
        assert out["expected_dates"] == 5
        assert out["generated_dates"] == 0
        assert len(out["missing_dates"]) == 5

    def test_finds_gaps_in_window(self, output_dir: Path, capsys) -> None:
        today = self._today()
        # seed 3 of last 5 days
        rows = []
        for i, n in [(0, 1), (2, 1), (4, 1)]:
            d = (today - timedelta(days=i)).isoformat()
            rows.append((d, d + "T08:00:00+00:00", 1))
        _seed_db(output_dir / "yengo-search.db", rows)
        rc = cmd_daily_status(_ns(window_days=5))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["generated_dates"] == 3
        assert len(out["missing_dates"]) == 2

    def test_marks_stale(self, output_dir: Path, capsys) -> None:
        today = self._today()
        d = today.isoformat()
        old_gen = (today - timedelta(days=30)).isoformat() + "T08:00:00+00:00"
        _seed_db(output_dir / "yengo-search.db",
                 [(d, old_gen, 1)])
        rc = cmd_daily_status(_ns(window_days=1, stale_days=14))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert len(out["stale_dates"]) == 1
        assert out["stale_dates"][0]["age_days"] >= 14
