# SGF Processing Architecture

> **See also**:
>
> - [Architecture: Frontend Overview](./overview.md) — Technology stack, component hierarchy
> - [Architecture: Board State Design](./board-state-design.md) — Coordinate system
> - [Architecture: Goban Integration](./goban-integration.md) — goban library rendering
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — YenGo custom SGF properties

**Last Updated**: 2026-03-24

---

## SGF Processing Modules

The frontend has **three SGF modules** at different layers:

| Module | Location | Responsibility |
|--------|----------|---------------|
| SGF Parser | `lib/sgf/parser.ts` | SGF string → parsed tree (core parser) |
| Metadata Extractor | `lib/sgf-metadata.ts` | Extract metadata from parsed SGF |
| Preprocessor | `lib/sgf-preprocessor.ts` | Clean/normalize SGF, extract YenGo properties |

Additional SGF modules:
- `lib/sgf-solution.ts` — Builds `SolutionNode` tree from parsed SGF
- `lib/sgf-to-puzzle.ts` — SGF → `PuzzleObject` (initial_state + move_tree)

```
Raw SGF string
    │
    ▼
sgf-preprocessor.ts ──► YenGoMetadata (level, tags, hints, ko, moveOrder)
    │                     + firstCorrectMove (bracket-depth-aware extraction)
    ▼
lib/sgf/parser.ts   ──► Parsed SGF tree
    │
    ▼
lib/sgf-solution.ts ──► SolutionNode tree (for move validation)
    │
    ▼
goban library        ──► Board rendering, variation tree navigation
```

### Why Pre-processing?

goban's `parseSGF()` silently ignores unknown SGF properties. YenGo-specific properties (`YG`, `YT`, `YH`, `YK`, `YO`, `YL`) must be extracted from raw SGF text **before** passing to goban. The preprocessor:

1. Extracts metadata via regex
2. Validates levels/tags against boot-loaded config (`getBootConfigs()`)
3. Strips custom properties so goban receives clean SGF

---

## Key Module: `sgf-preprocessor.ts`

### Input/Output

```typescript
// Input: raw SGF text
const result: PreprocessedPuzzle = preprocessSgf(rawSgf);

// Output
result.metadata; // YenGoMetadata — level, tags, hints, koContext, moveOrder
result.cleanSgf; // string — SGF with YenGo properties stripped
result.firstCorrectMove; // string | undefined — first correct move coordinate
```

### YenGoMetadata Fields

| Field       | Type                           | Source                   | Default      |
| ----------- | ------------------------------ | ------------------------ | ------------ |
| `level`     | `LevelSlug`                    | `YG[intermediate]`       | `'beginner'` |
| `tags`      | `string[]`                     | `YT[ko,ladder]`          | `[]`         |
| `hints`     | `string[]`                     | `YH[Corner\|Ladder\|C3]` | `[]` (max 3) |
| `koContext` | `'none'\|'direct'\|'approach'` | `YK[direct]`             | `'none'`     |
| `moveOrder` | `'strict'\|'flexible'`         | `YO[strict]`             | `'flexible'` |

### `firstCorrectMove` Extraction

The parser uses a **bracket-depth-aware** algorithm to find the first correct move from the SGF solution tree. Edge cases handled:

- **Pass moves** (`B[]` or `W[]`)
- **BM (Bad Move) markers** — skipped, not considered "correct"
- **Comment brackets** — `C[text with [brackets]]` doesn't break depth tracking
- **Setup stones** — `AB`, `AW`, `AE` are ignored (not moves)

---

## Coordinate System

Board coordinates use the `utils/coordinates.ts` module:

- SGF uses `aa`–`ss` letter pairs (a=1, s=19)
- Display uses A1–T19 (skipping 'I' per Go convention)
- Conversion: `sgfToDisplay('cc')` → `'C3'`

---

## Relationship to goban

| Responsibility            | Module                                     |
| ------------------------- | ------------------------------------------ |
| SGF metadata extraction   | `sgf-preprocessor.ts`                      |
| Board rendering           | `goban` library (via `useGoban` hook)      |
| Move validation           | `goban` puzzle mode (built-in)             |
| Variation tree navigation | `goban` `GoEngine`                         |
| Board markers             | `useBoardMarkers` hook (reads goban state) |

goban is treated as an **untouched external dependency** (FR-012): we configure it but never modify its source.
