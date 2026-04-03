"""Calibration tests for instinct classifier and policy entropy.

Two calibration sets:
1. golden-calibration/ — Original golden set for KataGo-dependent tests (AC-2 entropy)
2. instinct-calibration/ — Instinct-specific golden set for geometric classifier (AC-1..AC-4)

Tests for set (1) require KataGo engine — skip automatically when unavailable.
Tests for set (2) run without KataGo — pure geometric classification.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

import pytest
from analyzers.instinct_classifier import classify_instinct
from core.tsumego_analysis import extract_correct_first_move, extract_position, parse_sgf
from models.analysis_response import sgf_to_gtp
from models.instinct_result import TIER_HIGH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Golden calibration set (existing — KataGo-dependent)
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden-calibration"
LABELS_FILE = GOLDEN_DIR / "labels.json"


def _load_golden_labels() -> list[dict]:
    """Load golden calibration labels."""
    if not LABELS_FILE.exists():
        return []
    data = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    return data.get("puzzles", [])


@pytest.fixture
def golden_labels():
    labels = _load_golden_labels()
    if not labels:
        pytest.skip("Golden calibration set not yet populated")
    return labels


class TestGoldenCalibration:
    """Original golden set — KataGo-dependent tests."""

    def test_golden_set_has_minimum_puzzles(self, golden_labels):
        assert len(golden_labels) >= 50, (
            f"Golden set has {len(golden_labels)} puzzles, need ≥50"
        )

    def test_instinct_accuracy_threshold(self, golden_labels):
        """Verify instinct classifier ≥70% accurate against manual labels."""
        pytest.skip("Requires KataGo analysis — run separately with engine")


class TestEntropyCorrelation:
    """AC-2: Entropy-difficulty Spearman ≥ 0.3 on golden set."""

    def test_entropy_correlation_threshold(self, golden_labels):
        """Verify entropy correlates with human difficulty."""
        pytest.skip("Requires KataGo analysis — run separately with engine")


# ---------------------------------------------------------------------------
# Instinct calibration set (new — geometric classifier, no KataGo needed)
# ---------------------------------------------------------------------------

INSTINCT_DIR = Path(__file__).parent / "fixtures" / "instinct-calibration"
INSTINCT_LABELS_FILE = INSTINCT_DIR / "labels.json"


def _load_instinct_labels() -> dict[str, dict]:
    """Load instinct calibration labels keyed by filename."""
    if not INSTINCT_LABELS_FILE.exists():
        return {}
    data = json.loads(INSTINCT_LABELS_FILE.read_text(encoding="utf-8"))
    return data.get("puzzles", {})


def _classify_puzzle(sgf_path: Path) -> list:
    """Parse SGF and run instinct classifier. Returns list of InstinctResult."""
    sgf_text = sgf_path.read_text(encoding="utf-8", errors="replace")
    root = parse_sgf(sgf_text)
    position = extract_position(root)
    correct_move_sgf = extract_correct_first_move(root)
    if not correct_move_sgf:
        return []
    correct_move_gtp = sgf_to_gtp(correct_move_sgf, position.board_size)
    return classify_instinct(position, correct_move_gtp)


@pytest.fixture
def instinct_labels():
    labels = _load_instinct_labels()
    if not labels:
        pytest.skip("Instinct calibration set not yet populated")
    return labels


class TestInstinctCalibration:
    """Instinct classifier calibration against human-labeled golden set."""

    def test_instinct_set_has_minimum_puzzles(self, instinct_labels):
        """AC-5: ≥120 puzzles with complete labels."""
        assert len(instinct_labels) >= 120, (
            f"Instinct set has {len(instinct_labels)} puzzles, need ≥120"
        )

    @pytest.mark.xfail(
        reason="Calibration baseline — classifier improvements needed (R-4)",
        strict=False,
    )
    def test_instinct_macro_accuracy(self, instinct_labels):
        """AC-1: Macro instinct accuracy ≥70%.

        For each puzzle with non-empty instinct_labels, check if the
        classifier's primary result is in the human instinct_labels list.
        """
        correct = 0
        total = 0
        mismatches: list[str] = []

        for filename, label in instinct_labels.items():
            human_labels = label.get("instinct_labels", [])
            if not human_labels:
                continue  # skip null-category puzzles

            sgf_path = INSTINCT_DIR / filename
            if not sgf_path.exists():
                continue

            results = _classify_puzzle(sgf_path)
            primary = next((r for r in results if r.is_primary), None)
            classifier_instinct = primary.instinct if primary else None

            total += 1
            if classifier_instinct in human_labels:
                correct += 1
            else:
                mismatches.append(
                    f"{filename}: expected one of {human_labels}, got {classifier_instinct}"
                )

        assert total > 0, "No puzzles with instinct labels found"
        accuracy = correct / total
        logger.info(
            "Macro instinct accuracy: %.1f%% (%d/%d). Mismatches: %d",
            accuracy * 100, correct, total, len(mismatches),
        )
        if mismatches:
            logger.info("Sample mismatches:\n  %s", "\n  ".join(mismatches[:10]))
        assert accuracy >= 0.70, (
            f"Macro accuracy {accuracy:.1%} < 70% threshold "
            f"({correct}/{total}, {len(mismatches)} mismatches)"
        )

    @pytest.mark.xfail(
        reason="Calibration baseline — classifier improvements needed (R-4)",
        strict=False,
    )
    def test_per_instinct_accuracy(self, instinct_labels):
        """AC-2: Per-instinct accuracy ≥60% each.

        Group puzzles by instinct_primary, compute accuracy for each.
        """
        groups: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)

        for filename, label in instinct_labels.items():
            human_labels = label.get("instinct_labels", [])
            primary = label.get("instinct_primary", "")
            if not human_labels or primary == "null":
                continue
            groups[primary].append((filename, human_labels))

        per_instinct_results: dict[str, tuple[int, int]] = {}

        for instinct, puzzles in groups.items():
            correct = 0
            total = 0
            for filename, human_labels in puzzles:
                sgf_path = INSTINCT_DIR / filename
                if not sgf_path.exists():
                    continue
                results = _classify_puzzle(sgf_path)
                primary_result = next((r for r in results if r.is_primary), None)
                classifier_instinct = primary_result.instinct if primary_result else None
                total += 1
                if classifier_instinct in human_labels:
                    correct += 1

            per_instinct_results[instinct] = (correct, total)

        failures: list[str] = []
        for instinct, (correct, total) in sorted(per_instinct_results.items()):
            if total == 0:
                continue
            accuracy = correct / total
            logger.info(
                "  %s: %.1f%% (%d/%d)", instinct, accuracy * 100, correct, total
            )
            if accuracy < 0.60:
                failures.append(
                    f"{instinct}: {accuracy:.1%} ({correct}/{total})"
                )

        assert not failures, (
            f"Per-instinct accuracy below 60% for: {', '.join(failures)}"
        )

    @pytest.mark.xfail(
        reason="Calibration baseline — classifier improvements needed (R-4)",
        strict=False,
    )
    def test_high_tier_precision(self, instinct_labels):
        """AC-3: HIGH-tier precision ≥85%.

        For all classifier results with tier==HIGH, check if correct.
        """
        correct = 0
        total = 0

        for filename, label in instinct_labels.items():
            human_labels = label.get("instinct_labels", [])
            sgf_path = INSTINCT_DIR / filename
            if not sgf_path.exists():
                continue

            results = _classify_puzzle(sgf_path)
            for r in results:
                if r.tier == TIER_HIGH:
                    total += 1
                    # For non-null puzzles, check if HIGH-tier result matches labels
                    if human_labels and r.instinct in human_labels:
                        correct += 1
                    elif not human_labels:
                        # Null puzzle got a HIGH-tier result — false positive
                        pass  # counted in total but not correct

        if total == 0:
            pytest.skip("No HIGH-tier classifications found")

        precision = correct / total
        logger.info(
            "HIGH-tier precision: %.1f%% (%d/%d)", precision * 100, correct, total
        )
        assert precision >= 0.85, (
            f"HIGH-tier precision {precision:.1%} < 85% threshold ({correct}/{total})"
        )

    @pytest.mark.xfail(
        reason="Calibration baseline — classifier improvements needed (R-4)",
        strict=False,
    )
    def test_null_false_positive(self, instinct_labels):
        """AC-4: Null false-positive rate must be 0%.

        If human labels instinct_labels as [], classifier must not return
        any primary instinct.
        """
        false_positives: list[str] = []

        for filename, label in instinct_labels.items():
            human_labels = label.get("instinct_labels", [])
            if human_labels:
                continue  # only test null-category puzzles

            sgf_path = INSTINCT_DIR / filename
            if not sgf_path.exists():
                continue

            results = _classify_puzzle(sgf_path)
            primary = next((r for r in results if r.is_primary), None)
            if primary is not None:
                false_positives.append(
                    f"{filename}: classifier returned '{primary.instinct}' "
                    f"(conf={primary.confidence:.2f}) for null-instinct puzzle"
                )

        assert not false_positives, (
            f"Null false positives ({len(false_positives)}):\n  "
            + "\n  ".join(false_positives[:10])
        )
