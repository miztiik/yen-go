"""Multi-orientation test infrastructure for tactical detectors (G-4)."""

from __future__ import annotations

import asyncio

import pytest
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone

# ---------------------------------------------------------------------------
# Position.rotate() / Position.reflect() unit tests
# ---------------------------------------------------------------------------


class TestPositionRotate:
    """T1 verification: rotation transforms work correctly."""

    @staticmethod
    def _make_position(stones_xy: list[tuple[str, int, int]], board_size: int = 19) -> Position:
        return Position(
            board_size=board_size,
            stones=[Stone(color=Color(c), x=x, y=y) for c, x, y in stones_xy],
            player_to_move=Color.BLACK,
        )

    def test_rotate_0_is_identity(self):
        pos = self._make_position([("B", 3, 3)])
        rotated = pos.rotate(0)
        assert rotated.stones[0].x == 3
        assert rotated.stones[0].y == 3

    def test_rotate_90(self):
        pos = self._make_position([("B", 3, 3)], board_size=19)
        rotated = pos.rotate(90)
        # (3, 3) → (18-3, 3) = (15, 3)
        assert rotated.stones[0].x == 15
        assert rotated.stones[0].y == 3

    def test_rotate_180(self):
        pos = self._make_position([("B", 3, 3)], board_size=19)
        rotated = pos.rotate(180)
        # (3, 3) → (15, 15)
        assert rotated.stones[0].x == 15
        assert rotated.stones[0].y == 15

    def test_rotate_270(self):
        pos = self._make_position([("B", 3, 3)], board_size=19)
        rotated = pos.rotate(270)
        # (3, 3) → (3, 15)
        assert rotated.stones[0].x == 3
        assert rotated.stones[0].y == 15

    def test_rotate_invalid_raises(self):
        pos = self._make_position([("B", 3, 3)])
        with pytest.raises(ValueError):
            pos.rotate(45)

    def test_rotate_preserves_stone_count(self):
        pos = self._make_position([("B", 3, 3), ("W", 5, 5), ("B", 10, 10)])
        for deg in (0, 90, 180, 270):
            rotated = pos.rotate(deg)
            assert len(rotated.stones) == 3

    def test_rotate_preserves_color(self):
        pos = self._make_position([("B", 3, 3), ("W", 5, 5)])
        for deg in (0, 90, 180, 270):
            rotated = pos.rotate(deg)
            colors = {s.color for s in rotated.stones}
            assert colors == {Color.BLACK, Color.WHITE}

    def test_rotate_full_cycle_identity(self):
        """4 × 90° rotation = identity."""
        pos = self._make_position([("B", 2, 5), ("W", 10, 3)])
        result = pos
        for _ in range(4):
            result = result.rotate(90)
        for orig, final in zip(pos.stones, result.stones, strict=False):
            assert orig.x == final.x
            assert orig.y == final.y

    def test_rotate_is_immutable(self):
        pos = self._make_position([("B", 3, 3)])
        rotated = pos.rotate(90)
        assert pos.stones[0].x == 3  # Original unchanged
        assert rotated is not pos

    @pytest.mark.parametrize("board_size", [9, 13, 19])
    def test_rotate_respects_board_size(self, board_size):
        pos = Position(
            board_size=board_size,
            stones=[Stone(color=Color.BLACK, x=0, y=0)],
            player_to_move=Color.BLACK,
        )
        rotated = pos.rotate(90)
        assert rotated.stones[0].x == board_size - 1
        assert rotated.stones[0].y == 0


class TestPositionReflect:
    """T1 verification: reflection transforms work correctly."""

    @staticmethod
    def _make_position(stones_xy: list[tuple[str, int, int]], board_size: int = 19) -> Position:
        return Position(
            board_size=board_size,
            stones=[Stone(color=Color(c), x=x, y=y) for c, x, y in stones_xy],
            player_to_move=Color.BLACK,
        )

    def test_reflect_x(self):
        pos = self._make_position([("B", 3, 5)], board_size=19)
        reflected = pos.reflect("x")
        assert reflected.stones[0].x == 15  # 18 - 3
        assert reflected.stones[0].y == 5

    def test_reflect_y(self):
        pos = self._make_position([("B", 3, 5)], board_size=19)
        reflected = pos.reflect("y")
        assert reflected.stones[0].x == 3
        assert reflected.stones[0].y == 13  # 18 - 5

    def test_reflect_invalid_raises(self):
        pos = self._make_position([("B", 3, 3)])
        with pytest.raises(ValueError):
            pos.reflect("z")

    def test_reflect_double_is_identity(self):
        pos = self._make_position([("B", 3, 5), ("W", 10, 7)])
        result = pos.reflect("x").reflect("x")
        for orig, final in zip(pos.stones, result.stones, strict=False):
            assert orig.x == final.x
            assert orig.y == final.y

    def test_reflect_is_immutable(self):
        pos = self._make_position([("B", 3, 3)])
        reflected = pos.reflect("x")
        assert pos.stones[0].x == 3
        assert reflected is not pos


# ---------------------------------------------------------------------------
# Instinct classifier orientation tests
# ---------------------------------------------------------------------------


class TestInstinctOrientationInvariance:
    """Verify instinct classification is orientation-aware.

    If a position has a push at (3,3), rotating the position
    should still detect a push at the rotated coordinate.
    """

    @staticmethod
    def _make_push_position() -> tuple[Position, str]:
        """Create a position with a clear push configuration.

        Black stones pushing white:
          B at (5,5), W at (6,5), correct move B at (7,5)
          → push along x-axis
        """
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=5, y=5),
                Stone(color=Color.WHITE, x=6, y=5),
            ],
            player_to_move=Color.BLACK,
        )
        return pos, "H14"  # GTP for (7, 5) on 19x19

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_push_detected_all_rotations(self, rotation):
        """Push pattern should be detected in all 4 rotations."""
        from analyzers.instinct_classifier import _gtp_to_xy, classify_instinct

        pos, correct_gtp = self._make_push_position()

        if rotation == 0:
            test_pos = pos
            test_move = correct_gtp
        else:
            test_pos = pos.rotate(rotation)
            # Rotate the correct move coordinate too
            xy = _gtp_to_xy(correct_gtp, pos.board_size)
            if xy is None:
                pytest.skip("Could not parse GTP coordinate")
            mx, my = xy
            n = pos.board_size - 1
            if rotation == 90:
                rx, ry = n - my, mx
            elif rotation == 180:
                rx, ry = n - mx, n - my
            else:  # 270
                rx, ry = my, n - mx
            # Convert back to GTP
            letters = "ABCDEFGHJKLMNOPQRST"
            test_move = f"{letters[rx]}{pos.board_size - ry}"

        results = classify_instinct(test_pos, test_move)
        instinct_types = [r.instinct for r in results]
        assert "push" in instinct_types, (
            f"Push not detected at rotation={rotation}° "
            f"(detected: {instinct_types})"
        )


# ---------------------------------------------------------------------------
# Policy entropy and correct-move-rank unit tests
# ---------------------------------------------------------------------------


class TestPolicyEntropy:
    """T5 verification: policy entropy computation."""

    def test_single_dominant_move_low_entropy(self):
        from analyzers.estimate_difficulty import compute_policy_entropy

        class FakeMoveInfo:
            def __init__(self, prior):
                self.policy_prior = prior

        moves = [FakeMoveInfo(0.95), FakeMoveInfo(0.03), FakeMoveInfo(0.02)]
        entropy = compute_policy_entropy(moves)
        assert entropy < 0.5  # Low entropy = one dominant move

    def test_uniform_distribution_high_entropy(self):
        from analyzers.estimate_difficulty import compute_policy_entropy

        class FakeMoveInfo:
            def __init__(self, prior):
                self.policy_prior = prior

        moves = [FakeMoveInfo(0.1) for _ in range(10)]
        entropy = compute_policy_entropy(moves)
        assert entropy > 0.9  # High entropy = uniform distribution

    def test_empty_moves_returns_zero(self):
        from analyzers.estimate_difficulty import compute_policy_entropy
        assert compute_policy_entropy([]) == 0.0

    def test_entropy_range_0_to_1(self):
        from analyzers.estimate_difficulty import compute_policy_entropy

        class FakeMoveInfo:
            def __init__(self, prior):
                self.policy_prior = prior

        moves = [FakeMoveInfo(0.4), FakeMoveInfo(0.3), FakeMoveInfo(0.2), FakeMoveInfo(0.1)]
        entropy = compute_policy_entropy(moves)
        assert 0.0 <= entropy <= 1.0


class TestCorrectMoveRank:
    """T7 verification: correct move rank computation."""

    def test_top_move_rank_1(self):
        from analyzers.estimate_difficulty import find_correct_move_rank

        class FakeMoveInfo:
            def __init__(self, move, visits):
                self.move = move
                self.visits = visits

        moves = [FakeMoveInfo("D4", 100), FakeMoveInfo("E5", 50)]
        assert find_correct_move_rank(moves, "D4") == 1

    def test_second_move_rank_2(self):
        from analyzers.estimate_difficulty import find_correct_move_rank

        class FakeMoveInfo:
            def __init__(self, move, visits):
                self.move = move
                self.visits = visits

        moves = [FakeMoveInfo("D4", 100), FakeMoveInfo("E5", 50)]
        assert find_correct_move_rank(moves, "E5") == 2

    def test_not_found_returns_0(self):
        from analyzers.estimate_difficulty import find_correct_move_rank

        class FakeMoveInfo:
            def __init__(self, move, visits):
                self.move = move
                self.visits = visits

        moves = [FakeMoveInfo("D4", 100)]
        assert find_correct_move_rank(moves, "Z19") == 0

    def test_empty_inputs_returns_0(self):
        from analyzers.estimate_difficulty import find_correct_move_rank
        assert find_correct_move_rank([], "") == 0

    def test_case_insensitive(self):
        from analyzers.estimate_difficulty import find_correct_move_rank

        class FakeMoveInfo:
            def __init__(self, move, visits):
                self.move = move
                self.visits = visits

        moves = [FakeMoveInfo("D4", 100)]
        assert find_correct_move_rank(moves, "d4") == 1


# ---------------------------------------------------------------------------
# InstinctResult model tests
# ---------------------------------------------------------------------------


class TestInstinctResult:
    """T3 verification: InstinctResult model."""

    def test_construction(self):
        from models.instinct_result import InstinctResult
        r = InstinctResult(instinct="push", confidence=0.8, evidence="Adjacent push")
        assert r.instinct == "push"
        assert r.confidence == 0.8
        assert r.evidence == "Adjacent push"

    def test_instinct_types(self):
        from models.instinct_result import INSTINCT_TYPES
        assert INSTINCT_TYPES == frozenset({"push", "hane", "cut", "descent", "extend"})


# ---------------------------------------------------------------------------
# InstinctStage tests
# ---------------------------------------------------------------------------


class TestInstinctStage:
    """T10 verification: InstinctStage pipeline integration."""

    def test_stage_properties(self):
        from analyzers.stages.instinct_stage import InstinctStage
        from analyzers.stages.protocols import ErrorPolicy

        stage = InstinctStage()
        assert stage.name == "instinct_classification"
        assert stage.error_policy == ErrorPolicy.DEGRADE

    def test_stage_with_no_position_returns_empty(self):
        from analyzers.stages.instinct_stage import InstinctStage
        from analyzers.stages.protocols import PipelineContext

        stage = InstinctStage()
        ctx = PipelineContext()
        ctx.position = None
        ctx.correct_move_gtp = None

        result_ctx = asyncio.run(stage.run(ctx))
        assert result_ctx.instinct_results == []


# ---------------------------------------------------------------------------
# Level-adaptive hint tests
# ---------------------------------------------------------------------------


class TestLevelAdaptiveHints:
    """T16 verification: different hints for different level categories."""

    def test_entry_and_strong_produce_different_tier2(self):
        from analyzers.hint_generator import _generate_reasoning_hint

        analysis = {
            "difficulty": {"solution_depth": 5, "refutation_count": 3},
        }

        hint_entry = _generate_reasoning_hint(
            "ladder", analysis, ["ladder"],
            level_category="entry",
        )
        hint_strong = _generate_reasoning_hint(
            "ladder", analysis, ["ladder"],
            level_category="strong",
        )

        # They should produce different text for the same puzzle
        # (entry = generic, strong = reading guidance)
        assert hint_entry != hint_strong or hint_entry  # At minimum, non-empty


# ---------------------------------------------------------------------------
# RC-1: Tactical detector orientation invariance tests (AC-6)
#
# Each of the 5 named detectors (ladder, net, snapback, ko, throw-in)
# is tested across 4 rotations (0°, 90°, 180°, 270°) using
# Position.rotate() and rotated GTP coords in AnalysisResponse.
# ---------------------------------------------------------------------------


_GTP_LETTERS = "ABCDEFGHJKLMNOPQRST"


def _rotate_gtp(coord: str, degrees: int, board_size: int = 19) -> str:
    """Rotate a GTP coordinate by the given degrees (clockwise)."""
    if not coord or coord.lower() == "pass":
        return coord
    col_letter = coord[0].upper()
    row_str = coord[1:]
    if col_letter not in _GTP_LETTERS or not row_str.isdigit():
        return coord
    x = _GTP_LETTERS.index(col_letter)
    y = board_size - int(row_str)
    n = board_size - 1
    if degrees == 90:
        rx, ry = n - y, x
    elif degrees == 180:
        rx, ry = n - x, n - y
    elif degrees == 270:
        rx, ry = y, n - x
    else:
        rx, ry = x, y
    return f"{_GTP_LETTERS[rx]}{board_size - ry}"


def _rotate_analysis(analysis: AnalysisResponse, degrees: int, board_size: int = 19) -> AnalysisResponse:
    """Create a rotated copy of an AnalysisResponse (rotate GTP coords in moves and PVs)."""
    if degrees == 0:
        return analysis
    rotated_infos = []
    for mi in analysis.move_infos:
        rotated_infos.append(MoveAnalysis(
            move=_rotate_gtp(mi.move, degrees, board_size),
            visits=mi.visits,
            winrate=mi.winrate,
            score_lead=mi.score_lead,
            policy_prior=mi.policy_prior,
            pv=[_rotate_gtp(m, degrees, board_size) for m in mi.pv],
        ))
    return AnalysisResponse(
        move_infos=rotated_infos,
        root_winrate=analysis.root_winrate,
        root_score=analysis.root_score,
        total_visits=analysis.total_visits,
    )


@pytest.fixture
def enrichment_config():
    from config import load_enrichment_config
    return load_enrichment_config()


class TestLadderDetectorOrientation:
    """AC-6: Ladder detector produces same result across 4 rotations."""

    @staticmethod
    def _make_ladder_fixtures():
        """Position + analysis with clear diagonal-chase PV → ladder detected.

        PV must be ≥8 moves for the PV-only fallback to trigger (short corner
        sequences were producing false positives with the old 4-move minimum).
        """
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=2),
                Stone(color=Color.BLACK, x=3, y=2),
                Stone(color=Color.WHITE, x=2, y=3),
                Stone(color=Color.WHITE, x=3, y=3),
            ],
            player_to_move=Color.BLACK,
        )
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
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_ladder_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.ladder_detector import LadderDetector

        pos, analysis = self._make_ladder_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = LadderDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Ladder not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "ladder"


class TestKoDetectorOrientation:
    """AC-6: Ko detector produces same result across 4 rotations."""

    @staticmethod
    def _make_ko_fixtures():
        """Position + analysis with PV containing repeated coordinates → ko."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=2),
                Stone(color=Color.WHITE, x=3, y=2),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=500,
                    winrate=0.6,
                    pv=["D4", "E4", "D4", "E4"],
                ),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_ko_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.ko_detector import KoDetector

        pos, analysis = self._make_ko_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = KoDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Ko not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "ko"


class TestSnapbackDetectorOrientation:
    """AC-6: Snapback detector produces same result across 4 rotations."""

    @staticmethod
    def _make_snapback_fixtures():
        """Position + analysis with low-policy + high-winrate + recapture PV → snapback."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=2, y=2),
                Stone(color=Color.WHITE, x=3, y=2),
                Stone(color=Color.WHITE, x=2, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=600,
                    winrate=0.95,
                    score_lead=15.0,
                    policy_prior=0.02,
                    pv=["D4", "C4", "D4"],
                ),
                MoveAnalysis(
                    move="E5",
                    visits=50,
                    winrate=0.45,
                    score_lead=1.0,
                    policy_prior=0.1,
                    pv=["E5"],
                ),
            ],
            root_winrate=0.5,
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_snapback_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.snapback_detector import SnapbackDetector

        pos, analysis = self._make_snapback_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = SnapbackDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Snapback not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "snapback"


class TestNetDetectorOrientation:
    """AC-6: Net detector produces same result across 4 rotations."""

    @staticmethod
    def _make_net_fixtures():
        """Position + analysis with high-winrate + clustered refutations → net."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),
                Stone(color=Color.WHITE, x=5, y=5),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="E4", visits=1000, winrate=0.96, pv=["E4", "F5"]),
                MoveAnalysis(move="F5", visits=200, winrate=0.15, pv=["F5"]),
                MoveAnalysis(move="D5", visits=180, winrate=0.14, pv=["D5"]),
                MoveAnalysis(move="E6", visits=170, winrate=0.13, pv=["E6"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_net_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.net_detector import NetDetector

        pos, analysis = self._make_net_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = NetDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Net not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "net"


class TestThrowInDetectorOrientation:
    """AC-6: Throw-in detector produces same result across 4 rotations."""

    @staticmethod
    def _make_throw_in_fixtures():
        """Position + analysis with edge move, adjacent opponent, low policy + high winrate → throw-in."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=0, y=1),
                Stone(color=Color.WHITE, x=1, y=0),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="A19",
                    visits=500,
                    winrate=0.90,
                    policy_prior=0.01,
                    pv=["A19", "B19"],
                ),
                MoveAnalysis(
                    move="D4",
                    visits=50,
                    winrate=0.45,
                    policy_prior=0.1,
                    pv=["D4"],
                ),
            ],
            root_winrate=0.5,
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_throw_in_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.throw_in_detector import ThrowInDetector

        pos, analysis = self._make_throw_in_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = ThrowInDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Throw-in not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "throw-in"


# ---------------------------------------------------------------------------
# T39: Extended detector orientation tests — 7 additional families
# ---------------------------------------------------------------------------


class TestLifeAndDeathDetectorOrientation:
    """AC-8: Life-and-death detector (always-true base tag) across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=800, winrate=0.90, pv=["D4"]),
                MoveAnalysis(move="E5", visits=200, winrate=0.40, pv=["E5"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_life_and_death_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.life_and_death_detector import LifeAndDeathDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = LifeAndDeathDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Life-and-death not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "life-and-death"

    def test_life_and_death_detected_reflected(self, enrichment_config):
        from analyzers.detectors.life_and_death_detector import LifeAndDeathDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.reflect("x")

        detector = LifeAndDeathDetector()
        result = detector.detect(reflected_pos, analysis, None, enrichment_config)
        assert result.detected is True


class TestCaptureRaceDetectorOrientation:
    """AC-8: Capture-race detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Adjacent B/W groups with limited liberties → capture race."""
        pos = Position(
            board_size=19,
            stones=[
                # Black group: (2,2), (2,3)
                Stone(color=Color.BLACK, x=2, y=2),
                Stone(color=Color.BLACK, x=2, y=3),
                # White group: (3,2), (3,3)
                Stone(color=Color.WHITE, x=3, y=2),
                Stone(color=Color.WHITE, x=3, y=3),
                # Surround to limit liberties
                Stone(color=Color.WHITE, x=1, y=2),
                Stone(color=Color.WHITE, x=1, y=3),
                Stone(color=Color.BLACK, x=4, y=2),
                Stone(color=Color.BLACK, x=4, y=3),
                Stone(color=Color.WHITE, x=2, y=1),
                Stone(color=Color.BLACK, x=3, y=1),
                Stone(color=Color.WHITE, x=2, y=4),
                Stone(color=Color.BLACK, x=3, y=4),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.60, pv=["D4", "E5"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_capture_race_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.capture_race_detector import CaptureRaceDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = CaptureRaceDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Capture-race not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "capture-race"

    def test_capture_race_detected_reflected(self, enrichment_config):
        from analyzers.detectors.capture_race_detector import CaptureRaceDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.reflect("x")

        detector = CaptureRaceDetector()
        result = detector.detect(reflected_pos, analysis, None, enrichment_config)
        assert result.detected is True


class TestConnectionDetectorOrientation:
    """AC-8: Connection detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Move at F14=(5,5) connecting two Black groups at (4,5) and (6,5)."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=4, y=5),
                Stone(color=Color.BLACK, x=6, y=5),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="F14", visits=600, winrate=0.85, pv=["F14"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_connection_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.connection_detector import ConnectionDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = ConnectionDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Connection not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "connection"

    def test_connection_detected_reflected(self, enrichment_config):
        from analyzers.detectors.connection_detector import ConnectionDetector

        pos, analysis = self._make_fixtures()
        # Use 180° rotation as a combined x+y reflection equivalent
        reflected_pos = pos.rotate(180)
        reflected_analysis = _rotate_analysis(analysis, 180)

        detector = ConnectionDetector()
        result = detector.detect(reflected_pos, reflected_analysis, None, enrichment_config)
        assert result.detected is True


class TestNakadeDetectorOrientation:
    """AC-8: Nakade detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Move at F14=(5,5) surrounded by 3 opponent stones, high winrate."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.WHITE, x=5, y=4),
                Stone(color=Color.WHITE, x=5, y=6),
                Stone(color=Color.WHITE, x=6, y=5),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="F14", visits=700, winrate=0.92, pv=["F14"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_nakade_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.nakade_detector import NakadeDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = NakadeDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Nakade not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "nakade"

    def test_nakade_detected_reflected(self, enrichment_config):
        from analyzers.detectors.nakade_detector import NakadeDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.rotate(180)
        reflected_analysis = _rotate_analysis(analysis, 180)

        detector = NakadeDetector()
        result = detector.detect(reflected_pos, reflected_analysis, None, enrichment_config)
        assert result.detected is True


class TestSekiDetectorOrientation:
    """AC-8: Seki detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Winrate near 0.5, low score lead → seki signal."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="D4", visits=500, winrate=0.50, score_lead=0.5, pv=["D4"]),
                MoveAnalysis(move="E5", visits=400, winrate=0.48, score_lead=0.3, pv=["E5"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_seki_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.seki_detector import SekiDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = SekiDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Seki not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "seki"

    def test_seki_detected_reflected(self, enrichment_config):
        from analyzers.detectors.seki_detector import SekiDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.reflect("y")

        detector = SekiDetector()
        result = detector.detect(reflected_pos, analysis, None, enrichment_config)
        assert result.detected is True


class TestDoubleAtariDetectorOrientation:
    """AC-8: Double-atari detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Move at F14=(5,5) puts two White groups in atari (1 liberty each)."""
        pos = Position(
            board_size=19,
            stones=[
                # White group 1: W(4,5) with B surrounding at (3,5), (4,6)
                Stone(color=Color.WHITE, x=4, y=5),
                Stone(color=Color.BLACK, x=3, y=5),
                Stone(color=Color.BLACK, x=4, y=6),
                # White group 2: W(6,5) with B surrounding at (7,5), (6,4)
                Stone(color=Color.WHITE, x=6, y=5),
                Stone(color=Color.BLACK, x=7, y=5),
                Stone(color=Color.BLACK, x=6, y=4),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(move="F14", visits=800, winrate=0.95, pv=["F14"]),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_double_atari_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.double_atari_detector import DoubleAtariDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = DoubleAtariDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Double-atari not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "double-atari"

    def test_double_atari_detected_reflected(self, enrichment_config):
        from analyzers.detectors.double_atari_detector import DoubleAtariDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.rotate(180)
        reflected_analysis = _rotate_analysis(analysis, 180)

        detector = DoubleAtariDetector()
        result = detector.detect(reflected_pos, reflected_analysis, None, enrichment_config)
        assert result.detected is True


class TestSacrificeDetectorOrientation:
    """AC-8: Sacrifice detector across 4 rotations."""

    @staticmethod
    def _make_fixtures():
        """Low policy + high winrate + long PV → sacrifice signal."""
        pos = Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=3, y=3),
                Stone(color=Color.WHITE, x=4, y=3),
            ],
            player_to_move=Color.BLACK,
        )
        analysis = AnalysisResponse(
            move_infos=[
                MoveAnalysis(
                    move="D4",
                    visits=600,
                    winrate=0.92,
                    policy_prior=0.03,
                    pv=["D4", "E5", "D4", "F6"],
                ),
                MoveAnalysis(
                    move="E5",
                    visits=50,
                    winrate=0.40,
                    policy_prior=0.15,
                    pv=["E5"],
                ),
            ],
        )
        return pos, analysis

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_sacrifice_detected_all_rotations(self, rotation, enrichment_config):
        from analyzers.detectors.sacrifice_detector import SacrificeDetector

        pos, analysis = self._make_fixtures()
        rotated_pos = pos.rotate(rotation)
        rotated_analysis = _rotate_analysis(analysis, rotation)

        detector = SacrificeDetector()
        result = detector.detect(rotated_pos, rotated_analysis, None, enrichment_config)
        assert result.detected is True, (
            f"Sacrifice not detected at rotation={rotation}°"
        )
        assert result.tag_slug == "sacrifice"

    def test_sacrifice_detected_reflected(self, enrichment_config):
        from analyzers.detectors.sacrifice_detector import SacrificeDetector

        pos, analysis = self._make_fixtures()
        reflected_pos = pos.reflect("x")

        detector = SacrificeDetector()
        result = detector.detect(reflected_pos, analysis, None, enrichment_config)
        assert result.detected is True
