"""Tests for Phase B.5: technique_classifier module."""

from __future__ import annotations

import pytest
from analyzers.detectors import TechniqueDetector
from analyzers.technique_classifier import (
    TAG_PRIORITY,
    _detect_direct_capture,
    _detect_ko,
    _detect_ladder,
    _detect_net,
    _detect_seki,
    _detect_snapback,
    _detect_throw_in,
    _is_diagonal_chase,
    _parse_gtp,
    classify_techniques,
    get_all_detectors,
    run_detectors,
)
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone

# ---- Fixtures: analysis result builders ----


def _make_analysis(
    *,
    correct_move_gtp: str = "C3",
    correct_move_policy: float = 0.3,
    correct_move_winrate: float = 0.95,
    status: str = "accepted",
    pv: list[str] | None = None,
    refutations: list[dict] | None = None,
    solution_depth: int = 3,
    visits_to_solve: int = 500,
    tag_names: list[str] | None = None,
) -> dict:
    """Build a minimal AiAnalysisResult dict for testing."""
    return {
        "validation": {
            "correct_move_gtp": correct_move_gtp,
            "correct_move_policy": correct_move_policy,
            "correct_move_winrate": correct_move_winrate,
            "status": status,
            "pv": pv or [],
        },
        "refutations": refutations or [],
        "difficulty": {
            "solution_depth": solution_depth,
            "visits_to_solve": visits_to_solve,
        },
        "tag_names": tag_names or [],
    }


# ---- TAG_PRIORITY structure ----


class TestTagPriority:
    """Verify TAG_PRIORITY is well-formed."""

    def test_all_priority_levels_present(self):
        values = set(TAG_PRIORITY.values())
        assert values == {1, 2, 3, 4}

    def test_priority_1_contains_snapback(self):
        assert TAG_PRIORITY["snapback"] == 1

    def test_priority_1_contains_ko(self):
        assert TAG_PRIORITY["ko"] == 1

    def test_priority_1_contains_ladder(self):
        assert TAG_PRIORITY["ladder"] == 1

    def test_life_and_death_is_priority_2(self):
        assert TAG_PRIORITY["life-and-death"] == 2

    def test_capture_is_priority_4(self):
        assert TAG_PRIORITY["capture"] == 4

    def test_all_tags_are_lowercase_slugs(self):
        for tag in TAG_PRIORITY:
            assert tag == tag.lower()
            assert " " not in tag

    def test_net_is_priority_1(self):
        """RC-3: Net (geta) should be priority 1 to win over life-and-death."""
        assert TAG_PRIORITY["net"] == 1


# ---- _parse_gtp ----


class TestParseGtp:
    """Test GTP coordinate parsing."""

    def test_simple_coordinate(self):
        assert _parse_gtp("C3") == (3, 3)

    def test_skips_i(self):
        # J should be column 9 (A=1..H=8, skip I, J=9)
        assert _parse_gtp("J5") == (5, 9)

    def test_high_coordinate(self):
        assert _parse_gtp("T19") == (19, 19)

    def test_a1(self):
        assert _parse_gtp("A1") == (1, 1)

    def test_pass_returns_none(self):
        assert _parse_gtp("pass") is None

    def test_empty_returns_none(self):
        assert _parse_gtp("") is None

    def test_invalid_returns_none(self):
        assert _parse_gtp("Z99") is None

    def test_lowercase_accepted(self):
        # GTP uses uppercase, but _parse_gtp uppercases internally
        assert _parse_gtp("c3") == (3, 3)

    def test_i_column_rejected(self):
        # 'I' is never used in GTP coordinates
        assert _parse_gtp("I5") is None


# ---- _is_diagonal_chase ----


class TestIsDiagonalChase:
    """Test diagonal chase pattern detection."""

    def test_clear_diagonal(self):
        # 4 moves that form a diagonal: C3→D4→E5→F6
        pv = ["C3", "D4", "E5", "F6"]
        assert _is_diagonal_chase(pv) is True

    def test_too_short(self):
        pv = ["C3", "D4"]
        assert _is_diagonal_chase(pv, min_length=4) is False

    def test_non_diagonal(self):
        # Moves along a straight line (row constant)
        pv = ["C3", "D3", "E3", "F3"]
        assert _is_diagonal_chase(pv) is False

    def test_empty_pv(self):
        assert _is_diagonal_chase([]) is False


# ---- Ko detection ----


class TestDetectKo:
    """Test ko detection from refutation PVs."""

    def test_ko_in_refutation_type(self):
        refs = [{"refutation_type": "ko", "refutation_pv": []}]
        assert _detect_ko(refs) is True

    def test_positional_recapture(self):
        # Same position appears twice in PV
        refs = [{"refutation_type": "unclassified", "refutation_pv": ["C3", "D4", "C3"]}]
        assert _detect_ko(refs) is True

    def test_no_ko(self):
        refs = [{"refutation_type": "unclassified", "refutation_pv": ["C3", "D4", "E5"]}]
        assert _detect_ko(refs) is False

    def test_empty_refutations(self):
        assert _detect_ko([]) is False


# ---- Ladder detection ----


class TestDetectLadder:
    """Test ladder detection from PV diagonal patterns."""

    def test_ladder_in_correct_pv(self):
        validation = {"pv": ["C3", "D4", "E5", "F6", "G7"]}
        assert _detect_ladder(validation, []) is True

    def test_ladder_in_refutation_pv(self):
        validation = {"pv": []}
        refs = [{"refutation_pv": ["C3", "D4", "E5", "F6"]}]
        assert _detect_ladder(validation, refs) is True

    def test_no_ladder(self):
        validation = {"pv": ["C3", "D3", "E3"]}
        assert _detect_ladder(validation, []) is False


# ---- Snapback detection ----


class TestDetectSnapback:
    """Test snapback detection (low policy + high winrate + large delta)."""

    def test_snapback_pattern(self):
        validation = {
            "correct_move_policy": 0.02,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.5}]
        assert _detect_snapback(validation, refs) is True

    def test_no_snapback_high_policy(self):
        validation = {
            "correct_move_policy": 0.3,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.5}]
        assert _detect_snapback(validation, refs) is False

    def test_no_snapback_low_delta(self):
        validation = {
            "correct_move_policy": 0.02,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.1}]
        assert _detect_snapback(validation, refs) is False


# ---- Throw-in detection ----


class TestDetectThrowIn:
    """Test throw-in detection (first/second line moves)."""

    def test_first_line_row(self):
        assert _detect_throw_in("A1", {}) is True

    def test_second_line_row(self):
        assert _detect_throw_in("A2", {}) is True

    def test_first_line_col(self):
        # A-column is col 1
        assert _detect_throw_in("A5", {}) is True

    def test_b_column_second_line(self):
        # B-column is col 2
        assert _detect_throw_in("B5", {}) is True

    def test_center_move_not_throw_in(self):
        assert _detect_throw_in("J10", {}) is False

    def test_empty_move(self):
        assert _detect_throw_in("", {}) is False


# ---- Seki detection ----


class TestDetectSeki:
    """Test seki detection (no refutations + accepted + middling winrate)."""

    def test_seki_pattern(self):
        validation = {
            "status": "accepted",
            "correct_move_winrate": 0.5,
        }
        assert _detect_seki(validation, []) is True

    def test_not_seki_with_refutations(self):
        validation = {
            "status": "accepted",
            "correct_move_winrate": 0.5,
        }
        refs = [{"delta": 0.1}]
        assert _detect_seki(validation, refs) is False

    def test_not_seki_high_winrate(self):
        validation = {
            "status": "accepted",
            "correct_move_winrate": 0.95,
        }
        assert _detect_seki(validation, []) is False


# ---- Net detection ----


class TestDetectNet:
    """Test net/geta detection (high policy + high winrate + similar refutation deltas)."""

    def test_net_pattern(self):
        validation = {
            "correct_move_policy": 0.4,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.3}, {"delta": 0.32}]
        assert _detect_net(validation, refs) is True

    def test_no_net_low_policy(self):
        validation = {
            "correct_move_policy": 0.05,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.3}, {"delta": 0.32}]
        assert _detect_net(validation, refs) is False

    def test_no_net_single_refutation(self):
        validation = {
            "correct_move_policy": 0.4,
            "correct_move_winrate": 0.95,
        }
        refs = [{"delta": 0.3}]
        assert _detect_net(validation, refs) is False


# ---- Direct capture detection ----


class TestDetectDirectCapture:
    """Test direct capture (low depth, high winrate, low visits)."""

    def test_direct_capture(self):
        validation = {"correct_move_winrate": 0.95}
        difficulty = {"solution_depth": 1, "visits_to_solve": 100}
        assert _detect_direct_capture(validation, difficulty) is True

    def test_no_capture_deep_solution(self):
        validation = {"correct_move_winrate": 0.95}
        difficulty = {"solution_depth": 5, "visits_to_solve": 100}
        assert _detect_direct_capture(validation, difficulty) is False

    def test_no_capture_many_visits(self):
        validation = {"correct_move_winrate": 0.95}
        difficulty = {"solution_depth": 1, "visits_to_solve": 1000}
        assert _detect_direct_capture(validation, difficulty) is False


# ---- classify_techniques (integration) ----


class TestClassifyTechniques:
    """Integration tests for the full classify_techniques pipeline."""

    def test_no_fallback_returns_empty(self):
        """Empty analysis produces no tags (no fallback)."""
        analysis = _make_analysis(
            correct_move_gtp="J10",
            correct_move_policy=0.15,
            correct_move_winrate=0.7,
            solution_depth=5,
            visits_to_solve=1000,
        )
        tags = classify_techniques(analysis)
        assert tags == []

    def test_ko_detected_from_refutations(self):
        analysis = _make_analysis(
            refutations=[
                {
                    "refutation_type": "ko",
                    "refutation_pv": [],
                    "wrong_move": "D4",
                    "delta": 0.3,
                }
            ]
        )
        tags = classify_techniques(analysis)
        assert "ko" in tags

    def test_ladder_detected_from_pv(self):
        analysis = _make_analysis(
            pv=["C3", "D4", "E5", "F6", "G7"],
        )
        tags = classify_techniques(analysis)
        assert "ladder" in tags

    def test_snapback_detected(self):
        analysis = _make_analysis(
            correct_move_policy=0.02,
            correct_move_winrate=0.95,
            refutations=[{"delta": 0.5, "refutation_type": "unclassified", "refutation_pv": []}],
        )
        tags = classify_techniques(analysis)
        assert "snapback" in tags

    def test_existing_tags_preserved(self):
        analysis = _make_analysis(tag_names=["eye-shape", "corner"])
        tags = classify_techniques(analysis)
        assert "eye-shape" in tags
        assert "corner" in tags

    def test_priority_sorting(self):
        """Higher priority (lower number) tags come first."""
        analysis = _make_analysis(
            tag_names=["corner", "eye-shape"],
            refutations=[
                {"refutation_type": "ko", "refutation_pv": [], "wrong_move": "D4", "delta": 0.3}
            ],
        )
        tags = classify_techniques(analysis)
        ko_idx = tags.index("ko")
        corner_idx = tags.index("corner")
        assert ko_idx < corner_idx, "Priority 1 (ko) should come before priority 4 (corner)"

    def test_direct_capture_excluded_when_higher_technique(self):
        """Direct capture tag not added if ko/ladder/snapback present."""
        analysis = _make_analysis(
            correct_move_winrate=0.95,
            solution_depth=1,
            visits_to_solve=100,
            refutations=[
                {"refutation_type": "ko", "refutation_pv": [], "wrong_move": "D4", "delta": 0.3}
            ],
        )
        tags = classify_techniques(analysis)
        assert "ko" in tags
        assert "capture" not in tags

    def test_always_returns_list(self):
        tags = classify_techniques({})
        assert isinstance(tags, list)
        assert tags == []  # No fallback -- empty input returns empty list

    def test_returns_unique_tags(self):
        analysis = _make_analysis(tag_names=["ko", "ko", "life-and-death"])
        tags = classify_techniques(analysis)
        assert len(tags) == len(set(tags))


# ---- T69: Detector wiring integration tests ----


class TestGetAllDetectors:
    """Verify get_all_detectors() returns all 28 detector instances."""

    def test_returns_28_detectors(self):
        detectors = get_all_detectors()
        assert len(detectors) == 28

    def test_all_implement_protocol(self):
        detectors = get_all_detectors()
        for d in detectors:
            assert isinstance(d, TechniqueDetector), (
                f"{type(d).__name__} does not implement TechniqueDetector"
            )

    def test_all_unique_classes(self):
        detectors = get_all_detectors()
        class_names = [type(d).__name__ for d in detectors]
        assert len(class_names) == len(set(class_names)), (
            f"Duplicate detector classes: {[n for n in class_names if class_names.count(n) > 1]}"
        )


class TestRunDetectorsIntegration:
    """Verify run_detectors() produces tags from the 28 detector classes."""

    @pytest.fixture
    def config(self):
        return load_enrichment_config()

    @pytest.fixture
    def corner_position(self):
        """Simple position with stones in a corner — life-and-death scenario."""
        return Position(
            board_size=19,
            stones=[
                Stone(color=Color.BLACK, x=0, y=0),
                Stone(color=Color.BLACK, x=1, y=0),
                Stone(color=Color.BLACK, x=0, y=1),
                Stone(color=Color.WHITE, x=2, y=0),
                Stone(color=Color.WHITE, x=1, y=1),
                Stone(color=Color.WHITE, x=0, y=2),
            ],
            player_to_move=Color.BLACK,
        )

    @pytest.fixture
    def basic_analysis(self):
        return AnalysisResponse(
            request_id="test",
            move_infos=[
                MoveAnalysis(
                    move="A3",
                    visits=500,
                    winrate=0.95,
                    score_lead=10.0,
                    policy_prior=0.4,
                    pv=["A3", "B3"],
                ),
                MoveAnalysis(
                    move="B1",
                    visits=50,
                    winrate=0.3,
                    score_lead=-5.0,
                    policy_prior=0.1,
                    pv=["B1", "A3"],
                ),
            ],
            root_winrate=0.5,
            root_score=0.0,
            total_visits=550,
        )

    def test_run_detectors_returns_detection_results(
        self, corner_position, basic_analysis, config
    ):
        """run_detectors() returns DetectionResult objects (not tag strings)."""
        detectors = get_all_detectors()
        results = run_detectors(
            position=corner_position,
            analysis=basic_analysis,
            solution_tree=None,
            config=config,
            detectors=detectors,
        )
        for r in results:
            assert hasattr(r, "detected")
            assert hasattr(r, "tag_slug")
            assert hasattr(r, "confidence")
            assert r.detected is True

    def test_run_detectors_produces_at_least_one_tag(
        self, corner_position, basic_analysis, config
    ):
        """Corner position with stones should detect at least life-and-death."""
        detectors = get_all_detectors()
        results = run_detectors(
            position=corner_position,
            analysis=basic_analysis,
            solution_tree=None,
            config=config,
            detectors=detectors,
        )
        tag_slugs = [r.tag_slug for r in results]
        assert len(tag_slugs) >= 1, (
            "Expected at least one technique detected for corner position"
        )

    def test_run_detectors_with_explicit_list(self, corner_position, basic_analysis, config):
        """Passing explicit detectors list works."""
        from analyzers.detectors.life_and_death_detector import LifeAndDeathDetector
        results = run_detectors(
            position=corner_position,
            analysis=basic_analysis,
            solution_tree=None,
            config=config,
            detectors=[LifeAndDeathDetector()],
        )
        assert isinstance(results, list)


# --- Migrated from test_sprint1_fixes.py (P1.3 gap ID) ---


@pytest.mark.unit
class TestThrowInAllEdges:
    """P1.3: Throw-in detection must check all four board edges."""

    def test_bottom_edge(self):
        """Row 1-2 (bottom) → detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("A1", {}) is True
        assert _detect_throw_in("C2", {}) is True

    def test_left_edge(self):
        """Col A-B (left, col 1-2) → detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("A10", {}) is True
        assert _detect_throw_in("B10", {}) is True

    def test_top_edge(self):
        """Row 18-19 on 19×19 (top) → detected (P1.3 fix)."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("C19", {}, board_size=19) is True
        assert _detect_throw_in("C18", {}, board_size=19) is True

    def test_right_edge(self):
        """Col T (col 19 on 19×19, right) → detected (P1.3 fix)."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("T10", {}, board_size=19) is True
        assert _detect_throw_in("S10", {}, board_size=19) is True

    def test_center_not_detected(self):
        """Center moves → not detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("K10", {}, board_size=19) is False
        assert _detect_throw_in("E5", {}, board_size=19) is False

    def test_9x9_top_edge(self):
        """Row 8-9 on 9×9 → detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("C9", {}, board_size=9) is True
        assert _detect_throw_in("C8", {}, board_size=9) is True

    def test_9x9_right_edge(self):
        """Col J (col 9 on 9×9) → detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("J5", {}, board_size=9) is True
        assert _detect_throw_in("H5", {}, board_size=9) is True

    def test_9x9_center_not_detected(self):
        """Center on 9×9 → not detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("E5", {}, board_size=9) is False

    def test_empty_or_pass(self):
        """Empty or pass → not detected."""
        from analyzers.technique_classifier import _detect_throw_in
        assert _detect_throw_in("", {}) is False
        assert _detect_throw_in("pass", {}) is False
