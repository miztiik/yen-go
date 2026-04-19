# PDF-to-SGF Tool: Development Memory

**Last Updated**: 2026-04-12 (v4.0)

---

## Implementation History

### 2026-04-12 — v2: Observability + Confidence
- Added `models.py` with Pydantic event payloads (9 event types)
- Added `telemetry.py` with `RunLogger` → JSONL structured output
- Added confidence scoring: `BoardConfidence`, `MatchConfidence`, `PuzzleConfidence`
- Added digit detection on answer stones for move ordering (reuses `detect_digit` from image_to_board)
- Added problem label in SGF root comment (`C[Problem N\nMatch confidence: ...]`)
- Wired telemetry into all CLI commands (extract, convert)
- Added `tools/requirements.txt` entries: `PyMuPDF>=1.24`, `pydantic>=2.0`
- Test count: 34 → 56 (+22 new for models, telemetry, confidence, ordering)

### 2026-04-12 — v1: Core Pipeline
- Built 4-phase pipeline: pdf_extractor → board_detector → problem_matcher → CLI
- Enhanced `image_to_board.py` with CLAHE, `for_pdf()`/`for_scan()` presets
- Critical fix: wired `_complete_grid()` (was defined but never called)
- Jaccard similarity matching + positional fallback
- SGF generation via `SGFBuilder`
- 34 tests passing

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Dataclasses in matcher, Pydantic in models | Matcher dataclasses have RecognizedPosition (not serializable); events need validation |
| Sequential problem labeling | No OCR for text labels; digit detection is for numbered stones on board |
| JSONL not JSON for telemetry | Append-friendly, one event per line, streamable |
| Confidence weights 0.5/0.3/0.2 for board | Grid completeness is the strongest signal; edges next; density is noisy |
| `_complete_grid` fix in core | Grid lines occluded by stones were failing vote threshold; gap interpolation fixed it |

## Gotchas

- `RecognizedPosition` uses `grid: GridInfo` as first field, NOT `n_rows`/`n_cols` — those are properties
- `detect_digit(img, cx, cy, color_char, radius)` — cx/cy are pixel coords from `grid.x_lines[ix]`/`grid.y_lines[iy]`
- PDF preset only changes stone classification, NOT grid detection thresholds (defaults work with `_complete_grid`)
- `SGFBuilder.set_comment()` sets root `C[]` property — there is no `set_root_comment()`
- Sample PDFs in `_test_samples/` are gitignored; integration tests skip gracefully

### 2026-04-12 — v3: Robustness + Validation + Reporting
- Added `detect_columns()` for multi-column PDF layouts (2/3-column support)
- Added `has_board_grid()` grid pre-filter (HoughLines ≥ 15)
- Created `sgf_checker.py` with `validate_sgf()` — 9 correctness checks
- Enhanced all event models with `pdf_source`, `page_number` tracking
- New events: `ColumnDetectedEvent`, `BoardSkippedEvent`, `SgfValidatedEvent`, `SgfRejectedEvent`
- Enhanced `RunSummary` with yield_rate, review_needed, page_summary
- Added `RunLogger.format_report()` for human-readable yield report
- Report saved to `report.txt` alongside JSONL
- CLI now shows step-by-step progress: [1/7]...[7/7]
- Test count: 56 → 101 (+24 sgf_checker + 21 phase5)

### 2026-04-12 — v3.1: Circle Erasure (Phase 5c)
- Added `_erase_circles()` to `tools/core/image_to_board.py`
- HoughCircles with multi-blur voting (kernels 0, 3, 5, 7) detects stone-like circles
- Erases bounding box (black fill) + white center pixel to reveal grid lines under stones
- Deduplicates overlapping detections across blur levels (keep larger, discard close centres)
- Config: `circle_erasure`, `circle_erasure_min_radius` (5), `circle_erasure_max_radius` (40)
- Enabled in `for_pdf()` and `for_scan()` presets; off by default
- Grid detection runs on erased image; stone classification uses original image
- Test count: 101 → 108 (+7 circle erasure)

### 2026-04-12 — v4.0: OCR + Perspective + Variations + Digit Calibration
All 6 remaining open items implemented:

**OCR Module** (`ocr.py`):
- Lazy pytesseract import via `_get_pytesseract()` — avoids hang when Tesseract binary missing
- 7 public functions: `ensure_tesseract`, `ocr_region`, `ocr_line`, `detect_player_to_move`, `detect_problem_label`, `detect_answer_page`, `find_answer_start`
- Multi-language regex: English ("Black to play"), Japanese (黒先/白番), Chinese (黑先/白先)

**Perspective Correction** (`image_to_board.py`):
- `_correct_perspective()`: Canny → contours → largest quad → `cv2.warpPerspective()`
- `_order_corners()`: sum/diff corner ordering
- Config: `perspective_correction`, `perspective_min_area_ratio`, `perspective_output_size`
- Enabled in `for_scan()` preset only; wired before `_apply_clahe()`

**Wrong-Answer Variations** (`problem_matcher.py`):
- `_detect_wrong_moves()`: removed_stones = problem - answer
- `_detect_refutation_sequences()`: nearby opponent responses within 2 intersections
- `MatchResult.wrong_moves` + `MatchResult.variations`
- `position_to_sgf()`: variation branches with `BM[1]` markers, `player_to_move` parameter

**CLI Enhancements** (`__main__.py`):
- `--auto-detect-solution`: opt-in scan, outputs recommendation, does NOT auto-split
- `--key-pages RANGE`: explicit answer page range within same PDF (supports "50-" open-ended)
- OCR label/player detection per board when Tesseract available
- `AnswerSectionDetectedEvent` telemetry

**PDF Digit Calibration** (`image_to_board.py` + `generate_pdf_templates.py`):
- Template set system: `_template_cache` dict with per-set caching
- `_TEMPLATE_DIRS` mapping: "pdf" → `digit_templates_pdf/`
- `for_pdf()` uses `digit_template_set="pdf"` by default
- 30 synthetic templates (10 digits × 3 variants) generated via `generate_pdf_templates.py`

**Key fix**: pytesseract 0.3.13 hangs on `import pytesseract` when Tesseract binary isn't installed. Fixed by lazy import. Tests use `FakeTesseractNotFoundError` to avoid importing real pytesseract.

- Test count: 108 → 146 (+21 OCR + 7 perspective + 5 wrong-move + 5 digit template)

## Ecosystem Research Log

### 2026-04-12 — datavikingr/pdf2sgf
- **Repo**: https://github.com/datavikingr/pdf2sgf (1 contributor, 8 months old)
- **Architecture**: `pdf2sgf.py` (wrapper) → shell-out to `img2sgf.py` (patched `hanysz/img2sgf` for headless), `sanity_checker.py` (validation)
- **Key insight**: Circle erasure before grid detection is the most impactful technique — erase detected stone bounding boxes, replace with center pixel, then run HoughLines for much cleaner grid detection on crowded boards
- **Column detection**: Morphological close (5×100 kernel) + vertical projection profiling — simple and effective for 2/3-column layouts
- **Grid pre-filter**: HoughLines ≥ 15 as board-presence heuristic — cheap guard before expensive recognition
- **Whiteness filter failed**: Author confirmed false positives, abandoned the heuristic
- **Their `complete_grid()` matches ours**: Validates our `_complete_grid()` approach independently
- **No new dependencies needed** for column detection or grid pre-filter (already have OpenCV). OCR player detection would need `pytesseract`.

## Open Items

- [x] Multi-column layout detection (Phase 5a) ✅
- [x] Grid-line pre-filter (Phase 5b) ✅
- [x] Circle erasure before grid detection (Phase 5c) ✅
- [x] OCR player-to-move from footer text (Phase 5d / 6a OCR) ✅
- [x] SGF post-gen validation (Phase 5e) ✅
- [x] Text-based OCR for problem labels (Phase 6a OCR) ✅
- [x] Answer section auto-detection within single PDF (Phase 6a OCR) ✅
- [x] Wrong-answer variation extraction (Phase 6b) ✅
- [x] Perspective transform for skewed scans (Phase 6a) ✅
- [x] Calibrate digit detection for PDF-style numbered stones (Phase 6c) ✅

All planned features implemented. Future work:
- Sub-19×19 board support (from datavikingr `align_board()`)
- Multi-answer-board grouping (1-to-many matching for wrong answers shown separately)
- Additional template sets for exotic font styles
