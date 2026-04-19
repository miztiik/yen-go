# Plan: PDF-to-SGF Import Pipeline

**Last Updated**: 2026-04-12
**Correction Level**: Level 4 (Large Scale — 4+ files, structural addition)
**Status**: Complete (v2)

> **Moved**: Active plan is now at `tools/pdf_to_sgf/PLAN.md`.
> This file is retained for historical reference only.

---

## 1. Objective

Build a pipeline to import Go/Baduk tsumego puzzles from PDF books into SGF format, leveraging our existing `image_to_board.py` board recognition engine. This enables importing from scanned/digital tsumego books (Cho Chikun, Gokyo Shumyo, Xuanxuan Qijing, etc.) at scale.

## 2. Current State

### What We Have

| Component | Location | Status |
|-----------|----------|--------|
| **Board recognition** | `tools/core/image_to_board.py` (1,700 lines) | Production-quality for clean GIFs |
| **Digit detection** | Same file + `tools/core/digit_templates/` | 100% accuracy on Harada collection |
| **SGF tree builder** | `tools/minoru_harada_tsumego/sgf_tree_builder.py` | Builds solution trees from image diffs |
| **SGF rendering** | `tools/sgf2img/` | Reverse direction (SGF → image) |
| **PDF import doc** | `docs/how-to/backend/import-pdf.md` | Future-feature placeholder |

### What's Missing

| Capability | Description |
|-----------|-------------|
| **PDF page extraction** | Convert PDF pages to raster images |
| **Board region detection** | Find individual board diagrams on multi-board pages |
| **Grid tuning for PDFs** | Current thresholds calibrated for small GIFs, not hi-res PDFs |
| **CLAHE / lighting normalization** | Needed for scanned books with uneven lighting |
| **Problem-solution matching** | Pair problem diagrams with answer diagrams across pages |
| **OCR for labels** | Extract problem numbers and text labels |

## 3. Proof of Concept Results (2026-04-12)

### Test Material

Downloaded 2 PDFs from `travisgk/tsumego-pdf` (computer-generated Cho Chikun life-and-death):
- `demo-a.pdf` — 8 pages, problems (120 puzzles)
- `demo-a-key.pdf` — 7 pages, solutions with numbered moves

### Findings

| Step | Result | Notes |
|------|--------|-------|
| PDF extraction via PyMuPDF | **Works** | Each page has 1 embedded PNG image (3168×2448) |
| Board region detection | **Works** | Connected component analysis found 3 board regions per page correctly |
| Board recognition (image_to_board) | **Partial** | Detected stones but grid undercount (6×4 instead of ~13×6) |
| Digit detection on answer key | **Not tested yet** | Answer key has numbered moves (1-5) + problem labels |

### Root Cause of Grid Undercount

Our `image_to_board.py` was calibrated for Harada GIF images (~200×200px). The PDF board crops are ~859×355px with thinner grid lines relative to image size. The dark-pixel voting threshold (`dark_threshold // 3 ≈ 50`) is too aggressive for the thin gray lines in PDF-generated boards.

**Fix**: Use `RecognitionConfig` with tuned thresholds for PDF-style images, or add an adaptive threshold pre-processing step (CLAHE from skolchin/gbr).

## 4. Ecosystem Analysis

### Libraries Evaluated

| Library | What It Is | License | Verdict |
|---------|-----------|---------|---------|
| **merrillite/puzzle2sgf** | OGS API scraper (NOT image processing) | GPL-3.0 | **Not relevant** — simple API client |
| **skolchin/gbr** (82★) | Go board image recognition (OpenCV + tkinter) | MIT | **Adopt techniques** — CLAHE, channel splitting, perspective transform |
| **travisgk/tsumego-pdf** (9★) | Generates PDFs from pre-digitized puzzles | GPL-3.0 | **Test data source only** — 3,500+ puzzles as data |

### Techniques to Adopt from skolchin/gbr (MIT License)

| Technique | What | Why | Priority |
|-----------|------|-----|----------|
| **CLAHE** | Contrast-Limited Adaptive Histogram Equalization | Normalizes uneven lighting in scanned books | P0 |
| **Channel splitting** | Use R channel for white stones, B for black | Better stone separation in color images | P0 |
| **4-point perspective transform** | Correct camera angle via `imutils.perspective.four_point_transform` | Handle skewed scans | P1 |
| **Watershed post-filter** | Separate touching stones | Dense positions in advanced puzzles | P2 |

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    pdf_to_sgf Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐   ┌─────────────┐   ┌──────────────────────┐  │
│  │ PDF Input │──▶│ Page Extract │──▶│ Board Region Detect  │  │
│  │ (fitz)   │   │ (per page)   │   │ (contour + CC)       │  │
│  └──────────┘   └─────────────┘   └──────────┬───────────┘  │
│                                                │              │
│  ┌──────────┐   ┌─────────────┐   ┌──────────▼───────────┐  │
│  │ SGF Out  │◀──│ Tree Builder │◀──│ Board Recognition    │  │
│  │(SgfBuilder)│ │ (diff-based) │   │ (image_to_board.py)  │  │
│  └──────────┘   └─────────────┘   └──────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Problem-Solution Matcher                               │    │
│  │ - OCR problem numbers from labels                     │    │
│  │ - Digit detection on answer key numbered moves        │    │
│  │ - Position diff between problem and answer boards     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### File Structure (Proposed)

```
tools/pdf_to_sgf/
├── __init__.py
├── __main__.py            # CLI: python -m tools.pdf_to_sgf
├── pdf_extractor.py       # PDF → page images (PyMuPDF)
├── board_detector.py      # Find board regions on a page
├── problem_matcher.py     # Match problem-solution pairs
├── config.py              # PDF-specific recognition config presets
├── tests/
│   ├── test_pdf_extractor.py
│   ├── test_board_detector.py
│   └── test_recognition.py
└── _test_samples/         # Downloaded sample PDFs (gitignored)
```

### Dependencies

| Package | Version | Purpose | Already Installed? |
|---------|---------|---------|-------------------|
| PyMuPDF (fitz) | ≥1.24 | PDF page/image extraction | Yes |
| opencv-python-headless | ≥4.8 | Board detection, stones | Yes |
| numpy | ≥1.24 | Array ops | Yes |
| Pillow | ≥10.0 | Image loading | Yes |

No new dependencies needed. All are already in `tools/requirements.txt` or system-installed.

## 6. Phased Execution Plan

### Phase 0: Enhance image_to_board.py for PDF Sources

**Scope**: 1 file, ~50 lines
**Correction Level**: Level 1

| Task | Description |
|------|-------------|
| Add CLAHE preprocessing option | New `RecognitionConfig.clahe_enabled` + `clahe_clip_limit` |
| Add channel splitting option | `RecognitionConfig.use_channel_splitting` for color-aware stone detection |
| Add PDF preset config | `RecognitionConfig.for_pdf()` class method with tuned thresholds |
| Adapt grid detection threshold | Make dark_threshold auto-scale with image resolution |

**Acceptance Criteria**:
- Board recognition on PDF board crops achieves ≥95% grid line detection
- No regression on existing Harada GIF images (run eval)
- Configurable via `RecognitionConfig` without changing defaults

### Phase 1: PDF Extraction Layer

**Scope**: 2 new files
**Correction Level**: Level 2

| Task | Description |
|------|-------------|
| `pdf_extractor.py` | Extract pages as PIL Images from any PDF file |
| Support both embedded images and rendered pages | Try image extraction first, fall back to page rendering |
| Handle multi-image pages | Some PDFs embed individual board images; others embed full pages |

**Acceptance Criteria**:
- Successfully extracts images from tsumego-pdf sample PDFs
- Works with both computer-generated and scanned PDFs
- Returns `list[PIL.Image.Image]` with page numbers

### Phase 2: Board Region Detection

**Scope**: 1 new file
**Correction Level**: Level 2

| Task | Description |
|------|-------------|
| `board_detector.py` | Find rectangular board regions on a full page image |
| Connected component analysis | Dark-pixel regions → bounding boxes → board crops |
| Grid-line validation | Confirm detected regions contain Go board grid lines |
| Handle various layouts | 1-column, 2-column, with/without labels |

**Acceptance Criteria**:
- Finds all 3 boards on tsumego-pdf sample pages
- Returns bounding boxes with ≥95% coverage of actual board area
- Ignores non-board elements (text, page numbers, headers)

### Phase 3: Problem-Solution Matching

**Scope**: 1 new file
**Correction Level**: Level 2

| Task | Description |
|------|-------------|
| `problem_matcher.py` | Pair problem boards with their solution boards |
| Position similarity | Match boards by shared stone pattern (> 80% overlap) |
| OCR problem labels | Detect "problem NNN" text near boards (optional, fallback to positional) |
| Diff-based moves | Extract solution moves by diffing problem and answer positions |

**Acceptance Criteria**:
- Correctly pairs ≥90% of problems with solutions from tsumego-pdf samples
- Extracts at least the first move of the solution correctly

### Phase 4: End-to-End CLI Tool

**Scope**: 2 new files + docs
**Correction Level**: Level 3

| Task | Description |
|------|-------------|
| `__main__.py` | CLI: `python -m tools.pdf_to_sgf --pdf book.pdf --key answers.pdf` |
| SGF generation | Use `SgfBuilder` to create valid SGF files |
| Batch processing | Process all pages, skip failures, report stats |
| Documentation | Update `docs/how-to/backend/import-pdf.md` |

**Acceptance Criteria**:
- Processes tsumego-pdf sample PDFs end-to-end
- Produces valid SGF files that pass `validate_sgf()`
- ≥80% of puzzles have correct initial position
- ≥60% of puzzles have at least 1 correct solution move

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Grid detection accuracy on varied PDF styles | High | Phase 0 CLAHE + resolution-adaptive thresholds |
| Scanned books with noise/skew | Medium | Phase 0 perspective transform option |
| Problem-solution matching for books without numbered answers | Medium | Fallback to page-order heuristics |
| Copyright concerns with published books | High | Tool only processes user-provided PDFs; no bundled copyrighted content |
| GPL contamination from tsumego-pdf data | Medium | Use only for testing; don't ship their data |

## 8. Non-Goals (Explicit)

- ❌ AI/neural-net-based board recognition (keep OpenCV-only approach)
- ❌ Bundling copyrighted puzzle data
- ❌ Real-time camera capture (gbr scope, not ours)
- ❌ Move-order inference beyond what's numbered in diagrams
- ❌ Replacing the existing Harada pipeline (this is a new parallel tool)

## 9. Recommended Execution Order

```
Phase 0 (Quick Win)  →  Phase 1 + Phase 2 (parallel)  →  Phase 3  →  Phase 4
     ~1 session              ~1-2 sessions                ~1 session    ~1 session
```

Phase 0 can start immediately. Phase 1 and 2 are independent and can be developed in parallel. Phase 3 requires outputs from Phase 2. Phase 4 is integration.

## 10. Decision Points Needed

1. **Should we add PyMuPDF to `tools/requirements.txt`?** (It's already installed but not declared)
2. **Should the PDF tool live in `tools/pdf_to_sgf/` or extend `tools/core/`?** (Recommendation: separate tool, uses core as dependency)
3. **Should we pursue tsumego-pdf's puzzle data as a source?** (3,500+ puzzles, but GPL-3.0 and the puzzle positions from classical Go books may be available from other non-GPL sources)
