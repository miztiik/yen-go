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
from tools.core.sgf_types import Color, Point
from tools.core.text_cleaner import strip_cjk

from tools.senseis_enrichment.config import SenseisConfig
from tools.senseis_enrichment.html_parser import strip_commentary_attributions
from tools.senseis_enrichment.models import (
    MatchResult,
    SenseisPageData,
    SenseisSolutionData,
)
from tools.senseis_enrichment.diagram_tools import (
    find_matching_branch,
    parse_diagram_sgf,
    resolve_label_references,
    ALL_MARKER_PROPERTIES,
    _POINT_MARKERS,
    _COMPOSED_MARKERS,
)
from tools.senseis_enrichment.position_matcher import transform_point

logger = logging.getLogger("senseis_enrichment.merger")

# Senseis difficulty terms -> puzzle-levels.json slugs
_SENSEIS_DIFFICULTY_TO_SLUG: dict[str, str] = {
    "beginner": "beginner",          # 25k-21k
    "elementary": "elementary",      # 20k-16k
    "intermediate": "intermediate",  # 15k-11k
    "advanced": "advanced",          # 5k-1k
    "expert": "expert",              # 7d-9d
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

    In download mode (source dir doesn't exist), creates an empty enriched
    directory instead of copying.

    Returns path to the enriched directory.
    """
    source_dir = config.enriched_dir().parent / config.enriched_dir().name.replace(
        config.enriched_dir_suffix, ""
    )
    enriched = config.enriched_dir()

    if not enriched.exists():
        if source_dir.exists():
            logger.info("Copying %s -> %s", source_dir, enriched)
            shutil.copytree(source_dir, enriched)
            logger.info("Copied %d files", sum(1 for _ in enriched.glob("*.sgf")))
        else:
            # Download mode: no source dir to copy, create empty enriched dir
            logger.info("Creating enriched directory (download mode): %s", enriched)
            enriched.mkdir(parents=True, exist_ok=True)
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

    # Preserve existing comment if any, deduplicating paragraphs
    # (some source files have the same paragraph repeated)
    if existing_comment:
        normalized = existing_comment.replace("\r\n", "\n").replace("\r", "\n")
        seen: set[str] = set()
        for para in normalized.split("\n"):
            stripped = para.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                parts.append(stripped)

    return "\n".join(parts)


def _attach_markers(
    node: SgfNode,
    markers: dict[str, set[str]],
    transform: "PositionTransform | None",
    board_size: int,
) -> None:
    """Set visual markup properties on a node, transforming coordinates."""
    for prop, values in markers.items():
        if not values:
            continue
        transformed: list[str] = []
        if prop in _POINT_MARKERS:
            for sgf_coord in sorted(values):
                if transform:
                    p = Point.from_sgf(sgf_coord)
                    p = transform_point(p, board_size, transform)
                    transformed.append(p.to_sgf())
                else:
                    transformed.append(sgf_coord)
        elif prop in _COMPOSED_MARKERS:
            for pair in sorted(values):
                if ":" in pair:
                    c1, c2 = pair.split(":", 1)
                    if transform:
                        p1 = Point.from_sgf(c1.strip())
                        p1 = transform_point(p1, board_size, transform)
                        p2 = Point.from_sgf(c2.strip())
                        p2 = transform_point(p2, board_size, transform)
                        transformed.append(f"{p1.to_sgf()}:{p2.to_sgf()}")
                    else:
                        transformed.append(pair)
        if transformed:
            node.properties[prop] = ",".join(transformed)


def _attach_labels(
    node: SgfNode,
    labels: dict[str, str],
    transform: "PositionTransform | None",
    board_size: int,
) -> None:
    """Set LB[] property on a node, transforming coordinates."""
    if not labels:
        return
    pairs: list[str] = []
    for letter, sgf_coord in sorted(labels.items()):
        if transform:
            p = Point.from_sgf(sgf_coord)
            p = transform_point(p, board_size, transform)
            pairs.append(f"{p.to_sgf()}:{letter}")
        else:
            pairs.append(f"{sgf_coord}:{letter}")
    if pairs:
        node.properties["LB"] = ",".join(pairs)


def _attach_diagram_markup(
    node: SgfNode,
    seq: "DiagramMoveSequence",
    transform: "PositionTransform | None",
    board_size: int,
) -> None:
    """Attach visual markers and labels from a diagram to a node."""
    if seq.markers:
        _attach_markers(node, seq.markers, transform, board_size)
    if seq.labels:
        _attach_labels(node, seq.labels, transform, board_size)


def add_solution_commentary(
    tree: SgfTree,
    solution_data: SenseisSolutionData,
    match_result: MatchResult,
) -> None:
    """Add commentary from Senseis diagrams to solution tree nodes.

    For each diagram: parse its move sequence, match against local tree
    branches, and attach commentary to the correct node. When local tree
    lacks moves, build new branches from diagram data.

    Handles three cases:
      1. Full match — commentary attached to existing node
      2. Partial match — remaining moves built as new branch from divergence
      3. No match — entire move sequence built as new branch from root
    """
    if not solution_data.diagrams:
        return

    transform = match_result.transform
    board_size = tree.board_size

    for diagram in solution_data.diagrams:
        # Parse the diagram SGF for moves and labels
        seq = parse_diagram_sgf(diagram.sgf_content)

        # Skip diagrams with neither commentary nor moves
        if not diagram.commentary and not seq.moves:
            continue

        commentary = ""
        if diagram.commentary:
            # Normalize newlines from cached HTML paragraphs to spaces
            commentary = " ".join(diagram.commentary.split("\n"))

            # Strip wiki user attributions (works on cached joined text)
            commentary = strip_commentary_attributions(commentary)

            # Resolve label/move references to board coordinates
            commentary = resolve_label_references(
                commentary, seq.labels, seq.moves, transform, board_size
            )
            commentary = _sanitize_for_sgf(commentary)

        if not seq.moves:
            # No moves in diagram — commentary goes on root node
            if commentary:
                label = diagram.diagram_name or "Note"
                _append_comment(tree.solution_tree, f"({label}) {commentary}")
            continue

        # Find where this diagram's moves match the local tree
        target_node, depth = find_matching_branch(
            tree.solution_tree, seq.moves, transform, board_size
        )

        if target_node is not None and depth == len(seq.moves):
            # Full match — commentary describes this exact line
            if commentary:
                _append_comment(target_node, commentary)
            _attach_diagram_markup(target_node, seq, transform, board_size)
        elif target_node is not None and depth < len(seq.moves):
            # Partial match — build remaining moves as new variation
            leaf = _build_move_branch(
                target_node, seq.moves[depth:], transform, board_size
            )
            if commentary:
                label = diagram.diagram_name or "Variation"
                _append_comment(leaf, f"({label}) {commentary}")
            _attach_diagram_markup(leaf, seq, transform, board_size)
        elif seq.moves:
            # No match at all — build entire sequence as new branch from root
            leaf = _build_move_branch(
                tree.solution_tree, seq.moves, transform, board_size
            )
            if commentary:
                label = diagram.diagram_name or "Note"
                _append_comment(leaf, f"({label}) {commentary}")
            _attach_diagram_markup(leaf, seq, transform, board_size)


def _build_move_branch(
    parent: SgfNode,
    moves: list[tuple[str, str]],
    transform: "PositionTransform | None",
    board_size: int,
) -> SgfNode:
    """Build a branch of move nodes from diagram moves, returning the leaf.

    Reuses existing child nodes where moves match (shared prefix detection),
    only creating new nodes where the diagram diverges from existing branches.
    """
    current = parent
    for color_str, sgf_coord in moves:
        if transform:
            p = Point.from_sgf(sgf_coord)
            p = transform_point(p, board_size, transform)
            local_coord = p.to_sgf()
        else:
            local_coord = sgf_coord

        # Check if this move already exists as a child (shared prefix)
        existing = None
        for child in current.children:
            if (
                child.color
                and child.color.value == color_str
                and child.move
                and child.move.to_sgf() == local_coord
            ):
                existing = child
                break

        if existing:
            current = existing
        else:
            new_node = SgfNode(
                move=Point.from_sgf(local_coord),
                color=Color(color_str),
            )
            current.add_child(new_node)
            current = new_node

    return current


def _append_comment(node: SgfNode, text: str) -> None:
    """Append text to a node's comment, separated by newline."""
    if node.comment:
        node.comment = node.comment + "\n" + text
    else:
        node.comment = text


def _compute_yl(config: SenseisConfig, problem_number: int) -> str:
    """Compute YL[] value: slug or slug:chapter/position if sections exist."""
    slug = config.collection_slug
    if not config.sections:
        return slug

    for s in config.sections:
        s_dict = s if isinstance(s, dict) else vars(s)
        r = s_dict.get("range")
        if not r or len(r) != 2:
            continue
        lo, hi = r
        if lo <= problem_number <= hi:
            chapter = s_dict.get("number", 0)
            pos = problem_number - lo + 1
            return f"{slug}:{chapter}/{pos}"

    # Problem not in any section range — just use slug
    return slug


def merge_problem(
    config: SenseisConfig,
    problem_number: int,
    page_data: SenseisPageData | None,
    solution_data: SenseisSolutionData | None,
    match_result: MatchResult,
    source_path: Path | None = None,
    enriched_path: Path | None = None,
) -> bool:
    """Merge enrichment data into an enriched SGF copy.

    Always reads from the ORIGINAL file and writes to the enriched copy,
    ensuring idempotent re-runs without stacking content.

    Args:
        source_path: Explicit source file path (overrides local_sgf_path).
        enriched_path: Explicit enriched output path (overrides enriched_sgf_path).

    Returns True if the file was successfully enriched.
    """
    original_path = source_path or config.local_sgf_path(problem_number)
    enriched_path = enriched_path or config.enriched_sgf_path(problem_number)
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
    if preamble:
        preamble = strip_commentary_attributions(preamble)
    root_comment = build_root_comment(page_data, tree.root_comment, preamble)

    # Add solution commentary if we have solution data and position match
    if solution_data and solution_data.status == "ok" and match_result.matched:
        add_solution_commentary(tree, solution_data, match_result)

    # Rebuild SGF using the builder
    builder = SGFBuilder.from_tree(tree)

    # Infer PL from first solution move if not already set in original SGF
    if builder.player_to_move is None:
        first_child = tree.solution_tree.children[0] if tree.solution_tree.children else None
        if first_child and first_child.color:
            builder.set_player_to_move(first_child.color)

    # Merge root comment: page metadata + any diagram commentary added to root
    # (diagrams with no moves attach commentary to tree.solution_tree)
    # Deduplicate: diagram commentary often repeats the existing root comment
    root_commentary_from_diagrams = tree.solution_tree.comment
    if root_commentary_from_diagrams:
        # Split into individual notes, only add ones not already present
        existing_norm = root_comment.replace("\r\n", "\n").replace("\r", "\n")
        new_parts: list[str] = []
        for line in root_commentary_from_diagrams.split("\n"):
            stripped = line.strip()
            if stripped and stripped not in existing_norm:
                new_parts.append(stripped)
        if new_parts:
            root_comment = root_comment + "\n" + "\n".join(new_parts)
    builder.root_comment = root_comment

    # Set YG[] difficulty from Senseis mapping
    if page_data and page_data.difficulty:
        slug = _SENSEIS_DIFFICULTY_TO_SLUG.get(page_data.difficulty.lower())
        if slug:
            builder.set_level_slug(slug)

    # Add GN if we have a title (CJK-cleaned), fallback to collection + number
    if page_data and page_data.title_english:
        builder.metadata["GN"] = _clean_cjk(page_data.title_english)
    elif "GN" not in builder.metadata:
        # Fallback: use collection slug + problem number as title
        slug_title = config.collection_slug.replace("-", " ").title()
        builder.metadata["GN"] = f"{slug_title} Problem {problem_number}"

    # Set YL[] collection membership with chapter/position if sections exist
    yl_value = _compute_yl(config, problem_number)
    if yl_value:
        builder.set_collections([yl_value])

    new_sgf = builder.build()

    # Write the enriched file (ensure directory exists)
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_path.write_text(new_sgf, encoding="utf-8")
    logger.info("Enriched: %s", enriched_path.name)
    return True
