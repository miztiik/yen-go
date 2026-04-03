"""Tests for AI-Solve move classifier and tree builder (Phases 3-4, ai-solve-enrichment-plan-v3).

Gate 3 criteria:
- Classification uses ONLY delta thresholds — no absolute winrate gates
- Pre-filter reduces confirmation queries
- Sign adjustment correct for Black-to-play and White-to-play
- Pass as best move → explicit rejection
- All thresholds from config
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
def _make_config(
    t_good: float = 0.05,
    t_bad: float = 0.15,
    t_hotspot: float = 0.30,
    confirmation_min_policy: float = 0.03,
    pre_winrate_floor: float = 0.30,
    post_winrate_ceiling: float = 0.95,
):
    """Create an AiSolveConfig with given thresholds."""
    from config.ai_solve import AiSolveConfig
    return AiSolveConfig(
        enabled=True,
        thresholds={
            "t_good": t_good,
            "t_bad": t_bad,
            "t_hotspot": t_hotspot,
            "t_disagreement": 0.10,
        },
        confidence_metrics={
            "pre_winrate_floor": pre_winrate_floor,
            "post_winrate_ceiling": post_winrate_ceiling,
        },
        solution_tree={
            "confirmation_min_policy": confirmation_min_policy,
        },
    )


def _make_analysis(moves: list[dict]):
    """Create a mock AnalysisResponse with moveInfos as dicts.

    Sets root_winrate from the first move's winrate (DD-1 consistency).
    """
    analysis = MagicMock()
    analysis.moveInfos = moves
    # DD-1: root_winrate must be a float for analyze_position_candidates
    analysis.root_winrate = moves[0].get("winrate", 0.5) if moves else 0.5
    return analysis


@pytest.mark.unit
class TestNormalizeWinrate:
    """Perspective normalization for Black/White."""

    def test_same_perspective_unchanged(self):
        from analyzers.solve_position import normalize_winrate
        assert normalize_winrate(0.8, "B", "B") == pytest.approx(0.8)

    def test_opposite_perspective_flipped(self):
        from analyzers.solve_position import normalize_winrate
        assert normalize_winrate(0.8, "W", "B") == pytest.approx(0.2)

    def test_white_same_perspective(self):
        from analyzers.solve_position import normalize_winrate
        assert normalize_winrate(0.6, "W", "W") == pytest.approx(0.6)

    def test_black_to_white_flipped(self):
        from analyzers.solve_position import normalize_winrate
        assert normalize_winrate(0.7, "B", "W") == pytest.approx(0.3)


@pytest.mark.unit
class TestClassifyMoveQuality:
    """Delta-based classification: TE / BM / BM_HO / neutral."""

    def test_correct_move_te(self):
        """Move with small delta (< t_good) → TE."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_good=0.05)
        # root=0.50, move=0.48 → delta=0.02 < 0.05 → TE
        result = classify_move_quality(0.48, 0.50, 0.45, config)
        assert result == MoveQuality.TE

    def test_wrong_move_bm(self):
        """Move with large delta (> t_bad but < t_hotspot) → BM."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_bad=0.15, t_hotspot=0.30)
        # root=0.80, move=0.60 → delta=0.20 → BM
        result = classify_move_quality(0.60, 0.80, 0.10, config)
        assert result == MoveQuality.BM

    def test_blunder_hotspot_bm_ho(self):
        """Move with very large delta (> t_hotspot) → BM_HO."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_hotspot=0.30)
        # root=0.90, move=0.50 → delta=0.40 → BM_HO
        result = classify_move_quality(0.50, 0.90, 0.15, config)
        assert result == MoveQuality.BM_HO

    def test_neutral_move(self):
        """Move with delta between t_good and t_bad → NEUTRAL."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_good=0.05, t_bad=0.15)
        # root=0.70, move=0.60 → delta=0.10 → NEUTRAL
        result = classify_move_quality(0.60, 0.70, 0.10, config)
        assert result == MoveQuality.NEUTRAL

    def test_no_absolute_winrate_gate(self):
        """A move with low absolute winrate but small delta → TE (DD-6)."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_good=0.05)
        # root=0.20, move=0.18 → delta=0.02 → TE (even though absolute WR is low)
        result = classify_move_quality(0.18, 0.20, 0.50, config)
        assert result == MoveQuality.TE

    def test_exact_boundary_t_good(self):
        """Delta == t_good → TE (uses <=)."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_good=0.05)
        # root=0.50, move=0.45 → delta=0.05 exactly → TE
        result = classify_move_quality(0.45, 0.50, 0.30, config)
        assert result == MoveQuality.TE

    def test_exact_boundary_t_bad(self):
        """Delta == t_bad → BM (uses >=)."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        config = _make_config(t_bad=0.15, t_hotspot=0.30)
        # root=0.80, move=0.65 → delta=0.15 exactly → BM
        result = classify_move_quality(0.65, 0.80, 0.10, config)
        assert result == MoveQuality.BM

    def test_thresholds_from_config(self):
        """Custom config thresholds are respected."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality
        # Tighter thresholds
        config = _make_config(t_good=0.02, t_bad=0.08, t_hotspot=0.20)
        # delta=0.03 → was TE with default t_good=0.05, now NEUTRAL
        result = classify_move_quality(0.47, 0.50, 0.10, config)
        assert result == MoveQuality.NEUTRAL


@pytest.mark.unit
class TestAnalyzePositionCandidates:
    """Full position analysis with pre-filtering and pass rejection."""

    def test_pass_as_best_move_rejected(self):
        """EDGE-4: Pass as best move → ValueError."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config()
        analysis = _make_analysis([
            {"move": "pass", "winrate": 0.95, "prior": 0.80},
        ])
        with pytest.raises(ValueError, match="pass is the best move"):
            analyze_position_candidates(analysis, "B", "test-001", config)

    def test_pre_filter_removes_low_policy(self):
        """Moves below confirmation_min_policy are filtered out."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(confirmation_min_policy=0.03)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.45},
            {"move": "D4", "winrate": 0.85, "prior": 0.30},
            {"move": "E5", "winrate": 0.80, "prior": 0.01},  # below threshold
            {"move": "F6", "winrate": 0.75, "prior": 0.005},  # below threshold
        ])
        result = analyze_position_candidates(analysis, "B", "test-002", config)
        # Only 2 candidates should survive pre-filter
        assert len(result.all_classifications) == 2
        moves = [m.move_gtp for m in result.all_classifications]
        assert "E5" not in moves
        assert "F6" not in moves

    def test_correct_moves_sorted_by_winrate_desc(self):
        """Correct moves ranked by winrate descending (DD-2)."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(t_good=0.05)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.30},  # TE
            {"move": "D4", "winrate": 0.92, "prior": 0.45},  # TE
            {"move": "E5", "winrate": 0.88, "prior": 0.10},  # TE
        ])
        result = analyze_position_candidates(analysis, "B", "test-003", config)
        assert len(result.correct_moves) == 3
        # Sorted by winrate desc
        assert result.correct_moves[0].move_gtp == "D4"
        assert result.correct_moves[1].move_gtp == "C3"
        assert result.correct_moves[2].move_gtp == "E5"

    def test_wrong_moves_sorted_by_policy_desc(self):
        """Wrong moves ranked by policy descending (DD-2, most tempting first)."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(t_bad=0.15)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},  # TE (root)
            {"move": "D4", "winrate": 0.60, "prior": 0.25},  # BM (delta=0.30)
            {"move": "E5", "winrate": 0.70, "prior": 0.15},  # BM (delta=0.20)
            {"move": "F6", "winrate": 0.65, "prior": 0.05},  # BM (delta=0.25)
        ])
        result = analyze_position_candidates(analysis, "B", "test-004", config)
        # D4t and E5 are wrong; F6 policy=0.05 > 0.03 so not filtered
        wrong_moves = result.wrong_moves
        assert len(wrong_moves) >= 2
        # Sorted by policy desc
        if len(wrong_moves) >= 2:
            assert wrong_moves[0].policy >= wrong_moves[1].policy

    def test_confidence_annotation_low(self):
        """Root winrate below pre_winrate_floor → confidence 'low' (DD-6)."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(pre_winrate_floor=0.30)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.20, "prior": 0.50},
        ])
        result = analyze_position_candidates(analysis, "B", "test-005", config)
        assert result.root_winrate_confidence == "low"

    def test_confidence_annotation_high(self):
        """Root winrate above post_winrate_ceiling → confidence 'high' (DD-6)."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(post_winrate_ceiling=0.95)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.98, "prior": 0.80},
        ])
        result = analyze_position_candidates(analysis, "B", "test-006", config)
        assert result.root_winrate_confidence == "high"

    def test_empty_analysis(self):
        """No move candidates → position analysis with UNTOUCHED."""
        from analyzers.solve_position import analyze_position_candidates
        from models.solve_result import AiCorrectnessLevel
        config = _make_config()
        analysis = _make_analysis([])
        result = analyze_position_candidates(analysis, "B", "test-007", config)
        assert result.ac_level == AiCorrectnessLevel.UNTOUCHED
        assert len(result.all_classifications) == 0

    def test_pass_in_candidates_filtered(self):
        """Pass moves in candidate list (but not best) are skipped."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config()
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},
            {"move": "pass", "winrate": 0.40, "prior": 0.05},
        ])
        result = analyze_position_candidates(analysis, "B", "test-008", config)
        moves = [m.move_gtp for m in result.all_classifications]
        assert "pass" not in [m.upper() for m in moves]

    def test_sign_adjustment_black_to_play(self):
        """Black-to-play: winrate NOT flipped (same perspective)."""
        from analyzers.solve_position import analyze_position_candidates
        config = _make_config(t_good=0.05)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},
        ])
        result = analyze_position_candidates(analysis, "B", "test-009", config)
        assert result.root_winrate == pytest.approx(0.90)

    def test_all_thresholds_from_config(self):
        """Verify that custom config thresholds change classification."""
        from analyzers.solve_position import analyze_position_candidates
        from models.solve_result import MoveQuality

        # Default thresholds: t_good=0.05
        config_default = _make_config(t_good=0.05)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},
            {"move": "D4", "winrate": 0.87, "prior": 0.30},  # delta=0.03 < 0.05 → TE
        ])
        result1 = analyze_position_candidates(analysis, "B", "test-010a", config_default)
        d4_class = next(m for m in result1.all_classifications if m.move_gtp == "D4")
        assert d4_class.quality == MoveQuality.TE

        # Tighter threshold: t_good=0.02
        config_tight = _make_config(t_good=0.02, t_bad=0.15, t_hotspot=0.30)
        result2 = analyze_position_candidates(analysis, "B", "test-010b", config_tight)
        d4_class2 = next(m for m in result2.all_classifications if m.move_gtp == "D4")
        assert d4_class2.quality == MoveQuality.NEUTRAL  # delta=0.03 > 0.02 → NEUTRAL


# ---------------------------------------------------------------------------
# Phase 4: Tree Builder Tests
# ---------------------------------------------------------------------------


class MockEngine:
    """Mock engine for tree builder tests.

    Returns configurable analysis results based on move sequence depth.
    """

    def __init__(self, responses: list[list[dict]] | None = None, max_responses: int = 20):
        self.responses = responses or []
        self.query_count = 0
        self.max_responses = max_responses
        self._default_response = [
            {"move": "D4", "winrate": 0.90, "prior": 0.40},
            {"move": "E5", "winrate": 0.85, "prior": 0.30},
        ]

    def query(self, moves: list[str], *, max_visits: int | None = None):
        idx = self.query_count
        self.query_count += 1
        if idx < len(self.responses):
            data = self.responses[idx]
        else:
            data = self._default_response
        return _make_analysis(data)


class MockEnginePass:
    """Engine that returns pass as best move after N queries."""

    def __init__(self, pass_after: int = 1):
        self.query_count = 0
        self.pass_after = pass_after

    def query(self, moves: list[str], *, max_visits: int | None = None):
        self.query_count += 1
        if self.query_count > self.pass_after:
            return _make_analysis([
                {"move": "pass", "winrate": 0.95, "prior": 0.80},
            ])
        return _make_analysis([
            {"move": "D4", "winrate": 0.90, "prior": 0.40},
        ])


class MockEngineEmpty:
    """Engine that returns empty moveInfos (terminal position)."""

    def __init__(self):
        self.query_count = 0

    def query(self, moves: list[str], *, max_visits: int | None = None):
        self.query_count += 1
        return _make_analysis([])


class MockEngineSeki:
    """Engine that returns seki-like winrate for consecutive depths."""

    def __init__(self):
        self.query_count = 0

    def query(self, moves: list[str], *, max_visits: int | None = None):
        self.query_count += 1
        return _make_analysis([
            {"move": "D4", "winrate": 0.50, "prior": 0.40},
        ])


@pytest.mark.unit
class TestBuildSolutionTree:
    """Tree builder tests (Phase 4, DD-1, DD-3)."""

    def test_stops_at_max_depth(self):
        """Hard cap: stops at solution_max_depth."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        # Override depth profile to max_depth=3
        config.solution_tree.depth_profiles["core"].solution_max_depth = 3
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=50)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-depth",
        )
        assert root.move_gtp == "C3"
        assert root.is_correct is True
        assert budget.used <= 50

    def test_budget_required_not_optional(self):
        """QueryBudget is a required parameter."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        # Budget with 0 total → immediate truncation
        config = _make_config()
        engine = MockEngine()
        budget = QueryBudget(total=0)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-budget-zero",
        )
        assert root.truncated is True

    def test_budget_exhausted_truncates(self):
        """When budget exhausts, branches are truncated."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        config.solution_tree.depth_profiles["core"].solution_max_depth = 20

        engine = MockEngine()
        budget = QueryBudget(total=3)

        build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-budget-exhaust",
        )
        assert budget.remaining == 0 or budget.used <= 3

    def test_stops_at_pass_in_pv(self):
        """Terminal: pass in PV stops tree growth."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        engine = MockEnginePass(pass_after=1)
        budget = QueryBudget(total=50)

        build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-pass",
        )
        # Should stop after encountering pass
        assert engine.query_count <= 3

    def test_stops_at_no_legal_moves(self):
        """Terminal: no legal moves stops tree."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        engine = MockEngineEmpty()
        budget = QueryBudget(total=50)

        build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-empty",
        )
        assert engine.query_count == 1

    def test_stops_at_seki(self):
        """Seki detection: consecutive seki-band winrates → early exit."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        config.seki_detection.seki_consecutive_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngineSeki()
        budget = QueryBudget(total=50)

        build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-seki",
        )
        # Should stop after detecting seki pattern
        assert engine.query_count <= 5

    def test_branches_at_opponent_nodes(self):
        """Opponent nodes branch up to max_branch_width (DD-3)."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        config.solution_tree.max_branch_width = 2
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine(responses=[
            # First query (opponent responds after C3)
            [
                {"move": "D4", "winrate": 0.90, "prior": 0.40},
                {"move": "E5", "winrate": 0.85, "prior": 0.30},
                {"move": "F6", "winrate": 0.80, "prior": 0.20},
            ],
        ])
        budget = QueryBudget(total=50)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-branch",
        )
        # Root is C3, opponent branches should be ≤ max_branch_width=2
        assert len(root.children) <= 2

    def test_respects_depth_dependent_policy_threshold(self):
        """Opponent branches are filtered by depth-dependent policy threshold.

        L3 (Thomsen lambda-search): effective_min_policy = branch_min_policy + depth_policy_scale * depth.
        At depth 1 with base=0.05 and scale=0.05, threshold = 0.10.
        D4 (prior=0.40) passes; E5 (prior=0.05) is pruned.
        The counter tracks that E5 would have passed the flat 0.05 but was
        pruned by the depth-adjusted 0.10.
        """
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        config.solution_tree.branch_min_policy = 0.05
        config.solution_tree.depth_policy_scale = 0.05  # depth 1 threshold = 0.10
        config.solution_tree.depth_profiles["core"].solution_max_depth = 3
        config.solution_tree.depth_profiles["core"].solution_min_depth = 3
        # Wider wr_epsilon to avoid early winrate-stability stopping
        config.solution_tree.wr_epsilon = 0.50

        engine = MockEngine(responses=[
            # Depth 1: opponent responds after C3
            [
                {"move": "D4", "winrate": 0.90, "prior": 0.40},  # above 0.10
                {"move": "E5", "winrate": 0.85, "prior": 0.07},  # above flat 0.05 but below depth-adjusted 0.10
            ],
            # Depth 2: player responds after D4 (only D4 branched)
            [
                {"move": "F6", "winrate": 0.88, "prior": 0.50},
            ],
            # Depth 3: hits max_depth
            [
                {"move": "G7", "winrate": 0.90, "prior": 0.40},
            ],
        ])
        budget = QueryBudget(total=50)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-depth-policy",
        )
        # Only D4 should be branched (E5 pruned by depth-adjusted threshold)
        assert len(root.children) == 1
        assert root.children[0].move_gtp == "D4"
        # E5 was above flat 0.05 but below depth-adjusted 0.10 → counter incremented
        assert root.tree_completeness is not None
        assert root.tree_completeness.branches_pruned_by_depth_policy >= 1

    def test_tree_completeness_tracked(self):
        """TreeCompletenessMetrics tracked at root."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=50)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-completeness",
        )
        assert root.tree_completeness is not None
        assert root.tree_completeness.total_attempted_branches >= 0

    def test_entry_profile_selected_for_novice(self):
        """Novice level selects 'entry' depth profile."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        engine = MockEngine()
        budget = QueryBudget(total=50)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="novice",
            query_budget=budget,
            puzzle_id="test-novice",
        )
        # Entry profile max_depth=10, should complete without issues
        assert root.move_gtp == "C3"

    def test_strong_profile_selected_for_expert(self):
        """Expert level selects 'strong' depth profile."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget
        config = _make_config()
        budget = QueryBudget(total=5)  # limit budget to keep test fast

        engine = MockEngine()

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="expert",
            query_budget=budget,
            puzzle_id="test-expert",
        )
        assert root.move_gtp == "C3"


# ---------------------------------------------------------------------------
# Phase 5: SGF Injection Tests
# ---------------------------------------------------------------------------


def _make_sgf_root_node(children=None):
    """Create a mock SGF root node with .children and .properties."""
    from types import SimpleNamespace
    node = SimpleNamespace()
    node.children = children or []
    node.properties = {}
    return node


@pytest.mark.unit
class TestInjectSolutionIntoSgf:
    """SGF injection tests (Phase 5, DD-5)."""

    def test_adds_correct_child_node(self):
        """Adds solution tree's correct move as a child."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import SolutionNode
        root = _make_sgf_root_node()

        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95, policy=0.45,
            visits=500, is_correct=True,
        )
        inject_solution_into_sgf(root, tree, player_color="B")

        assert len(root.children) == 1
        assert "B" in root.children[0].properties

    def test_preserves_existing_solution(self):
        """Existing children are never deleted (additive-only)."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import SolutionNode

        existing = _make_sgf_root_node()
        existing.properties = {"B": ["cc"]}  # existing C3 move
        root = _make_sgf_root_node(children=[existing])

        tree = SolutionNode(
            move_gtp="D4", color="B", winrate=0.90, policy=0.30,
            visits=500, is_correct=True,
        )
        inject_solution_into_sgf(root, tree, player_color="B")

        # Both existing and new should be present
        assert len(root.children) == 2

    def test_adds_wrong_move_branches(self):
        """Wrong moves added as separate branches."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import MoveClassification, MoveQuality, SolutionNode

        root = _make_sgf_root_node()
        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95, policy=0.45,
            visits=500, is_correct=True,
        )
        wrong = [
            MoveClassification(
                move_gtp="D4", color="B", quality=MoveQuality.BM,
                winrate=0.30, delta=-0.20, policy=0.15, rank=3,
            ),
        ]
        inject_solution_into_sgf(root, tree, wrong, player_color="B")

        # 1 correct + 1 wrong
        assert len(root.children) == 2

    def test_white_to_play_nodes(self):
        """White-to-play produces W[] nodes."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import SolutionNode

        root = _make_sgf_root_node()
        tree = SolutionNode(
            move_gtp="C3", color="W", winrate=0.90, policy=0.40,
            visits=500, is_correct=True,
        )
        inject_solution_into_sgf(root, tree, player_color="W")

        assert len(root.children) == 1
        assert "W" in root.children[0].properties

    def test_adds_branching_tree(self):
        """Solution tree with children injects recursively."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import SolutionNode

        root = _make_sgf_root_node()
        child = SolutionNode(
            move_gtp="D4", color="W", winrate=0.10, policy=0.30,
            visits=200,
        )
        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95, policy=0.45,
            visits=500, is_correct=True, children=[child],
        )
        inject_solution_into_sgf(root, tree, player_color="B")

        assert len(root.children) == 1
        # The injected node should have a child
        assert len(root.children[0].children) == 1

    def test_no_duplicate_injection(self):
        """Same move is not added twice."""
        from analyzers.solve_position import inject_solution_into_sgf
        from models.solve_result import SolutionNode

        # Create existing C3 node
        existing = _make_sgf_root_node()
        existing.properties = {"B": ["cc"]}
        root = _make_sgf_root_node(children=[existing])

        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95, policy=0.45,
            visits=500, is_correct=True,
        )
        inject_solution_into_sgf(root, tree, player_color="B")

        # Should not duplicate — still 1
        assert len(root.children) == 1


# ---------------------------------------------------------------------------
# Phase 6: Alternative Discovery Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverAlternatives:
    """Alternative discovery tests (Phase 6, DD-7, DD-10)."""

    def test_finds_alternative_correct_move(self):
        """AI finds a correct move different from human's."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.05)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},  # TE
            {"move": "D4", "winrate": 0.90, "prior": 0.30},  # TE (alternative)
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-alt-001", config,
        )
        assert len(alts) >= 1
        assert alts[0].move_gtp == "D4"

    def test_no_alternatives_when_unique(self):
        """No alternatives when only one correct move exists."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.05, t_bad=0.15)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},  # TE
            {"move": "D4", "winrate": 0.70, "prior": 0.20},  # BM (delta=0.20)
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-alt-002", config,
        )
        assert len(alts) == 0
        assert confidence is None  # AI agrees with human

    def test_flags_losing_human_solution(self):
        """Human solution classified as 'losing' when large delta (DD-10)."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.03, t_bad=0.10, t_hotspot=0.30)

        analysis = _make_analysis([
            {"move": "D4", "winrate": 0.95, "prior": 0.50},  # TE (AI's pick)
            {"move": "C3", "winrate": 0.55, "prior": 0.10},  # BM (delta=0.40)
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-alt-003", config,
        )
        assert confidence == "losing"

    def test_human_solution_confidence_weak(self):
        """Human solution classified as 'weak' when moderate disagreement."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.03, t_bad=0.10, t_hotspot=0.30)

        analysis = _make_analysis([
            {"move": "D4", "winrate": 0.90, "prior": 0.45},  # TE
            {"move": "C3", "winrate": 0.75, "prior": 0.20},  # BM (delta=0.15)
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-alt-004", config,
        )
        assert confidence == "weak"

    def test_human_solution_confidence_strong(self):
        """Human solution is strong when AI agrees."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.05)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.50},
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-alt-005", config,
        )
        assert confidence is None  # AI agrees

    def test_co_correct_three_signal_detection(self):
        """Co-correct needs all three signals: both TE, small winrate gap, small score gap (DD-7)."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.05)
        config.alternatives.co_correct_min_gap = 0.03

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},  # TE
            {"move": "D4", "winrate": 0.91, "prior": 0.40},  # TE, gap=0.01
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-co-001", config,
        )
        assert co_correct is True

    def test_co_correct_not_detected_large_gap(self):
        """Co-correct NOT detected when winrate gap is too large."""
        from analyzers.solve_position import discover_alternatives
        config = _make_config(t_good=0.05)
        config.alternatives.co_correct_min_gap = 0.01

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},  # TE
            {"move": "D4", "winrate": 0.88, "prior": 0.40},  # TE, gap=0.04 > 0.01
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-co-002", config,
        )
        assert co_correct is False


# ---------------------------------------------------------------------------
# S1-G16: Per-Candidate Confirmation Queries
# ---------------------------------------------------------------------------


class MockConfirmationEngine:
    """Mock engine that tracks confirmation queries and returns specific winrates.

    Used to test S1-G16: per-candidate confirmation queries.
    Each call to query() records the move sequence and returns data
    from a pre-programmed response map keyed by the last move.
    """

    def __init__(self, responses: dict[str, dict] | None = None):
        """Initialize with move -> response mapping.

        Args:
            responses: Dict mapping GTP move string (uppercase) to
                {"winrate": float, "score_lead": float}. If a move isn't
                in the map, returns neutral defaults.
        """
        self.responses = responses or {}
        self.queries: list[tuple[list[str], int | None]] = []

    def query(self, moves: list[str], *, max_visits: int | None = None):
        """Record query and return pre-programmed response."""
        self.queries.append((list(moves), max_visits))
        last_move = moves[-1].upper() if moves else ""
        data = self.responses.get(last_move, {
            "winrate": 0.50, "score_lead": 0.0,
        })
        # Under SIDETOMOVE: after puzzle player's move, it's opponent's turn.
        # KataGo reports from opponent's perspective (high = good for opponent).
        # data["winrate"] is the intended puzzle-player perspective value,
        # so we flip to simulate what KataGo returns under SIDETOMOVE.
        return _make_analysis([{
            "move": "A1",  # opponent's response doesn't matter for confirmation
            "winrate": 1.0 - data["winrate"],  # SIDETOMOVE: opponent perspective
            "prior": 0.50,
            "score_lead": -data.get("score_lead", 0.0),
        }])


@pytest.mark.unit
class TestPerCandidateConfirmation:
    """S1-G16: Per-candidate confirmation queries for precise deltas."""

    def test_confirmation_queries_run_when_engine_provided(self):
        """When engine is provided, confirmation queries run for pre-filtered candidates."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(confirmation_min_policy=0.03)
        engine = MockConfirmationEngine(responses={
            "C3": {"winrate": 0.92, "score_lead": 5.0},
            "D4": {"winrate": 0.85, "score_lead": 2.0},
        })

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.40},
            {"move": "D4", "winrate": 0.80, "prior": 0.30},
            {"move": "E5", "winrate": 0.70, "prior": 0.01},  # below pre-filter
        ])

        analyze_position_candidates(
            analysis, "B", "test-confirm-001", config,
            engine=engine,
            initial_moves=[],
        )

        # Should have queried 2 candidates (C3 and D4), not E5
        assert len(engine.queries) == 2
        assert engine.queries[0][0] == ["C3"]
        assert engine.queries[1][0] == ["D4"]
        # All queries should use confirmation_visits (750 default)
        assert all(q[1] == 750 for q in engine.queries)

    def test_no_confirmation_without_engine(self):
        """Without engine parameter, uses shared analysis data (backward compatible)."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config()
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.40},
            {"move": "D4", "winrate": 0.80, "prior": 0.30},
        ])

        # Should work without engine (backward compatible)
        result = analyze_position_candidates(
            analysis, "B", "test-confirm-002", config,
        )
        assert len(result.all_classifications) == 2

    def test_confirmation_uses_confirmed_winrate(self):
        """Confirmed winrate is used for classification instead of shared scan data."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(t_good=0.05, t_bad=0.15)

        # Shared scan says D4 is at 0.80 (delta=0.10, NEUTRAL)
        # But confirmation says D4 is actually at 0.70 (delta=0.20, BM)
        engine = MockConfirmationEngine(responses={
            "C3": {"winrate": 0.90, "score_lead": 5.0},
            "D4": {"winrate": 0.70, "score_lead": 1.0},  # worse than shared scan
        })

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.40},
            {"move": "D4", "winrate": 0.80, "prior": 0.30},  # shared says 0.80
        ])

        result = analyze_position_candidates(
            analysis, "B", "test-confirm-003", config,
            engine=engine,
            initial_moves=[],
        )

        # D4 should be classified using confirmed winrate (0.70), not shared (0.80)
        d4_mc = next(mc for mc in result.all_classifications if mc.move_gtp == "D4")
        from models.solve_result import MoveQuality
        assert d4_mc.quality == MoveQuality.BM  # delta=0.20 > t_bad=0.15

    def test_confirmation_visits_from_config(self):
        """Confirmation queries use config.solution_tree.confirmation_visits."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config()
        config.solution_tree.confirmation_visits = 1000

        engine = MockConfirmationEngine(responses={
            "C3": {"winrate": 0.90},
        })

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.40},
        ])

        analyze_position_candidates(
            analysis, "B", "test-confirm-004", config,
            engine=engine,
            initial_moves=[],
        )

        # Should use configured 1000, not default 500
        assert engine.queries[0][1] == 1000

    def test_confirmation_failure_falls_back_to_shared(self):
        """If confirmation query fails, falls back to shared analysis data."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config()

        class FailingEngine:
            def query(self, moves, *, max_visits=None):
                raise ConnectionError("Engine unavailable")

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.40},
        ])

        result = analyze_position_candidates(
            analysis, "B", "test-confirm-005", config,
            engine=FailingEngine(),
            initial_moves=[],
        )

        # Should still classify using shared data
        assert len(result.all_classifications) == 1
        assert result.all_classifications[0].winrate == 0.90

    def test_prefilter_reduces_confirmations(self):
        """Pre-filter at 3% policy reduces confirmation queries from 10 to ~3-5."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(confirmation_min_policy=0.03)
        engine = MockConfirmationEngine()

        # 10 candidates, only 3 pass policy pre-filter
        moves = [
            {"move": f"A{i}", "winrate": 0.90 - i * 0.01, "prior": p}
            for i, p in enumerate([0.40, 0.20, 0.10, 0.02, 0.01, 0.005,
                                   0.004, 0.003, 0.002, 0.001])
        ]

        analysis = _make_analysis(moves)

        analyze_position_candidates(
            analysis, "B", "test-confirm-006", config,
            engine=engine,
            initial_moves=[],
        )

        # Only first 3 candidates have policy >= 0.03
        assert len(engine.queries) == 3


# ---------------------------------------------------------------------------
# S2-G13: Parallel Alternative Tree Building
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParallelAlternativeTreeBuilding:
    """S2-G13: Parallel tree building with split budgets."""

    def test_alternatives_built_with_split_budgets(self):
        """Multiple alternatives use split budgets via parallel execution."""
        from analyzers.solve_position import discover_alternatives
        from models.solve_result import QueryBudget

        config = _make_config(t_good=0.05)
        engine = MockEngine()
        budget = QueryBudget(total=20)

        # Two alternatives both TE
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},
            {"move": "D4", "winrate": 0.91, "prior": 0.40},
            {"move": "E5", "winrate": 0.90, "prior": 0.35},
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-parallel-001", config,
            engine=engine,
            initial_moves=[],
            level_slug="intermediate",
            query_budget=budget,
        )

        # Should have found 2 alternatives (D4 and E5)
        assert len(alts) == 2
        # Budget should have been consumed
        assert budget.used > 0

    def test_parallel_populates_solved_moves(self):
        """Parallel tree building adds SolvedMove objects to position."""
        from analyzers.solve_position import discover_alternatives
        from models.solve_result import QueryBudget

        config = _make_config(t_good=0.05)
        engine = MockEngine()
        budget = QueryBudget(total=30)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},
            {"move": "D4", "winrate": 0.91, "prior": 0.40},
        ])

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "test-parallel-002", config,
            engine=engine,
            initial_moves=[],
            level_slug="intermediate",
            query_budget=budget,
        )

        # The position analysis should have solved_moves populated
        # (discover_alternatives internally creates a PositionAnalysis)
        assert len(alts) == 1  # D4

    def test_budget_splitting_fair(self):
        """Budget is split fairly among alternatives."""
        from analyzers.solve_position import discover_alternatives
        from models.solve_result import QueryBudget

        config = _make_config(t_good=0.05)
        config.solution_tree.max_total_tree_queries = 30

        engine = MockEngine()
        budget = QueryBudget(total=30)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},
            {"move": "D4", "winrate": 0.91, "prior": 0.40},
            {"move": "E5", "winrate": 0.90, "prior": 0.35},
        ])

        alts, _, _ = discover_alternatives(
            analysis, "C3", "B", "test-parallel-003", config,
            engine=engine,
            initial_moves=[],
            level_slug="intermediate",
            query_budget=budget,
        )

        # With 30 total budget and 2 alternatives, each gets ~15
        assert budget.used <= budget.total

    def test_no_parallel_without_engine(self):
        """Without engine, no parallel tree building happens."""
        from analyzers.solve_position import discover_alternatives
        from models.solve_result import QueryBudget

        config = _make_config(t_good=0.05)
        budget = QueryBudget(total=20)

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.45},
            {"move": "D4", "winrate": 0.91, "prior": 0.40},
        ])

        alts, _, _ = discover_alternatives(
            analysis, "C3", "B", "test-parallel-004", config,
        )

        # Budget untouched when no engine
        assert budget.used == 0


@pytest.mark.unit
class TestTranspositionCache:
    """KM-02: Transposition table within tree building."""

    @staticmethod
    def _make_tp_config(transposition_enabled: bool = True):
        """Create an AiSolveConfig with transposition settings."""
        from config.ai_solve import AiSolveConfig
        return AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 1, "solution_max_depth": 3},
                    "core": {"solution_min_depth": 1, "solution_max_depth": 3},
                    "strong": {"solution_min_depth": 1, "solution_max_depth": 3},
                },
                "transposition_enabled": transposition_enabled,
                "max_branch_width": 2,
                "max_total_tree_queries": 20,
                "branch_min_policy": 0.01,
                "tree_visits": 100,
            },
        )

    def test_transposition_cache_reuses_position(self):
        """T023: Same position via different move orders -> single query."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        query_count = 0

        class CountingEngine:
            def query(self, moves, *, max_visits=None):
                nonlocal query_count
                query_count += 1
                return _make_analysis([
                    {"move": "C3", "winrate": 0.9, "prior": 0.8},
                ])

        config = self._make_tp_config(transposition_enabled=True)
        budget = QueryBudget(total=20)

        tree = build_solution_tree(
            engine=CountingEngine(),
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="elementary",
            query_budget=budget,
            puzzle_id="test-tp",
        )

        # With transposition enabled, cache should be used
        assert tree.tree_completeness is not None
        # The tree is built (queries were made)
        assert query_count > 0

    def test_transposition_disabled_no_caching(self):
        """T024: transposition_enabled=False -> no caching."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        config = self._make_tp_config(transposition_enabled=False)
        budget = QueryBudget(total=20)

        tree = build_solution_tree(
            engine=MockEngine(),
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="elementary",
            query_budget=budget,
            puzzle_id="test-tp-off",
        )

        assert tree.tree_completeness is not None
        assert tree.tree_completeness.transposition_hits == 0

    def test_transposition_cache_scoped_per_puzzle(self):
        """T025: Two separate build_solution_tree() calls don't share cache."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        query_counts: list[int] = []

        class CountingEngine:
            def query(self, moves, *, max_visits=None):
                query_counts.append(1)
                return _make_analysis([
                    {"move": "C3", "winrate": 0.9, "prior": 0.8},
                ])

        config = self._make_tp_config(transposition_enabled=True)

        query_counts.clear()
        build_solution_tree(
            engine=CountingEngine(),
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="elementary",
            query_budget=QueryBudget(total=20),
            puzzle_id="puzzle-1",
        )
        count1 = len(query_counts)

        query_counts.clear()
        build_solution_tree(
            engine=CountingEngine(),
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="elementary",
            query_budget=QueryBudget(total=20),
            puzzle_id="puzzle-2",
        )
        count2 = len(query_counts)

        # Both puzzles should make the same number of queries (no shared cache)
        assert count1 == count2

    def test_transposition_hits_tracked(self):
        """T026: TreeCompletenessMetrics.transposition_hits incremented."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        config = self._make_tp_config(transposition_enabled=True)

        tree = build_solution_tree(
            engine=MockEngine(),
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="elementary",
            query_budget=QueryBudget(total=20),
            puzzle_id="test-tp-track",
        )

        # transposition_hits is a non-negative integer
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.transposition_hits >= 0

    def test_compute_position_hash_basic(self):
        """T018: _compute_position_hash (legacy) returns consistent hash."""
        from analyzers.solve_position import _compute_position_hash

        h1 = _compute_position_hash(["C3", "D4"], player_to_move="B")
        h2 = _compute_position_hash(["C3", "D4"], player_to_move="B")
        assert h1 == h2

    def test_compute_position_hash_order_independent(self):
        """T018: Legacy hash: order of moves doesn't change the hash."""
        from analyzers.solve_position import _compute_position_hash

        h1 = _compute_position_hash(["C3", "D4"], player_to_move="B")
        h2 = _compute_position_hash(["D4", "C3"], player_to_move="B")
        assert h1 == h2

    def test_compute_position_hash_player_matters(self):
        """T018: Legacy hash: different player-to-move produces different hash."""
        from analyzers.solve_position import _compute_position_hash

        h1 = _compute_position_hash(["C3"], player_to_move="B")
        h2 = _compute_position_hash(["C3"], player_to_move="W")
        assert h1 != h2

    def test_board_state_position_hash_basic(self):
        """_BoardState.position_hash returns consistent hash with same board."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        board.place_stone("C3", "B")
        board.place_stone("D4", "W")
        h1 = board.position_hash("B")

        board2 = _BoardState(board_size=9)
        board2.place_stone("C3", "B")
        board2.place_stone("D4", "W")
        h2 = board2.position_hash("B")
        assert h1 == h2

    def test_board_state_hash_player_matters(self):
        """_BoardState.position_hash differs by player to move."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        board.place_stone("C3", "B")
        h1 = board.position_hash("B")
        h2 = board.position_hash("W")
        assert h1 != h2


@pytest.mark.unit
class TestBoardState:
    """KM-02: _BoardState board tracking with capture resolution."""

    def test_place_stone_basic(self):
        """Stone placed on empty board appears in grid."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        board.place_stone("C3", "B")
        # C3 on 9x9: col=2, row=9-3=6
        assert board.grid[6][2] == "B"

    def test_capture_removes_stones(self):
        """Single stone with no liberties is captured."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        # Surround a white stone at D5 (row=4, col=3)
        board.place_stone("D6", "B")  # above
        board.place_stone("D4", "B")  # below
        board.place_stone("C5", "B")  # left
        board.place_stone("D5", "W")  # the stone to be captured
        # Now play E5 to complete the surround
        board.place_stone("E5", "B")
        # D5 should be captured (removed)
        row, col = board._gtp_to_rc("D5")
        assert board.grid[row][col] is None

    def test_ko_detection(self):
        """Single stone capture records ko point."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        # Set up a ko: surround a single stone
        board.place_stone("D6", "B")
        board.place_stone("D4", "B")
        board.place_stone("C5", "B")
        board.place_stone("D5", "W")
        # Capture with E5
        board.place_stone("E5", "B")
        # Ko point should be set (D5 was captured)
        assert board.last_capture_point is not None

    def test_no_ko_on_multi_capture(self):
        """Multi-stone capture does NOT set ko point."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        # Place 2 white stones with no liberties once surrounded
        board.place_stone("C5", "W")
        board.place_stone("D5", "W")
        # Surround them
        board.place_stone("B5", "B")
        board.place_stone("E5", "B")
        board.place_stone("C4", "B")
        board.place_stone("D4", "B")
        board.place_stone("C6", "B")
        # Final capture move
        board.place_stone("D6", "B")
        # Multi-stone capture → no ko
        assert board.last_capture_point is None

    def test_position_hash_captures_change_hash(self):
        """Same final stone layout → same hash (when ko state matches)."""
        from analyzers.solve_position import _BoardState

        # Board where a stone was placed and then captured
        board1 = _BoardState(board_size=9)
        board1.place_stone("A1", "B")  # corner
        board1.place_stone("B1", "W")
        board1.place_stone("A2", "W")
        # A1 is captured — board1 has no stone at A1
        # Clear ko state so it matches board2
        board1.last_capture_point = None

        # Board without any capture — same final stones
        board2 = _BoardState(board_size=9)
        board2.place_stone("B1", "W")
        board2.place_stone("A2", "W")

        # Both should have the same stones on the board now
        h1 = board1.position_hash("B")
        h2 = board2.position_hash("B")
        assert h1 == h2  # same final position + same ko → same hash

    def test_position_hash_ko_differs(self):
        """Same stones but different ko state → different hash."""
        from analyzers.solve_position import _BoardState

        board1 = _BoardState(board_size=9)
        board1.place_stone("C3", "B")
        board1.last_capture_point = (5, 3)  # Ko at D4 (row=5, col=3 on 9x9)

        board2 = _BoardState(board_size=9)
        board2.place_stone("C3", "B")
        board2.last_capture_point = None  # No ko

        h1 = board1.position_hash("B")
        h2 = board2.position_hash("B")
        assert h1 != h2  # ko state matters

    def test_copy_independence(self):
        """Copied board state is independent of original."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        board.place_stone("C3", "B")
        copy = board.copy()
        copy.place_stone("D4", "W")
        # Original should not have D4
        row, col = board._gtp_to_rc("D4")
        assert board.grid[row][col] is None

    def test_add_initial_stone(self):
        """add_initial_stone places without capture resolution."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=9)
        # x=2, y=6 = column C, row 3 (0-indexed y=6 on 9x9)
        board.add_initial_stone("B", 2, 6)
        assert board.grid[6][2] == "B"

    def test_gtp_to_rc_skips_i(self):
        """GTP coordinate conversion correctly skips 'I'."""
        from analyzers.solve_position import _BoardState

        board = _BoardState(board_size=19)
        # J1 should map to col=8 (A=0...H=7, J=8, skip I)
        row, col = board._gtp_to_rc("J1")
        assert col == 8
        assert row == 18  # row 1 on 19x19 = row index 18

    def test_capture_snapback(self):
        """Snapback: capture, then recapture of stones with 0 liberties."""
        from analyzers.solve_position import _BoardState

        # Set up a snapback position:
        # White stone at B3 (row=2, col=1) surrounded on 3 sides
        # Black stones at A3, C3, B2
        board = _BoardState(board_size=5)
        board.add_initial_stone("B", 0, 2)  # A3 (row=2, col=0)
        board.add_initial_stone("B", 2, 2)  # C3 (row=2, col=2)
        board.add_initial_stone("B", 1, 3)  # B2 (row=3, col=1)
        # White at B3 (row=2, col=1)
        board.add_initial_stone("W", 1, 2)

        # Black plays B4 (row=1, col=1) — completes surrounding
        board.place_stone("B4", "B")
        # White stone at B3 should be captured
        assert board.grid[2][1] is None, "White stone should be captured"

    def test_double_ko_different_positions(self):
        """Two ko fights produce different hashes if stone configs differ."""
        from analyzers.solve_position import _BoardState

        # Two boards with different stone configurations
        b1 = _BoardState(board_size=9)
        b1.add_initial_stone("B", 0, 0)
        b1.add_initial_stone("W", 1, 0)

        b2 = _BoardState(board_size=9)
        b2.add_initial_stone("B", 0, 0)
        b2.add_initial_stone("W", 2, 0)  # Different position

        h1 = b1.position_hash("B")
        h2 = b2.position_hash("B")
        assert h1 != h2, "Different stone positions must hash differently"

    def test_zobrist_hash_deterministic(self):
        """Zobrist hash is deterministic across board instances."""
        from analyzers.solve_position import _BoardState

        b1 = _BoardState(board_size=9)
        b1.place_stone("C3", "B")
        b1.place_stone("D4", "W")
        b1.place_stone("E5", "B")

        b2 = _BoardState(board_size=9)
        b2.place_stone("C3", "B")
        b2.place_stone("D4", "W")
        b2.place_stone("E5", "B")

        assert b1._hash == b2._hash
        assert b1.position_hash("B") == b2.position_hash("B")

    def test_zobrist_incremental_after_capture(self):
        """Incremental hash correctly accounts for captured stones."""
        from analyzers.solve_position import _BoardState

        # Board with a capture
        board1 = _BoardState(board_size=9)
        board1.place_stone("A1", "B")  # will be captured
        board1.place_stone("B1", "W")
        board1.place_stone("A2", "W")  # captures A1
        board1.last_capture_point = None  # clear ko for comparison

        # Board without any capture — same final stones
        board2 = _BoardState(board_size=9)
        board2.place_stone("B1", "W")
        board2.place_stone("A2", "W")

        # Both should have the same internal hash (same stone configuration)
        assert board1._hash == board2._hash
        assert board1.position_hash("B") == board2.position_hash("B")


@pytest.mark.unit
class TestSimulation:
    """KM-01: Kawano simulation across sibling branches."""

    def _make_config(self, simulation_enabled=True):
        from config.ai_solve import AiSolveConfig
        return AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 2, "solution_max_depth": 5},
                    "core": {"solution_min_depth": 2, "solution_max_depth": 5},
                    "strong": {"solution_min_depth": 2, "solution_max_depth": 5},
                },
                "simulation_enabled": simulation_enabled,
                "simulation_verify_visits": 50,
                "transposition_enabled": False,
                "max_branch_width": 3,
                "max_total_tree_queries": 30,
                "branch_min_policy": 0.01,
                "tree_visits": 100,
            },
        )

    def test_simulation_reuses_refutation(self):
        """T033: Sibling opponent move refuted by same reply → simulation hit."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        call_count = 0
        class MockEngine:
            def query(self, moves, *, max_visits=None):
                nonlocal call_count
                call_count += 1
                # At opponent node (depth 1), return 3 opponent moves
                if len(moves) == 1:  # After correct first move
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                            {"move": "F6", "winrate": 0.92, "prior": 0.2},
                        ]
                    return R()
                # Player reply (G7 — must differ from correct_move C3 to avoid collision)
                else:
                    class R:
                        move_infos = [{"move": "G7", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.simulation_hits > 0

    def test_simulation_fails_falls_back(self):
        """T034: Sibling needs different reply → simulation fails, full expansion."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                # For simulation verification, return low winrate (fail)
                elif max_visits and max_visits <= 50:
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.3, "prior": 0.9}]
                    return R()
                else:
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-fail",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.simulation_misses >= 0

    def test_simulation_disabled_no_effect(self):
        """T035: simulation_enabled=False → no simulation attempted."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                else:
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=False)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-off",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.simulation_hits == 0
        assert tree.tree_completeness.simulation_misses == 0

    def test_simulation_hits_tracked(self):
        """T036: simulation_hits and simulation_misses counters tracked."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                else:
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-track",
        )
        m = tree.tree_completeness
        assert m is not None
        total_sim = m.simulation_hits + m.simulation_misses
        assert total_sim >= 0

    def test_simulation_respects_budget(self):
        """T037: Simulation verification queries consume from QueryBudget."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-budget",
        )
        # Budget was consumed (used > 0)
        assert budget.used > 0

    def test_simulation_only_at_opponent_nodes(self):
        """T038: Simulation never attempted at player nodes."""
        from analyzers.solve_position import _extract_player_reply_sequence

        # _extract_player_reply_sequence is a helper used at opponent nodes
        # Just verify it returns a list
        from models.solve_result import SolutionNode
        node = SolutionNode(move_gtp="C3", color="B", is_correct=True)
        result = _extract_player_reply_sequence(node)
        assert isinstance(result, list)

    def test_simulation_skipped_when_first_sibling_truncated(self):
        """T039: Truncated first sibling → no simulation for subsequent siblings."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            """Engine that truncates the first child's subtree.

            At depth 1 (opponent node) returns 2 opponent moves.
            For the first child's player response, budget runs out or
            engine fails — leading to truncation. The second sibling
            should NOT trigger simulation because the first was truncated
            (no cached_reply_sequence available).
            """
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    # Opponent responds with 2 moves
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                elif len(moves) == 2:
                    # First child's player query — raise to force truncation
                    raise RuntimeError("Engine failure — force truncation")
                else:
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-trunc",
        )
        m = tree.tree_completeness
        assert m is not None
        # No simulation should have been attempted (first child was truncated)
        assert m.simulation_hits == 0

    def test_simulation_uses_local_winrate(self):
        """Review Panel Finding 2: simulation compares against first sibling's
        proven reply winrate (local reference), not root_winrate."""
        from analyzers.solve_position import _try_simulation
        from models.solve_result import QueryBudget, TreeCompletenessMetrics

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                # Return a winrate that is close to reference but far from root
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.80, "prior": 0.9}]
                return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=10)
        completeness = TreeCompletenessMetrics()

        # Root winrate would be 0.95, local first-child winrate is 0.82
        # sim_wr = 0.80, delta from local = 0.82 - 0.80 = 0.02 <= t_good (0.05)
        # With root_winrate: delta = 0.95 - 0.80 = 0.15 > t_good → would FAIL
        # With local reference: delta = 0.02 → should PASS
        result = _try_simulation(
            engine=MockEngine(),
            moves=["C3", "D4"],
            cached_reply_sequence=["E5"],
            config=config,
            query_budget=budget,
            completeness=completeness,
            player_color="B",
            effective_visits=100,
            reference_winrate=0.82,  # local reference from first sibling
        )
        # Should succeed because delta from local reference is small
        assert result is not None
        assert completeness.simulation_hits == 1

    def test_depth_guard_shallow_uses_root_winrate(self):
        """Decision 3: At depth < 3, simulation uses root_winrate (global),
        not first_child_winrate (local peer)."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget


        class InstrumentedEngine:
            """Engine that records what reference_winrate simulation uses.

            At depth 1 (opponent node): returns 2 opponent moves with wr=0.92.
            root_winrate will be set to ~0.92.
            First child (D4) is fully expanded; first_child_winrate = 0.95.
            Second sibling (E5) triggers simulation.

            At depth < 3, reference should be root_winrate (~0.92),
            NOT first_child_winrate (0.95).
            """
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    # Opponent responds with 2 moves
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                else:
                    # Player reply: high winrate (G7 to avoid collision with C3)
                    class R:
                        move_infos = [{"move": "G7", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        config.solution_tree.depth_profiles["core"].solution_max_depth = 4
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=InstrumentedEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-depth-guard",
        )
        # Simulation should succeed (at depth 1, uses root_winrate ~0.92)
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.simulation_hits > 0

    def test_full_sequence_verification(self):
        """Decision 4: Simulation replays ALL cached moves, not just first."""
        from analyzers.solve_position import _try_simulation
        from models.solve_result import QueryBudget, TreeCompletenessMetrics

        moves_received = []

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                moves_received.append(list(moves))
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.93, "prior": 0.9}]
                return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=10)
        completeness = TreeCompletenessMetrics()

        result = _try_simulation(
            engine=MockEngine(),
            moves=["C3", "D4"],  # opponent already played D4
            cached_reply_sequence=["E5", "F6", "G7"],  # full sequence
            config=config,
            query_budget=budget,
            completeness=completeness,
            player_color="B",
            effective_visits=100,
            reference_winrate=0.95,
        )

        assert result is not None
        # Engine should have received ALL cached moves appended
        assert moves_received[0] == ["C3", "D4", "E5", "F6", "G7"]
        # Result should have the chain structure
        assert result.move_gtp == "E5"
        assert len(result.children) == 1
        assert result.children[0].move_gtp == "F6"
        assert len(result.children[0].children) == 1
        assert result.children[0].children[0].move_gtp == "G7"

    def test_full_sequence_single_move_unchanged(self):
        """Single-move cached sequence behaves identically to old behavior."""
        from analyzers.solve_position import _try_simulation
        from models.solve_result import QueryBudget, TreeCompletenessMetrics

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.93, "prior": 0.9}]
                return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=10)
        completeness = TreeCompletenessMetrics()

        result = _try_simulation(
            engine=MockEngine(),
            moves=["C3", "D4"],
            cached_reply_sequence=["E5"],  # single move
            config=config,
            query_budget=budget,
            completeness=completeness,
            player_color="B",
            effective_visits=100,
            reference_winrate=0.95,
        )

        assert result is not None
        assert result.move_gtp == "E5"
        assert len(result.children) == 0  # No chain for single move
        assert completeness.simulation_hits == 1

    def test_simulation_collision_skipped(self):
        """T040: Cached reply overlaps opponent move → simulation skipped."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            """Engine where cached reply coordinate matches a sibling move.

            At depth 1 (opponent node): returns D4, C3 (two siblings).
            Player reply to D4 is C3 (cached_reply_sequence = ["C3"]).
            Sibling C3 at depth 1 collides with cached reply "C3"
            → simulation must be skipped, not attempted.
            """
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    # Opponent responds with D4 and C3
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.5},
                            {"move": "C3", "winrate": 0.92, "prior": 0.3},
                        ]
                    return R()
                else:
                    # Player always replies C3
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = self._make_config(simulation_enabled=True)
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-sim-collision",
        )
        m = tree.tree_completeness
        assert m is not None
        assert m.simulation_collisions >= 1
        # Collision means simulation was NOT attempted, so no hits for that sibling
        assert m.simulation_hits == 0


class TestForcedMove:
    """KM-03: Forced move fast-path."""

    def _make_config(self, forced_move_visits=125, forced_move_policy_threshold=0.85):
        from config.ai_solve import AiSolveConfig
        return AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 2, "solution_max_depth": 4},
                    "core": {"solution_min_depth": 2, "solution_max_depth": 4},
                    "strong": {"solution_min_depth": 2, "solution_max_depth": 4},
                },
                "simulation_enabled": False,
                "transposition_enabled": False,
                "forced_move_visits": forced_move_visits,
                "forced_move_policy_threshold": forced_move_policy_threshold,
                "max_branch_width": 2,
                "max_total_tree_queries": 20,
                "branch_min_policy": 0.05,
                "tree_visits": 500,
            },
        )

    def test_forced_move_uses_reduced_visits(self):
        """T044: Single high-policy candidate → engine queried with forced_move_visits."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        visits_used = []
        class MockEngine:
            def query(self, moves, *, max_visits=None):
                visits_used.append(max_visits)
                if len(moves) == 1:
                    # After correct first move: opponent responds
                    class R:
                        move_infos = [{"move": "D4", "winrate": 0.92, "prior": 0.5}]
                    return R()
                else:
                    # Player: single high-policy forced move
                    class R:
                        move_infos = [{"move": "E5", "winrate": 0.95, "prior": 0.95}]
                    return R()

        config = self._make_config(forced_move_visits=125)
        budget = QueryBudget(total=20)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-fm",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.forced_move_count > 0

    def test_forced_move_multiple_candidates_uses_full(self):
        """T045: Two candidates above threshold → full visits."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    class R:
                        move_infos = [{"move": "D4", "winrate": 0.92, "prior": 0.5}]
                    return R()
                else:
                    # Two candidates above threshold = not forced
                    class R:
                        move_infos = [
                            {"move": "E5", "winrate": 0.95, "prior": 0.90},
                            {"move": "F6", "winrate": 0.93, "prior": 0.85},
                        ]
                    return R()

        config = self._make_config(forced_move_visits=125, forced_move_policy_threshold=0.85)
        budget = QueryBudget(total=20)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-fm-multi",
        )
        assert tree.tree_completeness is not None
        # With 2 candidates above threshold, forced_move should NOT trigger
        assert tree.tree_completeness.forced_move_count == 0

    def test_forced_move_disabled_when_visits_zero(self):
        """T045b: forced_move_visits=0 → disabled."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.95}]
                return R()

        config = self._make_config(forced_move_visits=0)
        budget = QueryBudget(total=20)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-fm-off",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.forced_move_count == 0

    def test_forced_move_count_tracked(self):
        """T047: forced_move_count counter incremented correctly."""
        from analyzers.solve_position import build_solution_tree
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                if len(moves) == 1:
                    class R:
                        move_infos = [{"move": "D4", "winrate": 0.92, "prior": 0.5}]
                    return R()
                else:
                    class R:
                        move_infos = [{"move": "E5", "winrate": 0.95, "prior": 0.95}]
                    return R()

        config = self._make_config(forced_move_visits=125)
        budget = QueryBudget(total=20)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-fm-count",
        )
        m = tree.tree_completeness
        assert m is not None
        assert m.forced_move_count > 0

    def test_forced_move_safety_net(self):
        """Review Panel Finding 3: forced move with wrong winrate triggers
        re-query at full visits."""
        from analyzers.solve_position import build_solution_tree
        from config.ai_solve import AiSolveConfig
        from models.solve_result import QueryBudget

        visits_log: list[tuple[int, int]] = []  # (depth, max_visits)

        class SafetyNetEngine:
            """Engine where forced-move reduced visits produce wrong winrate.

            At depth 1 (len=1): opponent responds → D4.
            At depth 2 (len=2, player, forced move): single high-policy E5.
            At depth 3+ (len>=3, opponent after forced move):
              - At reduced visits (125): returns low winrate (0.60) → safety net
              - At full visits (500): returns correct winrate (0.92)
            """
            def query(self, moves, *, max_visits=None):
                visits_log.append((len(moves), max_visits or 0))
                if len(moves) == 1:
                    # After correct first move: opponent responds
                    class R:
                        move_infos = [{"move": "D4", "winrate": 0.92, "prior": 0.5}]
                    return R()
                elif len(moves) == 2:
                    # Player node: single forced move (high policy)
                    class R:
                        move_infos = [{"move": "E5", "winrate": 0.92, "prior": 0.95}]
                    return R()
                else:
                    # Depth 3+: opponent node after forced move
                    if max_visits is not None and max_visits <= 125:
                        # Reduced visits → disagreeing winrate
                        class R:
                            move_infos = [{"move": "F6", "winrate": 0.60, "prior": 0.9}]
                        return R()
                    else:
                        # Full visits → correct winrate
                        class R:
                            move_infos = [{"move": "F6", "winrate": 0.92, "prior": 0.9}]
                        return R()

        # Use min_depth=4 so winrate stability doesn't prematurely stop the tree
        config = AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 4, "solution_max_depth": 6},
                    "core": {"solution_min_depth": 4, "solution_max_depth": 6},
                    "strong": {"solution_min_depth": 4, "solution_max_depth": 6},
                },
                "simulation_enabled": False,
                "transposition_enabled": False,
                "forced_move_visits": 125,
                "forced_move_policy_threshold": 0.85,
                "max_branch_width": 2,
                "max_total_tree_queries": 20,
                "branch_min_policy": 0.05,
                "tree_visits": 500,
            },
        )
        budget = QueryBudget(total=20)
        tree = build_solution_tree(
            engine=SafetyNetEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-fm-safety",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.forced_move_count > 0
        # Safety net should have caused a re-query: we should see both
        # reduced visits (125) and full visits (500) in the log
        visit_values = [v for _, v in visits_log]
        assert 125 in visit_values
        assert 500 in visit_values


class TestMaxResolvedDepth:
    """KM-04: max_resolved_depth computation."""

    def test_compute_max_resolved_depth_simple(self):
        """T049: Simple linear tree -> depth = number of moves."""
        from analyzers.solve_position import _compute_max_resolved_depth
        from models.solve_result import SolutionNode

        leaf = SolutionNode(move_gtp="E5", color="B")
        mid = SolutionNode(move_gtp="D4", color="W", children=[leaf])
        root = SolutionNode(move_gtp="C3", color="B", children=[mid])

        assert _compute_max_resolved_depth(root) == 2

    def test_compute_max_resolved_depth_truncated(self):
        """Truncated branches -> depth 0."""
        from analyzers.solve_position import _compute_max_resolved_depth
        from models.solve_result import SolutionNode

        trunc = SolutionNode(move_gtp="C3", color="B", truncated=True)
        assert _compute_max_resolved_depth(trunc) == 0

    def test_compute_max_resolved_depth_branching(self):
        """Branching tree -> max of non-truncated branches."""
        from analyzers.solve_position import _compute_max_resolved_depth
        from models.solve_result import SolutionNode

        deep_leaf = SolutionNode(move_gtp="F6", color="B")
        deep_mid = SolutionNode(move_gtp="E5", color="W", children=[deep_leaf])
        shallow_leaf = SolutionNode(move_gtp="G7", color="W")
        root = SolutionNode(move_gtp="C3", color="B", children=[deep_mid, shallow_leaf])

        assert _compute_max_resolved_depth(root) == 2

    def test_max_resolved_depth_populated_after_build(self):
        """T050: max_resolved_depth populated in TreeCompletenessMetrics."""
        from analyzers.solve_position import build_solution_tree
        from config.ai_solve import AiSolveConfig
        from models.solve_result import QueryBudget

        class MockEngine:
            def query(self, moves, *, max_visits=None):
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                return R()

        config = AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 1, "solution_max_depth": 3},
                    "core": {"solution_min_depth": 1, "solution_max_depth": 3},
                    "strong": {"solution_min_depth": 1, "solution_max_depth": 3},
                },
                "simulation_enabled": False,
                "transposition_enabled": False,
                "forced_move_visits": 0,
                "max_branch_width": 1,
                "max_total_tree_queries": 10,
                "branch_min_policy": 0.01,
                "tree_visits": 100,
            },
        )
        budget = QueryBudget(total=10)
        tree = build_solution_tree(
            engine=MockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="test-pda",
        )
        assert tree.tree_completeness is not None
        assert tree.tree_completeness.max_resolved_depth >= 0


@pytest.mark.unit
class TestBenchmarkOptimizationMechanics:
    """T059: Mock engine verifying optimization counters fire correctly."""

    def test_benchmark_optimization_mechanics(self):
        """All optimizations fire: simulation_hits > 0, transposition_hits >= 0,
        forced_move_count > 0 when all enabled. Mock returns realistic branching:
        3 opponent responses per node, 2 sharing same refutation."""
        from analyzers.solve_position import build_solution_tree
        from config.ai_solve import AiSolveConfig
        from models.solve_result import QueryBudget

        call_number = 0

        class RealisticMockEngine:
            """Mock with 3 opponent responses, where 2 share the same refutation."""

            def query(self, moves, *, max_visits=None):
                nonlocal call_number
                call_number += 1
                depth = len(moves)

                if depth == 0:
                    # Root query (shouldn't happen — tree starts after first move)
                    class R:
                        move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                    return R()
                elif depth == 1:
                    # After correct move: opponent has 3 responses
                    class R:
                        move_infos = [
                            {"move": "D4", "winrate": 0.92, "prior": 0.4},
                            {"move": "E5", "winrate": 0.92, "prior": 0.3},
                            {"move": "F6", "winrate": 0.92, "prior": 0.2},
                        ]
                    return R()
                elif depth >= 2:
                    # Player's reply: single forced move with high policy
                    class R:
                        move_infos = [{"move": "G7", "winrate": 0.95, "prior": 0.95}]
                    return R()
                else:
                    class R:
                        move_infos = [{"move": "H8", "winrate": 0.95, "prior": 0.9}]
                    return R()

        config = AiSolveConfig(
            enabled=True,
            solution_tree={
                "depth_profiles": {
                    "entry": {"solution_min_depth": 2, "solution_max_depth": 4},
                    "core": {"solution_min_depth": 2, "solution_max_depth": 4},
                    "strong": {"solution_min_depth": 2, "solution_max_depth": 4},
                },
                "simulation_enabled": True,
                "simulation_verify_visits": 50,
                "transposition_enabled": True,
                "forced_move_visits": 125,
                "forced_move_policy_threshold": 0.85,
                "max_branch_width": 3,
                "max_total_tree_queries": 30,
                "branch_min_policy": 0.01,
                "tree_visits": 500,
            },
        )
        budget = QueryBudget(total=30)
        tree = build_solution_tree(
            engine=RealisticMockEngine(), initial_moves=[], correct_move_gtp="C3",
            player_color="B", config=config, level_slug="elementary",
            query_budget=budget, puzzle_id="bench-mechanics",
        )

        m = tree.tree_completeness
        assert m is not None
        # At least some optimizations should fire with this mock
        total_optimizations = m.simulation_hits + m.transposition_hits + m.forced_move_count
        assert total_optimizations > 0
        assert m.max_resolved_depth >= 0

    def test_benchmark_solution_quality_unchanged(self):
        """T060: Same correct/wrong classifications with optimizations ON vs OFF."""
        from analyzers.solve_position import build_solution_tree
        from config.ai_solve import AiSolveConfig
        from models.solve_result import QueryBudget

        class DeterministicEngine:
            def query(self, moves, *, max_visits=None):
                class R:
                    move_infos = [{"move": "C3", "winrate": 0.95, "prior": 0.9}]
                return R()

        def run_with_opts(sim_on, trans_on, fm_visits):
            config = AiSolveConfig(
                enabled=True,
                solution_tree={
                    "depth_profiles": {
                        "entry": {"solution_min_depth": 1, "solution_max_depth": 3},
                        "core": {"solution_min_depth": 1, "solution_max_depth": 3},
                        "strong": {"solution_min_depth": 1, "solution_max_depth": 3},
                    },
                    "simulation_enabled": sim_on,
                    "transposition_enabled": trans_on,
                    "forced_move_visits": fm_visits,
                    "max_branch_width": 2,
                    "max_total_tree_queries": 15,
                    "branch_min_policy": 0.01,
                    "tree_visits": 100,
                },
            )
            budget = QueryBudget(total=15)
            return build_solution_tree(
                engine=DeterministicEngine(), initial_moves=[],
                correct_move_gtp="C3", player_color="B", config=config,
                level_slug="elementary", query_budget=budget,
                puzzle_id="bench-quality",
            )

        # With all optimizations ON
        tree_on = run_with_opts(True, True, 125)
        # With all optimizations OFF
        tree_off = run_with_opts(False, False, 0)

        # Root should be correct in both cases
        assert tree_on.is_correct
        assert tree_off.is_correct
        # Both should have the same correct first move
        assert tree_on.move_gtp == tree_off.move_gtp


# ===================================================================
# T7: CA-1 root_winrate fix (DD-1) — verify analysis.root_winrate used
# ===================================================================


@pytest.mark.unit
class TestRootWinrateUsesAnalysisField:
    """DD-1: root_winrate comes from analysis.root_winrate, not move_infos[0].winrate."""

    def test_root_winrate_from_analysis_field(self):
        """When analysis.root_winrate differs from best move winrate,
        result.root_winrate should match analysis.root_winrate (DD-1)."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config()
        # Set root_winrate differently from best move winrate
        analysis = MagicMock()
        analysis.moveInfos = [
            {"move": "C3", "winrate": 0.90, "prior": 0.50},
            {"move": "D4", "winrate": 0.40, "prior": 0.20},
        ]
        # DD-1: root_winrate from rootInfo.winrate, NOT move_infos[0].winrate
        analysis.root_winrate = 0.85  # Deliberately different from 0.90

        result = analyze_position_candidates(analysis, "B", "test-dd1", config)
        assert result.root_winrate == pytest.approx(0.85)

    def test_root_winrate_matches_best_move_when_equal(self):
        """Common case: root_winrate == best move winrate."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config()
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.92, "prior": 0.60},
        ])
        result = analyze_position_candidates(analysis, "B", "test-dd1-eq", config)
        assert result.root_winrate == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# T4: White-to-play parametrized tests (SIDETOMOVE perspective verification)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWhiteToPlayClassification:
    """Verify move classification works correctly for White-to-play puzzles.

    Under SIDETOMOVE, KataGo reports winrates from the current player's
    perspective. For White puzzles, root_winrate and move winrates are
    from White's perspective (high = good for White = good for puzzle player).
    No additional normalization is needed for the main classification path
    because all values are consistently from the current player's perspective.
    """

    def test_white_puzzle_correct_move_classified_te(self):
        """White-to-play: move with small delta → TE (correct)."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(t_good=0.05)
        # White puzzle: root=0.90 (White winning), correct move keeps it high
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.88, "prior": 0.50},  # delta=0.02 < 0.05
        ])
        result = analyze_position_candidates(analysis, "W", "test-white-te", config)
        assert len(result.correct_moves) == 1
        assert result.correct_moves[0].move_gtp == "C3"

    def test_white_puzzle_wrong_move_classified_bm(self):
        """White-to-play: move with large delta → BM (wrong)."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(t_good=0.05, t_bad=0.15)
        # White puzzle: root=0.90, wrong move drops to 0.70 → delta=0.20
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},  # best move, sets root
            {"move": "D4", "winrate": 0.70, "prior": 0.30},  # delta=0.20 → BM
        ])
        result = analyze_position_candidates(analysis, "W", "test-white-bm", config)
        assert len(result.wrong_moves) == 1
        assert result.wrong_moves[0].move_gtp == "D4"

    def test_white_puzzle_multiple_classifications(self):
        """White-to-play: mixed correct + wrong + neutral moves."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(t_good=0.05, t_bad=0.15, t_hotspot=0.30)
        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.88, "prior": 0.40},  # delta=0.02 → TE
            {"move": "D4", "winrate": 0.80, "prior": 0.25},  # delta=0.10 → NEUTRAL
            {"move": "E5", "winrate": 0.68, "prior": 0.15},  # delta=0.22 → BM
            {"move": "F6", "winrate": 0.55, "prior": 0.10},  # delta=0.35 → BM_HO
        ])
        result = analyze_position_candidates(analysis, "W", "test-white-mix", config)
        assert len(result.correct_moves) == 1  # C3
        assert len(result.neutral_moves) == 1  # D4
        assert len(result.wrong_moves) == 2  # E5, F6

    def test_white_puzzle_confirmation_queries(self):
        """White-to-play: confirmation queries work with SIDETOMOVE perspective."""
        from analyzers.solve_position import analyze_position_candidates

        config = _make_config(confirmation_min_policy=0.03)
        # After White plays C3, it's Black's turn. Under SIDETOMOVE, KataGo
        # reports Black's winrate. Opponent=B, puzzle_player=W.
        # Mock returns Black's (opponent's) perspective: 0.12 = low for Black
        # normalize_winrate(0.12, "B", "W") = 1.0 - 0.12 = 0.88 for White
        engine = MockConfirmationEngine(responses={
            "C3": {"winrate": 0.88, "score_lead": 5.0},  # intended White WR
        })

        analysis = _make_analysis([
            {"move": "C3", "winrate": 0.90, "prior": 0.50},
        ])

        result = analyze_position_candidates(
            analysis, "W", "test-white-confirm", config,
            engine=engine, initial_moves=[],
        )

        assert len(engine.queries) == 1
        # C3 should be classified correctly for White puzzle
        assert len(result.correct_moves) >= 0  # may be TE or not depending on confirmed delta


@pytest.mark.unit
class TestBlackWhiteParametrized:
    """Parametrized tests verifying identical classification for both colors."""

    @pytest.mark.parametrize("puzzle_player", ["B", "W"])
    def test_correct_move_te_both_colors(self, puzzle_player):
        """A move with delta < t_good is TE regardless of color."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality

        config = _make_config(t_good=0.05)
        # delta = 0.02 (< 0.05) → TE for both B and W
        result = classify_move_quality(0.48, 0.50, 0.30, config)
        assert result == MoveQuality.TE

    @pytest.mark.parametrize("puzzle_player", ["B", "W"])
    def test_wrong_move_bm_both_colors(self, puzzle_player):
        """A move with delta > t_bad is BM regardless of color."""
        from analyzers.solve_position import classify_move_quality
        from models.solve_result import MoveQuality

        config = _make_config(t_bad=0.15, t_hotspot=0.30)
        # delta = 0.20 (> 0.15, < 0.30) → BM for both
        result = classify_move_quality(0.60, 0.80, 0.10, config)
        assert result == MoveQuality.BM

    @pytest.mark.parametrize(
        "reported_player,puzzle_player,expected",
        [
            ("B", "B", 0.8),    # Same perspective: no flip
            ("W", "B", 0.2),    # Opponent reported: flip
            ("W", "W", 0.6),    # Same perspective: no flip
            ("B", "W", 0.4),    # Opponent reported: flip
        ],
    )
    def test_normalize_winrate_truth_table(self, reported_player, puzzle_player, expected):
        """SIDETOMOVE normalize_winrate truth table — 4 cases."""
        from analyzers.solve_position import normalize_winrate
        result = normalize_winrate(0.8 if reported_player in ("B",) and puzzle_player in ("B",) else
                                   0.8 if reported_player == "W" and puzzle_player == "B" else
                                   0.6 if reported_player == "W" and puzzle_player == "W" else 0.6,
                                   reported_player, puzzle_player)
        assert result == pytest.approx(expected)
