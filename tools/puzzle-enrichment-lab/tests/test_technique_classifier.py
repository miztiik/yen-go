"""Tests for technique_classifier module (v2 detector-based infrastructure).

Legacy classify_techniques() and _detect_* helpers were removed.
All technique classification now uses the 28 typed detector classes
via run_detectors().
"""

from __future__ import annotations

import pytest
from analyzers.detectors import TechniqueDetector
from analyzers.technique_classifier import (
    TAG_PRIORITY,
    get_all_detectors,
    run_detectors,
)
from config import load_enrichment_config
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.position import Color, Position, Stone


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
