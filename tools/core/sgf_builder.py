"""
SGF builder for creating and modifying puzzle files.

Fluent builder API for constructing SGF strings with YenGo custom
properties support.  Also provides ``publish_sgf()`` for round-trip
parse -> modify -> rebuild workflows.

Ported from backend/puzzle_manager/core/sgf_builder.py and
backend/puzzle_manager/core/sgf_publisher.py.
Tools must NOT import from backend/ — this is a standalone implementation.

Usage:
    from tools.core.sgf_builder import SGFBuilder, publish_sgf
    from tools.core.sgf_parser import parse_sgf
    from tools.core.sgf_types import Color, Point

    # Build from scratch
    builder = SGFBuilder(board_size=19)
    builder.add_black_stone(Point(3, 3))
    builder.set_player_to_move(Color.BLACK)
    builder.set_level_slug("beginner")
    builder.add_tag("life-and-death")
    builder.add_solution_move(Color.BLACK, Point(2, 3))
    sgf = builder.build()

    # Round-trip: parse -> modify -> rebuild
    tree = parse_sgf(existing_sgf)
    builder = SGFBuilder.from_tree(tree)
    builder.add_tags(["ko", "tesuji"])
    new_sgf = builder.build()

    # Shortcut for round-trip
    new_sgf = publish_sgf(tree)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tools.core.sgf_parser import (
    SgfNode,
    SgfTree,
    YenGoProperties,
    escape_sgf_value,
)
from tools.core.sgf_types import SLUG_TO_LEVEL, Color, Point

if TYPE_CHECKING:
    pass


class SGFBuildError(Exception):
    """Raised when SGF cannot be built due to invalid input."""

    pass


# SGF properties that use multiple [value] brackets per the SGF spec.
# When the parser stores them comma-joined (e.g., "aa:A,bb:B"), the
# builder must split and re-wrap each value on serialization.
_MULTI_VALUE_PROPERTIES = frozenset({
    "AB", "AW", "AE",          # Add Black/White/Empty stones
    "LB",                       # Labels: LB[cd:A][ef:B]
    "TR", "SQ", "CR", "MA",    # Markup: triangles, squares, circles, marks
    "SL",                       # Selected points
    "AR", "LN",                 # Arrows, lines: AR[cd:ef] LN[cd:ef]
    "TB", "TW",                 # Territory
    "DD", "VW",                 # Dim points, view
})


class SGFBuilder:
    """Builder for creating SGF content.

    Provides a fluent API where most setter methods return ``self`` for
    chaining.  Call ``build()`` to produce the final SGF string.
    """

    def __init__(self, board_size: int = 19) -> None:
        """Initialize builder with board size.

        Args:
            board_size: Board size (5-19).

        Raises:
            SGFBuildError: If board size is invalid.
        """
        if not (5 <= board_size <= 19):
            raise SGFBuildError(f"Invalid board size: {board_size}")

        self.board_size = board_size
        self.black_stones: list[Point] = []
        self.white_stones: list[Point] = []
        self.player_to_move: Color | None = None
        self.metadata: dict[str, str] = {}
        self.root_comment: str = ""
        self.yengo_props = YenGoProperties()
        self.solution_tree = SgfNode()
        self._current_node = self.solution_tree

    # --- Factory -----------------------------------------------------------

    @classmethod
    def from_tree(cls, tree: SgfTree) -> SGFBuilder:
        """Create builder from an existing parsed SgfTree.

        This is the inverse of ``to_tree()`` — it initializes a builder
        with the state from a parsed SGF, allowing modification and
        re-serialization.

        Args:
            tree: Parsed SgfTree object.

        Returns:
            SGFBuilder initialized with tree state.
        """
        builder = cls(board_size=tree.board_size)

        builder.black_stones = list(tree.black_stones)
        builder.white_stones = list(tree.white_stones)
        builder.player_to_move = tree.player_to_move
        builder.metadata = dict(tree.metadata)
        builder.root_comment = tree.root_comment

        # Use the same solution tree reference (SgfNode is mutable)
        builder.solution_tree = tree.solution_tree
        builder._current_node = builder.solution_tree

        # Deep-copy YenGo properties
        if tree.yengo_props:
            builder.yengo_props = YenGoProperties(
                level=tree.yengo_props.level,
                level_slug=tree.yengo_props.level_slug,
                tags=list(tree.yengo_props.tags),
                hint_texts=list(tree.yengo_props.hint_texts),
                version=tree.yengo_props.version,
                run_id=tree.yengo_props.run_id,
                quality=tree.yengo_props.quality,
                complexity=tree.yengo_props.complexity,
                source=tree.yengo_props.source,
                collections=list(tree.yengo_props.collections),
                corner=tree.yengo_props.corner,
                ko_context=tree.yengo_props.ko_context,
                move_order=tree.yengo_props.move_order,
                refutation_count=tree.yengo_props.refutation_count,
            )

        return builder

    # --- Stone setup -------------------------------------------------------

    def add_black_stone(self, point: Point) -> SGFBuilder:
        """Add a black stone to initial position."""
        self.black_stones.append(point)
        return self

    def add_black_stones(self, points: list[Point]) -> SGFBuilder:
        """Add multiple black stones to initial position."""
        self.black_stones.extend(points)
        return self

    def add_white_stone(self, point: Point) -> SGFBuilder:
        """Add a white stone to initial position."""
        self.white_stones.append(point)
        return self

    def add_white_stones(self, points: list[Point]) -> SGFBuilder:
        """Add multiple white stones to initial position."""
        self.white_stones.extend(points)
        return self

    # --- Game properties ---------------------------------------------------

    def set_player_to_move(self, color: Color) -> SGFBuilder:
        """Set the player to move."""
        self.player_to_move = color
        return self

    def set_metadata(self, key: str, value: str) -> SGFBuilder:
        """Set an arbitrary metadata property."""
        self.metadata[key] = value
        return self

    def set_game_name(self, name: str) -> SGFBuilder:
        """Set game name (GN property)."""
        return self.set_metadata("GN", name)

    def set_yengo_game_name(self, hex_hash: str) -> SGFBuilder:
        """Set standardized YenGo game name (``GN[YENGO-{16hex}]``).

        Args:
            hex_hash: 16-character lowercase hex string.

        Raises:
            SGFBuildError: If hex_hash format is invalid.
        """
        if len(hex_hash) != 16 or not all(
            c in "0123456789abcdef" for c in hex_hash.lower()
        ):
            raise SGFBuildError(
                f"hex_hash must be 16 hex chars, got: {hex_hash}"
            )
        return self.set_metadata("GN", f"YENGO-{hex_hash.lower()}")

    def set_comment(self, comment: str) -> SGFBuilder:
        """Set root comment (C property)."""
        self.root_comment = comment
        return self

    # --- YenGo properties --------------------------------------------------

    def set_level(self, level: int) -> SGFBuilder:
        """Set YenGo difficulty level (1-9 numeric)."""
        if not 1 <= level <= 9:
            raise SGFBuildError(f"Level must be 1-9, got {level}")
        self.yengo_props.level = level
        return self

    def set_level_slug(
        self, slug: str, sublevel: int | None = None
    ) -> SGFBuilder:
        """Set YenGo difficulty level as slug format.

        Args:
            slug: Level slug (e.g., ``"beginner"``).
            sublevel: Optional sub-level 1–3.

        Raises:
            SGFBuildError: If slug or sublevel is invalid.
        """
        valid_slugs = [
            "novice", "beginner", "elementary", "intermediate",
            "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
        ]
        if slug not in valid_slugs:
            raise SGFBuildError(f"Invalid level slug: {slug}")
        if sublevel is not None and not 1 <= sublevel <= 3:
            raise SGFBuildError(f"Sub-level must be 1-3, got {sublevel}")

        self.yengo_props.level_slug = (
            f"{slug}:{sublevel}" if sublevel else slug
        )
        self.yengo_props.level = SLUG_TO_LEVEL.get(slug)
        return self

    def set_version(self, version: int) -> SGFBuilder:
        """Set schema version (YV property)."""
        if version < 1:
            raise SGFBuildError(f"Version must be positive, got {version}")
        self.yengo_props.version = version
        return self

    def set_run_id(self, run_id: str) -> SGFBuilder:
        """Set pipeline run ID (YI property).

        Args:
            run_id: Run ID in ``YYYYMMDD-xxxxxxxx`` format.

        Raises:
            SGFBuildError: If format is invalid.
        """
        pattern = r"^[0-9]{8}-[a-f0-9]{8}$"
        if not re.match(pattern, run_id):
            raise SGFBuildError(
                f"Run ID must be YYYYMMDD-xxxxxxxx, got: {run_id}"
            )
        self.yengo_props.run_id = run_id
        return self

    def set_quality(self, quality: str) -> SGFBuilder:
        """Set quality metrics (YQ property, e.g. ``"q:3;rc:2;hc:1"``)."""
        if not quality.startswith("q:"):
            raise SGFBuildError(f"Quality must start with 'q:', got {quality}")
        self.yengo_props.quality = quality
        return self

    def set_complexity(self, complexity: str) -> SGFBuilder:
        """Set complexity metrics (YX property, e.g. ``"d:5;r:13;s:24;u:1"``)."""
        if not complexity.startswith("d:"):
            raise SGFBuildError(
                f"Complexity must start with 'd:', got {complexity}"
            )
        self.yengo_props.complexity = complexity
        return self

    def set_source(self, source_id: str) -> SGFBuilder:
        """Set source adapter ID (YS property)."""
        self.yengo_props.source = source_id
        return self

    def set_corner(self, corner: str) -> SGFBuilder:
        """Set corner/region position (YC property)."""
        self.yengo_props.corner = corner
        return self

    def set_ko_context(self, ko_context: str) -> SGFBuilder:
        """Set ko context (YK property)."""
        self.yengo_props.ko_context = ko_context
        return self

    def set_move_order(self, move_order: str) -> SGFBuilder:
        """Set move order flexibility (YO property)."""
        self.yengo_props.move_order = move_order
        return self

    def set_refutation_count(self, refutation_count: str) -> SGFBuilder:
        """Set refutation moves (YR property — comma-separated SGF coords)."""
        self.yengo_props.refutation_count = refutation_count
        return self

    def add_tag(self, tag: str) -> SGFBuilder:
        """Add a technique tag to YT."""
        if tag not in self.yengo_props.tags:
            self.yengo_props.tags.append(tag)
        return self

    def add_tags(self, tags: list[str]) -> SGFBuilder:
        """Add multiple technique tags."""
        for tag in tags:
            self.add_tag(tag)
        return self

    def add_collection(self, slug: str) -> SGFBuilder:
        """Add a collection membership (YL property)."""
        if slug not in self.yengo_props.collections:
            self.yengo_props.collections.append(slug)
        return self

    def set_collections(self, slugs: list[str]) -> SGFBuilder:
        """Set collection memberships (YL property), replacing all."""
        self.yengo_props.collections = list(slugs)
        return self

    def add_hints(self, hints: list[str]) -> SGFBuilder:
        """Add compact text hints (YH property, pipe-delimited)."""
        non_empty = [h.strip() for h in hints if h and h.strip()]
        self.yengo_props.hint_texts = non_empty
        return self

    # --- Solution tree -----------------------------------------------------

    def add_solution_move(
        self,
        color: Color,
        point: Point,
        comment: str = "",
        is_correct: bool = True,
    ) -> SGFBuilder:
        """Add a move to the solution tree at the current position."""
        node = SgfNode(
            move=point,
            color=color,
            comment=comment,
            is_correct=is_correct,
        )
        self._current_node.add_child(node)
        self._current_node = node
        return self

    def add_variation(self) -> SGFBuilder:
        """Start a new variation from the root."""
        self._current_node = self.solution_tree
        return self

    def back_to_root(self) -> SGFBuilder:
        """Return cursor to root for adding another variation."""
        self._current_node = self.solution_tree
        return self

    # --- Serialization -----------------------------------------------------

    def build(self) -> str:
        """Build the SGF string.

        Returns:
            Complete SGF string.
        """
        parts: list[str] = ["(;"]

        # Root properties
        parts.append(f"SZ[{self.board_size}]")
        parts.append("FF[4]")
        parts.append("GM[1]")

        # Player to move
        if self.player_to_move:
            parts.append(f"PL[{self.player_to_move}]")

        # Metadata
        for key, value in self.metadata.items():
            escaped = escape_sgf_value(value)
            parts.append(f"{key}[{escaped}]")

        # Root comment
        if self.root_comment:
            escaped = escape_sgf_value(self.root_comment)
            parts.append(f"C[{escaped}]")

        # --- YenGo properties ---
        if self.yengo_props.version is not None:
            parts.append(f"YV[{self.yengo_props.version}]")

        if self.yengo_props.level_slug:
            parts.append(f"YG[{self.yengo_props.level_slug}]")
        elif self.yengo_props.level is not None:
            parts.append(f"YG[{self.yengo_props.level}]")

        if self.yengo_props.tags:
            tags_str = ",".join(sorted(set(self.yengo_props.tags)))
            parts.append(f"YT[{tags_str}]")

        if self.yengo_props.run_id:
            parts.append(f"YI[{self.yengo_props.run_id}]")

        if self.yengo_props.quality:
            parts.append(f"YQ[{self.yengo_props.quality}]")

        if self.yengo_props.complexity:
            parts.append(f"YX[{self.yengo_props.complexity}]")

        if self.yengo_props.source:
            parts.append(f"YS[{self.yengo_props.source}]")

        if self.yengo_props.collections:
            collections_str = ",".join(
                sorted(set(self.yengo_props.collections))
            )
            parts.append(f"YL[{collections_str}]")

        if self.yengo_props.hint_texts:
            hint_string = "|".join(self.yengo_props.hint_texts)
            escaped = escape_sgf_value(hint_string)
            parts.append(f"YH[{escaped}]")

        if self.yengo_props.corner:
            parts.append(f"YC[{self.yengo_props.corner}]")

        if self.yengo_props.ko_context:
            parts.append(f"YK[{self.yengo_props.ko_context}]")

        if self.yengo_props.move_order:
            parts.append(f"YO[{self.yengo_props.move_order}]")

        if self.yengo_props.refutation_count:
            parts.append(f"YR[{self.yengo_props.refutation_count}]")

        # Initial stones
        if self.black_stones:
            coords = "][".join(p.to_sgf() for p in self.black_stones)
            parts.append(f"AB[{coords}]")

        if self.white_stones:
            coords = "][".join(p.to_sgf() for p in self.white_stones)
            parts.append(f"AW[{coords}]")

        # Solution tree
        parts.append(self._build_tree(self.solution_tree))

        parts.append(")")
        return "".join(parts)

    def _build_tree(self, node: SgfNode) -> str:
        """Build SGF string for solution tree."""
        if not node.children:
            return ""

        parts: list[str] = []

        if len(node.children) == 1:
            # Single variation — no parens needed
            child = node.children[0]
            parts.append(self._build_node(child))
            parts.append(self._build_tree(child))
        else:
            # Multiple variations — wrap each in parens
            for child in node.children:
                parts.append("(")
                parts.append(self._build_node(child))
                parts.append(self._build_tree(child))
                parts.append(")")

        return "".join(parts)

    def _build_node(self, node: SgfNode) -> str:
        """Build SGF string for a single move node.

        Preserves ALL properties stored in ``node.properties`` so that
        arbitrary SGF annotations (LB, MN, TR, SQ, MA, CR, etc.) survive
        a parse -> modify -> rebuild round-trip.

        When ``node.properties`` is populated (i.e. the node came from
        ``parse_sgf``), the properties dict is the source of truth and
        we serialize every entry.  When building from scratch (properties
        dict is empty), we fall back to the explicit fields (move, color,
        comment, is_correct).
        """
        parts = [";"]

        if node.properties:
            # --- Round-trip mode: serialize all stored properties ---
            # Properties that we handle specially (emitted from typed fields)
            # B/W = move, C = comment, BM = bad-move marker (from is_correct)
            # TE/IT = correct markers (replaced by is_correct logic)
            HANDLED = {"B", "W", "C", "BM", "TE", "IT"}

            # Move — prefer the node's typed fields (may have been edited)
            if node.move and node.color:
                parts.append(f"{node.color}[{node.move.to_sgf()}]")
            elif "B" in node.properties:
                parts.append(f"B[{node.properties['B']}]")
            elif "W" in node.properties:
                parts.append(f"W[{node.properties['W']}]")

            # Comment — prefer the node's typed field
            if node.comment:
                escaped = escape_sgf_value(node.comment)
                parts.append(f"C[{escaped}]")
            elif "C" in node.properties:
                escaped = escape_sgf_value(node.properties["C"])
                parts.append(f"C[{escaped}]")

            # Correctness markers
            if not node.is_correct:
                parts.append("BM[1]")
            elif "TE" in node.properties:
                parts.append(f"TE[{node.properties['TE']}]")
            elif "IT" in node.properties:
                parts.append(f"IT[{node.properties['IT']}]")

            # All other properties — preserved verbatim
            for key, value in node.properties.items():
                if key in HANDLED:
                    continue
                # Multi-value properties (e.g., LB[pm:16],LB[om:A])
                # are stored as comma-joined in the parser.  For
                # properties that use multiple [] values per SGF spec,
                # split and re-wrap each value.
                if key in _MULTI_VALUE_PROPERTIES and "," in value:
                    for sub in value.split(","):
                        parts.append(f"{key}[{sub}]")
                else:
                    parts.append(f"{key}[{value}]")
        else:
            # --- Build-from-scratch mode: use typed fields only ---
            if node.move and node.color:
                parts.append(f"{node.color}[{node.move.to_sgf()}]")

            if node.comment:
                escaped = escape_sgf_value(node.comment)
                parts.append(f"C[{escaped}]")

            if not node.is_correct:
                parts.append("BM[1]")

        return "".join(parts)

    def to_tree(self) -> SgfTree:
        """Convert builder state to SgfTree object."""
        return SgfTree(
            board_size=self.board_size,
            black_stones=list(self.black_stones),
            white_stones=list(self.white_stones),
            player_to_move=self.player_to_move,
            solution_tree=self.solution_tree,
            metadata=dict(self.metadata),
            root_comment=self.root_comment,
            yengo_props=YenGoProperties(
                level=self.yengo_props.level,
                level_slug=self.yengo_props.level_slug,
                tags=list(self.yengo_props.tags),
                hint_texts=list(self.yengo_props.hint_texts),
                version=self.yengo_props.version,
                run_id=self.yengo_props.run_id,
                quality=self.yengo_props.quality,
                complexity=self.yengo_props.complexity,
                source=self.yengo_props.source,
                collections=list(self.yengo_props.collections),
                corner=self.yengo_props.corner,
                ko_context=self.yengo_props.ko_context,
                move_order=self.yengo_props.move_order,
                refutation_count=self.yengo_props.refutation_count,
            ),
            raw_sgf=self.build(),
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def publish_sgf(tree: SgfTree) -> str:
    """Serialize an SgfTree back to an SGF string.

    Shortcut for ``SGFBuilder.from_tree(tree).build()``.

    Args:
        tree: Parsed SgfTree object.

    Returns:
        SGF string.
    """
    return SGFBuilder.from_tree(tree).build()
