"""Seed a sample search DB from the real SGF corpus.

Usage::

    python -m backend.puzzle_manager.scripts.seed_sample_db
    python -m backend.puzzle_manager.scripts.seed_sample_db --count 100
    python -m backend.puzzle_manager.scripts.seed_sample_db --output my-sample.db
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from backend.puzzle_manager.core.db_builder import build_search_db
from backend.puzzle_manager.core.db_models import CollectionMeta, PuzzleEntry
from backend.puzzle_manager.paths import rel_path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SGF_DIR = _PROJECT_ROOT / "yengo-puzzle-collections" / "sgf"
_CONFIG_DIR = _PROJECT_ROOT / "config"

_DEFAULT_COUNT = 50
_DEFAULT_OUTPUT = _PROJECT_ROOT / "yengo-puzzle-collections" / "yengo-search-sample.db"

# ── regex patterns for SGF property extraction ──────────────────────────
_RE_GN = re.compile(r"GN\[([^\]]+)\]")
_RE_YG = re.compile(r"YG\[([^\]]+)\]")
_RE_YT = re.compile(r"YT\[([^\]]+)\]")
_RE_YL = re.compile(r"YL\[([^\]]+)\]")
_RE_YQ = re.compile(r"YQ\[([^\]]+)\]")
_RE_YX = re.compile(r"YX\[([^\]]+)\]")


# ── config loaders ──────────────────────────────────────────────────────

def _load_level_map() -> dict[str, int]:
    """Return ``{slug: numeric_id}`` from ``config/puzzle-levels.json``."""
    path = _CONFIG_DIR / "puzzle-levels.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {lv["slug"]: lv["id"] for lv in data["levels"]}
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Could not load puzzle-levels.json: %s", exc)
        return {}


def _load_tag_map() -> dict[str, int]:
    """Return ``{slug: numeric_id}`` from ``config/tags.json``."""
    path = _CONFIG_DIR / "tags.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {slug: tag["id"] for slug, tag in data["tags"].items()}
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Could not load tags.json: %s", exc)
        return {}


def _load_collection_map() -> dict[str, int]:
    """Return ``{slug: numeric_id}`` from ``config/collections.json``."""
    path = _CONFIG_DIR / "collections.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {c["slug"]: c["id"] for c in data["collections"]}
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Could not load collections.json: %s", exc)
        return {}


def _load_collection_meta() -> list[CollectionMeta]:
    """Load all collections as :class:`CollectionMeta` objects."""
    path = _CONFIG_DIR / "collections.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [
            CollectionMeta(
                collection_id=c["id"],
                slug=c["slug"],
                name=c["name"],
                category=c.get("type"),
            )
            for c in data["collections"]
        ]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Could not load collections metadata: %s", exc)
        return []


# ── SGF parsing helpers ─────────────────────────────────────────────────

def _parse_quality(yq_str: str) -> int:
    """Extract ``q`` value from a ``YQ`` string like ``q:2;rc:0;hc:0;ac:1``."""
    match = re.search(r"q:(\d+)", yq_str)
    return int(match.group(1)) if match else 0


def _parse_ac(yq_str: str) -> int:
    """Extract ``ac`` value from a ``YQ`` string like ``q:2;rc:0;hc:0;ac:1``."""
    match = re.search(r"ac:(\d+)", yq_str)
    return int(match.group(1)) if match else 0


def _parse_complexity(yx_str: str) -> tuple[int, int, int, int]:
    """Extract ``(d, r, s, u)`` from a ``YX`` string like ``d:1;r:2;s:19;u:1``."""
    def _val(key: str) -> int:
        m = re.search(rf"{key}:(\d+)", yx_str)
        return int(m.group(1)) if m else 0

    return _val("d"), _val("r"), _val("s"), _val("u")


def _parse_sgf_entry(
    sgf_text: str,
    batch: str,
    level_map: dict[str, int],
    tag_map: dict[str, int],
    collection_map: dict[str, int],
) -> PuzzleEntry | None:
    """Parse a single SGF string into a :class:`PuzzleEntry`, or ``None`` on failure."""
    gn_match = _RE_GN.search(sgf_text)
    if not gn_match:
        return None

    gn_value = gn_match.group(1)
    # content_hash: strip "YENGO-" prefix if present
    content_hash = gn_value.removeprefix("YENGO-")

    # Level
    yg_match = _RE_YG.search(sgf_text)
    level_slug = yg_match.group(1) if yg_match else ""
    level_id = level_map.get(level_slug, 0)

    # Tags
    yt_match = _RE_YT.search(sgf_text)
    tag_ids: list[int] = []
    if yt_match:
        for slug in yt_match.group(1).split(","):
            slug = slug.strip()
            if slug and slug in tag_map:
                tag_ids.append(tag_map[slug])

    # Collections
    yl_match = _RE_YL.search(sgf_text)
    collection_ids: list[int] = []
    if yl_match:
        for slug in yl_match.group(1).split(","):
            slug = slug.strip()
            if slug and slug in collection_map:
                collection_ids.append(collection_map[slug])

    # Quality
    yq_match = _RE_YQ.search(sgf_text)
    yq_raw = yq_match.group(1) if yq_match else ""
    quality = _parse_quality(yq_raw) if yq_raw else 0
    ac = _parse_ac(yq_raw) if yq_raw else 0

    # Complexity
    yx_match = _RE_YX.search(sgf_text)
    cx_d, cx_r, cx_s, cx_u = _parse_complexity(yx_match.group(1)) if yx_match else (0, 0, 0, 0)

    return PuzzleEntry(
        content_hash=content_hash,
        batch=batch,
        level_id=level_id,
        quality=quality,
        ac=ac,
        tag_ids=tag_ids,
        collection_ids=collection_ids,
        cx_depth=cx_d,
        cx_refutations=cx_r,
        cx_solution_len=cx_s,
        cx_unique_resp=cx_u,
    )


# ── main ────────────────────────────────────────────────────────────────

def _collect_sgf_files(sgf_dir: Path, count: int) -> list[Path]:
    """Walk *sgf_dir*, return up to *count* ``.sgf`` files sorted by path."""
    if not sgf_dir.is_dir():
        logger.error("SGF directory not found: %s", rel_path(sgf_dir))
        return []

    files = sorted(sgf_dir.rglob("*.sgf"))
    logger.info("Found %d SGF files, selecting first %d", len(files), count)
    return files[:count]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Seed a sample search DB from the SGF corpus",
    )
    parser.add_argument(
        "--output", type=Path, default=_DEFAULT_OUTPUT,
        help=f"Output .db path (default: {_DEFAULT_OUTPUT.name})",
    )
    parser.add_argument(
        "--count", type=int, default=_DEFAULT_COUNT,
        help=f"Number of puzzles to include (default: {_DEFAULT_COUNT})",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Load config lookup maps
    level_map = _load_level_map()
    tag_map = _load_tag_map()
    collection_map = _load_collection_map()
    collections_meta = _load_collection_meta()

    logger.info("Config loaded: %d levels, %d tags, %d collections",
                len(level_map), len(tag_map), len(collection_map))

    # Collect SGF files
    sgf_files = _collect_sgf_files(_SGF_DIR, args.count)
    if not sgf_files:
        logger.error("No SGF files found — aborting")
        sys.exit(1)

    # Parse entries
    entries: list[PuzzleEntry] = []
    skipped = 0
    for sgf_path in sgf_files:
        text = sgf_path.read_text(encoding="utf-8", errors="replace")
        # Batch is the parent directory name (e.g. "0001")
        batch = sgf_path.parent.name
        entry = _parse_sgf_entry(text, batch, level_map, tag_map, collection_map)
        if entry:
            entries.append(entry)
        else:
            skipped += 1
            logger.debug("Skipped (no GN): %s", sgf_path.name)

    if not entries:
        logger.error("No valid puzzle entries parsed — aborting")
        sys.exit(1)

    # Build DB
    output_path = args.output.resolve()
    version_info = build_search_db(
        entries, collections_meta, output_path,
    )

    # Write db-version.json alongside the DB
    version_path = output_path.parent / "db-version.json"
    version_path.write_text(
        json.dumps(version_info.to_dict(), indent=4) + "\n",
        encoding="utf-8",
    )

    # Final summary (print, not log — user-facing)
    print(f"\n{'='*50}")
    print(f"Sample DB created: {output_path}")
    print(f"  Puzzles: {version_info.puzzle_count}")
    print(f"  Skipped: {skipped}")
    print(f"  Version: {version_info.db_version}")
    print(f"  db-version.json: {version_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
