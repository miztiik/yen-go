"""Unit tests for ``activity`` (Theme 13a).

Two layers:
1. Pure aggregation tests on ``compute_activity()`` — merging, ordering,
   filter semantics, missing-source tolerance.
2. CLI handler test that drives ``cmd_activity`` against a tmp
   ``YENGO_RUNTIME_DIR`` populated with real run-state JSON. The wire
   shape is what the dashboard's timeline consumes.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.models.activity import (
    ActivityEvent,
    compute_activity,
)


def _write_run(runs_dir: Path, *, run_id: str, status: str, ts: str,
               failures: int = 0) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "status": status,
        "started_at": ts,
        "completed_at": ts,
        "failures": [{"item_id": f"p{i}", "stage": "ingest"} for i in range(failures)],
    }
    (runs_dir / f"{run_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_audit(audit_file: Path, *, ts: str, operation: str, target: str,
                 details: dict | None = None) -> None:
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": ts, "operation": operation, "target": target,
           "details": details or {}}
    with audit_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _write_publish(publish_dir: Path, *, date: str, run_id: str, count: int,
                   source_id: str = "src") -> None:
    publish_dir.mkdir(parents=True, exist_ok=True)
    f = publish_dir / f"{date}.jsonl"
    with f.open("a", encoding="utf-8") as fh:
        for i in range(count):
            row = {"run_id": run_id, "puzzle_id": f"p{i}", "source_id": source_id}
            fh.write(json.dumps(row) + "\n")


class TestComputeActivity:
    def test_missing_sources_return_empty(self, tmp_path: Path) -> None:
        events = compute_activity(
            runs_dir=tmp_path / "absent",
            audit_file=tmp_path / "missing.jsonl",
            publish_log_dir=tmp_path / "absent2",
        )
        assert events == []

    def test_merges_three_sources_newest_first(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        audit = tmp_path / "audit.jsonl"
        pub = tmp_path / "publish-log"
        _write_run(runs, run_id="20260507-aaaaaaaa", status="completed",
                   ts="2026-05-07T10:00:00+00:00")
        _write_audit(audit, ts="2026-05-07T11:00:00+00:00",
                     operation="cleanup", target="staging")
        _write_publish(pub, date="2026-05-07", run_id="20260507-bbbbbbbb", count=3)

        events = compute_activity(
            runs_dir=runs, audit_file=audit, publish_log_dir=pub,
        )
        assert len(events) == 3
        # publish anchored at end-of-day → newest
        assert events[0].kind == "publish"
        assert events[1].kind == "maintenance"
        assert events[2].kind == "run"
        # publish summary aggregates per-run
        assert "3 puzzle(s)" in events[0].summary

    def test_kinds_filter(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        audit = tmp_path / "audit.jsonl"
        _write_run(runs, run_id="r1", status="completed",
                   ts="2026-05-07T10:00:00+00:00")
        _write_audit(audit, ts="2026-05-07T11:00:00+00:00",
                     operation="cleanup", target="staging")
        events = compute_activity(
            runs_dir=runs, audit_file=audit,
            publish_log_dir=tmp_path / "absent",
            kinds=["run"],
        )
        assert [e.kind for e in events] == ["run"]

    def test_kinds_filter_rejects_unknown(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="unknown kinds"):
            compute_activity(
                runs_dir=tmp_path, audit_file=tmp_path / "x",
                publish_log_dir=tmp_path, kinds=["bogus"],
            )

    def test_time_window_filter(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs, run_id="r-old", status="completed",
                   ts="2026-04-01T00:00:00+00:00")
        _write_run(runs, run_id="r-new", status="completed",
                   ts="2026-05-07T00:00:00+00:00")
        events = compute_activity(
            runs_dir=runs,
            audit_file=tmp_path / "x.jsonl",
            publish_log_dir=tmp_path / "absent",
            from_ts="2026-05-01T00:00:00+00:00",
        )
        assert {e.subject_id for e in events} == {"r-new"}

    def test_limit_caps_after_sort(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        for i in range(5):
            _write_run(runs, run_id=f"r{i}", status="completed",
                       ts=f"2026-05-0{i+1}T00:00:00+00:00")
        events = compute_activity(
            runs_dir=runs, audit_file=tmp_path / "x.jsonl",
            publish_log_dir=tmp_path / "absent", limit=3,
        )
        assert len(events) == 3
        # Newest first.
        assert events[0].subject_id == "r4"

    def test_run_failure_summary_includes_count(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs, run_id="r-fail", status="failed",
                   ts="2026-05-07T00:00:00+00:00", failures=4)
        events = compute_activity(
            runs_dir=runs, audit_file=tmp_path / "x",
            publish_log_dir=tmp_path / "absent",
        )
        assert "failed" in events[0].summary
        assert "4 failures" in events[0].summary


class TestActivityModel:
    def test_kind_validated(self) -> None:
        with pytest.raises(Exception):
            ActivityEvent(
                ts="2026-05-07T00:00:00+00:00",
                kind="bogus",  # type: ignore[arg-type]
                actor="cli", subject_id="x", summary="y",
            )


class TestActivityCli:
    @pytest.fixture
    def env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        runs_dir = tmp_path / ".pm-runtime" / "state" / "runs"
        _write_run(runs_dir, run_id="20260507-aaaaaaaa", status="completed",
                   ts="2026-05-07T10:00:00+00:00")
        yield tmp_path
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

    def _args(self, **overrides: object) -> Namespace:
        base = {
            "config": None, "json": True, "command": "activity", "verbose": 0,
            "from_ts": None, "to_ts": None, "kinds": None, "limit": 100,
        }
        base.update(overrides)
        return Namespace(**base)

    def test_emits_activity_json(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_activity
        rc = cmd_activity(self._args())
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        assert any(e["kind"] == "run" for e in payload)
        assert payload[0]["subject_id"] == "20260507-aaaaaaaa"

    def test_kinds_filter_via_cli(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_activity
        rc = cmd_activity(self._args(kinds="maintenance"))
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload == []  # only seeded a run, none match

    def test_invalid_kind_returns_2(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_activity
        rc = cmd_activity(self._args(kinds="bogus"))
        assert rc == 2
        assert "unknown kinds" in capsys.readouterr().err

    def test_human_output_when_empty(
        self, env: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from backend.puzzle_manager.cli import cmd_activity
        rc = cmd_activity(self._args(json=False, kinds="publish"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "(no activity)" in out
