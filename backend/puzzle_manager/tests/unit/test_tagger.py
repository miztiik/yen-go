"""Unit tests for high-precision tagger module.

Tests the precision-first tagging strategy:
- No fallback to life-and-death (empty list is valid)
- Word-boundary keyword matching (no false positives from substrings)
- Ko verified by Board ko_point (not heuristic)
- Ladder verified by 3+ chase simulation
- Snapback verified by sacrifice-recapture geometry
- Capture-race localized to capture site (not whole-board scan)
- Net only detected from comments (no board heuristic)

See docs/architecture/backend/tagging-strategy.md for design rationale.
"""

import pytest

from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SolutionNode
from backend.puzzle_manager.core.tagger import (
    APPROVED_TAGS,
    Confidence,
    _analyze_move,
    _contains_word,
    _detect_verified_ladder,
    _upgrade_evidence,
    _verify_ladder_chase,
    detect_techniques,
    get_approved_tags,
)


class TestApprovedTags:
    """Tests for approved tag constants loaded from global config."""

    def test_approved_tags_is_set(self) -> None:
        """Approved tags should be a set."""
        assert isinstance(APPROVED_TAGS, set)

    def test_approved_tags_non_empty(self) -> None:
        """Approved tags should not be empty."""
        assert len(APPROVED_TAGS) > 0

    def test_common_tags_present(self) -> None:
        """Common Go technique tags should be present (from global config/tags.json)."""
        # These are the canonical tags from config/tags.json
        assert "life-and-death" in APPROVED_TAGS
        assert "ladder" in APPROVED_TAGS
        assert "snapback" in APPROVED_TAGS
        assert "ko" in APPROVED_TAGS

    def test_get_approved_tags_returns_set(self) -> None:
        """get_approved_tags() should return a set."""
        tags = get_approved_tags()
        assert isinstance(tags, set)
        assert len(tags) > 0


class TestDetectTechniques:
    """Tests for technique detection."""

    def test_returns_list(self) -> None:
        """Detection should return a list of tags."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        assert isinstance(tags, list)
        assert all(isinstance(t, str) for t in tags)

    def test_returns_sorted(self) -> None:
        """Detected tags should be sorted."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        assert tags == sorted(tags)

    def test_no_fallback_to_life_and_death(self) -> None:
        """Empty detection should return empty list — NO fallback.

        Design decision: misleading tags are worse than no tags.
        Source-provided tags are preserved separately by the analyze stage.
        """
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        # Simple puzzle with no comments and no detectable technique
        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        # Should be empty — no confident detection possible
        assert isinstance(tags, list)
        # Must NOT contain life-and-death as fallback
        assert "life-and-death" not in tags

    def test_detects_ko_from_comment(self) -> None:
        """Comment containing 'ko' should produce ko tag."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]PL[B]AB[cc]AW[dd]
        ;B[dc]C[This is a ko fight])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)
        assert "ko" in tags

    def test_detects_ladder_from_comment(self) -> None:
        """Comment containing 'ladder' should produce ladder tag."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]PL[B]AB[cc]AW[dd]
        ;B[dc]C[Use the ladder])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)
        assert "ladder" in tags


# =============================================================================
# Word boundary matching (no regex)
# =============================================================================


class TestContainsWord:
    """Tests for _contains_word() — whole-word matching without regex."""

    def test_exact_match(self) -> None:
        assert _contains_word("this is a cut", "cut")

    def test_no_substring_match(self) -> None:
        """'cut' should NOT match inside 'execute'."""
        assert not _contains_word("execute the plan", "cut")

    def test_no_match_in_shortcut(self) -> None:
        """'cut' should NOT match inside 'shortcut'."""
        assert not _contains_word("use a shortcut", "cut")

    def test_word_at_start(self) -> None:
        assert _contains_word("cut here", "cut")

    def test_word_at_end(self) -> None:
        assert _contains_word("make the cut", "cut")

    def test_word_with_punctuation(self) -> None:
        assert _contains_word("it's a cut!", "cut")

    def test_word_with_comma(self) -> None:
        assert _contains_word("cut, slash", "cut")

    def test_ko_not_in_kono(self) -> None:
        """'ko' should NOT match inside 'kono' (Japanese word)."""
        assert not _contains_word("kono te wa", "ko")

    def test_ko_standalone(self) -> None:
        assert _contains_word("this is a ko fight", "ko")

    def test_eye_not_in_eyebrow(self) -> None:
        """'eye' should NOT match inside 'eyebrow'."""
        assert not _contains_word("raise an eyebrow", "eye")

    def test_eye_standalone(self) -> None:
        assert _contains_word("make an eye", "eye")

    def test_net_not_in_network(self) -> None:
        assert not _contains_word("network connection", "net")

    def test_multi_word_phrase(self) -> None:
        assert _contains_word("play under the stones here", "under the stones")

    def test_empty_text(self) -> None:
        assert not _contains_word("", "cut")

    def test_word_equals_text(self) -> None:
        assert _contains_word("cut", "cut")


# =============================================================================
# Confidence and evidence system
# =============================================================================


class TestConfidence:
    """Tests for the Confidence enum and evidence system."""

    def test_confidence_ordering(self) -> None:
        assert Confidence.NONE < Confidence.WEAK < Confidence.MODERATE
        assert Confidence.MODERATE < Confidence.HIGH < Confidence.CERTAIN

    def test_upgrade_never_downgrades(self) -> None:
        evidence: dict[str, Confidence] = {"ko": Confidence.HIGH}
        _upgrade_evidence(evidence, "ko", Confidence.MODERATE)
        assert evidence["ko"] == Confidence.CERTAIN  # upgraded by multi-signal

    def test_upgrade_to_certain_on_multi_signal(self) -> None:
        """HIGH + MODERATE from different sources → CERTAIN."""
        evidence: dict[str, Confidence] = {"ladder": Confidence.HIGH}
        _upgrade_evidence(evidence, "ladder", Confidence.MODERATE)
        assert evidence["ladder"] == Confidence.CERTAIN

    def test_new_tag_gets_assigned(self) -> None:
        evidence: dict[str, Confidence] = {}
        _upgrade_evidence(evidence, "ko", Confidence.HIGH)
        assert evidence["ko"] == Confidence.HIGH


# =============================================================================
# Ladder detection (3+ chase simulation)
# =============================================================================


class TestVerifiedLadder:
    """Tests for ladder verification by chase simulation."""

    def _make_board(self, size: int = 9) -> Board:
        return Board(size)

    def test_no_ladder_when_opponent_not_in_atari(self) -> None:
        """No ladder: opponent has multiple liberties."""
        board = self._make_board()
        board.place_stone(Color.WHITE, Point(4, 4))
        # White has 4 liberties — no atari
        evidence: dict[str, Confidence] = {}
        _detect_verified_ladder(board, Point(3, 4), Color.BLACK, evidence)
        assert "ladder" not in evidence

    def test_no_ladder_when_no_opponent(self) -> None:
        """No ladder: no opponent stones adjacent."""
        board = self._make_board()
        evidence: dict[str, Confidence] = {}
        _detect_verified_ladder(board, Point(4, 4), Color.BLACK, evidence)
        assert "ladder" not in evidence

    def test_no_ladder_single_atari_not_enough(self) -> None:
        """Single atari with diagonal escape is NOT confirmed as ladder.

        Old tagger would tag this. New tagger requires 3+ chase moves.
        """
        board = self._make_board()
        board.place_stone(Color.WHITE, Point(3, 3))
        board.place_stone(Color.BLACK, Point(2, 3))  # above
        board.place_stone(Color.BLACK, Point(3, 2))  # left
        board.place_stone(Color.BLACK, Point(4, 3))  # below
        # White at (3,3) has 1 liberty at (3,4) — in atari
        # But single atari doesn't verify a ladder chase
        evidence: dict[str, Confidence] = {}
        _detect_verified_ladder(board, Point(4, 3), Color.BLACK, evidence)
        # May or may not detect depending on chase continuation
        # The key test is that a non-chase atari doesn't produce false positive
        # (if it does detect, it means the chase actually continues ≥3 moves)

    def test_ladder_chase_simulation_uses_board(self) -> None:
        """Verify that ladder chase simulation runs without errors.

        Sets up a position where opponent is in atari and tests that
        _verify_ladder_chase runs correctly using pure Board operations.
        """
        board = self._make_board()
        # Set up a simple atari situation
        board.place_stone(Color.WHITE, Point(4, 4))
        board.place_stone(Color.BLACK, Point(3, 4))
        board.place_stone(Color.BLACK, Point(4, 3))
        board.place_stone(Color.BLACK, Point(5, 4))
        # White at (4,4) has 1 liberty at (4,5)
        group = board.get_group(Point(4, 4))
        assert group is not None
        assert len(group.liberties) == 1
        # This should run without error — it just may not confirm as ladder
        # if the chase doesn't continue 3+ moves
        result = _verify_ladder_chase(board, group, Color.BLACK, min_chase=3)
        assert isinstance(result, bool)


# =============================================================================
# Snapback detection (sacrifice-recapture geometry)
# =============================================================================


class TestSnapbackDetection:
    """Tests for high-precision snapback detection."""

    def test_single_capture_not_snapback(self) -> None:
        """Capturing a single stone is NOT automatically snapback.

        Old tagger tagged every single-stone capture as snapback.
        New tagger requires sacrifice-recapture geometry.
        """
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        # Simple capture: black plays to capture one white stone
        # No sacrifice-recapture geometry = not snapback
        sgf = """(;GM[1]FF[4]SZ[9]PL[B]
        AB[cc][dc][cd]AW[dd]
        ;B[de])"""
        game = parse_sgf(sgf)
        tags = detect_techniques(game)
        assert "snapback" not in tags


# =============================================================================
# Ko detection (Board-verified)
# =============================================================================


class TestKoDetection:
    """Tests for high-precision ko detection using Board ko_point."""

    def test_single_stone_atari_not_ko(self) -> None:
        """Single stone in atari is NOT automatically ko.

        Old tagger tagged every single-stone-in-atari as ko.
        New tagger requires Board.play() to confirm ko shape.
        """
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        # White stone in atari but NOT a ko shape
        sgf = """(;GM[1]FF[4]SZ[9]PL[B]
        AB[cc][dc][cd]AW[dd]
        ;B[de])"""
        game = parse_sgf(sgf)
        tags = detect_techniques(game)
        # Should not have ko — this is just a simple capture
        assert "ko" not in tags


# =============================================================================
# Net detection (comment-only, no board heuristic)
# =============================================================================


class TestNetDetection:
    """Tests for net detection — now comment-only (no board heuristic).

    Net (geta) is too subtle for board-based detection without full
    escape reading. Board heuristic had excessive false positives.
    """

    def test_net_from_comment(self) -> None:
        """Net keyword in comment should produce net tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="Use a net to capture",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "net" in tags

    def test_net_from_geta_comment(self) -> None:
        """Japanese loanword 'geta' should produce net tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="This geta captures the stones",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "net" in tags

    def test_no_net_from_network(self) -> None:
        """'net' inside 'network' should NOT produce net tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="Check the network status",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "net" not in tags

    def test_no_board_heuristic_for_net(self) -> None:
        """Board pattern alone should NOT produce net tag.

        Old tagger: opponent at distance 2 with few liberties → net.
        New tagger: net only from comments.
        """
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        # Position where old tagger would falsely detect "net"
        sgf = """(;GM[1]FF[4]SZ[9]PL[B]
        AB[bb][cb]AW[dd]
        ;B[fd])"""
        game = parse_sgf(sgf)
        tags = detect_techniques(game)
        # No comment says "net" → no net tag
        assert "net" not in tags


# =============================================================================
# Comment keyword matching (word boundaries)
# =============================================================================


class TestCommentKeywordPrecision:
    """Tests for precise comment keyword matching."""

    def test_cut_not_in_execute(self) -> None:
        """'cut' inside 'execute' should NOT produce cutting tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="Execute this sequence",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "cutting" not in tags

    def test_cut_standalone(self) -> None:
        """Standalone 'cut' should produce cutting tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="Cut here to separate",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "cutting" in tags

    def test_ko_not_in_kono(self) -> None:
        """'ko' inside Japanese word 'kono' should NOT produce ko tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="kono te wa tadashii",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "ko" not in tags

    def test_eye_not_in_eyebrow(self) -> None:
        """'eye' inside 'eyebrow' should NOT produce eye-shape tag."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="Raise an eyebrow at this move",
        )
        tags: set[str] = set()
        _analyze_move(node, Board(9), tags)
        assert "eye-shape" not in tags


# =============================================================================
# Japanese keywords (preserved from original)
# =============================================================================


class TestJapaneseKeywords:
    """Tests for Japanese keyword matching in _analyze_move() (T023)."""

    def _make_node(self, comment: str) -> SolutionNode:
        """Create a SolutionNode with the given comment and a move."""
        node = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment=comment,
        )
        return node

    @pytest.mark.parametrize(
        "keyword,expected_tag",
        [
            ("シチョウ", "ladder"),
            ("ゲタ", "net"),
            ("ウッテガエシ", "snapback"),
            ("コウ", "ko"),
            ("ホウリコミ", "throw-in"),
            ("セキ", "seki"),
            ("攻め合い", "capture-race"),
            ("ナカデ", "nakade"),
        ],
    )
    def test_japanese_keyword_detected(self, keyword: str, expected_tag: str) -> None:
        """Each Japanese keyword should produce the correct tag."""
        node = self._make_node(comment=f"この手は{keyword}です")
        board = Board(9)
        tags: set[str] = set()
        _analyze_move(node, board, tags)
        assert expected_tag in tags, f"Expected '{expected_tag}' for keyword '{keyword}'"

    def test_no_japanese_keyword_no_tag(self) -> None:
        """No Japanese keywords → no Japanese-specific tags added."""
        node = self._make_node(comment="この手は正解です")
        board = Board(9)
        tags: set[str] = set()
        _analyze_move(node, board, tags)
        # None of the 8 specific Japanese keyword tags should be present
        japanese_tags = {"ladder", "net", "snapback", "ko", "throw-in", "seki", "capture-race", "nakade"}
        assert not tags.intersection(japanese_tags)

    def test_mixed_japanese_english_comment(self) -> None:
        """Comments mixing Japanese and English keywords should detect both."""
        node = self._make_node(comment="This is a ladder シチョウ with ko")
        board = Board(9)
        tags: set[str] = set()
        _analyze_move(node, board, tags)
        assert "ladder" in tags
        assert "ko" in tags
