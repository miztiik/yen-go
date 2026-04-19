"""Detect individual Go board regions on a page image.

Given a full-page image (from a PDF or scan), finds bounding boxes
of individual Go board diagrams using connected component analysis
and grid-line validation.

Supports multi-column PDF layouts (1/2/3 columns) via column
projection analysis, and grid-line pre-filtering to reject
non-board regions before expensive recognition.

Usage:
    from tools.pdf_to_sgf.board_detector import detect_boards

    boards = detect_boards(page_image)
    for bbox, crop in boards:
        print(f"Board at {bbox}: {crop.size}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionConfig:
    """Configuration for board region detection."""

    binarize_threshold: int = 200
    """Grayscale threshold for binarization (pixels below are 'dark')."""

    min_board_area: int = 10_000
    """Minimum pixel area for a candidate board region."""

    padding: int = 20
    """Minimum pixel padding around detected board bounding boxes.
    Actual padding is max(this, 4% of board dimension) to handle
    stones at the outermost grid intersections."""

    min_aspect_ratio: float = 0.3
    """Minimum width/height ratio (reject very tall/thin noise)."""

    max_aspect_ratio: float = 3.5
    """Maximum width/height ratio (reject very wide/flat noise)."""

    merge_distance: int = 30
    """Merge nearby components within this pixel distance."""

    min_grid_lines: int = 15
    """Minimum HoughLines to accept a region as a board (pre-filter)."""

    enable_grid_filter: bool = True
    """Enable grid-line pre-filtering of candidate regions."""

    enable_column_detection: bool = True
    """Enable multi-column layout detection to split pages."""

    column_morph_height: int = 100
    """Morphological kernel height for column detection."""

    column_smooth_size: int = 51
    """Gaussian smoothing kernel size for column projection."""

    min_column_width: int = 100
    """Minimum pixel width to count as a column."""

    enable_boundary_refinement: bool = True
    """Enable contour-based boundary rectangle refinement to avoid clipping edge stones."""

    boundary_min_area_ratio: float = 0.50
    """Reject boundary rectangles smaller than this fraction of CC crop area."""

    boundary_stone_padding_ratio: float = 0.06
    """Padding beyond boundary rect as fraction of board dimension (~half grid spacing)."""

    enable_edge_walk: bool = True
    """Walk bbox edges outward to nearest white row/col to avoid cutting through stones."""

    edge_walk_max_pixels: int = 30
    """Maximum pixels to walk outward per edge."""

    edge_walk_min_padding: int = 5
    """Minimum pixels of whitespace margin beyond the detected white boundary."""

    edge_walk_white_threshold: int = 240
    """Pixel intensity >= this counts as white."""

    edge_walk_white_ratio: float = 0.98
    """Fraction of pixels in row/col that must be white."""


_DEFAULT_CONFIG = DetectionConfig()


@dataclass(frozen=True)
class DetectedBoard:
    """A single board region detected on a page."""

    bbox: tuple[int, int, int, int]
    """Bounding box (x1, y1, x2, y2) on the original page."""

    image: Image.Image
    """Cropped board image (RGB)."""

    index: int
    """0-based index of this board on the page (reading order: left-to-right, top-to-bottom)."""

    detection_confidence: float = 0.0
    """Confidence that the bounding box correctly encompasses the full board (0.0-1.0).
    0.0 = CC fallback (no boundary rectangle found), >0 = contour-based refinement succeeded."""


# ---------------------------------------------------------------------------
# Column detection (Phase 5a)
# ---------------------------------------------------------------------------


def detect_columns(
    page_image: Image.Image,
    config: DetectionConfig = _DEFAULT_CONFIG,
) -> list[tuple[Image.Image, int]]:
    """Detect and split multi-column layouts.

    Uses morphological close + vertical projection profiling to count
    contiguous active blocks. Splits page into 1/2/3 columns.

    Parameters
    ----------
    page_image : PIL.Image.Image
        Full page image (RGB or grayscale).
    config : DetectionConfig
        Detection settings.

    Returns
    -------
    list[tuple[Image.Image, int]]
        Column images with their x-offset in page coordinates.
        Returns [(page_image, 0)] if single-column.
    """
    gray = np.array(page_image.convert("L"))
    _, binary = cv2.threshold(gray, config.binarize_threshold, 255, cv2.THRESH_BINARY_INV)

    # Morphological close to merge text/diagram blocks vertically
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, config.column_morph_height))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Vertical projection: sum active pixels per column
    col_sums = np.sum(closed > 0, axis=0).astype(np.float32)

    # Smooth the projection to reduce noise
    k = config.column_smooth_size
    if k % 2 == 0:
        k += 1  # must be odd for GaussianBlur
    smoothed = cv2.GaussianBlur(col_sums.reshape(1, -1), (k, 1), 0).flatten()

    # Threshold at 50% of max to find active column regions
    threshold = np.max(smoothed) * 0.5 if np.max(smoothed) > 0 else 0
    active = smoothed > threshold

    # Count contiguous blocks wider than minimum
    col_count = 0
    col_boundaries: list[tuple[int, int]] = []
    width = 0
    start = 0
    in_col = False
    for i, is_active in enumerate(active):
        if is_active:
            if not in_col:
                start = i
                in_col = True
            width += 1
        elif in_col:
            if width >= config.min_column_width:
                col_count += 1
                col_boundaries.append((start, start + width))
            width = 0
            in_col = False
    if in_col and width >= config.min_column_width:
        col_count += 1
        col_boundaries.append((start, start + width))

    col_count = max(1, min(col_count, 3))  # clamp 1-3

    if col_count <= 1 or len(col_boundaries) <= 1:
        log.debug("Single-column layout detected")
        return [(page_image, 0)]

    log.info("Detected %d-column layout (boundaries: %s)", col_count, col_boundaries)

    # Split into columns
    columns: list[tuple[Image.Image, int]] = []
    page_w = page_image.width
    page_h = page_image.height
    # Compute safe margin between columns so edge stones aren't clipped.
    # Stones on the 1st line extend ~0.5 grid-spacing (~17px at 200 DPI)
    # beyond the board edge line. The content boundary often lands ON the
    # edge line, so we need ≥20px beyond it. Use half the inter-column gap
    # (which is typically 40-50px) to maximise margin without overlap.
    if len(col_boundaries) >= 2:
        min_gap = min(
            col_boundaries[i + 1][0] - col_boundaries[i][1]
            for i in range(len(col_boundaries) - 1)
        )
        col_margin = max(20, min_gap // 2)
    else:
        col_margin = 40

    for start_x, end_x in col_boundaries[:col_count]:
        x1 = max(0, start_x - col_margin)
        x2 = min(page_w, end_x + col_margin)
        if x2 - x1 >= config.min_column_width:
            columns.append((page_image.crop((x1, 0, x2, page_h)), x1))

    return columns if columns else [(page_image, 0)]


# ---------------------------------------------------------------------------
# Grid-line pre-filter (Phase 5b)
# ---------------------------------------------------------------------------


def has_board_grid(
    region_image: Image.Image,
    min_lines: int = 15,
) -> tuple[bool, int]:
    """Check if an image region contains a Go board grid.

    Uses Canny edge detection + HoughLines to check if sufficient
    grid lines are present. Fast guard before expensive recognition.

    Parameters
    ----------
    region_image : PIL.Image.Image
        Cropped region to check.
    min_lines : int
        Minimum line count to consider a board.

    Returns
    -------
    tuple[bool, int]
        (is_board, line_count)
    """
    gray = np.array(region_image.convert("L"))
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 120)
    num_lines = 0 if lines is None else len(lines)
    return num_lines >= min_lines, num_lines


# ---------------------------------------------------------------------------
# Boundary rectangle refinement (Phase 5c)
# ---------------------------------------------------------------------------


def _find_boundary_rectangle(
    crop_gray: np.ndarray,
    config: DetectionConfig,
) -> tuple[tuple[int, int, int, int] | None, float]:
    """Find the thick boundary rectangle in a board crop.

    Uses Canny + contour analysis to detect the outermost board border
    (the thick black rectangle that surrounds the grid).

    Parameters
    ----------
    crop_gray : np.ndarray
        Grayscale image of the cropped board region.
    config : DetectionConfig
        Detection settings.

    Returns
    -------
    tuple[rect | None, confidence]
        rect is (x1, y1, x2, y2) in crop-local coordinates, or None.
        confidence is 0.0-1.0.
    """
    h, w = crop_gray.shape
    crop_area = h * w

    # Canny edge detection + dilate to connect broken edges
    edges = cv2.Canny(crop_gray, 50, 150, apertureSize=3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, 0.0

    # Sort contours by area (largest first)
    contours_sorted = sorted(contours, key=cv2.contourArea, reverse=True)

    # Phase A: Look for 4-sided polygons via approxPolyDP
    for contour in contours_sorted:
        area = cv2.contourArea(contour)
        if area < config.boundary_min_area_ratio * crop_area:
            break  # sorted by area, so all subsequent are smaller

        perimeter = cv2.arcLength(contour, closed=True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, closed=True)

        if len(approx) != 4:
            continue

        # Get axis-aligned bounding rect of the polygon
        rx, ry, rw, rh = cv2.boundingRect(approx)
        ratio = rw / rh if rh > 0 else 0
        if ratio < 0.4 or ratio > 2.5:
            continue

        rect = (rx, ry, rx + rw, ry + rh)
        rect_area_ratio = area / crop_area
        confidence = 0.95 if rect_area_ratio > 0.70 else 0.80
        log.debug("Boundary rect found via approxPolyDP: %s (area_ratio=%.2f, conf=%.2f)",
                  rect, rect_area_ratio, confidence)
        return rect, confidence

    # Phase B: Fallback — try minAreaRect on the largest contour
    largest = contours_sorted[0]
    largest_area = cv2.contourArea(largest)
    if largest_area < config.boundary_min_area_ratio * crop_area:
        return None, 0.0

    min_rect = cv2.minAreaRect(largest)
    angle = min_rect[2]
    # Accept only near-axis-aligned rectangles (within 5 degrees)
    if not (angle < 5 or angle > 85 or abs(angle - 90) < 5):
        return None, 0.0

    box = cv2.boxPoints(min_rect)
    rx, ry, rw, rh = cv2.boundingRect(np.int32(box))
    ratio = rw / rh if rh > 0 else 0
    if ratio < 0.4 or ratio > 2.5:
        return None, 0.0

    rect = (rx, ry, rx + rw, ry + rh)
    log.debug("Boundary rect found via minAreaRect fallback: %s (conf=0.65)", rect)
    return rect, 0.65


def _refine_board_bbox(
    region_image: Image.Image,
    cc_bbox: tuple[int, int, int, int],
    config: DetectionConfig,
) -> tuple[tuple[int, int, int, int], Image.Image, float]:
    """Refine a CC-based bounding box using boundary rectangle detection.

    Parameters
    ----------
    region_image : PIL.Image.Image
        The full column/region image.
    cc_bbox : tuple[int, int, int, int]
        The CC-derived bounding box (x1, y1, x2, y2) in region coordinates.
    config : DetectionConfig
        Detection settings.

    Returns
    -------
    tuple[bbox, crop, confidence]
        Refined bbox in region coordinates, cropped image, and confidence score.
        If no boundary rectangle found, returns cc_bbox unchanged with confidence=0.0.
    """
    cx1, cy1, cx2, cy2 = cc_bbox
    rh, rw = np.array(region_image.convert("L")).shape

    # Extract the CC crop for analysis
    crop_gray = np.array(region_image.convert("L"))[cy1:cy2, cx1:cx2]
    if crop_gray.size == 0:
        return cc_bbox, region_image.crop(cc_bbox), 0.0

    rect, confidence = _find_boundary_rectangle(crop_gray, config)
    if rect is None or confidence == 0.0:
        return cc_bbox, region_image.crop(cc_bbox), 0.0

    # Convert crop-local rect to region coordinates
    rx1, ry1, rx2, ry2 = rect
    abs_x1 = cx1 + rx1
    abs_y1 = cy1 + ry1
    abs_x2 = cx1 + rx2
    abs_y2 = cy1 + ry2

    # Add stone padding beyond the boundary rectangle
    bw = abs_x2 - abs_x1
    bh = abs_y2 - abs_y1
    pad_x = int(bw * config.boundary_stone_padding_ratio)
    pad_y = int(bh * config.boundary_stone_padding_ratio)

    # Clamp to region bounds
    final_x1 = max(0, abs_x1 - pad_x)
    final_y1 = max(0, abs_y1 - pad_y)
    final_x2 = min(rw, abs_x2 + pad_x)
    final_y2 = min(rh, abs_y2 + pad_y)

    refined_bbox = (final_x1, final_y1, final_x2, final_y2)
    refined_crop = region_image.crop(refined_bbox)

    log.debug("Refined bbox: CC(%d,%d,%d,%d) → boundary(%d,%d,%d,%d) conf=%.2f",
              cx1, cy1, cx2, cy2, final_x1, final_y1, final_x2, final_y2, confidence)

    return refined_bbox, refined_crop, confidence


# ---------------------------------------------------------------------------
# Phase 5d: Edge-walk refinement
# ---------------------------------------------------------------------------


def _walk_edge_to_whitespace(
    gray: np.ndarray,
    bbox: tuple[int, int, int, int],
    *,
    max_walk: int = 30,
    min_padding: int = 5,
    white_threshold: int = 240,
    white_ratio: float = 0.98,
) -> tuple[int, int, int, int]:
    """Extend bbox edges outward to the nearest all-white row/column.

    For each edge, scan outward up to *max_walk* pixels.  A row/column
    is "white" if >= *white_ratio* of its pixels have intensity >=
    *white_threshold*.  Once found, the edge is placed *min_padding*
    pixels beyond the white boundary to avoid pixel-tight crops.

    If no white row/column is found within *max_walk*, the original
    edge is kept.  Results are clamped to image bounds.
    """
    h, w = gray.shape[:2]
    x1, y1, x2, y2 = bbox

    def _is_white_row(y: int) -> bool:
        row = gray[y, max(0, x1):min(w, x2)]
        if len(row) == 0:
            return True
        return float(np.sum(row >= white_threshold)) / len(row) >= white_ratio

    def _is_white_col(x: int) -> bool:
        col = gray[max(0, y1):min(h, y2), x]
        if len(col) == 0:
            return True
        return float(np.sum(col >= white_threshold)) / len(col) >= white_ratio

    # Top: walk upward
    new_y1 = y1
    for y in range(y1, max(-1, y1 - max_walk - 1), -1):
        if y < 0:
            break
        if _is_white_row(y):
            # Only add min_padding if we had to walk (edge was cutting content)
            new_y1 = max(0, y - min_padding) if y != y1 else y1
            break

    # Bottom: walk downward
    new_y2 = y2
    for y in range(y2, min(h, y2 + max_walk + 1)):
        if y >= h:
            break
        if _is_white_row(y):
            new_y2 = min(h, y + min_padding) if y != y2 else y2
            break

    # Left: walk leftward
    new_x1 = x1
    for x in range(x1, max(-1, x1 - max_walk - 1), -1):
        if x < 0:
            break
        if _is_white_col(x):
            new_x1 = max(0, x - min_padding) if x != x1 else x1
            break

    # Right: walk rightward
    new_x2 = x2
    for x in range(x2, min(w, x2 + max_walk + 1)):
        if x >= w:
            break
        if _is_white_col(x):
            new_x2 = min(w, x + min_padding) if x != x2 else x2
            break

    if (new_x1, new_y1, new_x2, new_y2) != (x1, y1, x2, y2):
        log.debug("Edge-walk: (%d,%d,%d,%d) → (%d,%d,%d,%d)",
                  x1, y1, x2, y2, new_x1, new_y1, new_x2, new_y2)

    return (new_x1, new_y1, new_x2, new_y2)


# ---------------------------------------------------------------------------
# Main detection
# ---------------------------------------------------------------------------


def detect_boards(
    page_image: Image.Image,
    config: DetectionConfig = _DEFAULT_CONFIG,
) -> list[DetectedBoard]:
    """Detect individual Go board regions on a page image.

    Pipeline:
    1. Optionally detect and split multi-column layouts
    2. Find candidate regions via CC analysis
    3. Optionally pre-filter by grid-line count
    4. Return boards sorted in reading order (left-to-right, top-to-bottom)

    Parameters
    ----------
    page_image : PIL.Image.Image
        Full page image (RGB).
    config : DetectionConfig
        Detection settings.

    Returns
    -------
    list[DetectedBoard]
        Detected board regions, sorted in reading order.
    """
    # Phase 5a: split multi-column layouts
    if config.enable_column_detection:
        columns = detect_columns(page_image, config)
    else:
        columns = [(page_image, 0)]

    all_boards: list[DetectedBoard] = []
    global_idx = 0

    for col_idx, (col_image, col_offset_x) in enumerate(columns):
        boards_in_col = _detect_boards_in_region(col_image, config, col_offset_x, global_idx)
        global_idx += len(boards_in_col)
        all_boards.extend(boards_in_col)

    # Re-sort into reading order: row-first (y), then column (x).
    # Column detection produces column-major order, but PDFs are read
    # left-to-right, top-to-bottom (row-major).
    # Boards in the same visual row may have slightly different y values,
    # so we bucket by row using a tolerance based on board height.
    if len(columns) > 1 and len(all_boards) > 1:
        # Estimate row tolerance: half the typical board height
        avg_height = sum(b.bbox[3] - b.bbox[1] for b in all_boards) / len(all_boards)
        row_tolerance = avg_height * 0.5

        def _row_bucket(y: int) -> int:
            """Assign a row index by bucketing y coordinates."""
            return int(y / row_tolerance)

        all_boards.sort(key=lambda b: (_row_bucket(b.bbox[1]), b.bbox[0]))
        # Re-assign indices after sort
        all_boards = [
            DetectedBoard(bbox=b.bbox, image=b.image, index=i,
                          detection_confidence=b.detection_confidence)
            for i, b in enumerate(all_boards)
        ]

    log.info("Found %d board region(s) on %dx%d page (%d column(s))",
             len(all_boards), page_image.width, page_image.height, len(columns))

    return all_boards


def _detect_boards_in_region(
    region_image: Image.Image,
    config: DetectionConfig,
    offset_x: int = 0,
    start_index: int = 0,
) -> list[DetectedBoard]:
    """Detect boards within a single column/region."""
    img_np = np.array(region_image.convert("L"))
    h, w = img_np.shape

    # Binarize: dark content = white in mask
    _, binary = cv2.threshold(
        img_np, config.binarize_threshold, 255, cv2.THRESH_BINARY_INV
    )

    # Morphological close to merge nearby grid lines and stones
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (config.merge_distance, config.merge_distance)
    )
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Find connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        closed, connectivity=8
    )

    candidates: list[tuple[int, int, int, int, int]] = []
    for i in range(1, num_labels):  # skip background (label 0)
        x, y, cw, ch, area = stats[i]

        # Filter by area
        if area < config.min_board_area:
            continue

        # Filter by aspect ratio
        ratio = cw / ch if ch > 0 else 0
        if ratio < config.min_aspect_ratio or ratio > config.max_aspect_ratio:
            continue

        candidates.append((x, y, x + cw, y + ch, area))

    # Sort top-to-bottom by y coordinate
    candidates.sort(key=lambda c: c[1])

    # Crop with padding and optionally pre-filter by grid lines
    boards: list[DetectedBoard] = []
    idx = start_index
    for x1, y1, x2, y2, _area in candidates:
        # Proportional padding: at least config.padding, but scale with board size
        # to ensure edge stones (which extend beyond outermost grid line) are included
        pad_x = max(config.padding, int((x2 - x1) * 0.04))
        pad_y = max(config.padding, int((y2 - y1) * 0.04))
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y)

        crop = region_image.crop((cx1, cy1, cx2, cy2))

        # Phase 5c: boundary rectangle refinement
        det_confidence = 0.0
        if config.enable_boundary_refinement:
            refined_bbox, refined_crop, det_confidence = _refine_board_bbox(
                region_image, (cx1, cy1, cx2, cy2), config,
            )
            if det_confidence > 0:
                cx1, cy1, cx2, cy2 = refined_bbox
                crop = refined_crop

        # Phase 5d: Edge-walk to ensure bbox cuts through whitespace, not stones
        if config.enable_edge_walk:
            cx1, cy1, cx2, cy2 = _walk_edge_to_whitespace(
                img_np, (cx1, cy1, cx2, cy2),
                max_walk=config.edge_walk_max_pixels,
                min_padding=config.edge_walk_min_padding,
                white_threshold=config.edge_walk_white_threshold,
                white_ratio=config.edge_walk_white_ratio,
            )
            crop = region_image.crop((cx1, cy1, cx2, cy2))

        # Phase 5b: grid-line pre-filter
        if config.enable_grid_filter:
            is_board, line_count = has_board_grid(crop, min_lines=config.min_grid_lines)
            if not is_board:
                log.debug("Skipping region (%d,%d,%d,%d): only %d grid lines (need %d)",
                           cx1, cy1, cx2, cy2, line_count, config.min_grid_lines)
                continue

        boards.append(DetectedBoard(
            bbox=(cx1 + offset_x, cy1, cx2 + offset_x, cy2),
            image=crop,
            index=idx,
            detection_confidence=det_confidence,
        ))
        log.debug("Board %d: bbox=(%d,%d,%d,%d) size=%dx%d",
                   idx, cx1 + offset_x, cy1, cx2 + offset_x, cy2, crop.width, crop.height)
        idx += 1

    return boards
