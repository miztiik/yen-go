"""Theme 1a+1b: pin --json schema for rollback + vacuum-db dry-run.

The dashboard's preview endpoints depend on stable, machine-readable JSON
from these CLI subcommands. These tests pin the contract so a future
refactor of the human-readable output cannot silently break the dashboard
preview modal.
"""

from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.puzzle_manager.cli import cmd_rollback, cmd_vacuum_db
from backend.puzzle_manager.models.previews import RollbackPreview, VacuumDbPreview
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogWriter


def _make_entry(run_id: str, idx: int) -> PublishLogEntry:
    return PublishLogEntry(
        run_id=run_id,
        puzzle_id=f"hash{idx:012x}",
        source_id="test-source",
        path=f"sgf/0001/hash{idx:012x}.sgf",
        quality=2,
        trace_id=f"{idx:016x}",
        level="beginner",
        tags=("life-and-death",),
        collections=(),
    )


@pytest.fixture
def rollback_fixture(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    sgf_dir = output_dir / "sgf" / "0001"
    sgf_dir.mkdir(parents=True)

    log_dir = tmp_path / "publish-log"
    log_dir.mkdir()
    entries = [_make_entry("20260507-aa11bb22", i) for i in range(3)]
    PublishLogWriter(log_dir=log_dir).write_batch(entries)

    for entry in entries:
        (output_dir / entry.path).write_text(
            "(;FF[4]GM[1]SZ[19])", encoding="utf-8"
        )

    monkeypatch.setattr(
        "backend.puzzle_manager.cli.get_output_dir", lambda: output_dir
    )
    monkeypatch.setattr(
        "backend.puzzle_manager.cli.get_publish_log_dir", lambda: log_dir
    )
    return output_dir, entries


class TestRollbackJsonDryRun:
    def test_dry_run_emits_rollback_preview_shape(self, rollback_fixture):
        _, entries = rollback_fixture
        ns = argparse.Namespace(
            run_id="20260507-aa11bb22",
            dry_run=True,
            yes=False,
            reason="schema test",
            verify=False,
            json=True,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_rollback(ns)

        assert rc == 0
        # Stdout must be parseable JSON only (no chatter).
        payload = json.loads(buf.getvalue().strip())
        # Pydantic schema validation pins the contract.
        preview = RollbackPreview.model_validate(payload)
        assert preview.puzzles_affected == 3
        assert preview.affected_puzzles == [e.puzzle_id for e in entries]
        assert preview.affected_runs == ["20260507-aa11bb22"]
        assert preview.reversible is False
        assert preview.errors == []

    def test_dry_run_with_unknown_run_id_returns_zero_count(
        self, rollback_fixture
    ):
        ns = argparse.Namespace(
            run_id="20990101-deadbeef",
            dry_run=True,
            yes=False,
            reason="ghost",
            verify=False,
            json=True,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_rollback(ns)
        assert rc == 0
        preview = RollbackPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.puzzles_affected == 0
        assert preview.affected_puzzles == []
        # affected_runs falls back to the requested run_id so the operator
        # can still see what they asked for.
        assert preview.affected_runs == ["20990101-deadbeef"]
        # The 'no entries found' note surfaces as an informational error.
        assert preview.errors and "20990101-deadbeef" in preview.errors[0]


@pytest.fixture
def vacuum_fixture(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    sgf_dir = output_dir / "sgf" / "0001"
    sgf_dir.mkdir(parents=True)

    # Two SGFs on disk; one orphan in content DB.
    on_disk_hashes = ["hash000000000001", "hash000000000002"]
    for h in on_disk_hashes:
        (sgf_dir / f"{h}.sgf").write_text("(;FF[4])", encoding="utf-8")

    import sqlite3

    content_db = output_dir / "yengo-content.db"
    conn = sqlite3.connect(content_db)
    conn.execute("CREATE TABLE sgf_files (content_hash TEXT PRIMARY KEY)")
    conn.executemany(
        "INSERT INTO sgf_files (content_hash) VALUES (?)",
        [(h,) for h in on_disk_hashes + ["hash00000000orph"]],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "backend.puzzle_manager.cli.get_output_dir", lambda: output_dir
    )
    return output_dir


class TestVacuumDbJsonDryRun:
    def test_dry_run_emits_vacuum_db_preview_shape(self, vacuum_fixture):
        ns = argparse.Namespace(rebuild=False, dry_run=True, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_vacuum_db(ns)

        assert rc == 0
        payload = json.loads(buf.getvalue().strip())
        preview = VacuumDbPreview.model_validate(payload)
        assert preview.has_content_db is True
        assert preview.on_disk_files == 2
        assert preview.orphan_rows == 1
        assert preview.rebuild is False
        # Estimate is row_count * 4096 (per the comment in cmd_vacuum_db).
        assert preview.freed_bytes_estimate == 4096

    def test_dry_run_with_rebuild_flag_passthrough(self, vacuum_fixture):
        ns = argparse.Namespace(rebuild=True, dry_run=True, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_vacuum_db(ns)
        preview = VacuumDbPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.rebuild is True

    def test_dry_run_no_content_db_emits_zero_shape(
        self, tmp_path: Path, monkeypatch
    ):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setattr(
            "backend.puzzle_manager.cli.get_output_dir", lambda: empty_dir
        )
        ns = argparse.Namespace(rebuild=False, dry_run=True, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_vacuum_db(ns)
        assert rc == 0
        preview = VacuumDbPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.has_content_db is False
        assert preview.orphan_rows == 0
        assert preview.on_disk_files == 0
