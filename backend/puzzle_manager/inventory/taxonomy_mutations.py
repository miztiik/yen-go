"""Theme 11 apply path: writer functions for tag/level taxonomy mutations.

Each writer rewrites the relevant SGF root property (`YT[...]` for tags,
`YG[...]` for levels) across every published SGF, then atomically rewrites
the affected config JSON. Caller (cli.py) wraps the call with a
`PipelineLock` and emits an `audit.jsonl` row.

The regex-based property rewrite is safe because:
- `YT[]` and `YG[]` are root-level SGF properties whose values are
  comma-separated slugs / a single slug, with no nested ']'.
- Move-level `C[]` comments may contain `]` but never reach a node-root
  property regex because we only rewrite the first match (the SGF root
  node carries YT/YG; later nodes do not).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from backend.puzzle_manager.core.atomic_write import atomic_write_json
from backend.puzzle_manager.paths import get_project_root, get_sgf_output_dir

logger = logging.getLogger("puzzle_manager.inventory.taxonomy_mutations")

_YT_RE = re.compile(r"YT\[([^\]]*)\]")
_YG_RE = re.compile(r"YG\[([^\]]*)\]")


@dataclass
class TaxonomyApplyResult:
    """Outcome of a Theme 11 apply pass."""

    op: str
    sources: list[str]
    target: str
    files_scanned: int
    files_rewritten: int
    config_updated: bool


def _iter_sgf_files(root: Path | None = None) -> list[Path]:
    base = root or get_sgf_output_dir()
    if not base.exists():
        return []
    return sorted(base.rglob("*.sgf"))


def _rewrite_yt(content: str, mapping: dict[str, str]) -> tuple[str, bool]:
    """Apply tag rename/merge to a single SGF's root YT[]. Returns (new_content, changed).

    `mapping` keys are old slugs, values are replacement slugs (target). Any
    tag mapped to its own value is unchanged. Duplicate tags after rewrite
    are deduplicated. Tag list is re-sorted to match the canonical SGF
    convention (`YT[a,b,c]`).
    """
    match = _YT_RE.search(content)
    if not match:
        return content, False
    raw = match.group(1)
    tags = [t.strip() for t in raw.split(",") if t.strip()]
    if not any(t in mapping for t in tags):
        return content, False
    new_tags: list[str] = []
    for t in tags:
        nt = mapping.get(t, t)
        if nt and nt not in new_tags:
            new_tags.append(nt)
    new_tags.sort()
    if new_tags == sorted(tags):
        return content, False
    new_value = ",".join(new_tags)
    return content[: match.start()] + f"YT[{new_value}]" + content[match.end() :], True


def _rewrite_yg(content: str, old: str, new: str) -> tuple[str, bool]:
    """Replace `YG[old]` with `YG[new]` on the root node. No-op when slug differs."""
    match = _YG_RE.search(content)
    if not match:
        return content, False
    if match.group(1).strip() != old:
        return content, False
    return content[: match.start()] + f"YG[{new}]" + content[match.end() :], True


def _config_path(name: str) -> Path:
    return get_project_root() / "config" / name


def apply_tags_rename(
    old: str, new: str, *, sgf_root: Path | None = None, config_dir: Path | None = None
) -> TaxonomyApplyResult:
    """Rename a tag slug across every published SGF + config/tags.json."""
    files = _iter_sgf_files(sgf_root)
    rewritten = 0
    mapping = {old: new}
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, changed = _rewrite_yt(text, mapping)
        if changed:
            f.write_text(new_text, encoding="utf-8")
            rewritten += 1

    cfg_path = (config_dir / "tags.json") if config_dir else _config_path("tags.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    tags = dict(cfg.get("tags", {}) or {})
    config_updated = False
    if old in tags:
        body = dict(tags.pop(old))
        body["name"] = body.get("name", new)
        tags[new] = body
        cfg["tags"] = tags
        atomic_write_json(cfg_path, cfg)
        config_updated = True

    logger.info(
        "tags-rename apply: %s -> %s, scanned=%d rewritten=%d config_updated=%s",
        old, new, len(files), rewritten, config_updated,
    )
    return TaxonomyApplyResult(
        op="tags-rename", sources=[old], target=new,
        files_scanned=len(files), files_rewritten=rewritten,
        config_updated=config_updated,
    )


def apply_tags_merge(
    sources: list[str], target: str, *,
    sgf_root: Path | None = None, config_dir: Path | None = None,
) -> TaxonomyApplyResult:
    """Merge multiple source tags into a single target across SGFs + config."""
    if len(sources) < 2:
        raise ValueError("merge requires at least two source tags")
    files = _iter_sgf_files(sgf_root)
    mapping = {s: target for s in sources}
    rewritten = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, changed = _rewrite_yt(text, mapping)
        if changed:
            f.write_text(new_text, encoding="utf-8")
            rewritten += 1

    cfg_path = (config_dir / "tags.json") if config_dir else _config_path("tags.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    tags = dict(cfg.get("tags", {}) or {})
    config_updated = False
    if target not in tags:
        for s in sources:
            if s in tags:
                seed = dict(tags[s])
                seed["name"] = seed.get("name", target)
                tags[target] = seed
                config_updated = True
                break
    for s in sources:
        if s != target and s in tags:
            tags.pop(s)
            config_updated = True
    if config_updated:
        cfg["tags"] = tags
        atomic_write_json(cfg_path, cfg)

    logger.info(
        "tags-merge apply: %s -> %s, scanned=%d rewritten=%d config_updated=%s",
        sources, target, len(files), rewritten, config_updated,
    )
    return TaxonomyApplyResult(
        op="tags-merge", sources=list(sources), target=target,
        files_scanned=len(files), files_rewritten=rewritten,
        config_updated=config_updated,
    )


def apply_levels_rename(
    old: str, new: str, *, sgf_root: Path | None = None, config_dir: Path | None = None,
) -> TaxonomyApplyResult:
    """Rename a level slug across every published SGF's `YG[]` + config/puzzle-levels.json."""
    files = _iter_sgf_files(sgf_root)
    rewritten = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, changed = _rewrite_yg(text, old, new)
        if changed:
            f.write_text(new_text, encoding="utf-8")
            rewritten += 1

    cfg_path = (config_dir / "puzzle-levels.json") if config_dir else _config_path(
        "puzzle-levels.json",
    )
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    levels = list(cfg.get("levels", []) or [])
    config_updated = False
    for entry in levels:
        if entry.get("slug") == old:
            entry["slug"] = new
            config_updated = True
            break
    if config_updated:
        cfg["levels"] = levels
        atomic_write_json(cfg_path, cfg)

    logger.info(
        "levels-rename apply: %s -> %s, scanned=%d rewritten=%d config_updated=%s",
        old, new, len(files), rewritten, config_updated,
    )
    return TaxonomyApplyResult(
        op="levels-rename", sources=[old], target=new,
        files_scanned=len(files), files_rewritten=rewritten,
        config_updated=config_updated,
    )
