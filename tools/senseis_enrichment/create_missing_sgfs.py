"""Create missing SGFs from Senseis diagram data for unmatched problems.

Reads cached Senseis page data and diagram SGFs to build new puzzle files
for problems that exist on Senseis but have no local equivalent.

Usage:
    python -m tools.senseis_enrichment.create_missing_sgfs --config <config.json> --dry-run
    python -m tools.senseis_enrichment.create_missing_sgfs --config <config.json>
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_types import Color, Point

from tools.senseis_enrichment.config import SenseisConfig, load_config

logger = logging.getLogger("senseis_enrichment.create_missing")


def _load_senseis_hashes(config: SenseisConfig) -> dict:
    # Check _results/ first (new location), fall back to _working/ (legacy)
    path = config.results_dir() / "_senseis_hashes.json"
    if not path.exists():
        path = config.working_dir() / "_senseis_hashes.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_page_cache(config: SenseisConfig, n: int) -> dict | None:
    path = config.page_cache_dir() / f"{n:04d}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_position_mapping(config: SenseisConfig) -> dict:
    # Check _results/ first (new location), fall back to _working/ (legacy)
    path = config.results_dir() / "_position_mapping.json"
    if not path.exists():
        path = config.working_dir() / "_position_mapping.json"
    if not path.exists():
        return {"mappings": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _find_unmatched_globals(config: SenseisConfig) -> list[int]:
    """Find Senseis global numbers that have no local match."""
    mapping = _load_position_mapping(config)
    mapped_globals = {m["senseis_global"] for m in mapping["mappings"]}
    hashes = _load_senseis_hashes(config)
    all_globals = set(int(k) for k in hashes.keys())
    return sorted(all_globals - mapped_globals)


def _parse_player_from_instruction(instruction: str) -> Color | None:
    """Extract player to move from instruction text.

    Returns None if neither color is mentioned.
    """
    lower = instruction.lower()
    if "black" in lower:
        return Color.BLACK
    if "white" in lower:
        return Color.WHITE
    return None


def create_sgf_from_diagram(
    config: SenseisConfig,
    senseis_global: int,
) -> str | None:
    """Create an SGF string from Senseis diagram data.

    Returns the SGF string, or None if diagram data unavailable.
    """
    page_data = _load_page_cache(config, senseis_global)
    if not page_data:
        logger.warning("No page cache for global %d", senseis_global)
        return None

    diagram_url = page_data.get("diagram_sgf_url", "")
    if not diagram_url:
        logger.warning("No diagram URL for global %d", senseis_global)
        return None

    # Load the diagram SGF
    diagram_filename = diagram_url.replace("/", "_")
    diagram_path = config.diagram_cache_dir() / diagram_filename
    if not diagram_path.exists():
        logger.warning("Diagram file missing for global %d: %s", senseis_global, diagram_path)
        return None

    diagram_content = diagram_path.read_text(encoding="utf-8")

    try:
        tree = parse_sgf(diagram_content)
    except Exception as e:
        logger.error("Failed to parse diagram for global %d: %s", senseis_global, e)
        return None

    # Extract stone positions from the parsed tree
    black_stones = list(tree.black_stones)
    white_stones = list(tree.white_stones)

    # Walk diagram moves and include them as setup stones.
    # Senseis problem diagrams often encode a "trigger move" as a B[]/W[] node
    # rather than an AB/AW setup stone.  Solution diagrams treat these stones
    # as part of the initial position (AB/AW), so we must include them here.
    last_move_color: Color | None = None
    node = tree.solution_tree
    while node.children:
        node = node.children[0]
        if node.move and node.color:
            if node.color == Color.BLACK:
                black_stones.append(node.move)
            else:
                white_stones.append(node.move)
            last_move_color = node.color

    if not black_stones and not white_stones:
        logger.warning("No stones in diagram for global %d", senseis_global)
        return None

    # Build new SGF
    builder = SGFBuilder(board_size=config.board_size)
    builder.add_black_stones(black_stones)
    builder.add_white_stones(white_stones)

    # Set player to move: instruction text takes priority, then infer from
    # the last diagram move (opponent's turn after the trigger move).
    instruction = page_data.get("instruction", "")
    if instruction:
        player = _parse_player_from_instruction(instruction)
        if player is not None:
            builder.set_player_to_move(player)
        builder.root_comment = instruction
    elif last_move_color is not None:
        builder.set_player_to_move(
            Color.WHITE if last_move_color == Color.BLACK else Color.BLACK
        )

    # Set difficulty
    difficulty = page_data.get("difficulty", "")
    if difficulty:
        slug = difficulty.lower()
        # Map known Senseis difficulty terms
        slug_map = {
            "beginner": "beginner",
            "elementary": "elementary",
            "intermediate": "intermediate",
            "advanced": "advanced",
            "expert": "expert",
        }
        mapped_slug = slug_map.get(slug)
        if mapped_slug:
            builder.set_level_slug(mapped_slug)

    return builder.build()


def create_missing_sgfs(
    config: SenseisConfig,
    dry_run: bool = False,
) -> dict:
    """Create SGF files for unmatched Senseis problems.

    Returns summary dict.
    """
    hashes = _load_senseis_hashes(config)
    unmatched = _find_unmatched_globals(config)

    # Filter to only globals that have diagram data
    to_create = []
    for g in unmatched:
        entry = hashes.get(str(g), {})
        section_name = entry.get("section_name", "")
        section_pos = entry.get("section_pos", 0)
        to_create.append((g, section_name, section_pos))

    logger.info("Found %d unmatched Senseis globals to process", len(to_create))

    created = 0
    skipped = 0
    failed = 0
    target_dir = config.enriched_dir()

    for g, section_name, section_pos in to_create:
        sgf_content = create_sgf_from_diagram(config, g)
        if sgf_content is None:
            skipped += 1
            continue

        # Generate filename using section-based naming
        clean_section = section_name.replace(" ", "")
        # Determine padding from max count in section
        max_count = max(
            (s.get("count", 0) for s in (config.sections or [])
             if s.get("name", "") == section_name),
            default=99,
        )
        pad = 3 if max_count >= 100 else 2
        filename = f"{clean_section}-{section_pos:0{pad}d}.sgf"

        if dry_run:
            logger.info("  Would create: %s (global %d, %s #%d)", filename, g, section_name, section_pos)
            created += 1
            continue

        out_path = target_dir / filename
        if out_path.exists():
            logger.info("  Already exists: %s", filename)
            skipped += 1
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(sgf_content, encoding="utf-8")
        logger.info("  Created: %s (global %d)", filename, g)
        created += 1

    summary = {"created": created, "skipped": skipped, "failed": failed, "total": len(to_create)}
    logger.info("Done: created=%d, skipped=%d, failed=%d", created, skipped, failed)
    return summary


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    create_missing_sgfs(config, dry_run=args.dry_run)
