"""
SGF builder for creating puzzle files.

Builds SGF content from primitives with YenGo custom properties support.
"""

from backend.puzzle_manager.core.constants import MAX_BOARD_SIZE, MIN_BOARD_SIZE, SLUG_TO_LEVEL
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode, YenGoProperties
from backend.puzzle_manager.core.sgf_utils import escape_sgf_value
from backend.puzzle_manager.core.text_cleaner import standardize_move_comment
from backend.puzzle_manager.core.trace_utils import build_pipeline_meta
from backend.puzzle_manager.exceptions import SGFBuildError


class SGFBuilder:
    """Builder for creating SGF content.

    Usage:
        builder = SGFBuilder(board_size=19)
        builder.add_black_stone(Point(3, 3))
        builder.add_white_stone(Point(3, 4))
        builder.set_player_to_move(Color.BLACK)
        builder.set_level(3)
        builder.add_tag("life-and-death")
        builder.add_solution_move(Color.BLACK, Point(2, 3))
        sgf = builder.build()
    """

    def __init__(self, board_size: int = 19) -> None:
        """Initialize builder with board size.

        Args:
            board_size: Board size (5–19 inclusive).

        Raises:
            SGFBuildError: If board size is outside [5, 19].
        """
        if not (MIN_BOARD_SIZE <= board_size <= MAX_BOARD_SIZE):
            raise SGFBuildError(f"Invalid board size: {board_size}")

        self.board_size = board_size
        self.black_stones: list[Point] = []
        self.white_stones: list[Point] = []
        self.player_to_move: Color = Color.BLACK
        self.metadata: dict[str, str] = {}
        self.yengo_props = YenGoProperties()
        self.solution_tree = SolutionNode()
        self._current_node = self.solution_tree

    @classmethod
    def from_game(cls, game: SGFGame) -> "SGFBuilder":
        """Create builder from existing SGFGame.

        This is the inverse of to_game() - it creates a builder initialized
        with the state from a parsed SGF game, allowing modification and
        re-serialization.

        Args:
            game: Parsed SGFGame object.

        Returns:
            SGFBuilder initialized with game state.

        Example:
            game = parse_sgf(sgf_content)
            builder = SGFBuilder.from_game(game)
            builder.add_tags(["new-tag"])
            new_sgf = builder.build()
        """
        builder = cls(board_size=game.board_size)

        # Copy stones
        builder.black_stones = list(game.black_stones)
        builder.white_stones = list(game.white_stones)

        # Copy player to move
        builder.player_to_move = game.player_to_move

        # Copy metadata
        builder.metadata = dict(game.metadata)

        # Copy solution tree (use the same object, as SolutionNode is mutable)
        builder.solution_tree = game.solution_tree
        builder._current_node = builder.solution_tree

        # Copy YenGo properties
        if game.yengo_props:
            builder.yengo_props = YenGoProperties(
                level=game.yengo_props.level,
                level_slug=game.yengo_props.level_slug,
                tags=list(game.yengo_props.tags),
                hint_texts=list(game.yengo_props.hint_texts),
                version=game.yengo_props.version,
                run_id=game.yengo_props.run_id,
                quality=game.yengo_props.quality,
                complexity=game.yengo_props.complexity,
                source=game.yengo_props.source,
                collections=list(game.yengo_props.collections),
                collection_sequences=dict(game.yengo_props.collection_sequences),
                corner=game.yengo_props.corner,
                ko_context=game.yengo_props.ko_context,
                move_order=game.yengo_props.move_order,
                refutation_count=game.yengo_props.refutation_count,
                pipeline_meta=game.yengo_props.pipeline_meta,
            )

        return builder

    def add_black_stone(self, point: Point) -> "SGFBuilder":
        """Add a black stone to initial position."""
        self.black_stones.append(point)
        return self

    def add_black_stones(self, points: list[Point]) -> "SGFBuilder":
        """Add multiple black stones to initial position."""
        self.black_stones.extend(points)
        return self

    def add_white_stone(self, point: Point) -> "SGFBuilder":
        """Add a white stone to initial position."""
        self.white_stones.append(point)
        return self

    def add_white_stones(self, points: list[Point]) -> "SGFBuilder":
        """Add multiple white stones to initial position."""
        self.white_stones.extend(points)
        return self

    def set_player_to_move(self, color: Color) -> "SGFBuilder":
        """Set the player to move."""
        self.player_to_move = color
        return self

    def set_metadata(self, key: str, value: str) -> "SGFBuilder":
        """Set metadata property."""
        self.metadata[key] = value
        return self

    def set_game_name(self, name: str) -> "SGFBuilder":
        """Set game name (GN property).

        Note: In v8, GN must follow format YENGO-{16-hex-chars}.
        Use set_yengo_game_name() to set a standardized name.
        """
        return self.set_metadata("GN", name)

    def set_yengo_game_name(self, hex_hash: str) -> "SGFBuilder":
        """Set standardized YenGo game name (GN property).

        Args:
            hex_hash: 16-character hex string (usually from filename).

        Returns:
            Self for chaining.
        """
        if len(hex_hash) != 16 or not all(c in '0123456789abcdef' for c in hex_hash.lower()):
            raise SGFBuildError(f"hex_hash must be 16 hex chars, got: {hex_hash}")
        return self.set_metadata("GN", f"YENGO-{hex_hash.lower()}")

    def set_comment(self, comment: str) -> "SGFBuilder":
        """Set game comment (GC property)."""
        return self.set_metadata("GC", comment)

    def set_level(self, level: int) -> "SGFBuilder":
        """Set YenGo difficulty level (1-9).

        Note: This sets the numeric level. Use set_level_slug() for the new
        slug-based format (per Spec 036 T072-T074).
        """
        if not 1 <= level <= 9:
            raise SGFBuildError(f"Level must be 1-9, got {level}")
        self.yengo_props.level = level
        return self

    def set_level_slug(self, slug: str, sublevel: int | None = None) -> "SGFBuilder":
        """Set YenGo difficulty level as slug format.

        Args:
            slug: Level slug (e.g., "beginner", "intermediate").
            sublevel: Optional sub-level 1-3.

        Returns:
            Self for chaining.
        """
        valid_slugs = [
            "novice", "beginner", "elementary", "intermediate",
            "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
        ]
        if slug not in valid_slugs:
            raise SGFBuildError(f"Invalid level slug: {slug}")
        if sublevel is not None and not 1 <= sublevel <= 3:
            raise SGFBuildError(f"Sub-level must be 1-3, got {sublevel}")

        self.yengo_props.level_slug = slug
        if sublevel:
            self.yengo_props.level_slug = f"{slug}:{sublevel}"

        # Also set numeric level for backward compatibility using shared constants
        self.yengo_props.level = SLUG_TO_LEVEL.get(slug)
        return self

    def set_version(self, version: int) -> "SGFBuilder":
        """Set schema version (YV property).

        Args:
            version: Schema version number (e.g., 5).

        Returns:
            Self for chaining.
        """
        if version < 1:
            raise SGFBuildError(f"Version must be positive, got {version}")
        self.yengo_props.version = version
        return self

    def set_run_id(self, run_id: str) -> "SGFBuilder":
        """Set pipeline run ID (stored in YM pipeline metadata).

        Args:
            run_id: Run ID in YYYYMMDD-xxxxxxxx format (17 chars, date + 8 hex).

        Returns:
            Self for chaining.
        """
        import re
        # Pattern: YYYYMMDD-xxxxxxxx only
        pattern = r"^[0-9]{8}-[a-f0-9]{8}$"
        if not re.match(pattern, run_id):
            raise SGFBuildError(
                f"Run ID must be in YYYYMMDD-xxxxxxxx format, got: {run_id}"
            )
        self.yengo_props.run_id = run_id
        return self

    def set_quality(self, quality: str) -> "SGFBuilder":
        """Set quality metrics (YQ property).

        Args:
            quality: Quality string (e.g., "q:3;rc:2;hc:1").

        Returns:
            Self for chaining.
        """
        # Basic validation of format
        if not quality.startswith("q:"):
            raise SGFBuildError(f"Quality must start with 'q:', got {quality}")
        self.yengo_props.quality = quality
        return self

    def set_complexity(self, complexity: str) -> "SGFBuilder":
        """Set complexity metrics (YX property).

        Args:
            complexity: Complexity string (e.g., "d:5;r:13;s:24;u:1").

        Returns:
            Self for chaining.
        """
        # Basic validation of format
        if not complexity.startswith("d:"):
            raise SGFBuildError(f"Complexity must start with 'd:', got {complexity}")
        self.yengo_props.complexity = complexity
        return self

    def set_source(self, source_id: str) -> "SGFBuilder":
        """Set source adapter ID (stored in YM pipeline metadata).

        Records which adapter ingested this puzzle, enabling accurate
        source tracking in publish logs even when stages run separately.

        Args:
            source_id: Source adapter ID (e.g., "sanderland", "kisvadim").

        Returns:
            Self for chaining.
        """
        self.yengo_props.source = source_id
        return self

    def set_corner(self, corner: str) -> "SGFBuilder":
        """Set corner/region position (YC property).

        Args:
            corner: Position value (TL, TR, BL, BR, C, E).

        Returns:
            Self for chaining.
        """
        self.yengo_props.corner = corner
        return self

    def set_ko_context(self, ko_context: str) -> "SGFBuilder":
        """Set ko context (YK property).

        Args:
            ko_context: Ko type (simple, superko:positional, superko:situational).

        Returns:
            Self for chaining.
        """
        self.yengo_props.ko_context = ko_context
        return self

    def set_move_order(self, move_order: str) -> "SGFBuilder":
        """Set move order flexibility (YO property).

        Args:
            move_order: Order type (strict, flexible, miai).

        Returns:
            Self for chaining.
        """
        self.yengo_props.move_order = move_order
        return self

    def set_refutation_count(self, refutation_count: str) -> "SGFBuilder":
        """Set refutation moves (YR property).

        Note: Despite the method name, YR stores comma-separated SGF coordinates
        of wrong first moves (e.g., "cd,de"), not a numeric count. The actual
        refutation count is the ``rc`` field in YQ. Method name retained for
        backward compatibility.

        Args:
            refutation_count: Comma-separated SGF coordinates of wrong first moves.

        Returns:
            Self for chaining.
        """
        self.yengo_props.refutation_count = refutation_count
        return self

    def set_pipeline_meta(
        self,
        trace_id: str,
        original_filename: str = "",
        run_id: str = "",
    ) -> "SGFBuilder":
        """Set pipeline metadata (YM property, v13).

        Consolidates trace_id, original_filename, and run_id into a
        single JSON property. Source adapter ID is tracked via
        context.source_id and publish log, not embedded in YM.

        Args:
            trace_id: 16-char hex trace ID.
            original_filename: Optional original source filename.
            run_id: Pipeline run ID (e.g., "20260220-abc12345").

        Returns:
            Self for chaining.
        """
        self.yengo_props.pipeline_meta = build_pipeline_meta(
            trace_id, original_filename, run_id
        )
        # Also populate the convenience field for internal use
        if run_id:
            self.yengo_props.run_id = run_id
        return self

    def add_tag(self, tag: str) -> "SGFBuilder":
        """Add a technique tag."""
        if tag not in self.yengo_props.tags:
            self.yengo_props.tags.append(tag)
        return self

    def add_tags(self, tags: list[str]) -> "SGFBuilder":
        """Add multiple technique tags."""
        for tag in tags:
            self.add_tag(tag)
        return self

    def add_collection(self, slug: str) -> "SGFBuilder":
        """Add a collection membership (YL property, v10).

        Args:
            slug: Collection slug from config/collections.json.

        Returns:
            Self for chaining.
        """
        if slug not in self.yengo_props.collections:
            self.yengo_props.collections.append(slug)
        return self

    def set_collections(self, slugs: list[str]) -> "SGFBuilder":
        """Set collection memberships (YL property, v10).

        Args:
            slugs: List of collection slugs from config/collections.json.

        Returns:
            Self for chaining.
        """
        self.yengo_props.collections = list(slugs)
        return self

    def add_hints(self, hints: list[str]) -> "SGFBuilder":
        """Add compact text hints (YH property, v8 format).

        Args:
            hints: List of hint strings in pedagogical order (1-3 items).
                  Only non-empty hints should be passed.

        Returns:
            Self for chaining.

        Example:
            builder.add_hints([
                "Focus on corner. White has 2 libs.",
                "Look for ladder.",
                "First move is C5."
            ])
            # Produces: YH[Focus on corner. White has 2 libs.|Look for ladder.|First move is C5.]

        Note: YH1/YH2/YH3 are REMOVED in v8 - only compact format supported.
        """
        # Filter empty strings
        non_empty = [h.strip() for h in hints if h and h.strip()]
        self.yengo_props.hint_texts = non_empty
        return self

    def add_solution_move(
        self,
        color: Color,
        point: Point,
        comment: str = "",
        is_correct: bool = True,
    ) -> "SGFBuilder":
        """Add a move to the solution tree.

        Adds to the current node's children and moves to the new node.
        """
        node = SolutionNode(
            move=point,
            color=color,
            comment=comment,
            is_correct=is_correct,
        )
        self._current_node.add_child(node)
        self._current_node = node
        return self

    def add_variation(self) -> "SGFBuilder":
        """Start a new variation from the parent node."""
        # Go back to parent (root for now)
        self._current_node = self.solution_tree
        return self

    def back_to_root(self) -> "SGFBuilder":
        """Return to root for adding another variation."""
        self._current_node = self.solution_tree
        return self

    def build(self) -> str:
        """Build SGF string.

        Returns:
            Complete SGF string.
        """
        parts = ["(;"]

        # Root properties
        parts.append(f"SZ[{self.board_size}]")

        # File format
        parts.append("FF[4]")
        parts.append("GM[1]")

        # Player to move
        if self.player_to_move:
            parts.append(f"PL[{self.player_to_move}]")

        # Metadata
        # Markup properties (LB, TR, SQ, CR, MA) use multi-value bracket
        # format: LB[ab:1][cd:A] instead of LB[ab:1,cd:A].
        _MULTI_VALUE_PROPS = {"LB", "TR", "SQ", "CR", "MA"}
        for key, value in self.metadata.items():
            if key in _MULTI_VALUE_PROPS:
                values = value.split(",")
                brackets = "".join(f"[{v}]" for v in values)
                parts.append(f"{key}{brackets}")
            else:
                escaped = escape_sgf_value(value)
                parts.append(f"{key}[{escaped}]")

        # YenGo properties (Schema v14) — alphabetical by second character
        # YC: Corner/region position
        if self.yengo_props.corner:
            parts.append(f"YC[{self.yengo_props.corner}]")

        # YG: Difficulty level - prefer slug format, fall back to int
        if self.yengo_props.level_slug:
            parts.append(f"YG[{self.yengo_props.level_slug}]")
        elif self.yengo_props.level is not None:
            parts.append(f"YG[{self.yengo_props.level}]")

        # YH: Compact text hints (v8 format only)
        if self.yengo_props.hint_texts:
            hint_string = "|".join(self.yengo_props.hint_texts)
            escaped = escape_sgf_value(hint_string)
            parts.append(f"YH[{escaped}]")

        # YK: Ko context
        if self.yengo_props.ko_context:
            parts.append(f"YK[{self.yengo_props.ko_context}]")

        # YL: Collection membership (with optional chapter/position sequences)
        if self.yengo_props.collections:
            entries = []
            for slug in sorted(set(self.yengo_props.collections)):
                if slug in self.yengo_props.collection_sequences:
                    chapter, position = self.yengo_props.collection_sequences[slug]
                    if chapter:
                        entries.append(f"{slug}:{chapter}/{position}")
                    else:
                        entries.append(f"{slug}:{position}")
                else:
                    entries.append(slug)
            parts.append(f"YL[{','.join(entries)}]")

        # YM: Pipeline metadata (JSON — trace_id + run_id)
        # Build YM from component fields if not already set
        if not self.yengo_props.pipeline_meta:
            from backend.puzzle_manager.core.trace_utils import build_pipeline_meta as _build_ym
            if self.yengo_props.run_id:
                self.yengo_props.pipeline_meta = _build_ym(
                    trace_id="",
                    run_id=self.yengo_props.run_id or "",
                )
        if self.yengo_props.pipeline_meta:
            escaped = escape_sgf_value(self.yengo_props.pipeline_meta)
            parts.append(f"YM[{escaped}]")

        # YO: Move order
        if self.yengo_props.move_order:
            parts.append(f"YO[{self.yengo_props.move_order}]")

        # YQ: Quality metrics
        if self.yengo_props.quality:
            parts.append(f"YQ[{self.yengo_props.quality}]")

        # YR: Refutation moves (wrong first-move SGF coords, comma-separated)
        if self.yengo_props.refutation_count:
            parts.append(f"YR[{self.yengo_props.refutation_count}]")

        # YT: Tags (comma-separated, sorted)
        if self.yengo_props.tags:
            tags_str = ",".join(self.yengo_props.tags)
            parts.append(f"YT[{tags_str}]")

        # YV: Schema version
        if self.yengo_props.version is not None:
            parts.append(f"YV[{self.yengo_props.version}]")

        # YX: Complexity metrics
        if self.yengo_props.complexity:
            parts.append(f"YX[{self.yengo_props.complexity}]")

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

    def _build_tree(self, node: SolutionNode) -> str:
        """Build SGF string for solution tree."""
        if not node.children:
            return ""

        parts = []

        if len(node.children) == 1:
            # Single variation - no parens needed
            child = node.children[0]
            # Step 6: single first-level move auto-inferred correctness
            is_sole_first_move = (node is self.solution_tree)
            parts.append(self._build_node(child, is_sole_first_move=is_sole_first_move))
            parts.append(self._build_tree(child))
        else:
            # Multiple variations - wrap each in parens
            for child in node.children:
                parts.append("(")
                parts.append(self._build_node(child))
                parts.append(self._build_tree(child))
                parts.append(")")

        return "".join(parts)

    def _build_node(self, node: SolutionNode, *, is_sole_first_move: bool = False) -> str:
        """Build SGF string for a single node.

        Applies comment standardization (Correct/Wrong prefix) and CJK stripping.
        For single first-level moves with no explicit signals, marks as
        'Correct {auto-inferred}'.
        """
        parts = [";"]

        if node.move and node.color:
            parts.append(f"{node.color}[{node.move.to_sgf()}]")

        # Determine the output comment
        comment = node.comment or ""

        # Step 6: Single-move auto-inferred correctness
        # If this is the sole first-level child, has no explicit comment,
        # has no BM marker (is_correct=True by default), and no explicit
        # SGF correctness markers — mark as auto-inferred.
        if (
            is_sole_first_move
            and node.is_correct
            and not comment.strip()
            and "TE" not in node.properties
            and "BM" not in node.properties
        ):
            comment = "Correct {auto-inferred}"
        elif comment.strip() or node.is_correct is not None:
            # Standardize comment: Correct/Wrong prefix + CJK stripping
            comment = standardize_move_comment(comment, node.is_correct)

        if comment:
            escaped = escape_sgf_value(comment)
            parts.append(f"C[{escaped}]")

        if not node.is_correct:
            parts.append("BM[1]")  # Bad move marker

        # Serialize SGF markup properties (board annotations).
        # These are visual annotations (labels, shapes) that help readers
        # understand the puzzle explanation. Preserved from source SGF.
        #
        # Note: TR (triangle) is NOT serialized from node.properties because
        # correctness.py uses "TR" in properties as a wrong-move marker
        # (Layer 1 inference). Re-emitting it would cause round-trip
        # correctness misclassification. If triangle markup is needed in
        # output, it should be stored in a dedicated field, not properties.
        _MARKUP_PROPS = ("LB", "SQ", "CR", "MA")
        for prop in _MARKUP_PROPS:
            if prop in node.properties:
                raw = node.properties[prop]
                # Multi-valued properties were joined with commas during
                # parsing. Split and wrap each value in brackets.
                values = raw.split(",")
                brackets = "".join(f"[{v}]" for v in values)
                parts.append(f"{prop}{brackets}")

        return "".join(parts)

    def to_game(self) -> SGFGame:
        """Convert builder state to SGFGame object."""
        return SGFGame(
            board_size=self.board_size,
            black_stones=list(self.black_stones),
            white_stones=list(self.white_stones),
            player_to_move=self.player_to_move,
            solution_tree=self.solution_tree,
            metadata=dict(self.metadata),
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
                pipeline_meta=self.yengo_props.pipeline_meta,
            ),
            raw_sgf=self.build(),
        )
