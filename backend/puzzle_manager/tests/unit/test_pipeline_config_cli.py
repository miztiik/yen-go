"""Unit tests for ``pipeline-config`` show/set (Theme 7d)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.puzzle_manager.cli import cmd_pipeline_config


def _seed(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "pipeline.json").write_text(
        json.dumps({
            "version": "1.0",
            "batch": {"size": 2000, "max_files_per_dir": 2000},
            "retention": {"logs_days": 45},
        }),
        encoding="utf-8",
    )
    return cfg_dir


def _ns(cfg_dir: Path, action: str, **kw) -> argparse.Namespace:
    base = {
        "config": str(cfg_dir),
        "json": True,
        "force": True,
        "pipeline_config_action": action,
        "set_pairs": [],
    }
    base.update(kw)
    return argparse.Namespace(**base)


class TestShow:
    def test_show_emits_pipeline_envelope(
        self, tmp_path: Path, capsys,
    ) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(cfg, "show"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["pipeline"]["batch"]["size"] == 2000


class TestSet:
    def test_set_dotted_path_mutates(
        self, tmp_path: Path, capsys,
    ) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(
            cfg, "set", set_pairs=["batch.size=4000"],
        ))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True and out["applied"] is True
        doc = json.loads((cfg / "pipeline.json").read_text(encoding="utf-8"))
        assert doc["batch"]["size"] == 4000
        # untouched siblings preserved
        assert doc["batch"]["max_files_per_dir"] == 2000
        assert doc["retention"]["logs_days"] == 45

    def test_set_creates_intermediate_dicts(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(
            cfg, "set", set_pairs=["new.nested.key=42"],
        ))
        assert rc == 0
        doc = json.loads((cfg / "pipeline.json").read_text(encoding="utf-8"))
        assert doc["new"]["nested"]["key"] == 42

    def test_set_without_pairs_returns_2(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(cfg, "set", set_pairs=[]))
        assert rc == 2

    def test_plain_value_falls_back_to_string(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(
            cfg, "set", set_pairs=["staging.cleanup_policy=on_failure"],
        ))
        assert rc == 0
        doc = json.loads((cfg / "pipeline.json").read_text(encoding="utf-8"))
        assert doc["staging"]["cleanup_policy"] == "on_failure"

    def test_json_value_parses(self, tmp_path: Path) -> None:
        cfg = _seed(tmp_path)
        rc = cmd_pipeline_config(_ns(
            cfg, "set", set_pairs=['daily.target_levels=[1,2,3]'],
        ))
        assert rc == 0
        doc = json.loads((cfg / "pipeline.json").read_text(encoding="utf-8"))
        assert doc["daily"]["target_levels"] == [1, 2, 3]
