"""Tests for AI-Solve data models (Phase 2, ai-solve-enrichment-plan-v3).

Gate 2 criteria:
- All models instantiate with defaults
- All models serialize to/from JSON
- QueryBudget.can_query() returns False when exhausted
- TreeCompletenessMetrics.is_complete() works correctly
- No imports from backend/ (tools isolation boundary)
"""

import json
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent


@pytest.mark.unit
class TestQueryBudget:
    """QueryBudget is required, tracks queries, and rejects overspend."""

    def test_instantiate_with_total(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=50)
        assert qb.total == 50
        assert qb.used == 0
        assert qb.remaining == 50

    def test_can_query_when_budget_available(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=5)
        assert qb.can_query() is True

    def test_can_query_returns_false_when_exhausted(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=3, used=3)
        assert qb.can_query() is False

    def test_consume_decrements_remaining(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=10)
        qb.consume(3)
        assert qb.used == 3
        assert qb.remaining == 7

    def test_consume_raises_on_overspend(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=5, used=4)
        with pytest.raises(ValueError, match="Cannot consume"):
            qb.consume(2)

    def test_consume_at_exact_boundary(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=5, used=4)
        qb.consume(1)
        assert qb.remaining == 0
        assert qb.can_query() is False

    def test_repr(self):
        from models.solve_result import QueryBudget
        qb = QueryBudget(total=50, used=12)
        assert "12/50" in repr(qb)


@pytest.mark.unit
class TestTreeCompletenessMetrics:
    """TreeCompletenessMetrics tracks branch completion ratio."""

    def test_defaults(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics()
        assert m.completed_branches == 0
        assert m.total_attempted_branches == 0

    def test_is_complete_when_all_branches_done(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics(completed_branches=5, total_attempted_branches=5)
        assert m.is_complete() is True

    def test_is_complete_false_when_truncated(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics(completed_branches=3, total_attempted_branches=5)
        assert m.is_complete() is False

    def test_is_complete_true_when_zero_attempted(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics()
        assert m.is_complete() is True

    def test_completion_ratio(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics(completed_branches=3, total_attempted_branches=4)
        assert m.completion_ratio == pytest.approx(0.75)

    def test_completion_ratio_zero_attempted(self):
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics()
        assert m.completion_ratio == pytest.approx(1.0)

    def test_serialize_round_trip(self):
        from models.solve_result import TreeCompletenessMetrics
        original = TreeCompletenessMetrics(completed_branches=7, total_attempted_branches=10)
        data = original.model_dump()
        restored = TreeCompletenessMetrics(**data)
        assert restored == original


@pytest.mark.unit
class TestMoveClassification:
    """MoveClassification with TE/BM/BM_HO/neutral."""

    def test_te_classification(self):
        from models.solve_result import MoveClassification, MoveQuality
        mc = MoveClassification(
            move_gtp="C3", color="B", quality=MoveQuality.TE,
            winrate=0.95, delta=0.03, policy=0.45, rank=0,
        )
        assert mc.quality == MoveQuality.TE
        assert mc.move_gtp == "C3"

    def test_bm_ho_classification(self):
        from models.solve_result import MoveClassification, MoveQuality
        mc = MoveClassification(
            move_gtp="D4", color="B", quality=MoveQuality.BM_HO,
            winrate=0.15, delta=-0.35, policy=0.20, rank=3,
        )
        assert mc.quality == MoveQuality.BM_HO

    def test_neutral_classification(self):
        from models.solve_result import MoveClassification, MoveQuality
        mc = MoveClassification(
            move_gtp="E5", color="W", quality=MoveQuality.NEUTRAL,
            winrate=0.50, delta=-0.08, policy=0.10, rank=5,
        )
        assert mc.quality == MoveQuality.NEUTRAL

    def test_serialize_round_trip(self):
        from models.solve_result import MoveClassification, MoveQuality
        original = MoveClassification(
            move_gtp="C3", color="B", quality=MoveQuality.TE,
            winrate=0.95, delta=0.03, policy=0.45, rank=0,
        )
        json_str = original.model_dump_json()
        restored = MoveClassification.model_validate_json(json_str)
        assert restored == original


@pytest.mark.unit
class TestSolutionNode:
    """SolutionNode: recursive tree with completeness at root."""

    def test_leaf_node(self):
        from models.solve_result import SolutionNode
        node = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95,
            policy=0.45, visits=500, is_correct=True,
        )
        assert node.children == []
        assert node.truncated is False
        assert node.tree_completeness is None

    def test_branching_tree(self):
        from models.solve_result import SolutionNode, TreeCompletenessMetrics
        child1 = SolutionNode(move_gtp="D4", color="W", winrate=0.10, policy=0.3, visits=200)
        child2 = SolutionNode(move_gtp="E5", color="W", winrate=0.08, policy=0.2, visits=200)
        root = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95,
            policy=0.45, visits=500, is_correct=True,
            children=[child1, child2],
            tree_completeness=TreeCompletenessMetrics(
                completed_branches=2, total_attempted_branches=2,
            ),
        )
        assert len(root.children) == 2
        assert root.tree_completeness.is_complete()

    def test_truncated_branch(self):
        from models.solve_result import SolutionNode
        node = SolutionNode(
            move_gtp="C3", color="B", winrate=0.60,
            policy=0.10, visits=50, truncated=True,
        )
        assert node.truncated is True

    def test_serialize_round_trip(self):
        from models.solve_result import SolutionNode, TreeCompletenessMetrics
        child = SolutionNode(move_gtp="D4", color="W", winrate=0.10, policy=0.3, visits=200)
        root = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95,
            policy=0.45, visits=500, is_correct=True,
            children=[child],
            tree_completeness=TreeCompletenessMetrics(
                completed_branches=1, total_attempted_branches=1,
            ),
        )
        json_str = root.model_dump_json()
        restored = SolutionNode.model_validate_json(json_str)
        assert restored.move_gtp == root.move_gtp
        assert len(restored.children) == 1
        assert restored.tree_completeness.is_complete()


@pytest.mark.unit
class TestSolvedMove:
    """SolvedMove: correct move with solution tree."""

    def test_instantiate(self):
        from models.solve_result import SolvedMove
        sm = SolvedMove(
            move_gtp="C3", color="B", winrate=0.95,
            confidence="high",
        )
        assert sm.move_gtp == "C3"
        assert sm.confidence == "high"
        assert sm.solution_tree is None

    def test_with_solution_tree(self):
        from models.solve_result import SolutionNode, SolvedMove
        tree = SolutionNode(
            move_gtp="C3", color="B", winrate=0.95,
            policy=0.45, visits=500, is_correct=True,
        )
        sm = SolvedMove(
            move_gtp="C3", color="B", winrate=0.95,
            confidence="high", solution_tree=tree,
        )
        assert sm.solution_tree is not None
        assert sm.solution_tree.is_correct is True


@pytest.mark.unit
class TestPositionAnalysis:
    """PositionAnalysis: complete analysis result."""

    def test_defaults(self):
        from models.solve_result import AiCorrectnessLevel, PositionAnalysis
        pa = PositionAnalysis(
            puzzle_id="test-001", root_winrate=0.50, player_color="B",
        )
        assert pa.co_correct_detected is False
        assert pa.ladder_suspected is False
        assert pa.ai_solution_validated is False
        assert pa.human_solution_confidence is None
        assert pa.ac_level == AiCorrectnessLevel.UNTOUCHED
        assert pa.queries_used == 0

    def test_with_classifications(self):
        from models.solve_result import (
            MoveClassification,
            MoveQuality,
            PositionAnalysis,
        )
        correct = MoveClassification(
            move_gtp="C3", color="B", quality=MoveQuality.TE,
            winrate=0.95, delta=0.03, policy=0.45, rank=0,
        )
        wrong = MoveClassification(
            move_gtp="D4", color="B", quality=MoveQuality.BM,
            winrate=0.30, delta=-0.20, policy=0.15, rank=3,
        )
        pa = PositionAnalysis(
            puzzle_id="test-002", root_winrate=0.50, player_color="B",
            correct_moves=[correct], wrong_moves=[wrong],
            all_classifications=[correct, wrong],
        )
        assert len(pa.correct_moves) == 1
        assert len(pa.wrong_moves) == 1

    def test_serialize_round_trip(self):
        from models.solve_result import AiCorrectnessLevel, PositionAnalysis
        pa = PositionAnalysis(
            puzzle_id="test-003", root_winrate=0.85, player_color="W",
            co_correct_detected=True, ac_level=AiCorrectnessLevel.AI_SOLVED,
        )
        json_str = pa.model_dump_json()
        restored = PositionAnalysis.model_validate_json(json_str)
        assert restored.puzzle_id == pa.puzzle_id
        assert restored.co_correct_detected is True
        assert restored.ac_level == AiCorrectnessLevel.AI_SOLVED


@pytest.mark.unit
class TestBatchSummary:
    """BatchSummary: batch observability aggregate."""

    def test_instantiate(self):
        from models.solve_result import BatchSummary
        bs = BatchSummary(batch_id="run-001")
        assert bs.total_puzzles == 0
        assert bs.disagreement_rate == 0.0

    def test_with_data(self):
        from models.solve_result import BatchSummary
        bs = BatchSummary(
            batch_id="run-002",
            total_puzzles=100, position_only=30, has_solution=70,
            ac_1_count=60, ac_2_count=30, disagreements=5,
            total_queries=1500, collection="cho-elementary",
            disagreement_rate=5.0 / 70,
        )
        assert bs.total_puzzles == 100
        assert bs.disagreement_rate == pytest.approx(5.0 / 70)

    def test_serialize_round_trip(self):
        from models.solve_result import BatchSummary
        bs = BatchSummary(
            batch_id="run-003", total_puzzles=50, ac_2_count=20,
        )
        json_str = bs.model_dump_json()
        restored = BatchSummary.model_validate_json(json_str)
        assert restored == bs


@pytest.mark.unit
class TestDisagreementRecord:
    """DisagreementRecord: structured JSONL record."""

    def test_instantiate(self):
        from models.solve_result import DisagreementRecord, HumanSolutionConfidence
        dr = DisagreementRecord(
            puzzle_id="puz-001", run_id="run-001",
            human_move_gtp="C3", ai_move_gtp="D4",
            human_winrate=0.40, ai_winrate=0.95, delta=0.55,
            human_solution_confidence=HumanSolutionConfidence.LOSING,
        )
        assert dr.puzzle_id == "puz-001"
        assert dr.delta == pytest.approx(0.55)
        assert dr.human_solution_confidence == HumanSolutionConfidence.LOSING

    def test_serialize_to_jsonl_line(self):
        from models.solve_result import DisagreementRecord, HumanSolutionConfidence
        dr = DisagreementRecord(
            puzzle_id="puz-002", run_id="run-002",
            human_move_gtp="E5", ai_move_gtp="F6",
            human_winrate=0.70, ai_winrate=0.90, delta=0.20,
            human_solution_confidence=HumanSolutionConfidence.WEAK,
            collection="cho-intermediate",
        )
        line = dr.model_dump_json()
        # Must be valid JSON (single line)
        parsed = json.loads(line)
        assert parsed["puzzle_id"] == "puz-002"
        assert parsed["human_solution_confidence"] == "weak"

    def test_serialize_round_trip(self):
        from models.solve_result import DisagreementRecord, HumanSolutionConfidence
        dr = DisagreementRecord(
            puzzle_id="puz-003", run_id="run-003",
            human_move_gtp="C3", ai_move_gtp="D4",
            human_winrate=0.80, ai_winrate=0.85, delta=0.05,
            human_solution_confidence=HumanSolutionConfidence.STRONG,
        )
        json_str = dr.model_dump_json()
        restored = DisagreementRecord.model_validate_json(json_str)
        assert restored == dr


@pytest.mark.unit
class TestEnums:
    """Enum values are correct."""

    def test_move_quality_values(self):
        from models.solve_result import MoveQuality
        assert MoveQuality.TE.value == "te"
        assert MoveQuality.BM.value == "bm"
        assert MoveQuality.BM_HO.value == "bm_ho"
        assert MoveQuality.NEUTRAL.value == "neutral"

    def test_ai_correctness_levels(self):
        from models.solve_result import AiCorrectnessLevel
        assert AiCorrectnessLevel.UNTOUCHED == 0
        assert AiCorrectnessLevel.ENRICHED == 1
        assert AiCorrectnessLevel.AI_SOLVED == 2
        assert AiCorrectnessLevel.VERIFIED == 3

    def test_human_solution_confidence_values(self):
        from models.solve_result import HumanSolutionConfidence
        assert HumanSolutionConfidence.STRONG.value == "strong"
        assert HumanSolutionConfidence.WEAK.value == "weak"
        assert HumanSolutionConfidence.LOSING.value == "losing"


@pytest.mark.unit
class TestNoBackendImports:
    """Models must not import from backend/ (tools isolation boundary)."""

    def test_no_backend_imports_in_solve_result(self):
        source = (_LAB / "models" / "solve_result.py").read_text()
        # Check actual import lines, not docstrings
        import_lines = [
            line.strip() for line in source.splitlines()
            if (line.strip().startswith("from ") or line.strip().startswith("import "))
            and not line.strip().startswith("#")
        ]
        for line in import_lines:
            assert "backend" not in line, f"Backend import found: {line}"


@pytest.mark.unit
class TestKMCompletenessMetrics:
    """T016: New KM counter fields in TreeCompletenessMetrics."""

    def test_completeness_metrics_new_counters_default_zero(self):
        """T016: All new KM counters initialize to 0."""
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics()
        assert m.simulation_hits == 0
        assert m.simulation_misses == 0
        assert m.transposition_hits == 0
        assert m.forced_move_count == 0
        assert m.max_resolved_depth == 0

    def test_completeness_metrics_new_counters_settable(self):
        """KM counters can be set and incremented."""
        from models.solve_result import TreeCompletenessMetrics
        m = TreeCompletenessMetrics(
            simulation_hits=5,
            simulation_misses=2,
            transposition_hits=10,
            forced_move_count=3,
            max_resolved_depth=8,
        )
        assert m.simulation_hits == 5
        assert m.simulation_misses == 2
        assert m.transposition_hits == 10
        assert m.forced_move_count == 3
        assert m.max_resolved_depth == 8
