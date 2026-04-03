"""S.4.1 — Two-population fixture integrity tests.

Ensures calibration and evaluation fixture populations are disjoint,
properly sized, and documented. The two-population split prevents
overfitting: calibration fixtures tune thresholds, evaluation fixtures
measure accuracy independently.

Tests reference tests/fixtures/calibration/ and tests/fixtures/evaluation/.
Run `python scripts/prepare_calibration_fixtures.py` to generate fixtures.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CALIBRATION_DIR = FIXTURES_DIR / "calibration"
EVALUATION_DIR = FIXTURES_DIR / "evaluation"
EXTENDED_BENCHMARK_DIR = FIXTURES_DIR / "extended-benchmark"

# Ground-truth level mapping from Cho Chikun collection directory names
# to expected difficulty range (the pipeline may assign adjacent levels)
COLLECTION_LEVELS = {
    "cho-elementary": "elementary",
    "cho-intermediate": "intermediate",
    "cho-advanced": "advanced",
}

# Minimum evaluation fixture count (S.4.1 requirement: ≥30)
EVALUATION_MINIMUM_COUNT = 30

# Minimum distinct ground-truth levels in evaluation (3 Cho categories)
# Full 9-level coverage requires additional source collections (future work).
EVALUATION_MINIMUM_DISTINCT_LEVELS = 3


def _collect_sgf_names(root: Path) -> set[str]:
    """Recursively collect all SGF filenames under root."""
    return {p.name for p in root.rglob("*.sgf")}


def _read_sgf_root_comment(sgf_path: Path) -> str:
    """Extract root C[] property value from SGF file."""
    text = sgf_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"C\[([^\]]*)\]", text)
    return match.group(1) if match else ""


def _read_sgf_property(sgf_path: Path, prop: str) -> str:
    """Extract a named SGF property value (e.g., PC, YG)."""
    text = sgf_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"{prop}\[([^\]]*)\]", text)
    return match.group(1) if match else ""


class TestNoOverlap:
    """No SGF may appear in both calibration and evaluation populations."""

    def test_no_fixture_in_both_populations(self):
        """Calibration and evaluation must be completely disjoint by filename."""
        if not CALIBRATION_DIR.exists() or not EVALUATION_DIR.exists():
            pytest.skip("Fixture directories not generated (run prepare script)")

        cal_names = _collect_sgf_names(CALIBRATION_DIR)
        eval_names = _collect_sgf_names(EVALUATION_DIR)

        overlap = cal_names & eval_names
        assert overlap == set(), (
            f"Found {len(overlap)} SGF(s) in BOTH populations — "
            f"this invalidates evaluation: {sorted(overlap)[:10]}"
        )


class TestEvaluationCoverage:
    """Evaluation fixtures must span sufficient difficulty levels."""

    def test_evaluation_covers_all_levels(self):
        """Evaluation fixtures span at least 3 distinct ground-truth levels.

        Ground truth is derived from the Cho Chikun collection directory name.
        Full 9-level coverage requires additional source collections and is
        tracked as future work.
        """
        if not EVALUATION_DIR.exists():
            pytest.skip("Evaluation fixtures not generated")

        subdirs = [d for d in EVALUATION_DIR.iterdir() if d.is_dir()]
        levels_found = set()
        for subdir in subdirs:
            sgfs = list(subdir.glob("*.sgf"))
            if sgfs:
                level = COLLECTION_LEVELS.get(subdir.name, subdir.name)
                levels_found.add(level)

        assert len(levels_found) >= EVALUATION_MINIMUM_DISTINCT_LEVELS, (
            f"Evaluation covers only {len(levels_found)} levels "
            f"({sorted(levels_found)}), need ≥{EVALUATION_MINIMUM_DISTINCT_LEVELS}"
        )


class TestEvaluationCount:
    """Evaluation population must meet minimum size requirements."""

    def test_evaluation_minimum_count(self):
        """At least 30 evaluation fixtures exist."""
        if not EVALUATION_DIR.exists():
            pytest.skip("Evaluation fixtures not generated")

        count = len(list(EVALUATION_DIR.rglob("*.sgf")))
        assert count >= EVALUATION_MINIMUM_COUNT, (
            f"Evaluation has {count} SGFs, need ≥{EVALUATION_MINIMUM_COUNT}"
        )


class TestCalibrationDocumented:
    """Each calibration fixture must have documentation for traceability."""

    def test_calibration_fixtures_documented(self):
        """Every calibration SGF has a root C[] comment identifying its source.

        Cho Chikun SGFs use C[Elementary], C[Intermediate], or C[Advanced]
        as the root comment, which serves as the ground-truth label.
        """
        if not CALIBRATION_DIR.exists():
            pytest.skip("Calibration fixtures not generated")

        undocumented = []
        for sgf in sorted(CALIBRATION_DIR.rglob("*.sgf")):
            comment = _read_sgf_root_comment(sgf)
            if not comment.strip():
                undocumented.append(sgf.relative_to(FIXTURES_DIR))

        assert not undocumented, (
            f"{len(undocumented)} calibration fixture(s) lack C[] documentation: "
            f"{[str(p) for p in undocumented[:5]]}"
        )


class TestEvaluationDocumented:
    """Each evaluation fixture must have documentation for traceability."""

    def test_evaluation_fixtures_documented(self):
        """Every evaluation SGF has a root C[] comment identifying its source.

        Cho Chikun SGFs use C[Elementary], C[Intermediate], or C[Advanced]
        as the root comment. This provides the ground-truth difficulty label
        for measuring pipeline accuracy.
        """
        if not EVALUATION_DIR.exists():
            pytest.skip("Evaluation fixtures not generated")

        undocumented = []
        for sgf in sorted(EVALUATION_DIR.rglob("*.sgf")):
            comment = _read_sgf_root_comment(sgf)
            if not comment.strip():
                undocumented.append(sgf.relative_to(FIXTURES_DIR))

        assert not undocumented, (
            f"{len(undocumented)} evaluation fixture(s) lack C[] documentation: "
            f"{[str(p) for p in undocumented[:5]]}"
        )


# Minimum extended-benchmark fixture count (5 techniques × ≈2-3 variants)
EXTENDED_BENCHMARK_MINIMUM_COUNT = 10

# Expected techniques with difficulty-stratified fixtures
EXTENDED_BENCHMARK_TECHNIQUES = {
    "life-and-death",
    "ko",
    "snapback",
    "ladder",
    "nakade",
}


class TestExtendedBenchmarkPopulation:
    """Extended benchmark fixtures provide difficulty-stratified technique coverage."""

    def test_minimum_count(self):
        """At least 10 extended benchmark fixtures exist."""
        if not EXTENDED_BENCHMARK_DIR.exists():
            pytest.skip("Extended benchmark directory not generated")

        count = len(list(EXTENDED_BENCHMARK_DIR.glob("*.sgf")))
        assert count >= EXTENDED_BENCHMARK_MINIMUM_COUNT, (
            f"Extended benchmark has {count} SGFs, "
            f"need ≥{EXTENDED_BENCHMARK_MINIMUM_COUNT}"
        )

    def test_technique_coverage(self):
        """Extended benchmark covers all 5 target techniques."""
        if not EXTENDED_BENCHMARK_DIR.exists():
            pytest.skip("Extended benchmark directory not generated")

        found_techniques = set()
        for sgf_path in EXTENDED_BENCHMARK_DIR.glob("*.sgf"):
            # Naming: {technique}_{level}_{source_id}.sgf
            parts = sgf_path.stem.split("_")
            if len(parts) >= 3:
                # Reconstruct technique slug (may contain hyphens via underscores)
                technique = "-".join(parts[:-2])
                found_techniques.add(technique)

        missing = EXTENDED_BENCHMARK_TECHNIQUES - found_techniques
        assert not missing, (
            f"Extended benchmark missing techniques: {sorted(missing)}"
        )

    def test_has_readme(self):
        """Extended benchmark directory has a README documenting provenance."""
        if not EXTENDED_BENCHMARK_DIR.exists():
            pytest.skip("Extended benchmark directory not generated")

        readme = EXTENDED_BENCHMARK_DIR / "README.md"
        assert readme.exists(), "Extended benchmark missing README.md"
        assert readme.stat().st_size > 100, "Extended benchmark README.md is too short"
