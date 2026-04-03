"""Tests for Priority-3 technique detectors (T42-T46).

Tests seki, nakade, double-atari, sacrifice, and escape detectors
using mock Position and AnalysisResponse objects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_lab_root = str(Path(__file__).resolve().parent.parent)

from analyzers.detectors.double_atari_detector import DoubleAtariDetector
from analyzers.detectors.escape_detector import EscapeDetector
from analyzers.detectors.nakade_detector import NakadeDetector
from analyzers.detectors.sacrifice_detector import SacrificeDetector
from analyzers.detectors.seki_detector import SekiDetector
from config import EnrichmentConfig, load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> EnrichmentConfig:
    return load_enrichment_config()


@pytest.fixture
def basic_position() -> Position:
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


# ===========================================================================
# T42: Seki detector
# ===========================================================================

class TestSekiDetector:
    def test_detects_seki_balanced_winrate(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Winrate near 50% + low score → seki."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.50,
                    score_lead=1.0, policy_prior=0.3, pv=["D4", "E4"],
                ),
                MoveAnalysis(
                    move="E5", visits=400, winrate=0.48,
                    score_lead=0.5, pv=["E5"],
                ),
            ],
        )
        detector = SekiDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "seki"
        assert result.confidence > 0.5

    def test_no_seki_high_winrate(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """High winrate → not seki."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.95,
                    score_lead=10.0, pv=["D4"],
                ),
            ],
        )
        detector = SekiDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "seki"

    def test_no_seki_high_score_lead(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Winrate near 50% but high score lead → not seki."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.50,
                    score_lead=20.0, pv=["D4"],
                ),
            ],
        )
        detector = SekiDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_no_seki_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        detector = SekiDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False

    def test_seki_boosted_by_ownership_contestation(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Ownership data with many contested points boosts confidence."""
        # 19*19=361 ownership values, all near 0 (contested)
        ownership = [0.1] * 361
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.50,
                    score_lead=1.0, pv=["D4"],
                ),
            ],
            ownership=ownership,
        )
        detector = SekiDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.confidence > 0.65  # boosted


# ===========================================================================
# T43: Nakade detector
# ===========================================================================

class TestNakadeDetector:
    def test_detects_nakade_surrounded_by_opponent(
        self, config: EnrichmentConfig
    ):
        """Move surrounded by 3+ opponent stones → nakade.

        Position: White stones surround D16 (x=3,y=3) on three sides.
        D16 in GTP = x=3, y=19-16=3.
        Neighbors of (3,3): (3,2),(3,4),(2,3),(4,3).
        White on (3,2),(2,3),(4,3) = 3 opponent neighbors.
        """
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=3, y=2),  # above D16
                Stone(color=Color.WHITE, x=2, y=3),  # left of D16
                Stone(color=Color.WHITE, x=4, y=3),  # right of D16
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D16", visits=500, winrate=0.90,
                    policy_prior=0.4, pv=["D16", "E16"],
                ),
            ],
        )
        detector = NakadeDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "nakade"

    def test_no_nakade_few_opponent_neighbors(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Move with only 1 opponent neighbor → not nakade."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.90, pv=["D4"],
                ),
            ],
        )
        detector = NakadeDetector()
        result = detector.detect(basic_position, analysis, None, config)
        # D4 = (3,15); neighbors at (3,14)=nothing, (3,16)=nothing, (2,15)=nothing, (4,15)=nothing
        # The basic_position stones are at (2,2),(3,2),(2,3),(3,3) — far from D4
        assert result.detected is False

    def test_no_nakade_low_winrate(self, config: EnrichmentConfig):
        """Surrounded but low winrate → not nakade."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=3, y=2),
                Stone(color=Color.WHITE, x=2, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D16", visits=500, winrate=0.30, pv=["D16"],
                ),
            ],
        )
        detector = NakadeDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False

    def test_no_nakade_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        detector = NakadeDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False


# ===========================================================================
# T44: Double-atari detector
# ===========================================================================

class TestDoubleAtariDetector:
    def test_detects_double_atari(self, config: EnrichmentConfig):
        """E16 puts two white groups in atari.

        Board (19×19, 0-indexed):
        White group A: (3,3) with liberties at (3,2),(2,3) → after move at (4,3),
        Group A has (3,2),(2,3) minus (4,3) occupied = still (3,2),(2,3).

        Simpler setup: two separate white stones each with 2 liberties,
        and placing Black at a shared liberty puts both in atari.

        White stone at (5,3) — liberties: (4,3),(6,3),(5,2),(5,4)
        White stone at (3,3) — liberties: (2,3),(4,3),(3,2),(3,4)
        Black move at E16 = (4,3):
          Group at (5,3): liberties = (6,3),(5,2),(5,4) = 3 ... too many.

        Better: force each group to have exactly 2 liberties before the move,
        sharing one liberty (the move point), leaving 1 liberty after.

        Group A: W(5,3) with B(6,3),B(5,2) around it.
          Liberties before: (4,3),(5,4) = 2
          After B at (4,3): liberties = (5,4) = 1 → atari!

        Group B: W(3,3) with B(2,3),B(3,2) around it.
          Liberties before: (4,3),(3,4) = 2
          After B at (4,3): liberties = (3,4) = 1 → atari!
        """
        position = Position(
            board_size=19,
            stones=[
                # Group A: single white stone at (5,3)
                Stone(color=Color.WHITE, x=5, y=3),
                Stone(color=Color.BLACK, x=6, y=3),  # block liberty
                Stone(color=Color.BLACK, x=5, y=2),  # block liberty
                # Group B: single white stone at (3,3)
                Stone(color=Color.WHITE, x=3, y=3),
                Stone(color=Color.BLACK, x=2, y=3),  # block liberty
                Stone(color=Color.BLACK, x=3, y=2),  # block liberty
            ],
            player_to_move=Color.BLACK,
        )
        # Move E16 = (4,3) shares a liberty with both groups
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E16", visits=500, winrate=0.95,
                    policy_prior=0.5, pv=["E16"],
                ),
            ],
        )
        detector = DoubleAtariDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "double-atari"
        assert "2" in result.evidence  # 2 groups

    def test_no_double_atari_single_group(self, config: EnrichmentConfig):
        """Only one group in atari → not double-atari."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=5, y=3),
                Stone(color=Color.BLACK, x=6, y=3),
                Stone(color=Color.BLACK, x=5, y=2),
                # No second group
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E16", visits=500, winrate=0.95, pv=["E16"],
                ),
            ],
        )
        detector = DoubleAtariDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False

    def test_no_double_atari_low_winrate(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Low winrate → not double atari."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.30, pv=["D4"],
                ),
            ],
        )
        detector = DoubleAtariDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_no_double_atari_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        detector = DoubleAtariDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False


# ===========================================================================
# T45: Sacrifice detector
# ===========================================================================

class TestSacrificeDetector:
    def test_detects_sacrifice_low_policy_high_winrate(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Low policy + high winrate + long PV → sacrifice."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=1000, winrate=0.92,
                    policy_prior=0.03, pv=["D4", "E4", "D3", "E3"],
                ),
                MoveAnalysis(
                    move="E5", visits=200, winrate=0.50,
                    policy_prior=0.25, pv=["E5"],
                ),
            ],
        )
        detector = SacrificeDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "sacrifice"
        assert "sacrifice" in result.evidence.lower()

    def test_no_sacrifice_high_policy(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """High policy → move looks obvious, not a sacrifice."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.95,
                    policy_prior=0.6, pv=["D4", "E4"],
                ),
            ],
        )
        detector = SacrificeDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_no_sacrifice_low_winrate(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        """Low winrate → even if low policy, not a working sacrifice."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.30,
                    policy_prior=0.02, pv=["D4"],
                ),
            ],
        )
        detector = SacrificeDetector()
        result = detector.detect(basic_position, analysis, None, config)
        assert result.detected is False

    def test_no_sacrifice_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        detector = SacrificeDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False


# ===========================================================================
# T46: Escape detector
# ===========================================================================

class TestEscapeDetector:
    def test_detects_escape_liberty_gain(self, config: EnrichmentConfig):
        """Weak group gains liberties after the move → escape.

        Black stones at (3,3),(4,3) with limited liberties.
        Move at E15 = (4,4) extends the group downward.

        Black group: (3,3) and (4,3).
        Surround with white to limit liberties:
        W(2,3), W(5,3), W(3,2), W(4,2) → group libs: (3,4),(4,4) = 2 libs

        After B at (4,4): group = (3,3),(4,3),(4,4)
        Libs: (3,4),(4,5),(5,4) = 3 libs
        Gain = 3-2 = 1. Need gain >= 2.

        Tighter: add W(3,4) to block one more.
        Before: group (3,3),(4,3), libs = (4,4) = 1 lib.
        After B at (4,4): group = (3,3),(4,3),(4,4)
        Libs: (4,5),(5,4) = 2 libs. Gain = 2-1 = ... but we see from (3,4) blocked.
        Wait, (3,4) is White. So group (3,3),(4,3) before:
          neighbors of (3,3): (2,3)=W,(4,3)=B,(3,2)=W,(3,4)=W → no lib from (3,3)
          neighbors of (4,3): (3,3)=B,(5,3)=W,(4,2)=W,(4,4)=empty → lib=(4,4)
          Total: 1 lib
        After B at (4,4): group = (3,3),(4,3),(4,4)
          from (4,4): (3,4)=W, (5,4)=empty, (4,3)=B, (4,5)=empty → libs=(5,4),(4,5)
          Total: 2 libs. Gain = 2-1 = 1. Still only 1.

        Make the group have 1 liberty, and move opens 3+:
        Remove W(3,4), keep it empty. Then group has libs=(3,4),(4,4)=2.
        Add W on more sides... let's use a simpler setup.

        Simpler: single black stone at (4,3) surrounded on 3 sides.
        W(3,3), W(5,3), W(4,2). Libs: (4,4) = 1 lib.
        After B at E15=(4,4): group = (4,3),(4,4).
        Libs from (4,4): (3,4),(5,4),(4,5) = 3. Plus from (4,3): nothing new.
        Total: 3. Gain = 3-1 = 2. ✓
        """
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=4, y=3),   # the weak stone
                Stone(color=Color.WHITE, x=3, y=3),   # block left
                Stone(color=Color.WHITE, x=5, y=3),   # block right
                Stone(color=Color.WHITE, x=4, y=2),   # block above
            ],
            player_to_move=Color.BLACK,
        )
        # Move E15 = (4,4): extends the group, gains liberties
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E15", visits=500, winrate=0.85,
                    policy_prior=0.3, pv=["E15", "D15"],
                ),
            ],
        )
        detector = EscapeDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "escape"
        assert "liberties" in result.evidence.lower()

    def test_no_escape_no_weak_group(
        self, config: EnrichmentConfig
    ):
        """No weak group near the move → not escape."""
        # Stones far from D4
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=15, y=15),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.90, pv=["D4"],
                ),
            ],
        )
        detector = EscapeDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False
        assert result.tag_slug == "escape"

    def test_no_escape_low_winrate(self, config: EnrichmentConfig):
        """Even with weak group, low winrate → not escape."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=4, y=3),
                Stone(color=Color.WHITE, x=3, y=3),
                Stone(color=Color.WHITE, x=5, y=3),
                Stone(color=Color.WHITE, x=4, y=2),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E15", visits=500, winrate=0.30, pv=["E15"],
                ),
            ],
        )
        detector = EscapeDetector()
        result = detector.detect(position, analysis, None, config)
        assert result.detected is False

    def test_no_escape_empty_analysis(
        self, basic_position: Position, config: EnrichmentConfig
    ):
        detector = EscapeDetector()
        result = detector.detect(basic_position, AnalysisResponse(), None, config)
        assert result.detected is False
