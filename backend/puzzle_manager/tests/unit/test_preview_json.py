"""Theme 1a+1b+1c: pin --json schema for rollback, vacuum-db, and clean.

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

from backend.puzzle_manager.cli import cmd_clean, cmd_rollback, cmd_vacuum_db
from backend.puzzle_manager.models.previews import (
    CleanPreview,
    RollbackPreview,
    VacuumDbPreview,
)
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


@pytest.fixture
def clean_runtime(tmp_path: Path, monkeypatch):
    """Stand up a fake .pm-runtime/ + output_dir on tmp_path.

    Patches all six paths.* getters that cleanup.preview_clean depends on
    so the scan stays inside tmp_path and never touches the real
    workspace runtime.
    """
    runtime = tmp_path / ".pm-runtime"
    logs_dir = runtime / "logs"
    state_dir = runtime / "state"
    staging_dir = runtime / "staging"
    raw_dir = runtime / "raw"
    output_dir = tmp_path / "out"
    publish_log_dir = output_dir / ".puzzle-inventory-state" / "publish-log"
    for d in (logs_dir, state_dir / "runs", state_dir / "failures",
              staging_dir / "failed", raw_dir, publish_log_dir):
        d.mkdir(parents=True)

    # cleanup.py imports get_logs_dir et al. at module load — patch the
    # module's bound names rather than paths.* sources.
    monkeypatch.setattr(
        "backend.puzzle_manager.pipeline.cleanup.get_logs_dir",
        lambda: logs_dir,
    )
    monkeypatch.setattr(
        "backend.puzzle_manager.pipeline.cleanup.get_pm_state_dir",
        lambda: state_dir,
    )
    monkeypatch.setattr(
        "backend.puzzle_manager.pipeline.cleanup.get_pm_staging_dir",
        lambda: staging_dir,
    )
    monkeypatch.setattr(
        "backend.puzzle_manager.pipeline.cleanup.get_pm_raw_dir",
        lambda: raw_dir,
    )
    monkeypatch.setattr(
        "backend.puzzle_manager.pipeline.cleanup.get_output_dir",
        lambda: output_dir,
    )
    # rel_path uses get_project_root from paths module — re-anchor to tmp_path
    # so emitted paths are relative POSIX strings rooted in the fixture.
    monkeypatch.setattr(
        "backend.puzzle_manager.paths.get_project_root", lambda: tmp_path
    )
    return {
        "tmp_path": tmp_path,
        "runtime": runtime,
        "logs_dir": logs_dir,
        "state_dir": state_dir,
        "staging_dir": staging_dir,
        "raw_dir": raw_dir,
        "output_dir": output_dir,
        "publish_log_dir": publish_log_dir,
    }


def _age_file(path: Path, days: int) -> None:
    """Backdate ``path``'s mtime by ``days`` so retention scans pick it up."""
    import os
    import time

    past = time.time() - days * 86400
    os.utime(path, (past, past))


class TestCleanJsonDryRun:
    def test_dry_run_default_target_emits_clean_preview_shape(
        self, clean_runtime
    ):
        """No --target → retention-based scan returns matching files."""
        old_log = clean_runtime["logs_dir"] / "old.log"
        old_log.write_text("ancient", encoding="utf-8")
        _age_file(old_log, days=60)
        # A young file must be excluded from a 45-day cutoff.
        (clean_runtime["logs_dir"] / "fresh.log").write_text(
            "today", encoding="utf-8"
        )

        ns = argparse.Namespace(
            target=None, retention_days=45, dry_run="true", json=True
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_clean(ns)

        assert rc == 0
        preview = CleanPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.target is None
        assert preview.retention_days == 45
        assert preview.total_files == 1
        assert preview.total_bytes == len("ancient")
        # Path must be relative POSIX (no backslashes, no drive letter).
        only = preview.would_delete[0]
        assert "\\" not in only.path
        assert only.path.endswith("old.log")
        assert only.bytes == len("ancient")

    def test_dry_run_logs_target_lists_every_file(self, clean_runtime):
        """--target logs → every file under logs/ regardless of mtime."""
        for name in ("a.log", "b.log", "c.txt"):
            (clean_runtime["logs_dir"] / name).write_text(
                "x" * 7, encoding="utf-8"
            )

        ns = argparse.Namespace(
            target="logs", retention_days=45, dry_run="true", json=True
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_clean(ns)
        assert rc == 0

        preview = CleanPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.target == "logs"
        assert preview.total_files == 3
        assert preview.total_bytes == 21
        assert {Path(item.path).name for item in preview.would_delete} == {
            "a.log", "b.log", "c.txt"
        }

    def test_dry_run_unknown_target_records_error(self, clean_runtime):
        """Defensive path: invalid target surfaces in `errors`."""
        ns = argparse.Namespace(
            target="not-a-real-target",
            retention_days=45,
            dry_run="true",
            json=True,
        )
        buf = io.StringIO()
        # argparse normally rejects bad choices, but cmd_clean is invoked
        # directly here so we exercise preview_clean's defensive branch.
        with redirect_stdout(buf):
            rc = cmd_clean(ns)
        assert rc == 0
        preview = CleanPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.total_files == 0
        assert preview.errors and "not-a-real-target" in preview.errors[0]

    def test_dry_run_publish_logs_target_uses_date_filename_filter(
        self, clean_runtime
    ):
        """publish-logs target only collects date-formatted .jsonl files
        older than retention; audit logs always preserved."""
        from datetime import UTC, datetime, timedelta

        log_dir = clean_runtime["publish_log_dir"]
        old_date = (
            datetime.now(UTC) - timedelta(days=200)
        ).strftime("%Y-%m-%d")
        (log_dir / f"{old_date}.jsonl").write_text("{}", encoding="utf-8")
        # Audit logs are protected — must NOT appear in the preview.
        (log_dir / "audit.jsonl").write_text("{}", encoding="utf-8")
        (log_dir / "rollback-audit.jsonl").write_text("{}", encoding="utf-8")
        # A fresh date-stamped log must NOT appear (within retention).
        new_date = datetime.now(UTC).strftime("%Y-%m-%d")
        (log_dir / f"{new_date}.jsonl").write_text("{}", encoding="utf-8")

        # publish-logs uses publish-log dir resolution from paths module —
        # patch that too so the scan stays in tmp_path.
        with patch(
            "backend.puzzle_manager.paths.get_publish_log_dir",
            return_value=log_dir,
        ):
            ns = argparse.Namespace(
                target="publish-logs",
                retention_days=90,
                dry_run="true",
                json=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cmd_clean(ns)

        assert rc == 0
        preview = CleanPreview.model_validate(json.loads(buf.getvalue()))
        assert preview.target == "publish-logs"
        assert preview.total_files == 1
        names = {Path(item.path).name for item in preview.would_delete}
        assert names == {f"{old_date}.jsonl"}
