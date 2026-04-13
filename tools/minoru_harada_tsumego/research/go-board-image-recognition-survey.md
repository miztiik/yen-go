# Go Board Image Recognition — External Library Survey

*Research date: 2026-04-11*

A survey of 5 open-source Go board image recognition tools. The goal is to catalog techniques, identify modularizable patterns, and extract ideas that could improve our own `image_to_board.py` pipeline. **None of this code should be imported or referenced directly** — this is inspiration-only research.

---

## Repositories Analyzed

| Repo | Author | Language | Approach | Status |
|------|--------|----------|----------|--------|
| [hanysz/img2sgf](https://github.com/hanysz/img2sgf) | Alexander Hanysz | Python | Classical CV (OpenCV + sklearn) | Archived Oct 2023 |
| [noword/image2sgf](https://github.com/noword/image2sgf) | noword | Python | Deep learning (PyTorch) + classical fallback | Active (v0.07, Apr 2023) |
| [shanleiguang/vQi](https://github.com/shanleiguang/vQi) | shanleiguang | Perl | SGF-to-image (NOT recognition) | Active |
| [chaossy/goban-image-reader](https://github.com/chaossy/goban-image-reader) | chaossy | Python | Deep learning (Keras/ResNet-34) | Stale (Aug 2018) |
| [JoeHowarth/GoScanner](https://github.com/JoeHowarth/GoScanner) | Joe Howarth | Python | Classical CV + Keras CNN | Non-working (3 commits) |

**Note:** vQi converts SGF files into Chinese ancient-style board images (the inverse direction). Included because it was in the original list, but no recognition techniques to extract.

---

## 1. Grid / Board Detection

### 1a. Circles-First Strategy (hanysz/img2sgf)

The key insight: **detect stones before grid lines**. Stone edges produce false positives in line detection. By finding circles first, masking them, then detecting lines, the grid becomes cleaner.

**Pipeline:**
1. Preprocess: contrast adjust, grayscale, Gaussian blur at 4 blur levels (kernel 1, 3, 5, 7)
2. Hough Circle Transform (`cv.HOUGH_GRADIENT`, dp=1, minDist=10, param1=100, param2=30, rMin=1, rMax=30) — run on ALL blur variants, results stacked
3. For each circle: erase bounding box (r+2 padding), replace with single center pixel
4. Canny edge detection on masked image
5. Hough line transform on edge image, theta restricted to near-horizontal or near-vertical (1 degree tolerance)
6. Agglomerative clustering (sklearn, single linkage, distance threshold = 10px) to merge duplicate lines
7. Grid completion: gap-fill missing lines via median-spacing interpolation

**Partial board handling:** If fewer than 19 lines detected, interpolate gaps. If 20 lines → drop caption line. If 21 → drop bounding box lines. User-selectable alignment (TL/TR/BL/BR) maps partial boards to full 19x19.

**Stone filtering after grid:** Diameter must be 60–130% of grid spacing. Rejects noise circles that don't match board scale.

**Relevance to Harada pipeline:** Our pipeline targets printed diagrams (like img2sgf), not photographs. The circles-first masking is a strong idea — our current grid detection doesn't mask stones first, so stone-on-line intersections may confuse dark-pixel voting. However, Harada GIF images have clean grid lines (no anti-aliasing or variable thickness), so this may be over-engineering for our case.

### 1b. CNN Corner Detection + Perspective Transform (noword/image2sgf)

Uses FCOS (Fully Convolutional One-Stage) anchor-free detector with ResNet-50 + FPN backbone to locate 4 board corners directly.

**Pipeline:**
1. Expand image to square (pad with most-frequent-color background)
2. Run FCOS model (4 corner classes + background, max 8 detections)
3. NMS with IoU threshold 0.1
4. Extract top-left corner of each corner bounding box as source points
5. `cv2.getPerspectiveTransform` → `cv2.warpPerspective` → 1024x1024 rectified board

**Relevance:** Not applicable to Harada — our images are already flat, axis-aligned GIF diagrams with no perspective distortion. But the approach of detecting corners as objects (rather than lines) is a fundamentally different paradigm worth noting.

### 1c. Document-Scanner Approach (GoScanner)

Classical contour-based: resize to 500px height, Canny edge detection (75/200), find contours sorted by area, approximate largest quadrilateral via `approxPolyDP` (epsilon = 2% perimeter), then `four_point_transform` from pyimagesearch.

**Relevance:** Incomplete implementation (grid segmentation never built). The contour-quad approach is standard document scanning, nothing novel here.

---

## 2. Stone Detection & Classification

### 2a. Pixel Intensity Thresholding (hanysz/img2sgf)

For each stone position: compute mean pixel intensity in a neighborhood spanning one grid cell. Threshold at 128 (adjustable via interactive histogram). Below = black, above = white.

**Relevance:** Our pipeline uses a similar approach (`classify_intersections` in `image_to_board.py` with dark/bright pixel ratios). The interactive histogram-threshold idea is interesting for debugging but not needed for our batch pipeline.

### 2b. CNN Per-Intersection Classifier (noword/image2sgf)

After perspective correction to canonical 1024x1024:
1. Divide into 19x19 grid cells using `NpBoxPostion` lookup table
2. Extract all 361 cells, batch into single tensor
3. Run EfficientNet-B3 classifier (6 classes: empty, black, white + possibly marked variants)
4. `argmax` per cell

This achieves the cleanest separation of concerns: grid geometry is entirely deterministic after perspective correction, and all intelligence goes into the classifier.

**Also provides a K-means fallback** (classical CV):
1. Hough circles on multiple blur variants (same as hanysz approach)
2. Snap each circle to nearest grid intersection
3. Extract average BGR color for each stone region
4. K-means (k=2) on color vectors → separate black/white
5. Cluster with higher total intensity = white

**Relevance:** The K-means color clustering is a neat alternative to fixed thresholds. Instead of deciding "black < 128 < white", let the data decide. Could be useful if our images have varying brightness levels across years.

### 2c. ResNet-34 Full-Board Classifier (chaossy/goban-image-reader)

Single model outputs 361 × 3 predictions simultaneously (one 3-class softmax per intersection):
- ResNet-34 variant: 7x7 stem, [2,2,3,2] blocks, [64,128,256,512] filters
- 7x7 AveragePooling → Flatten → 361 separate Dense(3, softmax) heads
- Trained on synthetic board images, fine-tuned on real photographs
- Per-intersection accuracy: ~99.8%, whole-board accuracy: ~72%

**Key insight:** 99.8% per-intersection still yields only 72% whole-board accuracy because 0.998^361 ≈ 48.5%. The compounding error makes per-position accuracy requirements extreme for full-board recognition.

**Relevance:** Our puzzles are partial boards (typically 4x4 to 8x8 regions, not full 19x19), so compounding is less severe. But the lesson stands: even small per-stone error rates matter. Our current 100% stone detection accuracy is critical.

### 2d. Synthetic Training Data (noword/image2sgf, chaossy/goban-image-reader)

Both projects generate artificial board images for training:
- **noword**: `gogame_generator.py` with random stone placement, pixel-level jitter (±1px), random scaling ratio, alpha-composited stone images, partial board cropping
- **chaossy**: Synthetic boards for initial training, real photographs for fine-tuning

**Relevance:** Not directly applicable (we don't train neural nets), but the concept of generating ground truth data programmatically is valuable. Our `eval_digit_detection.py` evaluation framework follows a similar philosophy — known-good data enables iterative improvement.

---

## 3. Digit / Move Number Detection

**None of the 5 repositories implement digit or move number detection.**

- **hanysz/img2sgf**: Explicitly notes it "does a reasonable job of ignoring stone numbers, marks and annotations"
- **noword/image2sgf**: 6-class stone classifier may handle some markup, but no digit reading
- **chaossy/goban-image-reader**: Position-only, no move numbers
- **GoScanner**: Position-only, no move numbers
- **vQi**: Renders digits onto images (the inverse problem)

This confirms that **digit detection on Go board images is a niche, largely unsolved problem in open-source tools**. Our `detect_digit()` pipeline with connected component analysis + structural feature classification is novel in this space.

---

## 4. SGF Generation

| Repo | SGF Method | Approach |
|------|------------|----------|
| hanysz/img2sgf | Manual string building | `"(;GM[1]FF[4]SZ[19]"` + coordinate concatenation |
| noword/image2sgf | `sgfmill` library | `sgf.Sgf_game(size=19)`, `root_node.set_setup_stones(blacks, whites)` |
| chaossy/goban-image-reader | None | Outputs board state to console only |
| GoScanner | None (planned) | Mentioned but never implemented |

**noword's approach is clearly superior** — using `sgfmill` eliminates string-building bugs. Our pipeline already uses `SgfBuilder` (from `tools/core/sgf_builder.py`), which is the right pattern per CLAUDE.md ("use SgfBuilder, no manual SGF string building").

---

## 5. Technique Comparison Matrix

| Technique | img2sgf | image2sgf | goban-reader | GoScanner | Our Pipeline |
|-----------|---------|-----------|--------------|-----------|-------------|
| **Grid detection** | Hough lines + clustering | CNN corner detection | Full-image CNN | Contour quad | Dark-pixel voting + clustering |
| **Stone detection** | Hough circles | CNN batch inference | Full-image CNN | - | Intensity ratios at intersections |
| **Stone color** | Mean intensity threshold | EfficientNet-B3 / K-means | ResNet-34 softmax | - | Dark/bright pixel ratios |
| **Digit detection** | Skip (ignore) | Skip | Skip | Skip | Connected components + structural features |
| **Perspective correction** | None (flat only) | getPerspectiveTransform | None (synthetic data) | four_point_transform | None (flat GIF only) |
| **Partial boards** | User-aligned, gap-fill | CNN partial detector | - | - | Edge-ratio detection + coordinate mapping |
| **Multi-blur robustness** | 4 blur variants stacked | - | - | - | Single threshold |
| **Eval framework** | Manual inspection | COCO metrics | Train/eval split | - | Versioned JSON with confusion matrix |

---

## 6. Applicable Learnings

Techniques that could improve our pipeline, ranked by expected value:

### High Value

**A. Multi-blur circle/stone detection (from img2sgf)**
Running stone detection at multiple blur levels and unioning results catches stones that are visible at one blur kernel but not another. Our pipeline uses a single threshold — stacking results from 2–3 blur variants could improve stone detection robustness on degraded/noisy images.

**B. K-means color clustering (from image2sgf)**
Instead of fixed intensity thresholds (dark < T < bright), use K-means (k=2) on the mean colors of detected stones. The algorithm discovers the natural black/white boundary per image. This is more adaptive than our current `dark_ratio`/`bright_ratio` thresholds, especially useful if image brightness varies across years.

**C. Stone-size filtering after grid detection (from img2sgf)**
After detecting the grid, filter stones by diameter: must be 60–130% of grid spacing. This rejects noise circles (too small) and merged blobs (too large). Our pipeline doesn't currently apply this kind of post-filter.

### Medium Value

**D. Circles-first grid cleaning (from img2sgf)**
Detect stones first, mask them out, THEN detect grid lines. Prevents stone edges from polluting line detection. Our dark-pixel voting approach is already fairly robust to stones (they add pixels but don't create consistent row/column votes), but masking could improve edge cases.

**E. Grid completion via median-spacing interpolation (from img2sgf)**
When fewer than expected lines are found, compute median spacing and interpolate missing lines. Our pipeline already does this (`detect_grid` in `image_to_board.py`), but the specific implementation of classifying spaces as "small" vs "big" and interpolating only big gaps is a cleaner pattern.

**F. Synthetic data generation for ground truth expansion (from image2sgf, goban-image-reader)**
Programmatically generate known board positions as images to expand our ground truth beyond 22 images. Our Harada images are low-resolution GIFs, but we could render artificial GIF-style boards with known digit placements to stress-test edge cases.

### Low Value (Not Applicable)

**G. Perspective correction** — Harada images are flat GIFs, no perspective distortion.
**H. CNN-based classifiers** — Our images are simple 2-color GIFs; a neural network is overkill. Connected component analysis + structural features achieves 100%.
**I. FCOS corner detection** — Same reason as G.

---

## 7. Modularization Opportunities

Techniques that could become standalone modules in `tools/core/`:

| Technique | Proposed Module | Input | Output |
|-----------|----------------|-------|--------|
| K-means stone color separation | `stone_color_classifier.py` | List of (position, mean_color) | List of (position, BLACK\|WHITE) |
| Multi-blur union for robust detection | Extension to `image_to_board.py` | Image, list of blur kernels | Unioned detection results |
| Grid completion with gap classification | Already in `detect_grid` | Detected lines | Completed grid |
| Synthetic board image generator | `tools/core/board_renderer.py` | Board position, style config | PIL Image |

The synthetic board renderer would be the most impactful new module — it enables unlimited ground truth generation for any future image recognition work, not just Harada.

---

## 8. Architecture Patterns

### Two-Stage vs End-to-End

| Pattern | Examples | Trade-off |
|---------|----------|-----------|
| **Classical 2-stage**: detect grid, then classify intersections | img2sgf, our pipeline | Interpretable, debuggable, no training data needed. Brittle on unusual images. |
| **CNN end-to-end**: single model maps image → board state | goban-image-reader | High accuracy on trained distribution. Opaque failures. Needs large labeled dataset. |
| **Hybrid**: CNN for geometry, classical for classification (or vice versa) | image2sgf (CNN corners + K-means fallback) | Best of both worlds for varied inputs. More complex to maintain. |

Our pipeline is firmly in the **classical 2-stage** camp, which is the right choice for low-resolution, uniform-style GIF diagrams. The classical approach is deterministic and 100% accurate on our ground truth — there's no accuracy gap to close with ML.

### Evaluation Frameworks

| Repo | Eval Approach |
|------|--------------|
| img2sgf | Manual visual inspection (no automated eval) |
| image2sgf | COCO object detection metrics |
| goban-image-reader | Per-intersection + whole-board accuracy |
| GoScanner | None |
| Our pipeline | Versioned JSON with per-run accuracy, confusion matrix, per-image breakdown |

Our eval framework is the most comprehensive in this set. The versioned tracking with run-by-run comparison is unique.

---

## References

- [hanysz/img2sgf](https://github.com/hanysz/img2sgf) — MIT license, archived
- [noword/image2sgf](https://github.com/noword/image2sgf) — MIT license, v0.07
- [shanleiguang/vQi](https://github.com/shanleiguang/vQi) — MIT license (SGF→image, not recognition)
- [chaossy/goban-image-reader](https://github.com/chaossy/goban-image-reader) — MIT license
- [JoeHowarth/GoScanner](https://github.com/JoeHowarth/GoScanner) — no license specified

---

*This document is for internal research only. No code from these repositories should be imported, vendored, or directly referenced in our codebase.*
