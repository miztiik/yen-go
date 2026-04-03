"""Integration tests for Benson/interior-point gates and ko board-replay verification.

RT-2: Verify Benson gate fires inside _build_tree_recursive with puzzle_region.
RT-3: Verify query short-circuit (fewer queries when gates fire).
RT-5: Ko capture verification with board-state inputs.
NF-01: Board state uses actual board size (9x9 / 13x13).
NF-02: Adjacency rejects identical coordinates.
R1/NF-03: puzzle_region threads through discover_alternatives.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent

from analyzers.ko_validation import (
    KoType,
    _are_adjacent,
    detect_ko_in_pv,
    validate_ko,
)
from analyzers.solve_position import QueryBudget, build_solution_tree, discover_alternatives
from analyzers.validate_correct_move import ValidationStatus
from config.ai_solve import AiSolveConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    max_depth: int = 5,
    min_depth: int = 1,
    transposition_enabled: bool = True,
    terminal_detection_enabled: bool = True,
) -> AiSolveConfig:
    return AiSolveConfig(
        enabled=True,
        thresholds={
            "t_good": 0.05,
            "t_bad": 0.15,
            "t_hotspot": 0.30,
            "t_disagreement": 0.10,
        },
        confidence_metrics={
            "pre_winrate_floor": 0.30,
            "post_winrate_ceiling": 0.95,
        },
        solution_tree={
            "confirmation_min_policy": 0.03,
            "transposition_enabled": transposition_enabled,
            "terminal_detection_enabled": terminal_detection_enabled,
            "solution_max_depth": max_depth,
            "solution_min_depth": min_depth,
            "max_total_tree_queries": 50,
            # Override depth_profiles so min/max_depth actually takes effect
            # (build_solution_tree reads from depth_profiles[category], not
            # the top-level solution_min/max_depth fields).
            "depth_profiles": {
                "entry": {"solution_min_depth": min_depth, "solution_max_depth": max_depth},
                "core": {"solution_min_depth": min_depth, "solution_max_depth": max_depth},
                "strong": {"solution_min_depth": min_depth, "solution_max_depth": max_depth},
            },
        },
    )


def _make_engine_counting_queries(board_size: int = 19):
    """Create a mock engine that counts queries and returns a non-pass move.

    Attaches a _raw_position with the given board_size so _BoardState
    initializes correctly (NF-01 fix).
    """
    from models.position import Color, Position

    engine = MagicMock()
    counter = {"n": 0}

    # Provide a real Position so _BoardState can read board_size and stones
    engine._raw_position = Position(
        board_size=board_size,
        stones=[],
        player_to_move=Color.BLACK,
    )

    def _query_mock(moves, max_visits=100):
        counter["n"] += 1
        resp = MagicMock()
        resp.move_infos = [
            {
                "move": "D4",
                "visits": 100,
                "winrate": 0.6,
                "policy_prior": 0.5,
                "prior": 0.5,
                "pv": ["D4", "E4"],
                "score_lead": 5.0,
            }
        ]
        resp.root_winrate = 0.5
        return resp

    engine.query = _query_mock
    return engine, counter


# ===================================================================
# RT-2 / R3: Benson gate fires — zero queries at gate node
# ===================================================================


@pytest.mark.unit
class TestBensonGateIntegration:
    """Verify Benson gate fires with exact query count assertions."""

    def test_benson_gate_zero_queries_when_fires_at_depth_1(self):
        """With min_depth=1 and puzzle_region covering D4 (15,3),
        Benson gate fires at depth=2 (after opponent places D4 as White)
        → only 1 engine query (root at depth=1).

        At depth=1: no White stones in puzzle_region yet → gate skips → query.
        At depth=2: White at (15,3) in puzzle_region → contest_stones match
        alive_group → Benson fires → no further queries.
        """
        engine, counter = _make_engine_counting_queries()
        config = _make_config(max_depth=5, min_depth=1, transposition_enabled=True)
        budget = QueryBudget(total=50)
        # D4 on 19x19: row = 19 - 4 = 15, col = ord('D') - ord('A') = 3
        puzzle_region = frozenset({(15, 3), (15, 4), (16, 3), (16, 4)})
        alive_group = frozenset({(15, 3), (15, 4), (16, 3), (16, 4)})

        def _mock_alive(stones_dict, board_size):
            return {alive_group}

        def _mock_interior(stones_dict, defender_color, puzzle_region, board_size):
            return False

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
            side_effect=_mock_alive,
        ), patch(
            "analyzers.benson_check.check_interior_point_death",
            side_effect=_mock_interior,
        ):
            root = build_solution_tree(
                engine=engine,
                initial_moves=[],
                correct_move_gtp="A1",
                player_color="B",
                config=config,
                level_slug="elementary",
                query_budget=budget,
                puzzle_id="test-benson-zero",
                puzzle_region=puzzle_region,
            )

        assert root is not None
        # Gate fires at depth=2 (after root query at depth=1)
        # Root query happens once, then gate prevents deeper queries
        assert counter["n"] == 1, (
            f"Expected 1 query (root only) when Benson gate fires at depth=2, got {counter['n']}"
        )

    def test_interior_point_gate_zero_queries_when_fires_at_depth_1(self):
        """With min_depth=1, interior-point gate fires at depth=1 (first call)
        → ZERO engine queries because the gate returns before engine.query().
        """
        engine, counter = _make_engine_counting_queries()
        config = _make_config(max_depth=5, min_depth=1, transposition_enabled=True)
        budget = QueryBudget(total=50)
        puzzle_region = frozenset({(0, 0), (0, 1), (1, 0), (1, 1)})

        def _mock_alive(stones_dict, board_size):
            return set()

        def _mock_interior(stones_dict, defender_color, puzzle_region, board_size):
            return True  # Interior-point death

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
            side_effect=_mock_alive,
        ), patch(
            "analyzers.benson_check.check_interior_point_death",
            side_effect=_mock_interior,
        ):
            root = build_solution_tree(
                engine=engine,
                initial_moves=[],
                correct_move_gtp="D4",
                player_color="B",
                config=config,
                level_slug="elementary",
                query_budget=budget,
                puzzle_id="test-interior-zero",
                puzzle_region=puzzle_region,
            )

        assert root is not None
        # Interior-point gate fires at depth=1 → zero engine queries
        assert counter["n"] == 0, (
            f"Expected 0 queries when interior-point gate fires at depth=1, got {counter['n']}"
        )
        assert budget.used == 0


# ===================================================================
# RT-3 / R3: No puzzle_region → at least 1 query (no gates)
# ===================================================================


@pytest.mark.unit
class TestQueryShortCircuit:
    """Without puzzle_region, gates cannot fire → queries must happen."""

    def test_no_puzzle_region_at_least_one_query(self):
        """Without puzzle_region, gates never fire — at least 1 query must occur."""
        engine, counter = _make_engine_counting_queries()
        config = _make_config(max_depth=2, min_depth=1, transposition_enabled=True)
        budget = QueryBudget(total=20)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-no-region",
            puzzle_region=None,
        )

        assert root is not None
        assert counter["n"] >= 1, (
            f"Without puzzle_region, at least 1 query expected, got {counter['n']}"
        )
        assert budget.used >= 1

    def test_gates_vs_no_gates_query_count_comparison(self):
        """Gate-enabled run uses strictly fewer queries than no-gate run."""
        config = _make_config(max_depth=5, min_depth=1, transposition_enabled=True)

        # --- Run WITHOUT gates (no puzzle_region) ---
        engine1, counter1 = _make_engine_counting_queries()
        budget1 = QueryBudget(total=50)

        build_solution_tree(
            engine=engine1, initial_moves=[], correct_move_gtp="D4",
            player_color="B", config=config, level_slug="intermediate",
            query_budget=budget1, puzzle_id="no-gate",
            puzzle_region=None,
        )
        queries_without = counter1["n"]

        # --- Run WITH gates (interior-point fires at depth=1 → 0 queries) ---
        engine2, counter2 = _make_engine_counting_queries()
        budget2 = QueryBudget(total=50)
        puzzle_region = frozenset({(15, 3)})

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
            return_value=set(),
        ), patch(
            "analyzers.benson_check.check_interior_point_death",
            return_value=True,  # Interior-point fires immediately
        ):
            build_solution_tree(
                engine=engine2, initial_moves=[], correct_move_gtp="D4",
                player_color="B", config=config, level_slug="intermediate",
                query_budget=budget2, puzzle_id="with-gate",
                puzzle_region=puzzle_region,
            )
        queries_with = counter2["n"]

        assert queries_without >= 1, (
            f"No-gate run expected >= 1 query, got {queries_without}"
        )
        assert queries_with < queries_without, (
            f"Gate-enabled ({queries_with}) should use fewer queries "
            f"than no-gate ({queries_without})"
        )


# ===================================================================
# NF-01: Board size from engine context, not hardcoded 19
# ===================================================================


@pytest.mark.unit
class TestBoardSizeFromEngine:
    """_BoardState should use board_size from engine's position."""

    def test_9x9_board_size_used(self):
        """On a 9x9 position, _BoardState grid should be 9x9."""
        from models.position import Color, Position, Stone

        engine, counter = _make_engine_counting_queries()
        # Attach a 9x9 position to the engine
        engine._raw_position = Position(
            board_size=9,
            stones=[Stone(color=Color.BLACK, x=0, y=0)],
            player_to_move=Color.BLACK,
        )
        config = _make_config(max_depth=2, min_depth=1, transposition_enabled=True)
        budget = QueryBudget(total=10)

        # The gate should fire using a 9x9 sized board state
        puzzle_region = frozenset({(0, 0), (0, 1), (1, 0)})

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
        ) as mock_benson, patch(
            "analyzers.benson_check.check_interior_point_death",
            return_value=True,  # Fire the gate
        ):
            mock_benson.return_value = set()
            root = build_solution_tree(
                engine=engine, initial_moves=[], correct_move_gtp="B1",
                player_color="B", config=config, level_slug="novice",
                query_budget=budget, puzzle_id="test-9x9",
                puzzle_region=puzzle_region,
            )

        assert root is not None
        # Benson was called with board_size=9
        if mock_benson.called:
            _, kwargs = mock_benson.call_args
            if "board_size" in kwargs:
                assert kwargs["board_size"] == 9
            else:
                # positional arg: stones_dict, board_size
                assert mock_benson.call_args[0][1] == 9

    def test_13x13_board_size_used(self):
        """On a 13x13 position, _BoardState grid should be 13x13."""
        from models.position import Color, Position, Stone

        engine, counter = _make_engine_counting_queries()
        engine._raw_position = Position(
            board_size=13,
            stones=[Stone(color=Color.BLACK, x=6, y=6)],
            player_to_move=Color.BLACK,
        )
        config = _make_config(max_depth=2, min_depth=1, transposition_enabled=True)
        budget = QueryBudget(total=10)
        puzzle_region = frozenset({(6, 6), (6, 7), (7, 6)})

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
        ) as mock_benson, patch(
            "analyzers.benson_check.check_interior_point_death",
            return_value=True,
        ):
            mock_benson.return_value = set()
            build_solution_tree(
                engine=engine, initial_moves=[], correct_move_gtp="G7",
                player_color="B", config=config, level_slug="intermediate",
                query_budget=budget, puzzle_id="test-13x13",
                puzzle_region=puzzle_region,
            )

        if mock_benson.called:
            assert mock_benson.call_args[0][1] == 13


# ===================================================================
# NF-02: Adjacency rejects identical coordinates (Manhattan == 1)
# ===================================================================


@pytest.mark.unit
class TestAdjacencyCorrectness:
    """_is_adjacent must return False for identical coordinates."""

    def test_identical_coordinates_not_adjacent(self):
        """Same coordinate has Manhattan distance 0, not adjacent."""
        assert _are_adjacent("D4", "D4") is False

    def test_orthogonal_neighbors_are_adjacent(self):
        """Orthogonal neighbors (distance=1) are adjacent."""
        assert _are_adjacent("D4", "D5") is True
        assert _are_adjacent("D4", "D3") is True
        assert _are_adjacent("D4", "E4") is True
        assert _are_adjacent("D4", "C4") is True

    def test_diagonal_not_adjacent(self):
        """Diagonal neighbors (distance=2) are not adjacent."""
        assert _are_adjacent("D4", "E5") is False
        assert _are_adjacent("D4", "C3") is False


# ===================================================================
# R1/NF-03: puzzle_region threads through discover_alternatives
# ===================================================================


@pytest.mark.unit
class TestDiscoverAlternativesRegionThreading:
    """discover_alternatives must forward puzzle_region to build_solution_tree."""

    def test_puzzle_region_forwarded_to_alt_tree_build(self):
        """puzzle_region passed to discover_alternatives reaches build_solution_tree."""
        from models.analysis_response import AnalysisResponse, MoveAnalysis

        puzzle_region = frozenset({(0, 0), (0, 1)})

        # Analysis with two TE moves → one alternative
        analysis = AnalysisResponse(
            request_id="test",
            move_infos=[
                MoveAnalysis(move="A1", visits=200, winrate=0.90,
                             policy_prior=0.7, pv=["A1", "B1"]),
                MoveAnalysis(move="B2", visits=180, winrate=0.88,
                             policy_prior=0.6, pv=["B2", "C2"]),
            ],
            root_winrate=0.85, root_score=5.0, total_visits=400,
        )

        engine = MagicMock()
        config = _make_config(max_depth=2)
        budget = QueryBudget(total=20)

        captured_region = {"value": "NOT_CALLED"}


        def _spy_build(*args, **kwargs):
            captured_region["value"] = kwargs.get("puzzle_region", "MISSING")
            # Return a minimal node to avoid deep recursion
            from analyzers.solve_position import SolutionNode
            return SolutionNode(move_gtp="B2", color="B")

        with patch(
            "analyzers.solve_position.build_solution_tree",
            side_effect=_spy_build,
        ):
            alts, co_correct, hc = discover_alternatives(
                analysis, "A1", "B", "test-alt-region", config,
                engine=engine, initial_moves=[], level_slug="elementary",
                query_budget=budget,
                puzzle_region=puzzle_region,
            )

        assert captured_region["value"] == puzzle_region, (
            f"Expected puzzle_region={puzzle_region}, "
            f"got {captured_region['value']}"
        )


# ===================================================================
# R5: Ko capture verification — deterministic True/False assertions
# ===================================================================


@pytest.mark.unit
class TestKoCaptureVerificationDeterministic:
    """Ko detection with explicit True/False assertions under board-replay."""

    def test_adjacent_repeat_is_ko_without_board(self):
        """Adjacency-only: repeated coord with adjacent interleave → ko=True."""
        pv = ["D4", "E4", "D4"]
        result = detect_ko_in_pv(pv, initial_stones=None)
        assert result.ko_detected is True

    def test_no_repeat_means_no_ko(self):
        """No repeated coordinate in PV → ko_detected=False."""
        pv = ["D4", "E4", "F4"]
        result = detect_ko_in_pv(pv, initial_stones=None)
        assert result.ko_detected is False

    def test_identical_coord_no_longer_false_positive(self):
        """After NF-02 fix, identical coordinates are not adjacent,
        so PV like [D4, D4, D4] should NOT trigger ko via adjacency.
        (Repeated coord at gap=2 requires the between-move to be adjacent.)
        """
        # D4 at index 0 and 2, with D4 between them — D4-D4 is NOT adjacent (distance 0)
        pv = ["D4", "D4", "D4"]
        result = detect_ko_in_pv(pv, initial_stones=None)
        # Between-move D4 is not adjacent to repeated-move D4 (same coord), so no ko
        assert result.ko_detected is False

    def test_validate_ko_threads_position_to_detect(self):
        """validate_ko passes position's stones through to detect_ko_in_pv."""
        from config import load_enrichment_config
        from models.analysis_response import AnalysisResponse, MoveAnalysis
        from models.position import Color, Position, Stone

        config = load_enrichment_config()
        position = Position(
            board_size=9,
            stones=[
                Stone(color=Color.BLACK, x=0, y=0),
                Stone(color=Color.WHITE, x=0, y=1),
                Stone(color=Color.BLACK, x=1, y=0),
            ],
            player_to_move=Color.BLACK,
        )

        response = AnalysisResponse(
            request_id="test",
            move_infos=[
                MoveAnalysis(
                    move="A1", visits=100, winrate=0.85, policy_prior=0.6,
                    pv=["A1", "B1", "A1", "B1"],
                )
            ],
            root_winrate=0.80, root_score=0.0, total_visits=200,
        )

        captured_calls: list[dict] = []
        original_detect = detect_ko_in_pv

        def _spy_detect(pv, config=None, initial_stones=None,
                        first_player_color="B", board_size=19):
            captured_calls.append({
                "initial_stones": initial_stones,
                "first_player_color": first_player_color,
                "board_size": board_size,
            })
            return original_detect(
                pv, config=config, initial_stones=initial_stones,
                first_player_color=first_player_color, board_size=board_size,
            )

        with patch("analyzers.ko_validation.detect_ko_in_pv", side_effect=_spy_detect):
            result = validate_ko(
                response=response, correct_move_gtp="A1",
                ko_type=KoType.DIRECT, config=config, position=position,
            )

        assert isinstance(result.status, ValidationStatus)
        assert len(captured_calls) >= 1
        first_call = captured_calls[0]
        assert first_call["initial_stones"] == {(0, 0): "B", (0, 1): "W", (1, 0): "B"}
        assert first_call["first_player_color"] == "B"
        assert first_call["board_size"] == 9


# ===================================================================
# Terminal detection config decoupling
# ===================================================================


@pytest.mark.unit
class TestTerminalDetectionConfigDecoupling:
    """Verify terminal_detection_enabled independently controls gates."""

    def test_gates_disabled_queries_not_short_circuited(self):
        """With terminal_detection_enabled=False, gates do NOT fire even when
        board_state and puzzle_region exist. Compare against gate-enabled run.
        """
        puzzle_region = frozenset({(15, 3), (15, 4), (16, 3), (16, 4)})

        # Run WITH gates enabled — interior-point fires immediately → 0 queries
        engine1, counter1 = _make_engine_counting_queries()
        config1 = _make_config(
            max_depth=5, min_depth=1,
            transposition_enabled=True,
            terminal_detection_enabled=True,
        )
        budget1 = QueryBudget(total=50)

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
            return_value=set(),
        ), patch(
            "analyzers.benson_check.check_interior_point_death",
            return_value=True,
        ):
            build_solution_tree(
                engine=engine1, initial_moves=[], correct_move_gtp="D4",
                player_color="B", config=config1, level_slug="elementary",
                query_budget=budget1, puzzle_id="test-gates-on",
                puzzle_region=puzzle_region,
            )
        queries_with_gates = counter1["n"]

        # Run WITHOUT gates — terminal_detection_enabled=False
        engine2, counter2 = _make_engine_counting_queries()
        config2 = _make_config(
            max_depth=5, min_depth=1,
            transposition_enabled=True,
            terminal_detection_enabled=False,
        )
        budget2 = QueryBudget(total=50)

        build_solution_tree(
            engine=engine2, initial_moves=[], correct_move_gtp="D4",
            player_color="B", config=config2, level_slug="elementary",
            query_budget=budget2, puzzle_id="test-gates-off",
            puzzle_region=puzzle_region,
        )
        queries_without_gates = counter2["n"]

        # Gates-disabled should use MORE queries (no short-circuit)
        assert queries_without_gates > queries_with_gates, (
            f"Gates-disabled ({queries_without_gates}) should use more queries "
            f"than gates-enabled ({queries_with_gates})"
        )

    def test_transposition_disabled_gates_still_fire(self):
        """With transposition_enabled=False but terminal_detection_enabled=True,
        Benson gate fires (board_state initialized for gate support).
        """
        engine, counter = _make_engine_counting_queries()
        config = _make_config(
            max_depth=5, min_depth=1,
            transposition_enabled=False,
            terminal_detection_enabled=True,
        )
        budget = QueryBudget(total=50)
        puzzle_region = frozenset({(15, 3), (15, 4), (16, 3), (16, 4)})
        alive_group = frozenset({(15, 3), (15, 4), (16, 3), (16, 4)})

        def _mock_alive(stones_dict, board_size):
            return {alive_group}

        def _mock_interior(stones_dict, defender_color, puzzle_region, board_size):
            return False

        with patch(
            "analyzers.benson_check.find_unconditionally_alive_groups",
            side_effect=_mock_alive,
        ), patch(
            "analyzers.benson_check.check_interior_point_death",
            side_effect=_mock_interior,
        ):
            root = build_solution_tree(
                engine=engine,
                initial_moves=[],
                correct_move_gtp="A1",
                player_color="B",
                config=config,
                level_slug="elementary",
                query_budget=budget,
                puzzle_id="test-tp-off-gates-on",
                puzzle_region=puzzle_region,
            )

        assert root is not None
        # Gate fires at depth=2 (after root query at depth=1)
        assert counter["n"] == 1, (
            f"Expected 1 query when gates enabled + transposition disabled, got {counter['n']}"
        )


# ===================================================================
# RC-2 / RC-5: Unmocked Benson gate tests — real algorithm, real _BoardState
# ===================================================================


@pytest.mark.unit
class TestBensonGateUnmocked:
    """Exercise the real Benson algorithm through solve_position's gate path.

    These tests do NOT mock benson_check functions. They validate that
    _BoardState coordinate encoding is compatible with benson_check.py's
    expected (row, col) format.
    """

    def test_unmocked_alive_group_fires_gate(self):
        """RC-2: Known unconditionally-alive position triggers Benson gate.

        Build a 5x5 board where White has a group with two clear eyes,
        then verify the gate fires (fewer queries) without mocking.

        Board (5x5):
           0 1 2 3 4
        0  . W W W .
        1  W . W . W
        2  W W W W W
        3  . . . . .
        4  . . . . .

        White eyes at (1,1) and (1,3). Puzzle player is Black (attacker),
        defender is White. Contest group = White stones in puzzle_region.
        Benson should find White unconditionally alive → gate fires.
        """
        from models.position import Color, Position, Stone

        # Build position with White two-eye shape
        white_stones = []
        # Row 0: W at (x=1,y=0), (x=2,y=0), (x=3,y=0)
        for x in [1, 2, 3]:
            white_stones.append(Stone(color=Color.WHITE, x=x, y=0))
        # Row 1: W at (x=0,y=1), (x=2,y=1), (x=4,y=1)
        for x in [0, 2, 4]:
            white_stones.append(Stone(color=Color.WHITE, x=x, y=1))
        # Row 2: W at all columns
        for x in range(5):
            white_stones.append(Stone(color=Color.WHITE, x=x, y=2))

        engine, counter = _make_engine_counting_queries(board_size=5)
        engine._raw_position = Position(
            board_size=5,
            stones=white_stones,
            player_to_move=Color.BLACK,
        )

        config = _make_config(max_depth=3, min_depth=1, terminal_detection_enabled=True)
        budget = QueryBudget(total=20)

        # puzzle_region covers the White group area in (row, col) format
        # Row 0-2, Col 0-4 — matches where _BoardState places stones via
        # add_initial_stone(color, x, y) which sets grid[y][x]
        puzzle_region = frozenset(
            (r, c) for r in range(3) for c in range(5)
        )

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="A5",  # Black plays at row 4
            player_color="B",
            config=config,
            level_slug="novice",
            query_budget=budget,
            puzzle_id="test-unmocked-alive",
            puzzle_region=puzzle_region,
        )

        assert root is not None
        # The Benson gate should have fired, reducing total queries.
        # Without the gate, max_depth=3 would produce multiple queries.
        # With the gate, White is alive → short circuit at depth 2.
        # At minimum we expect the gate to have saved some queries.
        assert budget.used <= 1, (
            f"Expected Benson gate to fire (≤1 query), got {budget.used} queries. "
            "This may indicate a coordinate mismatch between _BoardState and benson_check."
        )

    def test_unmocked_one_eye_group_does_not_fire_gate(self):
        """RC-5: Known single-eye position does NOT trigger Benson gate.

        Build a 7x7 board where White has only one enclosed eye and
        Black stones break the exterior enclosure.

        Board (7x7):
           0 1 2 3 4 5 6
        0  . . . . . . .
        1  . W W W W W .
        2  . W . W W W .
        3  . W W W W W .
        4  . B . . . B .
        5  . . . . . . .
        6  . . . . . . .

        White eye at (2,2) only — row 1 is solid so no second interior eye.
        Black stones at (4,1) and (4,5) break the exterior empty region's
        enclosure by White, so the large external empty area is NOT a vital
        region for White. White has < 2 vital regions → NOT alive.
        """
        from models.position import Color, Position, Stone

        white_stones = []
        # Row 1: W at all cols 1-5
        for x in range(1, 6):
            white_stones.append(Stone(color=Color.WHITE, x=x, y=1))
        # Row 2: W with one eye at (x=2,y=2)
        for x in [1, 3, 4, 5]:
            white_stones.append(Stone(color=Color.WHITE, x=x, y=2))
        # Row 3: W at all cols 1-5
        for x in range(1, 6):
            white_stones.append(Stone(color=Color.WHITE, x=x, y=3))

        # Black stones to break exterior enclosure
        black_stones = [
            Stone(color=Color.BLACK, x=1, y=4),
            Stone(color=Color.BLACK, x=5, y=4),
        ]

        engine, counter = _make_engine_counting_queries(board_size=7)
        engine._raw_position = Position(
            board_size=7,
            stones=white_stones + black_stones,
            player_to_move=Color.BLACK,
        )

        config = _make_config(max_depth=2, min_depth=1, terminal_detection_enabled=True)
        budget = QueryBudget(total=20)

        # puzzle_region covers the White group area
        puzzle_region = frozenset(
            (r, c) for r in range(4) for c in range(7)
        )

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="A7",
            player_color="B",
            config=config,
            level_slug="novice",
            query_budget=budget,
            puzzle_id="test-unmocked-one-eye",
            puzzle_region=puzzle_region,
        )

        assert root is not None
        # Benson gate should NOT fire — White has only 1 interior eye and
        # Black stones break exterior enclosure.
        assert budget.used >= 1, (
            f"Expected ≥1 engine query (Benson should NOT fire for 1-eye group), "
            f"got {budget.used}. Gate may have false-positived."
        )
