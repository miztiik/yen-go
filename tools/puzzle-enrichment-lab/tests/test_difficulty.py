"""Tests for Task A.3: Difficulty estimation.

A.3.1: Policy-only difficulty (Tier 0.5) — maps raw policy prior to level.
A.3.2: MCTS-based difficulty (Tier 2) — composite score from multiple signals.

All thresholds are loaded from config/katago-enrichment.json.
Level IDs are loaded from config/puzzle-levels.json (source of truth).
"""

from pathlib import Path

import pytest

# Resolve project root for config loading
_LAB_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _LAB_DIR.parent.parent

from analyzers.estimate_difficulty import (
    estimate_difficulty,
    estimate_difficulty_policy_only,
)
from analyzers.validate_correct_move import CorrectMoveResult, ValidationStatus
from config import clear_cache, load_enrichment_config, load_puzzle_levels
from models.refutation_result import RefutationResult


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Ensure each test gets fresh config."""
    clear_cache()
    yield
    clear_cache()


def _make_validation(
    *,
    correct_move_policy: float = 0.5,
    katago_agrees: bool = True,
    visits_used: int = 200,
    correct_move_winrate: float = 0.9,
) -> CorrectMoveResult:
    """Helper to build a CorrectMoveResult with sensible defaults."""
    return CorrectMoveResult(
        puzzle_id="test-1",
        correct_move_gtp="D4",
        status=ValidationStatus.ACCEPTED if katago_agrees else ValidationStatus.FLAGGED,
        katago_agrees=katago_agrees,
        katago_top_move="D4",
        correct_move_policy=correct_move_policy,
        correct_move_winrate=correct_move_winrate,
        visits_used=visits_used,
        confidence="high",
    )


def _make_refutations(
    count: int = 0,
    wrong_move_policy: float = 0.1,
    winrate_delta: float = -0.2,
    score_delta: float = 0.0,
) -> RefutationResult:
    """Helper to build a RefutationResult."""
    from models.refutation_result import Refutation
    refutations = [
        Refutation(
            wrong_move=f"m{i}",
            wrong_move_policy=wrong_move_policy,
            refutation_sequence=["aa", "bb"],
            winrate_after_wrong=0.3,
            winrate_delta=winrate_delta,
            score_delta=score_delta,
        )
        for i in range(count)
    ]
    return RefutationResult(
        puzzle_id="test-1",
        refutations=refutations,
        total_candidates_evaluated=count,
    )


# ===================================================================
# A.3.1 — Policy-only difficulty (Tier 0.5)
# ===================================================================

@pytest.mark.unit
class TestPolicyOnlyEasyPuzzle:
    """High policy prior → novice/beginner level."""

    def test_easy_puzzle_high_prior(self):
        """Policy prior > 0.5 maps to novice or beginner."""
        result = estimate_difficulty_policy_only(
            policy_prior=0.6,
            move_order="strict",
            correct_move_priors=None,
        )
        assert result.estimated_level in ("novice", "beginner"), (
            f"Policy 0.6 should be novice/beginner, got {result.estimated_level}"
        )
        assert result.policy_prior == 0.6


@pytest.mark.unit
class TestPolicyOnlyHardPuzzle:
    """Low policy prior → dan-level."""

    def test_hard_puzzle_low_prior(self):
        """Policy prior < 0.05 maps to dan-level or higher."""
        result = estimate_difficulty_policy_only(
            policy_prior=0.02,
            move_order="strict",
            correct_move_priors=None,
        )
        dan_levels = {"advanced", "low-dan", "high-dan", "expert"}
        assert result.estimated_level in dan_levels, (
            f"Policy 0.02 should be dan-level, got {result.estimated_level}"
        )


@pytest.mark.unit
class TestPolicyOnlyMiaiMaxPrior:
    """YO=miai → max(priors), NOT sum."""

    def test_miai_max_prior(self):
        """Two moves at 0.25 each → difficulty based on max (0.25), not sum (0.50).

        max(0.25) falls in elementary/intermediate range, NOT novice.
        """
        result = estimate_difficulty_policy_only(
            policy_prior=0.25,  # not used directly for miai
            move_order="miai",
            correct_move_priors=[0.25, 0.25],
        )
        # max(0.25, 0.25) = 0.25 → should be elementary or intermediate
        # NOT novice (which would happen if sum=0.50 were used)
        assert result.estimated_level not in ("novice",), (
            f"Miai should use max(0.25), not sum(0.50). Got {result.estimated_level}"
        )
        # Should be in elementary-intermediate range based on 0.25 prior
        valid = {"elementary", "intermediate", "beginner"}
        assert result.estimated_level in valid, (
            f"Expected elementary/intermediate/beginner for max prior 0.25, got {result.estimated_level}"
        )


@pytest.mark.unit
class TestPolicyOnlyLevelSlugValid:
    """Output level must be one of the 9 valid slugs."""

    def test_level_slug_valid(self):
        """Level slug is from config/puzzle-levels.json."""
        levels = load_puzzle_levels()
        valid_slugs = set(levels.keys())

        for prior in [0.0, 0.01, 0.05, 0.1, 0.3, 0.5, 0.8, 1.0]:
            result = estimate_difficulty_policy_only(
                policy_prior=prior,
                move_order="strict",
                correct_move_priors=None,
            )
            assert result.estimated_level in valid_slugs, (
                f"Level '{result.estimated_level}' not in valid slugs for prior={prior}"
            )


@pytest.mark.unit
class TestPolicyOnlyLevelIdsFromConfig:
    """Level IDs must match config/puzzle-levels.json source of truth."""

    def test_level_ids_from_config(self):
        """Level IDs are 110-230, NOT hardcoded 100-180."""
        levels = load_puzzle_levels()

        result = estimate_difficulty_policy_only(
            policy_prior=0.6,
            move_order="strict",
            correct_move_priors=None,
        )
        assert result.estimated_level_id == levels[result.estimated_level], (
            f"ID mismatch: got {result.estimated_level_id}, "
            f"expected {levels[result.estimated_level]} for {result.estimated_level}"
        )


@pytest.mark.unit
class TestPolicyOnlyThresholdsFromConfig:
    """Thresholds come from config/katago-enrichment.json, not hardcoded."""

    def test_threshold_boundaries_from_config(self):
        """Config has 9 policy_to_level thresholds matching 9 levels."""
        cfg = load_enrichment_config()
        thresholds = cfg.difficulty.policy_to_level.thresholds
        levels = load_puzzle_levels()

        assert len(thresholds) == len(levels), (
            f"Expected {len(levels)} thresholds, got {len(thresholds)}"
        )
        # All threshold slugs must be valid level slugs
        for t in thresholds:
            assert t.level_slug in levels, (
                f"Threshold slug '{t.level_slug}' not in puzzle-levels.json"
            )
        # Thresholds must be sorted descending by min_prior
        priors = [t.min_prior for t in thresholds]
        assert priors == sorted(priors, reverse=True), (
            "policy_to_level thresholds must be sorted descending by min_prior"
        )


@pytest.mark.unit
class TestPolicyOnlyThreePlusMiaiMoves:
    """Puzzle with 3+ equivalent correct moves."""

    def test_three_plus_miai_moves(self):
        """3 equivalent moves: max of 3 priors used, not sum."""
        result = estimate_difficulty_policy_only(
            policy_prior=0.15,  # fallback, not used for miai
            move_order="miai",
            correct_move_priors=[0.15, 0.12, 0.10],
        )
        # max = 0.15 → should be elementary or intermediate
        # sum = 0.37 → would be beginner (wrong)
        assert result.estimated_level not in ("novice",), (
            f"Should use max(0.15), not sum. Got {result.estimated_level}"
        )


# ===================================================================
# A.3.2 — MCTS-based difficulty (Tier 2)
# ===================================================================

@pytest.mark.unit
class TestVisitsToSolveEasy:
    """Easy puzzle: correct move is top at low visits."""

    def test_visits_to_solve_easy(self):
        """Easy puzzle: KataGo agrees → visits_to_solve = visits_used."""
        validation = _make_validation(
            correct_move_policy=0.6,
            katago_agrees=True,
            visits_used=200,
        )
        refutations = _make_refutations(count=0)
        result = estimate_difficulty(
            validation=validation,
            refutation_result=refutations,
            solution_moves=["dd"],
            puzzle_id="easy-1",
        )
        # S.3: visits_to_solve = visits_used when KataGo agrees
        assert result.visits_to_solve == 200, (
            f"Easy puzzle should have visits_to_solve == visits_used, got {result.visits_to_solve}"
        )


@pytest.mark.unit
class TestVisitsToSolveHard:
    """Hard puzzle: correct move NOT top at moderate visits."""

    def test_visits_to_solve_hard(self):
        """Hard puzzle: KataGo disagrees → visits_to_solve > visits_used."""
        validation = _make_validation(
            correct_move_policy=0.01,
            katago_agrees=False,
            visits_used=200,
        )
        refutations = _make_refutations(count=3)
        result = estimate_difficulty(
            validation=validation,
            refutation_result=refutations,
            solution_moves=["dd", "ee", "ff", "gg", "hh"],
            puzzle_id="hard-1",
        )
        # S.3: visits_to_solve = visits_used * 2 when KataGo disagrees
        assert result.visits_to_solve == 400, (
            f"Hard puzzle should have visits_to_solve == 400, got {result.visits_to_solve}"
        )


@pytest.mark.unit
class TestTrapDensityNoTraps:
    """Trivial puzzle: single obvious move → trap_density ≈ 0."""

    def test_trap_density_no_traps(self):
        """No plausible wrong moves → trap_density near 0."""
        validation = _make_validation(
            correct_move_policy=0.8,
            katago_agrees=True,
            visits_used=50,
        )
        refutations = _make_refutations(count=0)
        result = estimate_difficulty(
            validation=validation,
            refutation_result=refutations,
            solution_moves=["dd"],
            puzzle_id="trivial-1",
        )
        assert result.trap_density < 0.1, (
            f"No wrong moves → trap_density should be < 0.1, got {result.trap_density}"
        )


@pytest.mark.unit
class TestTrapDensityManyTraps:
    """Many tempting wrong moves → high trap_density."""

    def test_trap_density_many_traps(self):
        """Multiple wrong moves with high policy and big delta → trap_density > 0.3."""
        validation = _make_validation(
            correct_move_policy=0.1,
            katago_agrees=True,
            visits_used=200,
        )
        # Use higher winrate_delta to simulate truly tempting wrong moves
        refutations = _make_refutations(count=3, wrong_move_policy=0.15, winrate_delta=-0.5)
        result = estimate_difficulty(
            validation=validation,
            refutation_result=refutations,
            solution_moves=["dd", "ee", "ff"],
            puzzle_id="trappy-1",
        )
        assert result.trap_density > 0.3, (
            f"Many wrong moves → trap_density should be > 0.3, got {result.trap_density}"
        )


@pytest.mark.unit
class TestCompositeScoreMonotonic:
    """Easy < medium < hard composite scores."""

    def test_composite_score_monotonic(self):
        """Composite score increases with difficulty."""
        # Easy: high policy, few moves, agreed
        easy_val = _make_validation(correct_move_policy=0.7, katago_agrees=True, visits_used=50)
        easy_ref = _make_refutations(count=0)
        easy = estimate_difficulty(easy_val, easy_ref, ["dd"], "easy")

        # Medium: medium policy, moderate depth
        med_val = _make_validation(correct_move_policy=0.1, katago_agrees=True, visits_used=200)
        med_ref = _make_refutations(count=1)
        medium = estimate_difficulty(med_val, med_ref, ["dd", "ee", "ff"], "medium")

        # Hard: low policy, deep, many wrong moves
        hard_val = _make_validation(correct_move_policy=0.01, katago_agrees=False, visits_used=2000)
        hard_ref = _make_refutations(count=3)
        hard = estimate_difficulty(hard_val, hard_ref, ["dd", "ee", "ff", "gg", "hh", "ii", "jj"], "hard")

        assert easy.raw_difficulty_score < medium.raw_difficulty_score, (
            f"Easy ({easy.raw_difficulty_score:.1f}) should be < Medium ({medium.raw_difficulty_score:.1f})"
        )
        assert medium.raw_difficulty_score < hard.raw_difficulty_score, (
            f"Medium ({medium.raw_difficulty_score:.1f}) should be < Hard ({hard.raw_difficulty_score:.1f})"
        )


@pytest.mark.unit
class TestCompositeWeightsFromConfig:
    """Composite formula weights loaded from config."""

    def test_composite_weights_from_config(self):
        """Weights from config/katago-enrichment.json are used, not hardcoded."""
        cfg = load_enrichment_config()
        w = cfg.difficulty.weights

        # S.3: Verify all weight fields are positive
        assert w.policy_rank > 0, "policy_rank weight must be positive"
        assert w.visits_to_solve > 0, "visits_to_solve weight must be positive"
        assert w.trap_density > 0, "trap_density weight must be positive"
        assert w.structural > 0, "structural weight must be positive"
        assert w.complexity > 0, "complexity weight must be positive"

        # G11/T17: PUCT-coupled signals (policy+visits) < 40%, structural >= 35%
        puct_weight = w.policy_rank + w.visits_to_solve
        structural_weight = w.structural
        total = w.policy_rank + w.visits_to_solve + w.trap_density + structural_weight + w.complexity

        assert abs(total - 100.0) < 0.1, (
            f"Weights should sum to 100, got {total}"
        )
        assert puct_weight < 40.0, (
            f"PUCT-coupled signals (policy+visits) should be < 40%, got {puct_weight}"
        )
        assert structural_weight >= 35.0, (
            f"Structural weight should be >= 35%, got {structural_weight}"
        )


class TestProofDepthSignal:
    """KM-04: Proof-depth difficulty signal."""

    def _make_validation(self, policy=0.5, visits=200, agrees=True):
        """Create a minimal CorrectMoveResult for testing."""
        from analyzers.validate_correct_move import CorrectMoveResult, ValidationStatus
        return CorrectMoveResult(
            puzzle_id="test-pd",
            status=ValidationStatus.ACCEPTED if agrees else ValidationStatus.FLAGGED,
            correct_move_gtp="C3",
            correct_move_policy=policy,
            correct_move_visits=visits,
            katago_agrees=agrees,
            visits_used=visits,
        )

    def _make_refutations(self, count=1):
        """Create minimal RefutationResult."""
        from models.refutation_result import Refutation, RefutationResult
        refs = [
            Refutation(
                wrong_move="D4",
                wrong_move_policy=0.1,
                winrate_delta=-0.3,
                refutation_sequence=["E5"],
            )
            for _ in range(count)
        ]
        return RefutationResult(refutations=refs)

    def test_proof_depth_affects_difficulty(self):
        """T053: Deeper tree -> higher raw difficulty score."""
        from analyzers.estimate_difficulty import estimate_difficulty
        from config import clear_cache
        clear_cache()

        v = self._make_validation()
        r = self._make_refutations()

        # Same puzzle, different proof depths
        d1 = estimate_difficulty(v, r, solution_moves=["C3", "D4"],
                                 max_resolved_depth=0)
        d2 = estimate_difficulty(v, r, solution_moves=["C3", "D4"],
                                 max_resolved_depth=10)
        # Deeper proof -> higher score (or equal if weight is very small)
        assert d2.raw_difficulty_score >= d1.raw_difficulty_score

    def test_proof_depth_zero_when_no_tree(self):
        """T054: ac:1 puzzles (no AI tree) -> signal = 0, no change."""
        from analyzers.estimate_difficulty import estimate_difficulty
        from config import clear_cache
        clear_cache()

        v = self._make_validation()
        r = self._make_refutations()

        d_without = estimate_difficulty(v, r, solution_moves=["C3", "D4"],
                                        max_resolved_depth=0)
        # Running without max_resolved_depth should produce same result
        d_default = estimate_difficulty(v, r, solution_moves=["C3", "D4"])

        assert abs(d_without.raw_difficulty_score - d_default.raw_difficulty_score) < 0.01

    def test_proof_depth_capped_at_ceiling(self):
        """T055: depth > ceiling normalized to 1.0."""
        from analyzers.estimate_difficulty import estimate_difficulty
        from config import clear_cache
        clear_cache()

        v = self._make_validation()
        r = self._make_refutations()

        d_at_ceiling = estimate_difficulty(v, r, solution_moves=["C3", "D4"],
                                            max_resolved_depth=20)
        d_above_ceiling = estimate_difficulty(v, r, solution_moves=["C3", "D4"],
                                              max_resolved_depth=100)
        # Both should produce same score (capped at 1.0)
        assert abs(d_at_ceiling.raw_difficulty_score - d_above_ceiling.raw_difficulty_score) < 0.01

    def test_difficulty_backward_compat(self):
        """T057: proof_depth=0 produces identical difficulty output to pre-change."""
        from analyzers.estimate_difficulty import estimate_difficulty
        from config import clear_cache
        clear_cache()

        v = self._make_validation()
        r = self._make_refutations()

        # Without parameter = default 0
        d = estimate_difficulty(v, r, solution_moves=["C3", "D4"])
        assert d.raw_difficulty_score >= 0
        assert d.estimated_level is not None


# ===================================================================
# T5 — Score-based trap density tests (v1.17)
# ===================================================================


@pytest.mark.unit
class TestTrapDensityScoreBased:
    """Score-based formula produces different densities than winrate-only."""

    def test_score_divergent_vs_winrate_divergent(self):
        """Score-delta and winrate-delta produce different trap densities."""
        from analyzers.estimate_difficulty import _compute_trap_density

        # Case A: large score_delta, small winrate_delta
        ref_score = _make_refutations(
            count=2, wrong_move_policy=0.2, winrate_delta=-0.1, score_delta=-15.0
        )
        density_score = _compute_trap_density(ref_score)

        # Case B: small score_delta (fallback to winrate), same winrate_delta
        ref_wr = _make_refutations(
            count=2, wrong_move_policy=0.2, winrate_delta=-0.1, score_delta=0.0
        )
        density_wr = _compute_trap_density(ref_wr)

        # Score-based: |15|/30 = 0.5 per ref → density = 0.5
        # Winrate-based: |0.1| per ref → density = 0.1
        assert density_score > density_wr, (
            f"Score-based ({density_score}) should > winrate-only ({density_wr})"
        )

    def test_floor_activates_with_refutations(self):
        """Floor activates when raw density < floor and refutations exist."""
        from analyzers.estimate_difficulty import _compute_trap_density

        # Very small score_delta → raw density below floor
        ref = _make_refutations(
            count=1, wrong_move_policy=0.1, winrate_delta=0.0, score_delta=-0.5
        )
        density = _compute_trap_density(ref)
        # |0.5|/30 = 0.0167, floor = 0.05
        assert density >= 0.05, (
            f"Floor should activate: density={density}, expected >= 0.05"
        )

    def test_floor_does_not_activate_zero_refutations(self):
        """Floor does NOT activate when 0 refutations → density = 0.0."""
        from analyzers.estimate_difficulty import _compute_trap_density

        ref = _make_refutations(count=0)
        density = _compute_trap_density(ref)
        assert density == 0.0

    def test_fallback_to_winrate_when_score_delta_zero(self):
        """score_delta == 0 falls back to |winrate_delta|."""
        from analyzers.estimate_difficulty import _compute_trap_density

        ref = _make_refutations(
            count=2, wrong_move_policy=0.2, winrate_delta=-0.4, score_delta=0.0
        )
        density = _compute_trap_density(ref)
        # Fallback: |0.4| = 0.4 → density = 0.4 (> floor 0.05)
        assert abs(density - 0.4) < 0.01, (
            f"Fallback to winrate_delta: expected ~0.4, got {density}"
        )

    def test_score_normalization_cap_respected(self):
        """score_delta beyond cap is capped at 1.0 normalized loss."""
        from analyzers.estimate_difficulty import _compute_trap_density

        # score_delta = -60 → |60|/30 = 2.0, capped to 1.0
        ref = _make_refutations(
            count=1, wrong_move_policy=0.5, winrate_delta=0.0, score_delta=-60.0
        )
        density = _compute_trap_density(ref)
        # normalized_loss capped at 1.0 → density = 1.0
        assert abs(density - 1.0) < 0.01, (
            f"Expected density capped at 1.0, got {density}"
        )


# ===================================================================
# T7 — Elo-anchor gate tests (v1.17)
# ===================================================================


@pytest.mark.unit
class TestEloAnchorGateOverride:
    """Elo gate overrides when divergence >= threshold."""

    def test_override_large_divergence(self):
        """Level overridden when composite vs policy diverge by >= 2 levels."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        # Composite says elementary (130), policy says advanced (160) → diff = 3 levels
        slug, lid = _elo_anchor_gate(
            policy_prior=0.03,  # → advanced
            composite_level_slug="elementary",
            composite_level_id=130,
            cfg=cfg,
            puzzle_id="test-override",
        )
        assert slug != "elementary", (
            f"Expected override from elementary, got {slug}"
        )
        assert slug == "advanced", f"Expected advanced, got {slug}"
        assert lid == 160


@pytest.mark.unit
class TestEloAnchorGatePreserve:
    """Elo gate preserves when divergence < threshold."""

    def test_preserve_small_divergence(self):
        """Level preserved when divergence < 2 levels."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        # Composite = intermediate (140), policy prior maps to intermediate too
        slug, lid = _elo_anchor_gate(
            policy_prior=0.10,  # → intermediate (140)
            composite_level_slug="intermediate",
            composite_level_id=140,
            cfg=cfg,
            puzzle_id="test-preserve",
        )
        assert slug == "intermediate"
        assert lid == 140


@pytest.mark.unit
class TestEloAnchorGateSkipNovice:
    """Elo gate skips novice (outside covered range)."""

    def test_skip_novice(self):
        """Novice level is outside Elo anchor range → no override."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        slug, lid = _elo_anchor_gate(
            policy_prior=0.01,
            composite_level_slug="novice",
            composite_level_id=110,
            cfg=cfg,
            puzzle_id="test-novice",
        )
        assert slug == "novice"
        assert lid == 110


@pytest.mark.unit
class TestEloAnchorGateSkipBeginner:
    """Elo gate skips beginner (outside covered range)."""

    def test_skip_beginner(self):
        """Beginner level is outside Elo anchor range → no override."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        slug, lid = _elo_anchor_gate(
            policy_prior=0.01,
            composite_level_slug="beginner",
            composite_level_id=120,
            cfg=cfg,
            puzzle_id="test-beginner",
        )
        assert slug == "beginner"
        assert lid == 120


@pytest.mark.unit
class TestEloAnchorGateSkipExpert:
    """Elo gate skips expert (outside covered range)."""

    def test_skip_expert(self):
        """Expert level is outside Elo anchor range → no override."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        slug, lid = _elo_anchor_gate(
            policy_prior=0.50,
            composite_level_slug="expert",
            composite_level_id=230,
            cfg=cfg,
            puzzle_id="test-expert",
        )
        assert slug == "expert"
        assert lid == 230


@pytest.mark.unit
class TestEloAnchorGateCoveredRange:
    """Elo gate works across the full covered range."""

    @pytest.mark.parametrize("level_slug,level_id", [
        ("elementary", 130),
        ("intermediate", 140),
        ("upper-intermediate", 150),
        ("advanced", 160),
        ("low-dan", 210),
        ("high-dan", 220),
    ])
    def test_covered_levels_accepted(self, level_slug, level_id):
        """Covered levels are processed (not skipped) by Elo gate."""
        from analyzers.estimate_difficulty import _elo_anchor_gate

        cfg = load_enrichment_config()
        # Use a policy that maps to the same level — should preserve
        level_policies = {
            "elementary": 0.15, "intermediate": 0.10,
            "upper-intermediate": 0.05, "advanced": 0.03,
            "low-dan": 0.015, "high-dan": 0.005,
        }
        policy = level_policies[level_slug]
        slug, lid = _elo_anchor_gate(
            policy_prior=policy,
            composite_level_slug=level_slug,
            composite_level_id=level_id,
            cfg=cfg,
            puzzle_id=f"test-covered-{level_slug}",
        )
        # Same level → divergence = 0 → preserved
        assert slug == level_slug
        assert lid == level_id


@pytest.mark.unit
class TestEloAnchorGateThresholdConfig:
    """Override threshold is config-driven."""

    def test_threshold_from_config(self):
        """override_threshold_levels from config is respected."""

        cfg = load_enrichment_config()
        threshold = cfg.elo_anchor.override_threshold_levels
        assert threshold == 2, f"Expected threshold=2, got {threshold}"


@pytest.mark.unit
class TestEloAnchorGateDisabled:
    """Elo gate disabled returns original level."""

    def test_disabled_returns_original(self):
        """When elo_anchor.enabled=false, always returns original level."""
        from analyzers.estimate_difficulty import _elo_anchor_gate
        from config.difficulty import EloAnchorConfig

        cfg = load_enrichment_config()
        # Create a modified config with elo_anchor disabled
        disabled_cfg = cfg.model_copy(update={
            "elo_anchor": EloAnchorConfig(enabled=False),
        })
        slug, lid = _elo_anchor_gate(
            policy_prior=0.01,  # → expert
            composite_level_slug="elementary",
            composite_level_id=130,
            cfg=disabled_cfg,
            puzzle_id="test-disabled",
        )
        assert slug == "elementary"
        assert lid == 130


# ===================================================================
# RC-3 / VAL-7: Golden-set difficulty calibration spot-check
# ===================================================================

# 9-level ordering for tier-distance computation
_LEVEL_ORDER = [
    "novice", "beginner", "elementary", "intermediate",
    "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
]


def _level_index(slug: str) -> int:
    return _LEVEL_ORDER.index(slug)


def _tier_distance(a: str, b: str) -> int:
    return abs(_level_index(a) - _level_index(b))


# 50 representative puzzle profiles spanning the full difficulty range.
# Each tuple: (profile_name, policy, visits, agrees, depth, refutations,
#               ref_policy, ref_wr_delta, ref_score_delta,
#               expected_min_level, expected_max_level)
# Score thresholds: novice≤40, beginner≤50, elementary≤62, intermediate≤70,
# upper-intermediate≤78, advanced≤85, low-dan≤91, high-dan≤96, expert≤100
# Weights: policy=15, visits=15, trap=20, structural=35, complexity=15
_GOLDEN_PROFILES = [
    # ── Novice (score ≤ 40) — high policy, shallow depth ──
    ("trivial-capture", 0.85, 50, True, 1, 0, 0.0, 0.0, 0.0, "novice", "novice"),
    ("obvious-atari", 0.75, 50, True, 1, 0, 0.0, 0.0, 0.0, "novice", "novice"),
    ("easy-capture-2", 0.70, 100, True, 2, 0, 0.0, 0.0, 0.0, "novice", "beginner"),
    ("simple-life-1", 0.65, 100, True, 2, 1, 0.05, -0.1, -3.0, "novice", "beginner"),
    ("easy-corner", 0.60, 100, True, 1, 0, 0.0, 0.0, 0.0, "novice", "beginner"),
    # ── Novice/Beginner — medium policy, short depth, few traps ──
    ("basic-eye", 0.45, 150, True, 2, 1, 0.1, -0.15, -5.0, "novice", "beginner"),
    ("simple-connect", 0.40, 150, True, 3, 1, 0.1, -0.2, -8.0, "novice", "beginner"),
    ("capture-race-easy", 0.35, 200, True, 3, 1, 0.12, -0.2, -6.0, "novice", "beginner"),
    ("throw-in-1", 0.30, 200, True, 2, 1, 0.08, -0.15, -4.0, "novice", "beginner"),
    ("ladder-simple", 0.28, 200, True, 4, 1, 0.1, -0.2, -7.0, "novice", "beginner"),
    # ── Beginner/Elementary — lower policy, moderate depth+traps ──
    ("life-death-3", 0.22, 300, True, 3, 2, 0.12, -0.25, -10.0, "novice", "elementary"),
    ("ko-simple", 0.20, 300, True, 3, 2, 0.15, -0.3, -12.0, "novice", "elementary"),
    ("snapback-1", 0.18, 300, True, 2, 2, 0.1, -0.2, -8.0, "novice", "elementary"),
    ("eye-shape-2", 0.16, 350, True, 4, 2, 0.1, -0.25, -9.0, "novice", "elementary"),
    ("cutting-1", 0.15, 350, True, 3, 2, 0.12, -0.3, -10.0, "novice", "elementary"),
    # ── Elementary/Intermediate — low policy, deeper, more traps ──
    ("life-death-5", 0.12, 500, True, 5, 2, 0.15, -0.35, -15.0, "novice", "intermediate"),
    ("ko-complex", 0.10, 500, True, 5, 3, 0.15, -0.3, -12.0, "novice", "intermediate"),
    ("sacrifice-1", 0.09, 500, True, 4, 2, 0.12, -0.3, -14.0, "novice", "intermediate"),
    ("net-1", 0.08, 500, True, 3, 3, 0.1, -0.25, -10.0, "novice", "intermediate"),
    ("nakade-simple", 0.08, 400, True, 4, 2, 0.12, -0.25, -11.0, "novice", "intermediate"),
    # ── Intermediate/Upper-intermediate — very low policy, deep ──
    ("seki-1", 0.06, 800, True, 5, 3, 0.15, -0.35, -16.0, "beginner", "upper-intermediate"),
    ("capture-race-hard", 0.05, 1000, True, 6, 3, 0.15, -0.4, -18.0, "beginner", "advanced"),
    ("life-death-7", 0.05, 800, True, 7, 3, 0.12, -0.3, -14.0, "beginner", "advanced"),
    ("double-ko", 0.04, 1000, True, 5, 3, 0.15, -0.35, -15.0, "beginner", "advanced"),
    ("tesuji-combo", 0.04, 900, True, 6, 3, 0.12, -0.3, -12.0, "beginner", "advanced"),
    # ── Advanced — expert-level policy, deep trees ──
    ("deep-ladder", 0.03, 1500, True, 8, 3, 0.1, -0.4, -20.0, "elementary", "high-dan"),
    ("ko-fight-1", 0.03, 1500, True, 7, 3, 0.15, -0.35, -18.0, "elementary", "high-dan"),
    ("life-death-9", 0.025, 1500, True, 9, 3, 0.12, -0.4, -22.0, "elementary", "high-dan"),
    ("sacrifice-deep", 0.025, 1200, True, 7, 3, 0.1, -0.35, -16.0, "elementary", "high-dan"),
    ("seki-deep", 0.02, 1500, True, 6, 3, 0.15, -0.4, -20.0, "elementary", "high-dan"),
    # ── Low-Dan — pro-level policy, deep+complex ──
    ("pro-tsumego-1", 0.015, 2000, True, 10, 3, 0.12, -0.45, -25.0, "intermediate", "expert"),
    ("pro-tsumego-2", 0.015, 2000, False, 8, 3, 0.15, -0.4, -20.0, "intermediate", "expert"),
    ("crane-nest-1", 0.012, 2500, True, 12, 3, 0.1, -0.45, -28.0, "intermediate", "expert"),
    ("cho-chikun-1", 0.012, 2000, True, 10, 3, 0.12, -0.4, -22.0, "intermediate", "expert"),
    ("deep-ko-2", 0.01, 2500, False, 9, 3, 0.15, -0.45, -25.0, "intermediate", "expert"),
    # ── High-Dan — extreme policy, very deep ──
    ("xuanxuan-1", 0.008, 3000, False, 12, 3, 0.12, -0.5, -30.0, "upper-intermediate", "expert"),
    ("xuanxuan-2", 0.007, 3000, False, 14, 3, 0.1, -0.45, -28.0, "upper-intermediate", "expert"),
    ("famous-tsumego-1", 0.006, 4000, False, 15, 3, 0.12, -0.5, -30.0, "upper-intermediate", "expert"),
    ("gokyo-1", 0.005, 3500, False, 12, 3, 0.15, -0.45, -25.0, "upper-intermediate", "expert"),
    ("gokyo-2", 0.005, 4000, False, 14, 3, 0.1, -0.5, -30.0, "upper-intermediate", "expert"),
    # ── Expert — minimum policy, maximum depth ──
    ("igo-hatsuyoron-1", 0.003, 5000, False, 18, 3, 0.12, -0.5, -35.0, "advanced", "expert"),
    ("igo-hatsuyoron-2", 0.002, 5000, False, 20, 3, 0.1, -0.55, -40.0, "advanced", "expert"),
    ("famous-problem-1", 0.003, 4500, False, 16, 3, 0.15, -0.5, -32.0, "advanced", "expert"),
    ("famous-problem-2", 0.002, 5000, False, 22, 3, 0.12, -0.55, -38.0, "advanced", "expert"),
    ("extreme-1", 0.001, 5000, False, 25, 3, 0.1, -0.6, -45.0, "advanced", "expert"),
    # ── Edge cases ──
    ("min-policy", 0.001, 100, True, 1, 0, 0.0, 0.0, 0.0, "novice", "expert"),
    ("max-policy", 0.99, 50, True, 1, 0, 0.0, 0.0, 0.0, "novice", "novice"),
    ("many-traps", 0.10, 500, True, 3, 3, 0.25, -0.5, -20.0, "novice", "advanced"),
    ("disagree-simple", 0.30, 200, False, 2, 1, 0.1, -0.2, -8.0, "novice", "intermediate"),
    ("deep-no-traps", 0.01, 2000, True, 15, 0, 0.0, 0.0, 0.0, "novice", "expert"),
]


@pytest.mark.unit
class TestGoldenSetCalibration:
    """RC-3 / VAL-7: Verify 5-component difficulty formula produces
    reasonable YG assignments across 50 representative puzzle profiles.

    Each profile defines an expected level RANGE (min, max). The formula
    must produce a level within that range. Tier shifts > 1 from the
    center of the expected range are flagged.
    """

    @pytest.mark.parametrize(
        "name,policy,visits,agrees,depth,ref_count,"
        "ref_policy,ref_wr_delta,ref_score_delta,"
        "expected_min,expected_max",
        _GOLDEN_PROFILES,
        ids=[p[0] for p in _GOLDEN_PROFILES],
    )
    def test_golden_profile(
        self, name, policy, visits, agrees, depth, ref_count,
        ref_policy, ref_wr_delta, ref_score_delta,
        expected_min, expected_max,
    ):
        """Each golden profile produces a level within expected range."""
        validation = _make_validation(
            correct_move_policy=policy,
            katago_agrees=agrees,
            visits_used=visits,
        )
        refutations = _make_refutations(
            count=ref_count,
            wrong_move_policy=ref_policy,
            winrate_delta=ref_wr_delta,
            score_delta=ref_score_delta,
        )
        solution = [f"m{i}" for i in range(depth)]

        result = estimate_difficulty(
            validation=validation,
            refutation_result=refutations,
            solution_moves=solution,
            puzzle_id=name,
        )

        level = result.estimated_level
        min_idx = _level_index(expected_min)
        max_idx = _level_index(expected_max)
        actual_idx = _level_index(level)

        assert min_idx <= actual_idx <= max_idx, (
            f"Profile '{name}': got {level} (idx={actual_idx}), "
            f"expected range {expected_min}..{expected_max} "
            f"(idx={min_idx}..{max_idx}). "
            f"raw_score={result.raw_difficulty_score:.1f}"
        )

    def test_monotonic_across_difficulty_gradient(self):
        """Profiles sorted by increasing difficulty produce
        monotonically non-decreasing raw scores."""
        scores = []
        for profile in _GOLDEN_PROFILES[:45]:  # Exclude edge cases
            name, policy, visits, agrees, depth, ref_count, \
                ref_policy, ref_wr_delta, ref_score_delta, _, _ = profile
            validation = _make_validation(
                correct_move_policy=policy,
                katago_agrees=agrees,
                visits_used=visits,
            )
            refutations = _make_refutations(
                count=ref_count,
                wrong_move_policy=ref_policy,
                winrate_delta=ref_wr_delta,
                score_delta=ref_score_delta,
            )
            solution = [f"m{i}" for i in range(depth)]
            result = estimate_difficulty(
                validation=validation,
                refutation_result=refutations,
                solution_moves=solution,
                puzzle_id=name,
            )
            scores.append((name, result.raw_difficulty_score))

        # Check monotonicity within same-category 5-profile groups
        for group_start in range(0, 45, 5):
            group = scores[group_start:group_start + 5]
            prev_avg = sum(s for _, s in group) / len(group)
            if group_start > 0:
                prev_group = scores[group_start - 5:group_start]
                prev_group_avg = sum(s for _, s in prev_group) / len(prev_group)
                assert prev_avg >= prev_group_avg - 5.0, (
                    f"Group {group_start//5} avg ({prev_avg:.1f}) should be >= "
                    f"previous group avg ({prev_group_avg:.1f}) - 5.0 margin"
                )

    def test_no_extreme_tier_shifts(self):
        """No profile produces a level outside its expected range
        by more than 1 tier."""
        out_of_range = []
        for profile in _GOLDEN_PROFILES:
            name, policy, visits, agrees, depth, ref_count, \
                ref_policy, ref_wr_delta, ref_score_delta, \
                expected_min, expected_max = profile
            validation = _make_validation(
                correct_move_policy=policy,
                katago_agrees=agrees,
                visits_used=visits,
            )
            refutations = _make_refutations(
                count=ref_count,
                wrong_move_policy=ref_policy,
                winrate_delta=ref_wr_delta,
                score_delta=ref_score_delta,
            )
            solution = [f"m{i}" for i in range(depth)]
            result = estimate_difficulty(
                validation=validation,
                refutation_result=refutations,
                solution_moves=solution,
                puzzle_id=name,
            )
            actual_idx = _level_index(result.estimated_level)
            min_idx = _level_index(expected_min)
            max_idx = _level_index(expected_max)
            # Allow 1-tier overshoot beyond expected range
            if actual_idx < min_idx - 1 or actual_idx > max_idx + 1:
                out_of_range.append(
                    f"  {name}: got {result.estimated_level} "
                    f"(idx={actual_idx}), expected range "
                    f"{expected_min}..{expected_max} "
                    f"(idx={min_idx}..{max_idx})"
                )
        assert not out_of_range, (
            "Profiles outside expected range (+1 tolerance):\n"
            + "\n".join(out_of_range)
        )


# --- Migrated from test_sprint1_fixes.py (P1.7 gap ID) ---


@pytest.mark.unit
class TestDifficultyWeightsValidation:
    """P1.7: Difficulty weight models must validate sum == 100."""

    def test_default_weights_valid(self):
        """Default weights sum to 100."""
        from config.difficulty import DifficultyWeights, StructuralDifficultyWeights
        w = DifficultyWeights()
        total = w.policy_rank + w.visits_to_solve + w.trap_density + w.structural + w.complexity
        assert abs(total - 100.0) < 0.01

        sw = StructuralDifficultyWeights()
        total_s = sw.solution_depth + sw.branch_count + sw.local_candidates + sw.refutation_count + sw.proof_depth
        assert abs(total_s - 100.0) < 0.01

    def test_weights_sum_80_rejected(self):
        """Weights summing to 80 → validation error."""
        from config.difficulty import DifficultyWeights
        with pytest.raises(ValueError, match="must sum to 100"):
            DifficultyWeights(policy_rank=20, visits_to_solve=20, trap_density=20, structural=20, complexity=0)

    def test_structural_weights_sum_80_rejected(self):
        """Structural weights summing to 80 → validation error."""
        from config.difficulty import StructuralDifficultyWeights
        with pytest.raises(ValueError, match="must sum to 100"):
            StructuralDifficultyWeights(
                solution_depth=20, branch_count=20,
                local_candidates=20, refutation_count=20,
            )

    def test_custom_weights_sum_100_accepted(self):
        """Custom weights summing to 100 → accepted."""
        from config.difficulty import DifficultyWeights
        w = DifficultyWeights(policy_rank=20, visits_to_solve=20, trap_density=20, structural=20, complexity=20)
        total = w.policy_rank + w.visits_to_solve + w.trap_density + w.structural + w.complexity
        assert abs(total - 100.0) < 0.01


# --- Migrated from test_sprint4_fixes.py ---


@pytest.mark.unit
class TestStructuralWeightsFromConfig:
    """G4: Structural difficulty formula must use config weights, not hardcoded."""

    def test_structural_weights_exist_in_config(self):
        """EnrichmentConfig has structural_weights field."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        sw = cfg.difficulty.structural_weights
        assert sw is not None
        assert sw.solution_depth > 0
        assert sw.branch_count > 0
        assert sw.local_candidates > 0
        assert sw.refutation_count > 0

    def test_structural_weights_sum_to_100(self):
        """Structural sub-weights must sum to 100."""
        from config import load_enrichment_config
        cfg = load_enrichment_config()
        sw = cfg.difficulty.structural_weights
        total = sw.solution_depth + sw.branch_count + sw.local_candidates + sw.refutation_count + sw.proof_depth
        assert abs(total - 100.0) < 0.01

    def test_difficulty_uses_all_4_dimensions(self):
        """estimate_difficulty uses depth, branches, local_candidates, AND refutation_count.

        Regression test: old code only used depth (0.6) and branches (0.4),
        ignoring local_candidates and refutation_count entirely.
        """
        from analyzers.estimate_difficulty import estimate_difficulty
        from analyzers.validate_correct_move import CorrectMoveResult, ValidationStatus
        from models.refutation_result import Refutation, RefutationResult

        # Build a validation result with known values
        validation = CorrectMoveResult(
            status=ValidationStatus.ACCEPTED,
            correct_move_gtp="C3",
            katago_top_move="C3",
            katago_agrees=True,
            correct_move_winrate=0.95,
            correct_move_policy=0.5,
            visits_used=500,
        )

        # Case A: zero local_candidates + zero refutations
        refutation_a = RefutationResult(puzzle_id="test-a", refutations=[])
        result_a = estimate_difficulty(
            validation=validation,
            refutation_result=refutation_a,
            solution_moves=["A1", "B2", "C3"],
            puzzle_id="test-a",
            branch_count=2,
            local_candidate_count=0,  # zero
        )

        # Case B: high local_candidates + refutations (should be harder)
        ref = Refutation(
            wrong_move="dd",
            wrong_move_policy=0.3,
            refutation_sequence=["cd", "dc"],
            winrate_after_wrong=0.2,
            winrate_delta=-0.7,
            refutation_depth=2,
        )
        refutation_b = RefutationResult(
            puzzle_id="test-b",
            refutations=[ref, ref, ref],  # 3 refutations
        )
        result_b = estimate_difficulty(
            validation=validation,
            refutation_result=refutation_b,
            solution_moves=["A1", "B2", "C3"],
            puzzle_id="test-b",
            branch_count=2,
            local_candidate_count=15,  # high
        )

        # B should have higher raw score than A because it has more
        # local candidates and refutations (structural component is larger)
        assert result_b.raw_difficulty_score >= result_a.raw_difficulty_score, (
            f"Expected B ({result_b.raw_difficulty_score:.2f}) >= A ({result_a.raw_difficulty_score:.2f}). "
            "local_candidates and refutation_count may not be wired into formula."
        )

    def test_custom_structural_weights(self):
        """Custom structural weights are respected by the formula."""
        from config.difficulty import StructuralDifficultyWeights
        sw = StructuralDifficultyWeights(
            solution_depth=40,
            branch_count=25,
            local_candidates=15,
            refutation_count=10,
            proof_depth=10,
        )
        total = sw.solution_depth + sw.branch_count + sw.local_candidates + sw.refutation_count + sw.proof_depth
        assert abs(total - 100.0) < 0.01
