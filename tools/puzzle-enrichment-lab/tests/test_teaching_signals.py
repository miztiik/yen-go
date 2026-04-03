"""Tests for R-1 computed teaching signals.

Covers:
- compute_log_policy_score edge cases and value ranges
- compute_score_lead_rank ordering and edge cases
- compute_position_closeness symmetry and boundary behavior
- build_teaching_signal_payload integration
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure enrichment lab is on path
_lab = Path(__file__).resolve().parent.parent
if str(_lab) not in sys.path:
    sys.path.insert(0, str(_lab))

from analyzers.estimate_difficulty import (
    compute_log_policy_score,
    compute_position_closeness,
    compute_score_lead_rank,
)
from analyzers.teaching_signal_payload import build_teaching_signal_payload
from models.analysis_response import AnalysisResponse, MoveAnalysis

# ---------------------------------------------------------------------------
# compute_log_policy_score
# ---------------------------------------------------------------------------

class TestLogPolicyScore:
    def test_dominant_move(self):
        """Policy 1.0 -> score 1.0."""
        assert compute_log_policy_score(1.0) == 1.0

    def test_zero_policy(self):
        """Policy 0.0 -> clamped to 1e-6 -> score 0.0."""
        assert compute_log_policy_score(0.0) == 0.0

    def test_tiny_policy(self):
        """Very small policy -> near 0."""
        score = compute_log_policy_score(1e-6)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_medium_policy(self):
        """Policy 0.1 -> should be in upper range."""
        score = compute_log_policy_score(0.1)
        assert 0.7 < score < 0.95

    def test_hidden_tesuji(self):
        """Policy 0.001 -> should be in middle range."""
        score = compute_log_policy_score(0.001)
        assert 0.3 < score < 0.6

    def test_monotonic(self):
        """Higher policy -> higher score."""
        priors = [0.001, 0.01, 0.1, 0.5, 1.0]
        scores = [compute_log_policy_score(p) for p in priors]
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1]

    def test_output_range(self):
        """Output always in [0, 1]."""
        for p in [0.0, 1e-8, 1e-6, 0.001, 0.01, 0.1, 0.5, 0.99, 1.0]:
            score = compute_log_policy_score(p)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_score_lead_rank
# ---------------------------------------------------------------------------

class TestScoreLeadRank:
    def _make_moves(self, scores):
        return [MoveAnalysis(move=chr(65 + i) + "1", score_lead=s) for i, s in enumerate(scores)]

    def test_best_move(self):
        """Best scoring move -> rank 1.0."""
        moves = self._make_moves([10.0, 5.0, -3.0])
        rank = compute_score_lead_rank(moves, "A1")
        assert rank == 1.0

    def test_worst_move(self):
        """Worst scoring move -> rank 0.0."""
        moves = self._make_moves([10.0, 5.0, -3.0])
        rank = compute_score_lead_rank(moves, "C1")
        assert rank == 0.0

    def test_middle_move(self):
        """Middle move -> rank 0.5."""
        moves = self._make_moves([10.0, 5.0, -3.0])
        rank = compute_score_lead_rank(moves, "B1")
        assert rank == 0.5

    def test_empty_moves(self):
        """Empty list -> default 0.5."""
        assert compute_score_lead_rank([], "A1") == 0.5

    def test_single_move(self):
        """Single move -> 0.5."""
        moves = self._make_moves([5.0])
        assert compute_score_lead_rank(moves, "A1") == 0.5

    def test_target_not_found(self):
        """Unknown target -> 0.5."""
        moves = self._make_moves([10.0, 5.0])
        assert compute_score_lead_rank(moves, "Z1") == 0.5


# ---------------------------------------------------------------------------
# compute_position_closeness
# ---------------------------------------------------------------------------

class TestPositionCloseness:
    def test_even_position(self):
        """Winrate 0.5 -> closeness 1.0 (maximally contested)."""
        assert compute_position_closeness(0.5) == 1.0

    def test_decided_black(self):
        """Winrate 1.0 -> closeness 0.0."""
        assert compute_position_closeness(1.0) == 0.0

    def test_decided_white(self):
        """Winrate 0.0 -> closeness 0.0."""
        assert compute_position_closeness(0.0) == 0.0

    def test_slight_advantage(self):
        """Winrate 0.6 -> closeness 0.8."""
        assert compute_position_closeness(0.6) == pytest.approx(0.8)

    def test_symmetry(self):
        """Symmetric around 0.5."""
        assert compute_position_closeness(0.3) == pytest.approx(compute_position_closeness(0.7))


# ---------------------------------------------------------------------------
# build_teaching_signal_payload
# ---------------------------------------------------------------------------

class TestTeachingSignalPayload:
    def _make_response(self):
        return AnalysisResponse(
            request_id="test",
            move_infos=[
                MoveAnalysis(move="D4", visits=100, winrate=0.9, score_lead=12.0, policy_prior=0.7),
                MoveAnalysis(move="C3", visits=50, winrate=0.4, score_lead=-3.0, policy_prior=0.15),
                MoveAnalysis(move="E5", visits=20, winrate=0.3, score_lead=-8.0, policy_prior=0.05),
            ],
            root_winrate=0.55,
            root_score=2.5,
            total_visits=170,
        )

    def test_basic_payload_structure(self):
        resp = self._make_response()
        payload = build_teaching_signal_payload(
            response=resp,
            correct_move_gtp="D4",
            policy_entropy=0.65,
            correct_move_rank=1,
        )
        # Option B: version + three sections
        assert payload["version"] == 1
        assert "correct_move" in payload
        assert "position" in payload
        assert "wrong_moves" in payload
        # Correct move section
        cm = payload["correct_move"]
        assert "move_gtp" in cm
        assert "log_policy_score" in cm
        assert "score_lead_rank" in cm
        assert "play_selection_value" in cm
        # Position section
        pos = payload["position"]
        assert "root_winrate" in pos
        assert "root_score" in pos
        assert "position_closeness" in pos
        assert "policy_entropy" in pos
        assert "correct_move_rank" in pos

    def test_correct_move_signals(self):
        resp = self._make_response()
        payload = build_teaching_signal_payload(
            response=resp,
            correct_move_gtp="D4",
            policy_entropy=0.65,
            correct_move_rank=1,
        )
        cm = payload["correct_move"]
        assert cm["log_policy_score"] > 0.5  # policy 0.7 -> high log score
        assert cm["score_lead_rank"] == 1.0  # best score_lead
        assert payload["position"]["position_closeness"] > 0.0

    def test_none_response(self):
        payload = build_teaching_signal_payload(
            response=None,
            correct_move_gtp="D4",
            policy_entropy=0.0,
            correct_move_rank=0,
        )
        assert payload["correct_move"]["log_policy_score"] == 0.0
        assert payload["position"]["position_closeness"] == 0.5


# ---------------------------------------------------------------------------
# T15: RefutationEntry field propagation
# ---------------------------------------------------------------------------

class TestRefutationEntryFieldPropagation:
    """T15: Verify build_refutation_entries() propagates score_delta,
    wrong_move_policy, and ownership_delta from Refutation → RefutationEntry."""

    def test_score_delta_propagated(self):
        from analyzers.result_builders import build_refutation_entries
        from models.refutation_result import Refutation, RefutationResult
        ref = Refutation(wrong_move="cd", score_delta=-5.2, refutation_sequence=["de"])
        rr = RefutationResult(puzzle_id="t", refutations=[ref], total_candidates_evaluated=1, visits_per_candidate=100)
        entries = build_refutation_entries(rr)
        assert entries[0].score_delta == -5.2

    def test_wrong_move_policy_propagated(self):
        from analyzers.result_builders import build_refutation_entries
        from models.refutation_result import Refutation, RefutationResult
        ref = Refutation(wrong_move="cd", wrong_move_policy=0.18, refutation_sequence=["de"])
        rr = RefutationResult(puzzle_id="t", refutations=[ref], total_candidates_evaluated=1, visits_per_candidate=100)
        entries = build_refutation_entries(rr)
        assert entries[0].wrong_move_policy == 0.18

    def test_ownership_delta_propagated(self):
        from analyzers.result_builders import build_refutation_entries
        from models.refutation_result import Refutation, RefutationResult
        ref = Refutation(wrong_move="cd", ownership_delta=0.67, refutation_sequence=["de"])
        rr = RefutationResult(puzzle_id="t", refutations=[ref], total_candidates_evaluated=1, visits_per_candidate=100)
        entries = build_refutation_entries(rr)
        assert entries[0].ownership_delta == 0.67

    def test_all_fields_default_zero(self):
        from analyzers.result_builders import build_refutation_entries
        from models.refutation_result import Refutation, RefutationResult
        ref = Refutation(wrong_move="cd", refutation_sequence=["de"])
        rr = RefutationResult(puzzle_id="t", refutations=[ref], total_candidates_evaluated=1, visits_per_candidate=100)
        entries = build_refutation_entries(rr)
        assert entries[0].score_delta == 0.0
        assert entries[0].wrong_move_policy == 0.0
        assert entries[0].ownership_delta == 0.0


# ---------------------------------------------------------------------------
# T16: Option B payload — instructiveness, seki, ownership, board_size, config
# ---------------------------------------------------------------------------

class TestOptionBPayload:
    """T16: Comprehensive tests for the Option B rich payload."""

    def _make_response(self, root_winrate=0.55):
        return AnalysisResponse(
            request_id="test",
            move_infos=[
                MoveAnalysis(move="D4", visits=80, winrate=0.9, score_lead=12.0, policy_prior=0.7, play_selection_value=0.85),
                MoveAnalysis(move="E5", visits=15, winrate=0.3, score_lead=-8.0, policy_prior=0.08),
            ],
            root_winrate=root_winrate,
            root_score=2.5,
            total_visits=95,
        )

    def _make_result_with_refutations(self):
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(
                wrong_move="ee", delta=-0.35, score_delta=-8.2,
                wrong_move_policy=0.08, ownership_delta=0.45,
                refutation_depth=3, refutation_pv=["ee", "df", "ce"],
                refutation_type="opponent_lives",
            ),
        ]
        return result

    def test_wrong_moves_populated(self):
        """Payload includes wrong moves from populated result.refutations."""
        resp = self._make_response()
        result = self._make_result_with_refutations()
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19,
        )
        assert len(payload["wrong_moves"]) == 1
        wm = payload["wrong_moves"][0]
        assert wm["score_delta"] == -8.2
        assert wm["wrong_move_policy"] == 0.08
        assert wm["refutation_depth"] == 3
        assert wm["refutation_pv"] == ["ee", "df", "ce"]
        assert wm["refutation_type"] == "opponent_lives"

    def test_instructiveness_gate_true(self):
        """abs(delta) >= threshold → instructive=True."""
        from config.teaching import TeachingSignalConfig
        resp = self._make_response()
        result = self._make_result_with_refutations()
        cfg = TeachingSignalConfig(instructiveness_threshold=0.05)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        assert payload["wrong_moves"][0]["instructive"] is True
        assert payload["wrong_moves"][0]["seki_exception"] is False

    def test_instructiveness_gate_false(self):
        """abs(delta) < threshold → instructive=False (no seki)."""
        from config.teaching import TeachingSignalConfig
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        resp = self._make_response()  # root_winrate=0.55 → closeness=0.9 (NOT > 0.9)
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(wrong_move="ee", delta=-0.02),
        ]
        cfg = TeachingSignalConfig(instructiveness_threshold=0.05, seki_closeness_threshold=0.95)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        assert payload["wrong_moves"][0]["instructive"] is False

    def test_seki_exception_at_boundary(self):
        """position_closeness > seki_threshold bypasses instructiveness gate."""
        from config.teaching import TeachingSignalConfig
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        # root_winrate=0.50 → closeness=1.0 > 0.9
        resp = self._make_response(root_winrate=0.50)
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(wrong_move="ee", delta=-0.02),
        ]
        cfg = TeachingSignalConfig(instructiveness_threshold=0.05, seki_closeness_threshold=0.9)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        wm = payload["wrong_moves"][0]
        assert wm["instructive"] is True
        assert wm["seki_exception"] is True

    def test_ownership_conditional_emit(self):
        """ownership_delta > threshold → ownership_delta_max emitted."""
        from config.teaching import TeachingSignalConfig
        resp = self._make_response()
        result = self._make_result_with_refutations()  # ownership_delta=0.45
        cfg = TeachingSignalConfig(ownership_delta_threshold=0.3)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        assert "ownership_delta_max" in payload["wrong_moves"][0]
        assert payload["wrong_moves"][0]["ownership_delta_max"] == 0.45

    def test_ownership_conditional_skip(self):
        """ownership_delta <= threshold → ownership_delta_max absent."""
        from config.teaching import TeachingSignalConfig
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        resp = self._make_response()
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(wrong_move="ee", delta=-0.3, ownership_delta=0.1),
        ]
        cfg = TeachingSignalConfig(ownership_delta_threshold=0.3)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=1.0,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        assert "ownership_delta_max" not in payload["wrong_moves"][0]

    def test_board_size_9(self):
        """board_size=9 produces valid SGF↔GTP conversion."""
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        resp = AnalysisResponse(
            request_id="test9",
            move_infos=[MoveAnalysis(move="D4", visits=50, winrate=0.8, score_lead=5.0, policy_prior=0.6)],
            root_winrate=0.6, root_score=3.0, total_visits=50,
        )
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(wrong_move="ee", delta=-0.3, refutation_pv=["ee", "df"]),
        ]
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=0.5,
            correct_move_rank=1, result=result, board_size=9,
        )
        # Should not crash; wrong move GTP conversion should work for 9x9
        assert len(payload["wrong_moves"]) == 1

    def test_max_wrong_moves_cap(self):
        """wrong_moves capped at config.max_wrong_moves."""
        from config.teaching import TeachingSignalConfig
        from models.ai_analysis_result import AiAnalysisResult, RefutationEntry
        resp = self._make_response()
        result = AiAnalysisResult()
        result.refutations = [
            RefutationEntry(wrong_move="ee", delta=-0.3),
            RefutationEntry(wrong_move="cc", delta=-0.2),
            RefutationEntry(wrong_move="ff", delta=-0.1),
        ]
        cfg = TeachingSignalConfig(max_wrong_moves=1)
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=0.5,
            correct_move_rank=1, result=result, board_size=19, config=cfg,
        )
        assert len(payload["wrong_moves"]) == 1

    def test_play_selection_value_present(self):
        """play_selection_value is surfaced in correct_move section."""
        resp = self._make_response()
        payload = build_teaching_signal_payload(
            response=resp, correct_move_gtp="D4", policy_entropy=0.5,
            correct_move_rank=1, board_size=19,
        )
        assert payload["correct_move"]["play_selection_value"] == 0.85


# ---------------------------------------------------------------------------
# T17: AiAnalysisResult serialization with teaching_signals
# ---------------------------------------------------------------------------

class TestAiAnalysisResultTeachingSignals:
    """T17: Verify teaching_signals field on AiAnalysisResult."""

    def test_teaching_signals_default_none(self):
        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult()
        assert result.teaching_signals is None

    def test_teaching_signals_in_json(self):
        """teaching_signals dict round-trips through JSON serialization."""
        import json

        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult()
        result.teaching_signals = {
            "version": 1,
            "correct_move": {"move_gtp": "D4", "log_policy_score": 0.8},
            "position": {"root_winrate": 0.55},
            "wrong_moves": [],
        }
        data = json.loads(result.model_dump_json())
        assert data["teaching_signals"]["version"] == 1
        assert data["teaching_signals"]["correct_move"]["move_gtp"] == "D4"

    def test_teaching_signals_none_in_json(self):
        """teaching_signals=None serializes as null."""
        import json

        from models.ai_analysis_result import AiAnalysisResult
        result = AiAnalysisResult()
        data = json.loads(result.model_dump_json())
        assert data["teaching_signals"] is None

    def test_schema_version_10(self):
        """Schema version is 10 (bumped for teaching_signals)."""
        from models.ai_analysis_result import AI_ANALYSIS_SCHEMA_VERSION, AiAnalysisResult
        assert AI_ANALYSIS_SCHEMA_VERSION == 10
        result = AiAnalysisResult()
        assert result.schema_version == 10
