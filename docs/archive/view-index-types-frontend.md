# View Index Types Architecture

**Last Updated**: 2026-02-20

## Overview

The frontend uses a v4.0 compact entry system for all view index data (level, tag, collection). All views are always-paginated with a directory structure. Compact entries use short keys and numeric IDs on the wire, decoded to domain types at the loader boundary.

## JSON Schema Contract

**Source of truth**: [`config/schemas/view-index.schema.json`](../../../config/schemas/view-index.schema.json)

The schema defines these document types:

| Document Type  | Purpose                            | TypeScript Type                                                 |
| -------------- | ---------------------------------- | --------------------------------------------------------------- |
| PageDocument   | Single page of compact entries     | `PageDocument<T extends ViewEntry>`                             |
| DirectoryIndex | Pagination directory/metadata      | `DirectoryIndex`                                                |
| MasterIndex    | Top-level index with distributions | `LevelMasterIndex`, `TagMasterIndex`, `CollectionMasterIndexV2` |

## Compact Entry Format (Wire)

All view types share the same compact wire format defined in `services/entryDecoder.ts`:

```typescript
interface CompactEntry {
  p: string; // "0001/hash" → sgf/0001/hash.sgf
  l: number; // Numeric level ID (110-230)
  t: number[]; // Numeric tag IDs (Obj 10-16, Tesuji 30-52, Tech 60-82)
  c: number[]; // Numeric collection IDs (1-159)
  x: number[]; // [depth, refutations, solution_length, unique_responses]
  n?: number; // Sequence number (collection entries only)
}
```

## Decode Layer

`entryDecoder.ts` and `configService.ts` form the decode boundary between wire format and domain types:

| Wire Format    | Decode Function           | Domain Type       | Fields             |
| -------------- | ------------------------- | ----------------- | ------------------ |
| `CompactEntry` | `decodeLevelEntry()`      | `LevelEntry`      | `{path, tags}`     |
| `CompactEntry` | `decodeTagEntry()`        | `TagEntry`        | `{path, level}`    |
| `CompactEntry` | `decodeCollectionEntry()` | `CollectionEntry` | `{path, level, n}` |

`configService.ts` provides the ID resolution (delegates to config modules via Vite JSON imports):

- `levelIdToSlug(id)`: 120 → "beginner"
- `tagIdToSlug(id)`: 36 → "net"

`entryDecoder.ts` provides the decode functions and utilities:

- `expandPath(p)`: "0001/hash" → "sgf/0001/hash.sgf"
- `isCompactEntry(entry)`: type guard detecting compact vs legacy format
- `decodeEntry(raw)`: unified decoder returning `DecodedEntry` with complexity

## Data Flow

```
JSON Schema (config/schemas/view-index.schema.json)
    ↓ validates
Compact Entries (wire: {p, l, t, c, x})
    ↓ fetched by
Pagination Loaders (src/lib/puzzle/pagination.ts)
    ↓ decoded at boundary via entryDecoder.ts + configService.ts
Domain Types (LevelEntry, TagEntry, CollectionEntry)
    ↓ used by
Service Layer (puzzleLoader.ts, collectionService.ts, tag-loader.ts)
    ↓ normalized data
Hooks (usePaginatedPuzzles.ts → usePaginatedView)
    ↓ reactive state
Components (PuzzleGrid, CollectionViewPage, TechniqueFocusPage, etc.)
```

## Generic Pagination API

All views are always-paginated (`{entity}/index.json` + `{entity}/page-NNN.json`):

```typescript
// Load a single page of entries (decodes compact entries internally)
loadPage<T extends ViewEntry>(baseUrl: string, type: ViewType, name: string, page: number): Promise<PageDocument<T>>

// Create a full pagination loader with state management
createPaginationLoader<T extends ViewEntry>(type: ViewType, options: PaginationLoaderOptions): PaginationLoader<T>
```

## Master Index v2.0

Master indexes include distribution counters with numeric ID keys:

```typescript
interface LevelMasterEntry extends MasterIndexEntry {
  tags: Record<string, number>; // {"36": 5, "60": 3}
}
interface TagMasterEntry extends MasterIndexEntry {
  levels: Record<string, number>; // {"120": 8, "160": 3}
}
interface CollectionMasterEntry extends MasterIndexEntry {
  levels: Record<string, number>;
  tags: Record<string, number>;
}
```

## Type Guards

Runtime type checking:

| Guard                             | Checks                                                                        |
| --------------------------------- | ----------------------------------------------------------------------------- |
| `isCompactEntry(entry)`           | Has `p` string property (compact vs legacy) — exported from `entryDecoder.ts` |
| `isDirectoryIndex(data)`          | `total_count` + `page_size` + `pages`                                         |
| `isPageDocument(data)`            | `page` + `entries`                                                            |
| `isCollectionMasterIndexV3(data)` | `collections` array (checks `CollectionMasterIndexV2` type)                   |

## Contract Test

[`tests/unit/view-schema-contract.test.ts`](../../../frontend/tests/unit/view-schema-contract.test.ts) validates TypeScript types match JSON Schema `$defs` at build time.

> **See also**:
>
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — SGF custom properties and schema version
> - [Concepts: Numeric ID Scheme](../../concepts/numeric-id-scheme.md) — ID ranges and category bands
> - [Reference: View Index Schema](../../reference/view-index-schema.md) — Full schema reference
