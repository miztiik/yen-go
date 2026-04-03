"""
SGF parser for puzzle files.

Parses SGF content into internal representation including YenGo custom properties.
Uses KaTrain's SGF parser internally for robust SGF grammar handling.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.puzzle_manager.core.constants import SLUG_TO_LEVEL
from backend.puzzle_manager.core.katrain_sgf_parser import (
    SGF as KaTrainSGF,
)
from backend.puzzle_manager.core.katrain_sgf_parser import (
    ParseError as KaTrainParseError,
)
from backend.puzzle_manager.core.katrain_sgf_parser import (
    SGFNode as KaTrainNode,
)
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.exceptions import SGFParseError

logger = logging.getLogger("sgf_parser")


@dataclass
class YenGoProperties:
    """YenGo custom SGF properties (Schema v14).

    YV: Schema version (integer, current: 14)
    YG: Difficulty level (slug format, e.g., "beginner" or "beginner:1")
    YT: Technique tags (comma-separated, alphabetically sorted)
    YH: Compact hint list (pipe-separated text strings)
    YQ: Quality metrics (e.g., "q:3;rc:2;hc:1")
    YX: Complexity metrics (e.g., "d:5;r:13;s:24;u:1")
    YL: Collection membership (comma-separated, with optional :CHAPTER/POSITION suffix)
        - Bare slug: "life-and-death" (backward compatible)
        - With chapter+position: "cho-chikun-elementary:3/12" (chapter "3", position 12)
        - With position only: "cho-chikun-elementary:12" (no chapter, position 12)
        collections field stores bare slugs only; collection_sequences stores
        (chapter_str, position_int) tuples keyed by slug. Chapter is a string
        to support both numeric ("3") and named ("intro-a") chapters.
        Position-only entries use empty string as chapter.
    YM: Pipeline metadata JSON containing:
        t: trace_id (16-char hex, cross-stage correlation)
        i: run_id (e.g., "20260220-abc12345") — was YI in v12
        f: original_filename (from source adapter, optional) — set at ingest,
           stripped at publish (publish log records it independently)

    Note: Source adapter ID tracked via context.source_id and publish log,
    not embedded in YM (\"s\" key removed in v13 cleanup).
    Note: YS and YI removed as separate properties in v13 (folded into YM).
    Note: YH1/YH2/YH3 are REMOVED in v8 - no backward compatibility.
    """

    level: int | None = None
    level_slug: str | None = None  # Stores slug like "beginner"
    tags: list[str] = field(default_factory=list)
    hint_texts: list[str] = field(default_factory=list)  # Compact text hints
    version: int | None = None     # YV
    run_id: str | None = None      # From YM.i (was YI in v12)
    quality: str | None = None     # YQ
    complexity: str | None = None  # YX
    source: str | None = None      # From context.source_id (not in YM)
    collections: list[str] = field(default_factory=list)  # YL (bare slugs)
    collection_sequences: dict[str, tuple[str, int]] = field(default_factory=dict)  # slug → (chapter, position), from YL :CHAPTER/POSITION
    corner: str | None = None      # YC - corner/region position (TL, TR, BL, BR, C, E)
    ko_context: str | None = None  # YK - ko context (simple, superko:positional, etc.)
    move_order: str | None = None  # YO - move order (strict, flexible, miai)
    refutation_count: str | None = None  # YR - wrong first-move SGF coords (comma-sep), not a count
    pipeline_meta: str | None = None  # YM - JSON pipeline metadata (trace_id, original_filename)

    @classmethod
    def from_sgf_props(cls, props: dict[str, str]) -> "YenGoProperties":
        """Create from SGF property dictionary."""
        level = None
        level_slug = None
        if "YG" in props:
            yg_value = props["YG"]
            # Slug format: "beginner" or "beginner:1"
            if yg_value and not yg_value[0].isdigit():
                level_slug = yg_value.split(":")[0]  # Extract slug part
                # Map slug to level number using shared constants
                level = SLUG_TO_LEVEL.get(level_slug, None)
            else:
                # Legacy integer format for parsing old files
                try:
                    level = int(yg_value.split(":")[0])
                except ValueError:
                    pass

        tags = []
        if "YT" in props:
            tags = [t.strip() for t in props["YT"].split(",") if t.strip()]

        # Parse hints - v8 compact format only (YH1/YH2/YH3 not supported)
        hint_texts: list[str] = []
        if "YH" in props and props["YH"]:
            # v8 compact format: YH[hint1|hint2|hint3]
            hint_texts = [h.strip() for h in props["YH"].split("|") if h.strip()]

        # Parse other properties
        version = None
        if "YV" in props:
            try:
                version = int(props["YV"])
            except ValueError:
                pass

        run_id = None
        quality = props.get("YQ")
        complexity = props.get("YX")
        source = None

        # Parse collections (YL, added in v10, extended in v14 with :CHAPTER/POSITION)
        collections: list[str] = []
        collection_sequences: dict[str, tuple[str, int]] = {}
        if "YL" in props and props["YL"]:
            for entry in props["YL"].split(","):
                entry = entry.strip()
                if not entry:
                    continue
                if ":" in entry:
                    slug, seq_part = entry.split(":", 1)
                    collections.append(slug)
                    if "/" in seq_part:
                        # chapter/position format: "3/12" or "intro-a/5"
                        chapter_str, pos_str = seq_part.split("/", 1)
                        try:
                            collection_sequences[slug] = (chapter_str, int(pos_str))
                        except ValueError:
                            logger.warning("Invalid position in YL entry: %s", entry)
                    else:
                        # position-only format: "12" (no chapter)
                        try:
                            collection_sequences[slug] = ("", int(seq_part))
                        except ValueError:
                            logger.warning("Invalid YL sequence format: %s", entry)
                else:
                    collections.append(entry)
            collections = sorted(collections)

        # Parse optional enrichment properties
        corner = props.get("YC")
        ko_context = props.get("YK")
        move_order = props.get("YO")
        refutation_count = props.get("YR")

        # Parse pipeline metadata (v13 — run_id lives here; source tracked via context)
        pipeline_meta = props.get("YM")

        if pipeline_meta:
            from backend.puzzle_manager.core.trace_utils import parse_pipeline_meta
            _, _, _, ym_run_id = parse_pipeline_meta(pipeline_meta)
            if ym_run_id:
                run_id = ym_run_id

        return cls(
            level=level,
            level_slug=level_slug,
            tags=tags,
            hint_texts=hint_texts,
            version=version,
            run_id=run_id,
            quality=quality,
            complexity=complexity,
            source=source,
            collections=collections,
            collection_sequences=collection_sequences,
            corner=corner,
            ko_context=ko_context,
            move_order=move_order,
            refutation_count=refutation_count,
            pipeline_meta=pipeline_meta,
        )


@dataclass
class SolutionNode:
    """Node in the solution tree."""

    move: Point | None = None
    color: Color | None = None
    comment: str = ""
    is_correct: bool = True
    children: list["SolutionNode"] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    def add_child(self, node: "SolutionNode") -> None:
        """Add a child variation."""
        self.children.append(node)

    def get_main_line(self) -> list["SolutionNode"]:
        """Get the main line (first variation at each node)."""
        result = []
        current: SolutionNode | None = self
        while current is not None:
            result.append(current)
            current = current.children[0] if current.children else None
        return result

    def count_variations(self) -> int:
        """Count total variations in subtree."""
        count = 1
        for child in self.children:
            count += child.count_variations()
        return count


@dataclass
class SGFGame:
    """Parsed SGF game representation."""

    board_size: int = 19
    black_stones: list[Point] = field(default_factory=list)
    white_stones: list[Point] = field(default_factory=list)
    player_to_move: Color = Color.BLACK
    solution_tree: SolutionNode = field(default_factory=SolutionNode)
    metadata: dict[str, Any] = field(default_factory=dict)
    yengo_props: YenGoProperties = field(default_factory=YenGoProperties)
    raw_sgf: str = ""
    root_comment: str = ""  # Root C[] comment, stored separately from metadata

    @property
    def has_solution(self) -> bool:
        """Check if puzzle has at least one solution move."""
        return bool(self.solution_tree.children)

    def get_first_move(self) -> tuple[Color, Point] | None:
        """Get the first correct move if available."""
        if not self.solution_tree.children:
            return None
        first = self.solution_tree.children[0]
        if first.move and first.color:
            return (first.color, first.move)
        return None


class _RootPropertyTokenizer:
    """Minimal tokenizer for extracting root node properties only.

    Used by parse_root_properties_only() for fast metadata extraction
    without building the full game tree.
    """

    def __init__(self, content: str) -> None:
        self.content = content.strip()
        self.pos = 0

    def parse_root_props(self) -> dict[str, str]:
        """Parse root node properties and return as dict."""
        props: dict[str, str] = {}
        self._skip_whitespace()
        if self.pos >= len(self.content) or self.content[self.pos] != ";":
            return props
        self.pos += 1
        while self.pos < len(self.content):
            self._skip_whitespace()
            if self.pos >= len(self.content):
                break
            char = self.content[self.pos]
            if char in ";()":
                break
            prop_name = self._parse_property_name()
            if not prop_name:
                self.pos += 1
                continue
            prop_values = self._parse_property_values()
            if prop_values:
                props[prop_name] = prop_values[-1] if len(prop_values) == 1 else ",".join(prop_values)
        return props

    def _parse_property_name(self) -> str:
        start = self.pos
        while self.pos < len(self.content) and self.content[self.pos].isupper():
            self.pos += 1
        return self.content[start:self.pos]

    def _parse_property_values(self) -> list[str]:
        values = []
        while self.pos < len(self.content) and self.content[self.pos] == "[":
            self.pos += 1
            value_start = self.pos
            depth = 1
            while self.pos < len(self.content) and depth > 0:
                char = self.content[self.pos]
                if char == "\\":
                    self.pos += 2
                    continue
                if char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                self.pos += 1
            values.append(self.content[value_start:self.pos - 1])
        return values

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.content) and self.content[self.pos] in " \t\n\r":
            self.pos += 1


def _convert_katrain_node(kt_node: KaTrainNode, parent_color: Color | None = None) -> SolutionNode:
    """Convert a KaTrain SGFNode to a SolutionNode (recursive)."""
    from backend.puzzle_manager.core.correctness import infer_correctness

    node = SolutionNode()

    # Extract move
    if kt_node.move is not None and not kt_node.move.is_pass:
        move = kt_node.move
        sgf_coord = move.sgf(kt_node.board_size)
        if sgf_coord:
            node.move = Point.from_sgf(sgf_coord)
            node.color = Color.BLACK if move.player == "B" else Color.WHITE

    # Extract comment
    comment = kt_node.get_property("C", "")
    if comment:
        node.comment = comment

    # Flatten properties for correctness inference
    flat_props: dict[str, str] = {}
    for k, v in kt_node.properties.items():
        if v:
            flat_props[k] = v[0] if len(v) == 1 else ",".join(v)
    node.properties = flat_props

    # Infer correctness
    result = infer_correctness(node.comment, flat_props)
    if result is not None:
        node.is_correct = result

    # Recursively convert children
    for child in kt_node.children:
        child_node = _convert_katrain_node(child)
        node.add_child(child_node)

    return node


def _convert_katrain_tree(root: KaTrainNode) -> SGFGame:
    """Convert a KaTrain SGFNode root into an SGFGame."""
    from backend.puzzle_manager.core.property_policy import get_policy_registry

    game = SGFGame(raw_sgf=root.sgf())

    # Board size
    bs = root.board_size
    game.board_size = bs[0]

    # Initial stones (AB/AW)
    for coord in root.get_list_property("AB"):
        if coord:
            try:
                game.black_stones.append(Point.from_sgf(coord))
            except ValueError:
                pass
    for coord in root.get_list_property("AW"):
        if coord:
            try:
                game.white_stones.append(Point.from_sgf(coord))
            except ValueError:
                pass

    # Player to move
    pl = root.get_property("PL", "")
    if pl == "W":
        game.player_to_move = Color.WHITE
    else:
        game.player_to_move = Color.BLACK

    # Copy metadata — use property policy registry to filter
    registry = get_policy_registry()
    flat_props: dict[str, str] = {}
    for k, v in root.properties.items():
        if v:
            flat_props[k] = v[0] if len(v) == 1 else ",".join(v)

    for key in ("GN", "GC", "PB", "PW", "SO", "AN"):
        if key in flat_props and registry.is_property_allowed(key):
            game.metadata[key] = flat_props[key]

    # Preserve root-level SGF markup properties
    _ROOT_MARKUP_PROPS = ("LB", "SQ", "CR", "MA", "TR")
    for key in _ROOT_MARKUP_PROPS:
        if key in flat_props:
            game.metadata[key] = flat_props[key]

    # Store root comment
    comment = root.get_property("C", "")
    if comment:
        game.root_comment = comment

    # YenGo custom properties
    game.yengo_props = YenGoProperties.from_sgf_props(flat_props)

    # Convert solution tree from root's children
    solution_root = SolutionNode()
    for child in root.children:
        child_node = _convert_katrain_node(child)
        solution_root.add_child(child_node)
    game.solution_tree = solution_root

    return game


def parse_sgf(content: str) -> SGFGame:
    """Parse SGF content into SGFGame.

    Uses KaTrain's SGF parser internally for robust grammar handling,
    then converts the KaTrain tree to SGFGame/SolutionNode/YenGoProperties.

    Args:
        content: SGF file content.

    Returns:
        Parsed SGFGame object.

    Raises:
        SGFParseError: If SGF is invalid.
    """
    content = content.strip()
    if not content:
        raise SGFParseError("Empty SGF content")

    try:
        kt_root = KaTrainSGF.parse_sgf(content)
    except KaTrainParseError as e:
        raise SGFParseError(f"Failed to parse SGF: {e}") from e
    except Exception as e:
        raise SGFParseError(f"Failed to parse SGF: {e}") from e

    return _convert_katrain_tree(kt_root)


def parse_root_properties_only(content: str) -> dict[str, str]:
    """Parse only root node properties from SGF, without building the game tree.

    ~10-50x faster than full parse_sgf() for reconciliation/metadata-only use cases.
    Reuses the existing SGFParser tokenizer but stops after the root node —
    no tree construction, no move parsing, no SolutionNode allocation.

    Args:
        content: SGF file content.

    Returns:
        dict of property name → value for root node only (e.g. {"YT": "ko,ladder", "YQ": "q:2;rc:0;hc:0"}).

    Raises:
        SGFParseError: If SGF is empty or missing opening paren.
    """
    stripped = content.strip()
    if not stripped:
        raise SGFParseError("Empty SGF content")
    if not stripped.startswith("("):
        raise SGFParseError("SGF must start with '('")

    tokenizer = _RootPropertyTokenizer(stripped)
    tokenizer.pos = 1  # Skip opening paren
    return tokenizer.parse_root_props()
