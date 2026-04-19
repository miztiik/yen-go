# PDF-to-SGF Tool: Implementation Plan

**Last Updated**: 2026-04-12
**Status**: Complete (v4 — with OCR, perspective correction, wrong-answer variations, digit calibration)

---

## Objective

Import Go/Baduk tsumego puzzles from PDF books into SGF format using computer vision, with full confidence scoring and structured telemetry.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     pdf_to_sgf Pipeline                         │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PDF Input ──▶ Page Extract ──▶ Board Detect ──▶ Recognize      │
│  (PyMuPDF)    (embedded/render)  (CC analysis)   (image_to_board)│
│                                                       │          │
│  SGF Out  ◀── Tree Builder  ◀── Match + Diff  ◀──────┘          │
│  (SgfBuilder)  (digit ordering)  (Jaccard similarity)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Observability Layer                                    │       │
│  │ - Pydantic event models with validation               │       │
│  │ - RunLogger → JSONL telemetry per run                 │       │
│  │ - BoardConfidence / MatchConfidence / PuzzleConfidence │       │
│  │ - RunSummary with aggregate metrics                   │       │
│  └──────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────┘
```

## File Structure

```
tools/pdf_to_sgf/
├── __init__.py
├── __main__.py            # CLI: extract, convert, preview
├── pdf_extractor.py       # PDF → page images (PyMuPDF)
├── board_detector.py      # Find board regions on a page (CC analysis)
├── problem_matcher.py     # Match problem-solution + confidence + digits
├── ocr.py                 # OCR utilities (pytesseract lazy import)
├── models.py              # Pydantic event payloads + confidence models
├── telemetry.py           # RunLogger → JSONL structured logging
├── sgf_checker.py         # SGF correctness validation (9 checks)
├── PLAN.md                # This file
├── MEMORY.md              # State tracking
├── tests/
│   ├── __init__.py
│   ├── test_pdf_pipeline.py       # PDF extraction + board detection (10)
│   ├── test_matcher.py            # Matching + SGF generation + wrong-move detection (22)
│   ├── test_cli.py                # CLI commands (7)
│   ├── test_models_telemetry.py   # Models + telemetry + confidence (22)
│   ├── test_sgf_checker.py        # SGF correctness validation (24)
│   ├── test_phase5.py             # Column, grid filter, perspective, digits (40)
│   └── test_ocr.py                # OCR tests — all mocked (21)
└── _test_samples/         # Sample PDFs (gitignored)
```

## Phases (All Complete)

### Phase 0: Enhance image_to_board.py ✅
- CLAHE preprocessing (`clahe_enabled`, `clahe_clip_limit`)
- `RecognitionConfig.for_pdf()` and `.for_scan()` presets
- Wired `_complete_grid()` for gap interpolation
- `grid_vote_ratio` config parameter

### Phase 1: PDF Extraction ✅
- `pdf_extractor.py` with embedded image + rendered page strategies
- `ExtractionConfig` dataclass
- `ExtractedPage` with page number, source, dimensions

### Phase 2: Board Region Detection ✅
- `board_detector.py` with binarize → morphological close → CC analysis
- Aspect ratio filtering, area thresholds, merge distance
- Top-to-bottom sorting

### Phase 3: Problem-Solution Matching ✅
- Jaccard similarity on occupied cell positions
- Positional fallback when board counts match
- Digit detection on answer stones for move ordering
- Confidence scoring (board + match + puzzle level)
- Problem label in root comment
- Root comment with confidence metadata

### Phase 4: CLI + Observability ✅
- `__main__.py` with `extract`, `convert`, `preview` subcommands
- Pydantic models (`models.py`) for all events
- `RunLogger` with JSONL output (`telemetry.py`)
- Structured events: RunStart, PageExtracted, BoardDetected, BoardRecognized, MatchFound, SgfGenerated, Error, RunSummary

## Confidence Model

### BoardConfidence
| Metric | Weight | Source |
|--------|--------|--------|
| `grid_completeness` | 0.5 | actual_lines / (expected_size × 2) |
| `edge_fraction` | 0.3 | detected_edges / 4 |
| `stone_density` | 0.2 | occupied_cells / total_cells (capped ×5) |

### MatchConfidence
| Metric | Weight | Source |
|--------|--------|--------|
| `jaccard_similarity` | 0.4 | Jaccard(problem_occupied, answer_occupied) |
| `stone_count_ratio` | 0.2 | min(p,a) / max(p,a) stone counts |
| `solution_plausibility` | 0.2 | 1.0 if 1-10 moves, scaled down outside |
| `moves_ordered` | 0.2 | fraction with digit-detected order |

### PuzzleConfidence
Composite of board + match confidence, averaged.

## Event Types (JSONL)

| Event | When | Key Fields |
|-------|------|-----------|
| `run_start` | Pipeline begins | pdf_path, key_path, preset, command |
| `page_extracted` | Page image ready | page_number, source, dimensions |
| `board_detected` | Board region found | bbox, dimensions |
| `board_recognized` | Stones classified | grid size, stone counts, BoardConfidence |
| `match_found` | Problem-answer paired | similarity, strategy, solution_moves, MatchConfidence |
| `sgf_generated` | SGF file written | output_file, PuzzleConfidence |
| `error` | Recoverable failure | stage, detail |
| `run_complete` | Final summary | aggregated counts, avg confidences, duration |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyMuPDF (fitz) | ≥1.24 | PDF extraction |
| opencv-python-headless | ≥4.8 | Board detection + recognition |
| numpy | ≥1.24 | Array operations |
| Pillow | ≥10.0 | Image loading |
| pydantic | ≥2.0 | Event models + validation |
| pytesseract | ≥0.3.10 | OCR (requires Tesseract binary) |

## Test Coverage

146 tests total:
- 10 PDF extraction + board detection (integration, skip if no samples)
- 22 matcher + SGF generation + wrong-move detection (5 unit + 6 unit + 3 integration + 3 fallback + 5 wrong-move)
- 7 CLI commands (parsing + integration)
- 20 models + telemetry + confidence (pure unit, no samples needed)
- 24 SGF correctness checker (parseability, properties, bounds, overlap, moves, PL)
- 40 Phase 5+ features (column, grid filter, circle erasure, events, report, perspective, digit templates)
- 21 OCR (player-to-move, problem labels, answer section — all mocked)

## Ecosystem Research

### datavikingr/pdf2sgf (2024, Python, 1 contributor)

**Repo**: [github.com/datavikingr/pdf2sgf](https://github.com/datavikingr/pdf2sgf)
**What it does**: Wraps `hanysz/img2sgf` (1,310-line OpenCV GUI app patched for headless) to batch-process 68 tsumego PDFs (tasuki + 101books) into SGFs via shell-out. Three files: `pdf2sgf.py` (orchestration, 253 LOC), `img2sgf.py` (recognition, 1,310 LOC), `sanity_checker.py` (validation, 149 LOC).

**Techniques worth adopting**:

| Technique | File/Function | Relevance | Priority |
|-----------|--------------|-----------|----------|
| Multi-column layout detection | `pdf2sgf.py: detect_column_count` | Morphological close (5×100 kernel) + column projection profiling + Gaussian smooth → count contiguous active blocks. Handles 2-col and 3-col layouts. We have no column detection. | **High** |
| Grid-line count pre-filter | `pdf2sgf.py: detect_problem_regions` | Canny + HoughLines ≥ 15 → valid board. Regions with fewer lines are skipped (title pages, text blocks). Saves recognition time, reduces false positives. | **High** |
| Circle erasure before grid detection | `img2sgf.py: process_image` | Erase detected circles (stones) in bounding boxes, replace with single center pixel → much cleaner grid line detection in crowded boards. | **Medium** |
| Multi-blur circle/stone detection | `img2sgf.py: process_image` | Run HoughCircles across multiple blur kernels (median + Gaussian at varying sizes), accumulate all circles → better recall for varied stone appearances. | **Medium** |
| OCR-based player-to-move | `pdf2sgf.py: detect_player_from_text` | Crop 50px footer band below each problem, run pytesseract OCR, detect "black/white to play". More accurate than pure stone counting for annotated PDFs. | **Medium** |
| SGF empty/validity post-check | `pdf2sgf.py: is_empty` | Check generated SGF: file size ≥ 50 bytes AND contains `AB[`/`AW[` patterns. Flag failed conversions for re-processing. | **Low** |

**Techniques NOT adopted** (and why):

| Technique | Reason |
|-----------|--------|
| Whiteness filter (`sanity_checker.py: test_whiteness`) | Author explicitly marked "FAILED HEURISTIC" — false positives |
| AgglomerativeClustering for line grouping (`img2sgf.py`) | Our Hough vote + complete_grid approach works; sklearn dependency not worth it |
| pdf2image (poppler) for PDF extraction | PyMuPDF is faster, pure Python, already in our stack |
| Subprocess shell-out for recognition | Our pipeline is in-process, much more efficient |
| Sidecar `.player` files | We embed player-to-move directly in SGF |
| GUI (tkinter) code | We're headless-only |

**Architectural observations**:
- Their row-sum + gap-merge approach for problem region splitting is simpler than our CC analysis but less robust for irregular layouts. Potential fallback strategy.
- `complete_grid()` in img2sgf is functionally identical to our `_complete_grid()` — validates our approach.
- `truncate_grid()` cleverly handles 1-2 extra detected lines (bounding box, captions) — we could add similar logic.
- Board alignment for partial boards (`align_board()`) is relevant if we add sub-19×19 support.

---

## Phase 5: Robustness + Validation + Reporting ✅

Implemented from `datavikingr/pdf2sgf` ecosystem research:

### 5a. Multi-column layout detection ✅
- Added `detect_columns()` to `board_detector.py`
- Morphological close (5×N kernel) → column projection → Gaussian smooth → active block counting
- Splits page into columns before board detection
- Supports 1/2/3-column layouts (clamped range)
- Configurable: `enable_column_detection`, `column_morph_height`, `min_column_width`

### 5b. Grid-line pre-filter ✅
- Added `has_board_grid()` to `board_detector.py`
- Canny + HoughLines on candidate region before full recognition
- Threshold: ≥ 15 lines = valid board candidate (configurable `min_grid_lines`)
- Skips non-board regions early → faster processing, fewer false positives
- Emits `BoardSkippedEvent` to telemetry

### 5c. Circle erasure before grid detection ✅
- Added `_erase_circles()` to `tools/core/image_to_board.py` (near `_apply_clahe`)
- HoughCircles with multi-blur voting (0, 3, 5, 7 kernels) detects stone-like circles
- Erases bounding box (black fill) and places white center pixel to reveal hidden grid lines
- Deduplicates overlapping detections across blur levels
- Config: `circle_erasure`, `circle_erasure_min_radius` (5), `circle_erasure_max_radius` (40)
- Enabled by default in `for_pdf()` and `for_scan()` presets
- Grid detection uses erased image; stone classification uses original (un-erased) image
- Technique from datavikingr/pdf2sgf (img2sgf.py)

### 5d. OCR player-to-move detection ✅
- Created `ocr.py` module with lazy pytesseract import (avoids hang when Tesseract binary missing)
- `ensure_tesseract()` validates binary, clear error message with install instructions
- `ocr_region()` (PSM 6) and `ocr_line()` (PSM 7) for text extraction
- `detect_player_to_move()` — crops footer below board, regex for "Black to play"/"黒先"/"白番" etc → "B"/"W"/None
- `detect_problem_label()` — crops header above board, patterns for "Problem N"/"第N問"/"#N"
- `detect_answer_page()` — scans top 15% for answer markers ("答え"/"Answer"/"Solution"/"解答"/"正解")
- `find_answer_start()` — reverse-scans pages from end (tsumego books have solutions at back)
- Wired into CLI: OCR label/player detection per detected board if Tesseract available
- CLI flag `--auto-detect-solution` (opt-in scan, outputs recommendation only, does NOT auto-split)
- CLI flag `--key-pages RANGE` (explicit answer page range within same PDF)
- New event: `AnswerSectionDetectedEvent(page_number, marker_text, confidence)`
- 21 tests in test_ocr.py (all mocked, no Tesseract binary required)

### 5e. SGF correctness validation ✅
- Created `sgf_checker.py` with full `validate_sgf()` function
- 9 validation checks: parseability, required properties, board size, stone bounds, overlap, solution moves, player-to-move, solution sanity
- 3 severity levels: ERROR (structural), WARNING (quality), INFO (review note)
- `SgfCheckResult` with metadata: board_size, stone counts, solution count
- Wired into CLI: every generated SGF is validated, emits `SgfValidatedEvent` or `SgfRejectedEvent`

### 5f. Granular telemetry + yield report ✅
- Enhanced all events with `pdf_source` and `page_number` tracking
- New events: `ColumnDetectedEvent`, `BoardSkippedEvent`, `SgfValidatedEvent`, `SgfRejectedEvent`
- `RunSummary` now includes: yield_rate, review_needed, columns_detected, boards_skipped, sgf_validated, sgf_rejected, page_summary
- `RunLogger.format_report()` produces human-readable yield report
- Report saved to `report.txt` alongside JSONL telemetry
- Per-page breakdown shows: label, SGF file, confidence, validation status
- Step-by-step CLI output: [1/7]...[7/7] showing exact processing stage

---

## Phase 6: OCR + Variations + Perspective + Digit Calibration ✅

### 6a. Perspective correction ✅
- `_correct_perspective()` in `image_to_board.py`: Canny → contours → largest quadrilateral → `cv2.warpPerspective()`
- `_order_corners()`: sum/diff method to identify TL/TR/BR/BL
- Config: `perspective_correction`, `perspective_min_area_ratio`, `perspective_output_size`
- Enabled in `for_scan()` only (NOT `for_pdf()` — PDFs are axis-aligned)
- Wired into `recognize_position()` BEFORE `_apply_clahe()` (perspective first, then contrast)
- If no quadrilateral found → returns original image (no crash)

### 6b. Wrong-answer variation extraction ✅
- `_detect_wrong_moves(problem_pos, answer_pos)`: removed_stones = problem - answer → wrong first moves
- `_detect_refutation_sequences()`: for each wrong move, finds nearby opponent responses within 2 intersections
- `MatchResult` extended with `wrong_moves` and `variations` fields
- `position_to_sgf()` emits variation branches: `builder.back_to_root()` → `add_solution_move(is_correct=False)` → BM[1] markers
- Wired into both Jaccard match and positional fallback paths
- `player_to_move` parameter on `position_to_sgf()` — OCR-detected PL takes priority

### 6c. PDF digit detection calibration ✅
- Template set system: `digit_template_set` config field with per-set caching
- `_template_cache: dict[str, tuple[...]]` replaces single global variables
- `_TEMPLATE_DIRS` mapping: "default" → `digit_templates/`, "pdf" → `digit_templates_pdf/`
- `for_pdf()` preset uses `digit_template_set="pdf"`
- `tools/core/generate_pdf_templates.py` script: generates 30 `.npy` files (10 digits × 3 variants)
- PDF templates: thicker strokes (3px), anti-aliased, FONT_HERSHEY_SIMPLEX, 4x render → resize to (10,14)

---

## Known Limitations

- Grid detection depends on visible grid lines; circle erasure (5c) helps but heavily distorted lines may still fail
- Digit detection has two template sets (default + pdf); exotic fonts may need additional sets
- Answer section auto-detection (`--auto-detect-solution`) only recommends — user must confirm via `--key-pages`
- Wrong-answer variation extraction relies on stone removal heuristic; complex ko sequences may be missed
- Perspective correction uses largest quadrilateral heuristic; very small or non-dominant boards may not be corrected
- pytesseract requires Tesseract binary installed separately (lazy import prevents hang when missing)
