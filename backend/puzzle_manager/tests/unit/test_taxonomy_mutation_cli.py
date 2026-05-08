"""Unit tests for ``tags rename`` / ``tags merge`` / ``levels rename`` (Theme 11).

Preview path: every dispatch returns a ``TaxonomyMutationPreview`` and rc=0
(valid) or rc=2 (invalid). Apply path (Theme 11 sub-slice 4a): writer
functions rewrite SGFs + config under a temp tree and return a
``TaxonomyApplyResult``. The CLI's apply branch is wrapped at integration
level by ``test_taxonomy_mutation_apply_cli`` (server slice).
"""

from __future__ import annotations

import argparse
import json

import pytest

from backend.puzzle_manager.cli import (
    _cmd_levels_rename_preview,
    _cmd_tags_merge_preview,
    _cmd_tags_rename_preview,
)


def _ns(**kw) -> argparse.Namespace:
    kw.setdefault("dry_run", True)
    kw.setdefault("apply", False)
    kw.setdefault("json", True)
    return argparse.Namespace(**kw)


class TestTagsRenamePreview:
    def test_unknown_source_returns_invalid(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_rename_preview(_ns(old="nonexistent-tag-xyz", new="new-tag-abc"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is False
        assert any("unknown tag" in e for e in out["errors"])
        assert out["op"] == "tags-rename"

    def test_invalid_slug_rejected(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_rename_preview(_ns(old="life-and-death", new="Has Spaces!"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any("invalid target slug" in e for e in out["errors"])

    def test_dry_run_or_apply_required(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_rename_preview(_ns(
            old="life-and-death", new="lnd-v2", dry_run=False, apply=False,
        ))
        assert rc == 2
        err = capsys.readouterr().err
        assert "dry-run" in err and "apply" in err

    def test_valid_rename_passes(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_rename_preview(_ns(old="life-and-death", new="lnd-renamed-xyz"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert out["sources"] == ["life-and-death"]
        assert out["target"] == "lnd-renamed-xyz"
        assert out["config_changes"]["rename_key"] == {"life-and-death": "lnd-renamed-xyz"}


class TestTagsMergePreview:
    def test_requires_two_sources(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_merge_preview(_ns(sources=["life-and-death"], target="merged-xyz"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any("at least two" in e for e in out["errors"])

    def test_target_cannot_be_a_source(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_merge_preview(_ns(
            sources=["life-and-death", "ko"], target="ko",
        ))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any("cannot also be a source" in e for e in out["errors"])

    def test_valid_merge_aggregates_count(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_tags_merge_preview(_ns(
            sources=["life-and-death", "ko"], target="merged-xyz",
        ))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert set(out["sources"]) == {"life-and-death", "ko"}
        assert out["target"] == "merged-xyz"
        assert isinstance(out["affected_puzzle_count"], int)


class TestLevelsRenamePreview:
    def test_unknown_level_returns_invalid(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_levels_rename_preview(_ns(old="not-a-level-xyz", new="new-level"))
        assert rc == 2
        out = json.loads(capsys.readouterr().out)
        assert any("unknown level" in e for e in out["errors"])

    def test_valid_rename_passes(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = _cmd_levels_rename_preview(_ns(old="elementary", new="elementary-renamed"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert out["sources"] == ["elementary"]
        assert out["op"] == "levels-rename"
