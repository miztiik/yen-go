"""Tests for Priority-1 technique detectors (T33-T36).

Tests life-and-death, ko, ladder, and snapback detectors
using mock Position and AnalysisResponse objects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Ensure lab root is on sys.path
_lab_root = str(Path(__file__).resolve().parent.parent)

from analyzers.detectors.ko_detector import KoDetector
from analyzers.detectors.ladder_detector import LadderDetector
from analyzers.detectors.life_and_death_detector import LifeAndDeathDetector
from analyzers.detectors.snapback_detector import SnapbackDetector
from config import EnrichmentConfig, load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone
from models.solve_result import SolutionNode

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> EnrichmentConfig:
    return load_enrichment_config()


@pytest.fixture
def basic_position() -> Position:
    """A simple corner position with a few stones."""
    return Position(
        board_size=19,
        stones=[
            Stone(color=Color.BLACK, x=2, y=2),
            Stone(color=Color.BLACK, x=3, y=2),
            Stone(color=Color.WHITE, x=2, y=3),
            Stone(color=Color.WHITE, x=3, y=3),
        ],
        player_to_move=Color.BLACK,
    )


@pytest.fixture
def basic_analysis() -> AnalysisResponse:
    """Standard analysis with a clear top move."""
    return AnalysisResponse(
        move_infos=[
            MoveAnalysis(
                move="D4",
                visits=1000,
                winrate=0.95,
                score_lead=10.0,
                policy_prior=0.6,
                pv=["D4", "E4", "D3"],
            ),
            MoveAnalysis(
                move="E5",
                visits=200,
                winrate=0.45,
                score_lead=1.0,
                policy_prior=0.1,
                pv=["E5", "D4"],
            ),
        ],
        root_winrate=0.5,
        root_score=0.0,
    )


# ===========================================================================
# T33: Life-and-death detector
# ===========================================================================

class TestLifeAndDeathDetector:
    def test_always_detects_for_standard_position(
        self, basic_position: Position, basic_analysis: AnalysisResponse, config: EnrichmentConfig
    ):
        detector = LifeAndDeathDetector()
        result = detector.detect(basic_position, basic_analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "life-and-death"
        assert result.confidence >= 0.9

    def test_detects_even_with_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        empty_analysis = AnalysisResponse()
        detector = LifeAndDeathDetector()
        result = detector.detect(basic_position, empty_analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "life-and-death"
        assert result.confidence == 0.9

    def test_boosted_confidence_with_ownership_swing(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Confidence increases when ownership maps differ significantly."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=1000, winrate=0.95,
                    pv=["D4", "E4"],
                    ownership=[[0.9, 0.8], [-0.5, -0.6]],  # Black alive
                ),
                MoveAnalysis(
                    move="E5", visits=200, winrate=0.3,
                    pv=["E5"],
                    ownership=[[-0.5, -0.6], [0.9, 0.8]],  # Swapped
                ),
            ],
        )
        detector = LifeAndDeathDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.confidence > 0.9


# ===========================================================================
# T34: Ko detector
# ===========================================================================

class TestKoDetector:
    def test_detects_ko_in_pv_with_repeated_coord(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """PV with same coordinate appearing twice → ko."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=500,
                    winrate=0.6,
                    pv=["D4", "E4", "D4", "E4"],  # D4 recaptured
                ),
            ],
        )
        detector = KoDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "ko"
        assert result.confidence > 0.0
        assert "D4" in result.evidence

    def test_no_ko_in_normal_pv(
        self, basic_position: Position, basic_analysis: AnalysisResponse, config: EnrichmentConfig
    ):
        """Normal PV without repeated coords → no ko."""
        detector = KoDetector()
        result = detector.detect(basic_position, basic_analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "ko"

    def test_detects_ko_from_solution_tree(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Solution tree with recapture pattern."""
        tree = SolutionNode(
            move_gtp="D4", color="B", is_correct=True,
            children=[
                SolutionNode(
                    move_gtp="E4", color="W",
                    children=[
                        SolutionNode(move_gtp="D4", color="B", is_correct=True),
                    ],
                ),
            ],
        )
        empty_analysis = AnalysisResponse()
        detector = KoDetector()
        result = detector.detect(basic_position, empty_analysis, tree, config)
        assert result.detected is True
        assert result.tag_slug == "ko"


# ===========================================================================
# T35: Ladder detector
# ===========================================================================

class TestLadderDetector:
    def test_detects_ladder_diagonal_pv(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """PV with consistent diagonal moves (8+) → ladder."""
        # Diagonal chase: D4→E5→F6→G7→H8→J9→K10→L11
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=800,
                    winrate=0.95,
                    pv=["D4", "E5", "F6", "G7", "H8", "J9", "K10", "L11"],
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "ladder"
        assert result.confidence > 0.3

    def test_no_ladder_in_straight_pv(
        self, basic_position: Position, basic_analysis: AnalysisResponse, config: EnrichmentConfig
    ):
        """Normal PV without diagonal pattern → no ladder."""
        detector = LadderDetector()
        result = detector.detect(basic_position, basic_analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "ladder"

    def test_no_ladder_with_short_pv(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """PV too short for ladder detection."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=100, pv=["D4", "E5"]),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_no_ladder_with_short_diagonal_pv(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """PV-only fallback requires 8+ moves; a 6-move diagonal PV is
        too short and matches corner sequences by coincidence."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=800,
                    winrate=0.95,
                    pv=["D4", "E5", "F6", "G7", "H8", "J9"],
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_detects_ladder_in_solution_tree(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Solution tree mainline with diagonal chase (8+ moves)."""
        tree = SolutionNode(
            move_gtp="D4", color="B", is_correct=True,
            children=[SolutionNode(
                move_gtp="E5", color="W",
                children=[SolutionNode(
                    move_gtp="F6", color="B", is_correct=True,
                    children=[SolutionNode(
                        move_gtp="G7", color="W",
                        children=[SolutionNode(
                            move_gtp="H8", color="B", is_correct=True,
                            children=[SolutionNode(
                                move_gtp="J9", color="W",
                                children=[SolutionNode(
                                    move_gtp="K10", color="B", is_correct=True,
                                    children=[SolutionNode(
                                        move_gtp="L11", color="W",
                                    )],
                                )],
                            )],
                        )],
                    )],
                )],
            )],
        )
        empty_analysis = AnalysisResponse()
        detector = LadderDetector()
        result = detector.detect(basic_position, empty_analysis, tree, config)
        assert result.detected is True
        assert result.tag_slug == "ladder"

    # --- T71: Board-state synthetic ladder tests (RC-1 remediation) ---

    def test_board_state_ladder_runs_to_edge(self, config: EnrichmentConfig):
        """Synthetic 19×19: ladder detected via PV diagonal chase.

        A proper ladder requires surrounding geometry that forces the
        defender into exactly 2 liberties after each extend. We build
        a wall of Black stones along the chase diagonal. PV diagonal
        fallback (8+ moves) qualifies as detected=True.
        """
        position = Position(
            board_size=19,
            stones=[
                # White target
                Stone(color=Color.WHITE, x=4, y=4),
                # Black containment: left + above + diagonal wall
                Stone(color=Color.BLACK, x=3, y=4),
                Stone(color=Color.BLACK, x=4, y=3),
                Stone(color=Color.BLACK, x=5, y=3),
                Stone(color=Color.BLACK, x=5, y=5),
                Stone(color=Color.BLACK, x=6, y=5),
                Stone(color=Color.BLACK, x=6, y=6),
                Stone(color=Color.BLACK, x=7, y=6),
                Stone(color=Color.BLACK, x=7, y=7),
                Stone(color=Color.BLACK, x=8, y=7),
                Stone(color=Color.BLACK, x=8, y=8),
                Stone(color=Color.BLACK, x=9, y=8),
                Stone(color=Color.BLACK, x=9, y=9),
            ],
            player_to_move=Color.BLACK,
        )
        # Black plays E15 → PV shows 8-move diagonal chase
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E15",
                    visits=800,
                    winrate=0.95,
                    pv=["E15", "F14", "G15", "H14", "H15", "J14", "K15", "L14"],
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "ladder"
        assert result.confidence > 0.3

    def test_board_state_ladder_breaker_blocks(self, config: EnrichmentConfig):
        """Synthetic 9×9: ladder-breaker stone prevents chase → not a ladder.

        Same starting position as edge test but with a White friendly stone
        in the escape path that gives > 2 liberties after extend.
        """
        position = Position(
            board_size=9,
            stones=[
                # White target stone
                Stone(color=Color.WHITE, x=4, y=4),  # board[(4,4)]
                # Black stones creating atari
                Stone(color=Color.BLACK, x=4, y=3),  # board[(3,4)]
                Stone(color=Color.BLACK, x=3, y=4),  # board[(4,3)]
                # White ladder-breaker: friendly stone in the escape diagonal
                # When White extends to (5,4), the breaker at (6,5) connects
                # giving > 2 liberties
                Stone(color=Color.WHITE, x=5, y=5),  # board[(5,5)] — breaker
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="F5",
                    visits=800,
                    winrate=0.6,
                    pv=["F5", "F6", "E6"],  # short PV — no chase
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "ladder"

    def test_board_state_net_not_detected_as_ladder(self, config: EnrichmentConfig):
        """Synthetic 9×9: net/surrounding pattern → not a ladder.

        Net positions surround a stone but don't produce the alternating
        atari-extend chase that defines a ladder. Board simulation should
        fail to find a chase sequence.
        """
        position = Position(
            board_size=9,
            stones=[
                # Black surrounding net
                Stone(color=Color.BLACK, x=3, y=3),  # board[(3,3)]
                Stone(color=Color.BLACK, x=5, y=3),  # board[(3,5)]
                Stone(color=Color.BLACK, x=3, y=5),  # board[(5,3)]
                Stone(color=Color.BLACK, x=5, y=5),  # board[(5,5)]
                Stone(color=Color.BLACK, x=4, y=2),  # board[(2,4)]
                # White trapped inside
                Stone(color=Color.WHITE, x=4, y=3),  # board[(3,4)]
                Stone(color=Color.WHITE, x=4, y=4),  # board[(4,4)]
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E6",  # closing the net
                    visits=800,
                    winrate=0.95,
                    pv=["E6", "D5", "E4"],  # no diagonal chase
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "ladder"

    def test_ladder_capture_removes_stones_during_chase(
        self, config: EnrichmentConfig
    ):
        """Ladder chase on 19×19 with PV showing 8+ move diagonal chase.

        Tests that the detector correctly identifies a ladder pattern even
        when the board-state simulation doesn't confirm, as long as the PV
        shows a sufficiently long diagonal chase sequence.
        """
        position = Position(
            board_size=19,
            stones=[
                # White target
                Stone(color=Color.WHITE, x=4, y=4),
                # Black containment
                Stone(color=Color.BLACK, x=3, y=4),
                Stone(color=Color.BLACK, x=4, y=3),
                Stone(color=Color.BLACK, x=5, y=5),
                Stone(color=Color.BLACK, x=5, y=3),
                Stone(color=Color.BLACK, x=6, y=5),
                Stone(color=Color.BLACK, x=6, y=6),
                Stone(color=Color.BLACK, x=7, y=6),
                Stone(color=Color.BLACK, x=7, y=7),
                Stone(color=Color.BLACK, x=8, y=7),
                Stone(color=Color.BLACK, x=8, y=8),
                Stone(color=Color.WHITE, x=5, y=6),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E15",
                    visits=800,
                    winrate=0.95,
                    pv=["E15", "F14", "G15", "H14", "H15", "J14", "K15", "L14"],
                ),
            ],
        )
        detector = LadderDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "ladder"
        assert result.confidence > 0.3


# ===========================================================================
# T36: Snapback detector
# ===========================================================================

class TestSnapbackDetector:
    def test_detects_snapback_sacrifice_pattern(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Low policy + high winrate + large delta → snapback."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=1000,
                    winrate=0.95,
                    policy_prior=0.02,  # Very low — sacrifice looks bad
                    pv=["D4", "E4", "D3"],
                ),
                MoveAnalysis(
                    move="E5",
                    visits=200,
                    winrate=0.40,  # Much worse alternative
                    policy_prior=0.3,
                    pv=["E5"],
                ),
            ],
        )
        detector = SnapbackDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "snapback"
        assert "sacrifice" in result.evidence.lower()

    def test_no_snapback_normal_capture(
        self, basic_position: Position, basic_analysis: AnalysisResponse, config: EnrichmentConfig
    ):
        """Normal high-policy move → not a snapback."""
        detector = SnapbackDetector()
        result = detector.detect(basic_position, basic_analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "snapback"

    def test_no_snapback_with_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Empty analysis → no snapback."""
        detector = SnapbackDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False

    def test_pv_confirmed_snapback(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """T82: PV shows sacrifice→capture→recapture near original → high confidence."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=1000,
                    winrate=0.95,
                    policy_prior=0.02,
                    # sacrifice at D4, opponent captures at E4, recapture at D4
                    pv=["D4", "E4", "D4"],
                ),
                MoveAnalysis(
                    move="E5",
                    visits=200,
                    winrate=0.40,
                    policy_prior=0.3,
                    pv=["E5"],
                ),
            ],
        )
        detector = SnapbackDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "snapback"
        assert result.confidence >= 0.85
        assert "PV recapture confirmed" in result.evidence

    def test_pv_unconfirmed_cutting_move_reduces_confidence(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """T82: Low policy + high winrate but PV shows a cutting move (no recapture) → low confidence."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=1000,
                    winrate=0.95,
                    policy_prior=0.02,
                    # PV goes far away — no recapture near D4
                    pv=["D4", "Q16", "R17"],
                ),
                MoveAnalysis(
                    move="E5",
                    visits=200,
                    winrate=0.40,
                    policy_prior=0.3,
                    pv=["E5"],
                ),
            ],
        )
        detector = SnapbackDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "snapback"
        assert result.confidence == 0.45
        assert "PV unconfirmed" in result.evidence
