"""Tests for per-puzzle diagnostic model and batch aggregation (G10, AC-15, AC-16).

T20: PuzzleDiagnostic model serialization
T21: Batch diagnostic output via BatchSummaryAccumulator
"""

import json
from pathlib import Path

import pytest

_LAB = Path(__file__).resolve().parent.parent

from models.diagnostic import PuzzleDiagnostic

# ---------------------------------------------------------------------------
# T20: PuzzleDiagnostic model serialization (AC-15)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPuzzleDiagnosticModel:
    """AC-15: PuzzleDiagnostic serialization and default values."""

    def test_default_instantiation(self):
        diag = PuzzleDiagnostic()
        assert diag.puzzle_id == ""
        assert diag.qk_score == 0
        assert diag.ac_level == 0
        assert diag.enrichment_tier == 0
        assert diag.stages_run == []
        assert diag.stages_skipped == []
        assert diag.signals_computed == {}
        assert diag.errors == []
        assert diag.warnings == []
        assert diag.goal_agreement == "unknown"

    def test_json_serialization_roundtrip(self):
        diag = PuzzleDiagnostic(
            puzzle_id="abc123",
            source_file="test.sgf",
            timestamp="2026-03-18T00:00:00Z",
            stages_run=["parse_sgf", "analyze", "validate"],
            stages_skipped=["teaching"],
            signals_computed={"policy_entropy": 0.42, "correct_move_rank": 1},
            goal_stated="kill",
            goal_inferred="kill",
            goal_agreement="match",
            errors=[],
            warnings=["validation_flag: center_position"],
            phase_timings={"parse_sgf": 0.1, "analyze": 1.5},
            qk_score=3,
            ac_level=2,
            enrichment_tier=3,
        )
        json_str = diag.model_dump_json()
        parsed = json.loads(json_str)

        # All fields present
        assert parsed["puzzle_id"] == "abc123"
        assert parsed["source_file"] == "test.sgf"
        assert parsed["stages_run"] == ["parse_sgf", "analyze", "validate"]
        assert parsed["stages_skipped"] == ["teaching"]
        assert parsed["signals_computed"] == {"policy_entropy": 0.42, "correct_move_rank": 1}
        assert parsed["goal_agreement"] == "match"
        assert parsed["qk_score"] == 3
        assert parsed["ac_level"] == 2
        assert parsed["enrichment_tier"] == 3
        assert parsed["warnings"] == ["validation_flag: center_position"]

        # Roundtrip
        restored = PuzzleDiagnostic.model_validate(parsed)
        assert restored == diag

    def test_all_fields_present_in_json(self):
        diag = PuzzleDiagnostic()
        data = diag.model_dump()
        expected_fields = {
            "puzzle_id", "source_file", "timestamp",
            "stages_run", "stages_skipped", "signals_computed",
            "goal_stated", "goal_inferred", "goal_agreement",
            "disagreements", "errors", "warnings",
            "phase_timings", "qk_score", "ac_level", "enrichment_tier",
        }
        assert expected_fields.issubset(set(data.keys()))

    def test_qk_score_bounds(self):
        diag = PuzzleDiagnostic(qk_score=5)
        assert diag.qk_score == 5

        with pytest.raises(Exception):
            PuzzleDiagnostic(qk_score=6)

        with pytest.raises(Exception):
            PuzzleDiagnostic(qk_score=-1)

    def test_ac_level_bounds(self):
        diag = PuzzleDiagnostic(ac_level=3)
        assert diag.ac_level == 3

        with pytest.raises(Exception):
            PuzzleDiagnostic(ac_level=4)

    def test_enrichment_tier_bounds(self):
        diag = PuzzleDiagnostic(enrichment_tier=3)
        assert diag.enrichment_tier == 3

        with pytest.raises(Exception):
            PuzzleDiagnostic(enrichment_tier=4)


# ---------------------------------------------------------------------------
# T20: build_diagnostic_from_result
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildDiagnosticFromResult:
    """Test diagnostic builder from AiAnalysisResult."""

    def test_build_from_result_basic(self):
        from analyzers.enrich_single import build_diagnostic_from_result
        from models.ai_analysis_result import AiAnalysisResult

        result = AiAnalysisResult(
            puzzle_id="test-001",
            source_file="test.sgf",
            ac_level=1,
            enrichment_tier=3,
            goal="kill",
            phase_timings={"parse_sgf": 0.05, "analyze": 1.2},
        )
        result.difficulty.policy_entropy = 0.55
        result.difficulty.correct_move_rank = 2

        diag = build_diagnostic_from_result(result)
        assert diag.puzzle_id == "test-001"
        assert diag.ac_level == 1
        assert diag.enrichment_tier == 3
        assert diag.goal_inferred == "kill"
        assert diag.goal_agreement == "inferred"
        assert "policy_entropy" in diag.signals_computed
        assert "correct_move_rank" in diag.signals_computed
        assert "parse_sgf" in diag.stages_run
        assert "analyze" in diag.stages_run
        assert diag.timestamp  # non-empty

    def test_build_from_result_unknown_goal(self):
        from analyzers.enrich_single import build_diagnostic_from_result
        from models.ai_analysis_result import AiAnalysisResult

        result = AiAnalysisResult(goal="unknown")
        diag = build_diagnostic_from_result(result)
        assert diag.goal_agreement == "unknown"

    def test_build_from_result_with_validation_flags(self):
        from analyzers.enrich_single import build_diagnostic_from_result
        from models.ai_analysis_result import AiAnalysisResult

        result = AiAnalysisResult()
        result.validation.flags = ["center_position", "ko_pending"]
        diag = build_diagnostic_from_result(result)
        assert len(diag.warnings) == 2
        assert "validation_flag: center_position" in diag.warnings


# ---------------------------------------------------------------------------
# T21: Batch diagnostic aggregation (AC-16)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchDiagnosticAggregation:
    """AC-16: BatchSummaryAccumulator aggregates per-puzzle diagnostics."""

    def test_record_single_diagnostic(self):
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-run")
        diag = PuzzleDiagnostic(
            puzzle_id="p1",
            qk_score=3,
            ac_level=2,
            goal_agreement="match",
        )
        acc.record_diagnostic(diag)

        assert acc.diagnostic_count == 1
        assert acc.diagnostic_error_count == 0
        assert acc.diagnostic_qk_scores == [3]

    def test_record_multiple_diagnostics(self):
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-run")
        for i, (qk, ac, ga) in enumerate([
            (2, 1, "match"),
            (4, 2, "mismatch"),
            (0, 0, "unknown"),
        ]):
            diag = PuzzleDiagnostic(
                puzzle_id=f"p{i}",
                qk_score=qk,
                ac_level=ac,
                goal_agreement=ga,
            )
            acc.record_diagnostic(diag)

        assert acc.diagnostic_count == 3
        assert acc.diagnostic_qk_scores == [2, 4, 0]

    def test_diagnostic_error_counting(self):
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-run")
        # Diagnostic with errors
        diag_err = PuzzleDiagnostic(
            puzzle_id="p1",
            errors=["parse failed"],
        )
        # Diagnostic without errors
        diag_ok = PuzzleDiagnostic(puzzle_id="p2")

        acc.record_diagnostic(diag_err)
        acc.record_diagnostic(diag_ok)

        assert acc.diagnostic_count == 2
        assert acc.diagnostic_error_count == 1

    def test_diagnostic_goal_agreement_tracking(self):
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-run")
        acc.record_diagnostic(PuzzleDiagnostic(goal_agreement="match"))
        acc.record_diagnostic(PuzzleDiagnostic(goal_agreement="match"))
        acc.record_diagnostic(PuzzleDiagnostic(goal_agreement="mismatch"))

        # Goal agreement counters are tracked via existing fields
        assert acc._goal_agreement_matches == 2
        assert acc._goal_agreement_mismatches == 1

    def test_diagnostic_and_record_puzzle_coexist(self):
        """Diagnostics and record_puzzle can be used together."""
        from analyzers.observability import BatchSummaryAccumulator

        acc = BatchSummaryAccumulator(batch_id="test-run")
        acc.record_puzzle(has_solution=True, ac_level=1)
        acc.record_diagnostic(PuzzleDiagnostic(puzzle_id="p1", qk_score=3))

        assert acc.diagnostic_count == 1
        summary = acc.emit()
        assert summary.total_puzzles == 1  # record_puzzle count
        assert acc.diagnostic_count == 1   # diagnostic count independent
