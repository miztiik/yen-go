"""Unit tests for ``adapter-scaffold`` (Theme 12).

V1 ships ``--kind local`` only: writes a thin LocalAdapter wrapper into a
new ``backend/puzzle_manager/adapters/{ID}/`` package and appends a stub
entry to ``sources.json``. Tests use ``--adapters-dir`` (hidden flag) to
point the writer at a tmp directory so we never mutate the real package.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.puzzle_manager.cli import cmd_adapter_scaffold


def _seed_cfg(tmp_path: Path) -> Path:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "sources.json").write_text(
        json.dumps({
            "active_adapter": "src-a",
            "sources": [{
                "id": "src-a", "name": "A", "adapter": "local",
                "config": {"path": "data/a"},
            }],
        }),
        encoding="utf-8",
    )
    return cfg


def _ns(*, cfg: Path, adapters_dir: Path, **kw) -> argparse.Namespace:
    base = {
        "config": str(cfg),
        "adapters_dir": str(adapters_dir),
        "json": True,
        "force": True,
        "kind": "local",
        "new_id": "scratch_one",
        "new_name": None,
        "new_path": None,
        "dry_run": False,
    }
    base.update(kw)
    return argparse.Namespace(**base)


class TestAdapterScaffold:
    def test_invalid_id_rejected(self, tmp_path: Path, capsys) -> None:
        cfg = _seed_cfg(tmp_path)
        adapters = tmp_path / "adapters"
        adapters.mkdir()
        rc = cmd_adapter_scaffold(_ns(cfg=cfg, adapters_dir=adapters,
                                       new_id="Has Spaces"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is False
        assert any(e["code"] == "invalid-id" for e in out["errors"])

    def test_dry_run_does_not_write(self, tmp_path: Path, capsys) -> None:
        cfg = _seed_cfg(tmp_path)
        adapters = tmp_path / "adapters"
        adapters.mkdir()
        before = (cfg / "sources.json").read_text(encoding="utf-8")
        rc = cmd_adapter_scaffold(_ns(cfg=cfg, adapters_dir=adapters,
                                       new_id="my-new-src", dry_run=True))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["dry_run"] is True
        assert out["sources_entry"]["id"] == "my-new-src"
        assert len(out["files_created"]) == 2
        assert not (adapters / "my-new-src").exists()
        assert (cfg / "sources.json").read_text(encoding="utf-8") == before

    def test_apply_writes_package_and_sources(self, tmp_path: Path) -> None:
        cfg = _seed_cfg(tmp_path)
        adapters = tmp_path / "adapters"
        adapters.mkdir()
        rc = cmd_adapter_scaffold(_ns(cfg=cfg, adapters_dir=adapters,
                                       new_id="my-new-src",
                                       new_name="My New Src",
                                       new_path="data/my-new-src"))
        assert rc == 0
        pkg = adapters / "my-new-src"
        assert (pkg / "__init__.py").exists()
        adapter_py = (pkg / "adapter.py").read_text(encoding="utf-8")
        assert '@register_adapter("my-new-src")' in adapter_py
        assert "class MyNewSrcAdapter(LocalAdapter)" in adapter_py
        doc = json.loads((cfg / "sources.json").read_text(encoding="utf-8"))
        ids = [s["id"] for s in doc["sources"]]
        assert "my-new-src" in ids
        new_entry = next(s for s in doc["sources"] if s["id"] == "my-new-src")
        assert new_entry["adapter"] == "my-new-src"
        assert new_entry["name"] == "My New Src"
        assert new_entry["config"]["path"] == "data/my-new-src"

    def test_pkg_collision_refused(self, tmp_path: Path, capsys) -> None:
        cfg = _seed_cfg(tmp_path)
        adapters = tmp_path / "adapters"
        adapters.mkdir()
        (adapters / "already-here").mkdir()
        rc = cmd_adapter_scaffold(_ns(cfg=cfg, adapters_dir=adapters,
                                       new_id="already-here"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any(e["code"] == "pkg-exists" for e in out["errors"])

    def test_registered_id_collision_refused(self, tmp_path: Path, capsys) -> None:
        # `local` is one of the built-in registered adapters.
        cfg = _seed_cfg(tmp_path)
        adapters = tmp_path / "adapters"
        adapters.mkdir()
        rc = cmd_adapter_scaffold(_ns(cfg=cfg, adapters_dir=adapters,
                                       new_id="local"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any(e["code"] == "id-collision" for e in out["errors"])
