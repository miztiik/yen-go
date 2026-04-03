"""
Unit tests for content classifier module.

Tests is_trivial_capture and classify_content_type.
All tests inject config via fixture — no filesystem dependency.
"""


import pytest

import backend.puzzle_manager.core.content_classifier as cc_module
from backend.puzzle_manager.core.content_classifier import (
    classify_content_type,
    get_content_type_id,
    is_trivial_capture,
    reset_content_type_config,
)
from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode, YenGoProperties

# ---------------------------------------------------------------------------
# Config fixture — injects config dict to avoid filesystem dependency
# ---------------------------------------------------------------------------

_TEST_CONFIG = {
    "schema_version": "1.0",
    "types": {
        "1": {"name": "curated", "display_label": "Curated", "description": "High-quality"},
        "2": {"name": "practice", "display_label": "Practice", "description": "Standard"},
        "3": {"name": "training", "display_label": "Training", "description": "Teaching"},
    },
    "teaching_patterns": [
        r"\bdemonstrates?\b",
        r"\bexplains?\b",
        r"\bshows?\b",
        r"\bconcepts?\b",
        r"\blessons?\b",
        r"\bexamples?\b",
        r"\btutorials?\b",
        r"\billustrates?\b",
    ],
    "curated_thresholds": {
        "min_quality": 3,
        "min_refutations": 2,
        "require_unique_first_move": True,
    },
    "training_thresholds": {
        "max_depth": 1,
        "min_comment_level": 2,
    },
}


@pytest.fixture(autouse=True)
def _inject_config():
    """Inject test config dict into content_classifier module."""
    cc_module._content_type_config = _TEST_CONFIG.copy()
    yield
    cc_module._content_type_config = None


# Convenience constants (loaded from test config)
CONTENT_TYPE_CURATED = 1
CONTENT_TYPE_PRACTICE = 2
CONTENT_TYPE_TRAINING = 3


def _make_game(
    *,
    board_size: int = 9,
    black_stones: list[Point] | None = None,
    white_stones: list[Point] | None = None,
    player_to_move: Color = Color.BLACK,
    solution_depth: int = 0,
    num_correct: int = 1,
    num_wrong: int = 0,
    quality_str: str | None = None,
    complexity_str: str | None = None,
    root_comment: str = "",
) -> SGFGame:
    """Build an SGFGame with a controllable solution tree for testing."""
    root = SolutionNode()
    if solution_depth > 0:
        # Add correct branches
        for c in range(num_correct):
            node = SolutionNode(
                move=Point(4, 4 + c),
                color=player_to_move,
                is_correct=True,
            )
            # Build depth chain on the first correct branch
            if c == 0:
                current = node
                for d in range(solution_depth - 1):
                    color = player_to_move.opponent() if d % 2 == 0 else player_to_move
                    child = SolutionNode(
                        move=Point(5 + d, 5),
                        color=color,
                        is_correct=True,
                    )
                    current.children.append(child)
                    current = child
            root.children.append(node)

        # Add wrong branches
        for w in range(num_wrong):
            wrong_node = SolutionNode(
                move=Point(3, 3 + w),
                color=player_to_move,
                is_correct=False,
            )
            # Give wrong nodes some depth for refutation depth tests
            wrong_child = SolutionNode(
                move=Point(2, 2 + w),
                color=player_to_move.opponent(),
                is_correct=True,
            )
            wrong_node.children.append(wrong_child)
            root.children.append(wrong_node)

    yengo_props = YenGoProperties(
        quality=quality_str,
        complexity=complexity_str,
    )

    return SGFGame(
        board_size=board_size,
        black_stones=black_stones or [Point(4, 4)],
        white_stones=white_stones or [Point(6, 6)],
        player_to_move=player_to_move,
        solution_tree=root,
        root_comment=root_comment,
        yengo_props=yengo_props,
    )


class TestIsTrivialCapture:
    """Tests for is_trivial_capture function."""

    def test_no_solution_not_trivial(self):
        """Puzzle with no solution tree is not trivial capture."""
        game = _make_game(solution_depth=0)
        assert is_trivial_capture(game) is False

    def test_atari_capture_is_trivial(self):
        """Single stone at 1 liberty with first move capturing it is trivial."""
        # White stone at (0,1) surrounded by black stones at (0,0) and (1,1),
        # with only liberty at (0,2). First correct move at (0,2) captures.
        root = SolutionNode()
        correct = SolutionNode(
            move=Point(0, 2),
            color=Color.BLACK,
            is_correct=True,
        )
        root.children.append(correct)

        game = SGFGame(
            board_size=9,
            black_stones=[Point(0, 0), Point(1, 1)],
            white_stones=[Point(0, 1)],
            player_to_move=Color.BLACK,
            solution_tree=root,
        )
        assert is_trivial_capture(game) is True

    def test_no_atari_not_trivial(self):
        """Position with no atari groups is not trivial."""
        game = _make_game(
            black_stones=[Point(4, 4)],
            white_stones=[Point(6, 6)],  # Far from any black stones
            solution_depth=3,
            num_wrong=2,
        )
        assert is_trivial_capture(game) is False

    def test_no_stones_not_trivial(self):
        """Empty board can't be trivial capture."""
        game = _make_game(
            black_stones=[],
            white_stones=[],
            solution_depth=1,
        )
        assert is_trivial_capture(game) is False


class TestClassifyContentType:
    """Tests for classify_content_type function."""

    def test_returns_valid_content_type(self):
        """Content type should be 1, 2, or 3."""
        game = _make_game(
            solution_depth=3,
            num_wrong=2,
            quality_str="q:3;rc:2;hc:0",
            complexity_str="d:3;r:5;s:10;u:1",
        )
        ct = classify_content_type(game)
        assert ct in (CONTENT_TYPE_CURATED, CONTENT_TYPE_PRACTICE, CONTENT_TYPE_TRAINING)

    def test_no_solution_is_training(self):
        """Puzzle without solution should be classified as training (3)."""
        game = _make_game(solution_depth=0)
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_TRAINING

    def test_curated_high_quality(self):
        """High quality puzzle with refutations and unique first move → curated."""
        game = _make_game(
            solution_depth=5,
            num_correct=1,
            num_wrong=3,
            quality_str="q:4;rc:3;hc:2",
            complexity_str="d:5;r:8;s:15;u:1",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_CURATED

    def test_average_puzzle_is_practice(self):
        """Average puzzle (insufficient for curated, not training) → practice."""
        game = _make_game(
            solution_depth=3,
            num_wrong=1,
            quality_str="q:2;rc:1;hc:0",
            complexity_str="d:3;r:3;s:10;u:1",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_PRACTICE

    def test_teaching_root_comment_is_training(self):
        """Puzzle with teaching root comment → training."""
        game = _make_game(
            solution_depth=3,
            num_wrong=1,
            quality_str="q:3;rc:2;hc:2",
            complexity_str="d:3;r:5;s:10;u:1",
            root_comment="This example demonstrates the ladder technique",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_TRAINING

    def test_single_move_tutorial_is_training(self):
        """Single-move depth with hc:2 → training."""
        game = _make_game(
            solution_depth=1,
            quality_str="q:3;rc:0;hc:2",
            complexity_str="d:1;r:1;s:10;u:1",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_TRAINING


class TestContentTypeValues:
    """Tests for content type values loaded from config."""

    def test_curated_is_1(self):
        assert get_content_type_id("curated") == 1

    def test_practice_is_2(self):
        assert get_content_type_id("practice") == 2

    def test_training_is_3(self):
        assert get_content_type_id("training") == 3

    def test_unknown_type_raises(self):
        with pytest.raises(KeyError, match="unknown"):
            get_content_type_id("unknown")


class TestConfigDrivenBehavior:
    """Tests that classification uses config values, not hardcoded ones."""

    def test_missing_config_raises(self):
        """FileNotFoundError raised when config file is missing."""
        cc_module._content_type_config = None  # Force reload
        import unittest.mock as mock
        with mock.patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="content-types.json"):
                reset_content_type_config()
                cc_module._content_type_config = None
                get_content_type_id("curated")

    def test_training_thresholds_from_config(self):
        """Step 4 uses config training_thresholds, not hardcoded 1 and 2."""
        # Override: max_depth=2, min_comment_level=1 (more lenient)
        cc_module._content_type_config = {
            **_TEST_CONFIG,
            "training_thresholds": {"max_depth": 2, "min_comment_level": 1},
        }
        # depth=2, hc=1 → should now be training (wouldn't be with defaults)
        game = _make_game(
            solution_depth=2,
            quality_str="q:3;rc:2;hc:1",
            complexity_str="d:2;r:5;s:10;u:1",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_TRAINING

    def test_custom_curated_thresholds(self):
        """Changing min_quality in config changes curated classification."""
        # Raise min_quality to 5 — puzzle with q:4 should no longer be curated
        cc_module._content_type_config = {
            **_TEST_CONFIG,
            "curated_thresholds": {
                "min_quality": 5,
                "min_refutations": 2,
                "require_unique_first_move": True,
            },
        }
        game = _make_game(
            solution_depth=5,
            num_correct=1,
            num_wrong=3,
            quality_str="q:4;rc:3;hc:2",
            complexity_str="d:5;r:8;s:15;u:1",
        )
        ct = classify_content_type(game)
        assert ct == CONTENT_TYPE_PRACTICE  # Not curated because q:4 < min_quality:5
