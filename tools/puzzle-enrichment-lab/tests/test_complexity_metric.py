"""Tests for the complexity metric (T50/T51) — 5th difficulty component.

Covers:
- Complexity computation with uniform policy (all equal) → moderate complexity
- Complexity with one dominant move → low complexity
- Complexity weight is included in composite formula
- Weights still sum to 100 after rebalancing
"""

from __future__ import annotations

import pytest
from analyzers.estimate_difficulty import _compute_complexity, compute_per_move_accuracy
from config import clear_cache, load_enrichment_config
from config.difficulty import DifficultyWeights
from models.refutation_result import Refutation, RefutationResult


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Ensure each test gets fresh config."""
    clear_cache()
    yield
    clear_cache()


def _make_refutation(
    wrong_move: str = "cd",
    policy: float = 0.1,
    winrate_delta: float = -0.3,
    score_delta: float = -10.0,
) -> Refutation:
    """Create a Refutation with specified signals."""
    return Refutation(
        wrong_move=wrong_move,
        wrong_move_policy=policy,
        winrate_delta=winrate_delta,
        score_delta=score_delta,
        refutation_sequence=[wrong_move, "dd"],
    )


def _make_refutation_result(refutations: list[Refutation]) -> RefutationResult:
    """Wrap refutations in a RefutationResult."""
    return RefutationResult(refutations=refutations)


# ── T51-1: Weights sum to 100 ──────────────────────────────────────


class TestDifficultyWeightsSum:
    def test_default_weights_sum_to_100(self):
        """Default DifficultyWeights must sum to 100."""
        w = DifficultyWeights()
        total = w.policy_rank + w.visits_to_solve + w.trap_density + w.structural + w.complexity
        assert abs(total - 100.0) < 0.01

    def test_config_weights_sum_to_100(self):
        """Loaded config weights must sum to 100."""
        cfg = load_enrichment_config()
        w = cfg.difficulty.weights
        total = w.policy_rank + w.visits_to_solve + w.trap_density + w.structural + w.complexity
        assert abs(total - 100.0) < 0.01

    def test_invalid_weights_rejected(self):
        """Weights that don't sum to 100 should raise."""
        with pytest.raises(ValueError, match="sum to 100"):
            DifficultyWeights(
                policy_rank=10.0,
                visits_to_solve=10.0,
                trap_density=10.0,
                structural=10.0,
                complexity=10.0,
            )

    def test_complexity_weight_present(self):
        """Complexity weight field must exist on DifficultyWeights."""
        w = DifficultyWeights()
        assert hasattr(w, "complexity")
        assert w.complexity == 15.0


# ── T51-2: Complexity computation ───────────────────────────────────


class TestComplexityComputation:
    def test_no_refutations_returns_zero(self):
        """Empty refutation list → complexity = 0."""
        result = _make_refutation_result([])
        assert _compute_complexity(result) == 0.0

    def test_uniform_policy_moderate_complexity(self):
        """All refutations with equal policy and similar loss → moderate complexity."""
        refs = [
            _make_refutation("cd", policy=0.1, score_delta=-15.0),
            _make_refutation("de", policy=0.1, score_delta=-15.0),
            _make_refutation("ef", policy=0.1, score_delta=-15.0),
        ]
        result = _make_refutation_result(refs)
        c = _compute_complexity(result)
        # All have same policy/loss, so complexity = min(15/30, 1.0) = 0.5
        assert 0.4 < c < 0.6

    def test_one_dominant_move_low_complexity(self):
        """One refutation with high policy, small loss → low complexity."""
        refs = [
            _make_refutation("cd", policy=0.8, score_delta=-2.0),
        ]
        result = _make_refutation_result(refs)
        c = _compute_complexity(result)
        # normalized_loss = min(2/30, 1.0) ≈ 0.067
        assert c < 0.1

    def test_high_loss_caps_at_one(self):
        """Score losses beyond cap are capped at 1.0 in normalization."""
        refs = [
            _make_refutation("cd", policy=0.5, score_delta=-100.0),
        ]
        result = _make_refutation_result(refs)
        c = _compute_complexity(result)
        # normalized_loss = min(100/30, 1.0) = 1.0
        assert abs(c - 1.0) < 0.01

    def test_zero_prior_returns_zero(self):
        """Refutations with zero prior → complexity 0 (no weight)."""
        refs = [
            _make_refutation("cd", policy=0.0, score_delta=-15.0),
        ]
        result = _make_refutation_result(refs)
        assert _compute_complexity(result) == 0.0

    def test_winrate_fallback_when_no_score_delta(self):
        """Falls back to |winrate_delta| when score_delta ≈ 0."""
        refs = [
            _make_refutation("cd", policy=0.2, score_delta=0.0, winrate_delta=-0.4),
        ]
        result = _make_refutation_result(refs)
        c = _compute_complexity(result)
        assert abs(c - 0.4) < 0.01


# ── T61: Per-move accuracy ─────────────────────────────────────────


class TestPerMoveAccuracy:
    def test_no_refutations_returns_none(self):
        """No refutations → None."""
        result = _make_refutation_result([])
        assert compute_per_move_accuracy(result) is None

    def test_accuracy_in_valid_range(self):
        """Per-move accuracy should be in (0, 100]."""
        refs = [
            _make_refutation("cd", policy=0.2, score_delta=-15.0),
        ]
        result = _make_refutation_result(refs)
        acc = compute_per_move_accuracy(result)
        assert acc is not None
        assert 0.0 < acc <= 100.0

    def test_high_loss_low_accuracy(self):
        """High complexity → low accuracy."""
        refs = [
            _make_refutation("cd", policy=0.5, score_delta=-100.0),
        ]
        result = _make_refutation_result(refs)
        acc = compute_per_move_accuracy(result)
        assert acc is not None
        # complexity ≈ 1.0 → accuracy = 100 * 0.75^1.0 = 75
        assert 70 < acc < 80


# --- Migrated from test_sprint2_fixes.py ---


@pytest.mark.unit
class TestStoneGtpCoordAudit:
    """G3: Confirm Stone.gtp_coord property has no external callers
    and that gtp_coord_for() is the correct alternative.
    """

    def test_gtp_coord_for_9x9(self):
        """Stone.gtp_coord_for(9) produces correct coordinates."""
        from models.position import Color, Stone
        # y=0 = top row, so row = board_size - 0 = 9 → A9
        stone = Stone(color=Color.BLACK, x=0, y=0)
        assert stone.gtp_coord_for(9) == "A9"

    def test_gtp_coord_for_9x9_bottom(self):
        """Stone at bottom of 9×9: x=0, y=8 → A1."""
        from models.position import Color, Stone
        # y=8 (bottom) → row = 9 - 8 = 1
        stone = Stone(color=Color.BLACK, x=0, y=8)
        assert stone.gtp_coord_for(9) == "A1"

    def test_gtp_coord_for_13x13(self):
        """Stone.gtp_coord_for(13) at center-ish."""
        from models.position import Color, Stone
        # x=6, y=6 → col G, row = 13 - 6 = 7 → G7
        stone = Stone(color=Color.BLACK, x=6, y=6)
        assert stone.gtp_coord_for(13) == "G7"

    def test_gtp_coord_defaults_to_19(self):
        """Stone.gtp_coord (property) assumes 19×19."""
        from models.position import Color, Stone
        # y=0 = top row → row = 19 for 19×19
        stone = Stone(color=Color.BLACK, x=0, y=0)
        assert stone.gtp_coord == "A19"
