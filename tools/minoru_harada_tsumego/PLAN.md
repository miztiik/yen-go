# Harada Tsumego Tool — Implementation Plan

## Overview

Import and process **Weekly Tsumego by Minoru Harada** (1996–2020) — 1,182 life-and-death problems archived from the Wayback Machine. Each puzzle has elementary and intermediate levels with problem images, correct answer images, wrong answer images, and variations.

**Pipeline:** Crawl → Download → Recognize → Build SGF Trees → Enrich → Output

---

## Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| A | Plan & Docs | ✅ | This file + README.md + MEMORY.md |
| B | Rename & Scrub | ✅ | `hitachi_archive/` → `minoru_harada_tsumego/`, scrub all references |
| C | Extract Core | ✅ | `recognizer.py` → `tools/core/image_to_board.py` (generic, reusable) |
| D | Tree Builder | ✅ | `sgf_tree_builder.py` + `build` CLI command, verified on test images |
| E1 | Catalog Redesign | ✅ | Set-based checkpoint, semantic IDs, per-year status, retry/year filter |
| E2 | Bulk Download | ✅ | All 1,182 puzzles attempted; 429 have images, 753 permanently 404 |
| E3 | SGF Quality & Validation | ✅ | BM fix, comment normalization, copyright stripping, placeholder filter, validation gating, 11-rule validator |
| F | Enrichment | ⏸️ | Go-Advisor difficulty calibration, technique tagging, hints (blocked on KataGo enrichment lab) |
| F2 | Comment Enrichment | ✅ | Sub-agent rewrite of teaching comments with coordinate mapping |
| F3 | Gated Puzzle Recovery | ✅ | Strict alternation, noise filtering, digit-order validation, PL inference, branch promotion |
| G | Pipeline Output | ✅ | 830 SGFs at `external-sources/authors/Minoru Harada/sgf/batch-001/`, registered in `sources.json` |

---

## Phase Details

### Phase B: Rename & Scrub ✅
- Directory: `tools/hitachi_archive/` → `tools/minoru_harada_tsumego/`
- Config: `hitachi_config.json` → `harada_config.json`
- Class: `HitachiConfig` → `CollectionConfig`
- All imports, docstrings, comments updated (URLs preserved)
- Verification: grep clean, config loads, recognizer works

### Phase C: Extract Core ✅
- Created: `tools/core/image_to_board.py` (~400 LOC)
- Generic Pillow-only board recognition (GIF/PNG/PDF-extracted)
- `RecognitionConfig` frozen dataclass with parameterized thresholds
- `recognize_position()` accepts `PIL.Image.Image` or file path

### Phase D: Tree Builder ✅
- Created: `tools/minoru_harada_tsumego/sgf_tree_builder.py`
- `build_puzzle_sgf()` → images → recognition → diff → SGF with move tree
- `build` CLI command: `--puzzle N`, `--level`, `--all`, `--output-dir`
- Verified: Puzzle #1 elementary = 5 correct moves, 1 wrong branch, 1 variation
- Verified: Puzzle #1 intermediate = 3 correct moves, 1 wrong branch, 1 variation

### Phase E1: Catalog Redesign ✅

Redesign the catalog schema and checkpoint strategy for efficient multi-pass downloading of a 20+ year archive. See [MEMORY.md](MEMORY.md) for full decision rationale.

**Tasks:**

| Task | File | What |
|------|------|------|
| T1 | `models.py` | `semantic_id` on `PuzzleImage`, `asset_summary` property on `PuzzleEntry`, `per_year_summary()` on `Catalog`, version bump to 1.1.0 |
| T2 | `orchestrator.py` | Compute semantic IDs during download: `{year}_{NNN}_{level}_{type}` |
| T3 | `orchestrator.py` | Set-based checkpoint: `completed_puzzles: list[int]` replaces sequential `last_problem_completed` |
| T4 | `orchestrator.py` | Rich `show_status` with per-year breakdown table |
| T5 | `orchestrator.py` | `--retry-only` flag (skip completed puzzles) + `--year YYYY` filter |
| T6 | `orchestrator.py` | Auto-migrate old checkpoint format (sequential → set-based) |
| T7 | `__main__.py` | CLI flags for `--retry-only` and `--year` |
| T8 | `orchestrator.py` | Audit all logger calls: URLs as structured kwargs |

**Key Design Decisions:**
- **Option A (Enhanced Single Catalog)** chosen over Option B (year-sharded files). See MEMORY.md.
- Set-based checkpoint allows non-sequential processing — puzzle #50 can fail while #51-100 succeed.
- Semantic IDs stored in catalog only, not on the filesystem (YAGNI).
- All changes are local to this tool — nothing new moves to `tools/core/`.

### Phase E2: Bulk Download ✅
- All 1,182 puzzles attempted across 25 years (1996–2020)
- 4,950 images discovered; 2,820 downloaded; 2,130 returned 404
- **429 puzzles have usable images** → max theoretical 821 SGFs (e + m)
- **753 puzzles permanently lost** — Wayback did not archive their images
- No further downloading will increase yield

### Phase F: Enrichment ⬜
- Go-Advisor agent for difficulty calibration and technique tagging
- Elementary → novice/beginner/elementary mapping
- Intermediate → intermediate/upper-intermediate mapping
- Tags from `config/tags.json`, hints (YH), quality scoring (YQ)

### Phase E3: SGF Quality & Validation ✅

Systemic quality audit + iterative fix-validate cycle. 4 iterations to reach 0 errors.

**Issues Found & Fixed:**

| Issue | Pre-fix | Fix | Post-fix |
|-------|---------|-----|----------|
| Consecutive same-color moves | 577/821 (70%) | Validation gating — skip broken SGFs | 0 in output |
| Spurious newlines in comments | 821/821 (100%) | `_normalize_comment()` joins mid-sentence breaks | 0 |
| BM[1] on ALL wrong moves | 560/821 (68%) | BM[1] only on first wrong move | 0 |
| Empty board (placeholders) | 145/821 (18%) | File-size filter (<500b = skip) + prefer level-specific images | 0 (recovered 29 SGFs) |
| Copyright in comments | 7 files | `_COPYRIGHT_PATTERN` stripping in normalizer | 0 |
| Variation branch colors | 112 files | Added CONSECUTIVE_COLORS_VARIATION gating | 0 |

**Validation Infrastructure:**

- `validate_sgfs.py` — 11-rule automated checker, runs against all output SGFs
- Rules: setup stones, solution tree, color alternation, BM markers, comment quality (HTML/CSS/footer), move bounds, PL mismatch, excessive moves, move-on-occupied, outlier moves, stray properties
- `--sample N` for random spot-checks, `--export` for JSON agent review
- Go-Advisor spot-check of 15% sample: 3 PASS, 1 WARN (difficulty), 1 FAIL (phantom moves)

**Code Changes:**

1. **`sgf_tree_builder.py`**: `_normalize_comment()`, `_COPYRIGHT_PATTERN`, `has_critical_warnings()`, empty board detection, file-size filter in `_images_by_type()`
2. **`__main__.py`**: Gated vs error tracking, `gated_details` in build-status.json
3. **`validate_sgfs.py`**: New file — 11-rule comprehensive validator

### Phase F2: Comment & Structure Enrichment ✅

Deep audit (puzzle #412 + Go-Advisor + collection-wide scan) revealed structural quality issues:

| Issue | Scope | Root Cause |
|-------|-------|-----------|
| Teaching text at root only | 112/713 | All text in root C[], not on branch moves |
| Missing wrong/variation branches | 112+44 | Wrong-answer images 404 from Wayback |
| Outlier/noise moves | 349/713 | Image diff picks up continuation stones |
| Digit detection misreads | ~20% | OCR reads wrong digit values |

**Sub-phases:**

- **F2a**: Comment redistribution ✅ — parse "Wrong Answer"/"(Variation)" markers, split to branch C[]
  - Root C[]: puzzle header only
  - Correct branch: `C[Correct: teaching text...]`
  - Wrong branch: `C[Wrong: explanation...]`
  - Variation branch: `C[Variation: alternative explanation...]`
  - All 713 SGFs now have text on the correct branches
- **F2b**: Outlier move filtering ✅ — Sub-agent validation confirmed 0 outlier moves at any margin; bbox margin=3 safe, no tightening needed
- **F2c**: Sub-agent validation ✅ — 20-puzzle sample, 0 FAIL, 11 PASS, 9 WARN (see Phase F2c section below)
- **F2d**: Digit detection rewrite + move coordinate mapping ✅
  - Rewrote `detect_digit()` with structural features (zone, h-bar, col fill)
  - 56/56 (100%) on 9-image ground truth test suite
  - Fixed phantom stones at image edges (`classify_intersections` edge margin)
  - "Black 1" → "Black C19" coordinate mapping in comments
- **F2e**: OpenCV Rewrite + Eval Framework ✅
  - Full OpenCV rewrite of `tools/core/image_to_board.py`: numpy vectorized voting, connected components digit detection, contour-based structural feature classification
  - Expanded ground truth: 22 images, 147 digits (was 9 images, 56 digits)
  - Evaluation framework: `eval_digit_detection.py` with versioned JSON tracking (`eval_results.json`), confusion matrices, per-image breakdown
  - CLI: `python -m tools.minoru_harada_tsumego eval [--compare] [--run-id ID] [--no-save]`
  - 10 iteration cycles: 88.4% → 90.5% accuracy (v1.0 → v1.10), then GT correction → 100% (v3.1)
  - Multi-digit detection (10-18) via connected component analysis + left-to-right assembly
  - Ground truth corrections: 13/147 labels were wrong — verified via 8x crop visual inspection
  - StructuredLogger telemetry added to `sgf_tree_builder.py` (timing, stone counts, grid dims)
  - SGF rebuild: 712 SGFs (0 gated, 146 errors)
  - **Completed**: Ground truth corrections via vision inspection resolved all 13 "failures" — detector was correct, labels were wrong. 100% accuracy achieved (v3.1).
- **F2f**: Honest Evaluation & Survey-Inspired Improvements ✅
  - Fixed circular evaluation (train-on-test contamination) with three-level methodology:
    - **Resubstitution** (193/193): Labeled as train=test, no longer misleading
    - **Leave-One-Image-Out CV** (147/147): Each of 22 training images held out in turn, templates built from remaining 21
    - **Holdout test set** (46/46): 8 new images from 2002-2007, independently verified, never in training
  - Applied learnings from external Go board recognition survey (5 repos analyzed):
    - **Color-specific template loading**: `_load_templates()` now loads `digit_N_black.npy`/`digit_N_white.npy`, `_classify_component()` prefers color-specific templates when stone color is known
    - **Stone-size post-filtering**: Intersections with too few active pixels relative to grid spacing are reclassified as EMPTY (configurable via `stone_min_fill_ratio`)
    - **K-means stone color validation**: Diagnostic `validate_stone_colors()` runs K-means(k=2) on stone intensities and warns if clusters diverge from fixed thresholds
  - CLI: `--cv` for cross-validation, `--holdout` for holdout-only eval
- **F2g**: Survey Techniques & Structural SGF Fixes ✅
  - **Multi-blur stone classification**: `classify_intersections()` runs stone detection at multiple Gaussian blur levels (configurable via `blur_kernels`, default `(0, 3, 5)`) with majority voting. Reduces noise sensitivity on low-quality images.
  - **Stone diameter range filtering**: After fill-ratio check, computes bounding box of active pixels and rejects stones whose effective diameter falls outside `stone_min_diameter_ratio`–`stone_max_diameter_ratio` (default 60–130%) of grid spacing.
  - **K-means adaptive classification**: Opt-in (`kmeans_adaptive=True`). When K-means cluster boundary diverges >40px from fixed thresholds, adapts pixel cutoffs from cluster centers and re-runs classification. Default OFF — zero behavior change for existing callers.
  - **Shared-prefix branch merging (B1)**: When correct and wrong branches share opening moves, the SGF tree builder now merges the shared prefix and places BM[1] on the actual divergence move. Fixed 89 CONFLICTING_FIRST_MOVE warnings, harada_0273_m (BM on wrong node), harada_0392_m (same move both correct+wrong).
  - **Per-section comment coordinate mapping (B2)**: `_replace_move_refs()` now maps coordinates per comment section — correct section uses correct branch, wrong section uses wrong branches, variation section uses variation branches. Previously all sections used the longest branch, causing 35% comment coordinate error rate.
  - **Puzzle #109 intermediate (B3)**: No longer fails — the code improvements resolved the recognition issue. SGF count increased from 712 to 713.
  - **Validator fix**: `_check_player_first_move()` now checks the first move in the entire SGF (main line) rather than the first variation branch, accommodating the new nested branch structure.
  - All three eval levels remain 100%: resubstitution 193/193, CV 147/147, holdout 46/46.
  - **Result**: 713 SGFs, 100% clean, 0 errors, 0 gated.

### Phase F3: Gated Puzzle Recovery ✅

Recovered all 401 previously-gated puzzles via 5 structural fixes to `sgf_converter.py` and `sgf_tree_builder.py`.

**Fixes Applied:**

| Fix | What | Recovery |
|-----|------|----------|
| Noise filtering | Drop moves on occupied stones & outside bounding box | +48 SGFs |
| Trailing trim | Remove consecutive same-color moves at end of sequence | +226 SGFs |
| Strict alternation | Stop interleaving when one color runs out (no overflow) | Built into trim |
| Digit-order validation | When OCR digits don't alternate, fall back to interleaving | +127 SGFs |
| PL inference | Set PL[] from actual first move, not hardcoded Black | +1 SGF |
| Branch promotion | Promote wrong/variation to correct when no correct exists | +43 SGFs |
| Setup-only skip | Don't output puzzles without solution trees | -68 (quality gate) |
| Move truncation | Cap branches at 15 moves to trim image-recognition noise | Quality |

**Result**: 713 SGFs, 100% clean, 0 gated, 0 errors, 0 warnings.

### Phase G: Pipeline Output ✅
- 830 SGFs at `external-sources/authors/Minoru Harada/sgf/batch-001/`
- Sequential filenames: `harada_NNNN_L_SSS.sgf` (e.g., `harada_0036_e_069.sgf`)
- 773 with solution trees, 57 setup-only (`puzzle_only` marker in root comment)
- 28 remaining errors (no usable images for that level — permanently unrecoverable)
- Registered as local adapter in `backend/puzzle_manager/config/sources.json` (id: `harada-tsumego`)
- Source config: `include_folders: ["batch-001"]`, `validate: true`

### Phase G2: Post-Build Quality Fixes ✅

8 fixes applied in a single session (2026-04-11), improving yield from 713 → 830 SGFs:

| Fix | File | What | Impact |
|-----|------|------|--------|
| Answer-image blur fix | `sgf_tree_builder.py` | `RecognitionConfig(blur_kernels=(0,))` for answer images | Single-move SGFs 25→6, +30% total moves |
| Hybrid move ordering | `sgf_converter.py` | Use detected digits as anchors, infer undetected via alternation | Fixed ~42% of answer images with partial digit detection |
| Problem image inference | `sgf_tree_builder.py` | Infer problem from answer image by removing numbered stones | Recovered 60 puzzles with no problem image |
| Setup-only SGFs | `sgf_tree_builder.py` | Emit `puzzle_only` SGFs when no solution moves exist | 57 additional SGFs (setup only, no solution tree) |
| Sequential filenames | `__main__.py` | `harada_NNNN_L_SSS.sgf` format with global sequence counter | Visible count in filenames |
| Image filename rename | `orchestrator.py` | Level before type: `{year}_{seq}_{level}_{type}.gif` | Elementary/intermediate images group together |
| Overlap-based unknown filtering | `sgf_tree_builder.py` | `_is_compatible_variation()` checks stone overlap ≥90% | Unknown variations assigned to correct level only |
| Continuation branching | `sgf_tree_builder.py` | `_find_common_prefix()` already handled it | Variations branch at divergence point, not root |

### Phase F2c: Sub-Agent Validation ✅

20-puzzle random sample (15% × 2 batches) validated by Cho Chikun and Lee Sedol personas (2026-04-11).

**Results:**

| Rating | Count | % | Description |
|--------|-------|---|-------------|
| PASS | 11 | 55% | Tactically sound, no issues |
| WARN | 9 | 45% | Metadata issues only (comments, labels) |
| FAIL | 0 | 0% | None |

**Key findings:**
- All 20 solution trees are **tactically correct** — zero failures in Go logic
- Comment coordinate mismatches are the dominant quality issue (7/20 puzzles) — SGF moves correct, but comment text references wrong board coordinate. Systematic translation/OCR artifact.
- 2 puzzles have unlabeled variations (missing Correct/Wrong/Variation label)
- 1 puzzle (`harada_0392_m`) has same first move labeled both Correct and Wrong (BM[1]) — structural SGF issue
- 1 puzzle (`harada_0273_m`) has BM[1] on first node instead of the third move where the actual mistake occurs
- Zero outlier moves detected — all solution moves within margin=1 of setup stones
- Bbox margin=3 confirmed safe by both reviewers; no tightening needed (build pipeline already filters effectively)

**Comment coordinate error pattern:** Comments generated during F2a (comment redistribution) contain coordinate references from the original Japanese publication. These map to the printed diagram numbering, not SGF coordinates. The issue affects human-readable text only — the actual SGF move data is correct in all cases. Fixing this would require a dedicated comment-coordinate remapping pass (future F2 sub-phase).

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Core lib name | `image_to_board` | Generic; accepts PIL.Image or path, converts to numpy internally |
| Recognition engine | OpenCV + numpy | Full rewrite from Pillow pixel loops to vectorized numpy voting + OpenCV connected components |
| Digit detection | Template + feature classification | Template matching with color-specific templates (preferred), structural feature fallback. Zone distribution (3×3), h-bar, column fill, contour hierarchy. Multi-digit via component sorting |
| Eval methodology | Three-level: resub + CV + holdout | Resubstitution (train=test, labeled), LOIO-CV (honest generalization), holdout (unseen years) |
| Eval framework | Versioned JSON | `eval_digit_detection.py` with run-by-run tracking, confusion matrix, per-image breakdown |
| Config file | `harada_config.json` | Named after the author's puzzle collection |
| Directory | `tools/minoru_harada_tsumego/` | Attribution to the puzzle author |
| Slug | `harada-tsumego` | Short, unique, URL-safe |
| Recognition thresholds | `RecognitionConfig` dataclass | Parameterized; can be tuned per source |
| Tree building | Build on 14 test images first | Validate before committing to 4.5h download |
| Catalog schema | Enhanced single file (Option A) | 1,182 puzzles is small; sharding adds complexity without benefit |
| Checkpoint | Set-based (`completed_puzzles`) | Non-sequential resume; survives failures at any position |
| Semantic IDs | In catalog, not filesystem | YAGNI — disk filenames from source; semantic lookup via catalog |
| Image classification | Strict filename pattern matching | Catch-all classification let site decoration GIFs (`space.gif`, `igotop.gif`) pollute catalog as problem images, producing 145 empty SGFs |
| Validation gating | Skip broken SGFs vs output-with-warnings | Outputting broken SGFs wastes downstream pipeline time; gated puzzles logged for future re-processing |
| BM marker scope | First wrong move only | SGF spec: BM marks the mistake, not the forced continuations after it |
| Comment enrichment | Sub-agent pass (Phase F2) | Coordinate mapping requires understanding of move sequences + board context — beyond regex |
| Capture-replay handling | Warning, not error | Some puzzles have legitimate plays on captured stones (ko, snapback); diff-based approach can't model captures |
| Validator design | 11-rule Python script | Catches all known issues; runs in <1s; supports `--sample` and `--export` for iterative quality loops |

---

## Current Yield (as of 2026-04-11)

| Metric | Count |
|--------|-------|
| Puzzles in catalog | 1,182 |
| Puzzles with images | 429 |
| Max theoretical SGFs | 858 (429 × e + m) |
| **Clean SGFs output** | **830** (100% pass validation) |
| → With solution trees | 773 |
| → Setup-only (puzzle_only) | 57 |
| → Published to external-sources | 830 |
| Gated | 0 |
| Build errors | 28 (no usable images — permanently unrecoverable) |
| Permanently lost (404) | 753 puzzles |
| **Digit detection accuracy** | **100%** (193/193 on ground truth) |
| → Resubstitution | 100% (193/193 — train=test, labeled as such) |
| → Cross-validated (LOIO-CV) | 100% (147/147 — each image held out from template building) |
| → Holdout test set | 100% (46/46 — 8 images from 2002-2007, never in training) |
| **Sub-agent validation** | 20/20 tactically correct (11 PASS, 9 WARN, 0 FAIL) |
| → Comment coordinate errors | Fixed via per-section mapping (B2) |
| → BM[1] placement errors | Fixed via shared-prefix merging (B1) |
| **Image recognition enhancements** | Multi-blur voting, diameter filtering, K-means adaptive |
| **Answer-image fix (2026-04-11)** | blur_kernels=(0,) for answer images; hybrid ordering; problem inference; overlap filtering |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [MEMORY.md](MEMORY.md) | Lessons learned, bugs, architecture decisions, catalog redesign rationale |
| [RESEARCH_LOG.md](RESEARCH_LOG.md) | Initial discovery research — site structure, image formats, Go-Advisor assessment |
| [README.md](README.md) | User-facing documentation — architecture, CLI usage, recognition algorithm |

---

*Last updated: 2026-04-11 (Phase G2 — 8 post-build quality fixes, yield 713→830, errors 145→28)*
