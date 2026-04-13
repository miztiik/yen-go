"""Recognize Go board positions from raster images using OpenCV.

OpenCV-based board recognition pipeline — works with any raster
image format (GIF, PNG, JPEG, or frames extracted from PDF).  Callers
provide a ``PIL.Image.Image`` or file path; this module handles
pixel-level analysis using OpenCV + NumPy for performance and
robustness.

Algorithm:
  1. Grid detection via Canny edge detection + HoughLinesP
  2. Line clustering with spacing-based filtering and gap interpolation
  3. Stone classification via HoughCircles + intensity with numpy fallback
  4. Board edge detection via line thickness measurement
  5. Digit detection via thresholding + connected components + template matching

Usage:
    from tools.core.image_to_board import recognize_position

    pos = recognize_position("path/to/board.gif")
    # or
    from PIL import Image
    img = Image.open("board.png")
    pos = recognize_position(img)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMPTY = "."
BLACK = "X"
WHITE = "O"

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecognitionConfig:
    """Tunable thresholds for board recognition.

    Defaults are calibrated for clean computer-generated Go diagrams
    (e.g. Harada tsumego GIF images).  Override for noisier sources.
    """

    # --- Grid detection ---
    canny_low: int = 30
    """Lower Canny edge threshold."""

    canny_high: int = 120
    """Upper Canny edge threshold."""

    hough_threshold: int = 30
    """Minimum votes for HoughLinesP."""

    hough_min_line_length: int = 15
    """Minimum line segment length for HoughLinesP."""

    hough_max_line_gap: int = 5
    """Maximum gap between line segments to merge in HoughLinesP."""

    min_grid_spacing: int = 8
    """Minimum pixels between grid lines (for clustering)."""

    angle_tolerance: float = 10.0
    """Max degrees from horizontal/vertical to accept a line."""

    # --- Stone classification ---
    black_intensity_threshold: int = 100
    """Mean intensity below which an intersection is classified as black stone."""

    white_intensity_threshold: int = 200
    """Mean intensity above which an intersection is classified as white stone."""

    stone_sample_ratio: float = 0.35
    """Fraction of grid spacing used as sampling radius for stone classification."""

    dark_ratio: float = 0.55
    """Minimum dark-pixel ratio (intensity < 80) to classify as black stone."""

    bright_ratio: float = 0.50
    """Minimum very-bright-pixel ratio to classify as white stone."""

    bright_pixel_threshold: int = 230
    """Grayscale intensity above which a pixel is counted as 'bright'
    for white stone classification."""

    dark_pixel_threshold: int = 80
    """Grayscale intensity below which a pixel is counted as 'dark'
    for black stone classification."""

    outlined_white_detection: bool = False
    """Enable variance-based detection of white stones with dark outlines.
    Clean PDFs draw white stones as circles with thick dark borders;
    the dark border inflates dark_ratio above the black threshold.
    When enabled, high std + moderate bright_ratio overrides the
    black classification."""

    bright_r: int = 230
    bright_g: int = 230
    bright_b: int = 230
    """Per-channel minimum for bright pixel detection."""

    dark_threshold: int = 150
    """RGB sum below which a pixel is dark (for grid voting fallback)."""

    # --- Edge detection ---
    edge_thickness_ratio: float = 1.4
    """Boundary-to-interior thickness ratio for edge detection."""

    edge_min_thickness: float = 1.8
    """Absolute minimum boundary thickness to be considered an edge."""

    # --- Digit detection ---
    digit_bright_threshold: int = 180
    """Per-channel min for digit pixels on black stones."""

    digit_dark_threshold: int = 100
    """Per-channel max for digit pixels on white stones."""

    digit_roi_radius: int = 7
    """Pixel radius around stone center for digit extraction."""

    digit_min_area: int = 4
    """Minimum connected component area (pixels) to consider as digit."""

    digit_max_area_ratio: float = 0.65
    """Maximum component area as fraction of ROI area."""

    template_match_threshold: float = 0.55
    """Minimum template match score to accept a digit classification."""

    stone_min_fill_ratio: float = 0.30
    """Minimum active pixel ratio relative to the sampling circle area.
    Stones with fewer active pixels than this fraction are reclassified
    as empty. Prevents noise from being detected as stones."""

    stone_min_diameter_ratio: float = 0.60
    """Minimum stone diameter as fraction of grid spacing. Detections
    smaller than this are likely noise."""

    stone_max_diameter_ratio: float = 1.30
    """Maximum stone diameter as fraction of grid spacing. Detections
    larger than this are likely misclassified regions."""

    blur_kernels: tuple[int, ...] = (0, 3, 5)
    """Gaussian blur kernel sizes for multi-blur stone classification.
    0 means no blur (original image). Majority voting across levels."""

    kmeans_adaptive: bool = False
    """When True, use K-means clustering to adapt stone classification
    thresholds per-image when the default thresholds diverge from the
    data. Runs after initial classification."""

    # --- Preprocessing (for PDF / scanned sources) ---
    clahe_enabled: bool = False
    """Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization)
    before grid detection. Improves results on unevenly-lit scans."""

    clahe_clip_limit: float = 2.0
    """CLAHE clip limit (higher = more contrast). 2.0 is a good default."""

    clahe_tile_size: int = 8
    """CLAHE tile grid size (NxN)."""

    adaptive_grid_threshold: bool = False
    """When True, auto-scale grid detection dark threshold relative to
    image resolution. Helps with thin grid lines in high-res PDF images."""

    grid_vote_ratio: float = 0.15
    """Fraction of scan lines a column/row must exceed to be a grid line
    candidate.  Lower values detect thinner lines in hi-res images."""

    circle_erasure: bool = False
    """When True, detect circle-shaped stones via HoughCircles and
    erase their bounding boxes before grid detection. Replaces each
    erased region with a center pixel so grid lines obscured by
    stones become visible. Technique from datavikingr/pdf2sgf."""

    circle_erasure_min_radius: int = 5
    """Minimum circle radius for HoughCircles detection."""

    circle_erasure_max_radius: int = 40
    """Maximum circle radius for HoughCircles detection."""

    digit_template_set: str = "default"
    """Template set for digit detection. 'default' uses tools/core/digit_templates/,
    'pdf' uses tools/core/digit_templates_pdf/ with thicker font rendering."""

    perspective_correction: bool = False
    """When True, detect the largest quadrilateral in the image and
    apply a perspective warp to rectify it. Useful for skewed scans
    or photos of physical boards. Applied before CLAHE."""

    perspective_min_area_ratio: float = 0.25
    """Minimum quadrilateral area as fraction of image area to be
    considered a valid board region for perspective correction."""

    perspective_output_size: int = 0
    """Output size for rectified image. 0 = use source dimensions."""

    @classmethod
    def for_pdf(cls) -> RecognitionConfig:
        """Preset tuned for computer-generated PDF board images.

        PDF board diagrams are high-resolution with thinner grid lines
        relative to image size. This preset enables CLAHE and K-means
        adaptive classification while keeping proven grid thresholds.
        """
        return cls(
            clahe_enabled=True,
            clahe_clip_limit=2.0,
            dark_ratio=0.40,
            bright_ratio=0.40,
            stone_sample_ratio=0.30,
            stone_min_fill_ratio=0.18,
            stone_min_diameter_ratio=0.45,
            kmeans_adaptive=True,
            circle_erasure=True,
            digit_template_set="pdf",
        )

    @classmethod
    def for_scan(cls) -> RecognitionConfig:
        """Preset tuned for scanned book pages.

        Scanned books have uneven lighting, thicker lines, and lower
        contrast than computer-generated diagrams. This preset uses
        aggressive CLAHE and relaxed thresholds.
        """
        return cls(
            clahe_enabled=True,
            clahe_clip_limit=3.0,
            dark_ratio=0.35,
            bright_ratio=0.35,
            stone_sample_ratio=0.30,
            stone_min_fill_ratio=0.15,
            kmeans_adaptive=True,
            blur_kernels=(0, 3, 5, 7),
            circle_erasure=True,
            perspective_correction=True,
        )

    @classmethod
    def for_clean_pdf(cls) -> RecognitionConfig:
        """Preset for clean computer-generated PDFs with light gray grids.

        Targets PDFs where grid lines are light gray (intensity 110-160)
        and white stones are solid white circles covering the grid.
        Uses a raised dark_threshold for grid detection and adjusted
        bright pixel classification thresholds.
        """
        return cls(
            dark_threshold=480,
            bright_pixel_threshold=200,
            bright_ratio=0.95,
            dark_ratio=0.40,
            stone_sample_ratio=0.30,
            stone_min_fill_ratio=0.18,
            stone_min_diameter_ratio=0.45,
            circle_erasure=False,
            digit_template_set="pdf",
            outlined_white_detection=True,
            grid_vote_ratio=0.40,
        )


_DEFAULT_CONFIG = RecognitionConfig()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridInfo:
    """Detected grid structure."""

    x_lines: tuple[int, ...]
    y_lines: tuple[int, ...]
    x_spacing: float
    y_spacing: float
    width: int
    height: int


@dataclass
class DigitDetectionResult:
    """Result of digit detection with confidence and diagnostics."""

    digit: int = 0                     # 0-18 (0 = undetected)
    confidence: float = 0.0            # 0.0-1.0
    method: str = "none"               # "template", "feature", "multi_digit", "none"
    rule_name: str = ""                # e.g. "R1_narrow_vertical"
    runner_up: int = 0                 # second-best digit candidate
    runner_up_score: float = 0.0       # its score
    features: dict = field(default_factory=dict)


@dataclass
class RecognizedPosition:
    """Result of board image recognition."""

    grid: GridInfo
    board: list[list[str]]  # [row][col] = EMPTY / BLACK / WHITE
    board_top: int  # 0-indexed row on full board
    board_left: int  # 0-indexed col on full board
    has_top_edge: bool
    has_bottom_edge: bool
    has_left_edge: bool
    has_right_edge: bool
    source_file: str = ""

    @property
    def n_rows(self) -> int:
        return len(self.board)

    @property
    def n_cols(self) -> int:
        return len(self.board[0]) if self.board else 0

    def stone_count(self) -> tuple[int, int]:
        """Return (black_count, white_count)."""
        b = w = 0
        for row in self.board:
            for cell in row:
                if cell == BLACK:
                    b += 1
                elif cell == WHITE:
                    w += 1
        return b, w


# ---------------------------------------------------------------------------
# Image loading helpers
# ---------------------------------------------------------------------------


def _to_numpy(image: Image.Image | str | Path) -> tuple[np.ndarray, str]:
    """Convert PIL Image or path to BGR numpy array."""
    if isinstance(image, (str, Path)):
        path = Path(image)
        # Use PIL for GIF support (OpenCV can't read GIF reliably)
        pil_img = Image.open(path).convert("RGB")
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return bgr, str(path)
    else:
        pil_img = image.convert("RGB") if image.mode != "RGB" else image
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return bgr, ""


def _correct_perspective(img: np.ndarray, config: RecognitionConfig) -> np.ndarray:
    """Detect and correct perspective distortion by finding the largest quadrilateral.

    1. Convert to grayscale → Gaussian blur → Canny edge detection
    2. Find contours → filter for largest 4-sided polygon
    3. If valid quad found (area > min_area_ratio × image_area):
       Order corners: top-left, top-right, bottom-right, bottom-left
       Apply cv2.getPerspectiveTransform + cv2.warpPerspective
    4. If no quad found → return original image unchanged

    Only used for scanned/photographed images where perspective distortion
    may prevent accurate grid detection. Not needed for PDF-generated diagrams.
    """
    if not config.perspective_correction:
        return img

    h, w = img.shape[:2]
    min_area = w * h * config.perspective_min_area_ratio

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate to close gaps in edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad: np.ndarray | None = None
    best_area = 0.0

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > min_area and area > best_area:
                best_area = area
                best_quad = approx

    if best_quad is None:
        log.debug("[PERSPECTIVE] No valid quadrilateral found")
        return img

    # Order corners: top-left, top-right, bottom-right, bottom-left
    pts = best_quad.reshape(4, 2).astype(np.float32)
    ordered = _order_corners(pts)

    # Compute output dimensions
    if config.perspective_output_size > 0:
        out_w = out_h = config.perspective_output_size
    else:
        # Use the max width/height from the quad edges
        w_top = np.linalg.norm(ordered[1] - ordered[0])
        w_bot = np.linalg.norm(ordered[2] - ordered[3])
        h_left = np.linalg.norm(ordered[3] - ordered[0])
        h_right = np.linalg.norm(ordered[2] - ordered[1])
        out_w = int(max(w_top, w_bot))
        out_h = int(max(h_left, h_right))

    dst = np.array([
        [0, 0],
        [out_w - 1, 0],
        [out_w - 1, out_h - 1],
        [0, out_h - 1],
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(ordered, dst)
    result = cv2.warpPerspective(img, matrix, (out_w, out_h))

    log.debug("[PERSPECTIVE] Corrected: %dx%d → %dx%d (area=%.0f)",
              w, h, out_w, out_h, best_area)
    return result


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 corner points as: top-left, top-right, bottom-right, bottom-left.

    Uses sum and difference of coordinates:
    - Top-left has smallest sum (x+y)
    - Bottom-right has largest sum
    - Top-right has smallest difference (y-x)
    - Bottom-left has largest difference
    """
    ordered = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).flatten()

    ordered[0] = pts[np.argmin(s)]   # top-left
    ordered[2] = pts[np.argmax(s)]   # bottom-right
    ordered[1] = pts[np.argmin(d)]   # top-right
    ordered[3] = pts[np.argmax(d)]   # bottom-left

    return ordered


def _apply_clahe(img: np.ndarray, config: RecognitionConfig) -> np.ndarray:
    """Apply CLAHE preprocessing to improve contrast.

    Converts to LAB color space, applies CLAHE to the L channel,
    and converts back to BGR.  This is the technique used by
    skolchin/gbr (MIT) for handling uneven lighting in scanned images.
    """
    if not config.clahe_enabled:
        return img

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=config.clahe_clip_limit,
        tileGridSize=(config.clahe_tile_size, config.clahe_tile_size),
    )
    l_ch = clahe.apply(l_ch)

    lab = cv2.merge([l_ch, a_ch, b_ch])
    result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    log.debug("[CLAHE] Applied clip=%.1f tile=%d",
              config.clahe_clip_limit, config.clahe_tile_size)
    return result


def _erase_circles(img: np.ndarray, config: RecognitionConfig) -> np.ndarray:
    """Erase circle-shaped stones so grid lines beneath become visible.

    Uses HoughCircles with multiple blur levels (majority voting) to
    detect stone-like circles.  Each detected circle's bounding box is
    filled with black, then a single white pixel is placed at the
    center so intersecting grid lines can still be found.

    Technique adapted from datavikingr/pdf2sgf (img2sgf.py).  The
    returned image should only be used for *grid detection* — stone
    classification must still run on the original (un-erased) image.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    out = img.copy()

    min_r = config.circle_erasure_min_radius
    max_r = config.circle_erasure_max_radius
    # min_dist between circle centres — at least 2× min_radius
    min_dist = max(min_r * 2, 10)

    all_circles: list[tuple[int, int, int]] = []

    for ksize in (0, 3, 5, 7):
        if ksize > 0:
            blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)
        else:
            blurred = gray

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min_dist,
            param1=80,
            param2=30,
            minRadius=min_r,
            maxRadius=max_r,
        )
        if circles is not None:
            for c in circles[0]:
                all_circles.append((int(c[0]), int(c[1]), int(c[2])))

    if not all_circles:
        log.debug("[CIRCLE_ERASURE] No circles detected")
        return out

    # Deduplicate overlapping detections: keep the one with larger
    # radius when centres are within min_r of each other.
    all_circles.sort(key=lambda c: c[2], reverse=True)
    kept: list[tuple[int, int, int]] = []
    for cx, cy, cr in all_circles:
        if all(
            abs(cx - kx) > min_r or abs(cy - ky) > min_r
            for kx, ky, _ in kept
        ):
            kept.append((cx, cy, cr))

    # Erase each circle's bounding box, place a center pixel.
    for cx, cy, cr in kept:
        x1 = max(cx - cr, 0)
        y1 = max(cy - cr, 0)
        x2 = min(cx + cr, w - 1)
        y2 = min(cy + cr, h - 1)
        out[y1:y2 + 1, x1:x2 + 1] = 0          # black fill
        out[cy, cx] = (255, 255, 255)            # white center pixel

    log.debug("[CIRCLE_ERASURE] Erased %d circles (from %d detections)",
              len(kept), len(all_circles))
    return out


# ---------------------------------------------------------------------------
# Grid detection
# ---------------------------------------------------------------------------


def detect_grid(
    img: np.ndarray,
    config: RecognitionConfig = _DEFAULT_CONFIG,
) -> GridInfo:
    """Detect grid line positions using numpy dark-pixel voting.

    Primary method: vectorised column/row dark-pixel voting — robust
    for clean computer-generated board images (GIF, PNG).  Grid lines
    produce persistent dark columns/rows across many scan lines, while
    stones are localised.

    Post-processing: cluster, filter outliers, fill gaps via median
    spacing interpolation.
    """
    t0 = time.perf_counter()
    grid = _detect_grid_voting(img, config)

    elapsed = (time.perf_counter() - t0) * 1000
    log.debug("[GRID] Final: %dx%d, spacing=%.1fx%.1f, elapsed=%.1fms",
              len(grid.x_lines), len(grid.y_lines),
              grid.x_spacing, grid.y_spacing, elapsed)

    return grid


def _detect_grid_voting(
    img: np.ndarray,
    config: RecognitionConfig,
) -> GridInfo:
    """Fallback: detect grid via pixel-column/row dark-pixel voting.

    Scans rows/columns counting dark pixels.  Grid lines appear as
    persistent dark columns/rows across many scan lines.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # Adaptive threshold scaling for high-res images
    dark_thr_gray = config.dark_threshold // 3  # ~50 in grayscale
    if config.adaptive_grid_threshold:
        # For hi-res images (> 500px), grid lines are thinner per pixel.
        # Raise grayscale threshold to catch lighter gray lines.
        scale = min(max(w, h) / 500.0, 3.0)
        if scale > 1.0:
            dark_thr_gray = min(int(dark_thr_gray * scale), 180)

    dark_mask = gray < dark_thr_gray

    vote_ratio = config.grid_vote_ratio

    # Vote for vertical lines (x positions) by summing columns
    col_sums = np.sum(dark_mask[4:h - 4:2, :], axis=0)
    n_row_scans = len(range(4, h - 4, 2))
    x_thr = n_row_scans * vote_ratio
    cons_x = sorted(int(x) for x in np.where(col_sums > x_thr)[0])

    # Vote for horizontal lines (y positions) by summing rows
    row_sums = np.sum(dark_mask[:, 4:w - 4:2], axis=1)
    n_col_scans = len(range(4, w - 4, 2))
    y_thr = n_col_scans * vote_ratio
    cons_y = sorted(int(y) for y in np.where(row_sums > y_thr)[0])

    x_lines = _cluster_intercepts(cons_x, gap=3)
    y_lines = _cluster_intercepts(cons_y, gap=3)
    x_lines = _filter_lines(x_lines)
    y_lines = _filter_lines(y_lines)

    # Fill gaps where stones occlude grid lines (common in hi-res images)
    x_lines = _complete_grid(x_lines)
    y_lines = _complete_grid(y_lines)

    x_sp = _avg_spacing(x_lines) if len(x_lines) > 1 else 24.0
    y_sp = _avg_spacing(y_lines) if len(y_lines) > 1 else 24.0

    return GridInfo(
        x_lines=tuple(x_lines),
        y_lines=tuple(y_lines),
        x_spacing=x_sp,
        y_spacing=y_sp,
        width=w,
        height=h,
    )


def _cluster_intercepts(positions: list[int], gap: int = 8) -> list[int]:
    """Cluster sorted integers within *gap* distance into centers."""
    if not positions:
        return []
    clusters: list[list[int]] = [[positions[0]]]
    for p in positions[1:]:
        if p - clusters[-1][-1] <= gap:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [sum(c) // len(c) for c in clusters]


def _avg_spacing(lines: list[int]) -> float:
    if len(lines) < 2:
        return 0.0
    gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    return sum(gaps) / len(gaps)


def _filter_lines(lines: list[int]) -> list[int]:
    """Remove lines that break spacing regularity.

    Close pairs (spacing < 55% of median) are resolved by keeping the
    line whose removal creates spacing closer to the median.
    """
    if len(lines) < 3:
        return lines

    for _ in range(3):
        gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
        if not gaps:
            break
        median = sorted(gaps)[len(gaps) // 2]
        threshold = median * 0.55

        to_remove: set[int] = set()
        i = 0
        while i < len(gaps):
            if gaps[i] < threshold:
                if i > 0 and i + 1 < len(gaps):
                    left_gap = gaps[i - 1] + gaps[i]
                    right_gap = gaps[i] + gaps[i + 1]
                    if abs(left_gap - median) <= abs(right_gap - median):
                        to_remove.add(lines[i])
                    else:
                        to_remove.add(lines[i + 1])
                elif i == 0:
                    to_remove.add(lines[0])
                else:
                    to_remove.add(lines[i + 1])
                i += 2
            else:
                i += 1

        if not to_remove:
            break
        lines = [ln for ln in lines if ln not in to_remove]

    return lines


def _complete_grid(lines: list[int]) -> list[int]:
    """Fill gaps in grid lines using median spacing interpolation.

    Inspired by img2sgf.py: detects gaps wider than 1.6× min spacing
    and fills them with evenly-spaced interpolated positions.
    """
    if len(lines) < 2:
        return lines

    gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    min_gap = min(gaps)

    if min_gap < 1:
        return lines

    result = [lines[0]]
    for i, gap in enumerate(gaps):
        n_missing = round(gap / min_gap) - 1
        if n_missing > 0 and n_missing <= 5:
            step = gap / (n_missing + 1)
            for j in range(1, n_missing + 1):
                result.append(int(lines[i] + j * step))
        result.append(lines[i + 1])

    return result


# ---------------------------------------------------------------------------
# Stone classification
# ---------------------------------------------------------------------------


def _classify_single_intersection(
    gray: np.ndarray,
    gx: int, gy: int,
    radius: int,
    config: RecognitionConfig,
) -> str:
    """Classify one intersection on a single grayscale image.

    Returns BLACK, WHITE, or EMPTY based on dark/bright pixel ratios.
    Does NOT apply fill-ratio or diameter post-filters (caller does that).
    """
    h, w = gray.shape
    y1, y2 = max(0, gy - radius), min(h, gy + radius + 1)
    x1, x2 = max(0, gx - radius), min(w, gx + radius + 1)
    roi = gray[y1:y2, x1:x2]
    if roi.size == 0:
        return EMPTY

    roi_h, roi_w = roi.shape
    yy, xx = np.ogrid[:roi_h, :roi_w]
    mask = ((xx - (gx - x1)) ** 2 + (yy - (gy - y1)) ** 2) <= radius * radius
    pixels = roi[mask]
    if len(pixels) == 0:
        return EMPTY

    dark_ratio = float(np.sum(pixels < config.dark_pixel_threshold) / len(pixels))
    bright_ratio = float(np.sum(pixels > config.bright_pixel_threshold) / len(pixels))

    # High-variance check: outlined white stones in clean PDFs have a mix
    # of dark (outline) and bright (interior) pixels, giving high std dev.
    # True black stones are uniformly dark (low std), so std distinguishes them.
    pixel_std = float(np.std(pixels.astype(np.float32)))

    if dark_ratio > config.dark_ratio:
        # High dark_ratio could be solid black OR outlined white.
        # If std is very high, it's an outline surrounding a bright interior.
        if config.outlined_white_detection and pixel_std > 100 and bright_ratio > 0.20:
            return WHITE
        return BLACK
    elif bright_ratio > config.bright_ratio:
        return WHITE
    # Outlined white fallback: stone has dark outline + bright interior → high std,
    # with moderate dark and bright ratios, but below both primary thresholds.
    if config.outlined_white_detection and pixel_std > 100 and dark_ratio > 0.20 and bright_ratio > 0.20:
        return WHITE
    return EMPTY


def classify_intersections(
    img: np.ndarray,
    grid: GridInfo,
    config: RecognitionConfig = _DEFAULT_CONFIG,
) -> list[list[str]]:
    """Classify each grid intersection as empty, black, or white.

    Uses multi-blur majority voting when ``config.blur_kernels`` has
    multiple entries: each kernel produces an independent classification,
    and the final label is the majority vote (ties → EMPTY).

    Post-filters applied after voting:
      - Fill-ratio: reject stones with too few active pixels.
      - Diameter: reject stones whose active-pixel cluster diameter falls
        outside ``stone_min_diameter_ratio``–``stone_max_diameter_ratio``
        of the grid spacing.
    """
    t0 = time.perf_counter()
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    radius = max(3, int(min(grid.x_spacing, grid.y_spacing) * config.stone_sample_ratio))
    edge_margin = max(3, radius // 2)
    circle_area = np.pi * radius * radius
    grid_spacing = min(grid.x_spacing, grid.y_spacing)

    # Build blurred grayscale versions for each kernel
    kernels = config.blur_kernels
    gray_versions: list[np.ndarray] = []
    for k in kernels:
        if k <= 0:
            gray_versions.append(gray)
        else:
            gray_versions.append(cv2.GaussianBlur(gray, (k, k), 0))

    n_versions = len(gray_versions)
    majority_threshold = (n_versions // 2) + 1  # ceil(N/2) for odd N

    board: list[list[str]] = []
    stats = {"black": 0, "white": 0, "empty": 0, "filtered": 0}

    for gy in grid.y_lines:
        row: list[str] = []
        for gx in grid.x_lines:
            # Skip intersections too close to image boundaries
            if gx < edge_margin or gx >= w - edge_margin or gy < edge_margin or gy >= h - edge_margin:
                row.append(EMPTY)
                stats["empty"] += 1
                continue

            # Multi-blur voting
            if n_versions == 1:
                voted = _classify_single_intersection(
                    gray_versions[0], gx, gy, radius, config)
            else:
                votes = {"B": 0, "W": 0, "E": 0}
                for gv in gray_versions:
                    label = _classify_single_intersection(gv, gx, gy, radius, config)
                    if label == BLACK:
                        votes["B"] += 1
                    elif label == WHITE:
                        votes["W"] += 1
                    else:
                        votes["E"] += 1

                if votes["B"] >= majority_threshold:
                    voted = BLACK
                elif votes["W"] >= majority_threshold:
                    voted = WHITE
                else:
                    voted = EMPTY

            # Post-filters only for detected stones
            if voted != EMPTY:
                # Extract ROI on original (unblurred) grayscale for spatial precision
                y1 = max(0, gy - radius)
                y2 = min(h, gy + radius + 1)
                x1 = max(0, gx - radius)
                x2 = min(w, gx + radius + 1)
                roi = gray[y1:y2, x1:x2]
                roi_h, roi_w = roi.shape
                yy, xx = np.ogrid[:roi_h, :roi_w]
                mask = ((xx - (gx - x1)) ** 2 + (yy - (gy - y1)) ** 2) <= radius * radius
                pixels = roi[mask]

                # Fill-ratio post-filter
                if voted == BLACK:
                    active_count = float(np.sum(pixels < config.dark_pixel_threshold))
                else:
                    active_count = float(np.sum(pixels > config.bright_pixel_threshold))

                if active_count < circle_area * config.stone_min_fill_ratio:
                    voted = EMPTY
                    stats["filtered"] += 1
                else:
                    # Diameter post-filter: bounding box of active pixels
                    active_mask = (pixels < config.dark_pixel_threshold) if voted == BLACK else (pixels > config.bright_pixel_threshold)
                    roi_active = np.zeros_like(roi, dtype=np.uint8)
                    roi_active[mask] = active_mask.astype(np.uint8) * 255
                    active_coords = np.argwhere(roi_active > 0)
                    if len(active_coords) >= 2:
                        min_yx = active_coords.min(axis=0)
                        max_yx = active_coords.max(axis=0)
                        eff_diameter = max(max_yx[0] - min_yx[0], max_yx[1] - min_yx[1])
                        if (eff_diameter < grid_spacing * config.stone_min_diameter_ratio or
                                eff_diameter > grid_spacing * config.stone_max_diameter_ratio):
                            voted = EMPTY
                            stats["filtered"] += 1

            if voted == BLACK:
                stats["black"] += 1
            elif voted == WHITE:
                stats["white"] += 1
            else:
                stats["empty"] += 1
            row.append(voted)

        board.append(row)

    elapsed = (time.perf_counter() - t0) * 1000
    if stats["filtered"]:
        log.debug("[STONES] Classified: %d black, %d white, %d empty (%d filtered) (%.1fms)",
                  stats["black"], stats["white"], stats["empty"], stats["filtered"], elapsed)
    else:
        log.debug("[STONES] Classified: %d black, %d white, %d empty (%.1fms)",
                  stats["black"], stats["white"], stats["empty"], elapsed)

    return board


def validate_stone_colors(
    img: np.ndarray,
    grid: GridInfo,
    board: list[list[str]],
    config: RecognitionConfig = _DEFAULT_CONFIG,
) -> dict:
    """Run K-means(k=2) on detected stone intensities as a diagnostic.

    Compares the K-means cluster boundary against fixed thresholds.
    Returns a diagnostic dict with cluster centers, the K-means boundary,
    and a warning flag if the boundary diverges significantly.

    This is a canary — not a replacement for the threshold classifier.
    Call it after classify_intersections() to flag images where the fixed
    thresholds may be unreliable.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    radius = max(3, int(min(grid.x_spacing, grid.y_spacing) * config.stone_sample_ratio))

    intensities: list[tuple[float, str]] = []  # (mean_val, classification)

    for iy, gy in enumerate(grid.y_lines):
        for ix, gx in enumerate(grid.x_lines):
            if iy >= len(board) or ix >= len(board[iy]):
                continue
            cell = board[iy][ix]
            if cell == EMPTY:
                continue

            y1, y2 = max(0, gy - radius), min(h, gy + radius + 1)
            x1, x2 = max(0, gx - radius), min(w, gx + radius + 1)
            roi = gray[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            roi_h, roi_w = roi.shape
            yy, xx = np.ogrid[:roi_h, :roi_w]
            mask = ((xx - (gx - x1)) ** 2 + (yy - (gy - y1)) ** 2) <= radius * radius
            pixels = roi[mask]
            if len(pixels) > 0:
                intensities.append((float(np.mean(pixels)), cell))

    result: dict = {
        "n_black": sum(1 for _, c in intensities if c == BLACK),
        "n_white": sum(1 for _, c in intensities if c == WHITE),
        "warning": False,
        "message": "",
    }

    if result["n_black"] < 2 or result["n_white"] < 2:
        result["message"] = "Not enough stones of both colors for K-means validation"
        return result

    # Run K-means with k=2
    vals = np.array([v for v, _ in intensities], dtype=np.float32).reshape(-1, 1)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels_km, centers = cv2.kmeans(vals, 2, None, criteria, 10, cv2.KMEANS_PP_CENTERS)

    c0, c1 = float(centers[0, 0]), float(centers[1, 0])
    dark_center = min(c0, c1)
    bright_center = max(c0, c1)
    km_boundary = (dark_center + bright_center) / 2.0

    result["dark_center"] = round(dark_center, 1)
    result["bright_center"] = round(bright_center, 1)
    result["km_boundary"] = round(km_boundary, 1)

    # Compare with fixed threshold midpoint (80 for dark, 230 for bright)
    # The fixed thresholds use dark_ratio > 0.55 at pixel < 80
    # and bright_ratio > 0.50 at pixel > 230.
    # A reasonable "boundary" for the fixed system is around 155 (midpoint).
    fixed_midpoint = 155.0
    divergence = abs(km_boundary - fixed_midpoint)

    if divergence > 40:
        result["warning"] = True
        result["message"] = (
            f"K-means boundary ({km_boundary:.0f}) diverges from "
            f"fixed midpoint ({fixed_midpoint:.0f}) by {divergence:.0f}px — "
            f"stone colors may be misclassified on this image"
        )
        log.warning("[STONES] %s", result["message"])
    else:
        result["message"] = (
            f"K-means boundary ({km_boundary:.0f}) consistent with "
            f"fixed thresholds (divergence={divergence:.0f}px)"
        )

    return result


def _refine_with_kmeans(
    img: np.ndarray,
    grid: GridInfo,
    board: list[list[str]],
    config: RecognitionConfig,
) -> list[list[str]]:
    """Refine stone classification using K-means adaptive thresholds.

    When ``config.kmeans_adaptive`` is True and the K-means cluster boundary
    diverges significantly from fixed thresholds, this function adapts the
    dark/bright pixel thresholds from the actual cluster centers and re-runs
    classification.

    Only called from recognize_position() after the initial classification.
    Returns the original board if no adaptation is warranted.
    """
    diag = validate_stone_colors(img, grid, board, config)
    if not diag.get("warning"):
        return board  # fixed thresholds are fine

    dark_center = diag.get("dark_center")
    bright_center = diag.get("bright_center")
    if dark_center is None or bright_center is None:
        return board

    # Derive adapted pixel thresholds from K-means cluster centers.
    # The boundary between clusters sits at (dark_center + bright_center) / 2.
    # Set dark pixel cutoff at boundary - 20%, bright cutoff at boundary + 20%.
    km_boundary = (dark_center + bright_center) / 2.0
    adapted_dark_cutoff = int(km_boundary * 0.8)
    adapted_bright_cutoff = int(km_boundary * 1.2)

    log.info(
        "[KMEANS] Adapting thresholds: dark_cutoff=%d (was 80), bright_cutoff=%d (was 230), "
        "km_boundary=%.0f, dark_center=%.0f, bright_center=%.0f",
        adapted_dark_cutoff, adapted_bright_cutoff, km_boundary,
        dark_center, bright_center,
    )

    # Re-classify with adapted thresholds by creating a temporary config
    # We override the classification logic inline rather than modifying the
    # RecognitionConfig (which uses fixed pixel cutoffs baked into the code).
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    radius = max(3, int(min(grid.x_spacing, grid.y_spacing) * config.stone_sample_ratio))
    edge_margin = max(3, radius // 2)
    circle_area = np.pi * radius * radius
    grid_spacing = min(grid.x_spacing, grid.y_spacing)

    kernels = config.blur_kernels
    gray_versions: list[np.ndarray] = []
    for k in kernels:
        if k <= 0:
            gray_versions.append(gray)
        else:
            gray_versions.append(cv2.GaussianBlur(gray, (k, k), 0))

    n_versions = len(gray_versions)
    majority_threshold = (n_versions // 2) + 1

    new_board: list[list[str]] = []

    for gy in grid.y_lines:
        row: list[str] = []
        for gx in grid.x_lines:
            if gx < edge_margin or gx >= w - edge_margin or gy < edge_margin or gy >= h - edge_margin:
                row.append(EMPTY)
                continue

            if n_versions == 1:
                voted = _classify_single_adaptive(
                    gray_versions[0], gx, gy, radius, config,
                    adapted_dark_cutoff, adapted_bright_cutoff)
            else:
                votes = {"B": 0, "W": 0, "E": 0}
                for gv in gray_versions:
                    label = _classify_single_adaptive(
                        gv, gx, gy, radius, config,
                        adapted_dark_cutoff, adapted_bright_cutoff)
                    if label == BLACK:
                        votes["B"] += 1
                    elif label == WHITE:
                        votes["W"] += 1
                    else:
                        votes["E"] += 1
                if votes["B"] >= majority_threshold:
                    voted = BLACK
                elif votes["W"] >= majority_threshold:
                    voted = WHITE
                else:
                    voted = EMPTY

            # Same post-filters as classify_intersections
            if voted != EMPTY:
                y1, y2 = max(0, gy - radius), min(h, gy + radius + 1)
                x1, x2 = max(0, gx - radius), min(w, gx + radius + 1)
                roi = gray[y1:y2, x1:x2]
                roi_h, roi_w = roi.shape
                yy, xx = np.ogrid[:roi_h, :roi_w]
                mask = ((xx - (gx - x1)) ** 2 + (yy - (gy - y1)) ** 2) <= radius * radius
                pixels = roi[mask]

                active_count = float(np.sum(pixels < adapted_dark_cutoff)) if voted == BLACK else float(np.sum(pixels > adapted_bright_cutoff))
                if active_count < circle_area * config.stone_min_fill_ratio:
                    voted = EMPTY
                else:
                    active_mask = (pixels < adapted_dark_cutoff) if voted == BLACK else (pixels > adapted_bright_cutoff)
                    roi_active = np.zeros_like(roi, dtype=np.uint8)
                    roi_active[mask] = active_mask.astype(np.uint8) * 255
                    active_coords = np.argwhere(roi_active > 0)
                    if len(active_coords) >= 2:
                        min_yx = active_coords.min(axis=0)
                        max_yx = active_coords.max(axis=0)
                        eff_diameter = max(max_yx[0] - min_yx[0], max_yx[1] - min_yx[1])
                        if (eff_diameter < grid_spacing * config.stone_min_diameter_ratio or
                                eff_diameter > grid_spacing * config.stone_max_diameter_ratio):
                            voted = EMPTY

            row.append(voted)
        new_board.append(row)

    # Log the change
    old_b = sum(cell == BLACK for r in board for cell in r)
    old_w = sum(cell == WHITE for r in board for cell in r)
    new_b = sum(cell == BLACK for r in new_board for cell in r)
    new_w = sum(cell == WHITE for r in new_board for cell in r)
    log.info("[KMEANS] Reclassified: black %d→%d, white %d→%d",
             old_b, new_b, old_w, new_w)

    return new_board


def _classify_single_adaptive(
    gray: np.ndarray,
    gx: int, gy: int,
    radius: int,
    config: RecognitionConfig,
    dark_cutoff: int,
    bright_cutoff: int,
) -> str:
    """Classify one intersection with adapted pixel cutoffs."""
    h, w = gray.shape
    y1, y2 = max(0, gy - radius), min(h, gy + radius + 1)
    x1, x2 = max(0, gx - radius), min(w, gx + radius + 1)
    roi = gray[y1:y2, x1:x2]
    if roi.size == 0:
        return EMPTY

    roi_h, roi_w = roi.shape
    yy, xx = np.ogrid[:roi_h, :roi_w]
    mask = ((xx - (gx - x1)) ** 2 + (yy - (gy - y1)) ** 2) <= radius * radius
    pixels = roi[mask]
    if len(pixels) == 0:
        return EMPTY

    dark_ratio = float(np.sum(pixels < dark_cutoff) / len(pixels))
    bright_ratio = float(np.sum(pixels > bright_cutoff) / len(pixels))

    if dark_ratio > config.dark_ratio:
        return BLACK
    elif bright_ratio > config.bright_ratio:
        return WHITE
    return EMPTY


# ---------------------------------------------------------------------------
# Board edge detection
# ---------------------------------------------------------------------------


def detect_board_edges(
    img: np.ndarray,
    grid: GridInfo,
    config: RecognitionConfig = _DEFAULT_CONFIG,
) -> tuple[bool, bool, bool, bool]:
    """Detect which board edges are visible (top, right, bottom, left).

    Board edges are thick (2-3 px) at the first/last grid line.
    Interior lines are thin (1 px).  Thickness is measured at midpoints
    between intersections using numpy array ops.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    dark_thr = config.dark_threshold // 3  # grayscale threshold

    if len(grid.x_lines) < 2 or len(grid.y_lines) < 2:
        return False, False, False, False

    def _h_spans(y_pos: int) -> list[int]:
        spans: list[int] = []
        for i in range(len(grid.x_lines) - 1):
            mx = (grid.x_lines[i] + grid.x_lines[i + 1]) // 2
            count = 0
            for dy in range(-4, 5):
                py = y_pos + dy
                if 0 <= mx < w and 0 <= py < h:
                    if gray[py, mx] < dark_thr:
                        count += 1
            spans.append(count)
        return spans

    def _v_spans(x_pos: int) -> list[int]:
        spans: list[int] = []
        for i in range(len(grid.y_lines) - 1):
            my = (grid.y_lines[i] + grid.y_lines[i + 1]) // 2
            count = 0
            for dx in range(-4, 5):
                px = x_pos + dx
                if 0 <= px < w and 0 <= my < h:
                    if gray[my, px] < dark_thr:
                        count += 1
            spans.append(count)
        return spans

    def _avg(spans: list[int]) -> float:
        return sum(spans) / len(spans) if spans else 0.0

    def _min_span(spans: list[int]) -> int:
        """Minimum span: board edges are thick at EVERY midpoint; interior
        lines have zero/thin spans between the sections where stones inflate them."""
        return min(spans) if spans else 0

    top_spans = _h_spans(grid.y_lines[0])
    bot_spans = _h_spans(grid.y_lines[-1])
    left_spans = _v_spans(grid.x_lines[0])
    right_spans = _v_spans(grid.x_lines[-1])

    top_t = _avg(top_spans)
    bot_t = _avg(bot_spans)
    left_t = _avg(left_spans)
    right_t = _avg(right_spans)

    # Measure multiple interior lines and use 25th-percentile thickness.
    # Stones inflate interior line averages; the 25th percentile resists
    # outliers from stone-heavy columns/rows.
    interior_h_vals = sorted(
        _avg(_h_spans(grid.y_lines[i]))
        for i in range(1, len(grid.y_lines) - 1)
    )
    interior_v_vals = sorted(
        _avg(_v_spans(grid.x_lines[i]))
        for i in range(1, len(grid.x_lines) - 1)
    )
    interior_h = interior_h_vals[len(interior_h_vals) // 4] if interior_h_vals else 0.0
    interior_v = interior_v_vals[len(interior_v_vals) // 4] if interior_v_vals else 0.0

    def _is_edge(boundary_avg: float, interior: float, boundary_spans: list[int]) -> bool:
        # Primary: boundary must be thicker than interior
        thick_enough = boundary_avg > max(
            interior * config.edge_thickness_ratio,
            config.edge_min_thickness,
        )
        # Secondary: board edges are uniformly thick. If the minimum span
        # is ≥ 2, the line is thick at every midpoint (not just near stones).
        uniformly_thick = _min_span(boundary_spans) >= 2
        return thick_enough or (uniformly_thick and boundary_avg >= config.edge_min_thickness)

    has_top = _is_edge(top_t, interior_h, top_spans)
    has_bot = _is_edge(bot_t, interior_h, bot_spans)
    has_left = _is_edge(left_t, interior_v, left_spans)
    has_right = _is_edge(right_t, interior_v, right_spans)

    log.debug("[EDGES] top=%s right=%s bottom=%s left=%s (thickness: T=%.1f B=%.1f L=%.1f R=%.1f int_h=%.1f int_v=%.1f)",
              has_top, has_right, has_bot, has_left, top_t, bot_t, left_t, right_t, interior_h, interior_v)

    return has_top, has_right, has_bot, has_left


def _compute_origin(
    grid: GridInfo,
    has_top: bool,
    has_right: bool,
    has_bottom: bool,
    has_left: bool,
    board_size: int = 19,
) -> tuple[int, int]:
    """Return (row_origin, col_origin) of the top-left visible intersection."""
    n_rows = len(grid.y_lines)
    n_cols = len(grid.x_lines)

    if has_left:
        col = 0
    elif has_right:
        col = board_size - n_cols
    else:
        col = (board_size - n_cols) // 2

    if has_top:
        row = 0
    elif has_bottom:
        row = board_size - n_rows
    else:
        row = (board_size - n_rows) // 2

    return row, col


# ---------------------------------------------------------------------------
# Digit detection — OpenCV contour + template matching
# ---------------------------------------------------------------------------

# Module-level template cache (per template set)
_template_cache: dict[str, tuple[dict[int, np.ndarray], dict[tuple[int, str], np.ndarray]]] = {}
_TEMPLATE_DIRS: dict[str, Path] = {
    "default": Path(__file__).parent / "digit_templates",
    "pdf": Path(__file__).parent / "digit_templates_pdf",
}
# Legacy aliases for backward compat
_digit_templates: dict[int, np.ndarray] | None = None
_color_templates: dict[tuple[int, str], np.ndarray] | None = None
_TEMPLATE_DIR = _TEMPLATE_DIRS["default"]
_TEMPLATE_SIZE = (10, 14)  # width, height for normalized digit images

# Map stone color codes to template filename suffixes
_COLOR_SUFFIX = {BLACK: "black", WHITE: "white"}


def _load_templates(template_set: str = "default") -> dict[int, np.ndarray]:
    """Load digit templates from .npy files. Cached per template set."""
    global _digit_templates, _color_templates

    if template_set in _template_cache:
        return _template_cache[template_set][0]

    template_dir = _TEMPLATE_DIRS.get(template_set, _TEMPLATE_DIRS["default"])

    dt: dict[int, np.ndarray] = {}
    ct: dict[tuple[int, str], np.ndarray] = {}

    if template_dir.exists():
        for digit in range(10):
            path = template_dir / f"digit_{digit}.npy"
            if path.exists():
                dt[digit] = np.load(str(path))
            for color_code, suffix in _COLOR_SUFFIX.items():
                cpath = template_dir / f"digit_{digit}_{suffix}.npy"
                if cpath.exists():
                    ct[(digit, color_code)] = np.load(str(cpath))
        log.debug("[DIGIT] Loaded %d universal + %d color-specific templates (set=%s)",
                  len(dt), len(ct), template_set)
    else:
        log.debug("[DIGIT] Template directory not found: %s", template_dir)

    _template_cache[template_set] = (dt, ct)

    # Update legacy globals for backward compat
    if template_set == "default":
        _digit_templates = dt
        _color_templates = ct

    return dt


def detect_digit(
    img: Image.Image | np.ndarray,
    cx: int,
    cy: int,
    stone_color: str,
    radius: int = 7,
    config: RecognitionConfig = _DEFAULT_CONFIG,
    templates: dict[int, np.ndarray] | None = None,
) -> DigitDetectionResult:
    """Detect a move-number digit drawn on a stone using OpenCV.

    Uses thresholding + connected component analysis to extract digit
    contours, then classifies via template matching (if available) or
    structural feature analysis.

    Supports multi-digit numbers (10-18) by detecting multiple
    digit components sorted left-to-right.

    Args:
        templates: Optional dict of digit templates to use instead of
            the global cached templates. Used for cross-validation
            where per-fold templates must be injected.

    Returns:
        DigitDetectionResult with digit (1-18 or 0), confidence,
        method, rule_name, runner_up, and feature diagnostics.
    """
    # Convert PIL to numpy if needed
    if isinstance(img, Image.Image):
        img_arr = np.array(img.convert("RGB"))
        img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img

    h, w = img_bgr.shape[:2]
    r = radius

    # Extract ROI
    y1 = max(0, cy - r)
    y2 = min(h, cy + r + 1)
    x1 = max(0, cx - r)
    x2 = min(w, cx + r + 1)
    roi = img_bgr[y1:y2, x1:x2]

    if roi.size == 0:
        return DigitDetectionResult()

    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    roi_h, roi_w = roi_gray.shape

    # Threshold to isolate digit pixels (contrasting with stone)
    if stone_color == BLACK:
        # Bright digits on dark stone
        _, thresh = cv2.threshold(roi_gray, config.digit_bright_threshold, 255, cv2.THRESH_BINARY)
    else:
        # Dark digits on bright stone
        _, thresh = cv2.threshold(roi_gray, config.digit_dark_threshold, 255, cv2.THRESH_BINARY_INV)

    # Connected components analysis
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)

    if n_labels <= 1:
        return DigitDetectionResult()  # Only background

    # Filter components
    roi_area = roi_h * roi_w
    min_area = config.digit_min_area
    max_area = int(roi_area * config.digit_max_area_ratio)

    valid_components: list[tuple[int, int, int, int, int, int]] = []  # (x, y, w, h, area, label_id)
    for label_id in range(1, n_labels):
        area = stats[label_id, cv2.CC_STAT_AREA]
        comp_x = stats[label_id, cv2.CC_STAT_LEFT]
        comp_y = stats[label_id, cv2.CC_STAT_TOP]
        comp_w = stats[label_id, cv2.CC_STAT_WIDTH]
        comp_h = stats[label_id, cv2.CC_STAT_HEIGHT]

        if area < min_area or area > max_area:
            continue

        # Filter by aspect ratio — digits are taller than wide
        if comp_w > 0 and comp_h > 0:
            aspect = comp_h / comp_w
            if aspect < 0.5 or aspect > 6.0:
                continue

        valid_components.append((comp_x, comp_y, comp_w, comp_h, area, label_id))

    if not valid_components:
        return DigitDetectionResult()

    # Keep only the largest connected cluster near the center
    valid_components = _filter_to_central_cluster(valid_components, roi_w, roi_h)

    if not valid_components:
        return DigitDetectionResult()

    # Sort left-to-right for multi-digit detection
    valid_components.sort(key=lambda c: c[0])

    # Determine if multi-digit (two separate components side by side)
    is_multi_digit = False
    if len(valid_components) >= 2:
        # Check if the gap between components suggests two separate digits
        c1 = valid_components[0]
        c2 = valid_components[1]
        gap = c2[0] - (c1[0] + c1[2])
        c2_touches_edge = c2[0] + c2[2] >= roi_w
        c1_touches_edge = c1[0] == 0
        if (gap >= 1 and c1[2] >= 2 and c2[2] >= 2
                and c1[4] >= min_area and c2[4] >= min_area
                and max(c1[3], c2[3]) <= 2 * min(c1[3], c2[3])
                and not c1_touches_edge and not c2_touches_edge):
            is_multi_digit = True

    if is_multi_digit and len(valid_components) >= 2:
        r1 = _classify_component(thresh, labels, valid_components[0], config, templates, stone_color)
        r2 = _classify_component(thresh, labels, valid_components[1], config, templates, stone_color)
        if r1.digit is not None and r2.digit is not None and r1.digit == 1 and 0 <= r2.digit <= 9:
            multi_digit = r1.digit * 10 + r2.digit
            if 10 <= multi_digit <= 18:
                return DigitDetectionResult(
                    digit=multi_digit,
                    confidence=min(r1.confidence, r2.confidence),
                    method="multi_digit",
                    rule_name=f"multi_{r1.rule_name}+{r2.rule_name}",
                    features={"d1": r1.features, "d2": r2.features},
                )

    # Single digit — prefer the component closest to ROI center.
    # When adjacent stones' digit strokes leak into the ROI, the neighbor's
    # component can be larger but is always farther from center.
    cx_roi, cy_roi = roi_w / 2.0, roi_h / 2.0
    def _centrality_score(c: tuple[int, int, int, int, int, int]) -> float:
        comp_cx = c[0] + c[2] / 2.0
        comp_cy = c[1] + c[3] / 2.0
        dist = ((comp_cx - cx_roi) ** 2 + (comp_cy - cy_roi) ** 2) ** 0.5
        return -dist + c[4] * 0.01

    main_comp = max(valid_components, key=_centrality_score)
    return _classify_component(thresh, labels, main_comp, config, templates, stone_color)


def _filter_to_central_cluster(
    components: list[tuple[int, int, int, int, int, int]],
    roi_w: int,
    roi_h: int,
) -> list[tuple[int, int, int, int, int, int]]:
    """Keep components close to the ROI center. Removes stray edge pixels
    and grid-line artifacts touching the ROI boundary."""
    cx, cy = roi_w / 2, roi_h / 2
    max_dist = max(roi_w, roi_h) * 0.6

    filtered = []
    for comp in components:
        comp_x, comp_y, comp_w, comp_h = comp[0], comp[1], comp[2], comp[3]
        comp_cx = comp_x + comp_w / 2
        comp_cy = comp_y + comp_h / 2
        dist = ((comp_cx - cx) ** 2 + (comp_cy - cy) ** 2) ** 0.5
        if dist > max_dist:
            continue

        # Skip narrow components touching the left/right ROI edge — likely
        # grid lines or board-edge artifacts, not digit strokes.
        touches_left = comp_x == 0
        touches_right = comp_x + comp_w >= roi_w
        if (touches_left or touches_right) and comp_w <= 3:
            continue

        filtered.append(comp)

    return filtered


def _classify_component(
    thresh: np.ndarray,
    labels: np.ndarray,
    component: tuple[int, int, int, int, int, int],
    config: RecognitionConfig,
    templates: dict[int, np.ndarray] | None = None,
    stone_color: str = "",
) -> DigitDetectionResult:
    """Classify a single connected component as a digit 0-9.

    Uses template matching if templates are loaded, otherwise falls
    back to structural feature analysis. When stone_color is provided
    and color-specific templates exist, those are tried first for
    better accuracy on digits that look different on black vs white.
    """
    comp_x, comp_y, comp_w, comp_h, area, label_id = component

    # Extract the component mask
    comp_mask = (labels[comp_y:comp_y + comp_h, comp_x:comp_x + comp_w] == label_id).astype(np.uint8) * 255

    # Normalize to template size
    if comp_mask.shape[0] < 2 or comp_mask.shape[1] < 2:
        return DigitDetectionResult()

    normalized = cv2.resize(comp_mask, _TEMPLATE_SIZE, interpolation=cv2.INTER_AREA)

    # --- Template matching ---
    # Track whether we're using global (cached) templates vs injected ones
    using_global = templates is None
    if templates is None:
        templates = _load_templates(config.digit_template_set)

    # Build effective template set: prefer color-specific over universal,
    # but only when using global templates (not injected CV-fold templates)
    effective_templates = dict(templates)
    if using_global and stone_color:
        _, ct = _template_cache.get(config.digit_template_set, ({}, {}))
        if ct:
            for digit in range(10):
                key = (digit, stone_color)
                if key in ct:
                    effective_templates[digit] = ct[key]

    if effective_templates:
        best_digit = None
        best_score = -1.0
        second_digit = None
        second_score = -1.0
        for digit, tmpl in effective_templates.items():
            result = cv2.matchTemplate(normalized, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(result[0, 0]) if result.size == 1 else float(np.max(result))
            if score > best_score:
                second_digit = best_digit
                second_score = best_score
                best_score = score
                best_digit = digit
            elif score > second_score:
                second_digit = digit
                second_score = score

        if best_digit is not None and best_score >= config.template_match_threshold:
            # Also get feature analysis for diagnostics
            _, rule_name, feats = _classify_by_features(comp_mask, comp_w, comp_h, area)
            feats["template_score"] = round(best_score, 4)
            feats["template_margin"] = round(best_score - second_score, 4) if second_score > -1.0 else 0.0
            return DigitDetectionResult(
                digit=best_digit,
                confidence=best_score,
                method="template",
                rule_name=f"template_d{best_digit}",
                runner_up=second_digit if second_digit is not None else 0,
                runner_up_score=second_score,
                features=feats,
            )

    # --- Fallback: structural feature analysis ---
    digit, rule_name, feats = _classify_by_features(comp_mask, comp_w, comp_h, area)
    if digit is not None:
        # Heuristic confidence: 0.6 base, reduced if features are borderline
        conf = 0.6
        return DigitDetectionResult(
            digit=digit,
            confidence=conf,
            method="feature",
            rule_name=rule_name,
            features=feats,
        )
    return DigitDetectionResult(features=feats, rule_name=rule_name)


def _classify_by_features(
    mask: np.ndarray,
    bbox_w: int,
    bbox_h: int,
    total: int,
) -> tuple[int | None, str, dict]:
    """Classify digit by structural features (fallback when no templates).

    Uses zone distribution, horizontal bars, column fill patterns,
    top/bottom row fill, and contour topology.

    Returns:
        (digit, rule_name, features_dict) where digit is None if unclassified.
    """
    if bbox_h < 3 or bbox_w < 1:
        return None, "too_small", {}

    # --- Feature extraction ---

    # Zone distribution (3x3 grid)
    zone_h = max(bbox_h / 3, 1)
    zone_w = max(bbox_w / 3, 1)
    zones = [[0] * 3 for _ in range(3)]
    ys, xs = np.where(mask > 0)
    for y, x in zip(ys, xs):
        zr = min(2, int(y / zone_h))
        zc = min(2, int(x / zone_w))
        zones[zr][zc] += 1

    # Top and bottom row fill
    top_fill = int(np.sum(mask[0, :] > 0))
    bot_fill = int(np.sum(mask[-1, :] > 0))

    # Left/right column fill
    left_col = int(np.sum(mask[:, 0] > 0))
    right_col = int(np.sum(mask[:, -1] > 0))

    # Left/right halves
    mid_x = bbox_w // 2
    left_half = int(np.sum(mask[:, :mid_x] > 0))
    right_half = total - left_half

    # Horizontal bar in middle 40%
    mid_start = int(bbox_h * 0.3)
    mid_end = int(bbox_h * 0.7)
    has_h_bar = False
    for y in range(mid_start, mid_end + 1):
        if y < bbox_h:
            row_count = int(np.sum(mask[y, :] > 0))
            if row_count >= bbox_w - 1:
                has_h_bar = True
                break

    # Zone totals
    top_zone = zones[0][0] + zones[0][1] + zones[0][2]
    bot_zone = zones[2][0] + zones[2][1] + zones[2][2]

    # Hole detection via contour hierarchy
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    n_holes = 0
    if hierarchy is not None and len(hierarchy) > 0:
        for i in range(len(hierarchy[0])):
            # Inner contour (has a parent)
            if hierarchy[0][i][3] >= 0:
                n_holes += 1

    # Aspect ratio for width vs height
    aspect = bbox_h / bbox_w if bbox_w > 0 else 0

    # Build features dict for diagnostics
    feats = {
        "bbox_w": int(bbox_w), "bbox_h": int(bbox_h), "total": int(total),
        "aspect": round(aspect, 2),
        "top_fill": int(top_fill), "bot_fill": int(bot_fill),
        "left_col": int(left_col), "right_col": int(right_col),
        "left_half": int(left_half), "right_half": int(right_half),
        "has_h_bar": has_h_bar, "n_holes": int(n_holes),
        "top_zone": int(top_zone), "bot_zone": int(bot_zone),
        "zones": [[int(c) for c in row] for row in zones],
    }

    # --- Classification rules ---
    # Rule ordering matters: specific structural rules first, then
    # hole-based rules, then fallbacks.

    # 1: Narrow vertical stroke
    if bbox_w <= 2:
        return 1, "R1_narrow", feats
    if bbox_w <= 4 and zones[1][0] == 0 and zones[2][0] == 0:
        return 1, "R1_narrow_left_empty", feats

    # 7: Top row nearly full, rest tapers, bottom-right empty.
    # Guards: left_col sparse, middle-left zone empty.
    if (top_fill >= bbox_w - 1 and zones[2][2] == 0 and bot_fill <= 3
            and left_col <= 2 and zones[1][0] == 0):
        return 7, "R7_top_full", feats
    # 7 alt: Wide bounding box (aspect < 0.7) — catches wide 7s.
    if (aspect < 0.7 and top_fill <= 2 and bot_fill >= bbox_w - 1
            and left_col <= 2 and right_half > left_half and zones[1][0] == 0):
        return 7, "R7_wide", feats

    # 4: Has h-bar with right-heavy weight, LEFT COLUMN SPARSE (≤2).
    if has_h_bar and right_half > left_half and n_holes <= 1:
        if left_col <= 2 and zones[1][0] == 0:
            return 4, "R4_hbar_right", feats

    # 5: Has h-bar AND top row full AND left column dense.
    if (has_h_bar and top_fill >= bbox_w - 1 and left_col >= bbox_h // 2
            and bot_fill < bbox_w - 1):
        return 5, "R5_hbar_top_full", feats

    # 6 early: hole + dense left column + sparse bottom row.
    if n_holes >= 1 and left_col >= bbox_h // 2 and bot_fill <= 2:
        return 6, "R6_hole_left_dense", feats

    # 6 open: No hole but characteristic 6 shape.
    if (n_holes == 0 and bot_fill >= bbox_w - 1 and top_fill < bbox_w - 1
            and right_col > bbox_h // 2 and aspect > 0.8 and bot_zone >= top_zone):
        return 6, "R6_open", feats

    # 2: Bottom row full, top row partial, no hole, aspect > 0.8.
    if (bot_fill >= bbox_w - 1 and top_fill < bbox_w - 1 and n_holes == 0
            and aspect > 0.8 and right_col <= bbox_h // 2):
        return 2, "R2_bot_full", feats

    # 4 alt: h-bar, 1 hole, sparse top/bottom fill.
    if has_h_bar and n_holes == 1 and top_fill <= 2 and bot_fill <= 2:
        return 4, "R4_hbar_hole", feats

    # 8: Two or more holes
    if n_holes >= 2:
        return 8, "R8_two_holes", feats

    # 9: Hole + dense left AND right columns.
    if n_holes >= 1 and left_col >= 3 and right_col >= 3:
        if top_zone >= bot_zone:
            return 9, "R9_hole_dense_cols", feats

    # 0: Has a hole, symmetrical, BOTH rows well-filled.
    if n_holes >= 1 and abs(top_zone - bot_zone) <= max(total * 0.20, 3):
        if bot_fill >= bbox_w - 2 and top_fill >= bbox_w - 2:
            return 0, "R0_hole_symmetric", feats

    # 9: Has a hole, top-heavy
    if n_holes >= 1 and top_zone > bot_zone + 1:
        return 9, "R9_hole_top_heavy", feats

    # 6: Has a hole, bottom-heavy
    if n_holes >= 1 and bot_zone > top_zone + 1:
        return 6, "R6_hole_bot_heavy", feats

    # 6 alt: left column dense, bottom-heavy (even without detected hole)
    if left_col >= bbox_h * 2 // 3 and bot_zone > top_zone:
        return 6, "R6_alt_left_dense", feats

    # 2 alt: Bottom row full, aspect > 0.8, right_col sparse
    if (bot_fill >= bbox_w - 1 and top_fill < bbox_w - 1 and aspect > 0.8
            and right_col <= bbox_h // 2):
        return 2, "R2_alt", feats

    # 3: Right-heavy with low left-column density
    if right_half > left_half + 2 and left_col <= 2:
        return 3, "R3_right_heavy", feats
    if right_col >= bbox_h * 2 // 3 and left_col <= 2:
        return 3, "R3_right_col_dense", feats

    # --- Fallback heuristics ---
    if n_holes >= 1:
        if left_col >= bbox_h // 2 and bot_fill <= 2:
            return 6, "FB_hole_left_dense", feats
        if top_zone > bot_zone:
            return 9, "FB_hole_top_heavy", feats
        elif bot_zone > top_zone:
            return 6, "FB_hole_bot_heavy", feats
        return 8, "FB_hole_default", feats

    if bot_fill > top_fill + 1 and aspect > 0.8:
        return 2, "FB_bot_heavy", feats
    if right_half > left_half + 1:
        return 3, "FB_right_heavy", feats
    if top_fill >= bbox_w - 1:
        return 5, "FB_top_full", feats

    return None, "unclassified", feats


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def recognize_position(
    image: Image.Image | str | Path,
    board_size: int = 19,
    config: RecognitionConfig | None = None,
) -> RecognizedPosition:
    """Recognize a Go board position from a raster image.

    Args:
        image: PIL Image, numpy array, or path to an image file.
        board_size: Expected full board size (default 19).
        config: Optional recognition thresholds.

    Returns:
        RecognizedPosition with grid, stones, and coordinate mapping.
    """
    t0 = time.perf_counter()
    cfg = config or _DEFAULT_CONFIG

    img_bgr, source = _to_numpy(image)
    h, w = img_bgr.shape[:2]

    log.debug("[RECOGNIZE] Start: %dx%d source=%s", w, h,
              Path(source).name if source else "<in-memory>")

    # Perspective correction for skewed scans (before any other preprocessing)
    img_bgr = _correct_perspective(img_bgr, cfg)

    # Apply CLAHE preprocessing if enabled (for PDF / scanned sources)
    img_bgr = _apply_clahe(img_bgr, cfg)

    # Erase circles (stones) before grid detection so grid lines
    # obscured by stones become visible. Uses the original image for
    # stone classification later — only the grid-detection input is cleaned.
    if cfg.circle_erasure:
        grid_input = _erase_circles(img_bgr, cfg)
    else:
        grid_input = img_bgr

    grid = detect_grid(grid_input, cfg)
    board = classify_intersections(img_bgr, grid, cfg)

    # K-means adaptive refinement (opt-in)
    if cfg.kmeans_adaptive:
        board = _refine_with_kmeans(img_bgr, grid, board, cfg)

    has_top, has_right, has_bottom, has_left = detect_board_edges(img_bgr, grid, cfg)
    row_origin, col_origin = _compute_origin(
        grid, has_top, has_right, has_bottom, has_left, board_size,
    )

    elapsed = (time.perf_counter() - t0) * 1000
    bc, wc = 0, 0
    for row in board:
        for cell in row:
            if cell == BLACK:
                bc += 1
            elif cell == WHITE:
                wc += 1

    log.debug("[RECOGNIZE] Done: grid=%dx%d stones=%dB/%dW edges=%s origin=(%d,%d) elapsed=%.1fms",
              len(grid.x_lines), len(grid.y_lines), bc, wc,
              "".join(s for s, f in [("T", has_top), ("R", has_right), ("B", has_bottom), ("L", has_left)] if f) or "none",
              row_origin, col_origin, elapsed)

    return RecognizedPosition(
        grid=grid,
        board=board,
        board_top=row_origin,
        board_left=col_origin,
        has_top_edge=has_top,
        has_bottom_edge=has_bottom,
        has_left_edge=has_left,
        has_right_edge=has_right,
        source_file=source,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_position(pos: RecognizedPosition) -> str:
    """Pretty-print a recognised position for visual verification."""
    edges = ", ".join(
        s
        for s, f in [
            ("top", pos.has_top_edge),
            ("right", pos.has_right_edge),
            ("bottom", pos.has_bottom_edge),
            ("left", pos.has_left_edge),
        ]
        if f
    ) or "none"

    bc, wc = pos.stone_count()
    lines = [
        f"Source: {Path(pos.source_file).name}" if pos.source_file else "Source: <in-memory>",
        f"Grid: {pos.n_cols}×{pos.n_rows}  "
        f"spacing: {pos.grid.x_spacing:.1f}×{pos.grid.y_spacing:.1f}",
        f"Edges: {edges}",
        f"Origin: row={pos.board_top}, col={pos.board_left}",
        f"Stones: {bc} black, {wc} white",
        "",
    ]

    col_labels = [str(pos.board_left + i) for i in range(pos.n_cols)]
    lines.append("     " + " ".join(f"{c:>2}" for c in col_labels))

    for iy, row in enumerate(pos.board):
        r = pos.board_top + iy
        cells = " ".join(f"{c:>2}" for c in row)
        lines.append(f"  {r:2d}  {cells}")

    return "\n".join(lines)
