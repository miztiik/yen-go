"""Unit tests for ``runs-diff`` (Theme 9)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_runs_diff
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.publish_log import PublishLogWriter


def _entry(run_id: str, puzzle_id: str) -> PublishLogEntry:
    return PublishLogEntry(
        run_id=run_id, puzzle_id=puzzle_id, source_id="src",
        path=f"sgf/0001/{puzzle_id}.sgf", quality=3,
        trace_id="t" * 16, level="elementary",
    )


def _seed_state(runs_dir: Path, run_id: str, ingested: int,
                failed: int, skipped: int, status: str = "success") -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "status": status,
        "stages": [
            {"name": "ingest", "processed_count": ingested,
             "failed_count": 0, "skipped_count": 0},
            {"name": "analyze", "processed_count": ingested,
             "failed_count": failed, "skipped_count": skipped},
        ],
    }), encoding="utf-8")


@pytest.fixture
def runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runs = tmp_path / "state" / "runs"
    publog = tmp_path / "publog"
    publog.mkdir(parents=True)
    monkeypatch.setattr("backend.puzzle_manager.cli.get_pm_state_dir",
                        lambda: tmp_path / "state", raising=False)
    monkeypatch.setattr("backend.puzzle_manager.paths.get_pm_state_dir",
                        lambda: tmp_path / "state")
    monkeypatch.setattr("backend.puzzle_manager.cli.get_publish_log_dir",
                        lambda: publog)
    return tmp_path


def _ns(a: str, b: str, **kw) -> argparse.Namespace:
    base = {"run_a": a, "run_b": b, "max_samples": 20, "json": True}
    base.update(kw)
    return argparse.Namespace(**base)


class TestRunsDiff:
    def test_set_diff_added_removed_common(
        self, runtime: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        runs_dir = runtime / "state" / "runs"
        _seed_state(runs_dir, "run-A", ingested=10, failed=1, skipped=2)
        _seed_state(runs_dir, "run-B", ingested=15, failed=0, skipped=3)

        publog = runtime / "publog"
        writer = PublishLogWriter(log_dir=publog)
        # A has {p1, p2, p3}; B has {p2, p3, p4, p5}
        for pid in ("p1", "p2", "p3"):
            writer.write(_entry("run-A", pid))
        for pid in ("p2", "p3", "p4", "p5"):
            writer.write(_entry("run-B", pid))

        rc = cmd_runs_diff(_ns("run-A", "run-B"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["run_a"]["exists"] is True
        assert out["run_b"]["exists"] is True
        assert out["added_puzzles"]["count"] == 2
        assert out["added_puzzles"]["samples"] == ["p4", "p5"]
        assert out["removed_puzzles"]["count"] == 1
        assert out["removed_puzzles"]["samples"] == ["p1"]
        assert out["common_count"] == 2
        assert out["stats_diff"] == {
            "ingested": 5, "failed": -1, "skipped": 1,
        }

    def test_missing_run_state_marks_not_exists(
        self, runtime: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = cmd_runs_diff(_ns("ghost-A", "ghost-B"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["run_a"]["exists"] is False
        assert out["run_b"]["exists"] is False
        assert out["added_puzzles"]["count"] == 0
        assert out["removed_puzzles"]["count"] == 0
