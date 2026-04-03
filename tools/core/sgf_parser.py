"""
SGF parser for puzzle files.

Character-by-character recursive descent parser that builds a tree structure
from SGF content, including YenGo custom properties (Schema v10).

Ported from backend/puzzle_manager/core/sgf_parser.py for use across all tools.
Tools must NOT import from backend/ — this is a standalone implementation.

Usage:
    from tools.core.sgf_parser import parse_sgf, SgfNode, SgfTree

    tree = parse_sgf(sgf_content)
    print(tree.board_size)           # 19
    print(tree.player_to_move)       # Color.BLACK
    print(tree.root.children)        # Solution variations
    print(tree.yengo_props.tags)     # ['life-and-death', 'ko']
    print(tree.root_comment)         # Root C[] text

Public API:
    parse_sgf(content) -> SgfTree       — Main entry point
    escape_sgf_value(value) -> str      — Escape text for SGF property values
    SgfNode                             — Tree node dataclass
    SgfTree                             — Top-level container dataclass
    YenGoProperties                     — YenGo custom SGF properties
    SGFParseError                       — Parse error exception
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from tools.core.sgf_correctness import infer_correctness
from tools.core.sgf_types import SLUG_TO_LEVEL, Color, Point

logger = logging.getLogger("tools.core.sgf_parser")


class SGFParseError(Exception):
    """Raised when SGF content cannot be parsed."""

    pass


# ---------------------------------------------------------------------------
# SGF text utilities
# ---------------------------------------------------------------------------


def escape_sgf_value(value: str) -> str:
    """Escape special characters in SGF property values.

    SGF requires escaping of backslash and closing bracket characters.
    The order of operations matters: backslash must be escaped first.

    Args:
        value: Raw string value to escape.

    Returns:
        Escaped string safe for SGF property value.

    Example:
        >>> escape_sgf_value("test]value")
        'test\\\\]value'
    """
    # Escape backslash first (order matters!)
    value = value.replace("\\", "\\\\")
    # Escape closing bracket
    value = value.replace("]", "\\]")
    return value


def unescape_sgf_value(value: str) -> str:
    """Unescape SGF property value text.

    Reverses the escaping done by ``escape_sgf_value``.

    Args:
        value: Escaped SGF property value.

    Returns:
        Unescaped text.
    """
    result: list[str] = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            result.append(value[i + 1])
            i += 2
        else:
            result.append(value[i])
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class YenGoProperties:
    """YenGo custom SGF properties (Schema v10).

    YV: Schema version (integer, current: 10)
    YG: Difficulty level (slug format, e.g., "beginner" or "beginner:1")
    YT: Technique tags (comma-separated, alphabetically sorted)
    YH: Compact hint list (pipe-separated text strings)
    YI: Pipeline run ID for rollback tracking
    YQ: Quality metrics (e.g., "q:3;rc:2;hc:1")
    YX: Complexity metrics (e.g., "d:5;r:13;s:24;u:1")
    YS: Source adapter ID (e.g., "sanderland", "ogs")
    YL: Collection membership (comma-separated sorted slugs)
    YC: Corner position (TL, TR, BL, BR, C, E)
    YK: Ko context (none, simple, superko:positional, superko:situational)
    YO: Move order (strict, flexible, miai)
    YR: Refutation moves — wrong first-move SGF coords (comma-separated)
    """

    level: int | None = None
    level_slug: str | None = None
    tags: list[str] = field(default_factory=list)
    hint_texts: list[str] = field(default_factory=list)
    version: int | None = None
    run_id: str | None = None
    quality: str | None = None
    complexity: str | None = None
    source: str | None = None
    collections: list[str] = field(default_factory=list)
    corner: str | None = None
    ko_context: str | None = None
    move_order: str | None = None
    refutation_count: str | None = None

    @classmethod
    def from_sgf_props(cls, props: dict[str, str]) -> YenGoProperties:
        """Create from SGF property dictionary.

        Parses all YenGo custom properties (Y-prefixed) from a dict of
        raw SGF property name -> value mappings.
        """
        level: int | None = None
        level_slug: str | None = None
        if "YG" in props:
            yg_value = props["YG"]
            if yg_value and not yg_value[0].isdigit():
                level_slug = yg_value.split(":")[0]
                level = SLUG_TO_LEVEL.get(level_slug)
            else:
                try:
                    level = int(yg_value.split(":")[0])
                except ValueError:
                    pass

        tags: list[str] = []
        if "YT" in props:
            tags = [t.strip() for t in props["YT"].split(",") if t.strip()]

        hint_texts: list[str] = []
        if "YH" in props and props["YH"]:
            hint_texts = [h.strip() for h in props["YH"].split("|") if h.strip()]

        version: int | None = None
        if "YV" in props:
            try:
                version = int(props["YV"])
            except ValueError:
                pass

        collections: list[str] = []
        if "YL" in props and props["YL"]:
            collections = sorted(
                [c.strip() for c in props["YL"].split(",") if c.strip()]
            )

        return cls(
            level=level,
            level_slug=level_slug,
            tags=tags,
            hint_texts=hint_texts,
            version=version,
            run_id=props.get("YI"),
            quality=props.get("YQ"),
            complexity=props.get("YX"),
            source=props.get("YS"),
            collections=collections,
            corner=props.get("YC"),
            ko_context=props.get("YK"),
            move_order=props.get("YO"),
            refutation_count=props.get("YR"),
        )


@dataclass
class SgfNode:
    """Node in the SGF solution tree.

    Each node represents a move (or the root placeholder) and contains
    child nodes for continuation / variation branches.
    """

    move: Point | None = None
    color: Color | None = None
    comment: str = ""
    is_correct: bool = True
    children: list[SgfNode] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    def add_child(self, node: SgfNode) -> None:
        """Add a child variation."""
        self.children.append(node)

    def get_main_line(self) -> list[SgfNode]:
        """Get the main line (first variation at each node)."""
        result: list[SgfNode] = []
        current: SgfNode | None = self
        while current is not None:
            result.append(current)
            current = current.children[0] if current.children else None
        return result

    def count_variations(self) -> int:
        """Count total nodes in subtree (including self)."""
        count = 1
        for child in self.children:
            count += child.count_variations()
        return count


@dataclass
class SgfTree:
    """Parsed SGF game representation.

    Top-level container holding board setup, solution tree, metadata,
    and YenGo custom properties.
    """

    board_size: int = 19
    black_stones: list[Point] = field(default_factory=list)
    white_stones: list[Point] = field(default_factory=list)
    player_to_move: Color = Color.BLACK
    solution_tree: SgfNode = field(default_factory=SgfNode)
    metadata: dict[str, Any] = field(default_factory=dict)
    yengo_props: YenGoProperties = field(default_factory=YenGoProperties)
    raw_sgf: str = ""
    root_comment: str = ""

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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class SGFParser:
    """Character-by-character recursive descent SGF parser.

    Parses SGF content into an SgfTree, handling:
    - Root node properties (SZ, AB, AW, PL, metadata)
    - YenGo custom properties (YV, YG, YT, YH, YI, YQ, YX, YS, YL, YC, YK, YO, YR)
    - Solution tree with nested variations
    - Escaped characters in property values
    - Move correctness inference via comment/marker analysis
    """

    def __init__(self, content: str) -> None:
        """Initialize parser with SGF content."""
        self.content = content.strip()
        self.pos = 0

    def parse(self) -> SgfTree:
        """Parse SGF content into SgfTree.

        Returns:
            Parsed SgfTree object.

        Raises:
            SGFParseError: If SGF is invalid.
        """
        if not self.content:
            raise SGFParseError("Empty SGF content")

        if not self.content.startswith("("):
            raise SGFParseError("SGF must start with '('")

        tree = SgfTree(raw_sgf=self.content)

        try:
            self._parse_game_tree(tree)
        except SGFParseError:
            raise
        except Exception as e:
            raise SGFParseError(f"Failed to parse SGF: {e}") from e

        return tree

    def _parse_game_tree(self, tree: SgfTree) -> None:
        """Parse the main game tree."""
        # Skip opening paren
        self.pos = 1

        # Parse root node
        root_props = self._parse_node()
        self._apply_root_properties(tree, root_props)

        # Parse solution tree
        tree.solution_tree = self._parse_variations()

    def _parse_node(self) -> dict[str, str]:
        """Parse a single node and return its properties.

        A node starts with ``;`` followed by zero or more properties.
        Each property is ``NAME[value]`` with optional multiple values
        ``NAME[v1][v2]``.  Escaped characters inside brackets are handled.
        """
        props: dict[str, str] = {}

        self._skip_whitespace()

        if self.pos >= len(self.content):
            return props

        # Must start with semicolon for a node
        if self.content[self.pos] != ";":
            return props

        self.pos += 1

        # Parse properties until we hit ; or ( or )
        while self.pos < len(self.content):
            self._skip_whitespace()

            if self.pos >= len(self.content):
                break

            char = self.content[self.pos]
            if char in ";()":
                break

            # Try to parse a property
            prop_name = self._parse_property_name()
            if not prop_name:
                self.pos += 1
                continue

            prop_values = self._parse_property_values()
            if prop_values:
                # Join multiple values (e.g., AB[aa][bb][cc] -> "aa,bb,cc")
                new_value = (
                    prop_values[0]
                    if len(prop_values) == 1
                    else ",".join(prop_values)
                )
                # Handle repeated property names (e.g., AB[oc]AB[od]AB[oe])
                # by appending to the existing value
                if prop_name in props:
                    props[prop_name] = props[prop_name] + "," + new_value
                else:
                    props[prop_name] = new_value

        return props

    def _parse_property_name(self) -> str:
        """Parse property name (one or more uppercase letters)."""
        start = self.pos
        while self.pos < len(self.content) and self.content[self.pos].isupper():
            self.pos += 1
        return self.content[start : self.pos]

    def _parse_property_values(self) -> list[str]:
        """Parse one or more bracketed property values.

        Handles escaped characters: ``\\]`` inside values is not treated
        as the closing bracket.
        """
        values: list[str] = []
        while self.pos < len(self.content) and self.content[self.pos] == "[":
            self.pos += 1  # Skip [
            value_start = self.pos
            depth = 1
            while self.pos < len(self.content) and depth > 0:
                char = self.content[self.pos]
                if char == "\\":
                    self.pos += 2  # Skip escaped char
                    continue
                if char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                self.pos += 1
            values.append(self.content[value_start : self.pos - 1])
        return values

    def _parse_variations(self) -> SgfNode:
        """Parse solution tree with variations."""
        root = SgfNode()
        self._parse_node_tree(root)
        return root

    def _parse_node_tree(self, parent: SgfNode) -> None:
        """Recursively parse node tree.

        Handles three SGF constructs:
        - ``)`` — end of current variation, return to caller
        - ``(`` — start of a new variation branch
        - ``;`` — a new node in the current sequence
        """
        while self.pos < len(self.content):
            self._skip_whitespace()

            if self.pos >= len(self.content):
                break

            char = self.content[self.pos]

            if char == ")":
                self.pos += 1
                return

            if char == "(":
                # Start of variation
                self.pos += 1
                var_node = SgfNode()
                self._parse_node_tree(var_node)
                # Add variation children to parent
                for child in var_node.children:
                    parent.add_child(child)
                continue

            if char == ";":
                # New node
                props = self._parse_node()
                node = self._props_to_node(props)
                parent.add_child(node)
                # Continue parsing children of this node
                self._parse_node_tree(node)
                return

            self.pos += 1

    def _props_to_node(self, props: dict[str, str]) -> SgfNode:
        """Convert raw properties dict to an SgfNode.

        Extracts move color/coordinate, comment text, and infers
        correctness using the 2-layer fallback system.
        """
        node = SgfNode(properties=props)

        # Extract move
        if "B" in props:
            coord = props["B"]
            node.color = Color.BLACK
            if coord and coord != "tt":
                try:
                    node.move = Point.from_sgf(coord)
                except ValueError:
                    pass
        elif "W" in props:
            coord = props["W"]
            node.color = Color.WHITE
            if coord and coord != "tt":
                try:
                    node.move = Point.from_sgf(coord)
                except ValueError:
                    pass

        # Extract comment
        if "C" in props:
            node.comment = props["C"]

        # Infer correctness using Layers 1 & 2
        result = infer_correctness(node.comment, props)
        if result is not None:
            node.is_correct = result

        return node

    def _apply_root_properties(self, tree: SgfTree, props: dict[str, str]) -> None:
        """Apply root node properties to the SgfTree."""
        # Board size
        if "SZ" in props:
            try:
                tree.board_size = int(props["SZ"])
            except ValueError:
                tree.board_size = 19

        # Initial stones — values are comma-joined by _parse_node
        if "AB" in props:
            for coord in props["AB"].split(","):
                coord = coord.strip()
                if coord:
                    try:
                        tree.black_stones.append(Point.from_sgf(coord))
                    except ValueError:
                        pass

        if "AW" in props:
            for coord in props["AW"].split(","):
                coord = coord.strip()
                if coord:
                    try:
                        tree.white_stones.append(Point.from_sgf(coord))
                    except ValueError:
                        pass

        # Player to move
        if "PL" in props:
            tree.player_to_move = (
                Color.WHITE if props["PL"] == "W" else Color.BLACK
            )

        # Copy standard metadata
        for key in ("GN", "GC", "PB", "PW", "DT", "RE", "SO", "AP", "MN"):
            if key in props:
                tree.metadata[key] = props[key]

        # Root comment — stored separately
        if "C" in props:
            tree.root_comment = props["C"]

        # YenGo custom properties
        tree.yengo_props = YenGoProperties.from_sgf_props(props)

    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while (
            self.pos < len(self.content)
            and self.content[self.pos] in " \t\n\r"
        ):
            self.pos += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_sgf(content: str) -> SgfTree:
    """Parse SGF content into an SgfTree.

    This is the main entry point for SGF parsing across all tools.

    Args:
        content: SGF file content string.

    Returns:
        Parsed SgfTree object with board setup, solution tree, metadata,
        and YenGo custom properties.

    Raises:
        SGFParseError: If SGF content is invalid or cannot be parsed.

    Example:
        tree = parse_sgf("(;SZ[19]AB[cd]AW[ef]PL[B](;B[gh]))")
        assert tree.board_size == 19
        assert len(tree.black_stones) == 1
        assert tree.has_solution is True
    """
    parser = SGFParser(content)
    return parser.parse()
