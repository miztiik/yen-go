"""Tests for Task A.5.2: SGF patcher.

Takes AiAnalysisResult + original SGF → patches SGF root properties:
  YR (refutations), YG (level), YX (complexity), YQ (quality metrics).

Respects validation status:
  - ACCEPTED → overwrite properties
  - FLAGGED → preserve existing human-curated YG, YT, YH
  - REJECTED → skip patch entirely (return original SGF unchanged)
"""

from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from analyzers.sgf_parser import parse_sgf
from analyzers.sgf_patcher import patch_sgf
from analyzers.validate_correct_move import ValidationStatus
from config import clear_cache
from models.ai_analysis_result import (
    AiAnalysisResult,
    DifficultySnapshot,
    EngineSnapshot,
    MoveValidation,
    RefutationEntry,
)

# Fixture directory
_FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _clear_config_cache():
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _make_accepted_result(
    puzzle_id: str = "test-puzzle",
    refutations: list[RefutationEntry] | None = None,
    level: str = "intermediate",
    level_id: int = 150,
    composite_score: float = 45.0,
    policy_prior: float = 0.15,
    visits_to_solve: int = 120,
    trap_density: float = 0.3,
    confidence: str = "high",
) -> AiAnalysisResult:
    """Build an ACCEPTED AiAnalysisResult for testing."""
    return AiAnalysisResult(
        puzzle_id=puzzle_id,
        engine=EngineSnapshot(model="b10c128.bin.gz", visits=200, config_hash="abc123"),
        validation=MoveValidation(
            correct_move_gtp="D1",
            katago_top_move_gtp="D1",
            status=ValidationStatus.ACCEPTED,
            katago_agrees=True,
            correct_move_winrate=0.95,
            correct_move_policy=policy_prior,
            validator_used="life_and_death",
            flags=[],
        ),
        refutations=refutations or [],
        difficulty=DifficultySnapshot(
            policy_prior_correct=policy_prior,
            visits_to_solve=visits_to_solve,
            trap_density=trap_density,
            composite_score=composite_score,
            suggested_level=level,
            suggested_level_id=level_id,
            confidence=confidence,
        ),
    )


def _make_flagged_result(**kwargs) -> AiAnalysisResult:
    """Build a FLAGGED result."""
    result = _make_accepted_result(**kwargs)
    result.validation.status = ValidationStatus.FLAGGED
    result.validation.katago_agrees = False
    result.validation.flags = ["low_confidence"]
    return result


def _make_rejected_result() -> AiAnalysisResult:
    """Build a REJECTED result."""
    return AiAnalysisResult(
        puzzle_id="test-puzzle",
        validation=MoveValidation(
            status=ValidationStatus.REJECTED,
            flags=["error: SGF parse failure"],
        ),
    )


# ===================================================================
# A.5.2 — Unit Tests
# ===================================================================


@pytest.mark.unit
class TestPatchYrFromRefutations:
    """Refutation entries → YR property set correctly."""

    def test_yr_single_refutation(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(
            refutations=[
                RefutationEntry(wrong_move="cd", refutation_pv=["dc", "dd"], delta=-0.4, refutation_depth=2),
            ],
        )

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        assert root.get("YR") == "cd"

    def test_yr_multiple_refutations(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(
            refutations=[
                RefutationEntry(wrong_move="cd", refutation_pv=["dc"], delta=-0.3, refutation_depth=1),
                RefutationEntry(wrong_move="de", refutation_pv=["ef"], delta=-0.5, refutation_depth=1),
                RefutationEntry(wrong_move="ef", refutation_pv=["fg"], delta=-0.2, refutation_depth=1),
            ],
        )

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        yr = root.get("YR")
        assert yr == "cd,de,ef"

    def test_yr_empty_when_no_refutations(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(refutations=[])

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        # YR should either be absent or empty
        yr = root.get("YR", "")
        assert yr == ""


@pytest.mark.unit
class TestPatchYgFromDifficulty:
    """Difficulty estimation → YG property updated."""

    def test_yg_set_from_difficulty(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(level="elementary", level_id=130)

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        assert root.get("YG") == "elementary"

    def test_yg_overwritten_when_accepted(self):
        """Existing YG is overwritten when status=ACCEPTED."""
        # Build SGF with existing YG
        sgf = _load_fixture("simple_life_death.sgf")
        # Inject YG into the SGF manually
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[novice]")

        result = _make_accepted_result(level="advanced", level_id=160)

        patched = patch_sgf(sgf_with_yg, result)
        root = parse_sgf(patched)
        assert root.get("YG") == "advanced"


@pytest.mark.unit
class TestEnrichIfAbsent:
    """Existing human-curated YG preserved when status=FLAGGED."""

    def test_flagged_preserves_existing_yg(self):
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[beginner]")

        result = _make_flagged_result(level="advanced", level_id=160)

        patched = patch_sgf(sgf_with_yg, result)
        root = parse_sgf(patched)
        # FLAGGED: existing YG preserved
        assert root.get("YG") == "beginner"

    def test_flagged_sets_yg_when_absent(self):
        """FLAGGED with no existing YG → set it (better than nothing)."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_flagged_result(level="advanced", level_id=160)

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        # No existing YG → use the AI suggestion even if flagged
        assert root.get("YG") == "advanced"


@pytest.mark.unit
class TestRoundtripSgfIntegrity:
    """SGF → enrich → patch → parse → all properties correct + structure preserved."""

    def test_roundtrip_preserves_structure(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(
            level="intermediate",
            level_id=150,
            refutations=[
                RefutationEntry(wrong_move="cd", refutation_pv=["dc", "dd"], delta=-0.4, refutation_depth=2),
            ],
        )

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)

        # Original properties preserved
        assert root.get("FF") == "4"
        assert root.get("GM") == "1"
        assert root.get("SZ") == "19"
        assert root.get("PL") == "B"

        # Enrichment properties set
        assert root.get("YG") == "intermediate"
        assert root.get("YR") == "cd"

        # YX should contain depth, refutations, solution_length, unique_responses
        yx = root.get("YX")
        assert yx != ""
        assert "d:" in yx
        assert "r:" in yx

        # Solution tree still valid (first correct move still exists)
        assert root.children  # Has children
        first_child = root.children[0]
        assert first_child.move is not None

    def test_existing_comments_preserved(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result()

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        # Root comment should be preserved
        assert "Kill" in root.get("C")


@pytest.mark.unit
class TestYxEnrichment:
    """Difficulty signals → YX complexity property updated."""

    def test_yx_format(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_accepted_result(
            refutations=[
                RefutationEntry(wrong_move="cd", refutation_pv=["dc", "dd"], delta=-0.4, refutation_depth=2),
                RefutationEntry(wrong_move="de", refutation_pv=["ef"], delta=-0.3, refutation_depth=1),
            ],
        )

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        yx = root.get("YX")
        # Format: d:{depth};r:{refutation_count};s:{solution_length};u:{unique_responses}
        assert yx.startswith("d:")
        assert ";r:2" in yx  # 2 refutations
        assert ";s:" in yx
        assert ";u:" in yx


@pytest.mark.unit
class TestFlaggedPreservesProperties:
    """status=FLAGGED → existing YG, YT, YH preserved."""

    def test_flagged_preserves_yt(self):
        sgf = _load_fixture("simple_life_death.sgf")
        # SGF now has YT[life-and-death] (added to fixture)
        result = _make_flagged_result()

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        assert root.get("YT") == "life-and-death"

    def test_flagged_still_sets_yr_and_yx(self):
        """FLAGGED still writes YR and YX (engine-derived, not human-curated)."""
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_flagged_result(
            refutations=[
                RefutationEntry(wrong_move="cd", refutation_pv=["dc"], delta=-0.3, refutation_depth=1),
            ],
        )

        patched = patch_sgf(sgf, result)
        root = parse_sgf(patched)
        # YR and YX are engine-derived, always written
        assert root.get("YR") == "cd"
        assert root.get("YX") != ""


@pytest.mark.unit
class TestRejectedSkipsPatch:
    """status=REJECTED → SGF not modified at all."""

    def test_rejected_returns_original(self):
        sgf = _load_fixture("simple_life_death.sgf")
        result = _make_rejected_result()

        patched = patch_sgf(sgf, result)
        # Must return exactly the same string
        assert patched == sgf

    def test_rejected_with_existing_props(self):
        sgf = _load_fixture("simple_life_death.sgf")
        sgf_with_yg = sgf.replace("PL[B]", "PL[B]YG[novice]")
        result = _make_rejected_result()

        patched = patch_sgf(sgf_with_yg, result)
        assert patched == sgf_with_yg
