"""Unit tests for ``inventory {rebuild,reconcile,fix} --dry-run --json`` (Theme 14c1)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.models.inventory_preview import InventoryMutationPreview


class TestInventoryMutationPreviewModel:
    def test_rejects_unknown_op(self) -> None:
        with pytest.raises(ValueError):
            InventoryMutationPreview(
                op="purge",  # type: ignore[arg-type]
                snapshot_exists=False,
                snapshot_total_before=None,
                disk_total=0,
                delta=0,
                would_rewrite_snapshot=True,
                would_rebuild_search_db=False,
            )

    def test_disk_total_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError):
            InventoryMutationPreview(
                op="rebuild",
                snapshot_exists=False,
                snapshot_total_before=None,
                disk_total=-1,
                delta=-1,
                would_rewrite_snapshot=True,
                would_rebuild_search_db=True,
            )


class TestInventoryDryRunCli:
    """Drives ``cmd_inventory`` against a real on-disk publication root with
    a known number of SGFs and a synthetic inventory.json snapshot.

    The fixture seeds 5 SGFs on disk under ``sgf/0001/`` and a snapshot
    that claims 3 puzzles, giving a +2 delta the assertions can pin.
    """

    @pytest.fixture
    def env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        from backend.puzzle_manager import paths
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

        pub = tmp_path / "yengo-puzzle-collections"
        sgf_dir = pub / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        for i in range(5):
            (sgf_dir / f"{i:016x}.sgf").write_text("(;FF[4])", encoding="utf-8")

        # Snapshot the dashboard would normally read — claim 3 puzzles, so
        # the dry-run should report delta=+2 against the 5 on disk.
        ops = pub / ".puzzle-inventory-state"
        ops.mkdir(parents=True)
        snapshot = {
            "schema_version": "2.0",
            "collection": {
                "total_puzzles": 3,
                "by_puzzle_level": {},
                "by_tag": {},
                "by_puzzle_quality": {},
            },
            "last_updated": "2026-05-07T00:00:00Z",
            "last_run_id": "fixture-run",
        }
        (ops / "inventory.json").write_text(
            json.dumps(snapshot), encoding="utf-8",
        )

        yield tmp_path
        paths.get_runtime_dir.cache_clear()
        paths.get_project_root.cache_clear()

    def _args(self, **overrides: object) -> Namespace:
        base: dict[str, object] = {
            "config": None, "command": "inventory", "verbose": 0,
            "json": True, "dry_run": True,
            "rebuild": False, "reconcile": False, "fix": False, "check": False,
        }
        base.update(overrides)
        return Namespace(**base)

    def test_reconcile_preview_reports_disk_count_and_delta(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(reconcile=True))
        assert rc == 0
        report = InventoryMutationPreview.model_validate_json(capsys.readouterr().out)
        assert report.op == "reconcile"
        assert report.snapshot_exists is True
        assert report.snapshot_total_before == 3
        assert report.disk_total == 5
        assert report.delta == 2
        assert report.would_rewrite_snapshot is True
        assert report.would_rebuild_search_db is False
        assert report.fix_skip_reason is None

    def test_rebuild_preview_flags_search_db_rewrite(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(rebuild=True))
        assert rc == 0
        report = InventoryMutationPreview.model_validate_json(capsys.readouterr().out)
        assert report.op == "rebuild"
        # No inventory op rebuilds yengo-search.db today (vacuum-db owns that).
        assert report.would_rebuild_search_db is False
        assert report.would_rewrite_snapshot is True

    def test_fix_preview_skips_when_check_clean(
        self, env: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force check_integrity to return a valid result so the fix path predicts no-op.
        from backend.puzzle_manager.inventory import cli as inv_cli

        class _OkResult:
            is_valid = True
            orphan_entries: list[str] = []
            orphan_files: list[str] = []
            discrepancies: list[str] = []
            level_mismatches: dict[str, tuple[int, int]] = {}
            total_actual = 5

        monkeypatch.setattr(inv_cli, "check_integrity", lambda **kw: _OkResult(), raising=False)
        # check_integrity is imported lazily inside _emit_mutation_preview.
        from backend.puzzle_manager.inventory import check as inv_check
        monkeypatch.setattr(inv_check, "check_integrity", lambda **kw: _OkResult())

        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(fix=True))
        assert rc == 0
        report = InventoryMutationPreview.model_validate_json(capsys.readouterr().out)
        assert report.op == "fix"
        assert report.would_rewrite_snapshot is False
        assert report.fix_skip_reason is not None

    def test_fix_preview_proceeds_when_check_dirty(
        self, env: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _DirtyResult:
            is_valid = False
            orphan_entries: list[str] = ["sgf/0001/missing.sgf"]
            orphan_files: list[str] = []
            discrepancies: list[str] = ["one missing"]
            level_mismatches: dict[str, tuple[int, int]] = {}
            total_actual = 5

        from backend.puzzle_manager.inventory import check as inv_check
        monkeypatch.setattr(inv_check, "check_integrity", lambda **kw: _DirtyResult())

        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(fix=True))
        assert rc == 0
        report = InventoryMutationPreview.model_validate_json(capsys.readouterr().out)
        assert report.op == "fix"
        assert report.would_rewrite_snapshot is True
        assert report.fix_skip_reason is None

    def test_dry_run_does_not_mutate_snapshot(self, env: Path) -> None:
        snapshot_path = env / "yengo-puzzle-collections" / ".puzzle-inventory-state" / "inventory.json"
        before = snapshot_path.read_text(encoding="utf-8")
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        for op in ("rebuild", "reconcile"):
            rc = cmd_inventory(self._args(**{op: True}))
            assert rc == 0
        after = snapshot_path.read_text(encoding="utf-8")
        # Byte-identical: dry-run is read-only.
        assert before == after

    def test_human_output_when_json_off(
        self, env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(self._args(reconcile=True, json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "--reconcile --dry-run" in out
        assert "Disk total" in out
        assert "Delta" in out
