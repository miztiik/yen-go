"""
Hint generation for puzzle enrichment.

Generates progressive hints with pedagogical design reviewed by 1P Go professionals.

Hint Philosophy (Cho Chikun, Lee Changho, Fujisawa Shuko):
-----------------------------------------------------------
1. YH1 (Technique): Name the concept — "Try a net (geta)."
   Naming the technique gives the student a framework for reading.

2. YH2 (Reasoning): Explain WHY + warn wrong approach.
   "Direct capture doesn't work — think about surrounding loosely."

3. YH3 (Coordinate): Give the answer + technique outcome.
   "The first move is at {!cg}. This creates an inescapable enclosure."

Design Principles:
- Technique → Reasoning → Coordinate (concept first, answer last)
- Do No Harm: misleading hint worse than no hint
- Liberty analysis gated to capture-race/ko only
- Tag-driven: tagger assigns tags, hint generator maps to text
- Transform-invariant: role-based labels, {!xy} coordinate tokens
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.enrichment.config import EnrichmentConfig
from backend.puzzle_manager.core.primitives import Color, Point

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode

logger = logging.getLogger("enrichment.hints")


@dataclass
class LibertyAnalysis:
    """Internal analysis of liberty situation for hints.

    NOT exposed as public API - only used to generate richer reasoning hints
    for capture-race and ko puzzles, and for atari detection.
    """

    player_liberties: int  # Liberties of player's weakest group
    opponent_liberties: int  # Liberties of opponent's weakest group
    player_in_atari: bool  # Player has a group in atari
    opponent_in_atari: bool  # Opponent has a group in atari
    player_weak_group_size: int  # Size of player's weakest group
    opponent_weak_group_size: int  # Size of opponent's weakest group


# Tags where liberty analysis is pedagogically appropriate
SEMEAI_KO_TAGS = frozenset({"capture-race", "ko"})


# Tag priority ordering: most specific tag drives the hint
TAG_PRIORITY: list[frozenset[str]] = [
    # Priority 1 (highest): Specific tesuji
    frozenset({"snapback", "double-atari", "connect-and-die", "under-the-stones", "clamp"}),
    # Priority 2: Tactical techniques
    frozenset({"ladder", "net", "throw-in", "sacrifice", "nakade", "vital-point"}),
    # Priority 3: General techniques
    frozenset({"capture-race", "liberty-shortage", "eye-shape", "connection", "cutting", "escape"}),
    # Priority 4 (lowest): Category labels
    frozenset({
        "life-and-death", "living", "ko", "seki", "shape", "corner",
        "endgame", "tesuji", "joseki", "fuseki", "dead-shapes",
    }),
]


# Technique-specific outcome text for YH3 coordinate hints
COORDINATE_TEMPLATES: dict[str, str] = {
    "ladder": "This begins the chase.",
    "net": "This creates an inescapable enclosure.",
    "snapback": "Let them capture — then take back more.",
    "sacrifice": "This stone will be sacrificed for the greater good.",
    "throw-in": "This stone will be sacrificed for the greater good.",
    "nakade": "This is the vital point inside.",
    "vital-point": "This is the vital point inside.",
    "life-and-death": "This determines the group's fate.",
    "living": "This determines the group's fate.",
    "ko": "This starts the ko fight.",
    "double-atari": "Two groups are threatened at once.",
    "connect-and-die": "The opponent's connection becomes a trap.",
    "under-the-stones": "After the capture, play in the space below.",
    "escape": "This is the escape route.",
    "connection": "This links the groups.",
    "cutting": "This separates the opponent's stones.",
    "capture-race": "Win the liberty race.",
}


class HintGenerator:
    """Generates pedagogical hints for puzzles.

    Hint Philosophy (reviewed by 1P Go professionals):
    --------------------------------------------------
    1. YH1 (Technique): Name the concept to apply
    2. YH2 (Reasoning): Explain WHY + warn about wrong approach
    3. YH3 (Coordinate): Give the answer + technique-specific outcome

    Tag-driven design: tagger assigns tags, hint generator maps tags to
    pedagogical content. Fix the tagger for wrong tags, fix TECHNIQUE_HINTS
    for wrong text.
    """

    # Technique descriptions with pedagogical reasoning templates
    # Format: (technique_hint, reasoning_template)
    # All 28 tags from config/tags.json MUST have entries
    TECHNIQUE_HINTS: dict[str, tuple[str, str]] = {
        # --- Priority 1: Specific tesuji ---
        "snapback": (
            "Consider a snapback sequence",
            "Letting opponent capture leads to recapture.",
        ),
        "double-atari": (
            "Look for a double atari",
            "One move threatening two groups.",
        ),
        "connect-and-die": (
            "What happens if the opponent connects?",
            "Connecting leads to a larger capture.",
        ),
        "under-the-stones": (
            "Think about playing under the stones",
            "After the capture, the vacated space becomes crucial.",
        ),
        "clamp": (
            "Consider a clamp (hasami-tsuke)",
            "Attach inside to reduce eye space.",
        ),
        # --- Priority 2: Tactical techniques ---
        "ladder": (
            "Look for a ladder (shicho) pattern",
            "The opponent can only escape in one direction.",
        ),
        "net": (
            "Try surrounding loosely with a net (geta)",
            "Direct capture isn't possible, but escape routes are limited.",
        ),
        "throw-in": (
            "A throw-in might be useful",
            "Sacrificing inside reduces eye space.",
        ),
        "sacrifice": (
            "Consider sacrificing stones",
            "After the sacrifice, the opponent's shape collapses.",
        ),
        "nakade": (
            "Look for a nakade — the vital point inside",
            "Playing the vital point prevents two eyes.",
        ),
        "vital-point": (
            "Find the vital point of the shape",
            "One move determines whether the group lives or dies.",
        ),
        # --- Priority 3: General techniques ---
        "capture-race": (
            "This is a capturing race (semeai)",
            "Compare liberties: the group with fewer will be captured first.",
        ),
        "liberty-shortage": (
            "Look for a liberty shortage (damezumari)",
            "Reducing liberties forces bad shape.",
        ),
        "eye-shape": (
            "Focus on the eye shape",
            "Can the group make two real eyes, or is one false?",
        ),
        "connection": (
            "Try to connect your groups",
            "Find the move that links both groups so neither can be cut.",
        ),
        "cutting": (
            "Look for a cutting point",
            "After separating, can the opponent save both halves?",
        ),
        "escape": (
            "Look for an escape route",
            "Which direction offers the best escape? Consider where friendly stones are.",
        ),
        # --- Priority 4: Category labels ---
        "life-and-death": (
            "This is a life-and-death problem",
            "Can the group make two independent eyes, or can you prevent it?",
        ),
        "living": (
            "Your group needs to live",
            "Find the move that guarantees two eyes.",
        ),
        "ko": (
            "This involves a ko fight",
            "Identify the ko — then look for local threats to win it.",
        ),
        "seki": (
            "Mutual life may be the best outcome",
            "Neither side can attack without self-destruction.",
        ),
        "shape": (
            "Look for the most efficient shape",
            "Good shape maximizes liberties and eye potential.",
        ),
        "corner": (
            "Corner positions have special properties",
            "Reduced liberties and edge effects change the tactics.",
        ),
        "endgame": (
            "This is an endgame (yose) problem",
            "Which move gains the most points?",
        ),
        "tesuji": (
            "Look for a sharp tactical move",
            "There is a tesuji that changes the outcome.",
        ),
        "joseki": (
            "This tests joseki knowledge",
            "Find the standard continuation for this corner pattern.",
        ),
        "fuseki": (
            "Consider the whole-board balance",
            "Which area is most urgent to play?",
        ),
        "dead-shapes": (
            "Recognize the shape — is it already dead?",
            "Some shapes cannot make two eyes regardless of who plays first.",
        ),
        # --- Aliases (backward compatibility with old tagger keys) ---
        "squeeze": (
            "Look for a liberty shortage (damezumari)",
            "Reducing liberties forces bad shape.",
        ),
        "connect": (
            "Try to connect your groups",
            "Find the move that links both groups so neither can be cut.",
        ),
        "cut": (
            "Look for a cutting point",
            "After separating, can the opponent save both halves?",
        ),
        "capture": (
            "This is a capturing race (semeai)",
            "Compare liberties: the group with fewer will be captured first.",
        ),
    }

    def __init__(self, config: EnrichmentConfig) -> None:
        """Initialize hint generator.

        Args:
            config: Enrichment configuration.
        """
        self.config = config

    def _get_primary_tag(self, tags: list[str]) -> str | None:
        """Get highest-priority tag from tag list.

        Uses TAG_PRIORITY ordering: specific tesuji > tactical > general > category.

        Args:
            tags: List of technique tags.

        Returns:
            Highest-priority tag or None.
        """
        tag_set = {t.lower().replace("_", "-") for t in tags}
        for priority_group in TAG_PRIORITY:
            matches = tag_set & priority_group
            if matches:
                # Return first match (sorted for determinism)
                return sorted(matches)[0]
        # Fallback: return first tag that exists in TECHNIQUE_HINTS
        for tag in tags:
            tag_lower = tag.lower().replace("_", "-")
            if tag_lower in self.TECHNIQUE_HINTS:
                return tag_lower
        return None

    def _get_solution_depth(self, solution_tree: SolutionNode) -> int:
        """Get depth of solution (number of correct moves in main line).

        Returns:
            Number of sequential correct moves. 0 means no solution moves.
        """
        depth = 0
        node = solution_tree
        while node.children:
            correct_child = None
            for child in node.children:
                if child.is_correct and child.move:
                    correct_child = child
                    break
            if correct_child is None:
                # Try first child with a move as fallback
                for child in node.children:
                    if child.move:
                        correct_child = child
                        break
            if correct_child is None:
                break
            depth += 1
            node = correct_child
        return depth

    def generate_technique_hint(
        self,
        tags: list[str],
        game: SGFGame,
    ) -> str | None:
        """Generate technique identification hint (YH1).

        Names the concept the solver should apply. Uses tag priority
        to pick the most specific technique.

        When atari is detected and primary tag is NOT capture-race/ko,
        atari becomes a standalone technique hint.

        Args:
            tags: Puzzle technique tags.
            game: Parsed SGF game (for atari detection).

        Returns:
            YH1 technique hint string or None.
        """
        primary_tag = self._get_primary_tag(tags)

        # Check for atari situation (standalone hint for non-semeai/ko)
        if primary_tag not in SEMEAI_KO_TAGS:
            liberty_info = self._analyze_liberties(game)
            if liberty_info:
                if liberty_info.opponent_in_atari:
                    return "The opponent is in atari! Look for the capturing move."
                if liberty_info.player_in_atari:
                    return "Your group is in atari! Escape or make eyes immediately."

        # Use tag priority to find technique hint
        if primary_tag and primary_tag in self.TECHNIQUE_HINTS:
            base_hint, _ = self.TECHNIQUE_HINTS[primary_tag]
            return f"{base_hint}."

        return None

    def generate_reasoning_hint(
        self,
        tags: list[str],
        game: SGFGame,
    ) -> str | None:
        """Generate reasoning hint with technique explanation (YH2).

        Explains WHY the technique applies and warns about wrong approaches.
        Liberty analysis is only included for capture-race/ko puzzles.

        Args:
            tags: Puzzle technique tags.
            game: Parsed SGF game.

        Returns:
            YH2 reasoning hint string or None.
        """
        primary_tag = self._get_primary_tag(tags)
        if not primary_tag or primary_tag not in self.TECHNIQUE_HINTS:
            return None

        if not self.config.include_technique_reasoning:
            return None

        _, reasoning = self.TECHNIQUE_HINTS[primary_tag]
        hint = reasoning

        # Add liberty analysis ONLY for capture-race/ko (gated)
        if primary_tag in SEMEAI_KO_TAGS and self.config.include_liberty_analysis:
            liberty_info = self._analyze_liberties(game)
            if liberty_info:
                hint = self._enhance_reasoning_with_liberties(hint, liberty_info)

        return hint

    def generate_coordinate_hint(
        self,
        game: SGFGame,
        tags: list[str],
    ) -> str | None:
        """Generate coordinate hint with technique-specific outcome (YH3).

        Shows the first correct move. Depth-gated:
        - Depth 1: Suppressed (coordinate IS the answer)
        - Depth 2-3: Coordinate only
        - Depth 4+: Coordinate + technique outcome

        Args:
            game: Parsed SGF game.
            tags: Puzzle technique tags (for outcome template).

        Returns:
            YH3 coordinate hint string or None.
        """
        if not game.has_solution:
            return None

        # Depth gating (Fujisawa principle)
        depth = self._get_solution_depth(game.solution_tree)
        if depth <= 1:
            return None

        # Get first correct move
        first_move = self._get_first_correct_move(game.solution_tree)
        if not first_move:
            return None

        coord_str = self._point_to_token(first_move)
        hint = f"The first move is at {coord_str}."

        # Add technique-specific outcome for depth 4+
        if depth >= 4 and self.config.include_consequence:
            primary_tag = self._get_primary_tag(tags)
            if primary_tag and primary_tag in COORDINATE_TEMPLATES:
                outcome = COORDINATE_TEMPLATES[primary_tag]
                hint = f"The first move is at {coord_str}. {outcome}"

        return hint

    # === Backward-compatible aliases ===

    def generate_yh1(
        self,
        game: SGFGame,
        region_code: str | None = None,
    ) -> str:
        """Generate area hint (backward-compatible alias).

        .. deprecated::
            Use :meth:`generate_technique_hint` instead.

        Args:
            game: Parsed SGF game.
            region_code: Pre-computed region code (ignored in new design).

        Returns:
            YH1 hint string.
        """
        tags = game.yengo_props.tags if game.yengo_props else []
        result = self.generate_technique_hint(tags, game)
        return result if result else ""

    def generate_yh2(self, tags: list[str]) -> str | None:
        """Generate technique hint (backward-compatible alias).

        .. deprecated::
            Use :meth:`generate_reasoning_hint` instead.

        Args:
            tags: Puzzle technique tags.

        Returns:
            YH2 hint string or None if no matching technique.
        """
        primary_tag = self._get_primary_tag(tags)
        if not primary_tag or primary_tag not in self.TECHNIQUE_HINTS:
            # Fallback for unrecognized tags
            for tag in (tags or []):
                tag_lower = tag.lower().replace("_", "-")
                if tag_lower in self.TECHNIQUE_HINTS:
                    base_hint, reasoning = self.TECHNIQUE_HINTS[tag_lower]
                    if self.config.include_technique_reasoning:
                        return f"{base_hint}. {reasoning}"
                    return base_hint
            return None
        base_hint, reasoning = self.TECHNIQUE_HINTS[primary_tag]
        if self.config.include_technique_reasoning:
            return f"{base_hint}. {reasoning}"
        return base_hint

    def generate_yh3(self, game: SGFGame) -> str | None:
        """Generate solution hint (backward-compatible alias).

        .. deprecated::
            Use :meth:`generate_coordinate_hint` instead.

        Args:
            game: Parsed SGF game.

        Returns:
            YH3 hint string or None if no solution.
        """
        tags = game.yengo_props.tags if game.yengo_props else []
        return self.generate_coordinate_hint(game, tags)

    # === Internal helpers ===

    def _analyze_liberties(self, game: SGFGame) -> LibertyAnalysis | None:
        """Internal: Analyze liberties for hint enrichment.

        Finds the weakest groups for both player and opponent.

        Args:
            game: Parsed SGF game.

        Returns:
            LibertyAnalysis or None if analysis fails.
        """
        try:
            if not (game.black_stones or game.white_stones):
                return None

            # Build board position
            board = Board(game.board_size)
            board.setup_position(game.black_stones, game.white_stones)

            # Determine colors
            player_color = game.player_to_move
            player_color.opponent()

            # Track weakest groups
            player_min_libs = float("inf")
            player_weak_size = 0
            opponent_min_libs = float("inf")
            opponent_weak_size = 0
            player_in_atari = False
            opponent_in_atari = False

            analyzed_points: set[Point] = set()

            # Analyze all stones
            all_stones = game.black_stones + game.white_stones
            for point in all_stones:
                if point in analyzed_points:
                    continue

                group = board.get_group(point)
                if group is None:
                    continue

                analyzed_points.update(group.stones)
                libs = len(group.liberties)

                if group.color == player_color:
                    if libs < player_min_libs:
                        player_min_libs = libs
                        player_weak_size = len(group.stones)
                    if libs == 1:
                        player_in_atari = True
                else:
                    if libs < opponent_min_libs:
                        opponent_min_libs = libs
                        opponent_weak_size = len(group.stones)
                    if libs == 1:
                        opponent_in_atari = True

            # Handle case where one side has no stones
            if player_min_libs == float("inf"):
                player_min_libs = 0
            if opponent_min_libs == float("inf"):
                opponent_min_libs = 0

            return LibertyAnalysis(
                player_liberties=int(player_min_libs),
                opponent_liberties=int(opponent_min_libs),
                player_in_atari=player_in_atari,
                opponent_in_atari=opponent_in_atari,
                player_weak_group_size=player_weak_size,
                opponent_weak_group_size=opponent_weak_size,
            )

        except Exception as e:
            logger.debug(f"Liberty analysis failed: {e}")
            return None

    def _enhance_reasoning_with_liberties(
        self,
        base_reasoning: str,
        liberty_info: LibertyAnalysis,
    ) -> str:
        """Add liberty information to reasoning hint (capture-race/ko only).

        Uses role-based labels ("Your" / "the opponent's") instead of
        color names so hints remain correct when the frontend swaps
        stone colors via board transforms.

        Args:
            base_reasoning: Base reasoning string.
            liberty_info: Liberty analysis result.

        Returns:
            Enhanced reasoning string.
        """
        # Prioritize atari situations
        if liberty_info.opponent_in_atari:
            return f"{base_reasoning} The opponent is in atari!"

        if liberty_info.player_in_atari:
            return f"{base_reasoning} Your group is in atari - act fast!"

        # Liberty race prompt
        if liberty_info.player_liberties > 0 and liberty_info.opponent_liberties > 0:
            if liberty_info.player_liberties != liberty_info.opponent_liberties:
                return (
                    f"{base_reasoning} Your weakest group has "
                    f"{liberty_info.player_liberties} liberties, "
                    f"the opponent's has {liberty_info.opponent_liberties} — "
                    f"who needs to act first?"
                )

        return base_reasoning

    def _enhance_hint_with_liberties(
        self,
        base_hint: str,
        liberty_info: LibertyAnalysis,
        player_color: Color,
    ) -> str:
        """Add liberty information to the base hint.

        .. deprecated::
            Use :meth:`_enhance_reasoning_with_liberties` instead.

        Args:
            base_hint: Base hint string.
            liberty_info: Liberty analysis result.
            player_color: Color of player to move (unused after role-based migration).

        Returns:
            Enhanced hint string.
        """
        return self._enhance_reasoning_with_liberties(base_hint, liberty_info)

    def _get_first_correct_move(self, solution_tree: SolutionNode) -> Point | None:
        """Get the first correct move from solution tree.

        Args:
            solution_tree: Root of solution tree.

        Returns:
            First correct move point or None.
        """
        for child in solution_tree.children:
            if child.is_correct and child.move:
                return child.move

        # Fallback: any move
        if solution_tree.children:
            first = solution_tree.children[0]
            if first.move:
                return first.move

        return None

    def _get_refutation_consequence(self, game: SGFGame) -> str | None:
        """Get consequence text for wrong moves.

        .. deprecated::
            Wrong-approach warnings are now part of the reasoning hint (YH2).
            Kept for backward compatibility.

        Args:
            game: Parsed SGF game.

        Returns:
            Consequence text or None.
        """
        if not game.has_solution:
            return None

        # Find refutation branch (wrong first move)
        for child in game.solution_tree.children:
            if not child.is_correct and child.move:
                wrong_move = self._point_to_token(child.move)

                # Try to get outcome from comments or child moves
                if child.comment:
                    return f"If you play {wrong_move}, {child.comment.lower()}"

                # Check for opponent's response
                if child.children:
                    return f"If you play {wrong_move}, the opponent can respond."

                return f"Playing {wrong_move} is incorrect."

        return None

    def _point_to_human_readable(self, point: Point, board_size: int) -> str:
        """Convert point to human-readable coordinate.

        Uses standard Go notation: A-T (excluding I) for columns, 1-19 for rows.

        .. deprecated::
            Use :meth:`_point_to_token` instead. Human-readable coordinates
            break when board transforms (flip/rotate) are applied in the
            frontend. Tokens are resolved after transforms.

        Args:
            point: Board point.
            board_size: Board size.

        Returns:
            Human-readable coordinate (e.g., "C5", "Q16").
        """
        # Column: A-T, skipping I
        col_letters = "ABCDEFGHJKLMNOPQRST"
        if point.x < len(col_letters):
            col = col_letters[point.x]
        else:
            col = chr(ord("A") + point.x)

        # Row: 1 from bottom, so invert y
        row = board_size - point.y

        return f"{col}{row}"

    def _point_to_token(self, point: Point) -> str:
        """Convert point to {!xy} token for frontend resolution.

        Token format: {!<col><row>} where col and row are SGF-style
        lowercase letters (a=0, b=1, ..., s=18).

        The frontend resolves these tokens to human-readable coordinates
        after applying board transforms, ensuring hints remain correct
        regardless of flip/rotation state.

        Args:
            point: Board point.

        Returns:
            Token string, e.g., "{!bb}" for Point(1, 1).
        """
        col = chr(ord("a") + point.x)
        row = chr(ord("a") + point.y)
        return f"{{!{col}{row}}}"
