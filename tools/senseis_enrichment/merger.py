"""Merge Senseis enrichment data into local SGF copies.

Adds metadata (title, difficulty, instruction) to root comments and
solution commentary to move nodes, with coordinate transformation.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from tools.core.sgf_parser import SgfNode, SgfTree, parse_sgf, read_sgf_file
from tools.core.sgf_builder import SGFBuilder
from tools.core.text_cleaner import strip_cjk

from tools.senseis_enrichment.config import SenseisConfig
from tools.senseis_enrichment.models import (
    MatchResult,
    SenseisPageData,
    SenseisSolutionData,
)
from tools.senseis_enrichment.diagram_tools import (
    find_matching_branch,
    parse_diagram_sgf,
    resolve_label_references,
)
from tools.senseis_enrichment.position_matcher import transform_point

logger = logging.getLogger("senseis_enrichment.merger")

# Senseis difficulty terms -> puzzle-levels.json slugs
_SENSEIS_DIFFICULTY_TO_SLUG: dict[str, str] = {
    "advanced": "advanced",  # 5k-1k
    "expert": "expert",      # 7d-9d
}

# Pattern to collapse empty parens left after CJK stripping
_EMPTY_PARENS_RE = re.compile(r"\s*\(\s*\)")


def _clean_cjk(text: str) -> str:
    """Strip CJK characters from text and clean up empty parentheses."""
    cleaned = strip_cjk(text)
    cleaned = _EMPTY_PARENS_RE.sub("", cleaned)
    return cleaned.strip()


def _sanitize_for_sgf(text: str) -> str:
    """Replace literal brackets in text that would break SGF C[] values.

    Our parser (and many others) mishandle unescaped [ inside property values.
    Replace with full-width equivalents which are visually identical in comments.
    """
    return text.replace("[", "\uff3b").replace("]", "\uff3d")


def prepare_enriched_directory(config: SenseisConfig) -> Path:
    """Copy original directory to enriched sibling (if not already done).

    Returns path to the enriched directory.
    """
    source_dir = config.enriched_dir().parent / config.enriched_dir().name.replace(
        config.enriched_dir_suffix, ""
    )
    enriched = config.enriched_dir()

    if not enriched.exists():
        logger.info("Copying %s -> %s", source_dir, enriched)
        shutil.copytree(source_dir, enriched)
        logger.info("Copied %d files", sum(1 for _ in enriched.glob("*.sgf")))
    else:
        logger.info("Enriched directory already exists: %s", enriched)

    return enriched


def build_root_comment(
    page_data: SenseisPageData | None,
    existing_comment: str = "",
    preamble_text: str = "",
) -> str:
    """Build a structured root comment from Senseis page data."""
    parts: list[str] = []

    if page_data:
        # Title — strip CJK from English title (Senseis sometimes embeds Chinese)
        title_parts = []
        if page_data.title_english:
            title_parts.append(_clean_cjk(page_data.title_english))
        if page_data.title_pinyin:
            title_parts.append(f"({page_data.title_pinyin})")
        if title_parts:
            parts.append(" ".join(title_parts))

        if page_data.instruction:
            parts.append(page_data.instruction)

    if preamble_text:
        parts.append(preamble_text)

    if page_data:
        if page_data.cross_references:
            parts.append("See also: " + "; ".join(page_data.cross_references))

    # Preserve existing comment if any
    if existing_comment:
        parts.append(existing_comment)

    return "\n".join(parts)


def add_solution_commentary(
    tree: SgfTree,
    solution_data: SenseisSolutionData,
    match_result: MatchResult,
) -> None:
    """Add commentary from Senseis diagrams to solution tree nodes.

    For each diagram: parse its move sequence, match against local tree
    branches, and attach commentary to the correct node with label
    coordinates resolved.
    """
    if not solution_data.diagrams:
        return

    transform = match_result.transform
    board_size = tree.board_size

    for diagram in solution_data.diagrams:
        if not diagram.commentary:
            continue

        # Normalize newlines from cached HTML paragraphs to spaces
        commentary = " ".join(diagram.commentary.split("\n"))

        # Parse the diagram SGF for moves and labels
        seq = parse_diagram_sgf(diagram.sgf_content)

        # Resolve label/move references to board coordinates
        resolved = resolve_label_references(
            commentary, seq.labels, seq.moves, transform, board_size
        )
        resolved = _sanitize_for_sgf(resolved)

        # Find where this diagram's moves match the local tree
        target_node, depth = find_matching_branch(
            tree.solution_tree, seq.moves, transform, board_size
        )

        if target_node is None:
            # No moves matched at all — attach to root as fallback
            label = diagram.diagram_name or "Note"
            text = f"({label}) {resolved}"
            if tree.solution_tree.children:
                _append_comment(tree.solution_tree.children[0], text)
            continue

        if depth == len(seq.moves):
            # Full match — commentary describes this exact line
            _append_comment(target_node, resolved)
        else:
            # Partial match — diagram diverges after depth moves.
            # Describe the variation from the divergence point.
            diverge_move_idx = depth  # 0-based index of first non-matching move
            if diverge_move_idx < len(seq.moves):
                color, coord = seq.moves[diverge_move_idx]
                if transform:
                    from tools.core.sgf_types import Point
                    p = Point.from_sgf(coord)
                    p = transform_point(p, board_size, transform)
                    local_coord = p.to_sgf()
                else:
                    local_coord = coord
                if diagram.diagram_name:
                    prefix = f"({diagram.diagram_name})"
                else:
                    prefix = f"(If {local_coord})"
            else:
                prefix = f"({diagram.diagram_name or 'Variation'})"
            _append_comment(target_node, f"{prefix} {resolved}")


def _append_comment(node: SgfNode, text: str) -> None:
    """Append text to a node's comment, separated by newline."""
    if node.comment:
        node.comment = node.comment + "\n" + text
    else:
        node.comment = text


def merge_problem(
    config: SenseisConfig,
    problem_number: int,
    page_data: SenseisPageData | None,
    solution_data: SenseisSolutionData | None,
    match_result: MatchResult,
) -> bool:
    """Merge enrichment data into an enriched SGF copy.

    Always reads from the ORIGINAL file and writes to the enriched copy,
    ensuring idempotent re-runs without stacking content.

    Returns True if the file was successfully enriched.
    """
    original_path = config.local_sgf_path(problem_number)
    enriched_path = config.enriched_sgf_path(problem_number)
    if not original_path.exists():
        logger.warning("Original file not found: %s", original_path)
        return False

    # Always parse from the original (not enriched) to avoid stacking
    content, _encoding = read_sgf_file(original_path)
    try:
        tree = parse_sgf(content)
    except Exception as e:
        logger.error("Failed to parse %s: %s", enriched_path, e)
        return False

    # Build enriched root comment
    preamble = solution_data.preamble_text if solution_data else ""
    root_comment = build_root_comment(page_data, tree.root_comment, preamble)

    # Add solution commentary if we have solution data and position match
    if solution_data and solution_data.status == "ok" and match_result.matched:
        add_solution_commentary(tree, solution_data, match_result)

    # Rebuild SGF using the builder
    builder = SGFBuilder.from_tree(tree)
    builder.root_comment = root_comment

    # Set YG[] difficulty from Senseis mapping
    if page_data and page_data.difficulty:
        slug = _SENSEIS_DIFFICULTY_TO_SLUG.get(page_data.difficulty.lower())
        if slug:
            builder.set_level_slug(slug)

    # Add GN if we have a title (CJK-cleaned)
    if page_data and page_data.title_english:
        builder.metadata["GN"] = _clean_cjk(page_data.title_english)

    new_sgf = builder.build()

    # Write the enriched file (ensure directory exists)
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_path.write_text(new_sgf, encoding="utf-8")
    logger.info("Enriched: %s", enriched_path.name)
    return True
