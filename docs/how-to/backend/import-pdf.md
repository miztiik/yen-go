# Import PDF Books

> **See also**:
>
> - [Reference: Puzzle Sources](../../reference/puzzle-sources.md) — Available pre-converted sources
> - [How-To: Create Adapter](./create-adapter.md) — Adapter development
> - [Architecture: Adapter Design](../../architecture/backend/adapter-design-standards.md) — Adapter patterns

**Last Updated**: 2026-03-24

> ⚠️ **FUTURE FEATURE** - This guide describes planned functionality not yet implemented.

---

## Overview

PDF-to-SGF import enables importing Go/Baduk tsumego puzzles from PDF books by:
1. Extracting page images from PDF files
2. Detecting Go board images on each page
3. Using computer vision to recognize stone positions
4. Matching problems with their solutions
5. Converting recognized positions to SGF format

---

## When Implemented

### Usage (Planned)

```bash
# Import single PDF
yengo-pm pdf-import --url https://example.com/book.pdf

# Import local file
yengo-pm pdf-import --file ./books/cho-elementary.pdf

# Batch import from manifest
yengo-pm pdf-import --manifest ./books/manifest.json
```

### Architecture (Planned)

```
PDF → Extract Pages → Detect Boards → Recognize Stones → Match Solutions → Generate SGF
```

**8-Stage Pipeline**:
1. **PDF Fetch** - Download or read local PDF
2. **Page Extract** - Convert pages to 200 DPI images
3. **Board Detect** - Find Go board regions using OpenCV
4. **Stone Recognize** - Detect black/white stones
5. **OCR/ID** - Extract problem numbers
6. **Problem-Solution Match** - Pair problems with solutions
7. **SGF Generate** - Create valid SGF files
8. **Publish** - Send to puzzle pipeline

---

## Technical Requirements

### Libraries (Planned)

| Component | Library | Purpose |
|-----------|---------|---------|
| PDF to Images | pdf2image (poppler) | Extract page images |
| Board Detection | skolchin/gbr + OpenCV | Find board regions |
| Stone Recognition | gbr + Hough Circles | Detect stone positions |
| OCR | pytesseract | Read problem numbers |
| SGF Generation | sgfmill | Create SGF files |

### Accuracy Targets

- Stone recognition: >95% on computer-rendered images
- Stone recognition: >85% on scanned books
- Problem-solution matching: >90% when numbering visible
- Valid SGF output: 80% pass validation without manual correction

---

## Related Specs

- [spec-009](../../specs/009-pdf-to-sgf-import/spec.md) - Full specification
- This is a "Category C" source (high effort) per the External Resources Import spec

---

## Current Alternatives

Until PDF import is implemented, use these alternatives:

1. **Pre-converted Collections** - Use sources like `travisgk/tsumego-pdf` which have already extracted PDFs
2. **Manual Conversion** - Use EidoGo or similar to manually create SGF from PDF images
3. **JSON Sources** - Import from `sanderland/tsumego` which provides JSON format

See [reference/puzzle-sources.md](../reference/puzzle-sources.md) for available pre-converted sources.
