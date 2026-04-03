#!/usr/bin/env python3
"""Measure enrichment quality against known collection ground truth.

Reads calibration results from one or more run directories and produces
an objective quality scorecard. For known collections (e.g. Cho Chikun
Elementary/Intermediate/Advanced), compares assigned difficulty levels
against expected ranges.

Usage:
    python scripts/measure_enrichment_quality.py \
        --results-dir .lab-runtime/calibration-results/v126-cho-elementary \
        --results-dir .lab-runtime/calibration-results/v126-cho-elementary-retry \
        --expected-level novice,beginner,elementary \
        --collection "Cho L&D Elementary"

    # Compare two config versions:
    python scripts/measure_enrichment_quality.py \
        --results-dir .lab-runtime/calibration-results/v125-cho-elementary \
        --compare-dir .lab-runtime/calibration-results/v126-cho-elementary \
        --expected-level novice,beginner,elementary

Output:
    Console scorecard with pass/fail quality gates and detailed metrics.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PuzzleResult:
    """Enrichment result for a single puzzle."""

    filename: str
    status: str  # accepted, flagged, rejected, error
    level: str
    level_id: int
    score: float
    solution_depth: int
    policy_prior: float
    refutation_count: int
    katago_agrees: bool
    confidence: str
    goal: str
    enrichment_quality: int
    hints_count: int
    technique_tags: list[str] = field(default_factory=list)


@dataclass
class QualityScorecard:
    """Aggregate quality metrics for a calibration run."""

    collection: str
    total_puzzles: int
    enriched: int
    accepted: int
    flagged: int
    rejected: int
    katago_agreement_rate: float
    level_accuracy: float  # % in expected range
    outliers: list[tuple[str, str, float]]  # (file, level, score)
    avg_score: float
    median_score: float
    score_range: tuple[float, float]
    avg_depth: float
    avg_policy: float
    high_policy_rate: float  # % with policy > 0.5
    avg_refutations: float
    hints_rate: float  # % with hints
    goal_detection_rate: float
    enrichment_quality_avg: float
    level_distribution: dict[str, int]

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.enriched * 100 if self.enriched else 0

    @property
    def overall_grade(self) -> str:
        """Compute overall grade A-F based on quality gates."""
        score = 0
        # Weight: acceptance rate (25%), level accuracy (25%),
        # KataGo agreement (20%), hints (15%), goal detection (15%)
        score += min(self.acceptance_rate / 100, 1.0) * 25
        score += min(self.level_accuracy / 100, 1.0) * 25
        score += min(self.katago_agreement_rate / 100, 1.0) * 20
        score += min(self.hints_rate / 100, 1.0) * 15
        score += min(self.goal_detection_rate / 100, 1.0) * 15
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"


def load_results(*dirs: Path) -> list[PuzzleResult]:
    """Load and merge results from multiple directories.

    If the same puzzle appears in multiple dirs, the later dir wins
    (allows merging initial run + retry).
    """
    merged: dict[str, dict] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            if f.name.startswith("_"):
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            score = data.get("difficulty", {}).get("composite_score", 0)
            if score > 0:
                merged[f.name] = data
            elif f.name not in merged:
                merged[f.name] = data  # Keep failed entries for counting

    results = []
    for fname in sorted(merged):
        data = merged[fname]
        diff = data.get("difficulty", {})
        val = data.get("validation", {})
        score = diff.get("composite_score", 0)
        if score <= 0:
            continue  # Skip truly failed results
        results.append(PuzzleResult(
            filename=fname,
            status=val.get("status", "unknown"),
            level=diff.get("suggested_level", "unknown"),
            level_id=diff.get("suggested_level_id", 0),
            score=score,
            solution_depth=diff.get("solution_depth", 0),
            policy_prior=diff.get("policy_prior_correct", 0),
            refutation_count=len(data.get("refutations", [])),
            katago_agrees=val.get("katago_agrees", False),
            confidence=diff.get("confidence", "unknown"),
            goal=data.get("goal", ""),
            enrichment_quality=data.get("enrichment_quality_level", 0),
            hints_count=len(data.get("hints", [])),
            technique_tags=data.get("technique_tags", []),
        ))
    return results


def compute_scorecard(
    results: list[PuzzleResult],
    expected_levels: set[str],
    collection: str,
    total_fixtures: int = 30,
) -> QualityScorecard:
    """Compute quality scorecard from enrichment results."""
    enriched = len(results)
    accepted = sum(1 for r in results if r.status == "accepted")
    flagged = sum(1 for r in results if r.status == "flagged")
    rejected = sum(1 for r in results if r.status == "rejected")

    in_range = sum(1 for r in results if r.level in expected_levels)
    outliers = [(r.filename, r.level, r.score) for r in results if r.level not in expected_levels]

    scores = [r.score for r in results]
    sorted_scores = sorted(scores)

    return QualityScorecard(
        collection=collection,
        total_puzzles=total_fixtures,
        enriched=enriched,
        accepted=accepted,
        flagged=flagged,
        rejected=rejected,
        katago_agreement_rate=sum(1 for r in results if r.katago_agrees) / enriched * 100 if enriched else 0,
        level_accuracy=in_range / enriched * 100 if enriched else 0,
        outliers=outliers,
        avg_score=sum(scores) / enriched if enriched else 0,
        median_score=sorted_scores[enriched // 2] if enriched else 0,
        score_range=(min(scores), max(scores)) if scores else (0, 0),
        avg_depth=sum(r.solution_depth for r in results) / enriched if enriched else 0,
        avg_policy=sum(r.policy_prior for r in results) / enriched if enriched else 0,
        high_policy_rate=sum(1 for r in results if r.policy_prior > 0.5) / enriched * 100 if enriched else 0,
        avg_refutations=sum(r.refutation_count for r in results) / enriched if enriched else 0,
        hints_rate=sum(1 for r in results if r.hints_count > 0) / enriched * 100 if enriched else 0,
        goal_detection_rate=sum(1 for r in results if r.goal) / enriched * 100 if enriched else 0,
        enrichment_quality_avg=sum(r.enrichment_quality for r in results) / enriched if enriched else 0,
        level_distribution=dict(Counter(r.level for r in results)),
    )


def format_scorecard(sc: QualityScorecard) -> str:
    """Format scorecard as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  ENRICHMENT QUALITY SCORECARD — {sc.collection.upper()}")
    lines.append(f"  Overall Grade: {sc.overall_grade}")
    lines.append("=" * 70)
    lines.append("")

    # Quality gates
    lines.append("  QUALITY GATES")
    lines.append("  " + "-" * 55)

    def gate(name: str, value: float, threshold: float, unit: str = "%") -> str:
        passed = value >= threshold
        icon = "PASS" if passed else "FAIL"
        return f"  [{icon}] {name:<30s} {value:6.1f}{unit}  (threshold: {threshold}{unit})"

    lines.append(gate("Acceptance Rate", sc.acceptance_rate, 80))
    lines.append(gate("Level Accuracy", sc.level_accuracy, 90))
    lines.append(gate("KataGo Agreement", sc.katago_agreement_rate, 75))
    lines.append(gate("Hint Coverage", sc.hints_rate, 90))
    lines.append(gate("Goal Detection", sc.goal_detection_rate, 90))
    lines.append(gate("Enrichment Quality", sc.enrichment_quality_avg, 2, " "))
    lines.append("")

    # Summary
    lines.append("  SUMMARY")
    lines.append("  " + "-" * 55)
    lines.append(f"  Total fixtures:     {sc.total_puzzles}")
    lines.append(f"  Enriched:           {sc.enriched}/{sc.total_puzzles} ({sc.enriched/sc.total_puzzles*100:.0f}%)")
    lines.append(f"  Accepted:           {sc.accepted}")
    lines.append(f"  Flagged:            {sc.flagged}")
    lines.append(f"  Rejected:           {sc.rejected}")
    lines.append("")

    # Difficulty
    lines.append("  DIFFICULTY DISTRIBUTION")
    lines.append("  " + "-" * 55)
    for lvl in ["novice", "beginner", "elementary", "intermediate",
                 "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"]:
        count = sc.level_distribution.get(lvl, 0)
        if count > 0:
            bar = "#" * count
            pct = count / sc.enriched * 100
            lines.append(f"  {lvl:>20s}: {count:3d} ({pct:4.1f}%) {bar}")
    lines.append("")

    if sc.outliers:
        lines.append("  OUTLIERS (outside expected range)")
        lines.append("  " + "-" * 55)
        for fname, level, score in sc.outliers:
            lines.append(f"    {fname:<20s} -> {level} (score={score:.1f})")
        lines.append("")

    # Metrics
    lines.append("  DETAILED METRICS")
    lines.append("  " + "-" * 55)
    lines.append(f"  Score:     min={sc.score_range[0]:.1f}  max={sc.score_range[1]:.1f}  avg={sc.avg_score:.1f}  median={sc.median_score:.1f}")
    lines.append(f"  Depth:     avg={sc.avg_depth:.1f}")
    lines.append(f"  Policy:    avg={sc.avg_policy:.4f}  (>{'.'}5: {sc.high_policy_rate:.0f}%)")
    lines.append(f"  Refutations: avg={sc.avg_refutations:.1f}")
    lines.append(f"  Hints:     {sc.hints_rate:.0f}% coverage")
    lines.append(f"  EQ Level:  avg={sc.enrichment_quality_avg:.1f}")
    lines.append("")

    lines.append("  " + "=" * 55)
    return "\n".join(lines)


def format_comparison(sc_a: QualityScorecard, sc_b: QualityScorecard, label_a: str, label_b: str) -> str:
    """Format side-by-side comparison of two scorecards."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  COMPARISON: {label_a} vs {label_b}")
    lines.append("=" * 70)
    lines.append("")

    def cmp(name: str, val_a: float, val_b: float, fmt: str = ".1f", higher_better: bool = True) -> str:
        delta = val_b - val_a
        direction = "+" if delta > 0 else ""
        color = "better" if (delta > 0) == higher_better else "worse" if delta != 0 else "same"
        return f"  {name:<25s} {val_a:{fmt}}  ->  {val_b:{fmt}}  ({direction}{delta:{fmt}}) [{color}]"

    lines.append("  METRIC                    " + f"{label_a:<8s}    {label_b:<8s}    CHANGE")
    lines.append("  " + "-" * 60)
    lines.append(cmp("Acceptance Rate %", sc_a.acceptance_rate, sc_b.acceptance_rate))
    lines.append(cmp("Level Accuracy %", sc_a.level_accuracy, sc_b.level_accuracy))
    lines.append(cmp("KataGo Agreement %", sc_a.katago_agreement_rate, sc_b.katago_agreement_rate))
    lines.append(cmp("Avg Score", sc_a.avg_score, sc_b.avg_score))
    lines.append(cmp("Avg Depth", sc_a.avg_depth, sc_b.avg_depth))
    lines.append(cmp("Avg Policy Prior", sc_a.avg_policy, sc_b.avg_policy, ".4f"))
    lines.append(cmp("Avg Refutations", sc_a.avg_refutations, sc_b.avg_refutations))
    lines.append(cmp("Hints Coverage %", sc_a.hints_rate, sc_b.hints_rate))
    lines.append(cmp("EQ Level", sc_a.enrichment_quality_avg, sc_b.enrichment_quality_avg))
    lines.append(cmp("Overall Grade", ord(sc_a.overall_grade), ord(sc_b.overall_grade), ".0f", higher_better=False))

    lines.append("")

    # Level distribution comparison
    all_levels = sorted(set(list(sc_a.level_distribution.keys()) + list(sc_b.level_distribution.keys())),
                        key=lambda x: ["novice", "beginner", "elementary", "intermediate",
                                       "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"].index(x)
                        if x in ["novice", "beginner", "elementary", "intermediate",
                                 "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"] else 99)
    lines.append("  LEVEL DISTRIBUTION")
    lines.append("  " + "-" * 60)
    for lvl in all_levels:
        a = sc_a.level_distribution.get(lvl, 0)
        b = sc_b.level_distribution.get(lvl, 0)
        delta = b - a
        direction = "+" if delta > 0 else ""
        lines.append(f"  {lvl:>20s}: {a:3d} -> {b:3d}  ({direction}{delta})")

    lines.append("")
    lines.append("  " + "=" * 55)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Measure enrichment quality")
    parser.add_argument(
        "--results-dir", action="append", required=True,
        help="Path to calibration results directory (can repeat for multiple runs)"
    )
    parser.add_argument(
        "--compare-dir", action="append", default=None,
        help="Path to comparison results (e.g. previous config version)"
    )
    parser.add_argument(
        "--expected-level", default="novice,beginner,elementary",
        help="Comma-separated list of expected difficulty levels"
    )
    parser.add_argument(
        "--collection", default="Cho L&D Elementary",
        help="Collection name for display"
    )
    parser.add_argument(
        "--total-fixtures", type=int, default=30,
        help="Total number of fixture puzzles in the collection"
    )
    parser.add_argument(
        "--output", default="",
        help="Write scorecard to file (in addition to stdout)"
    )
    args = parser.parse_args()

    expected = set(args.expected_level.split(","))
    result_dirs = [Path(d) for d in args.results_dir]
    results = load_results(*result_dirs)

    if not results:
        print("No successful results found.")
        return 1

    sc = compute_scorecard(results, expected, args.collection, args.total_fixtures)
    report = format_scorecard(sc)
    print(report)

    # Compare mode
    if args.compare_dir:
        compare_dirs = [Path(d) for d in args.compare_dir]
        compare_results = load_results(*compare_dirs)
        if compare_results:
            sc_cmp = compute_scorecard(compare_results, expected, args.collection, args.total_fixtures)
            comparison = format_comparison(sc_cmp, sc, "compare", "current")
            print()
            print(comparison)
            report += "\n\n" + comparison

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\nReport written to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
