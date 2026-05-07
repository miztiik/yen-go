"""Unit tests for ``runtime-info`` (Theme 3a).

Two layers:
1. Pure aggregation tests on ``compute_runtime_info()`` — directory walks,
   ingest-DB sidecar handling, missing-dir tolerance, by_source mapping.
2. CLI handler test that drives ``cmd_runtime_info`` against a tmp
   ``YENGO_RUNTIME_DIR`` populated with real files. The marshalling/dumping
   logic is the contract the dashboard depends on.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.models.runtime_info import (
    RuntimeInfo,
    compute_runtime_info,
)


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


class TestComputeRuntimeInfo:
    def test_missing_runtime_dir_returns_zeros(self, tmp_path: Path) -> None:
        info = compute_runtime_info(
            runtime_dir=tmp_path / "absent",
            sources=[],
            publish_log_dir=tmp_path / "absent" / "publish-log",
        )
        assert info.logs_bytes == 0
        assert info.state_bytes == 0
        assert info.staging_bytes == 0
        assert info.raw_bytes == 0
        assert info.ingest_dbs_bytes == 0
        assert info.publish_logs_bytes == 0
        assert info.by_source == {}
        assert info.captured_at  # ISO-8601 string

    def test_walks_subdirs_and_sums_sizes(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        _write(runtime / "logs" / "a.log", 100)
        _write(runtime / "logs" / "sub" / "b.log", 200)
        _write(runtime / "state" / "current_run.json", 50)
        _write(runtime / "staging" / "ingest" / "p1.sgf", 300)
        _write(runtime / "raw" / "src" / "x.json", 25)
        _write(tmp_path / "pub" / "2026-01.jsonl", 400)

        info = compute_runtime_info(
            runtime_dir=runtime,
            sources=[],
            publish_log_dir=tmp_path / "pub",
        )
        assert info.logs_bytes == 300
        assert info.state_bytes == 50
        assert info.staging_bytes == 300
        assert info.raw_bytes == 25
        assert info.publish_logs_bytes == 400

    def test_ingest_dbs_keyed_by_source_id_with_sidecars(self, tmp_path: Path) -> None:
        src_a = tmp_path / "data" / "alpha"
        src_b = tmp_path / "data" / "beta"
        _write(src_a / ".yengo-ingest.sqlite", 1000)
        _write(src_a / ".yengo-ingest.sqlite-wal", 200)
        _write(src_a / ".yengo-ingest.sqlite-shm", 50)
        _write(src_b / ".yengo-ingest.sqlite", 500)

        info = compute_runtime_info(
            runtime_dir=tmp_path / "absent",
            sources=[("alpha", src_a), ("beta", src_b), ("http-only", None)],
            publish_log_dir=tmp_path / "absent",
        )
        assert info.by_source == {"alpha": 1250, "beta": 500}
        assert info.ingest_dbs_bytes == 1750

    def test_sources_with_zero_byte_db_omitted(self, tmp_path: Path) -> None:
        # A source whose DB doesn't exist (or is empty) should not appear
        # in by_source — the dashboard treats absent keys as "no data".
        src = tmp_path / "data" / "gone"
        src.mkdir(parents=True)
        info = compute_runtime_info(
            runtime_dir=tmp_path / "absent",
            sources=[("gone", src)],
            publish_log_dir=tmp_path / "absent",
        )
        assert info.by_source == {}
        assert info.ingest_dbs_bytes == 0


class TestRuntimeInfoModel:
    def test_negative_byte_counts_rejected(self) -> None:
        with pytest.raises(Exception):
            RuntimeInfo(
                logs_bytes=-1, state_bytes=0, staging_bytes=0, raw_bytes=0,
                ingest_dbs_bytes=0, publish_logs_bytes=0,
                captured_at="2026-05-07T00:00:00+00:00",
            )


class TestRuntimeInfoCli:
    @pytest.fixture
    def env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        runtime = tmp_path / ".pm-runtime"
        _write(runtime / "logs" / "x.log", 123)
        _write(runtime / "state" / "current_run.json", 45)
        yield runtime
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

    def _args(self, **overrides: object) -> Namespace:
        base = {"config": None, "json": True, "command": "runtime-info", "verbose": 0}
        base.update(overrides)
        return Namespace(**base)

    def test_emits_runtime_info_json(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_runtime_info
        rc = cmd_runtime_info(self._args())
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["logs_bytes"] == 123
        assert payload["state_bytes"] == 45
        assert payload["staging_bytes"] == 0
        assert payload["captured_at"]
        assert payload["by_source"] == {}

    def test_human_output_includes_header(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_runtime_info
        rc = cmd_runtime_info(self._args(json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "Runtime footprint" in out
        assert "logs" in out
        assert "publish-logs" in out
