"""Unit tests for ``cmd_adapter_config`` (Theme 7a — read-only slice)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import (
    _adapter_schema_for_kind,
    _build_adapter_source_entries,
    cmd_adapter_config,
    create_parser,
)


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
def cfg_two_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Two local sources: one with an existing path, one missing."""
    real_dir = tmp_path / "data" / "good"
    real_dir.mkdir(parents=True)
    cfg_dir = _write_sources_json(
        tmp_path,
        sources=[
            {
                "id": "good-src",
                "name": "Good Source",
                "adapter": "local",
                "config": {"path": str(real_dir)},
            },
            {
                "id": "bad-src",
                "name": "Missing Source",
                "adapter": "local",
                "config": {"path": str(tmp_path / "data" / "missing")},
            },
        ],
        active="good-src",
    )
    return cfg_dir, real_dir, tmp_path / "data" / "missing"


class TestArgparse:
    def test_subcommands_register(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["adapter-config", "list", "--json"])
        assert args.command == "adapter-config"
        assert args.adapter_config_action == "list"
        assert args.json is True

    def test_show_takes_positional(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["adapter-config", "show", "src-1", "--json"])
        assert args.source_id == "src-1"


class TestList:
    def test_emits_active_marker_and_path_exists(
        self, cfg_two_sources: tuple[Path, Path, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cfg_dir, _, _ = cfg_two_sources
        ns = argparse.Namespace(
            command="adapter-config",
            adapter_config_action="list",
            json=True,
            config=cfg_dir,
        )
        rc = cmd_adapter_config(ns)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["active_adapter"] == "good-src"
        ids = {s["id"]: s for s in payload["sources"]}
        assert ids["good-src"]["active"] is True
        assert ids["good-src"]["path_exists"] is True
        assert ids["bad-src"]["active"] is False
        assert ids["bad-src"]["path_exists"] is False


class TestShow:
    def test_known_source_returns_schema_and_kinds(
        self, cfg_two_sources: tuple[Path, Path, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cfg_dir, _, _ = cfg_two_sources
        ns = argparse.Namespace(
            command="adapter-config",
            adapter_config_action="show",
            source_id="good-src",
            json=True,
            config=cfg_dir,
        )
        rc = cmd_adapter_config(ns)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["source"]["id"] == "good-src"
        assert payload["adapter_kind"] == "local"
        assert isinstance(payload["available_kinds"], list)
        assert "local" in payload["available_kinds"]
        # local has a per-kind schema fragment
        assert payload["schema_for_kind"] is not None
        assert "path" in payload["schema_for_kind"].get("properties", {})

    def test_unknown_source_returns_2(
        self, cfg_two_sources: tuple[Path, Path, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cfg_dir, _, _ = cfg_two_sources
        ns = argparse.Namespace(
            command="adapter-config",
            adapter_config_action="show",
            source_id="nope",
            json=True,
            config=cfg_dir,
        )
        rc = cmd_adapter_config(ns)
        assert rc == 2


class TestValidateAll:
    def test_path_missing_flagged(
        self, cfg_two_sources: tuple[Path, Path, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cfg_dir, _, _ = cfg_two_sources
        ns = argparse.Namespace(
            command="adapter-config",
            adapter_config_action="validate-all",
            json=True,
            config=cfg_dir,
        )
        rc = cmd_adapter_config(ns)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False
        rows_by_id = {r["id"]: r for r in payload["rows"]}
        assert rows_by_id["good-src"]["ok"] is True
        assert rows_by_id["bad-src"]["ok"] is False
        codes = [e["code"] for e in rows_by_id["bad-src"]["errors"]]
        assert "path-missing" in codes


class TestHelpers:
    def test_schema_lookup_local_returns_LocalConfig(self) -> None:
        schema, kinds = _adapter_schema_for_kind("local")
        assert schema is not None
        assert "path" in schema.get("properties", {})
        assert "local" in kinds

    def test_schema_lookup_unknown_kind_returns_none(self) -> None:
        schema, kinds = _adapter_schema_for_kind("definitely-not-a-real-kind")
        assert schema is None
        assert isinstance(kinds, list)

    def test_build_entries_marks_active_and_path(
        self, cfg_two_sources: tuple[Path, Path, Path],
    ) -> None:
        cfg_dir, _, _ = cfg_two_sources
        from backend.puzzle_manager.config.loader import ConfigLoader
        loader = ConfigLoader(cfg_dir)
        sources = loader.load_sources()
        rows = _build_adapter_source_entries(sources, active_id="good-src")
        by_id = {r["id"]: r for r in rows}
        assert by_id["good-src"]["active"] is True
        assert by_id["good-src"]["path_exists"] is True
        assert by_id["bad-src"]["path_exists"] is False
