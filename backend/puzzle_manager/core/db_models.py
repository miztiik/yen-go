from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.puzzle_manager.core.id_maps import IdMaps


@dataclass
class PuzzleEntry:
    """A puzzle row from the ``puzzles`` table plus resolved tag/collection IDs."""

    content_hash: str
    batch: str
    level_id: int
    quality: int = 0
    content_type: int = 2
    cx_depth: int = 0
    cx_refutations: int = 0
    cx_solution_len: int = 0
    cx_unique_resp: int = 0
    ac: int = 0
    source: str = ""
    tag_ids: list[int] = field(default_factory=list)
    collection_ids: list[int] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)

    @property
    def puzzle_id(self) -> str:
        return self.content_hash

    @property
    def compact_path(self) -> str:
        return f"{self.batch}/{self.content_hash}"


@dataclass
class CollectionMeta:
    """A row from the ``collections`` table."""

    collection_id: int
    slug: str
    name: str
    category: str | None = None
    puzzle_count: int = 0
    attrs: dict = field(default_factory=dict)


@dataclass
class DbVersionInfo:
    """Metadata written to ``db-version.json`` alongside the database file."""

    db_version: str
    puzzle_count: int
    generated_at: str
    schema_version: int = 2

    def to_dict(self) -> dict:
        return {
            "db_version": self.db_version,
            "puzzle_count": self.puzzle_count,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
        }


def generate_db_version(content_hashes: list[str] | None = None) -> str:
    """Generate a deterministic DB version ID in ``YYYYMMDD-{8hex}`` format.

    When *content_hashes* is supplied the hex part is derived from
    ``SHA-256(sorted hashes)`` so that identical puzzle sets produce
    identical versions (Charter C2: deterministic builds).

    Falls back to a date-only hash when no hashes are given.

    Example: ``'20260313-a1b2c3d4'``
    """
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    if content_hashes:
        digest = hashlib.sha256("\n".join(sorted(content_hashes)).encode()).hexdigest()[:8]
    else:
        digest = hashlib.sha256(date_part.encode()).hexdigest()[:8]
    return f"{date_part}-{digest}"


def sgf_to_puzzle_entry(
    sgf_content: str,
    content_hash: str,
    id_maps: IdMaps,
    output_root: Path | None = None,
    *,
    batch_hint: str | None = None,
    source: str = "",
) -> PuzzleEntry | None:
    """Convert an SGF content string to a PuzzleEntry for DB-1.

    Re-parses the SGF to extract level, tags, collections, and complexity
    metadata. Returns None if parsing fails or level cannot be resolved.

    Args:
        sgf_content: Raw SGF string.
        content_hash: The puzzle's content hash (filename stem).
        id_maps: Loaded IdMaps for numeric ID resolution.
        output_root: Output directory for batch lookup. If None, batch defaults to "0001".
        batch_hint: Pre-resolved batch from DB-2. Skips filesystem scan when provided.

    Returns:
        PuzzleEntry or None if metadata cannot be resolved.
    """
    from backend.puzzle_manager.core.classifier import get_level_name
    from backend.puzzle_manager.core.id_maps import parse_yx
    from backend.puzzle_manager.core.quality import parse_ac_level, parse_quality_level
    from backend.puzzle_manager.core.sgf_parser import parse_sgf

    try:
        game = parse_sgf(sgf_content)
    except Exception:
        return None

    level = game.yengo_props.level or 1
    level_name = get_level_name(level)
    level_id = id_maps.level_slug_to_id_safe(level_name)
    if level_id is None:
        return None

    tag_ids = sorted(
        id_maps.tag_slug_to_id(t)
        for t in (game.yengo_props.tags or [])
        if id_maps.tag_slug_to_id_safe(t) is not None
    )
    collection_ids = sorted(
        id_maps.collection_slug_to_id(c)
        for c in (game.yengo_props.collections or [])
        if id_maps.collection_slug_to_id_safe(c) is not None
    )
    complexity = parse_yx(game.yengo_props.complexity)
    quality_level = parse_quality_level(game.yengo_props.quality) or 0
    ac_level = parse_ac_level(game.yengo_props.quality)

    # Determine batch: prefer batch_hint (from DB-2), then filesystem scan
    batch = "0001"
    if batch_hint:
        batch = batch_hint
    elif output_root is not None:
        sgf_dir = output_root / "sgf"
        if sgf_dir.exists():
            for batch_dir in sgf_dir.iterdir():
                if batch_dir.is_dir() and (batch_dir / f"{content_hash}.sgf").exists():
                    batch = batch_dir.name
                    break

    # Read content_type from YM pipeline metadata (RC-3: wire ct to DB-1)
    from backend.puzzle_manager.core.content_classifier import get_content_type_id
    from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta_extended
    meta = parse_pipeline_meta_extended(game.yengo_props.pipeline_meta)
    content_type = meta.content_type if meta.content_type is not None else get_content_type_id("practice")

    return PuzzleEntry(
        content_hash=content_hash,
        batch=batch,
        level_id=level_id,
        quality=quality_level,
        content_type=content_type,
        ac=ac_level,
        source=source,
        tag_ids=tag_ids,
        collection_ids=collection_ids,
        cx_depth=complexity[0],
        cx_refutations=complexity[1],
        cx_solution_len=complexity[2],
        cx_unique_resp=complexity[3],
    )
