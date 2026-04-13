"""Extract digit templates from correctly-detected ground truth examples.

Loads ground_truth.json, runs detection on each entry, and for those
where the detector agrees with ground truth, extracts the normalized
component mask and averages across examples to produce clean templates.

Usage:
    python -m tools.minoru_harada_tsumego.extract_templates

Output:
    tools/core/digit_templates/digit_{N}.npy          (10 files, 0-9)
    tools/core/digit_templates/digit_{N}_{color}.npy   (per-color, if enough examples)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.core.image_to_board import (
    BLACK,
    WHITE,
    RecognitionConfig,
    _TEMPLATE_SIZE,
    detect_digit,
    recognize_position,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONFIG = RecognitionConfig()
_WORKING_DIR = Path(__file__).parent / "_working"
_GT_PATH = _WORKING_DIR / "ground_truth.json"
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "core" / "digit_templates"

# Minimum examples required to save a color-specific template
_MIN_COLOR_EXAMPLES = 3


# ---------------------------------------------------------------------------
# Mask extraction
# ---------------------------------------------------------------------------


def _extract_component_mask(
    img_bgr: np.ndarray,
    cx: int,
    cy: int,
    stone_color: str,
) -> np.ndarray | None:
    """Extract the normalized component mask for a digit at (cx, cy).

    Reproduces the threshold + connected component pipeline from
    detect_digit(), returning the largest component resized to
    _TEMPLATE_SIZE.

    Returns:
        Normalized binary mask (10x14) or None if extraction fails.
    """
    h, w = img_bgr.shape[:2]
    r = _CONFIG.digit_roi_radius

    # Extract ROI
    y1 = max(0, cy - r)
    y2 = min(h, cy + r + 1)
    x1 = max(0, cx - r)
    x2 = min(w, cx + r + 1)
    roi = img_bgr[y1:y2, x1:x2]

    if roi.size == 0:
        return None

    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    roi_h, roi_w = roi_gray.shape

    # Threshold to isolate digit pixels
    if stone_color == BLACK:
        _, thresh = cv2.threshold(
            roi_gray, _CONFIG.digit_bright_threshold, 255, cv2.THRESH_BINARY,
        )
    else:
        _, thresh = cv2.threshold(
            roi_gray, _CONFIG.digit_dark_threshold, 255, cv2.THRESH_BINARY_INV,
        )

    # Connected components
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)

    if n_labels <= 1:
        return None

    # Find the largest non-background component
    roi_area = roi_h * roi_w
    min_area = _CONFIG.digit_min_area
    max_area = int(roi_area * _CONFIG.digit_max_area_ratio)

    best_label = -1
    best_area = 0
    for label_id in range(1, n_labels):
        area = stats[label_id, cv2.CC_STAT_AREA]
        if area < min_area or area > max_area:
            continue
        comp_w = stats[label_id, cv2.CC_STAT_WIDTH]
        comp_h = stats[label_id, cv2.CC_STAT_HEIGHT]
        if comp_w > 0 and comp_h > 0:
            aspect = comp_h / comp_w
            if aspect < 0.5 or aspect > 6.0:
                continue
        if area > best_area:
            best_area = area
            best_label = label_id

    if best_label < 0:
        return None

    # Extract component bounding box mask
    comp_x = stats[best_label, cv2.CC_STAT_LEFT]
    comp_y = stats[best_label, cv2.CC_STAT_TOP]
    comp_w = stats[best_label, cv2.CC_STAT_WIDTH]
    comp_h = stats[best_label, cv2.CC_STAT_HEIGHT]

    comp_mask = (labels[comp_y:comp_y + comp_h, comp_x:comp_x + comp_w] == best_label).astype(np.uint8) * 255

    if comp_mask.shape[0] < 2 or comp_mask.shape[1] < 2:
        return None

    # Resize to template size
    normalized = cv2.resize(comp_mask, _TEMPLATE_SIZE, interpolation=cv2.INTER_AREA)
    return normalized


def build_templates_excluding(
    ground_truth_path: Path,
    image_base_dir: Path,
    exclude_image_id: str,
) -> dict[int, np.ndarray]:
    """Build digit templates from all ground truth images EXCEPT one.

    Used for leave-one-image-out cross-validation: templates are built
    from N-1 images and tested on the excluded image. This ensures the
    test image never contributes to its own templates.

    Args:
        ground_truth_path: Path to ground_truth.json.
        image_base_dir: Directory containing _images/ subdirectory.
        exclude_image_id: The image id to hold out (e.g. "2000_204_e_correct").

    Returns:
        Dict mapping digit (0-9) to averaged binary template (10x14 np.ndarray).
    """
    with open(ground_truth_path, encoding="utf-8") as f:
        gt = json.load(f)

    masks_by_digit: dict[int, list[np.ndarray]] = defaultdict(list)

    for img_entry in gt["images"]:
        image_id = img_entry["id"]

        # Skip the held-out image
        if image_id == exclude_image_id:
            continue

        # Skip holdout-group images (only use training group for templates)
        if img_entry.get("group") == "holdout":
            continue

        answer_path = image_base_dir / img_entry["answer_path"]
        if not answer_path.exists():
            continue

        answer_pos = recognize_position(str(answer_path))
        answer_pil = Image.open(str(answer_path)).convert("RGB")
        answer_arr = np.array(answer_pil)
        answer_bgr = cv2.cvtColor(answer_arr, cv2.COLOR_RGB2BGR)

        for digit_entry in img_entry["digits"]:
            iy = digit_entry["iy"]
            ix = digit_entry["ix"]
            expected = digit_entry["expected"]
            color = digit_entry["color"]

            if iy >= len(answer_pos.grid.y_lines) or ix >= len(answer_pos.grid.x_lines):
                continue

            cy = answer_pos.grid.y_lines[iy]
            cx = answer_pos.grid.x_lines[ix]

            # Only use examples where feature-only detection agrees with GT
            # (using empty templates to force feature-based classification)
            det_result = detect_digit(answer_pil, cx, cy, color, templates={})
            if det_result.digit != expected:
                continue

            mask = _extract_component_mask(answer_bgr, cx, cy, color)
            if mask is None:
                continue

            masks_by_digit[expected].append(mask)

    # Build averaged templates
    templates: dict[int, np.ndarray] = {}
    for digit, masks in masks_by_digit.items():
        if masks:
            avg = np.mean(np.stack(masks, axis=0), axis=0)
            templates[digit] = (avg >= 128).astype(np.uint8) * 255

    return templates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Extract digit templates from ground truth data."""
    if not _GT_PATH.exists():
        print(f"Ground truth not found: {_GT_PATH}")
        return

    with open(_GT_PATH, encoding="utf-8") as f:
        gt = json.load(f)

    # Collect masks by digit and by (digit, color)
    masks_by_digit: dict[int, list[np.ndarray]] = defaultdict(list)
    masks_by_digit_color: dict[tuple[int, str], list[np.ndarray]] = defaultdict(list)

    total_entries = 0
    used_entries = 0
    skipped_mismatch = 0
    skipped_extraction = 0

    for img_entry in gt["images"]:
        image_id = img_entry["id"]
        answer_path = _WORKING_DIR / img_entry["answer_path"]

        if not answer_path.exists():
            print(f"  SKIP {image_id}: missing {answer_path.name}")
            continue

        # Recognize position for grid coordinates
        answer_pos = recognize_position(str(answer_path))

        # Load image as PIL for detect_digit and as BGR for mask extraction
        answer_pil = Image.open(str(answer_path)).convert("RGB")
        answer_arr = np.array(answer_pil)
        answer_bgr = cv2.cvtColor(answer_arr, cv2.COLOR_RGB2BGR)

        for digit_entry in img_entry["digits"]:
            total_entries += 1
            iy = digit_entry["iy"]
            ix = digit_entry["ix"]
            expected = digit_entry["expected"]
            color = digit_entry["color"]

            # Get pixel coordinates
            if iy >= len(answer_pos.grid.y_lines) or ix >= len(answer_pos.grid.x_lines):
                skipped_extraction += 1
                continue

            cy = answer_pos.grid.y_lines[iy]
            cx = answer_pos.grid.x_lines[ix]

            # Run detector -- only use if it agrees with ground truth
            det_result = detect_digit(answer_pil, cx, cy, color)
            if det_result.digit != expected:
                skipped_mismatch += 1
                continue

            # Extract normalized component mask
            mask = _extract_component_mask(answer_bgr, cx, cy, color)
            if mask is None:
                skipped_extraction += 1
                continue

            masks_by_digit[expected].append(mask)
            masks_by_digit_color[(expected, color)].append(mask)
            used_entries += 1

    # Create output directory
    _TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    # Compute and save average templates
    print(f"\n{'='*60}")
    print(f"Template Extraction Results")
    print(f"{'='*60}")
    print(f"Total ground truth entries: {total_entries}")
    print(f"Used (detector agreed):     {used_entries}")
    print(f"Skipped (mismatch):         {skipped_mismatch}")
    print(f"Skipped (extraction fail):  {skipped_extraction}")
    print()

    print(f"{'Digit':<8} {'Count':<8} {'BLACK':<8} {'WHITE':<8} {'Saved'}")
    print(f"{'-'*50}")

    saved_count = 0
    for digit in range(10):
        masks = masks_by_digit.get(digit, [])
        n_black = len(masks_by_digit_color.get((digit, BLACK), []))
        n_white = len(masks_by_digit_color.get((digit, WHITE), []))
        saved_files = []

        if masks:
            # Compute pointwise mean, then threshold at 128
            avg = np.mean(np.stack(masks, axis=0), axis=0)
            template = (avg >= 128).astype(np.uint8) * 255
            out_path = _TEMPLATE_DIR / f"digit_{digit}.npy"
            np.save(str(out_path), template)
            saved_files.append(out_path.name)
            saved_count += 1

        # Color-specific templates
        for color_label, color_code in [("black", BLACK), ("white", WHITE)]:
            color_masks = masks_by_digit_color.get((digit, color_code), [])
            if len(color_masks) >= _MIN_COLOR_EXAMPLES:
                avg_c = np.mean(np.stack(color_masks, axis=0), axis=0)
                tmpl_c = (avg_c >= 128).astype(np.uint8) * 255
                out_c = _TEMPLATE_DIR / f"digit_{digit}_{color_label}.npy"
                np.save(str(out_c), tmpl_c)
                saved_files.append(out_c.name)

        saved_str = ", ".join(saved_files) if saved_files else "-"
        print(f"  {digit:<6} {len(masks):<8} {n_black:<8} {n_white:<8} {saved_str}")

    print(f"\nSaved {saved_count} digit templates to {_TEMPLATE_DIR}")


if __name__ == "__main__":
    main()
