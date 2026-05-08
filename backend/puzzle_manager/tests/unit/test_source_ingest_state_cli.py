"""Unit tests for ``cmd_source_ingest_state`` (Theme 6b)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import (
    _read_ingest_counts,
    cmd_source_ingest_state,
    create_parser,
)
from backend.puzzle_manager.core.source_ingest_db import (
    DB_FILENAME,
    FileStatus,
    SourceIngestDB,
)


def _seed_db(source_root: Path, *, source_id: str, run_id: str = "r1") -> Path:
    """Create a tiny ingest DB with one ingested + one failed row."""
    source_root.mkdir(parents=True, exist_ok=True)
    with SourceIngestDB.open(source_root, source_id=source_id, run_id=run_id) as db:
        db.upsert(
            rel_path="good.sgf",
            content_hash="aaaa",
            size_bytes=10,
            mtime_ns=1,
            status=FileStatus.INGESTED,
        )
        db.upsert(
            rel_path="bad.sgf",
            content_hash="bbbb",
            size_bytes=10,
            mtime_ns=2,
            status=FileStatus.FAILED,
            skip_reason="parse error",
        )
        db.commit()
    return source_root / DB_FILENAME


def _write_sources_json(tmp_path: Path, *, source_id: str, source_path: Path) -> Path:
    """Minimal sources.json with one local adapter pointing at ``source_path``.

    Returns the config *directory* (ConfigLoader takes the dir, not the file).
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(exist_ok=True)
    cfg = {
        "active_adapter": source_id,
        "sources": [
            {
                "id": source_id,
                "name": source_id,
                "adapter": "local",
                "config": {"path": str(source_path), "recursive": False},
            }
        ],
    }
    (cfg_dir / "sources.json").write_text(json.dumps(cfg), encoding="utf-8")
    return cfg_dir


@pytest.fixture
def project_root_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin both YENGO_PROJECT_ROOT and YENGO_RUNTIME_DIR to a tmp tree."""
    monkeypatch.setenv("YENGO_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
    return tmp_path


class TestArgparse:
    def test_parses_required_source_id(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["source-ingest-state", "src1", "--json"])
        assert args.command == "source-ingest-state"
        assert args.source_id == "src1"
        assert args.json is True
        assert args.reset is False
        assert args.dry_run is False


class TestInspect:
    def test_unknown_source_returns_2(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cfg = _write_sources_json(
            project_root_env,
            source_id="src1",
            source_path=project_root_env / "data" / "src1",
        )
        ns = argparse.Namespace(
            source_id="missing",
            reset=False,
            dry_run=False,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert "unknown source" in out["error"]

    def test_missing_db_returns_status_missing(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_path = project_root_env / "data" / "src1"
        source_path.mkdir(parents=True)
        cfg = _write_sources_json(
            project_root_env, source_id="src1", source_path=source_path
        )
        ns = argparse.Namespace(
            source_id="src1",
            reset=False,
            dry_run=False,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["source_id"] == "src1"
        assert out["db_exists"] is False
        assert out["status"] == "missing"
        assert out["rows"] == 0
        assert out["failed_rows"] == []

    def test_seeded_db_reports_counts_and_failed_rows(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_path = project_root_env / "data" / "src1"
        _seed_db(source_path, source_id="src1")
        cfg = _write_sources_json(
            project_root_env, source_id="src1", source_path=source_path
        )
        ns = argparse.Namespace(
            source_id="src1",
            reset=False,
            dry_run=False,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["db_exists"] is True
        assert out["status"] == "healthy"
        assert out["rows"] == 2
        assert out["ingested"] == 1
        assert out["failed"] == 1
        assert len(out["failed_rows"]) == 1
        assert out["failed_rows"][0]["rel_path"] == "bad.sgf"
        assert out["failed_rows"][0]["skip_reason"] == "parse error"


class TestResetDryRun:
    def test_dry_run_does_not_delete_and_reports_counts(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_path = project_root_env / "data" / "src1"
        db_file = _seed_db(source_path, source_id="src1")
        assert db_file.exists()
        cfg = _write_sources_json(
            project_root_env, source_id="src1", source_path=source_path
        )
        ns = argparse.Namespace(
            source_id="src1",
            reset=True,
            dry_run=True,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 0
        assert db_file.exists(), "dry-run must NOT delete the DB"
        out = json.loads(capsys.readouterr().out)
        assert out["source_id"] == "src1"
        assert out["db_exists"] is True
        assert out["row_count_lost"] == 2
        assert out["failed_rows_lost"] == 1
        assert out["requires_full_reingest"] is True
        assert out["would_delete_path"]


class TestResetApply:
    def test_apply_removes_db_atomically(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_path = project_root_env / "data" / "src1"
        db_file = _seed_db(source_path, source_id="src1")
        cfg = _write_sources_json(
            project_root_env, source_id="src1", source_path=source_path
        )
        ns = argparse.Namespace(
            source_id="src1",
            reset=True,
            dry_run=False,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 0
        assert not db_file.exists(), "reset must remove the DB file"
        out = json.loads(capsys.readouterr().out)
        assert out["removed"] is True
        assert out["rows_lost"] == 2
        assert out["deleted_path"]

    def test_apply_no_op_when_db_missing(
        self, project_root_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_path = project_root_env / "data" / "src1"
        source_path.mkdir(parents=True)
        cfg = _write_sources_json(
            project_root_env, source_id="src1", source_path=source_path
        )
        ns = argparse.Namespace(
            source_id="src1",
            reset=True,
            dry_run=False,
            json=True,
            max_failed_rows=20,
            config=str(cfg),
        )
        rc = cmd_source_ingest_state(ns)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["removed"] is False
        assert out["rows_lost"] == 0


class TestReadIngestCounts:
    def test_counts_match_seeded_rows(self, tmp_path: Path) -> None:
        source_path = tmp_path / "src"
        db_file = _seed_db(source_path, source_id="src1")
        ing, skp, fld, total = _read_ingest_counts(db_file)
        assert ing == 1
        assert skp == 0
        assert fld == 1
        assert total == 2

    def test_missing_file_returns_zeros(self, tmp_path: Path) -> None:
        ing, skp, fld, total = _read_ingest_counts(tmp_path / "no.sqlite")
        assert (ing, skp, fld, total) == (0, 0, 0, 0)
