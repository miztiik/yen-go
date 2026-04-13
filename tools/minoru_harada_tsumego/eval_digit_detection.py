"""Evaluation framework for digit detection accuracy.

Runs the OpenCV digit detector against a ground truth dataset,
records versioned results, and provides comparison views.

Usage (via CLI):
    python -m tools.minoru_harada_tsumego eval
    python -m tools.minoru_harada_tsumego eval --compare
    python -m tools.minoru_harada_tsumego eval --run-id v1.0_baseline
"""

from __future__ import annotations

import datetime
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from tools.core.image_to_board import (
    BLACK,
    WHITE,
    detect_digit,
    recognize_position,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DigitResult:
    """Result of a single digit detection test."""

    image_id: str
    iy: int
    ix: int
    color: str
    expected: int
    detected: int
    confidence: float = 0.0
    method: str = ""
    rule_name: str = ""
    runner_up: int = 0
    features: dict = field(default_factory=dict)

    @property
    def correct(self) -> bool:
        return self.expected == self.detected


@dataclass
class ImageResult:
    """Aggregate result for one ground-truth image."""

    image_id: str
    total: int
    correct: int
    failures: list[dict]


@dataclass
class EvalResult:
    """Full evaluation run result."""

    total_digits: int = 0
    correct: int = 0
    digit_results: list[DigitResult] = field(default_factory=list)
    per_image: list[ImageResult] = field(default_factory=list)
    confusion: Counter = field(default_factory=Counter)
    elapsed_ms: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total_digits if self.total_digits > 0 else 0.0


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------


def run_eval(
    ground_truth_path: Path,
    image_base_dir: Path,
    templates: dict[int, "np.ndarray"] | None = None,
    image_filter: set[str] | None = None,
) -> EvalResult:
    """Run digit detection against the ground truth dataset.

    Args:
        ground_truth_path: Path to ground_truth.json.
        image_base_dir: Directory containing _images/ subdirectory.
        templates: Optional templates dict to inject (for cross-validation).
            If None, uses the globally cached templates.
        image_filter: If set, only evaluate images whose id is in this set.

    Returns:
        EvalResult with per-digit and per-image accuracy.
    """
    with open(ground_truth_path, encoding="utf-8") as f:
        gt = json.load(f)

    result = EvalResult()
    t0 = time.perf_counter()

    for img_entry in gt["images"]:
        image_id = img_entry["id"]

        # Filter to specific images if requested
        if image_filter is not None and image_id not in image_filter:
            continue

        problem_path = image_base_dir / img_entry["problem_path"]
        answer_path = image_base_dir / img_entry["answer_path"]

        if not problem_path.exists() or not answer_path.exists():
            print(f"  SKIP {image_id}: missing image files")
            continue

        # Recognize both positions
        problem_pos = recognize_position(str(problem_path))
        answer_pos = recognize_position(str(answer_path))

        # Open answer image for digit detection
        answer_img = Image.open(str(answer_path)).convert("RGB")

        # Detect new stones (answer - problem diff)
        n_rows = min(len(problem_pos.board), len(answer_pos.board))
        new_stones: dict[tuple[int, int], str] = {}
        for iy in range(n_rows):
            n_cols = min(len(problem_pos.board[iy]), len(answer_pos.board[iy]))
            for ix in range(n_cols):
                p_cell = problem_pos.board[iy][ix]
                a_cell = answer_pos.board[iy][ix]
                if p_cell != a_cell and a_cell in (BLACK, WHITE):
                    new_stones[(iy, ix)] = a_cell

        # Test each ground truth digit
        image_correct = 0
        image_total = 0
        image_failures: list[dict] = []

        for digit_entry in img_entry["digits"]:
            iy = digit_entry["iy"]
            ix = digit_entry["ix"]
            expected = digit_entry["expected"]
            color = digit_entry["color"]

            # Get pixel coordinates from answer grid
            if iy < len(answer_pos.grid.y_lines) and ix < len(answer_pos.grid.x_lines):
                cy = answer_pos.grid.y_lines[iy]
                cx = answer_pos.grid.x_lines[ix]
                det_result = detect_digit(answer_img, cx, cy, color, templates=templates)
                detected = det_result.digit
                confidence = det_result.confidence
                method = det_result.method
                rule_name = det_result.rule_name
                runner_up = det_result.runner_up
                features = det_result.features
            else:
                detected = 0
                confidence = 0.0
                method = "out_of_bounds"
                rule_name = ""
                runner_up = 0
                features = {}

            dr = DigitResult(
                image_id=image_id,
                iy=iy, ix=ix,
                color=color,
                expected=expected,
                detected=detected,
                confidence=confidence,
                method=method,
                rule_name=rule_name,
                runner_up=runner_up,
                features=features,
            )
            result.digit_results.append(dr)
            image_total += 1

            if dr.correct:
                image_correct += 1
            else:
                result.confusion[f"{expected}->{detected}"] += 1
                image_failures.append({
                    "expected": expected,
                    "detected": detected,
                    "iy": iy,
                    "ix": ix,
                    "color": color,
                    "confidence": round(confidence, 4),
                    "method": method,
                    "rule_name": rule_name,
                    "runner_up": runner_up,
                    "features": {k: v for k, v in features.items()
                                 if k not in ("zones", "d1", "d2")},
                })

        result.per_image.append(ImageResult(
            image_id=image_id,
            total=image_total,
            correct=image_correct,
            failures=image_failures,
        ))
        result.total_digits += image_total
        result.correct += image_correct

    result.elapsed_ms = (time.perf_counter() - t0) * 1000
    return result


# ---------------------------------------------------------------------------
# Leave-One-Image-Out Cross-Validation
# ---------------------------------------------------------------------------


@dataclass
class CVResult:
    """Result of leave-one-image-out cross-validation."""

    total_digits: int = 0
    correct: int = 0
    per_fold: list[ImageResult] = field(default_factory=list)
    confusion: Counter = field(default_factory=Counter)
    elapsed_ms: float = 0.0
    digit_results: list[DigitResult] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total_digits if self.total_digits > 0 else 0.0


def run_eval_cv(ground_truth_path: Path, image_base_dir: Path) -> CVResult:
    """Run leave-one-image-out cross-validation.

    For each of the N ground truth images:
      1. Build templates from the other N-1 images
      2. Test the held-out image using those templates
      3. Record per-digit results

    This measures true generalization — each digit is tested with
    templates it never contributed to.

    Returns:
        CVResult with per-fold breakdown and aggregate CV accuracy.
    """
    from tools.minoru_harada_tsumego.extract_templates import build_templates_excluding

    with open(ground_truth_path, encoding="utf-8") as f:
        gt = json.load(f)

    # Only CV over training images (not holdout group)
    train_images = [
        img for img in gt["images"]
        if img.get("group") != "holdout"
    ]

    cv_result = CVResult()
    t0 = time.perf_counter()

    for fold_idx, held_out in enumerate(train_images):
        held_out_id = held_out["id"]
        print(f"  Fold {fold_idx + 1}/{len(train_images)}: hold out {held_out_id}")

        # Build templates excluding this image
        fold_templates = build_templates_excluding(
            ground_truth_path, image_base_dir, held_out_id,
        )

        # Evaluate only the held-out image using these templates
        fold_result = run_eval(
            ground_truth_path, image_base_dir,
            templates=fold_templates,
            image_filter={held_out_id},
        )

        # Merge into overall CV result
        cv_result.total_digits += fold_result.total_digits
        cv_result.correct += fold_result.correct
        cv_result.confusion.update(fold_result.confusion)
        cv_result.digit_results.extend(fold_result.digit_results)

        for ir in fold_result.per_image:
            cv_result.per_fold.append(ir)

    cv_result.elapsed_ms = (time.perf_counter() - t0) * 1000
    return cv_result


def show_cv_detail(cv_result: CVResult) -> None:
    """Print detailed cross-validation results."""
    print(f"\nLeave-One-Image-Out Cross-Validation")
    print(f"{'=' * 60}")
    print(f"Total digits: {cv_result.total_digits}")
    print(f"Correct:      {cv_result.correct}")
    print(f"CV Accuracy:  {cv_result.accuracy * 100:.1f}%")
    print(f"Elapsed:      {cv_result.elapsed_ms:.0f}ms")

    # Per-fold breakdown
    print(f"\n{'Image (held out)':<35} {'Score':>6} {'Failures'}")
    print("-" * 70)
    for ir in sorted(cv_result.per_fold, key=lambda x: x.correct / max(x.total, 1)):
        pct = f"{ir.correct}/{ir.total}"
        fails = ", ".join(f"{f['expected']}->{f['detected']}" for f in ir.failures)
        print(f"{ir.image_id:<35} {pct:>6} {fails}")

    # Failure diagnostics
    failed = [dr for dr in cv_result.digit_results if not dr.correct]
    if failed:
        print(f"\nCV Failure diagnostics ({len(failed)} failures):")
        print("-" * 80)
        for dr in failed:
            print(f"  {dr.image_id} ({dr.iy},{dr.ix}) {dr.color}: "
                  f"expected={dr.expected} detected={dr.detected} "
                  f"conf={dr.confidence:.2f} method={dr.method} rule={dr.rule_name}")

    # Confusion matrix
    if cv_result.confusion:
        print(f"\nCV Confusion matrix:")
        for pair, count in cv_result.confusion.most_common():
            print(f"  {pair}: {count}x")


# ---------------------------------------------------------------------------
# Versioned result logging
# ---------------------------------------------------------------------------


def log_run(
    result: EvalResult,
    results_path: Path,
    run_id: str | None = None,
    detector_version: str = "1.0",
    gt_version: int = 1,
) -> str:
    """Append evaluation run to versioned results JSON.

    Args:
        result: The evaluation result.
        results_path: Path to eval_results.json.
        run_id: Optional run identifier. Auto-generated if None.
        detector_version: Version string for the detector.
        gt_version: Ground truth dataset version.

    Returns:
        The run_id used.
    """
    if run_id is None:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        run_id = f"v{detector_version}_{ts}"

    # Load existing results
    data: dict = {"runs": []}
    if results_path.exists():
        with open(results_path, encoding="utf-8") as f:
            data = json.load(f)

    run_entry = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "detector_version": detector_version,
        "ground_truth_version": gt_version,
        "total_digits": result.total_digits,
        "correct": result.correct,
        "accuracy": round(result.accuracy, 4),
        "elapsed_ms": round(result.elapsed_ms, 1),
        "per_image": [
            {
                "image_id": ir.image_id,
                "total": ir.total,
                "correct": ir.correct,
                "failures": ir.failures,
            }
            for ir in result.per_image
        ],
        "confusion_matrix": dict(result.confusion.most_common()),
    }

    data["runs"].append(run_entry)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return run_id


# ---------------------------------------------------------------------------
# Comparison view
# ---------------------------------------------------------------------------


def show_comparison(results_path: Path) -> None:
    """Print a table comparing all evaluation runs."""
    if not results_path.exists():
        print("No evaluation results found.")
        return

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("runs", [])
    if not runs:
        print("No runs recorded.")
        return

    # Header
    print(f"{'Run ID':<30} {'Accuracy':>8} {'Correct':>8} {'Total':>6} {'Time':>8} {'Top Confusions'}")
    print("-" * 100)

    for run in runs:
        acc = f"{run['accuracy'] * 100:.1f}%"
        correct = str(run["correct"])
        total = str(run["total_digits"])
        elapsed = f"{run.get('elapsed_ms', 0):.0f}ms"

        # Top 3 confusions
        cm = run.get("confusion_matrix", {})
        top_conf = ", ".join(f"{k}({v})" for k, v in sorted(cm.items(), key=lambda x: -x[1])[:3])

        print(f"{run['run_id']:<30} {acc:>8} {correct:>8} {total:>6} {elapsed:>8} {top_conf}")


def show_detail(result: EvalResult, label: str = "Resubstitution") -> None:
    """Print detailed evaluation results to stdout."""
    if label == "Resubstitution":
        print(f"\nDigit Detection Evaluation (Resubstitution — train=test)")
        print(f"{'=' * 60}")
        print(f"Total digits: {result.total_digits}")
        print(f"Correct:      {result.correct}")
        print(f"Resubstitution Accuracy: {result.accuracy * 100:.1f}%")
        print(f"  (templates trained on same data — use --cv for honest accuracy)")
    else:
        print(f"\nDigit Detection Evaluation ({label})")
        print(f"{'=' * 60}")
        print(f"Total digits: {result.total_digits}")
        print(f"Correct:      {result.correct}")
        print(f"{label} Accuracy: {result.accuracy * 100:.1f}%")
    print(f"Elapsed:      {result.elapsed_ms:.0f}ms")

    # Method distribution
    method_counts: Counter = Counter()
    for dr in result.digit_results:
        method_counts[dr.method] += 1
    if method_counts:
        print(f"\nMethod distribution:")
        for method, count in method_counts.most_common():
            print(f"  {method}: {count}")

    # Per-image breakdown
    print(f"\n{'Image':<35} {'Score':>6} {'Failures'}")
    print("-" * 70)
    for ir in sorted(result.per_image, key=lambda x: x.correct / max(x.total, 1)):
        pct = f"{ir.correct}/{ir.total}"
        fails = ", ".join(f"{f['expected']}->{f['detected']}" for f in ir.failures)
        print(f"{ir.image_id:<35} {pct:>6} {fails}")

    # Detailed failure diagnostics
    failed = [dr for dr in result.digit_results if not dr.correct]
    if failed:
        print(f"\nFailure diagnostics ({len(failed)} failures):")
        print("-" * 80)
        for dr in failed:
            print(f"  {dr.image_id} ({dr.iy},{dr.ix}) {dr.color}: "
                  f"expected={dr.expected} detected={dr.detected} "
                  f"conf={dr.confidence:.2f} method={dr.method} rule={dr.rule_name}")
            if dr.runner_up:
                print(f"    runner_up={dr.runner_up}")
            f = dr.features
            if f:
                print(f"    bbox={f.get('bbox_w','?')}x{f.get('bbox_h','?')} "
                      f"tf={f.get('top_fill','?')} bf={f.get('bot_fill','?')} "
                      f"lc={f.get('left_col','?')} rc={f.get('right_col','?')} "
                      f"holes={f.get('n_holes','?')} hbar={f.get('has_h_bar','?')} "
                      f"tz={f.get('top_zone','?')} bz={f.get('bot_zone','?')}")

    # Low-confidence correct detections (fragile)
    fragile = [dr for dr in result.digit_results
               if dr.correct and 0 < dr.confidence < 0.7]
    if fragile:
        print(f"\nLow-confidence correct ({len(fragile)} fragile):")
        for dr in fragile:
            print(f"  {dr.image_id} ({dr.iy},{dr.ix}): digit={dr.detected} "
                  f"conf={dr.confidence:.2f} rule={dr.rule_name}")

    # Confusion matrix
    if result.confusion:
        print(f"\nConfusion matrix:")
        for pair, count in result.confusion.most_common():
            print(f"  {pair}: {count}x")
