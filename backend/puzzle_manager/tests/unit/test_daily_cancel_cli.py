"""Unit tests for ``daily-cancel`` (Theme 8c)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_daily_cancel


def _seed_db(db_path: Path, dates: list[tuple[str, int]]) -> None:
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
        for d, n in dates:
            conn.execute(
                "INSERT INTO daily_schedule (date, version, generated_at) "
                "VALUES (?, '3.0', '2026-05-01T00:00:00Z')", (d,),
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
    base = {"date": None, "from_date": None, "to_date": None,
            "dry_run": False, "force": True, "json": True}
    base.update(kw)
    return argparse.Namespace(**base)


class TestDailyCancel:
    def test_missing_args_returns_2(self, output_dir, capsys) -> None:
        rc = cmd_daily_cancel(_ns())
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is False

    def test_invalid_date_returns_2(self, output_dir, capsys) -> None:
        rc = cmd_daily_cancel(_ns(date="2026/05/01"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert "Invalid" in out["error"]

    def test_dry_run_lists_affected_no_writes(
        self, output_dir, capsys,
    ) -> None:
        db = output_dir / "yengo-search.db"
        _seed_db(db, [("2026-05-01", 3), ("2026-05-02", 2)])
        rc = cmd_daily_cancel(_ns(date="2026-05-01", dry_run=True))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["dry_run"] is True
        assert out["dates_affected"] == ["2026-05-01"]
        assert out["puzzle_rows_affected"] == 3
        # Verify nothing was deleted.
        conn = sqlite3.connect(str(db))
        try:
            n = conn.execute("SELECT COUNT(*) FROM daily_schedule").fetchone()[0]
            assert n == 2
        finally:
            conn.close()

    def test_apply_deletes_in_range(self, output_dir, capsys) -> None:
        db = output_dir / "yengo-search.db"
        _seed_db(db, [
            ("2026-05-01", 1), ("2026-05-02", 2), ("2026-05-03", 3),
        ])
        rc = cmd_daily_cancel(_ns(from_date="2026-05-02", to_date="2026-05-03"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["dates_affected"] == ["2026-05-02", "2026-05-03"]
        assert out["puzzle_rows_affected"] == 5
        assert out["schedule_rows_deleted"] == 2
        conn = sqlite3.connect(str(db))
        try:
            remaining = [r[0] for r in conn.execute(
                "SELECT date FROM daily_schedule ORDER BY date",
            )]
            assert remaining == ["2026-05-01"]
            puzzles = conn.execute(
                "SELECT COUNT(*) FROM daily_puzzles",
            ).fetchone()[0]
            assert puzzles == 1
        finally:
            conn.close()

    def test_db_missing_returns_ok_with_empty(
        self, output_dir, capsys,
    ) -> None:
        rc = cmd_daily_cancel(_ns(date="2026-05-08"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["db_exists"] is False
        assert out["dates_affected"] == []
