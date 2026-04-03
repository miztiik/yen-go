"""Tests for Priority 4/5/6 technique detectors (T47-T49).

Tests eye-shape, vital-point, liberty-shortage, dead-shapes, clamp,
living, corner, shape, endgame, tesuji, under-the-stones, connect-and-die,
joseki, and fuseki detectors using mock data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_lab_root = str(Path(__file__).resolve().parent.parent)

from analyzers.detectors import TechniqueDetector
from analyzers.detectors.clamp_detector import ClampDetector
from analyzers.detectors.connect_and_die_detector import ConnectAndDieDetector
from analyzers.detectors.corner_detector import CornerDetector
from analyzers.detectors.dead_shapes_detector import DeadShapesDetector
from analyzers.detectors.endgame_detector import EndgameDetector
from analyzers.detectors.eye_shape_detector import EyeShapeDetector
from analyzers.detectors.fuseki_detector import FusekiDetector
from analyzers.detectors.joseki_detector import JosekiDetector
from analyzers.detectors.liberty_shortage_detector import LibertyShortageDetector
from analyzers.detectors.living_detector import LivingDetector
from analyzers.detectors.shape_detector import ShapeDetector
from analyzers.detectors.tesuji_detector import TesujiDetector
from analyzers.detectors.under_the_stones_detector import UnderTheStonesDetector
from analyzers.detectors.vital_point_detector import VitalPointDetector
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
def corner_position() -> Position:
    """Stones clustered in top-left corner."""
    return Position(
        board_size=19,
        stones=[
            Stone(color=Color.BLACK, x=2, y=2),
            Stone(color=Color.BLACK, x=3, y=2),
            Stone(color=Color.WHITE, x=2, y=3),
            Stone(color=Color.WHITE, x=3, y=3),
            Stone(color=Color.WHITE, x=4, y=3),
        ],
        player_to_move=Color.BLACK,
    )


# ===========================================================================
# Protocol conformance
# ===========================================================================

class TestProtocolConformance:
    def test_all_p4_p5_p6_detectors_implement_protocol(self):
        detectors = [
            EyeShapeDetector(),
            VitalPointDetector(),
            LibertyShortageDetector(),
            DeadShapesDetector(),
            ClampDetector(),
            LivingDetector(),
            CornerDetector(),
            ShapeDetector(),
            EndgameDetector(),
            TesujiDetector(),
            UnderTheStonesDetector(),
            ConnectAndDieDetector(),
            JosekiDetector(),
            FusekiDetector(),
        ]
        for d in detectors:
            assert isinstance(d, TechniqueDetector), (
                f"{type(d).__name__} does not implement TechniqueDetector"
            )


# ===========================================================================
# T47: Priority 4 — eye-shape
# ===========================================================================

class TestEyeShapeDetector:
    def test_detects_eye_destruction(self, config: EnrichmentConfig):
        """Move surrounded by opponent stones → eye destruction."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=3, y=2),
                Stone(color=Color.WHITE, x=2, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
                Stone(color=Color.WHITE, x=3, y=4),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D16", visits=500, winrate=0.85, pv=["D16"]),
                MoveAnalysis(move="E15", visits=100, winrate=0.40, pv=["E15"]),
            ],
        )
        result = EyeShapeDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "eye-shape"

    def test_no_detection_open_area(self, config: EnrichmentConfig):
        """Move in open area → no eye shape."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=10, y=10)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.7, pv=["D4"]),
            ],
        )
        result = EyeShapeDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T47: Priority 4 — vital-point
# ===========================================================================

class TestVitalPointDetector:
    def test_detects_shared_liberty_point(self, config: EnrichmentConfig):
        """Move adjacent to both friendly and opponent stones → vital point."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=3),  # friendly below
                Stone(color=Color.WHITE, x=4, y=3),  # opponent right
            ],
            player_to_move=Color.BLACK,
        )
        # Move at C16 = (2, 3) ... adjust: D16 = col D=3, row 16 → y=19-16=3
        # Move at D16 (x=3, y=3) is adjacent to C16 (x=2,y=3) and E16 (x=4,y=3)
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D16", visits=500, winrate=0.80, pv=["D16"]),
            ],
        )
        result = VitalPointDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "vital-point"

    def test_no_detection_only_friendly(self, config: EnrichmentConfig):
        """Move adjacent to only friendly stones → no vital point."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=3),
                Stone(color=Color.BLACK, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D16", visits=500, winrate=0.80, pv=["D16"]),
            ],
        )
        result = VitalPointDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T47: Priority 4 — liberty-shortage
# ===========================================================================

class TestLibertyShortageDetector:
    def test_detects_group_with_few_liberties(self, config: EnrichmentConfig):
        """Group with 1-2 liberties near move → liberty shortage."""
        # White group at E16, E15 with Black surrounding
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=4, y=3),   # E16
                Stone(color=Color.WHITE, x=4, y=4),   # E15
                Stone(color=Color.BLACK, x=3, y=3),   # D16
                Stone(color=Color.BLACK, x=3, y=4),   # D15
                Stone(color=Color.BLACK, x=5, y=3),   # F16
                Stone(color=Color.BLACK, x=5, y=4),   # F15
                Stone(color=Color.BLACK, x=4, y=2),   # E17
            ],
            player_to_move=Color.BLACK,
        )
        # Move at E14 (x=4, y=5) — adjacent to the White group
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="E14", visits=500, winrate=0.90, pv=["E14"]),
            ],
        )
        result = LibertyShortageDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "liberty-shortage"

    def test_no_detection_many_liberties(self, config: EnrichmentConfig):
        """Isolated stone with many liberties → no shortage."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=10, y=10)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="L10", visits=500, winrate=0.70, pv=["L10"]),
            ],
        )
        result = LibertyShortageDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T47: Priority 4 — dead-shapes
# ===========================================================================

class TestDeadShapesDetector:
    def test_detects_straight_four(self, config: EnrichmentConfig):
        """Four opponent stones in a line → dead shape."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=3, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
                Stone(color=Color.WHITE, x=5, y=3),
                Stone(color=Color.WHITE, x=6, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="E16", visits=500, winrate=0.85, pv=["E16"]),
            ],
        )
        result = DeadShapesDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "dead-shapes"

    def test_no_detection_few_stones(self, config: EnrichmentConfig):
        """Only 2 opponent stones → no dead shape."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=3, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D16", visits=500, winrate=0.85, pv=["D16"]),
            ],
        )
        result = DeadShapesDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T47: Priority 4 — clamp
# ===========================================================================

class TestClampDetector:
    def test_detects_second_line_clamp(self, config: EnrichmentConfig):
        """Move on 2nd line between opponent stones → clamp."""
        # B1 = (1, 18), opponent stones at A1=(0,18) and C1=(2,18)
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=0, y=18),  # A1
                Stone(color=Color.WHITE, x=2, y=18),  # C1
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="B1", visits=500, winrate=0.75,
                    policy_prior=0.05, pv=["B1", "A2"],
                ),
            ],
        )
        result = ClampDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "clamp"

    def test_no_detection_center_move(self, config: EnrichmentConfig):
        """Move in center → no clamp."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=9, y=9),
                Stone(color=Color.WHITE, x=11, y=9),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="K10", visits=500, winrate=0.75,
                    policy_prior=0.05, pv=["K10"],
                ),
            ],
        )
        result = ClampDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — living
# ===========================================================================

class TestLivingDetector:
    def test_detects_living_with_ownership(self, config: EnrichmentConfig):
        """High winrate + strong ownership → living."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=2),
                Stone(color=Color.BLACK, x=3, y=2),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.92,
                    pv=["D4", "E4"],
                    ownership=[[0.8, 0.7], [-0.3, -0.2]],
                ),
            ],
        )
        result = LivingDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "living"

    def test_no_detection_low_winrate(self, config: EnrichmentConfig):
        """Low winrate → no living."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=2, y=2)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.40, pv=["D4"]),
            ],
        )
        result = LivingDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — corner
# ===========================================================================

class TestCornerDetector:
    def test_detects_corner_position(
        self, corner_position: Position, config: EnrichmentConfig
    ):
        """Stones in TL corner → corner detected."""
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.7, pv=["D4"]),
            ],
        )
        result = CornerDetector().detect(corner_position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "corner"
        assert "TL" in result.evidence

    def test_no_detection_center_position(self, config: EnrichmentConfig):
        """Stones in center → no corner."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=9, y=9),
                Stone(color=Color.BLACK, x=10, y=9),
                Stone(color=Color.WHITE, x=9, y=10),
                Stone(color=Color.WHITE, x=10, y=10),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="K10", visits=500, winrate=0.7, pv=["K10"]),
            ],
        )
        result = CornerDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — shape
# ===========================================================================

class TestShapeDetector:
    def test_detects_tiger_mouth(self, config: EnrichmentConfig):
        """Move at (3,3) with friendly at (4,3) and (3,4) → tiger mouth."""
        # D16 = (3, 3), E16 = (4, 3), D15 = (3, 4)
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=4, y=3),   # E16
                Stone(color=Color.BLACK, x=3, y=4),   # D15
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D16", visits=500, winrate=0.7, pv=["D16"]),
            ],
        )
        result = ShapeDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "shape"

    def test_no_detection_no_pattern(self, config: EnrichmentConfig):
        """Move with no adjacent friendly stones → no shape."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=15, y=15)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.7, pv=["D4"]),
            ],
        )
        result = ShapeDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — endgame
# ===========================================================================

class TestEndgameDetector:
    def test_detects_endgame_high_density(self, config: EnrichmentConfig):
        """High stone density + edge move + small score diff → endgame."""
        # Create a dense position (~30% density on 9x9)
        stones = []
        for x in range(5):
            for y in range(5):
                c = Color.BLACK if (x + y) % 2 == 0 else Color.WHITE
                stones.append(Stone(color=c, x=x, y=y))
        position = Position(board_size=9, stones=stones, player_to_move=Color.BLACK)

        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="A1", visits=500, winrate=0.55,
                    score_lead=2.0, pv=["A1", "B1"],
                ),
                MoveAnalysis(
                    move="B1", visits=300, winrate=0.50,
                    score_lead=0.5, pv=["B1"],
                ),
            ],
        )
        result = EndgameDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "endgame"

    def test_no_detection_sparse_board(self, config: EnrichmentConfig):
        """Low stone density → no endgame."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),
                Stone(color=Color.WHITE, x=15, y=15),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="K10", visits=500, winrate=0.55, pv=["K10"]),
            ],
        )
        result = EndgameDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — tesuji
# ===========================================================================

class TestTesujiDetector:
    def test_detects_tesuji_multiple_signals(self, config: EnrichmentConfig):
        """Low policy + high winrate + long PV + large delta → tesuji."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=3, y=3)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=800, winrate=0.92,
                    policy_prior=0.03,
                    pv=["D4", "E4", "D3", "E3", "D2"],
                ),
                MoveAnalysis(
                    move="E5", visits=100, winrate=0.40,
                    policy_prior=0.15, pv=["E5"],
                ),
            ],
        )
        result = TesujiDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "tesuji"

    def test_no_detection_obvious_move(self, config: EnrichmentConfig):
        """High policy (obvious move) → no tesuji."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=3, y=3)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=800, winrate=0.60,
                    policy_prior=0.50, pv=["D4", "E4"],
                ),
                MoveAnalysis(
                    move="E5", visits=600, winrate=0.55,
                    policy_prior=0.30, pv=["E5"],
                ),
            ],
        )
        result = TesujiDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — under-the-stones
# ===========================================================================

class TestUnderTheStonesDetector:
    def test_detects_sacrifice_revisit_pattern(self, config: EnrichmentConfig):
        """Low policy + PV revisiting area → under-the-stones."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=3, y=3)],
            player_to_move=Color.BLACK,
        )
        # PV: D4, E4(opp), D3(player, adjacent to D4), E3(opp), D2
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D16", visits=500, winrate=0.85,
                    policy_prior=0.04,
                    pv=["D16", "E16", "D15", "E15", "D14"],
                ),
            ],
        )
        result = UnderTheStonesDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "under-the-stones"

    def test_no_detection_high_policy(self, config: EnrichmentConfig):
        """High policy → no sacrifice → no under-the-stones."""
        position = Position(
            board_size=19,
            stones=[Stone(color=Color.BLACK, x=3, y=3)],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4", visits=500, winrate=0.85,
                    policy_prior=0.50, pv=["D4", "E4", "D3", "E3"],
                ),
            ],
        )
        result = UnderTheStonesDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T48: Priority 5 — connect-and-die
# ===========================================================================

class TestConnectAndDieDetector:
    def test_detects_connect_and_die(self, config: EnrichmentConfig):
        """Move adjacent to 2 separate opponent groups + high winrate."""
        # Two separate White groups: one at (2,3) and one at (4,3)
        # with gap at (3,3) where Black plays
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=2, y=3),   # group 1
                Stone(color=Color.WHITE, x=4, y=3),   # group 2 (separate)
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D16", visits=500, winrate=0.90,
                    pv=["D16", "E16"],
                ),
            ],
        )
        result = ConnectAndDieDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "connect-and-die"

    def test_no_detection_single_group(self, config: EnrichmentConfig):
        """Move adjacent to only 1 opponent group → no connect-and-die."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=2, y=3),
                Stone(color=Color.WHITE, x=3, y=3),  # connected to above
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="E16", visits=500, winrate=0.90,
                    pv=["E16"],
                ),
            ],
        )
        result = ConnectAndDieDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T49: Priority 6 — joseki
# ===========================================================================

class TestJosekiDetector:
    def test_detects_joseki_corner_opening(self, config: EnrichmentConfig):
        """Few stones in corner with balanced colors → joseki."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),   # D16 (4-4)
                Stone(color=Color.WHITE, x=2, y=3),   # C16
                Stone(color=Color.BLACK, x=3, y=2),   # D17
                Stone(color=Color.WHITE, x=4, y=3),   # E16
                Stone(color=Color.BLACK, x=3, y=4),   # D15
                Stone(color=Color.WHITE, x=2, y=2),   # C17
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D14", visits=500, winrate=0.55, pv=["D14"]),
            ],
        )
        result = JosekiDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "joseki"
        assert result.confidence <= 0.50

    def test_no_detection_too_many_stones(self, config: EnrichmentConfig):
        """Many stones → not joseki."""
        stones = [
            Stone(color=Color.BLACK if i % 2 == 0 else Color.WHITE, x=i % 19, y=i // 19)
            for i in range(25)
        ]
        position = Position(board_size=19, stones=stones, player_to_move=Color.BLACK)
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.55, pv=["D4"]),
            ],
        )
        result = JosekiDetector().detect(position, analysis, None, config)
        assert result.detected is False


# ===========================================================================
# T49: Priority 6 — fuseki
# ===========================================================================

class TestFusekiDetector:
    def test_detects_fuseki_sparse_spread(self, config: EnrichmentConfig):
        """Very few stones spread across board → fuseki."""
        position = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),    # TL corner area
                Stone(color=Color.WHITE, x=15, y=3),   # TR corner area
                Stone(color=Color.BLACK, x=3, y=15),   # BL corner area
                Stone(color=Color.WHITE, x=15, y=15),  # BR corner area
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="K10", visits=500, winrate=0.52, pv=["K10"]),
            ],
        )
        result = FusekiDetector().detect(position, analysis, None, config)
        assert result.detected is True
        assert result.tag_slug == "fuseki"
        assert result.confidence <= 0.40

    def test_no_detection_high_density(self, config: EnrichmentConfig):
        """High stone density → not fuseki."""
        stones = []
        for x in range(9):
            for y in range(4):
                c = Color.BLACK if (x + y) % 2 == 0 else Color.WHITE
                stones.append(Stone(color=c, x=x, y=y))
        position = Position(board_size=19, stones=stones, player_to_move=Color.BLACK)
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="K10", visits=500, winrate=0.52, pv=["K10"]),
            ],
        )
        result = FusekiDetector().detect(position, analysis, None, config)
        assert result.detected is False
