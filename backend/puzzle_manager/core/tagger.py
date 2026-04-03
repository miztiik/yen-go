"""
High-precision technique tagger for puzzles.

Design principle: **Precision over recall** — only tag when absolutely sure.
A misleading tag is worse than no tag. Empty tag list is a valid result.

Detection sources (ordered by reliability):
1. Comment keywords (exact word match)       → HIGH confidence
2. Japanese keywords (exact string match)    → HIGH confidence
3. Ko from Board ko_point after play()       → HIGH confidence
4. Ladder from 3+ move chase simulation      → HIGH confidence
5. Snapback from sacrifice-recapture shape   → HIGH confidence
6. Capture-race from localized semeai check  → MODERATE (emitted only at HIGH)

Tags that are ONLY detected from comments (too subtle for board heuristics):
- net, throw-in, sacrifice, nakade, eye-shape, connection, cutting
- double-atari, liberty-shortage, under-the-stones, seki, capture-race

No fallback: empty tag list is returned when no technique is confidently detected.
Source-provided tags are preserved separately by the analyze stage.

See docs/architecture/backend/tagging-strategy.md for full design rationale.
"""

from enum import IntEnum
from functools import lru_cache

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.primitives import Color, Move, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode
from backend.puzzle_manager.exceptions import TaggingError


class Confidence(IntEnum):
    """Evidence confidence level for tag detection.

    Only HIGH and CERTAIN tags are emitted. Lower levels are discarded.
    """

    NONE = 0        # No evidence
    WEAK = 1        # Heuristic match, likely false positive
    MODERATE = 2    # Pattern match but not independently verified
    HIGH = 3        # Comment keyword OR verified board pattern
    CERTAIN = 4     # Multiple signals agree (comment + board pattern)


# Minimum confidence required to emit a tag
_EMIT_THRESHOLD = Confidence.HIGH


@lru_cache(maxsize=1)
def get_approved_tags() -> set[str]:
    """Load approved tags from global config/tags.json (single source of truth).

    Returns:
        Set of approved tag IDs.
    """
    from backend.puzzle_manager.config.loader import ConfigLoader
    loader = ConfigLoader()
    return set(loader.get_tag_ids())


# Fallback tags if config cannot be loaded (for robustness)
_FALLBACK_TAGS = {
    "life-and-death",
    "ladder",
    "net",
    "snapback",
    "ko",
    "capture-race",
    "eye-shape",
    "throw-in",
    "sacrifice",
    "connection",
    "cutting",
    "tesuji",
    "nakade",
    "corner",
    "shape",
    "endgame",
    "joseki",
    "fuseki",
}


# ---------------------------------------------------------------------------
# Word-boundary helpers (no regex — plain string operations)
# ---------------------------------------------------------------------------

# Characters that are NOT part of a word (used for boundary detection)
_WORD_BOUNDARY_CHARS = frozenset(
    " \t\n\r,.;:!?()[]{}\"'/-+=<>@#$%^&*~`|\\0123456789"
)


def _is_boundary(char: str) -> bool:
    """Check if a character is a word boundary."""
    return char in _WORD_BOUNDARY_CHARS


def _contains_word(text: str, word: str) -> bool:
    """Check if text contains word as a whole word (not substring).

    Uses character-based boundary detection instead of regex.
    This prevents false positives like 'cut' matching 'execute'.

    Args:
        text: Text to search in (should be lowercased).
        word: Word to find (should be lowercased).

    Returns:
        True if word appears as a whole word in text.
    """
    start = 0
    word_len = len(word)
    text_len = len(text)

    while True:
        pos = text.find(word, start)
        if pos == -1:
            return False

        # Check left boundary
        left_ok = (pos == 0) or _is_boundary(text[pos - 1])
        # Check right boundary
        end_pos = pos + word_len
        right_ok = (end_pos == text_len) or _is_boundary(text[end_pos])

        if left_ok and right_ok:
            return True

        start = pos + 1


# ---------------------------------------------------------------------------
# English comment keyword → tag mapping
# ---------------------------------------------------------------------------

# Each entry: (keyword_to_find, tag_to_assign)
# Keywords are matched as whole words using _contains_word()
_ENGLISH_KEYWORD_TAGS: list[tuple[str, str]] = [
    ("ladder", "ladder"),
    ("net", "net"),
    ("geta", "net"),
    ("snapback", "snapback"),
    ("snap back", "snapback"),
    ("ko", "ko"),
    ("throw-in", "throw-in"),
    ("throw in", "throw-in"),
    ("sacrifice", "sacrifice"),
    ("eye", "eye-shape"),
    ("connect", "connection"),
    ("cut", "cutting"),
    ("squeeze", "liberty-shortage"),
    ("under the stones", "under-the-stones"),
    ("seki", "seki"),
    ("nakade", "nakade"),
    ("capture race", "capture-race"),
    ("semeai", "capture-race"),
]

# Special multi-word patterns checked separately
_DOUBLE_ATARI_WORDS = ("double", "atari")

# ---------------------------------------------------------------------------
# Japanese keyword → tag mapping
# ---------------------------------------------------------------------------

_JAPANESE_KEYWORD_TAGS: dict[str, str] = {
    "シチョウ": "ladder",
    "ゲタ": "net",
    "ウッテガエシ": "snapback",
    "コウ": "ko",
    "ホウリコミ": "throw-in",
    "セキ": "seki",
    "攻め合い": "capture-race",
    "ナカデ": "nakade",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_techniques(game: SGFGame) -> list[str]:
    """Detect techniques used in puzzle with high precision.

    Design: Only emits tags when confidence is HIGH or CERTAIN.
    No fallback — returns empty list if no technique is confidently detected.
    Source-provided tags (from adapters) are preserved separately by the
    analyze stage; this function only adds algorithmically-detected tags.

    Args:
        game: Parsed SGFGame object with original (unstripped) comments.

    Returns:
        Sorted list of detected technique tags. May be empty.

    Raises:
        TaggingError: If detection fails due to unexpected error.
    """
    try:
        evidence: dict[str, Confidence] = {}

        # Set up initial board position
        board = Board(game.board_size)
        board.setup_position(game.black_stones, game.white_stones)

        # Phase 1: Collect comment-based evidence (HIGH confidence)
        _collect_comment_evidence(game.solution_tree, evidence)

        # Phase 2: Collect board-based evidence (varies by technique)
        _collect_board_evidence(
            game.solution_tree, board, game.player_to_move, evidence
        )

        # Phase 3: Emit only tags at HIGH confidence or above
        tags = sorted(
            tag for tag, conf in evidence.items()
            if conf >= _EMIT_THRESHOLD
        )

        return tags

    except Exception as e:
        raise TaggingError(f"Failed to detect techniques: {e}") from e


# ---------------------------------------------------------------------------
# Phase 1: Comment-based evidence collection
# ---------------------------------------------------------------------------

def _collect_comment_evidence(
    node: SolutionNode,
    evidence: dict[str, Confidence],
) -> None:
    """Recursively scan solution tree comments for technique keywords.

    Comment keywords are HIGH confidence because the puzzle author
    explicitly named the technique.
    """
    if node.comment:
        _scan_comment(node.comment, evidence)

    for child in node.children:
        _collect_comment_evidence(child, evidence)


def _scan_comment(comment: str, evidence: dict[str, Confidence]) -> None:
    """Scan a single comment string for technique keywords."""
    comment_lower = comment.lower()

    # English whole-word matching
    for keyword, tag in _ENGLISH_KEYWORD_TAGS:
        if _contains_word(comment_lower, keyword):
            _upgrade_evidence(evidence, tag, Confidence.HIGH)

    # Double atari: requires both words present
    if (_contains_word(comment_lower, "double")
            and _contains_word(comment_lower, "atari")):
        _upgrade_evidence(evidence, "double-atari", Confidence.HIGH)

    # Japanese keywords (exact substring match — Japanese has no word boundaries)
    for keyword, tag in _JAPANESE_KEYWORD_TAGS.items():
        if keyword in comment:
            _upgrade_evidence(evidence, tag, Confidence.HIGH)


# ---------------------------------------------------------------------------
# Phase 2: Board-based evidence collection
# ---------------------------------------------------------------------------

def _collect_board_evidence(
    node: SolutionNode,
    board: Board,
    player: Color,
    evidence: dict[str, Confidence],
) -> None:
    """Recursively analyze solution tree for board-based technique evidence."""
    for child in node.children:
        if child.move and child.color:
            # Play the move and analyze captures
            try:
                new_board = board.copy()
                captured = new_board.play(Move.play(child.color, child.move))

                # Ko: Board's built-in ko detection (HIGH confidence)
                # Board.play() sets _ko_point when a genuine ko shape is
                # created (single stone captured AND capturer has exactly
                # 1 liberty). This is verified by Go rules.
                if new_board.ko_point is not None:
                    _upgrade_evidence(evidence, "ko", Confidence.HIGH)

                # Snapback: sacrifice-recapture shape (HIGH confidence)
                # After capturing 1 stone, if our group has exactly
                # 1 liberty AND >1 stone, opponent could recapture but
                # would lose >1 stone. That's snapback geometry.
                if len(captured) == 1:
                    our_group = new_board.get_group(child.move)
                    if (our_group
                            and len(our_group.liberties) == 1
                            and len(our_group.stones) > 1):
                        _upgrade_evidence(evidence, "snapback", Confidence.HIGH)

                # Capture-race: localized mutual low-liberty (MODERATE)
                # Only checks groups NEAR the capture site.
                if len(captured) > 1:
                    if _is_localized_semeai(
                        new_board, captured, child.move, child.color
                    ):
                        _upgrade_evidence(
                            evidence, "capture-race", Confidence.MODERATE
                        )

                # Ladder: verify by simulating 3+ chase moves
                _detect_verified_ladder(new_board, child.move, child.color, evidence)

                # Continue analyzing children
                _collect_board_evidence(
                    child, new_board, child.color.opponent(), evidence
                )

            except ValueError:
                # Invalid move (ko violation also signals ko presence)
                _upgrade_evidence(evidence, "ko", Confidence.MODERATE)
                _collect_board_evidence(child, board, player.opponent(), evidence)


# ---------------------------------------------------------------------------
# Board pattern detectors (high-precision implementations)
# ---------------------------------------------------------------------------

def _detect_verified_ladder(
    board: Board,
    move: Point,
    color: Color,
    evidence: dict[str, Confidence],
) -> None:
    """Detect ladder by simulating 3+ consecutive chase moves.

    A ladder is verified by reading out the chase: each step, the runner
    extends from atari, and the chaser puts them back in atari. If this
    continues for ≥3 iterations, it's a confirmed ladder.

    Pure Python using the Board class — no external tools needed.
    """
    neighbors = move.neighbors(board.size)

    for n in neighbors:
        if board.get(n) == color.opponent():
            group = board.get_group(n)
            if group and len(group.liberties) == 1:
                # Opponent group in atari — verify ladder chase
                if _verify_ladder_chase(board, group, color, min_chase=3):
                    _upgrade_evidence(evidence, "ladder", Confidence.HIGH)
                    return


def _verify_ladder_chase(
    board: Board,
    fleeing_group: object,
    chaser_color: Color,
    min_chase: int = 3,
) -> bool:
    """Simulate a ladder chase to verify it continues ≥min_chase atari moves.

    Pure Python implementation using Board.play() for each simulated move.
    No external solver or AI engine needed.

    Algorithm:
    1. Runner extends at their single liberty
    2. After extension, runner should have exactly 2 liberties
    3. Chaser plays at one of those liberties to create atari again
    4. Repeat — if chase continues for ≥min_chase iterations → ladder

    Args:
        board: Current board state.
        fleeing_group: Opponent group currently in atari (1 liberty).
        chaser_color: Color of the chasing player.
        min_chase: Minimum chase iterations to confirm ladder.

    Returns:
        True if ladder chase verified for ≥min_chase moves.
    """
    sim_board = board.copy()
    runner_color = chaser_color.opponent()
    chase_count = 0

    # Get a reference stone from the fleeing group to track it
    ref_stone = next(iter(fleeing_group.stones))  # type: ignore[union-attr]

    for _ in range(min_chase + 2):  # Extra margin to avoid off-by-one
        # Find current state of the fleeing group
        current_group = sim_board.get_group(ref_stone)
        if current_group is None:
            return False  # Group was captured — not a ladder
        if len(current_group.liberties) != 1:
            return False  # Not in atari — escaped

        # Runner extends at their single liberty
        escape_point = next(iter(current_group.liberties))
        try:
            sim_board.play(Move.play(runner_color, escape_point))
        except ValueError:
            return False  # Can't extend — not a standard ladder

        # After extension, runner group should have exactly 2 liberties
        extended_group = sim_board.get_group(escape_point)
        if extended_group is None:
            return False
        if len(extended_group.liberties) != 2:
            # 0-1 liberty: dead without chaser move (not ladder)
            # 3+ liberties: escaped — not a ladder
            return False

        # Chaser must find a move that puts runner back in atari
        atari_found = False
        for lib in sorted(extended_group.liberties, key=lambda p: (p.x, p.y)):
            test_board = sim_board.copy()
            try:
                test_board.play(Move.play(chaser_color, lib))
            except ValueError:
                continue  # Illegal move — try the other liberty

            # Check if runner is back in atari after this move
            chased_group = test_board.get_group(escape_point)
            if chased_group and len(chased_group.liberties) == 1:
                # Chase continues — apply this move
                sim_board.play(Move.play(chaser_color, lib))
                ref_stone = escape_point
                chase_count += 1
                atari_found = True
                break

        if not atari_found:
            return False  # Chaser can't continue — not a ladder

        if chase_count >= min_chase:
            return True

    return chase_count >= min_chase


def _is_localized_semeai(
    board: Board,
    captured_points: list[Point],
    last_move: Point,
    last_move_color: Color,
) -> bool:
    """Check for capture-race (semeai) near the capture site only.

    Unlike the old implementation that scanned the entire board,
    this only examines groups adjacent to the capture and the last move.
    Both sides must have low-liberty groups (≤3) near each other.

    Args:
        board: Board state after the capture.
        captured_points: Points where opponent stones were captured.
        last_move: Point where last move was played.
        last_move_color: Color of the player who just moved.

    Returns:
        True if both sides have low-liberty groups near the capture.
    """
    relevant_area: set[Point] = set()
    for cp in captured_points:
        for n in cp.neighbors(board.size):
            relevant_area.add(n)
    relevant_area.add(last_move)
    for n in last_move.neighbors(board.size):
        relevant_area.add(n)

    player_low = False
    opponent_low = False
    checked: set[Point] = set()

    for p in relevant_area:
        if p in checked or board.get(p) is None:
            continue
        group = board.get_group(p)
        if group is None:
            continue
        checked.update(group.stones)
        if len(group.liberties) <= 3:
            if group.color == last_move_color:
                player_low = True
            else:
                opponent_low = True
        if player_low and opponent_low:
            return True

    return player_low and opponent_low


# ---------------------------------------------------------------------------
# Evidence management
# ---------------------------------------------------------------------------

def _upgrade_evidence(
    evidence: dict[str, Confidence],
    tag: str,
    confidence: Confidence,
) -> None:
    """Upgrade evidence for a tag (never downgrade).

    If multiple sources detect the same tag, confidence is upgraded
    to CERTAIN (both comment and board agree).
    """
    current = evidence.get(tag, Confidence.NONE)
    if confidence > current:
        evidence[tag] = confidence
    elif current >= Confidence.HIGH and confidence >= Confidence.MODERATE:
        # Multiple independent signals → CERTAIN
        evidence[tag] = Confidence.CERTAIN


# ---------------------------------------------------------------------------
# Legacy-compatible public functions
# ---------------------------------------------------------------------------

# _analyze_move is kept for backward compatibility with tests that
# import it directly. It delegates to comment scanning.
def _analyze_move(node: SolutionNode, board: Board, tags: set[str]) -> None:
    """Analyze a single move for technique indicators (legacy API).

    Delegates to the new comment-scanning logic. Board pattern analysis
    is now handled separately in _collect_board_evidence().
    """
    if not node.comment:
        return
    evidence: dict[str, Confidence] = {}
    _scan_comment(node.comment, evidence)
    # Convert evidence to tags set (only HIGH+)
    for tag, conf in evidence.items():
        if conf >= _EMIT_THRESHOLD:
            tags.add(tag)


def validate_tags(tags: list[str]) -> list[str]:
    """Validate and filter tags against approved list from global config.

    Args:
        tags: List of tags to validate.

    Returns:
        List of valid tags only.
    """
    try:
        approved = get_approved_tags()
    except Exception:
        approved = _FALLBACK_TAGS
    return [tag for tag in tags if tag in approved]


# Keep APPROVED_TAGS as module-level for backwards compatibility with tests
# but it now loads from config
def _load_approved_tags() -> set[str]:
    """Load approved tags, with fallback for robustness."""
    try:
        return get_approved_tags()
    except Exception:
        return _FALLBACK_TAGS

APPROVED_TAGS = _load_approved_tags()
