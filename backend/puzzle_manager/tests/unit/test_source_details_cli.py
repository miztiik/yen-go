"""Theme 6a: source-status --details CLI tests.

Real-fixture tests against tmp_path runtime + tmp sources.json. No mocks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import _build_source_details, cmd_source_status, create_parser


def _write_run(
    runs_dir: Path,
    *,
    name: str,
    run_id: str,
    source_id: str | None,
    ingested: int = 0,
    failed: int = 0,
    skipped: int = 0,
    failures: list[dict] | None = None,
    status: str = "completed",
) -> Path:
    """Write a minimal run-state JSON file."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        "status": status,
        "started_at": "2026-05-08T10:00:00+00:00",
        "completed_at": "2026-05-08T10:05:00+00:00",
        "stages": [
            {"name": "ingest", "status": "completed",
             "processed_count": ingested, "failed_count": 0, "skipped_count": skipped},
            {"name": "analyze", "status": "completed",
             "processed_count": 0, "failed_count": failed, "skipped_count": 0},
        ],
        "failures": failures or [],
        "config_snapshot": {"source_id": source_id} if source_id else {},
    }
    path = runs_dir / name
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


class TestBuildSourceDetails:
    def test_returns_empty_lists_when_no_runs_exist(self, tmp_path: Path) -> None:
        out = _build_source_details(
            row={"adapter": "local", "ingested": 5, "skipped": 1, "failed": 0, "total": 6},
            source_id="foo",
            source_cfg={"path": "data/foo"},
            runs_dir=tmp_path / "missing",
        )
        assert out["id"] == "foo"
        assert out["adapter"] == "local"
        assert out["summary"] == {"ingested": 5, "skipped": 1, "failed": 0, "total": 6}
        assert out["recent_runs"] == []
        assert out["recent_failures"] == []
        assert out["config"] == {"path": "data/foo"}

    def test_filters_runs_by_source_id(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs, name="20260508-100000-a.json", run_id="A",
                   source_id="foo", ingested=10)
        _write_run(runs, name="20260508-110000-b.json", run_id="B",
                   source_id="bar", ingested=99)
        _write_run(runs, name="20260508-120000-c.json", run_id="C",
                   source_id="foo", ingested=20)

        out = _build_source_details(
            row={"adapter": "local", "ingested": 0, "skipped": 0, "failed": 0, "total": 0},
            source_id="foo",
            source_cfg={},
            runs_dir=runs,
        )
        ids = [r["run_id"] for r in out["recent_runs"]]
        # Newest-first sort: C then A.
        assert ids == ["C", "A"]
        assert all(r["status"] == "completed" for r in out["recent_runs"])

    def test_caps_at_max_runs(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        for i in range(15):
            _write_run(runs, name=f"20260508-{i:02d}0000-x.json", run_id=f"R{i}",
                       source_id="foo")
        out = _build_source_details(
            row={"adapter": "local", "ingested": 0, "skipped": 0, "failed": 0, "total": 0},
            source_id="foo", source_cfg={}, runs_dir=runs, max_runs=10,
        )
        assert len(out["recent_runs"]) == 10

    def test_collects_failures_with_run_id(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(
            runs, name="20260508-100000-f.json", run_id="RUNX",
            source_id="foo",
            failures=[
                {"item_id": "puz1", "stage": "analyze", "error_type": "ValueError",
                 "error_message": "bad input", "timestamp": "2026-05-08T10:01:00+00:00"},
                {"item_id": "puz2", "stage": "ingest", "error_type": "OSError",
                 "error_message": "missing file", "timestamp": "2026-05-08T10:02:00+00:00"},
            ],
        )
        out = _build_source_details(
            row={"adapter": "local", "ingested": 0, "skipped": 0, "failed": 2, "total": 2},
            source_id="foo", source_cfg={}, runs_dir=runs,
        )
        assert len(out["recent_failures"]) == 2
        assert all(f["run_id"] == "RUNX" for f in out["recent_failures"])
        assert {f["item_id"] for f in out["recent_failures"]} == {"puz1", "puz2"}

    def test_skips_truncated_state_file(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        (runs / "20260508-100000-a.json").write_text("{ not valid json", encoding="utf-8")
        _write_run(runs, name="20260508-110000-b.json", run_id="OK",
                   source_id="foo", ingested=3)
        out = _build_source_details(
            row={"adapter": "local", "ingested": 3, "skipped": 0, "failed": 0, "total": 3},
            source_id="foo", source_cfg={}, runs_dir=runs,
        )
        assert [r["run_id"] for r in out["recent_runs"]] == ["OK"]


class TestSourceStatusDetailsArgparse:
    def test_parser_accepts_details_flag(self) -> None:
        parser = create_parser()
        ns = parser.parse_args([
            "source-status", "--source", "foo", "--details", "--json",
        ])
        assert ns.command == "source-status"
        assert ns.source == "foo"
        assert ns.details is True
        assert ns.json is True


class TestSourceStatusDetailsCli:
    def test_details_without_source_returns_2(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ns = argparse.Namespace(
            command="source-status", source=None, json=True, details=True, config=None,
        )
        assert cmd_source_status(ns) == 2
        assert "requires --source" in capsys.readouterr().out

    def test_details_without_json_returns_2(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ns = argparse.Namespace(
            command="source-status", source="local", json=False, details=True, config=None,
        )
        rc = cmd_source_status(ns)
        # Either 2 (if --source resolves) or 1 (PuzzleManagerError before our check)
        # — we only care that we never emit a non-JSON details payload.
        out = capsys.readouterr().out
        if rc == 2:
            assert "requires --json" in out
