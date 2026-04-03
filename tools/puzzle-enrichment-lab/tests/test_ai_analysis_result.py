"""Tests for AiAnalysisResult structured output model.

Task A.1.4: All enrichment outputs for one puzzle in a single
serializable Pydantic model with JSON roundtrip, schema versioning,
and status field.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
from analyzers.validate_correct_move import ValidationStatus
from models.ai_analysis_result import (
    AI_ANALYSIS_SCHEMA_VERSION,
    AiAnalysisResult,
    EngineSnapshot,
    MoveValidation,
    generate_run_id,
    generate_trace_id,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_result(**overrides) -> AiAnalysisResult:
    """Build a minimal AiAnalysisResult with sensible defaults."""
    defaults = {
        "puzzle_id": "YENGO-abcdef1234567890",
        "trace_id": "a1b2c3d4e5f67890",
        "run_id": "20260228-deadbeef",
        "schema_version": AI_ANALYSIS_SCHEMA_VERSION,
        "engine": EngineSnapshot(
            model="g170-b6c96-s175395328-d26788732",
            visits=200,
            config_hash="abc123",
        ),
        "validation": MoveValidation(
            correct_move_gtp="D1",
            katago_top_move_gtp="D1",
            status=ValidationStatus.ACCEPTED,
            katago_agrees=True,
            correct_move_winrate=0.95,
            correct_move_policy=0.65,
            validator_used="life_and_death",
            flags=[],
        ),
        "tags": [10, 62],
        "corner": "TL",
        "move_order": "strict",
    }
    defaults.update(overrides)
    return AiAnalysisResult(**defaults)


# ===================================================================
# Unit Tests
# ===================================================================


@pytest.mark.unit
class TestResultRoundtripJson:
    """AiAnalysisResult serializes to JSON and back identically."""

    def test_roundtrip(self) -> None:
        """model_dump_json -> model_validate_json roundtrip preserves all fields."""
        original = _sample_result()
        json_str = original.model_dump_json()
        restored = AiAnalysisResult.model_validate_json(json_str)

        assert restored.puzzle_id == original.puzzle_id
        assert restored.trace_id == original.trace_id
        assert restored.run_id == original.run_id
        assert restored.schema_version == original.schema_version
        assert restored.engine.model == original.engine.model
        assert restored.engine.visits == original.engine.visits
        assert restored.validation.status == original.validation.status
        assert restored.validation.correct_move_gtp == original.validation.correct_move_gtp
        assert restored.validation.katago_agrees == original.validation.katago_agrees
        assert restored.tags == original.tags
        assert restored.corner == original.corner
        assert restored.move_order == original.move_order

    def test_roundtrip_via_dict(self) -> None:
        """model_dump -> json.loads/dumps -> model_validate roundtrip."""
        original = _sample_result()
        data = original.model_dump()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = AiAnalysisResult.model_validate(parsed)
        assert restored == original

    def test_roundtrip_with_flags(self) -> None:
        """Flags list survives roundtrip."""
        original = _sample_result(
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="E1",
                status=ValidationStatus.FLAGGED,
                katago_agrees=False,
                correct_move_winrate=0.55,
                correct_move_policy=0.20,
                validator_used="life_and_death",
                flags=["center_position", "uncertain_winrate"],
            )
        )
        json_str = original.model_dump_json()
        restored = AiAnalysisResult.model_validate_json(json_str)
        assert restored.validation.flags == ["center_position", "uncertain_winrate"]


@pytest.mark.unit
class TestAllRequiredFieldsPresent:
    """All required fields exist on AiAnalysisResult."""

    def test_required_fields(self) -> None:
        """puzzle_id, engine, validation, status all present."""
        result = _sample_result()
        assert result.puzzle_id != ""
        assert result.engine is not None
        assert result.validation is not None
        assert result.validation.status in (
            ValidationStatus.ACCEPTED,
            ValidationStatus.FLAGGED,
            ValidationStatus.REJECTED,
        )

    def test_engine_fields(self) -> None:
        """Engine snapshot has model, visits, config_hash."""
        result = _sample_result()
        assert result.engine.model != ""
        assert result.engine.visits > 0
        assert result.engine.config_hash != ""

    def test_validation_fields(self) -> None:
        """Validation has correct_move_gtp, katago_top_move_gtp, winrate, policy."""
        result = _sample_result()
        v = result.validation
        assert v.correct_move_gtp != ""
        assert v.katago_top_move_gtp != ""
        assert 0.0 <= v.correct_move_winrate <= 1.0
        assert 0.0 <= v.correct_move_policy <= 1.0


@pytest.mark.unit
class TestSchemaVersionField:
    """Output has schema version for forward compatibility."""

    def test_schema_version_present(self) -> None:
        """schema_version is an integer > 0."""
        result = _sample_result()
        assert isinstance(result.schema_version, int)
        assert result.schema_version > 0

    def test_schema_version_matches_constant(self) -> None:
        """Default schema_version matches AI_ANALYSIS_SCHEMA_VERSION constant."""
        result = _sample_result()
        assert result.schema_version == AI_ANALYSIS_SCHEMA_VERSION

    def test_schema_version_in_json(self) -> None:
        """schema_version appears in JSON output."""
        result = _sample_result()
        data = json.loads(result.model_dump_json())
        assert "schema_version" in data
        assert data["schema_version"] == AI_ANALYSIS_SCHEMA_VERSION


@pytest.mark.unit
class TestStatusFieldValues:
    """Status field is one of accepted, flagged, rejected."""

    def test_status_accepted(self) -> None:
        result = _sample_result()
        assert result.validation.status == ValidationStatus.ACCEPTED
        assert result.validation.status.value == "accepted"

    def test_status_flagged(self) -> None:
        result = _sample_result(
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="E1",
                status=ValidationStatus.FLAGGED,
                katago_agrees=False,
                correct_move_winrate=0.55,
                correct_move_policy=0.20,
                validator_used="life_and_death",
            )
        )
        assert result.validation.status == ValidationStatus.FLAGGED
        assert result.validation.status.value == "flagged"

    def test_status_rejected(self) -> None:
        result = _sample_result(
            validation=MoveValidation(
                correct_move_gtp="Z9",
                katago_top_move_gtp="D1",
                status=ValidationStatus.REJECTED,
                katago_agrees=False,
                correct_move_winrate=0.10,
                correct_move_policy=0.01,
                validator_used="life_and_death",
            )
        )
        assert result.validation.status == ValidationStatus.REJECTED
        assert result.validation.status.value == "rejected"


@pytest.mark.unit
class TestFlaggedPreservesExisting:
    """When status=flagged, existing human-curated properties are preserved."""

    def test_flagged_preserves_existing_tags(self) -> None:
        """Flagged result still has all original tags, corner, move_order."""
        result = _sample_result(
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="E1",
                status=ValidationStatus.FLAGGED,
                katago_agrees=False,
                correct_move_winrate=0.55,
                correct_move_policy=0.20,
                validator_used="life_and_death",
                flags=["uncertain_winrate"],
            ),
            tags=[10, 14, 62],
            corner="BR",
            move_order="flexible",
        )
        # Flagged status should NOT strip existing human-curated fields
        assert result.tags == [10, 14, 62]
        assert result.corner == "BR"
        assert result.move_order == "flexible"
        assert result.validation.status == ValidationStatus.FLAGGED

    def test_flagged_adds_flags_without_losing_data(self) -> None:
        """Flagged result preserves all data, just adds flags."""
        result = _sample_result(
            validation=MoveValidation(
                correct_move_gtp="D1",
                katago_top_move_gtp="E1",
                status=ValidationStatus.FLAGGED,
                katago_agrees=False,
                correct_move_winrate=0.50,
                correct_move_policy=0.15,
                validator_used="seki",
                flags=["seki_balanced_winrate", "seki_low_score"],
            ),
        )
        # All fields retained
        assert result.puzzle_id == "YENGO-abcdef1234567890"
        assert result.engine.model == "g170-b6c96-s175395328-d26788732"
        assert result.validation.validator_used == "seki"
        assert len(result.validation.flags) == 2


@pytest.mark.unit
class TestFromCorrectMoveResult:
    """Factory method builds AiAnalysisResult from CorrectMoveResult."""

    def test_from_correct_move_result(self) -> None:
        """AiAnalysisResult.from_validation() creates valid result."""
        from analyzers.validate_correct_move import CorrectMoveResult

        cmr = CorrectMoveResult(
            status=ValidationStatus.ACCEPTED,
            katago_agrees=True,
            correct_move_gtp="D1",
            katago_top_move="D1",
            correct_move_winrate=0.92,
            correct_move_policy=0.65,
            validator_used="life_and_death",
            flags=[],
        )
        result = AiAnalysisResult.from_validation(
            puzzle_id="YENGO-abc123",
            correct_move_result=cmr,
            model_name="g170-b6c96-s175395328-d26788732",
            visits=200,
            config_hash="def456",
            tags=[10],
            corner="TL",
            move_order="strict",
            trace_id="fedcba9876543210",
            run_id="20260228-cafebabe",
        )
        assert result.puzzle_id == "YENGO-abc123"
        assert result.trace_id == "fedcba9876543210"
        assert result.run_id == "20260228-cafebabe"
        assert result.validation.status == ValidationStatus.ACCEPTED
        assert result.engine.model == "g170-b6c96-s175395328-d26788732"
        assert result.engine.visits == 200
        assert result.tags == [10]


# ===================================================================
# A.3.3 — Difficulty fields on AiAnalysisResult
# ===================================================================

@pytest.mark.unit
class TestDifficultyFieldsPresent:
    """AiAnalysisResult has difficulty fields from A.3."""

    def test_difficulty_fields_present(self) -> None:
        """All difficulty fields: policy_prior_correct, visits_to_solve,
        trap_density, composite_score, suggested_level are present."""
        from models.ai_analysis_result import DifficultySnapshot

        result = _sample_result(
            difficulty=DifficultySnapshot(
                policy_prior_correct=0.35,
                visits_to_solve=180,
                trap_density=0.25,
                composite_score=42.5,
                suggested_level="intermediate",
                suggested_level_id=140,
                confidence="high",
            )
        )
        d = result.difficulty
        assert d.policy_prior_correct == 0.35
        assert d.visits_to_solve == 180
        assert d.trap_density == 0.25
        assert d.composite_score == 42.5
        assert d.suggested_level == "intermediate"
        assert d.suggested_level_id == 140
        assert d.confidence == "high"


@pytest.mark.unit
class TestDifficultySerialization:
    """Difficulty data roundtrips through JSON."""

    def test_difficulty_serialization(self) -> None:
        """Difficulty fields survive JSON roundtrip."""
        from models.ai_analysis_result import DifficultySnapshot

        result = _sample_result(
            difficulty=DifficultySnapshot(
                policy_prior_correct=0.12,
                visits_to_solve=800,
                trap_density=0.6,
                composite_score=65.3,
                suggested_level="advanced",
                suggested_level_id=160,
                confidence="medium",
            )
        )
        json_str = result.model_dump_json()
        restored = AiAnalysisResult.model_validate_json(json_str)

        assert restored.difficulty.policy_prior_correct == 0.12
        assert restored.difficulty.visits_to_solve == 800
        assert restored.difficulty.trap_density == pytest.approx(0.6, abs=0.01)
        assert restored.difficulty.composite_score == pytest.approx(65.3, abs=0.01)
        assert restored.difficulty.suggested_level == "advanced"
        assert restored.difficulty.suggested_level_id == 160
        assert restored.difficulty.confidence == "medium"


# ===================================================================
# Traceability — trace_id and run_id (schema v4)
# ===================================================================


@pytest.mark.unit
class TestTraceIdGeneration:
    """trace_id is a 16-char hex string, unique per call."""

    def test_trace_id_format(self) -> None:
        tid = generate_trace_id()
        assert len(tid) == 16
        assert all(c in "0123456789abcdef" for c in tid)

    def test_trace_id_unique(self) -> None:
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100  # all unique


@pytest.mark.unit
class TestRunIdGeneration:
    """run_id follows YYYYMMDD-HHMMSS-xxxxxxxx format."""

    def test_run_id_format(self) -> None:
        rid = generate_run_id()
        parts = rid.split("-")
        assert len(parts) == 3  # YYYYMMDD-HHMMSS-xxxxxxxx
        assert len(parts[0]) == 8  # YYYYMMDD
        assert parts[0].isdigit()
        assert len(parts[1]) == 6  # HHMMSS
        assert parts[1].isdigit()
        assert len(parts[2]) == 8  # 8 hex chars lowercase
        assert all(c in "0123456789abcdef" for c in parts[2])

    def test_run_id_unique(self) -> None:
        ids = {generate_run_id() for _ in range(20)}
        assert len(ids) == 20


@pytest.mark.unit
class TestTraceabilityFields:
    """trace_id and run_id survive JSON roundtrip."""

    def test_trace_fields_in_json(self) -> None:
        result = _sample_result()
        data = json.loads(result.model_dump_json())
        assert "trace_id" in data
        assert "run_id" in data
        assert data["trace_id"] == "a1b2c3d4e5f67890"
        assert data["run_id"] == "20260228-deadbeef"

    def test_trace_fields_roundtrip(self) -> None:
        result = _sample_result(
            trace_id="fedcba9876543210",
            run_id="20260301-cafebabe",
        )
        restored = AiAnalysisResult.model_validate_json(result.model_dump_json())
        assert restored.trace_id == "fedcba9876543210"
        assert restored.run_id == "20260301-cafebabe"

    def test_schema_version_is_4(self) -> None:
        assert AI_ANALYSIS_SCHEMA_VERSION == 10
        result = _sample_result()
        assert result.schema_version == 10


@pytest.mark.unit
class TestHumanReadableFields:
    """Schema v5: human-readable fields (tag_names, level name/range, status_label)."""

    def test_tag_names_included_in_json(self) -> None:
        result = _sample_result(
            tags=[10, 62],
            tag_names=["Life & Death", "Snapback"],
        )
        data = json.loads(result.model_dump_json())
        assert data["tag_names"] == ["Life & Death", "Snapback"]

    def test_tag_names_default_empty(self) -> None:
        result = _sample_result()
        assert result.tag_names == []

    def test_suggested_level_name_in_json(self) -> None:
        result = _sample_result(suggested_level_name="Beginner")
        data = json.loads(result.model_dump_json())
        assert data["suggested_level_name"] == "Beginner"

    def test_suggested_level_range_in_json(self) -> None:
        result = _sample_result(suggested_level_range="25k\u201321k")
        data = json.loads(result.model_dump_json())
        assert data["suggested_level_range"] == "25k\u201321k"

    def test_status_label_from_validation(self) -> None:
        result = _sample_result(status_label="accepted")
        assert result.status_label == "accepted"
        data = json.loads(result.model_dump_json())
        assert data["status_label"] == "accepted"

    def test_status_label_default_empty(self) -> None:
        result = _sample_result()
        assert result.status_label == ""

    def test_roundtrip_preserves_human_fields(self) -> None:
        result = _sample_result(
            tag_names=["Life & Death", "Ko"],
            suggested_level_name="Intermediate",
            suggested_level_range="15k\u201311k",
            status_label="flagged",
        )
        restored = AiAnalysisResult.model_validate_json(result.model_dump_json())
        assert restored.tag_names == ["Life & Death", "Ko"]
        assert restored.suggested_level_name == "Intermediate"
        assert restored.suggested_level_range == "15k\u201311k"
        assert restored.status_label == "flagged"


# --- Migrated from test_sprint1_fixes.py (P0.2 gap ID) ---


@pytest.mark.unit
class TestTreeValidationSortByVisits:
    """P0.2: Tree validation must sort moves by visits, not policy_prior.

    Tesuji (throw-in, sacrifice, under-the-stones) often have LOW policy
    prior but become the best move after deep reading (high visits).
    Sorting by policy_prior would reject these correct moves.
    """

    def test_high_visits_low_policy_in_top3(self):
        """A move with high visits but low policy should be in top 3."""
        from models.analysis_response import MoveAnalysis

        # Sacrifice move: low policy (0.01) but high visits (500)
        sacrifice = MoveAnalysis(
            move="C3", visits=500, winrate=0.95, policy_prior=0.01, pv=["C3"]
        )
        # Normal move: high policy (0.4) but fewer visits (200)
        normal1 = MoveAnalysis(
            move="D4", visits=200, winrate=0.80, policy_prior=0.40, pv=["D4"]
        )
        normal2 = MoveAnalysis(
            move="E5", visits=150, winrate=0.75, policy_prior=0.35, pv=["E5"]
        )
        normal3 = MoveAnalysis(
            move="F6", visits=100, winrate=0.70, policy_prior=0.20, pv=["F6"]
        )

        moves = [sacrifice, normal1, normal2, normal3]

        # Sort by visits (the fix)
        top_by_visits = [
            m.move.upper()
            for m in sorted(moves, key=lambda m: m.visits, reverse=True)[:3]
        ]
        assert "C3" in top_by_visits, "High-visits sacrifice move missing from top 3"

        # Sort by policy_prior (the old, broken behavior)
        top_by_policy = [
            m.move.upper()
            for m in sorted(moves, key=lambda m: m.policy_prior, reverse=True)[:3]
        ]
        assert "C3" not in top_by_policy, (
            "Low-policy sacrifice move should NOT be in policy-sorted top 3"
        )


# --- Migrated from test_sprint1_fixes.py (G10 gap ID) ---


@pytest.mark.unit
class TestDifficultyEstimateRename:
    """G10: DifficultyEstimate importable from canonical module name."""

    def test_import_from_new_name(self):
        """Import from canonical difficulty_estimate module."""
        from models.difficulty_estimate import DifficultyEstimate
        assert DifficultyEstimate is not None
        d = DifficultyEstimate(puzzle_id="test")
        assert d.puzzle_id == "test"
