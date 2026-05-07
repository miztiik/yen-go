"""Unit tests for ``inventory {rebuild,reconcile,fix}`` apply path (Theme 14c2).

Covers the lock + audit + ``InventoryMutationResult`` JSON wire contract for
the non-dry-run mutating ops.
"""

from __future__ import annotations

import json
import shutil
from argparse import Namespace
from pathlib import Path

import pytest

from backend.puzzle_manager.models.inventory_preview import (
    InventoryMutationResult,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Seed YENGO_ROOT with config/, 5 published SGFs, and a stale snapshot
    that claims 3 puzzles. Apply ops must update the snapshot to 5.
    """
    monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
    monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
    from backend.puzzle_manager import paths
    paths.get_runtime_dir.cache_clear()
    paths.get_project_root.cache_clear()

    shutil.copytree(REPO_ROOT / "config", tmp_path / "config")

    pub = tmp_path / "yengo-puzzle-collections"
    sgf_dir = pub / "sgf" / "0001"
    sgf_dir.mkdir(parents=True)
    for i in range(5):
        (sgf_dir / f"{i:016x}.sgf").write_text("(;FF[4])", encoding="utf-8")

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
    (ops / "inventory.json").write_text(json.dumps(snapshot), encoding="utf-8")

    yield tmp_path
    paths.get_runtime_dir.cache_clear()
    paths.get_project_root.cache_clear()


def _args(**overrides: object) -> Namespace:
    base: dict[str, object] = {
        "config": None, "command": "inventory", "verbose": 0,
        "json": True, "dry_run": False,
        "rebuild": False, "reconcile": False, "fix": False, "check": False,
    }
    base.update(overrides)
    return Namespace(**base)


def _audit_path(env: Path) -> Path:
    return env / "yengo-puzzle-collections" / ".puzzle-inventory-state" / "audit.jsonl"


def _stub_reconcile(monkeypatch: pytest.MonkeyPatch, total: int = 5) -> None:
    """Bypass the heavy SGF parser — reconcile_inventory hits ``parse_sgf`` per
    file. Apply tests only care about the lock + audit + result shape, so we
    stub it to return a synthetic inventory with the expected total.
    """
    from backend.puzzle_manager.inventory import cli as inv_cli
    from backend.puzzle_manager.inventory.models import (
        CollectionStats,
        PuzzleCollectionInventory,
    )

    def _fake_reconcile(*args: object, **kwargs: object) -> PuzzleCollectionInventory:
        from datetime import UTC, datetime
        return PuzzleCollectionInventory(
            schema_version="2.0",
            collection=CollectionStats(
                total_puzzles=total,
                by_puzzle_level={},
                by_tag={},
                by_puzzle_quality={},
            ),
            last_updated=datetime.now(UTC),
            last_run_id="test-run",
        )

    monkeypatch.setattr(inv_cli, "_apply_rebuild", inv_cli._apply_rebuild)
    import backend.puzzle_manager.inventory.reconcile as rec_mod
    monkeypatch.setattr(rec_mod, "reconcile_inventory", _fake_reconcile)


class TestRebuildApply:
    def test_emits_result_and_writes_audit(
        self,
        env: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _stub_reconcile(monkeypatch, total=5)
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(_args(rebuild=True))
        assert rc == 0

        result = InventoryMutationResult.model_validate_json(capsys.readouterr().out)
        assert result.op == "rebuild"
        assert result.executed is True
        assert result.snapshot_total_before == 3
        assert result.snapshot_total_after == 5
        assert result.delta == 2
        assert result.rewrote_snapshot is True
        assert result.rebuilt_search_db is False
        assert result.audit_timestamp is not None

        audit_lines = _audit_path(env).read_text(encoding="utf-8").splitlines()
        assert len(audit_lines) == 1
        entry = json.loads(audit_lines[0])
        assert entry["operation"] == "inventory_rebuild"
        assert entry["target"] == "puzzle-collection"
        assert entry["details"]["total_after"] == 5
        assert entry["details"]["delta"] == 2


class TestReconcileApply:
    def test_writes_audit_with_correct_operation(
        self,
        env: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _stub_reconcile(monkeypatch, total=5)
        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(_args(reconcile=True))
        assert rc == 0
        capsys.readouterr()  # drain

        entry = json.loads(_audit_path(env).read_text(encoding="utf-8").splitlines()[0])
        assert entry["operation"] == "inventory_reconcile"


class TestFixApplySkipsWhenClean:
    def test_no_audit_when_pre_check_clean(
        self,
        env: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from backend.puzzle_manager.inventory import check as inv_check

        class _Ok:
            is_valid = True
            orphan_entries: list[str] = []
            orphan_files: list[str] = []
            discrepancies: list[str] = []
            level_mismatches: dict[str, tuple[int, int]] = {}
            total_actual = 5

        monkeypatch.setattr(inv_check, "check_integrity", lambda **kw: _Ok())

        from backend.puzzle_manager.inventory.cli import cmd_inventory
        rc = cmd_inventory(_args(fix=True))
        assert rc == 0

        result = InventoryMutationResult.model_validate_json(capsys.readouterr().out)
        assert result.op == "fix"
        assert result.rewrote_snapshot is False
        assert result.audit_timestamp is None
        assert result.fix_skip_reason is not None
        # No audit row should be written when fix short-circuits.
        assert not _audit_path(env).exists()


class TestPipelineLockBlocks:
    def test_rebuild_refuses_when_pipeline_lock_held(
        self,
        env: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _stub_reconcile(monkeypatch, total=5)
        from backend.puzzle_manager.pipeline.lock import PipelineLock

        held = PipelineLock(run_id="external-run")
        held.acquire()
        try:
            from backend.puzzle_manager.inventory.cli import cmd_inventory
            rc = cmd_inventory(_args(rebuild=True))
            # cmd_inventory traps exceptions and returns 1.
            assert rc == 1
            assert "[ERROR]" in capsys.readouterr().out
            # Snapshot must NOT have been rewritten while another holder owned the lock.
            snap = json.loads(
                (env / "yengo-puzzle-collections" / ".puzzle-inventory-state" / "inventory.json").read_text(encoding="utf-8")
            )
            assert snap["collection"]["total_puzzles"] == 3
        finally:
            held.release()
