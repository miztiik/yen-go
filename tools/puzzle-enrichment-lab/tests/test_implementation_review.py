"""Tests for implementation review fixes — Phase A post-completion review.

Covers P0-P2 issues identified in the thorough implementation review:
- P0 #1: SGF parser escaped-bracket handling
- P0 #2: gtp_to_sgf board_size parameter
- P0 #3: gtp_to_sgf malformed input guard
- P0 #4: Player alternation in to_katago_json
- P1 #6: Stone.gtp_coord_for board_size method
- P2 #15: SGF canonical property format
"""

from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from core.tsumego_analysis import compose_enriched_sgf, parse_sgf
from models.analysis_request import AnalysisRequest
from models.analysis_response import gtp_to_sgf, sgf_to_gtp
from models.position import Color, Position, Stone

# =========================================================================
# P0 #1: SGF parser escaped-bracket handling
# =========================================================================


@pytest.mark.unit
class TestEscapedBracketParsing:
    """Verify that the SGF parser handles escaped brackets in property values."""

    def test_plain_comment_parsed(self):
        """Normal comment without escaped brackets parses correctly."""
        sgf = "(;FF[4]GM[1]SZ[19]C[Hello world];B[cd])"
        root = parse_sgf(sgf)
        assert root.get("C") == "Hello world"

    def test_escaped_bracket_in_comment(self):
        """Comment with escaped \\] is parsed correctly."""
        sgf = r"(;FF[4]GM[1]SZ[19]C[See YR\]abc];B[cd])"
        root = parse_sgf(sgf)
        comment = root.get("C")
        assert comment is not None
        assert r"YR\]abc" in comment or "YR]abc" in comment

    def test_multiple_escaped_brackets(self):
        """Multiple escaped brackets in a single property value."""
        sgf = r"(;FF[4]GM[1]SZ[19]C[a\]b\]c];B[cd])"
        root = parse_sgf(sgf)
        comment = root.get("C")
        assert comment is not None
        assert len(comment) > 3  # Should contain the full escaped content

    def test_escaped_bracket_doesnt_break_next_property(self):
        """Escaped bracket doesn't consume the next property."""
        sgf = r"(;FF[4]GM[1]SZ[19]C[text\]more]PL[B];B[cd])"
        root = parse_sgf(sgf)
        assert root.get("PL") == "B"


# =========================================================================
# P0 #2+#3: gtp_to_sgf board_size and malformed input
# =========================================================================


@pytest.mark.unit
class TestGtpToSgf:
    """Verify gtp_to_sgf handles board_size and edge cases."""

    def test_19x19_default(self):
        """Default 19×19 conversion works as before."""
        assert gtp_to_sgf("D16") == "dd"  # col D=index 3 → 'd', row 19-16=3 → 'd'
        assert gtp_to_sgf("A1") == "as"
        assert gtp_to_sgf("T19") == "sa"

    def test_9x9_board(self):
        """9×9 board converts correctly."""
        # On 9×9: A1 → row = 9-1=8 → 'a' + 8 = 'i' → "ai"
        assert gtp_to_sgf("A1", board_size=9) == "ai"
        # A9 → row = 9-9=0 → 'a' → "aa"
        assert gtp_to_sgf("A9", board_size=9) == "aa"
        # E5 → col=4 → 'e', row=9-5=4 → 'e' → "ee"
        assert gtp_to_sgf("E5", board_size=9) == "ee"

    def test_13x13_board(self):
        """13×13 board converts correctly."""
        # A1 → row = 13-1=12 → 'a' + 12 = 'm' → "am"
        assert gtp_to_sgf("A1", board_size=13) == "am"
        # A13 → row = 13-13=0 → 'a' → "aa"
        assert gtp_to_sgf("A13", board_size=13) == "aa"

    def test_pass_returns_empty(self):
        """Pass moves return empty string."""
        assert gtp_to_sgf("pass") == ""
        assert gtp_to_sgf("PASS") == ""

    def test_empty_returns_empty(self):
        """Empty/None-like input returns empty string."""
        assert gtp_to_sgf("") == ""

    def test_single_char_returns_empty(self):
        """Malformed single-character input returns empty (P0 #3)."""
        assert gtp_to_sgf("A") == ""
        assert gtp_to_sgf("X") == ""

    def test_non_numeric_row_returns_empty(self):
        """Non-numeric row part returns empty string."""
        assert gtp_to_sgf("Abc") == ""

    def test_out_of_bounds_returns_empty(self):
        """Coordinates outside board bounds return empty string."""
        # Row 20 on a 19×19 board → row = 19-20 = -1 → out of bounds
        assert gtp_to_sgf("A20", board_size=19) == ""
        # Row 0 → off the board
        assert gtp_to_sgf("A0", board_size=19) == ""
        # Row 10 on a 9×9 board → row = 9-10 = -1
        assert gtp_to_sgf("A10", board_size=9) == ""

    def test_roundtrip_19x19(self):
        """GTP→SGF→GTP roundtrip for 19×19."""
        sgf = gtp_to_sgf("D16", 19)
        gtp = sgf_to_gtp(sgf, 19)
        assert gtp == "D16"

    def test_roundtrip_9x9(self):
        """GTP→SGF→GTP roundtrip for 9×9."""
        sgf = gtp_to_sgf("E5", 9)
        gtp = sgf_to_gtp(sgf, 9)
        assert gtp == "E5"

    def test_roundtrip_13x13(self):
        """GTP→SGF→GTP roundtrip for 13×13."""
        sgf = gtp_to_sgf("G7", 13)
        gtp = sgf_to_gtp(sgf, 13)
        assert gtp == "G7"


# =========================================================================
# P0 #4: Player alternation in to_katago_json
# =========================================================================


@pytest.mark.unit
class TestPlayerAlternation:
    """Verify allowMoves player label alternation is correct."""

    def test_initial_player_no_moves(self):
        """With no moves played and 1 allowed move, player is initial player."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=2, y=2)],
            player_to_move=Color.BLACK,
            komi=0.0,
        )
        req = AnalysisRequest(
            position=pos,
            allowed_moves=["D4"],
        )
        payload = req.to_katago_json()
        assert "allowMoves" in payload
        assert payload["allowMoves"][0]["player"] == "B"

    def test_player_after_one_move(self):
        """After 1 move by initial player B, the next player should be W."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=2, y=2)],
            player_to_move=Color.BLACK,
            komi=0.0,
        )
        req = AnalysisRequest(
            position=pos,
            moves=[["B", "D4"]],
            allowed_moves=["E5"],
        )
        payload = req.to_katago_json()
        assert "allowMoves" in payload
        assert payload["allowMoves"][0]["player"] == "W"

    def test_player_after_two_moves(self):
        """After 2 moves, back to initial player."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=2, y=2)],
            player_to_move=Color.BLACK,
            komi=0.0,
        )
        req = AnalysisRequest(
            position=pos,
            moves=[["B", "D4"], ["W", "E5"]],
            allowed_moves=["F6"],
        )
        payload = req.to_katago_json()
        assert "allowMoves" in payload
        assert payload["allowMoves"][0]["player"] == "B"

    def test_white_initial_player(self):
        """White as initial player: after 1 move, next is B."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.WHITE, x=2, y=2)],
            player_to_move=Color.WHITE,
            komi=0.0,
        )
        req = AnalysisRequest(
            position=pos,
            moves=[["W", "D4"]],
            allowed_moves=["E5"],
        )
        payload = req.to_katago_json()
        assert "allowMoves" in payload
        assert payload["allowMoves"][0]["player"] == "B"

    def test_allow_moves_emitted_for_puzzle_region(self):
        """allowMoves IS emitted for multi-move puzzle region restriction."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=2, y=2)],
            player_to_move=Color.BLACK,
            komi=0.0,
        )
        req = AnalysisRequest(
            position=pos,
            allowed_moves=["D4", "E5", "F6"],
        )
        payload = req.to_katago_json()
        assert "allowMoves" in payload
        # New KataGo dict format: [{"player": "B", "moves": [...], "untilDepth": 1}]
        assert len(payload["allowMoves"]) == 1  # single dict entry
        entry = payload["allowMoves"][0]
        assert entry["player"] == "B"
        assert set(entry["moves"]) == {"D4", "E5", "F6"}
        assert entry["untilDepth"] == 1


# =========================================================================
# P1 #6: Stone.gtp_coord_for(board_size)
# =========================================================================


@pytest.mark.unit
class TestStoneGtpCoord:
    """Verify Stone.gtp_coord and gtp_coord_for work correctly."""

    def test_gtp_coord_default_19(self):
        """gtp_coord property uses 19×19 (backward compat)."""
        stone = Stone(color=Color.BLACK, x=3, y=3)
        assert stone.gtp_coord == "D16"

    def test_gtp_coord_for_9x9(self):
        """gtp_coord_for(9) computes correctly for 9×9 board."""
        stone = Stone(color=Color.BLACK, x=0, y=0)
        assert stone.gtp_coord_for(9) == "A9"

    def test_gtp_coord_for_13x13(self):
        """gtp_coord_for(13) computes correctly for 13×13 board."""
        stone = Stone(color=Color.BLACK, x=0, y=12)
        assert stone.gtp_coord_for(13) == "A1"

    def test_gtp_coord_for_consistent_with_position(self):
        """Stone.gtp_coord_for matches Position.to_katago_initial_stones."""
        pos = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=4, y=4)],
        )
        katago_stones = pos.to_katago_initial_stones()
        assert katago_stones[0][1] == pos.stones[0].gtp_coord_for(9)


# =========================================================================
# P2 #15: SGF canonical property format
# =========================================================================


@pytest.mark.unit
class TestCanonicalSgfFormat:
    """Verify SGF compose uses canonical multi-value format."""

    def test_multi_value_property_format(self):
        """AB[cd][dd] should be canonical, not AB[cd]AB[dd]."""
        sgf = "(;FF[4]GM[1]SZ[19]AB[cd][dd][ed];B[cf])"
        root = parse_sgf(sgf)
        result = compose_enriched_sgf(root)
        # Canonical: AB[cd][dd][ed] — key appears once
        assert "AB[" in result
        # Should NOT have AB repeated for each value
        assert result.count("AB[") == 1

    def test_single_value_property_unchanged(self):
        """Single-value properties are unaffected."""
        sgf = "(;FF[4]GM[1]SZ[19];B[cd])"
        root = parse_sgf(sgf)
        result = compose_enriched_sgf(root)
        assert "FF[4]" in result
        assert "SZ[19]" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
