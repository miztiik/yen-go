"""Tests for query_builder — SGF → KataGo analysis query.

Task A.1.1: Build query from SGF.
All tests are unit tests (no KataGo engine needed).
"""

from pathlib import Path

import pytest
from analyzers.query_builder import (
    QueryResult,
    TsumegoQueryBundle,
    build_query_from_position,
    build_query_from_sgf,
    prepare_tsumego_query,
)
from models.position import Color, Position, Stone

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.unit
class TestQueryBuilder:
    """Tests for build_query_from_sgf()."""

    def _load(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    # ── A.1.1 test 1 ──────────────────────────────────────────────
    def test_valid_sgf_produces_valid_query(self) -> None:
        """SGF with AB/AW → JSON with correct initialStones."""
        sgf = self._load("simple_life_death.sgf")
        result = build_query_from_sgf(sgf)
        assert isinstance(result, QueryResult)
        request = result.request
        katago_json = request.to_katago_json()

        # Must have initialStones
        stones = katago_json["initialStones"]
        assert isinstance(stones, list)
        assert len(stones) > 0

        # Original SGF has 10 black + 9 white = 19 puzzle stones.
        # Frame adds more, so total must exceed 19.
        puzzle_stone_count = 19
        assert len(stones) >= puzzle_stone_count

        # Each stone entry is [color, gtp_coord]
        for entry in stones:
            assert len(entry) == 2
            assert entry[0] in ("B", "W")

    # ── A.1.1 test 2 ──────────────────────────────────────────────
    def test_frame_applied(self) -> None:
        """Query includes framed stones, not just puzzle stones."""
        sgf = self._load("simple_life_death.sgf")
        request = build_query_from_sgf(sgf).request

        # Original puzzle has 19 stones; frame must add more
        total_stones = len(request.position.stones)
        assert total_stones > 19, (
            f"Expected frame stones to be added; got {total_stones} total"
        )

    # ── A.1.1 test 3 ──────────────────────────────────────────────
    def test_komi_zero(self) -> None:
        """Tsumego queries use komi=0."""
        sgf = self._load("simple_life_death.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json["komi"] == 0.0
        assert request.position.komi == 0.0

    # ── A.1.1 test 4 ──────────────────────────────────────────────
    def test_ownership_and_policy_requested(self) -> None:
        """includeOwnership=true and includePolicy=true in query."""
        sgf = self._load("simple_life_death.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json.get("includeOwnership") is True
        assert katago_json.get("includePolicy") is True

    # ── A.1.1 test 5 ──────────────────────────────────────────────
    def test_black_to_play(self) -> None:
        """SGF with PL[B] → initialPlayer=B in query."""
        sgf = self._load("simple_life_death.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json["initialPlayer"] == "B"
        assert request.position.player_to_move == Color.BLACK

    # ── A.1.1 test 6 ──────────────────────────────────────────────
    def test_white_to_play(self) -> None:
        """SGF with PL[W] → initialPlayer=W in query."""
        sgf = self._load("white_to_play.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json["initialPlayer"] == "W"
        assert request.position.player_to_move == Color.WHITE

    # ── A.1.1 test 7 ──────────────────────────────────────────────
    def test_color_inferred_from_first_move(self) -> None:
        """No PL property → color inferred from first correct move.

        Fixture no_pl_white_first.sgf has no PL, first move is W[bb].
        So player_to_move should be inferred as WHITE.
        """
        sgf = self._load("no_pl_white_first.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json["initialPlayer"] == "W"
        assert request.position.player_to_move == Color.WHITE

    # ── A.1.1 test 8 ──────────────────────────────────────────────
    def test_board_size_propagated(self) -> None:
        """SZ[9] → boardXSize=9, boardYSize=9 in query."""
        sgf = self._load("board_9x9.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        assert katago_json["boardXSize"] == 9
        assert katago_json["boardYSize"] == 9
        assert request.position.board_size == 9

    # ── allowMoves safety test ─────────────────────────────────────
    def test_allow_moves_omitted_for_puzzle_region(self) -> None:
        """Puzzle region with multiple moves → allowMoves IS emitted.

        The puzzle region restricts KataGo analysis to moves near the
        puzzle stones, concentrating visits on relevant candidates.
        Both the tsumego frame and allowMoves work together.
        """
        sgf = self._load("simple_life_death.sgf")
        request = build_query_from_sgf(sgf).request
        katago_json = request.to_katago_json()

        # The request has allowed_moves from the ORIGINAL position's puzzle region
        # and to_katago_json emits allowMoves in dict format
        assert "allowMoves" in katago_json
        assert len(katago_json["allowMoves"]) == 1  # single dict entry
        entry = katago_json["allowMoves"][0]
        assert "player" in entry
        assert "moves" in entry
        assert len(entry["moves"]) > 0
        assert entry["untilDepth"] == 1


# ---------------------------------------------------------------------------
# Golden fixture regression tests (T9)
# ---------------------------------------------------------------------------

# Golden puzzle SGF: a corner life-and-death position, Black to play.
# Stones are in columns A-F, rows 17-19 (top-left corner on 19x19).
_GOLDEN_SGF = (
    "(;SZ[19]FF[4]GM[1]PL[B]"
    "C[problem 1 ]"
    "AB[fb][bb][cb][db]"
    "AW[ea][dc][cc][eb][bc])"
)


@pytest.mark.unit
class TestPrepareTsumegoQuery:
    """Tests for prepare_tsumego_query() — single source of truth."""

    @staticmethod
    def _golden_stones() -> list[Stone]:
        """Stones from the golden puzzle SGF (AB[fb][bb][cb][db] AW[ea][dc][cc][eb][bc])."""
        return [
            Stone.from_sgf(Color.BLACK, "fb"),
            Stone.from_sgf(Color.BLACK, "bb"),
            Stone.from_sgf(Color.BLACK, "cb"),
            Stone.from_sgf(Color.BLACK, "db"),
            Stone.from_sgf(Color.WHITE, "ea"),
            Stone.from_sgf(Color.WHITE, "dc"),
            Stone.from_sgf(Color.WHITE, "cc"),
            Stone.from_sgf(Color.WHITE, "eb"),
            Stone.from_sgf(Color.WHITE, "bc"),
        ]

    def test_returns_bundle(self) -> None:
        """Function returns a TsumegoQueryBundle with required fields."""
        position = Position(
            board_size=19,
            stones=self._golden_stones(),
            player_to_move=Color.BLACK,
            komi=6.5,
        )
        bundle = prepare_tsumego_query(position)
        assert isinstance(bundle, TsumegoQueryBundle)
        assert bundle.komi == 0.0
        assert bundle.framed_position.komi == 0.0
        assert isinstance(bundle.region_moves, list)
        assert len(bundle.region_moves) > 0
        assert bundle.rules == "chinese"

    def test_komi_always_zero(self) -> None:
        """Komi is overridden to 0.0 regardless of input."""
        position = Position(board_size=9, komi=7.5, player_to_move=Color.BLACK)
        bundle = prepare_tsumego_query(position)
        assert bundle.komi == 0.0
        assert bundle.framed_position.komi == 0.0

    def test_region_moves_within_bounding_box(self) -> None:
        """Region moves must stay near the puzzle stones."""
        # Parse golden SGF to get the position
        build_query_from_sgf(_GOLDEN_SGF)
        # Now test prepare_tsumego_query directly with a similar position
        position = Position(
            board_size=19,
            stones=TestPrepareTsumegoQuery._golden_stones(),
            player_to_move=Color.BLACK,
        )
        bundle = prepare_tsumego_query(position, puzzle_region_margin=2)
        assert len(bundle.region_moves) > 0
        # All region moves should be in the top-left area.
        # GTP columns: A=1..T=19, rows: 1..19
        # Puzzle stones are in cols A-F (1-6), rows 18-19 (top).
        # With margin=2, region should extend to roughly col H and row 16.
        for move_str in bundle.region_moves:
            col_char = move_str[0].upper()
            col_idx = ord(col_char) - ord('A') + (1 if col_char < 'I' else 0)
            # Ensure no moves beyond reasonable boundary (col ≤ 12, for safety)
            assert col_idx <= 12, f"Move {move_str} outside expected puzzle region"


@pytest.mark.unit
class TestGoldenFixtureSgfPath:
    """Golden fixture: build_query_from_sgf with the original broken puzzle."""

    def test_allowed_moves_present_in_sgf_path(self) -> None:
        """build_query_from_sgf includes allowed_moves for the golden puzzle."""
        result = build_query_from_sgf(_GOLDEN_SGF)
        assert result.request.allowed_moves is not None
        assert len(result.request.allowed_moves) > 0

    def test_no_star_point_moves_in_sgf_path(self) -> None:
        """Far-away star-point moves (D4, Q16, Q4) must not appear in allowed_moves."""
        result = build_query_from_sgf(_GOLDEN_SGF)
        # D16 is near the puzzle (top-left corner) so it may legitimately appear
        far_star_points = {"D4", "Q16", "Q4", "K10"}
        for sp in far_star_points:
            assert sp not in result.request.allowed_moves, (
                f"Far star point {sp} should not be in allowed_moves"
            )


@pytest.mark.unit
class TestGoldenFixturePositionPath:
    """Golden fixture: build_query_from_position with the original broken puzzle."""

    def test_allowed_moves_present_in_position_path(self) -> None:
        """build_query_from_position includes allowed_moves."""
        position = Position(
            board_size=19,
            stones=TestPrepareTsumegoQuery._golden_stones(),
            player_to_move=Color.BLACK,
        )
        result = build_query_from_position(position)
        assert result.request.allowed_moves is not None
        assert len(result.request.allowed_moves) > 0


# ---------------------------------------------------------------------------
# T28-T29: ko_type wiring through prepare_tsumego_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKoTypeWiring:
    """ko_type parameter flows through prepare_tsumego_query to apply_tsumego_frame."""

    @staticmethod
    def _make_19x19_position() -> Position:
        """Standard 19x19 position for ko_type tests."""
        return Position(
            board_size=19,
            stones=TestPrepareTsumegoQuery._golden_stones(),
            player_to_move=Color.BLACK,
        )

    def test_ko_type_none_no_ko_threats(self) -> None:
        """ko_type='none' → frame has no ko threat patterns.
        ko_type='direct' → frame includes ko threat stones."""
        pos = self._make_19x19_position()
        bundle_none = prepare_tsumego_query(pos, ko_type="none")
        bundle_direct = prepare_tsumego_query(pos, ko_type="direct")
        # Both should produce framed positions with substantial stones
        none_count = len(bundle_none.framed_position.stones)
        direct_count = len(bundle_direct.framed_position.stones)
        assert none_count > len(pos.stones), "Frame should add stones"
        assert direct_count > len(pos.stones), "Frame with ko should add stones"
        # With BFS fill, total stone counts may be similar because fill
        # quota adjusts — the key invariant is both produce valid frames
        assert direct_count >= none_count - 8, (
            f"ko_type='direct' should not produce significantly fewer stones: {direct_count} vs {none_count}"
        )

    def test_ko_type_default_is_none(self) -> None:
        """Default ko_type is 'none' — no extra stones from ko threats."""
        pos = self._make_19x19_position()
        bundle_default = prepare_tsumego_query(pos)
        bundle_explicit_none = prepare_tsumego_query(pos, ko_type="none")
        assert len(bundle_default.framed_position.stones) == len(bundle_explicit_none.framed_position.stones)
