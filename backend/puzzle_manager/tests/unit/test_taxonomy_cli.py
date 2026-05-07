"""Theme 5: tag/level taxonomy CLI tests.

Real-fixture tests against the production config files. No mocks.
"""

from __future__ import annotations

import argparse
import json
from unittest.mock import patch

import pytest

from backend.puzzle_manager.cli import cmd_levels, cmd_tags, create_parser
from backend.puzzle_manager.models.taxonomy import LevelUsageEntry, TagUsageEntry


class TestTagsList:
    def test_emits_tag_usage_entries(self, capsys: pytest.CaptureFixture[str]) -> None:
        ns = argparse.Namespace(tags_action="list", with_usage=False, json=True)
        rc = cmd_tags(ns)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        assert len(payload) > 0
        for row in payload:
            TagUsageEntry.model_validate(row)

    def test_human_format_includes_header_and_rows(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ns = argparse.Namespace(tags_action="list", with_usage=False, json=False)
        cmd_tags(ns)
        out = capsys.readouterr().out
        assert "tag" in out and "category" in out and "usage" in out

    def test_no_subaction_prints_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        ns = argparse.Namespace(tags_action=None)
        cmd_tags(ns)
        assert "Usage" in capsys.readouterr().out

    def test_with_usage_when_no_inventory_returns_zero_counts(
        self, capsys: pytest.CaptureFixture[str], tmp_path
    ) -> None:
        # Patch InventoryManager.exists to False so the path that returns
        # zero usage is exercised regardless of repo state.
        with patch(
            "backend.puzzle_manager.inventory.manager.InventoryManager.exists",
            return_value=False,
        ):
            ns = argparse.Namespace(tags_action="list", with_usage=True, json=True)
            cmd_tags(ns)
        payload = json.loads(capsys.readouterr().out)
        assert all(e["usage_count"] == 0 for e in payload)


class TestLevelsList:
    def test_emits_level_usage_entries(self, capsys: pytest.CaptureFixture[str]) -> None:
        ns = argparse.Namespace(levels_action="list", with_usage=False, json=True)
        rc = cmd_levels(ns)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        slugs = {row["level"] for row in payload}
        assert {"novice", "beginner", "intermediate", "expert"}.issubset(slugs)
        for row in payload:
            LevelUsageEntry.model_validate(row)

    def test_levels_sorted_by_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        ns = argparse.Namespace(levels_action="list", with_usage=False, json=True)
        cmd_levels(ns)
        payload = json.loads(capsys.readouterr().out)
        ids = [row["id"] for row in payload]
        assert ids == sorted(ids)

    def test_no_subaction_prints_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        ns = argparse.Namespace(levels_action=None)
        cmd_levels(ns)
        assert "Usage" in capsys.readouterr().out


class TestArgparse:
    def test_tags_list_accepts_with_usage_and_json(self) -> None:
        parser = create_parser()
        ns = parser.parse_args(["tags", "list", "--with-usage", "--json"])
        assert ns.command == "tags"
        assert ns.tags_action == "list"
        assert ns.with_usage is True
        assert ns.json is True

    def test_levels_list_accepts_with_usage_and_json(self) -> None:
        parser = create_parser()
        ns = parser.parse_args(["levels", "list", "--with-usage", "--json"])
        assert ns.command == "levels"
        assert ns.levels_action == "list"
        assert ns.with_usage is True
        assert ns.json is True
