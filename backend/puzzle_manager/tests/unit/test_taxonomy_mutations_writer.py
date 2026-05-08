"""Unit tests for the Theme 11 apply-path writer functions.

These exercise ``apply_tags_rename`` / ``apply_tags_merge`` /
``apply_levels_rename`` against a synthetic SGF tree under ``tmp_path``,
asserting that:

- Only the affected SGF root property (``YT[]`` / ``YG[]``) is rewritten.
- Comments (``C[]``) and unrelated root properties are untouched.
- The relevant config JSON is rewritten atomically.
- Writers are no-ops on SGFs that don't contain the affected slug.

The CLI's lock + audit wrapping is covered separately by
``test_taxonomy_mutation_cli`` (preview path) and the server route tests
in sub-slice 4c.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.taxonomy_mutations import (
    TaxonomyApplyResult,
    apply_levels_rename,
    apply_tags_merge,
    apply_tags_rename,
)


def _write_sgf(path: Path, *, yt: str | None = None, yg: str | None = None,
               extra: str = "") -> None:
    parts = ["(;FF[4]GM[1]SZ[19]"]
    if yt is not None:
        parts.append(f"YT[{yt}]")
    if yg is not None:
        parts.append(f"YG[{yg}]")
    parts.append(extra)
    parts.append(";B[aa]C[note: tag could be life-and-death])")
    path.write_text("".join(parts), encoding="utf-8")


def _write_tags_config(config_dir: Path, slugs: list[str]) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg = {"tags": {s: {"name": s, "category": "shape"} for s in slugs}}
    (config_dir / "tags.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _write_levels_config(config_dir: Path, slugs: list[str]) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg = {"levels": [{"slug": s, "id": 100 + i, "name": s.title()}
                      for i, s in enumerate(slugs)]}
    (config_dir / "puzzle-levels.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")


class TestApplyTagsRename:
    def test_rewrites_yt_and_config(self, tmp_path: Path) -> None:
        sgf_root = tmp_path / "sgf"
        config_dir = tmp_path / "config"
        (sgf_root / "0001").mkdir(parents=True)
        _write_sgf(sgf_root / "0001" / "a.sgf", yt="ko,life-and-death,shape")
        _write_sgf(sgf_root / "0001" / "b.sgf", yt="ko")
        _write_tags_config(config_dir, ["ko", "life-and-death", "shape"])

        res: TaxonomyApplyResult = apply_tags_rename(
            "life-and-death", "lnd-v2", sgf_root=sgf_root, config_dir=config_dir,
        )

        assert res.files_scanned == 2
        assert res.files_rewritten == 1
        assert res.config_updated is True
        text = (sgf_root / "0001" / "a.sgf").read_text(encoding="utf-8")
        assert "YT[ko,lnd-v2,shape]" in text
        # Comment must be untouched even though it mentions the old slug.
        assert "C[note: tag could be life-and-death]" in text
        unchanged = (sgf_root / "0001" / "b.sgf").read_text(encoding="utf-8")
        assert "YT[ko]" in unchanged

        cfg = json.loads((config_dir / "tags.json").read_text(encoding="utf-8"))
        assert "life-and-death" not in cfg["tags"]
        assert "lnd-v2" in cfg["tags"]

    def test_noop_when_slug_absent(self, tmp_path: Path) -> None:
        sgf_root = tmp_path / "sgf"
        config_dir = tmp_path / "config"
        (sgf_root / "0001").mkdir(parents=True)
        _write_sgf(sgf_root / "0001" / "a.sgf", yt="ko")
        _write_tags_config(config_dir, ["ko"])

        res = apply_tags_rename(
            "missing", "renamed", sgf_root=sgf_root, config_dir=config_dir,
        )
        assert res.files_rewritten == 0
        assert res.config_updated is False


class TestApplyTagsMerge:
    def test_merges_sources_into_target(self, tmp_path: Path) -> None:
        sgf_root = tmp_path / "sgf"
        config_dir = tmp_path / "config"
        (sgf_root / "0001").mkdir(parents=True)
        _write_sgf(sgf_root / "0001" / "a.sgf", yt="ko,life-and-death,shape")
        _write_sgf(sgf_root / "0001" / "b.sgf", yt="ko,life-and-death")
        _write_sgf(sgf_root / "0001" / "c.sgf", yt="endgame")
        _write_tags_config(config_dir, ["ko", "life-and-death", "shape", "endgame"])

        res = apply_tags_merge(
            ["ko", "life-and-death"], "ko-lnd",
            sgf_root=sgf_root, config_dir=config_dir,
        )

        assert res.files_scanned == 3
        assert res.files_rewritten == 2
        a = (sgf_root / "0001" / "a.sgf").read_text(encoding="utf-8")
        assert "YT[ko-lnd,shape]" in a
        b = (sgf_root / "0001" / "b.sgf").read_text(encoding="utf-8")
        assert "YT[ko-lnd]" in b
        c = (sgf_root / "0001" / "c.sgf").read_text(encoding="utf-8")
        assert "YT[endgame]" in c

        cfg = json.loads((config_dir / "tags.json").read_text(encoding="utf-8"))
        assert "ko" not in cfg["tags"]
        assert "life-and-death" not in cfg["tags"]
        assert "ko-lnd" in cfg["tags"]

    def test_requires_two_sources(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            apply_tags_merge(["ko"], "ko-v2", sgf_root=tmp_path, config_dir=tmp_path)


class TestApplyLevelsRename:
    def test_rewrites_yg_and_config(self, tmp_path: Path) -> None:
        sgf_root = tmp_path / "sgf"
        config_dir = tmp_path / "config"
        (sgf_root / "0001").mkdir(parents=True)
        _write_sgf(sgf_root / "0001" / "a.sgf", yg="elementary")
        _write_sgf(sgf_root / "0001" / "b.sgf", yg="beginner")
        _write_levels_config(config_dir, ["beginner", "elementary", "intermediate"])

        res = apply_levels_rename(
            "elementary", "elem-v2", sgf_root=sgf_root, config_dir=config_dir,
        )

        assert res.files_scanned == 2
        assert res.files_rewritten == 1
        assert res.config_updated is True
        a = (sgf_root / "0001" / "a.sgf").read_text(encoding="utf-8")
        assert "YG[elem-v2]" in a
        b = (sgf_root / "0001" / "b.sgf").read_text(encoding="utf-8")
        assert "YG[beginner]" in b

        cfg = json.loads((config_dir / "puzzle-levels.json").read_text(encoding="utf-8"))
        slugs = [e["slug"] for e in cfg["levels"]]
        assert "elementary" not in slugs
        assert "elem-v2" in slugs
