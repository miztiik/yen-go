# Import PDF Books

> **See also**:
>
> - [Reference: Puzzle Sources](../../reference/puzzle-sources.md) — Available pre-converted sources
> - [How-To: Create Adapter](./create-adapter.md) — Adapter development
> - [Architecture: Adapter Design](../../architecture/backend/adapter-design-standards.md) — Adapter patterns

**Last Updated**: 2026-07-11

---

## Overview

The `tools/pdf_to_sgf` tool imports Go/Baduk tsumego puzzles from PDF books by:

1. Extracting page images from PDF files (embedded or rendered)
2. Detecting Go board regions on each page via connected-component analysis
3. Recognizing stone positions with OpenCV (grid voting + multi-blur classification)
4. Matching problems with their answer-key solutions via Jaccard similarity
5. Generating SGF files with initial stones and solution moves

**Requirements**: Python 3.11+, OpenCV (`cv2`), PyMuPDF (`fitz`), Pillow, NumPy.

---

## Quick Start

### Preview PDF structure

```bash
# See how many boards are detected per page
python -m tools.pdf_to_sgf preview --pdf path/to/book.pdf

# Limit to specific pages
python -m tools.pdf_to_sgf preview --pdf path/to/book.pdf --pages 3-5
```

### Extract and recognize boards

```bash
# Extract boards, show grid/stone counts, save crops
python -m tools.pdf_to_sgf extract --pdf book.pdf --output-dir ./crops/

# Use PDF preset for scanned/low-contrast images
python -m tools.pdf_to_sgf extract --pdf book.pdf --preset pdf

# Verbose output (prints full board grids)
python -m tools.pdf_to_sgf extract --pdf book.pdf -v
```

### Convert to SGF

```bash
# Problem PDF + answer key PDF → matched SGF files
python -m tools.pdf_to_sgf convert \
  --pdf problems.pdf \
  --key answers.pdf \
  --output-dir ./sgf_output/

# Problem PDF only (no solution tree)
python -m tools.pdf_to_sgf convert \
  --pdf problems.pdf \
  --output-dir ./sgf_output/

# Limit to a page range
python -m tools.pdf_to_sgf convert \
  --pdf problems.pdf \
  --key answers.pdf \
  --output-dir ./sgf_output/ \
  --pages 3-10
```

---

## Architecture

```text
PDF → Extract Pages → Detect Boards → Recognize Stones → Match Solutions → Generate SGF
         (fitz)       (OpenCV CC)     (image_to_board)    (Jaccard sim)     (SGFBuilder)
```

### Modules

| Module              | Purpose                                       |
| ------------------- | --------------------------------------------- |
| `pdf_extractor.py`  | PDF → page images (embedded preferred, render fallback) |
| `board_detector.py` | Page image → board region crops (binarize + CC analysis) |
| `problem_matcher.py` | Problem-answer matching + solution extraction |
| `__main__.py`       | CLI tool: `extract`, `convert`, `preview`     |

### Recognition Presets

| Preset    | When to use                                  |
| --------- | -------------------------------------------- |
| `default` | Computer-generated PDFs (clean lines)        |
| `pdf`     | Scanned or low-contrast PDFs (CLAHE enabled) |
| `scan`    | Physical book scans with uneven lighting     |

---

## How Problem-Answer Matching Works

1. All boards from the problem PDF and answer-key PDF are detected and recognized
2. Stone positions are extracted as sets of `(row, col)` coordinates
3. Each answer board is matched to the problem board with the highest Jaccard similarity
4. Solution moves = stones in answer that aren't in the problem
5. Fallback: if similarity matching fails but board counts are equal, boards are paired by order

**Minimum similarity threshold**: 0.3 (configurable in code).

---

## Limitations

- Grid detection depends on visible grid lines; heavily obscured boards may fail
- Stone color classification can struggle with unusual PDF rendering
- Digit detection (for numbered solution moves) is available but not yet integrated into move ordering
- Partial boards (corner-only diagrams) are supported but may not cover the full 19×19 range

---

## Testing

```bash
# Run all PDF pipeline tests
pytest tools/pdf_to_sgf/tests/ -q --no-header --tb=short
```

Tests require sample PDFs in `tools/pdf_to_sgf/_test_samples/`. These are not tracked in git. The test suite skips gracefully if samples are absent.
