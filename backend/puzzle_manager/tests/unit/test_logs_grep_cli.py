"""Unit tests for ``logs grep`` CLI command (Theme 4a).

Real-fixture tests (no mocks): seed a tmp ``.pm-runtime/logs/`` with
known stage logs, point ``YENGO_RUNTIME_DIR`` + ``YENGO_ROOT`` at the
fixture, and drive the CLI handler directly. The tmp directory mirrors
the production layout (``YYYY-MM-DD-{stage}.log``) so the tests catch
filename-regex regressions.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import _cmd_logs_grep, cmd_logs


def _make_logs(tmp_path: Path) -> Path:
    """Seed a fake .pm-runtime/logs/ tree with three stages × two days."""
    logs_dir = tmp_path / ".pm-runtime" / "logs"
    logs_dir.mkdir(parents=True)

    def jline(ts: str, msg: str, **extra: object) -> str:
        return json.dumps({"ts": ts, "msg": msg, **extra})

    (logs_dir / "2026-05-05-ingest.log").write_text(
        "\n".join([
            jline("2026-05-05 10:00:00.001", "Ingest start", source="sanderland"),
            jline("2026-05-05 10:00:01.001", "Fetched batch", count=50),
            jline("2026-05-05 10:00:02.001", "ERROR rate-limited"),
            jline("2026-05-05 10:00:03.001", "Retry succeeded"),
        ]) + "\n",
        encoding="utf-8",
    )
    (logs_dir / "2026-05-05-analyze.log").write_text(
        "\n".join([
            jline("2026-05-05 11:00:00.001", "Analyze start"),
            jline("2026-05-05 11:00:01.001", "Analyzed puzzle abc123"),
        ]) + "\n",
        encoding="utf-8",
    )
    (logs_dir / "2026-05-06-ingest.log").write_text(
        "\n".join([
            jline("2026-05-06 09:00:00.001", "Ingest start", source="kisvadim"),
            "this line is not JSON but still scannable rate-limited",
            jline("2026-05-06 09:00:02.001", "Done"),
        ]) + "\n",
        encoding="utf-8",
    )
    # File that does NOT match YYYY-MM-DD-{stage}.log — must be skipped.
    (logs_dir / "stray-not-a-date.log").write_text("ignored\n", encoding="utf-8")
    return logs_dir


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point cli to a tmp project root + runtime dir; return the logs dir."""
    monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
    monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
    # paths.get_runtime_dir / get_project_root cache results — clear the LRU.
    from backend.puzzle_manager import paths
    paths.get_runtime_dir.cache_clear()
    paths.get_project_root.cache_clear()
    return _make_logs(tmp_path)


def _args(pattern: str, **overrides: object) -> Namespace:
    base = {
        "pattern": pattern,
        "stage": None,
        "from_date": None,
        "to_date": None,
        "limit": 200,
        "json": True,
    }
    base.update(overrides)
    return Namespace(**base)


def _run_grep(env_logs: Path, capsys: pytest.CaptureFixture[str], **kw: object) -> list[dict]:
    pattern = kw.pop("pattern", "ERROR")
    rc = _cmd_logs_grep(_args(pattern, **kw))
    assert rc == 0
    out = capsys.readouterr().out
    return json.loads(out)


class TestLogsGrepHappyPath:
    def test_finds_match_across_files(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="rate-limited")
        # Two files contain "rate-limited" — one JSON, one raw.
        assert len(hits) == 2
        files = sorted(h["file"] for h in hits)
        assert files == [
            ".pm-runtime/logs/2026-05-05-ingest.log",
            ".pm-runtime/logs/2026-05-06-ingest.log",
        ]

    def test_parses_ts_from_json_lines(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="Ingest start")
        assert len(hits) == 2
        for h in hits:
            assert h["ts"] is not None
            assert h["ts"].startswith("2026-05-0")
            assert h["stream"] == "stdout"
            assert h["line_no"] >= 1

    def test_ts_is_none_for_non_json_lines(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="not JSON but still scannable")
        assert len(hits) == 1
        assert hits[0]["ts"] is None
        assert "scannable" in hits[0]["text"]

    def test_context_before_and_after_capped_at_two(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        hits = _run_grep(env, capsys, pattern="ERROR rate-limited")
        assert len(hits) == 1
        h = hits[0]
        assert len(h["context_before"]) == 2
        assert len(h["context_after"]) == 1  # only one line follows in that file
        assert "Fetched batch" in h["context_before"][1]
        assert "Retry succeeded" in h["context_after"][0]


class TestLogsGrepFilters:
    def test_stage_filter(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="start", stage="analyze")
        assert len(hits) == 1
        assert "analyze" in hits[0]["file"]

    def test_date_range_filter(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="Ingest start", from_date="2026-05-06")
        assert len(hits) == 1
        assert "2026-05-06-ingest" in hits[0]["file"]

    def test_to_date_filter(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="Ingest start", to_date="2026-05-05")
        assert len(hits) == 1
        assert "2026-05-05-ingest" in hits[0]["file"]

    def test_limit_caps_results(self, env: Path, capsys: pytest.CaptureFixture[str]) -> None:
        hits = _run_grep(env, capsys, pattern="start", limit=1)
        assert len(hits) == 1


class TestLogsGrepEdgeCases:
    def test_no_logs_dir_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        rc = _cmd_logs_grep(_args("anything"))
        assert rc == 0
        assert json.loads(capsys.readouterr().out) == []

    def test_invalid_regex_returns_2(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = _cmd_logs_grep(_args("[unclosed"))
        assert rc == 2
        payload = json.loads(capsys.readouterr().out)
        assert payload["error"] == "invalid_regex"

    def test_filename_regex_skips_stray_files(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # The stray "stray-not-a-date.log" file contains "ignored" but
        # MUST NOT be scanned — its filename does not match the pattern.
        hits = _run_grep(env, capsys, pattern="ignored")
        assert hits == []

    def test_human_output_when_not_json(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = _cmd_logs_grep(_args("Analyze start", json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "2026-05-05-analyze.log" in out
        assert "Analyze start" in out


class TestCmdLogsDispatcher:
    def test_unknown_subcommand_returns_1(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = cmd_logs(Namespace(logs_command="bogus"))
        assert rc == 1
