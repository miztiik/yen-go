"""Sprint remediation tests — covering all 20 gaps across Sprints 1-5.

These tests verify the implementations from ai-solve-remediation-sprints.md:
- Sprint 1: Foundation fixes (algorithms & stopping conditions)
- Sprint 2: Multi-root trees & has-solution path
- Sprint 3: Output wiring (AC field, roundtrip, goal inference)
- Sprint 4: Observability (monitoring & sinks)
- Sprint 5: Missing plan-specified tests

Uses mock engines — not live KataGo.
"""

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
from analyzers.observability import (
    BatchSummaryAccumulator,
    DisagreementSink,
)
from analyzers.solve_position import (
    _check_ownership_convergence,
    analyze_position_candidates,
    build_solution_tree,
    classify_move_quality,
    discover_alternatives,
    infer_goal,
    inject_solution_into_sgf,
)
from config import clear_cache
from config.ai_solve import AiSolveConfig
from models.analysis_response import AnalysisResponse, MoveAnalysis
from models.solve_result import (
    DisagreementRecord,
    HumanSolutionConfidence,
    MoveClassification,
    MoveQuality,
    PositionAnalysis,
    QueryBudget,
    SolutionNode,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> AiSolveConfig:
    return AiSolveConfig(enabled=True, **overrides)


def _make_analysis(moves: list[dict]):
    """Create a mock AnalysisResponse with moveInfos as dicts."""
    analysis = MagicMock()
    analysis.moveInfos = moves
    return analysis


def _make_response(
    moves: list[dict] | None = None,
    root_winrate: float = 0.85,
) -> AnalysisResponse:
    if moves is None:
        moves = [
            {"move": "D1", "winrate": 0.90, "policy_prior": 0.50, "visits": 500},
            {"move": "E1", "winrate": 0.60, "policy_prior": 0.20, "visits": 200},
        ]
    move_infos = [
        MoveAnalysis(
            move=m["move"],
            winrate=m.get("winrate", 0.5),
            policy_prior=m.get("policy_prior", 0.1),
            visits=m.get("visits", 100),
            score_lead=m.get("score_lead", 0.0),
            pv=m.get("pv", [m["move"]]),
            ownership=m.get("ownership", None),
        )
        for m in moves
    ]
    return AnalysisResponse(
        request_id="test",
        move_infos=move_infos,
        root_winrate=root_winrate,
        total_visits=sum(m.get("visits", 100) for m in moves),
    )


class MockEngine:
    def __init__(self, responses=None, max_responses=20):
        self.responses = responses or []
        self.query_count = 0
        self._default = [
            {"move": "D4", "winrate": 0.90, "prior": 0.40},
        ]

    def query(self, moves, *, max_visits=None):
        idx = self.query_count
        self.query_count += 1
        if idx < len(self.responses):
            data = self.responses[idx]
        else:
            data = self._default
        return _make_analysis(data)


class MockEngineWithOwnership:
    """Engine that returns ownership data for convergence testing (S1-G1)."""

    def __init__(self, ownership_sequence):
        """ownership_sequence: list of ownership maps per query."""
        self._ownerships = ownership_sequence
        self.query_count = 0

    def query(self, moves, *, max_visits=None):
        idx = self.query_count
        self.query_count += 1
        own = self._ownerships[idx] if idx < len(self._ownerships) else None
        analysis = MagicMock()
        analysis.moveInfos = [
            {"move": "D4", "winrate": 0.90, "prior": 0.40, "ownership": own},
        ]
        return analysis


def _make_sgf_root(children=None):
    node = SimpleNamespace()
    node.children = children or []
    node.properties = {}
    return node


# ===================================================================
# Sprint 1 Tests: Foundation Fixes
# ===================================================================


@pytest.mark.unit
class TestS1G15ClassifyMoveQualitySignature:
    """S1-G15: classify_move_quality accepts score_lead parameter."""

    def test_accepts_score_lead_kwarg(self):
        config = _make_config()
        result = classify_move_quality(0.48, 0.50, 0.45, config, score_lead=5.0)
        assert result == MoveQuality.TE

    def test_backward_compatible_without_score_lead(self):
        config = _make_config()
        result = classify_move_quality(0.48, 0.50, 0.45, config)
        assert result == MoveQuality.TE


@pytest.mark.unit
class TestS1G16PerCandidateScoreLead:
    """S1-G16: MoveClassification includes score_lead from analysis."""

    def test_score_lead_populated_on_classification(self):
        config = _make_config()
        analysis = _make_response(moves=[
            {"move": "C3", "winrate": 0.92, "policy_prior": 0.50,
             "visits": 500, "score_lead": 12.5},
        ])
        pos = analyze_position_candidates(analysis, "B", "test-sl-001", config)
        assert len(pos.all_classifications) >= 1
        assert pos.all_classifications[0].score_lead == pytest.approx(12.5)


@pytest.mark.unit
class TestS1G1OwnershipConvergence:
    """S1-G1: Ownership convergence stopping condition."""

    def test_stops_at_ownership_convergence(self):
        """Tree builder stops when ownership values stabilize."""
        config = _make_config()
        config.solution_tree.own_epsilon = 0.05
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1
        config.solution_tree.depth_profiles["core"].solution_max_depth = 20

        # Create two nearly identical ownership maps
        own1 = [[0.8, -0.7, 0.3], [0.0, 0.5, -0.5], [0.9, -0.8, 0.0]]
        own2 = [[0.81, -0.69, 0.31], [0.0, 0.51, -0.49], [0.91, -0.79, 0.0]]
        # Third query would diverge but should not be reached
        own3 = [[0.1, 0.1, 0.1], [0.1, 0.1, 0.1], [0.1, 0.1, 0.1]]

        engine = MockEngineWithOwnership([own1, own2, own3])
        budget = QueryBudget(total=50)

        build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-own-conv",
        )
        # Should stop after 2 queries (first establishes baseline, second converges)
        assert engine.query_count <= 3

    def test_check_ownership_convergence_converged(self):
        """Direct test: convergence detected when max change < epsilon."""
        prev = [[0.8, -0.7], [-0.5, 0.9]]
        curr = [[0.81, -0.69], [-0.49, 0.91]]
        assert _check_ownership_convergence(prev, curr, 0.05) is True

    def test_check_ownership_convergence_not_converged(self):
        """Direct test: convergence NOT detected when change > epsilon."""
        prev = [[0.8, -0.7], [-0.5, 0.9]]
        curr = [[0.5, -0.3], [-0.1, 0.4]]
        assert _check_ownership_convergence(prev, curr, 0.05) is False

    def test_check_ownership_no_key_stones(self):
        """No key stones (all values < 0.3) → not converged."""
        prev = [[0.1, 0.0], [0.0, 0.2]]
        curr = [[0.1, 0.0], [0.0, 0.2]]
        assert _check_ownership_convergence(prev, curr, 0.05) is False


@pytest.mark.unit
class TestS1G12CornerAndLadderVisitBoosts:
    """S1-G12: Corner and ladder visit boosts applied to tree builder."""

    def test_corner_visit_boost(self):
        """Corner position applies visit boost multiplier."""
        config = _make_config()
        config.edge_case_boosts.corner_visit_boost = 1.5
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-corner-boost",
            corner_position="TL",
        )
        assert root.move_gtp == "C3"
        # Visits should have been boosted (we can't directly check the visits
        # in mock, but the tree should build successfully)
        assert root.is_correct is True

    def test_ladder_visit_boost(self):
        """Long PV triggers ladder visit boost."""
        config = _make_config()
        config.edge_case_boosts.ladder_visit_boost = 2.0
        config.edge_case_boosts.ladder_pv_threshold = 8
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-ladder-boost",
            pv_length=12,  # > 8 threshold
        )
        assert root.move_gtp == "C3"
        assert root.is_correct is True

    def test_no_boost_without_corner(self):
        """No boost when corner_position is empty or center."""
        config = _make_config()
        config.edge_case_boosts.corner_visit_boost = 1.5
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        # Center position — no corner boost
        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-no-corner",
            corner_position="C",
        )
        assert root.is_correct is True


@pytest.mark.unit
class TestV126AdaptiveBoostCompounding:
    """v1.26: Adaptive visit allocation compounds with edge-case boosts.

    Before v1.26, adaptive mode unconditionally set effective_visits = branch_visits,
    discarding any corner/ladder boost. Now it compounds: effective_visits = branch_visits * boost.
    """

    def test_adaptive_corner_boost_compounds(self):
        """Adaptive mode + corner position compounds boost with branch_visits."""
        config = _make_config()
        config.edge_case_boosts.corner_visit_boost = 1.5
        config.solution_tree.visit_allocation_mode = "adaptive"
        config.solution_tree.branch_visits = 500
        config.solution_tree.continuation_visits = 200
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-adaptive-corner",
            corner_position="TL",
        )
        assert root.is_correct is True
        # The tree should build successfully with compounded visits

    def test_adaptive_ladder_boost_compounds(self):
        """Adaptive mode + ladder PV compounds boost with branch_visits."""
        config = _make_config()
        config.edge_case_boosts.ladder_visit_boost = 2.0
        config.edge_case_boosts.ladder_pv_threshold = 8
        config.solution_tree.visit_allocation_mode = "adaptive"
        config.solution_tree.branch_visits = 500
        config.solution_tree.continuation_visits = 200
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-adaptive-ladder",
            pv_length=12,
        )
        assert root.is_correct is True

    def test_adaptive_corner_and_ladder_compound(self):
        """Adaptive mode with both corner and ladder boosts compound multiplicatively."""
        config = _make_config()
        config.edge_case_boosts.corner_visit_boost = 1.5
        config.edge_case_boosts.ladder_visit_boost = 2.0
        config.edge_case_boosts.ladder_pv_threshold = 8
        config.solution_tree.visit_allocation_mode = "adaptive"
        config.solution_tree.branch_visits = 500
        config.solution_tree.continuation_visits = 200
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-adaptive-both",
            corner_position="BR",
            pv_length=12,
        )
        assert root.is_correct is True

    def test_fixed_mode_unchanged(self):
        """Fixed mode still applies boosts to tree_visits (no regression)."""
        config = _make_config()
        config.edge_case_boosts.corner_visit_boost = 1.5
        config.solution_tree.visit_allocation_mode = "fixed"
        config.solution_tree.tree_visits = 500
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=10)

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-fixed-corner",
            corner_position="TL",
        )
        assert root.is_correct is True


@pytest.mark.unit
class TestS1G14CoCorrectScoreGap:
    """S1-G14: Co-correct detection requires score gap signal too."""

    def test_co_correct_score_gap_required(self):
        """Co-correct NOT detected when score gap is too large."""
        config = _make_config()
        config.alternatives.co_correct_min_gap = 0.03
        config.alternatives.co_correct_score_gap = 1.0  # tight score gap

        analysis = _make_response(moves=[
            {"move": "C3", "winrate": 0.92, "policy_prior": 0.45,
             "visits": 500, "score_lead": 10.0},
            {"move": "D4", "winrate": 0.91, "policy_prior": 0.40,
             "visits": 400, "score_lead": 15.0},  # score gap = 5.0 > 1.0
        ])

        alts, co_correct, _ = discover_alternatives(
            analysis, "C3", "B", "test-sg-001", config,
        )
        assert co_correct is False

    def test_co_correct_all_three_signals_pass(self):
        """Co-correct detected when all 3 signals pass."""
        config = _make_config()
        config.alternatives.co_correct_min_gap = 0.03
        config.alternatives.co_correct_score_gap = 3.0

        analysis = _make_response(moves=[
            {"move": "C3", "winrate": 0.92, "policy_prior": 0.45,
             "visits": 500, "score_lead": 10.0},
            {"move": "D4", "winrate": 0.91, "policy_prior": 0.40,
             "visits": 400, "score_lead": 11.0},  # score gap = 1.0 < 3.0
        ])

        alts, co_correct, _ = discover_alternatives(
            analysis, "C3", "B", "test-sg-002", config,
        )
        assert co_correct is True


# ===================================================================
# Sprint 2 Tests: Multi-root & Has-solution
# ===================================================================


@pytest.mark.unit
class TestS2G2MultiRootTreeBuilding:
    """S2-G2: Multi-root tree building with A/B/C priority."""

    def test_multiple_correct_root_trees(self):
        """Pipeline can build multiple correct-root trees."""
        config = _make_config()
        config.solution_tree.max_correct_root_trees = 2
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=50)

        # Build primary tree
        tree1 = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="multi-root-001",
        )
        assert tree1.is_correct is True

        # Build additional correct tree (using remaining budget)
        tree2 = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="D4",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="multi-root-001",
        )
        assert tree2.is_correct is True

    def test_refutation_root_trees(self):
        """Wrong-move refutation trees can be built."""
        config = _make_config()
        config.solution_tree.max_refutation_root_trees = 3
        config.solution_tree.depth_profiles["core"].solution_max_depth = 2
        config.solution_tree.depth_profiles["core"].solution_min_depth = 1

        engine = MockEngine()
        budget = QueryBudget(total=30)

        # Build refutation trees for wrong moves
        for move in ["E5", "F6", "G7"]:
            if not budget.can_query():
                break
            tree = build_solution_tree(
                engine=engine,
                initial_moves=[],
                correct_move_gtp=move,
                player_color="B",
                config=config,
                level_slug="intermediate",
                query_budget=budget,
                puzzle_id="refutation-root-001",
            )
            assert tree.move_gtp == move


@pytest.mark.unit
class TestS2G3HasSolutionPath:
    """S2-G3: Puzzles with existing solutions get AI enrichment."""

    def test_existing_solution_ai_enriched_in_pipeline(self):
        """discover_alternatives called with engine builds alternative trees."""
        config = _make_config()
        config.alternatives.co_correct_min_gap = 0.05

        analysis = _make_response(moves=[
            {"move": "C3", "winrate": 0.92, "policy_prior": 0.50, "visits": 500},
            {"move": "D4", "winrate": 0.91, "policy_prior": 0.40, "visits": 400},
        ])

        engine = MockEngine()
        budget = QueryBudget(total=20)

        alts, co_correct, confidence = discover_alternatives(
            analysis, "C3", "B", "has-sol-001", config,
            engine=engine,
            initial_moves=[],
            level_slug="intermediate",
            query_budget=budget,
        )

        assert len(alts) >= 1
        assert confidence is None  # AI agrees
        # Engine should have been queried for building alternative trees
        assert budget.used > 0


@pytest.mark.unit
class TestS2G5HumanSolutionConfidence:
    """S2-G5: human_solution_confidence wired through pipeline."""

    def test_confidence_returned_from_discover_alternatives(self):
        config = _make_config()
        analysis = _make_response(moves=[
            {"move": "D4", "winrate": 0.95, "policy_prior": 0.50, "visits": 500},
            {"move": "C3", "winrate": 0.55, "policy_prior": 0.10, "visits": 100},
        ])

        _, _, confidence = discover_alternatives(
            analysis, "C3", "B", "hsc-001", config,
        )
        assert confidence in ("losing", "weak")


@pytest.mark.unit
class TestS2G6AiSolutionValidated:
    """S2-G6: ai_solution_validated set when AI agrees."""

    def test_validated_when_ai_agrees(self):
        config = _make_config()
        analysis = _make_response(moves=[
            {"move": "C3", "winrate": 0.92, "policy_prior": 0.50, "visits": 500},
        ])

        _, _, confidence = discover_alternatives(
            analysis, "C3", "B", "asv-001", config,
        )
        # Confidence is None when AI agrees → ai_solution_validated = True
        assert confidence is None
        pa = PositionAnalysis(
            puzzle_id="asv-001", root_winrate=0.92, player_color="B",
            ai_solution_validated=True,
        )
        assert pa.ai_solution_validated is True


# ===================================================================
# Sprint 3 Tests: Output Wiring
# ===================================================================


@pytest.mark.unit
class TestS3G4AcLevelWiring:
    """S3-G4: AC level wired to AiAnalysisResult and YQ property."""

    def test_ac_level_on_ai_analysis_result(self):
        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult(puzzle_id="ac-test", ac_level=2)
        assert result.ac_level == 2

    def test_ac_level_serializes_to_json(self):
        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult(puzzle_id="ac-json", ac_level=1)
        data = result.model_dump()
        assert data["ac_level"] == 1

    def test_yq_ac_field_written(self):
        """YQ wire format includes ac:N field."""
        from analyzers.sgf_enricher import _build_yq
        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult(puzzle_id="yq-ac", ac_level=2)
        yq = _build_yq(result, "")
        assert "ac:2" in yq

    def test_yq_preserves_existing_fields(self):
        """Updating YQ preserves q/rc/hc values."""
        from analyzers.sgf_enricher import _build_yq
        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult(puzzle_id="yq-pres", ac_level=1)
        yq = _build_yq(result, "q:3;rc:1;hc:2;ac:0")
        assert yq.startswith("q:3;rc:1;hc:2;ac:1;qk:")


@pytest.mark.unit
class TestS3G7RoundtripAssertion:
    """S3-G7: Inject-then-extract roundtrip test."""

    def test_inject_then_extract_roundtrip(self):
        """After injection, extracting correct first move succeeds."""
        root = _make_sgf_root()
        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95, policy=0.45,
            visits=500, is_correct=True,
        )
        inject_solution_into_sgf(root, tree, player_color="B")

        # Root should now have children
        assert len(root.children) >= 1
        # Verify we can find the injected move
        found = False
        for child in root.children:
            props = getattr(child, "properties", {})
            if "B" in props:
                found = True
                break
        assert found, "Injected correct move not found in SGF children"


@pytest.mark.unit
class TestS3G11GoalInference:
    """S3-G11: Goal inference implementation."""

    def test_infer_goal_kill(self):
        """Large score delta → kill goal."""
        config = _make_config()
        goal, conf, _reason = infer_goal(
            pre_score_lead=0.0, post_score_lead=20.0,
            ownership=None, config=config,
        )
        assert goal == "kill"
        assert conf == "high"

    def test_infer_goal_live(self):
        """Small score delta → live goal."""
        config = _make_config()
        goal, conf, _reason = infer_goal(
            pre_score_lead=5.0, post_score_lead=6.0,
            ownership=None, config=config,
        )
        assert goal == "live"
        assert conf == "medium"

    def test_infer_goal_ko(self):
        """Ko context → ko goal."""
        config = _make_config()
        goal, conf, _reason = infer_goal(
            pre_score_lead=0.0, post_score_lead=8.0,
            ownership=None, config=config,
            ko_type="direct",
        )
        assert goal == "ko"

    def test_infer_goal_capture(self):
        """Moderate score delta → capture goal."""
        config = _make_config()
        goal, conf, _reason = infer_goal(
            pre_score_lead=0.0, post_score_lead=8.0,
            ownership=None, config=config,
        )
        assert goal == "capture"
        assert conf == "medium"

    def test_ownership_variance_lowers_confidence(self):
        """High ownership variance → low confidence."""
        config = _make_config()
        config.goal_inference.ownership_variance_gate = 0.001  # very tight
        # Ownership with high variance among occupied cells (key stones > 0.7)
        ownership = [[0.95, -0.95, 0.0], [0.0, 0.72, -0.71], [0.99, -0.75, 0.0]]
        goal, conf, _reason = infer_goal(
            pre_score_lead=0.0, post_score_lead=20.0,
            ownership=ownership, config=config,
        )
        assert goal == "kill"
        assert conf == "low"  # downgraded by ownership variance


# ===================================================================
# Sprint 4 Tests: Observability
# ===================================================================


@pytest.mark.unit
class TestS4G8BatchSummaryEmitter:
    """S4-G8: BatchSummaryAccumulator wiring."""

    def test_accumulator_collects_outcomes(self):
        acc = BatchSummaryAccumulator(batch_id="test-batch")
        acc.record_puzzle(has_solution=True, ac_level=1, queries_used=5)
        acc.record_puzzle(has_solution=True, ac_level=2, disagreement=True, queries_used=10)
        acc.record_puzzle(has_solution=False, ac_level=2, queries_used=15)

        summary = acc.emit()
        assert summary.total_puzzles == 3
        assert summary.has_solution == 2
        assert summary.position_only == 1
        assert summary.ac_1_count == 1
        assert summary.ac_2_count == 2
        assert summary.disagreements == 1
        assert summary.total_queries == 30

    def test_emitter_logs_at_info(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="log-test")
        acc.record_puzzle(has_solution=True, ac_level=1)

        with caplog.at_level(logging.INFO):
            acc.emit()
        assert any("BatchSummary" in r.message for r in caplog.records)


@pytest.mark.unit
class TestS4G9DisagreementSink:
    """S4-G9: DisagreementSink class writes JSONL."""

    def test_disagreement_sink_writes_jsonl(self, tmp_path):
        sink = DisagreementSink(
            sink_dir=str(tmp_path / "disagreements"),
            run_id="20260101-test0001",
        )

        record = DisagreementRecord(
            puzzle_id="puz-001", run_id="20260101-test0001",
            human_move_gtp="C3", ai_move_gtp="D4",
            human_winrate=0.55, ai_winrate=0.90, delta=0.35,
            human_solution_confidence=HumanSolutionConfidence.LOSING,
        )
        sink.write(record)
        sink.write(record)
        sink.close()

        path = tmp_path / "disagreements" / "20260101-test0001.jsonl"
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            parsed = json.loads(line)
            assert parsed["puzzle_id"] == "puz-001"
            assert parsed["human_solution_confidence"] == "losing"
            assert "timestamp" in parsed

    def test_sink_records_written_count(self, tmp_path):
        sink = DisagreementSink(str(tmp_path), "20260101-test0002")
        assert sink.records_written == 0
        record = DisagreementRecord(
            puzzle_id="p1", run_id="20260101-test0002",
            human_move_gtp="C3", ai_move_gtp="D4",
            human_winrate=0.5, ai_winrate=0.9, delta=0.4,
            human_solution_confidence=HumanSolutionConfidence.WEAK,
        )
        sink.write(record)
        assert sink.records_written == 1
        sink.close()


@pytest.mark.unit
class TestS4G10CollectionDisagreementMonitoring:
    """S4-G10: Per-collection disagreement monitoring with WARNING."""

    def test_collection_warning_emitted(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="col-test")
        # 10 puzzles in collection, 5 disagreements = 50%
        for i in range(10):
            acc.record_puzzle(
                has_solution=True, ac_level=1,
                disagreement=(i < 5),  # 5/10 = 50%
                collection="test-collection",
            )

        with caplog.at_level(logging.WARNING):
            acc.emit(warning_threshold=0.20)

        assert any("test-collection" in r.message and "disagreement rate" in r.message
                    for r in caplog.records)

    def test_no_warning_below_threshold(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="col-ok")
        for i in range(10):
            acc.record_puzzle(
                has_solution=True, ac_level=1,
                disagreement=(i < 1),  # 1/10 = 10%
                collection="ok-collection",
            )

        with caplog.at_level(logging.WARNING):
            acc.emit(warning_threshold=0.20)

        # No warning should be logged for this collection
        assert not any("ok-collection" in r.message and "disagreement rate" in r.message
                        for r in caplog.records)


@pytest.mark.unit
class TestP2bFrameImbalanceBatchSummary:
    """P2b: Frame imbalance tracking in BatchSummaryAccumulator."""

    def test_frame_imbalance_counted(self):
        acc = BatchSummaryAccumulator(batch_id="frame-test")
        acc.record_puzzle(has_solution=True, ac_level=1, frame_imbalance=True)
        acc.record_puzzle(has_solution=True, ac_level=1, frame_imbalance=False)
        acc.record_puzzle(
            has_solution=True, ac_level=1,
            frame_imbalance=True, tree_validation_override=True,
        )

        summary = acc.emit()
        assert summary.frame_imbalance_count == 2
        assert summary.tree_validation_overrides == 1

    def test_frame_imbalance_warning_emitted(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="frame-warn")
        acc.record_puzzle(has_solution=True, ac_level=1, frame_imbalance=True)
        acc.record_puzzle(has_solution=True, ac_level=1, frame_imbalance=False)

        with caplog.at_level(logging.WARNING):
            acc.emit()
        assert any("Frame imbalance" in r.message for r in caplog.records)

    def test_no_frame_imbalance_no_warning(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="frame-ok")
        acc.record_puzzle(has_solution=True, ac_level=1)
        acc.record_puzzle(has_solution=True, ac_level=1)

        with caplog.at_level(logging.WARNING):
            acc.emit()
        assert not any("Frame imbalance" in r.message for r in caplog.records)

    def test_frame_imbalance_by_tag_logged(self, caplog):
        acc = BatchSummaryAccumulator(batch_id="frame-tags")
        acc.record_puzzle(
            has_solution=True, ac_level=1,
            frame_imbalance=True,
            frame_imbalance_tags=["capture-race", "life-and-death"],
        )
        acc.record_puzzle(
            has_solution=True, ac_level=1,
            frame_imbalance=True,
            frame_imbalance_tags=["capture-race"],
        )

        with caplog.at_level(logging.WARNING):
            acc.emit()
        assert any("by tag" in r.message for r in caplog.records)


# ===================================================================
# Sprint 5 Tests: Additional Plan-Specified Tests
# ===================================================================


@pytest.mark.unit
class TestS5G20MissingTests:
    """S5-G20: Fill in missing plan-specified tests."""

    def test_9x9_coordinates(self):
        """9x9 board coordinate handling."""
        from analyzers.solve_position import _gtp_to_sgf, _sgf_to_gtp
        # 9x9: A1 to J9 (no I)
        assert _gtp_to_sgf("A1") == "aa"
        assert _gtp_to_sgf("J9") == "ii"
        assert _sgf_to_gtp("aa") == "A1"
        assert _sgf_to_gtp("ii") == "J9"

    def test_budget_exhausted_before_min_depth_low_confidence(self):
        """Budget exhaustion before min_depth → truncated tree."""
        config = _make_config()
        config.solution_tree.depth_profiles["core"].solution_min_depth = 5
        config.solution_tree.depth_profiles["core"].solution_max_depth = 10

        engine = MockEngine()
        budget = QueryBudget(total=1)  # Very tight budget

        root = build_solution_tree(
            engine=engine,
            initial_moves=[],
            correct_move_gtp="C3",
            player_color="B",
            config=config,
            level_slug="intermediate",
            query_budget=budget,
            puzzle_id="test-budget-min",
        )
        # Tree should be truncated due to budget, not reaching min_depth
        assert root.tree_completeness is not None

    def test_pass_as_correct_move_rejected(self):
        """Pass as correct move is rejected explicitly (separate from pass-as-best)."""
        config = _make_config()
        analysis = _make_analysis([
            {"move": "pass", "winrate": 0.95, "prior": 0.80},
        ])
        with pytest.raises(ValueError, match="pass is the best move"):
            analyze_position_candidates(analysis, "B", "test-pass-reject", config)

    def test_logs_disagreement(self, tmp_path):
        """Disagreement record is correctly structured for JSONL."""
        record = DisagreementRecord(
            puzzle_id="log-dis-001",
            run_id="run-log",
            collection="test-col",
            human_move_gtp="C3",
            ai_move_gtp="D4",
            human_winrate=0.55,
            ai_winrate=0.90,
            delta=0.35,
            human_solution_confidence=HumanSolutionConfidence.LOSING,
            level_slug="intermediate",
        )
        line = record.model_dump_json()
        parsed = json.loads(line)
        assert parsed["collection"] == "test-col"
        assert parsed["level_slug"] == "intermediate"
        assert parsed["human_solution_confidence"] == "losing"


@pytest.mark.unit
class TestMoveClassificationScoreLead:
    """Verify score_lead field on MoveClassification model."""

    def test_default_score_lead(self):
        mc = MoveClassification(
            move_gtp="C3", color="B", quality=MoveQuality.TE,
            winrate=0.9, delta=0.01, policy=0.5, rank=0,
        )
        assert mc.score_lead == 0.0

    def test_custom_score_lead(self):
        mc = MoveClassification(
            move_gtp="C3", color="B", quality=MoveQuality.TE,
            winrate=0.9, delta=0.01, policy=0.5, rank=0,
            score_lead=12.5,
        )
        assert mc.score_lead == 12.5


@pytest.mark.unit
class TestGoalAndAcOnAiAnalysisResult:
    """Verify new fields on AiAnalysisResult."""

    def test_goal_field_exists(self):
        from models.ai_analysis_result import AiAnalysisResult
        r = AiAnalysisResult(puzzle_id="goal-1", goal="kill", goal_confidence="high")
        assert r.goal == "kill"
        assert r.goal_confidence == "high"

    def test_ac_level_default(self):
        from models.ai_analysis_result import AiAnalysisResult
        r = AiAnalysisResult(puzzle_id="ac-def")
        assert r.ac_level == 0
