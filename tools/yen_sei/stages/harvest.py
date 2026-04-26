"""harvest stage: Extract teaching comments from local SGF copies.

Reads from data/sources/ (populated by the ingest stage).
NEVER reads from external-sources/ directly.
Parses each SGF, extracts board setup + all C[] comments into RawExtract records.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tools.core.sgf_parser import parse_sgf, read_sgf_file
from tools.core.text_cleaner import sanitize_for_training
from tools.yen_sei.config import RAW_DIR, RAW_JSONL, SOURCES_DIR
from tools.yen_sei.data_paths import to_posix_rel
from tools.yen_sei.models.raw_extract import RawExtract, SolutionNode
from tools.yen_sei.telemetry.logger import (
    configure_stage_file_logging,
    set_context,
    setup_logger,
)

logger = setup_logger(__name__)


def _extract_nodes(node, nodes: list[SolutionNode]) -> None:
    """Recursively extract solution nodes with comments."""
    if node.move is not None:
        # Point objects convert to SGF coords via str(); raw strings pass through
        move_str = str(node.move) if not isinstance(node.move, str) else node.move
        nodes.append(
            SolutionNode(
                move=move_str,
                color=node.color or "B",
                comment=sanitize_for_training(node.comment),
                is_correct=node.is_correct,
                children_count=len(node.children),
            )
        )
    for child in node.children:
        _extract_nodes(child, nodes)


def _parse_one_sgf(sgf_path: Path, source: str, tier: str) -> RawExtract | None:
    """Parse a single SGF file into a RawExtract."""
    try:
        content, _encoding = read_sgf_file(sgf_path)
        tree = parse_sgf(content)
    except Exception as e:
        logger.debug("Failed to parse %s: %s", sgf_path.name, e)
        return None

    nodes: list[SolutionNode] = []
    if tree.solution_tree:
        _extract_nodes(tree.solution_tree, nodes)

    # Compute setup stones as SGF coordinates
    setup_b = [str(p) if not isinstance(p, str) else p for p in tree.black_stones]
    setup_w = [str(p) if not isinstance(p, str) else p for p in tree.white_stones]

    total_chars = len(sanitize_for_training(tree.root_comment))
    total_chars += sum(len(n.comment) for n in nodes)

    # Extract metadata from YenGo properties if available
    yp = tree.yengo_props
    tags = yp.tags if yp and yp.tags else []
    level = yp.level_slug if yp and yp.level_slug else ""
    collection = ""
    if yp and yp.collections:
        collection = yp.collections[0] if isinstance(yp.collections, list) else str(yp.collections)

    return RawExtract(
        source=source,
        tier=tier,
        file_path=sgf_path.name,
        board_size=tree.board_size,
        player_to_move=tree.player_to_move or "B",
        setup_black=setup_b,
        setup_white=setup_w,
        root_comment=sanitize_for_training(tree.root_comment),
        solution_nodes=nodes,
        tags=tags,
        level=level,
        collection=collection,
        total_comment_chars=total_chars,
    )


def run_harvest(
    output_path: str | None = None,
) -> None:
    """Run the harvest stage. Reads from flat data/sources/ directory."""
    set_context(stage="harvest")
    run_log, latest_log, deleted_logs = configure_stage_file_logging("harvest", logger=logger)
    logger.info(
        "Run logs: %s (latest: %s)",
        to_posix_rel(run_log),
        to_posix_rel(latest_log),
    )
    if deleted_logs:
        logger.info("Run-log cleanup: removed %d old logs", len(deleted_logs))

    output = Path(output_path) if output_path else RAW_JSONL
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Verify ingest has been run
    if not SOURCES_DIR.exists() or not any(SOURCES_DIR.iterdir()):
        logger.error(
            "data/sources/ is empty. Run 'yen-sei ingest' first to copy SGFs from external-sources/."
        )
        return

    sgf_files = sorted(p for p in SOURCES_DIR.glob("*.sgf") if not p.name.startswith("_"))
    logger.info("Harvesting %d SGF files from %s", len(sgf_files), to_posix_rel(SOURCES_DIR))

    total_extracted = 0
    total_skipped = 0
    valid_tiers = {"gold", "silver", "bronze"}

    with output.open("w", encoding="utf-8") as f:
        for i, sgf_path in enumerate(sgf_files):
            # Filename convention: {tier}_{source}_{stem}.sgf
            parts = sgf_path.stem.split("_", 2)
            if len(parts) >= 3 and parts[0] in valid_tiers:
                tier, source_name, _stem = parts[0], parts[1], parts[2]
            else:
                # Legacy fallback (no tier prefix) — treat as bronze
                tier = "bronze"
                source_name = parts[0] if parts else "unknown"

            record = _parse_one_sgf(sgf_path, source_name, tier)
            if record is None:
                total_skipped += 1
                continue

            f.write(record.model_dump_json() + "\n")
            total_extracted += 1

            if (i + 1) % 1000 == 0:
                logger.info("  %d/%d processed", i + 1, len(sgf_files))

    logger.info(
        "Harvest complete: %d extracted, %d skipped → %s",
        total_extracted,
        total_skipped,
        to_posix_rel(output),
    )
