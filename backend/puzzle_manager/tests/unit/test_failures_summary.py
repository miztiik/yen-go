"""Unit tests for ``status --failures-summary`` (Theme 2a).

Two layers:
1. Pure aggregation tests on ``summarize_failures()`` — keyed by (stage,
   error_type), per-group caps, sort order, sample preservation.
2. CLI handler tests that drive ``cmd_status`` against a tmp
   ``YENGO_RUNTIME_DIR`` populated with real RunState JSON files via
   ``StateManager``. No mocks — the marshalling/dumping logic is the
   contract the dashboard depends on.
"""

from __future__ import annotations

import json
from argparse import Namespace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.puzzle_manager.models.failures import (
    FailureGroup,
    summarize_failures,
)
from backend.puzzle_manager.models.enums import RunStatus
from backend.puzzle_manager.state.models import Failure, RunState


def _mk_run(run_id: str, *, failures: list[tuple[str, str, str, str]]) -> RunState:
    """Helper: build a RunState with N failures.

    Each tuple: (item_id, stage, error_type, error_message).
    """
    started = datetime.now(UTC) - timedelta(minutes=int(run_id[-2:]) if run_id[-2:].isdigit() else 0)
    return RunState(
        run_id=run_id,
        status=RunStatus.FAILED,
        started_at=started,
        failures=[
            Failure(item_id=item, stage=stage, error_type=err, error_message=msg)
            for (item, stage, err, msg) in failures
        ],
    )


class TestSummarizeFailures:
    def test_empty_input_returns_empty(self) -> None:
        assert summarize_failures([]) == []

    def test_groups_by_stage_and_error_type(self) -> None:
        runs = [
            _mk_run("r1", failures=[
                ("p1", "ingest",  "HTTPError", "429 rate limited"),
                ("p2", "ingest",  "HTTPError", "503 backend"),
                ("p3", "analyze", "HTTPError", "another 429"),  # different stage → distinct group
            ]),
        ]
        groups = summarize_failures(runs)
        keys = [(g.stage, g.error_type, g.count) for g in groups]
        assert ("ingest", "HTTPError", 2) in keys
        assert ("analyze", "HTTPError", 1) in keys
        assert len(groups) == 2

    def test_sort_by_count_desc_then_stage(self) -> None:
        runs = [
            _mk_run("r1", failures=[
                ("p1", "publish", "Boom", "x"),
                ("p2", "ingest",  "ValueError", "x"),
                ("p3", "ingest",  "ValueError", "x"),
                ("p4", "ingest",  "ValueError", "x"),
            ]),
        ]
        groups = summarize_failures(runs)
        # count=3 first, count=1 second
        assert groups[0].count == 3
        assert groups[0].error_type == "ValueError"
        assert groups[-1].count == 1

    def test_sample_message_is_first_non_empty(self) -> None:
        runs = [
            _mk_run("r1", failures=[
                ("p1", "ingest", "E", ""),
                ("p2", "ingest", "E", "the real message"),
                ("p3", "ingest", "E", "later message"),
            ]),
        ]
        groups = summarize_failures(runs)
        assert groups[0].sample_message == "the real message"

    def test_sample_message_truncated_at_500(self) -> None:
        long_msg = "x" * 1000
        runs = [_mk_run("r1", failures=[("p1", "ingest", "E", long_msg)])]
        groups = summarize_failures(runs)
        assert len(groups[0].sample_message) == 500

    def test_sample_puzzle_ids_capped_at_5_and_deduped(self) -> None:
        runs = [
            _mk_run("r1", failures=[
                (f"p{i}", "ingest", "E", "msg") for i in range(10)
            ] + [
                ("p0", "ingest", "E", "dup")  # duplicate id → must not re-add
            ]),
        ]
        groups = summarize_failures(runs)
        assert groups[0].sample_puzzle_ids == ["p0", "p1", "p2", "p3", "p4"]

    def test_affected_runs_capped_at_5_and_deduped(self) -> None:
        runs = [
            _mk_run(f"run-{i:02d}", failures=[("p", "ingest", "E", "")])
            for i in range(8)
        ]
        groups = summarize_failures(runs)
        assert len(groups[0].affected_runs) == 5
        # Insertion order = first 5 distinct run_ids.
        assert groups[0].affected_runs == [r.run_id for r in runs[:5]]


class TestStatusFailuresSummaryCli:
    def _setup_runs(self, runs_dir: Path, runs: list[RunState]) -> None:
        runs_dir.mkdir(parents=True, exist_ok=True)
        for run in runs:
            (runs_dir / f"{run.run_id}.json").write_text(
                run.model_dump_json(indent=2), encoding="utf-8",
            )

    @pytest.fixture
    def env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        runs_dir = tmp_path / ".pm-runtime" / "state" / "runs"
        self._setup_runs(runs_dir, [
            _mk_run("20260507-aaaaaaaa", failures=[
                ("p1", "ingest", "HTTPError", "429"),
                ("p2", "ingest", "HTTPError", "503"),
            ]),
            _mk_run("20260507-bbbbbbbb", failures=[
                ("p3", "publish", "DBError", "locked"),
            ]),
        ])
        yield runs_dir
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

    def _args(self, **overrides: object) -> Namespace:
        base = {
            "config": None,
            "json": True,
            "history": None,
            "failures_summary": True,
            "last": 10,
            "command": "status",
        }
        base.update(overrides)
        return Namespace(**base)

    def test_emits_grouped_json(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_status
        rc = cmd_status(self._args())
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        # 2 distinct (stage, error_type) groups across both runs.
        assert {(g["stage"], g["error_type"]) for g in payload} == {
            ("ingest", "HTTPError"),
            ("publish", "DBError"),
        }
        ingest_grp = next(g for g in payload if g["stage"] == "ingest")
        assert ingest_grp["count"] == 2
        assert ingest_grp["sample_puzzle_ids"] == ["p1", "p2"]
        assert "20260507-aaaaaaaa" in ingest_grp["affected_runs"]

    def test_human_output_includes_header_and_rows(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_status
        rc = cmd_status(self._args(json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "Failure digest" in out
        assert "HTTPError" in out
        assert "DBError" in out

    def test_empty_history_returns_empty_list(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        try:
            from backend.puzzle_manager.cli import cmd_status
            rc = cmd_status(self._args())
            assert rc == 0
            assert json.loads(capsys.readouterr().out) == []
        finally:
            paths.get_runtime_dir.cache_clear()
            paths.get_project_root.cache_clear()

    def test_last_caps_runs_scanned(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.cli import cmd_status
        rc = cmd_status(self._args(last=1))
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        # Sorting is by run_id desc → only the lexicographically-last run scanned.
        # Both runs share a date prefix so 'b...' wins.
        runs_seen: set[str] = set()
        for g in payload:
            runs_seen.update(g["affected_runs"])
        assert runs_seen == {"20260507-bbbbbbbb"}


class TestFailureGroupModel:
    def test_count_must_be_at_least_1(self) -> None:
        with pytest.raises(Exception):
            FailureGroup(
                stage="ingest", error_type="E", count=0,
                sample_message="", sample_puzzle_ids=[], affected_runs=[],
            )
