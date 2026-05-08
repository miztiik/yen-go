"""Unit tests for ``puzzle-info`` (Theme 10)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_puzzle_info
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogWriter


def _entry(puzzle_id: str, run_id: str = "run-X") -> PublishLogEntry:
    return PublishLogEntry(
        run_id=run_id, puzzle_id=puzzle_id, source_id="src",
        path=f"sgf/0001/{puzzle_id}.sgf", quality=3,
        trace_id="t" * 16, level="elementary",
        tags=("life-and-death", "corner"),
        collections=("col-a",),
    )


def _seed_daily_db(db_path: Path, puzzle_id: str, dates: list[str]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE daily_schedule (
                date TEXT PRIMARY KEY, version TEXT NOT NULL DEFAULT '3.0',
                generated_at TEXT NOT NULL DEFAULT '2026-01-01T00:00:00Z',
                technique_of_day TEXT DEFAULT '', attrs TEXT DEFAULT '{}'
            );
            CREATE TABLE daily_puzzles (
                date TEXT NOT NULL, content_hash TEXT NOT NULL,
                section TEXT NOT NULL, position INTEGER NOT NULL,
                PRIMARY KEY (date, content_hash, section)
            );
        """)
        for d in dates:
            conn.execute(
                "INSERT INTO daily_schedule (date, generated_at, technique_of_day) "
                "VALUES (?, '2026-01-01T00:00:00Z', 'tesuji')", (d,),
            )
            conn.execute(
                "INSERT INTO daily_puzzles (date, content_hash, section, position) "
                "VALUES (?, ?, 'standard', 1)", (d, puzzle_id),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    publog = tmp_path / "publog"
    publog.mkdir()
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr("backend.puzzle_manager.cli.get_output_dir", lambda: out)
    monkeypatch.setattr("backend.puzzle_manager.cli.get_publish_log_dir",
                        lambda: publog)
    monkeypatch.setattr("backend.puzzle_manager.cli.get_audit_log_path",
                        lambda: audit)
    return tmp_path


def _ns(pid: str) -> argparse.Namespace:
    return argparse.Namespace(puzzle_id=pid, json=True)


class TestPuzzleInfo:
    def test_not_found_returns_empty_payload(
        self, env: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = cmd_puzzle_info(_ns("ffffffffffffffff"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["found"] is False
        assert out["publish_entries"] == []
        assert out["sgf"] is None

    def test_yengo_prefix_is_stripped(
        self, env: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        cmd_puzzle_info(_ns("YENGO-AbCdEf0123456789"))
        out = json.loads(capsys.readouterr().out)
        assert out["puzzle_id"] == "abcdef0123456789"

    def test_full_join_publish_sgf_daily_audit(
        self, env: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        pid = "abc123def4567890"
        publog_dir = env / "publog"
        out_dir = env / "out"

        # Seed publish-log: one earlier entry + one current.
        writer = PublishLogWriter(log_dir=publog_dir)
        writer.write(_entry(pid, run_id="run-OLD"))
        writer.write(_entry(pid, run_id="run-NEW"))

        # Seed SGF on disk at the path the latest entry points to.
        sgf_dir = out_dir / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / f"{pid}.sgf").write_text(
            "(;FF[4]GM[1]SZ[19]GN[YENGO-abc123def4567890])",
            encoding="utf-8",
        )

        # Seed daily DB.
        _seed_daily_db(out_dir / "yengo-search.db", pid,
                       ["2026-05-01", "2026-05-08"])

        # Seed audit row.
        (env / "audit.jsonl").write_text(json.dumps({
            "ts": "2026-05-01T00:00:00Z", "op": "rollback",
            "puzzle_id": pid, "reason": "test",
        }) + "\n", encoding="utf-8")

        rc = cmd_puzzle_info(_ns(pid))
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["found"] is True
        assert payload["puzzle_id"] == pid
        assert payload["source_id"] == "src"
        assert payload["level"] == "elementary"
        assert "life-and-death" in payload["tags"]
        assert "col-a" in payload["collections"]
        assert payload["latest"]["run_id"] == "run-NEW"
        assert payload["first_publish"]["run_id"] == "run-OLD"
        assert len(payload["publish_entries"]) == 2
        assert payload["sgf"]["exists"] is True
        assert payload["sgf"]["preview"].startswith("(;FF[4]")
        assert {r["date"] for r in payload["daily_appearances"]} == {
            "2026-05-01", "2026-05-08"
        }
        assert len(payload["audit"]) == 1
        assert payload["audit"][0]["op"] == "rollback"
