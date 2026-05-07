"""Unit tests for ``inventory check --json`` Pydantic contract (Theme 14a)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.models.integrity import (
    IntegrityIssue,
    IntegrityReport,
    IntegritySummary,
    _puzzle_id_from_path,
)


class _FakeLegacyResult:
    """Mimics the relevant subset of ``IntegrityResult`` without importing it."""

    def __init__(self, *, orphan_entries: list[str], orphan_files: list[str]) -> None:
        self.orphan_entries = orphan_entries  # = "missing_file" rows
        self.orphan_files = orphan_files  # = "orphan_file" rows


class TestPuzzleIdExtraction:
    def test_strips_dirs_and_extension(self) -> None:
        assert _puzzle_id_from_path("sgf/0001/abc123def4567890.sgf") == "abc123def4567890"

    def test_returns_none_for_non_sgf(self) -> None:
        assert _puzzle_id_from_path("logs/2026-05-07.log") is None

    def test_handles_bare_filename(self) -> None:
        assert _puzzle_id_from_path("xyz.sgf") == "xyz"


class TestIntegrityReportFromLegacy:
    def test_clean_corpus_is_ok(self) -> None:
        result = _FakeLegacyResult(orphan_entries=[], orphan_files=[])
        report = IntegrityReport.from_legacy_result(result)
        assert report.ok is True
        assert report.issues == []
        assert report.summary.missing_file == 0
        assert report.summary.orphan_file == 0

    def test_one_of_each_kind_classified(self) -> None:
        result = _FakeLegacyResult(
            orphan_entries=["sgf/0001/missing01.sgf"],
            orphan_files=["sgf/0001/orphan99.sgf"],
        )
        report = IntegrityReport.from_legacy_result(result)
        assert report.ok is False
        assert report.summary.missing_file == 1
        assert report.summary.orphan_file == 1
        kinds = {(i.kind, i.puzzle_id, i.path) for i in report.issues}
        assert kinds == {
            ("missing_file", "missing01", "sgf/0001/missing01.sgf"),
            ("orphan_file", "orphan99", "sgf/0001/orphan99.sgf"),
        }

    def test_unknown_kind_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError):
            IntegrityIssue(kind="hash_mismatch", path="x.sgf")  # type: ignore[arg-type]

    def test_summary_counts_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError):
            IntegritySummary(missing_file=-1, orphan_file=0)


class TestInventoryCheckJsonCli:
    """Drives ``cmd_inventory(check=True, json=True)`` against a real on-disk
    publication root + publish-log seeded to produce one missing + one orphan."""

    @pytest.fixture
    def env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()
        # Publication root: yengo-puzzle-collections/sgf/{batch}/{hash}.sgf
        pub = tmp_path / "yengo-puzzle-collections"
        sgf_dir = pub / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        # File on disk that has a publish-log entry → healthy, ignored.
        (sgf_dir / "aaaaaaaaaaaaaaaa.sgf").write_text("(;FF[4])", encoding="utf-8")
        # File on disk with NO publish-log entry → orphan_file row.
        (sgf_dir / "ffffffffffffffff.sgf").write_text("(;FF[4])", encoding="utf-8")
        # Publish-log entry that points at a missing file → missing_file row.
        log_dir = pub / ".puzzle-inventory-state" / "publish-log"
        log_dir.mkdir(parents=True)
        (log_dir / "2026-05-07.jsonl").write_text(
            "\n".join([
                json.dumps({
                    "puzzle_id": "aaaaaaaaaaaaaaaa",
                    "path": "sgf/0001/aaaaaaaaaaaaaaaa.sgf",
                    "run_id": "fixture", "source_id": "src",
                    "quality": 3, "trace_id": "t-aaa", "level": "intermediate",
                    "tags": [], "collections": [],
                }),
                json.dumps({
                    "puzzle_id": "1111111111111111",
                    "path": "sgf/0001/1111111111111111.sgf",
                    "run_id": "fixture", "source_id": "src",
                    "quality": 3, "trace_id": "t-bbb", "level": "intermediate",
                    "tags": [], "collections": [],
                }),
            ]) + "\n",
            encoding="utf-8",
        )
        yield tmp_path
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

    def _args(self, **overrides: object) -> Namespace:
        base = {
            "config": None, "command": "inventory", "verbose": 0,
            "json": True, "check": True,
            "rebuild": False, "reconcile": False, "fix": False,
        }
        base.update(overrides)
        return Namespace(**base)

    def test_json_output_matches_pydantic_shape(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args())
        # Exit code 1 because issues are present (matches pre-Theme-14a behavior).
        assert rc == 1
        payload = json.loads(capsys.readouterr().out)
        # Re-parse through the model to lock the wire contract.
        report = IntegrityReport.model_validate(payload)
        assert report.ok is False
        assert report.summary.missing_file == 1
        assert report.summary.orphan_file == 1
        kinds = {(i.kind, i.puzzle_id) for i in report.issues}
        assert kinds == {
            ("missing_file", "1111111111111111"),
            ("orphan_file", "ffffffffffffffff"),
        }

    def test_human_output_path_unchanged_when_json_off(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(json=False))
        assert rc == 1
        out = capsys.readouterr().out
        # Human format keeps the existing prefix from format_integrity_result.
        assert "Inventory integrity check" in out
