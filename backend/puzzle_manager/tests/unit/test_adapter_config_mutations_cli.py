"""Unit tests for ``adapter-config {add|clone|update|remove}`` (Theme 7b)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_adapter_config


def _write_sources_json(
    tmp_path: Path,
    *,
    sources: list[dict],
    active: str,
) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(exist_ok=True)
    cfg = {"active_adapter": active, "sources": sources}
    (cfg_dir / "sources.json").write_text(json.dumps(cfg), encoding="utf-8")
    return cfg_dir


@pytest.fixture
def cfg_dir(tmp_path: Path) -> Path:
    real = tmp_path / "data" / "good"
    real.mkdir(parents=True)
    return _write_sources_json(
        tmp_path,
        sources=[
            {
                "id": "src-a", "name": "Src A", "adapter": "local",
                "config": {"path": str(real)},
            },
            {
                "id": "src-b", "name": "Src B", "adapter": "local",
                "config": {"path": str(real)},
            },
        ],
        active="src-a",
    )


def _ns(cfg_dir: Path, **kw) -> argparse.Namespace:
    base = {
        "config": str(cfg_dir),
        "json": True,
        "force": True,  # bypass pipeline-lock in tests
    }
    base.update(kw)
    return argparse.Namespace(**base)


def _read(cfg_dir: Path) -> dict:
    return json.loads((cfg_dir / "sources.json").read_text(encoding="utf-8"))


class TestAdd:
    def test_appends_new_source(self, cfg_dir: Path, capsys, tmp_path: Path) -> None:
        new_path = tmp_path / "data" / "newsrc"
        new_path.mkdir(parents=True)
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="add",
            new_id="src-c", new_name="Src C", new_adapter="local",
            config_json=json.dumps({"path": str(new_path)}),
        ))
        assert rc == 0
        doc = _read(cfg_dir)
        ids = [s["id"] for s in doc["sources"]]
        assert "src-c" in ids

    def test_rejects_duplicate(self, cfg_dir: Path, capsys) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="add",
            new_id="src-a", new_name="Dup", new_adapter="local",
            config_json="{}",
        ))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any(e["code"] == "duplicate-id" for e in out["errors"])

    def test_rejects_bad_json(self, cfg_dir: Path, capsys) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="add",
            new_id="src-c", new_name="C", new_adapter="local",
            config_json="{not-json}",
        ))
        assert rc == 2

    def test_rejects_invalid_id_via_schema(
        self, cfg_dir: Path, capsys, tmp_path: Path,
    ) -> None:
        # IDs must match ^[a-z][a-z0-9-]*$ — uppercase fails.
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="add",
            new_id="BAD_ID", new_name="X", new_adapter="local",
            config_json="{}",
        ))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any(e["code"] == "schema" for e in out["errors"])


class TestClone:
    def test_preserves_config_block(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="clone",
            source_id="src-a", new_id="src-a-copy", new_name="Copy",
        ))
        assert rc == 0
        doc = _read(cfg_dir)
        original = next(s for s in doc["sources"] if s["id"] == "src-a")
        clone = next(s for s in doc["sources"] if s["id"] == "src-a-copy")
        assert clone["adapter"] == original["adapter"]
        assert clone["config"] == original["config"]

    def test_rejects_unknown_source(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="clone",
            source_id="ghost", new_id="x", new_name="X",
        ))
        assert rc == 2

    def test_rejects_duplicate_new_id(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="clone",
            source_id="src-a", new_id="src-b", new_name="dup",
        ))
        assert rc == 2


class TestUpdate:
    def test_set_pairs_merge_into_config(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="update",
            source_id="src-a",
            set_pairs=['validate=true', 'comment="hello"'],
            new_name="Renamed",
        ))
        assert rc == 0
        target = next(s for s in _read(cfg_dir)["sources"] if s["id"] == "src-a")
        assert target["name"] == "Renamed"
        assert target["config"]["validate"] is True
        assert target["config"]["comment"] == "hello"

    def test_string_fallback_for_non_json(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="update",
            source_id="src-a",
            set_pairs=["label=plain-string"],
            new_name=None,
        ))
        assert rc == 0
        target = next(s for s in _read(cfg_dir)["sources"] if s["id"] == "src-a")
        assert target["config"]["label"] == "plain-string"

    def test_bad_set_pair(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="update",
            source_id="src-a",
            set_pairs=["no-equals-sign"],
            new_name=None,
        ))
        assert rc == 2


class TestRemove:
    def test_refuses_active_without_force(
        self, cfg_dir: Path, capsys,
    ) -> None:
        ns = _ns(cfg_dir,
                 adapter_config_action="remove", source_id="src-a")
        ns.force = False
        rc = cmd_adapter_config(ns)
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any(e["code"] == "active-source" for e in out["errors"])

    def test_removes_inactive_source(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="remove", source_id="src-b",
        ))
        assert rc == 0
        ids = [s["id"] for s in _read(cfg_dir)["sources"]]
        assert "src-b" not in ids

    def test_rejects_unknown_source(self, cfg_dir: Path) -> None:
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="remove", source_id="ghost",
        ))
        assert rc == 2

    def test_force_allows_removing_active(self, cfg_dir: Path) -> None:
        # Need >= 2 remaining for schema minItems:1; since src-b stays, OK.
        rc = cmd_adapter_config(_ns(
            cfg_dir,
            adapter_config_action="remove", source_id="src-a",
        ))
        assert rc == 0
