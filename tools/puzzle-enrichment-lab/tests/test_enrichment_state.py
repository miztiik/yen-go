"""TDD tests for EnrichmentRunState dataclass (T9).

Tests: default values, field mutation, ai_solve_failed fall-through (MH-5),
notify_fn attachment.
"""

from __future__ import annotations

from pathlib import Path

_LAB_DIR = Path(__file__).resolve().parents[1]

from models.enrichment_state import EnrichmentRunState


class TestDefaults:
    """All fields should have safe defaults (MH-3)."""

    def test_all_flags_false_by_default(self):
        state = EnrichmentRunState()
        assert state.has_solution_path is False
        assert state.position_only_path is False
        assert state.ai_solve_failed is False
        assert state.budget_exhausted is False
        assert state.co_correct_detected is False
        assert state.ai_solution_validated is False

    def test_numeric_defaults(self):
        state = EnrichmentRunState()
        assert state.queries_used == 0

    def test_optional_defaults_are_none(self):
        state = EnrichmentRunState()
        assert state.solution_tree_completeness is None
        assert state.human_solution_confidence is None
        assert state.notify_fn is None
        assert state.correct_move_gtp is None
        assert state.correct_move_sgf is None
        assert state.solution_moves is None


class TestMutation:
    """Fields should be mutable (dataclass, not frozen)."""

    def test_set_has_solution_path(self):
        state = EnrichmentRunState()
        state.has_solution_path = True
        assert state.has_solution_path is True

    def test_set_queries_used(self):
        state = EnrichmentRunState()
        state.queries_used = 42
        assert state.queries_used == 42

    def test_set_human_solution_confidence(self):
        state = EnrichmentRunState()
        state.human_solution_confidence = "high"
        assert state.human_solution_confidence == "high"

    def test_set_solution_tree_completeness(self):
        state = EnrichmentRunState()
        state.solution_tree_completeness = {"depth": 3}
        assert state.solution_tree_completeness == {"depth": 3}

    def test_set_correct_move_gtp(self):
        state = EnrichmentRunState()
        state.correct_move_gtp = "C3"
        assert state.correct_move_gtp == "C3"

    def test_set_correct_move_sgf(self):
        state = EnrichmentRunState()
        state.correct_move_sgf = "cc"
        assert state.correct_move_sgf == "cc"

    def test_set_solution_moves(self):
        state = EnrichmentRunState()
        state.solution_moves = ["C3", "D4"]
        assert state.solution_moves == ["C3", "D4"]


class TestAiSolveFailedFallThrough:
    """MH-5: ai_solve_failed must allow state to fall through to
    subsequent pipeline stages (not early-return)."""

    def test_ai_solve_failed_does_not_block_other_fields(self):
        state = EnrichmentRunState()
        state.ai_solve_failed = True
        # Can still set downstream fields after failure
        state.has_solution_path = True
        state.queries_used = 10
        assert state.ai_solve_failed is True
        assert state.has_solution_path is True
        assert state.queries_used == 10


class TestNotifyFn:
    """notify_fn should be attachable and callable."""

    def test_attach_notify_fn(self):
        async def dummy_notify(stage: str, payload: dict | None = None) -> None:
            pass

        state = EnrichmentRunState(notify_fn=dummy_notify)
        assert state.notify_fn is dummy_notify

    def test_notify_fn_default_none(self):
        state = EnrichmentRunState()
        assert state.notify_fn is None


class TestIsDataclass:
    """MH-3: Must be a @dataclass."""

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(EnrichmentRunState)

    def test_is_not_frozen(self):
        import dataclasses
        dataclasses.fields(EnrichmentRunState)  # verify dataclass is valid
        # Verify we can mutate (not frozen)
        state = EnrichmentRunState()
        state.has_solution_path = True
        assert state.has_solution_path is True
