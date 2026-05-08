"""Unit tests for ``adapter-config bootstrap`` (Theme 7c)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_adapter_config


def _seed(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    good = tmp_path / "data" / "src-a-folder"
    good.mkdir(parents=True)
    (cfg_dir / "sources.json").write_text(
        json.dumps({
            "active_adapter": "src-a",
            "sources": [{
                "id": "src-a", "name": "A", "adapter": "local",
                "config": {"path": good.as_posix()},
            }],
        }),
        encoding="utf-8",
    )
    return cfg_dir


def _ns(cfg_dir: Path, **kw) -> argparse.Namespace:
    base = {
        "config": str(cfg_dir),
        "json": True,
        "force": True,
        "adapter_config_action": "bootstrap",
        "bootstrap_adapter": "local",
        "id_prefix": "",
        "dry_run": False,
    }
    base.update(kw)
    return argparse.Namespace(**base)


class TestBootstrap:
    def test_dry_run_proposes_without_writing(
        self, tmp_path: Path, capsys,
    ) -> None:
        cfg = _seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "alpha").mkdir(parents=True)
        (scan / "beta").mkdir(parents=True)
        before = (cfg / "sources.json").read_text(encoding="utf-8")
        rc = cmd_adapter_config(_ns(cfg, from_folder=str(scan), dry_run=True))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["dry_run"] is True
        assert out["applied"] is False
        ids = sorted(e["id"] for e in out["entries"])
        assert ids == ["alpha", "beta"]
        after = (cfg / "sources.json").read_text(encoding="utf-8")
        assert before == after, "dry-run must not touch sources.json"

    def test_apply_writes_only_fresh_ids(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "src-a").mkdir(parents=True)  # collides with existing
        (scan / "fresh-one").mkdir(parents=True)
        rc = cmd_adapter_config(_ns(cfg, from_folder=str(scan)))
        assert rc == 0
        doc = json.loads((cfg / "sources.json").read_text(encoding="utf-8"))
        ids = [s["id"] for s in doc["sources"]]
        assert "fresh-one" in ids
        # src-a unchanged (only one entry with that id)
        assert ids.count("src-a") == 1

    def test_id_prefix(self, tmp_path: Path, capsys) -> None:
        cfg = _seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "lab").mkdir(parents=True)
        rc = cmd_adapter_config(_ns(
            cfg, from_folder=str(scan), id_prefix="bootstrap-",
            dry_run=True,
        ))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["entries"][0]["id"] == "bootstrap-lab"

    def test_bad_folder(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_adapter_config(_ns(
            cfg, from_folder=str(tmp_path / "nope"),
        ))
        assert rc == 2

    def test_slugify_handles_spaces_and_caps(
        self, tmp_path: Path, capsys,
    ) -> None:
        cfg = _seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "Mixed Case Folder").mkdir(parents=True)
        rc = cmd_adapter_config(_ns(
            cfg, from_folder=str(scan), dry_run=True,
        ))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["entries"][0]["id"] == "mixed-case-folder"
