# Harada Tsumego Tool

Import and process **Weekly Tsumego by Minoru Harada** (1996–2020) — a collection of 1,182 Go life-and-death problems originally published on the Hitachi website, now preserved via the Wayback Machine.

Each weekly puzzle provides elementary and intermediate levels, with problem diagrams, correct answers, wrong answers, and variation diagrams.

## Architecture

```
tools/minoru_harada_tsumego/
├── __main__.py          # CLI entry point (discover, download, recognize, build, status)
├── config.py            # CollectionConfig frozen dataclass + load_config()
├── crawler.py           # WaybackCrawler with rate limiting and caching
├── parsers.py           # HTML parsers (old table + new dl/dt formats)
├── orchestrator.py      # Discovery & download pipeline with checkpoint resume
├── models.py            # Catalog, PuzzleEntry, PuzzleImage, YearEntry
├── sgf_converter.py     # Position → SGF, diff-based move extraction
├── sgf_tree_builder.py  # Full puzzle SGF with solution tree from image pairs
├── eval_digit_detection.py  # Evaluation framework: resubstitution, LOIO-CV, holdout
├── extract_templates.py # Digit template extraction from ground truth
├── harada_config.json   # Collection configuration
├── PLAN.md              # Implementation plan with phase tracking
├── MEMORY.md            # Lessons learned, bugs, decisions
├── RESEARCH_LOG.md      # Initial site structure research
└── _working/            # Runtime data (not in git)
    ├── catalog.json     # Puzzle catalog with discovery/download state
    ├── ground_truth.json # Digit detection ground truth (30 images, 193 digits)
    ├── eval_results.json # Versioned evaluation runs
    ├── _page_cache/     # Cached HTML pages
    └── _images/{year}/  # Downloaded GIF images
```

### Core Dependencies

| Module | Purpose |
|--------|---------|
| `tools/core/image_to_board.py` | OpenCV + numpy board recognition (grid, stones, digits) |
| `tools/core/sgf_builder.py` | SGFBuilder fluent API for SGF construction |
| `tools/core/sgf_types.py` | Color, Point, Move primitives |
| `tools/core/logging.py` | Structured logging setup |
| `tools/core/paths.py` | Working directory aliases |

### Python Dependencies

- `opencv-python-headless>=4.8` — Grid detection, stone classification, digit detection
- `numpy>=1.24` — Vectorized image processing
- `Pillow>=10.0` — Image loading

## Recognition Algorithm

OpenCV + numpy pipeline. Implemented in `tools/core/image_to_board.py`:

1. **Grid detection** — Numpy vectorized dark-pixel voting: convert to grayscale numpy array, scan rows/columns counting dark pixels via boolean comparisons. Grid lines vote consistently across the image; stones are localised. Lines clustered by proximity, filtered by spacing regularity.
2. **Grid completion** — Missing lines filled by median-spacing interpolation. Edge lines extended to image boundaries.
3. **Stone classification** — Numpy array slicing at each grid intersection. Extract square ROI (radius ≈ spacing/3), compute mean intensity and dark/bright pixel ratios via vectorized ops. Thresholds configurable via `RecognitionConfig`.
4. **Edge detection** — Boundary vs interior line thickness comparison using numpy array projections. Ratio > 1.4 → board edge detected. Maps partial boards to 19×19 coordinates.
5. **Digit detection** — Connected component analysis via `cv2.connectedComponentsWithStats()`:
   - ROI extraction around stone center (radius ≈ grid spacing × 0.3)
   - Adaptive thresholding: bright digits on black stones, dark digits on white stones
   - Component filtering by area, aspect ratio, centrality
   - **Single-digit classification**: Structural feature analysis — zone distribution (3×3 grid), horizontal bar detection, column fill patterns, contour hierarchy holes (`cv2.findContours(RETR_TREE)`)
   - **Multi-digit detection** (10-18): Multiple valid components sorted left-to-right, assembled as `left × 10 + right`
   - **Template matching**: Color-specific templates preferred (`digit_N_black.npy`/`digit_N_white.npy`), falls back to universal templates
   - Rule-based classifier with ordered rules: 1→7→4→5→6→2→8→9→0→3
   - **Stone-size post-filtering**: Detected stones with insufficient active pixel coverage relative to grid spacing are reclassified as EMPTY
   - **K-means validation**: Diagnostic `validate_stone_colors()` checks if K-means(k=2) cluster boundary diverges from fixed thresholds
   - Accuracy: **100%** on 193-digit ground truth (30 images, 3-level evaluation)

Configurable via `RecognitionConfig` frozen dataclass with tunable thresholds.

## Evaluation Framework

Three-level digit detection accuracy tracking in `eval_digit_detection.py`:

```bash
# Standard eval (resubstitution — train=test, labeled as such)
python -m tools.minoru_harada_tsumego eval

# Leave-One-Image-Out cross-validation (honest generalization metric)
python -m tools.minoru_harada_tsumego eval --cv

# Holdout test set (8 images from 2002-2007, never in training)
python -m tools.minoru_harada_tsumego eval --holdout

# Compare all historical runs
python -m tools.minoru_harada_tsumego eval --compare

# Custom run ID
python -m tools.minoru_harada_tsumego eval --run-id v2.0_template_matching
```

- **Resubstitution** (193 digits, 30 images): Templates trained on same data — explicitly labeled, useful for regression checks
- **LOIO-CV** (147 digits, 22 training images): Each image held out in turn, templates built from remaining 21 — proves generalization
- **Holdout** (46 digits, 8 images from 2002-2007): Never-seen images with independently verified digits — unbiased accuracy estimate
- Ground truth: `_working/ground_truth.json` (22 training + 8 holdout images)
- Results: `_working/eval_results.json` (versioned runs with accuracy, confusion matrix, per-image breakdown)

## Image Naming Convention

### Modern format (most puzzles)

| Pattern | Meaning |
|---------|---------|
| `{NNN}ep.gif` | Elementary problem |
| `{NNN}mp.gif` | Intermediate problem |
| `{NNN}ea{V}.gif` | Elementary answer (correct), variant V |
| `{NNN}ew{V}.gif` | Elementary wrong answer, variant V |
| `{NNN}ev{V}.gif` | Elementary variation |
| `{NNN}ma{V}.gif` | Intermediate answer (correct), variant V |
| `{NNN}mw{V}.gif` | Intermediate wrong answer, variant V |

### Old format (early puzzles, 1996)

| Pattern | Meaning |
|---------|---------|
| `{N}p{V}.gif` | Problem image, variant V |
| `{N}c{V}.gif` | Problem image (alternate), variant V |

Only puzzles #2–5 use this format. Classified as `problem` with empty level.

### Skipped filenames

Site decoration images (`space.gif`, `igotop.gif`, etc.) are skipped during parsing. Only filenames matching the patterns above are classified as puzzle images.

## CLI Usage

```bash
# Discovery — crawl index/year pages, build catalog
python -m tools.minoru_harada_tsumego discover

# Download — fetch all images (set-based checkpoint resume)
python -m tools.minoru_harada_tsumego download [--limit N]
python -m tools.minoru_harada_tsumego download --retry-only    # Only process pending/failed puzzles
python -m tools.minoru_harada_tsumego download --year 1996     # Only process a specific year

# Recognize — extract board position from single image
python -m tools.minoru_harada_tsumego recognize --image path/to/image.gif

# Build — construct SGF with solution tree
python -m tools.minoru_harada_tsumego build --puzzle 1 --level elementary
python -m tools.minoru_harada_tsumego build --all --output-dir sgf_output/

# Status — show catalog summary with per-year breakdown
python -m tools.minoru_harada_tsumego status

# Eval — run digit detection accuracy evaluation
python -m tools.minoru_harada_tsumego eval
python -m tools.minoru_harada_tsumego eval --cv        # Cross-validated accuracy
python -m tools.minoru_harada_tsumego eval --holdout   # Holdout-only eval
python -m tools.minoru_harada_tsumego eval --compare   # Compare all runs
python -m tools.minoru_harada_tsumego eval --no-save   # Run without saving
```

## Solution Tree Building

The `build` command produces SGFs with full move trees:

1. **Problem image** → `recognize_position()` → setup stones (AB/AW)
2. **Correct answer image** → diff against problem → ordered correct moves (main line)
3. **Wrong answer image** → diff against problem → wrong moves (variation branches)
4. **Variation image** → diff against problem → alternative continuations

SGF structure:
```
(;FF[4]GM[1]SZ[19]PL[B]
  AB[...]AW[...]
  C[Harada #1 (Elementary)\nBlack 1 is the vital point...]
  (;B[cb]C[Correct] ;W[bb] ;B[ac] ;W[ab] ;B[ba])
  (;B[ac]C[Wrong] ;W[ab] ;B[cb] ;W[ba])
  (;B[cb] ;W[ba] ;B[ab] ;W[ac] ;B[bb])
)
```

## Data Flow

```
Wayback Machine → crawler.py → _page_cache/ (HTML)
                → parsers.py → catalog.json (metadata)
                → orchestrator.py → _images/{year}/ (GIF)
                → image_to_board.py → RecognizedPosition
                → sgf_tree_builder.py → SGF with move tree
                → (future) external-sources/harada-tsumego/sgf/
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [PLAN.md](PLAN.md) | Implementation plan with phase tracking |
| [MEMORY.md](MEMORY.md) | Lessons learned, bugs, architecture decisions, catalog redesign rationale |
| [RESEARCH_LOG.md](RESEARCH_LOG.md) | Initial discovery research — site structure, image formats, Go-Advisor assessment |

---

*Last updated: 2026-04-11*
