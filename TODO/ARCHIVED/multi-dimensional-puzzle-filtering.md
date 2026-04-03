# Multi-Dimensional Puzzle Filtering — Research & Plan

**Last Updated**: 2026-02-17  
**Status**: Research Complete — Decisions Finalized → Ready for Implementation  
**Scale Target**: 150,000–200,000+ puzzles  
**Migration Strategy**: Big-bang (no backward compatibility required)  
**ViewEnvelope Version**: 4.0 (bump from 3.0)  
**Master Index Version**: 2.0 (bump from 1.0)  
**Schema Name**: ViewEnvelope (kept — no better verb-based alternative found)

---

## 1. Problem Statement

The app has three primary entry points from the home page, each selecting puzzles along a **primary dimension**. Users need the ability to **slice and dice** along secondary dimensions:

| Entry Point | Primary Dimension | Secondary Dimension(s) Needed | Status Today |
|-------------|-------------------|-------------------------------|--------------|
| **Training** (by Level) | Level (e.g., Beginner: 30k–25k) | Technique/Tag filter | **No secondary filter** |
| **Technique** (by Tag) | Tag (e.g., "ladder", "capture") | Level filter | **No secondary filter** |
| **Collections** | Collection (e.g., "Cho Chikun Elementary") | Level **AND** Tag (two secondary dimensions) | **No secondary filter** |
| **Daily** | Date (today's challenge) | Level **AND** Tag | **No secondary filter** |
| **Puzzle Rush** | (fetches from levels/tags) | Level **AND** Tag | Level selection only |

### Why This Matters (Cho Chikun / Go Expert Perspective)

> *"A 25-kyu player studying net (geta) problems must see positions with 2–3 liberties, not the 6-liberty nets that challenge dan players. Showing all levels together is like giving a math student algebra and calculus mixed together."*

> *"A collection like 'Cho Chikun's Elementary Life and Death' inherently spans levels. A student who finds it too hard should be able to filter down to just the novice/beginner puzzles."*

---

## 2. Current Architecture Analysis

### 2.1 View Index Entry Schemas (v3.0, Spec 119/130/131)

The current view indexes use **minimal, single-purpose entry shapes** per Spec 119, which deliberately removed cross-dimensional data to reduce payload:

| View Type | Directory | Entry Shape | Cross-ref Data |
|-----------|-----------|-------------|----------------|
| **by-level** | `views/by-level/{level}.json` | `{path, tags}` | Has tags ✓, level implicit from filename |
| **by-tag** | `views/by-tag/{tag}.json` | `{path, level}` | Has level ✓, tag implicit from filename |
| **by-collection** | `views/by-collection/{slug}.json` | `{path, level, sequence_number}` | Has level ✓, **NO tags** ✗ |
| **daily** | `views/daily/{YYYY}/{MM}/{date}-{NNN}.json` | `{path, level}` | Has level ✓, **NO tags** ✗ |

### 2.2 Master Indexes (Current)

Three master indexes exist at `views/by-{type}/index.json` (no daily master index exists yet):

```json
{
  "version": "1.0",
  "generated_at": "2026-02-16T22:06:15Z",
  "levels": [
    {"name": "beginner", "slug": "beginner", "paginated": false, "count": 6}
  ]
}
```

**Gap**: Master indexes contain only `{name, slug, paginated, count}`. No distribution data (e.g., "beginner has 12 ladder puzzles"). This means the UI cannot show "47 puzzles (12 at your level)" without loading the full tag index.

### 2.3 `collections.json` Catalog (Current)

Each collection in `config/collections.json` has: `slug`, `name`, `description`, `curator`, `source`, `type`, `ordering`, `tier`, `aliases[]`.

**Gap**: No `levels[]` or `tags[]` fields. The UI cannot show "spans 3 levels, covers ko and ladder" on the collection browse page without loading the full collection index.

### 2.4 Pagination System

- **Threshold**: 500 entries per file (configurable via `PaginationConfig`)
- **Flat mode**: Single `{slug}.json` ViewEnvelope when count ≤ 500
- **Paginated mode**: Directory with `index.json` (DirectoryIndex) + `page-NNN.json` (PageDocument) files
- **State tracking**: `.pagination-state.json` tracks total/pages/last_page_count per entity
- **PaginationWriter**: Handles flat→paginated transitions, dedup, append-only, atomic writes

### 2.5 Frontend Data Consumption

| Component | Data Source | Filtering Capability |
|-----------|-----------|---------------------|
| `TrainingPage` | `loadLevelIndex(level)` → by-level view | None — plays all puzzles at that level |
| `TechniqueFocusPage` → `CollectionViewPage` | `loadTagIndex(tag)` → by-tag view | None — plays all levels for that tag |
| `CollectionViewPage` | `loadCollection(id)` → by-collection view | None — plays all entries in order |
| `RandomPage` | Level filter → `loadLevelIndex()` | Level selection only (1D) |
| `collectionService.loadFilteredPuzzles()` | Loads by-level + filters by tags client-side | **Cross-dimensional but not exposed in main UI** |

### 2.6 Existing Cross-Filtering Code (Unused)

**Backend (tag-loader.ts)**:
- `filterPuzzlesByLevel(tag, level)` — loads tag index, filters `entries.filter(e => e.level === level)` — **exists but no UI calls it**
- `filterPuzzlesByRank(tag, minRank, maxRank)` — exists, unused

**Backend (collectionService.ts)**:
- `loadFilteredPuzzles(level, tags)` — loads level indexes, filters by tag intersection — **only used by CreatePracticeSetModal, not by main navigation**

### 2.7 JSON Schema (`config/schemas/view-index.schema.json`)

The schema is the source of truth. Currently:
- `LevelEntry`: `{path: string, tags: string[]}` — `additionalProperties: false`
- `TagEntry`: `{path: string, level: string}` — `additionalProperties: false`
- `CollectionEntry`: `{path: string, level: string, sequence_number: integer}` — `additionalProperties: false`

The `additionalProperties: false` constraint means adding new fields requires schema migration.

---

## 3. Scale Analysis (150k–200k puzzles)

### 3.1 Projected Data Volumes

| Metric | Current | At 200k puzzles |
|--------|---------|-----------------|
| Total SGF files | 57 | 200,000 |
| Tags per puzzle (avg) | 2.5 | ~3 (more diversity) |
| Total tag assignments | 144 | ~600,000 |
| Levels populated | 7 of 9 | 9 of 9 |
| Avg puzzles per level | ~8 | ~22,000 |
| Avg puzzles per tag | ~14 | ~21,000 (28 tags) |
| Collections | ~14 | 200+ |
| Avg puzzles per collection | ~4 | ~200–2,000 |

### 3.2 Per-Entry Payload Sizes

| Entry Type | Current Size | With Uniform Schema | Delta |
|------------|-------------|--------------------:|------:|
| LevelEntry `{path, tags}` | ~164 B | ~180 B (+level field) | +16 B |
| TagEntry `{path, level}` | ~110 B | ~180 B (+tags array) | +70 B |
| CollectionEntry `{path, level, seq}` | ~130 B | ~210 B (+tags array) | +80 B |

### 3.3 File Size Projections (With Uniform Schema)

**Important**: Gzip compression is NOT something we do. GitHub Pages' CDN automatically applies `Content-Encoding: gzip` during HTTP transport when the browser requests it. Files are stored as **raw uncompressed JSON** in the git repo and on GitHub Pages' storage. The "over the wire" column shows what the browser actually downloads; the "raw JSON" column is what matters for git repo size, browser memory, and `JSON.parse()` time.

| Scenario | Entries | Entry Size | Raw JSON (on disk) | Over the wire (auto-gzip by GH Pages) |
|----------|---------|-----------|----------|--------|
| Largest level (22k puzzles) | 22,000 | 180 B | **3.9 MB** | **~600 KB** |
| Single page (500 entries) | 500 | 180 B | **88 KB** | **~14 KB** |
| Largest tag (21k puzzles) | 21,000 | 180 B | **3.7 MB** | **~560 KB** |
| Large collection (2k) | 2,000 | 210 B | **410 KB** | **~65 KB** |
| Master index (9 levels enriched) | 9 | ~350 B | **~5 KB** | **~1.5 KB** |
| Tag master index (28 tags enriched) | 28 | ~300 B | **~10 KB** | **~3 KB** |
| Collection master index (200 enriched) | 200 | ~450 B | **~90 KB** | **~15 KB** |
| Daily master index (365 dates) | 365 | ~150 B | **~55 KB** | **~10 KB** |

### 3.4 Pagination Impact

At the 500-entry threshold with 200k puzzles:
- **by-level**: 9 levels × avg 44 pages each = ~400 page files
- **by-tag**: 28 tags × avg 42 pages each = ~1,200 page files  
- **by-collection**: 200 collections × avg 1-4 pages each = ~400 page files
- **Total page files**: ~2,000 files (all ≤88 KB each, manageable for GitHub Pages)

### 3.5 Client-Side Filtering Performance

Filtering 500 entries (one page) using `Array.filter()`:
- **Time**: <1ms on any modern device
- **Memory**: ~90 KB for the page + negligible filter overhead
- **Verdict**: **Client-side filtering per page is the correct approach** — no need for pre-computed cross-dimensional indexes

For the master indexes and filter preview (e.g., "12 beginner ladder puzzles"), loading a 500-entry page and counting is fast, but loading 44 pages to count across an entire tag would require 44 HTTP requests. **This is where enriched master indexes add value** — they provide counts without loading entry data.

---

## 4. Proposed Changes

### 4.1 Uniform Entry Schema (Big-Bang Migration)

**Every view entry gets `{path, level, tags}`** regardless of view type. Collection entries additionally keep `sequence_number`.

#### New Entry Shapes

```typescript
// UNIFIED: Every entry has path + level + tags
interface UnifiedViewEntry {
  readonly path: string;       // Relative path to SGF
  readonly level: string;      // Difficulty level slug
  readonly tags: readonly string[];  // Technique tags
}

// LevelEntry = UnifiedViewEntry (level is now explicit, not implicit)
interface LevelEntry extends UnifiedViewEntry {}

// TagEntry = UnifiedViewEntry (tags are now explicit, not just the parent tag)
interface TagEntry extends UnifiedViewEntry {}

// CollectionEntry = UnifiedViewEntry + sequence_number
interface CollectionEntry extends UnifiedViewEntry {
  readonly sequence_number: number;
}
```

#### Rationale

1. **Eliminates all data gaps** — every view can be filtered by level AND tags without cross-loading
2. **Simplifies frontend code** — one consistent entry shape, no type-specific handling
3. **Client-side filtering is trivial** — `entries.filter(e => e.level === selectedLevel && e.tags.includes(selectedTag))`
4. **Payload cost is acceptable** — +16 to +80 bytes per entry, offset by gzip compression
5. **Big-bang migration** means no backward-compatibility wrapper code

#### Backend Changes (publish.py)

```python
# BEFORE (Spec 119 — different shapes per view type):
level_entry = {"path": rel_path, "tags": game.yengo_props.tags}
tag_entry = {"path": rel_path, "level": level_name}
collection_entry = {"path": rel_path, "level": level_name, "sequence_number": ...}

# AFTER (Uniform schema):
base_entry = {"path": rel_path, "level": level_name, "tags": game.yengo_props.tags}
level_entry = base_entry  # Same shape
tag_entry = base_entry     # Same shape
collection_entry = {**base_entry, "sequence_number": ...}
```

### 4.2 Enriched Master Indexes

#### Current Shape
```json
{"name": "beginner", "slug": "beginner", "paginated": false, "count": 6}
```

#### Proposed Shape (with level and tag distribution)

**Level Master Index** — add tag distribution:
```json
{
  "name": "beginner",
  "slug": "beginner",
  "paginated": true,
  "count": 22000,
  "pages": 44,
  "tags": {
    "life-and-death": 3200,
    "ladder": 1800,
    "net": 4500,
    "ko": 2100
  }
}
```

**Tag Master Index** — add level distribution:
```json
{
  "name": "ladder",
  "slug": "ladder",
  "paginated": true,
  "count": 21000,
  "pages": 42,
  "levels": {
    "novice": 1200,
    "beginner": 2800,
    "elementary": 3500,
    "intermediate": 4200,
    "upper-intermediate": 3800,
    "advanced": 2900,
    "low-dan": 1600,
    "high-dan": 800,
    "expert": 200
  }
}
```

**Collection Master Index** — add level and tag distributions:
```json
{
  "name": "cho-chikun-elementary",
  "slug": "cho-chikun-elementary",
  "paginated": false,
  "count": 180,
  "levels": {
    "beginner": 45,
    "elementary": 72,
    "intermediate": 63
  },
  "tags": {
    "life-and-death": 120,
    "ko": 35,
    "eye-shape": 25
  }
}
```

### 4.3 Master Index → SGF Data Flow (How It All Connects)

The master index does **not** contain SGF file paths. It is an **index of indexes** — it tells the frontend what entities exist, how many puzzles each has, and whether the entity is paginated. The actual puzzle file paths live inside the ViewEnvelope/PageDocument files.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MASTER INDEX → SGF FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STEP 1: Load Master Index (one per dimension)                             │
│  ─────────────────────────────────────────────                             │
│  Frontend fetches: views/by-tag/index.json                                 │
│                                                                             │
│  Response:                                                                  │
│  {                                                                          │
│    "version": "2.0",                                                        │
│    "tags": [                                                                │
│      { "name": "ladder", "slug": "ladder",                                  │
│        "paginated": true, "count": 21000, "pages": 42,                     │
│        "levels": {"beginner": 2800, "intermediate": 4200, ...},             │
│        "tags": {...} },                                                     │
│      { "name": "ko", "slug": "ko",                                          │
│        "paginated": false, "count": 30,                                    │
│        "levels": {"novice": 5, "beginner": 10, ...},                        │
│        "tags": {...} },                                                     │
│      ...                                                                    │
│    ]                                                                        │
│  }                                                                          │
│                                                                             │
│  ↓ paginated: false              ↓ paginated: true                         │
│                                                                             │
│  STEP 2a: Flat ViewEnvelope      STEP 2b: Directory Index                  │
│  ──────────────────────────      ────────────────────────                   │
│  Fetch: views/by-tag/ko.json     Fetch: views/by-tag/ladder/index.json     │
│                                                                             │
│  Response:                        Response:                                 │
│  {                                {                                         │
│    "version": "4.0",              "type": "tag",                            │
│    "type": "tag",                 "name": "ladder",                         │
│    "name": "ko",                  "total_count": 21000,                     │
│    "total": 30,                   "page_size": 500,                         │
│    "entries": [                   "pages": 42                               │
│      {"path": "sgf/...",        }                                          │
│       "level": "novice",                                                    │
│       "tags": ["ko",...]},          ↓                                      │
│      ...                                                                    │
│    ]                             STEP 2c: Load Page                         │
│  }                               ─────────────────                         │
│                                  Fetch: views/by-tag/ladder/page-001.json  │
│                                                                             │
│                                  Response:                                  │
│                                  {                                          │
│       ↓                            "type": "tag",                           │
│                                    "name": "ladder",                        │
│                                    "page": 1,                               │
│                                    "entries": [                              │
│                                      {"path": "sgf/beginner/batch-0001/    │
│                                        fc38f029.sgf",                       │
│                                       "level": "beginner",                  │
│                                       "tags": ["ladder","net"]},            │
│                                      ... (500 entries)                      │
│                                    ]                                        │
│                                  }                                          │
│                                                                             │
│       ↓                              ↓                                      │
│                                                                             │
│  STEP 3: Client-Side Filter (optional)                                     │
│  ─────────────────────────────────────                                      │
│  entries.filter(e => e.level === selectedLevel)                             │
│  entries.filter(e => e.tags.includes(selectedTag))                         │
│       ↓                                                                     │
│                                                                             │
│  STEP 4: Extract Puzzle ID + Fetch SGF                                     │
│  ─────────────────────────────────────                                      │
│  entry.path = "sgf/beginner/batch-0001/fc38f029.sgf"                       │
│  puzzle_id = extractId(entry.path) → "fc38f029"                            │
│  Fetch: /yengo-puzzle-collections/sgf/beginner/batch-0001/fc38f029.sgf     │
│       ↓                                                                     │
│                                                                             │
│  STEP 5: Parse SGF → Build Solution Tree → Render on Goban                │
│  ─────────────────────────────────────────────────────────                  │
│  parseSGF(text) → extractMetadata() → buildSolutionTree() → GobanContainer │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key insight**: The master index is a **lightweight catalog** (~5-90 KB) that provides distributions and pagination info. It NEVER contains individual puzzle paths. Those live in the ViewEnvelope/PageDocument files (Steps 2a-2c). The master index enables the frontend to render rich filter UIs ("2,800 beginner ladder puzzles") with a SINGLE HTTP request.

#### Why This Matters at Scale

Without enriched master indexes, to show the Technique browse page with "ladder — 21,000 puzzles (2,800 at your level)" the frontend would need to:
1. Load the master index (1 request) — gets total count
2. Load the first page of the tag index (1 request) — 500 entries, count `level === 'beginner'`
3. Load pages 2–42 (41 more requests!) — just to count

With enriched master indexes:
1. Load the master index (1 request) — gets total count AND `levels.beginner = 2800`
2. **Done.** Zero additional fetches for count display.

The same applies to collection browse: showing puzzle count by level/tag per collection card requires zero fetches beyond the master index.

**Daily Master Index** — add level and tag distributions:
```json
{
  "name": "2026-02-17",
  "slug": "2026-02-17-001",
  "count": 8,
  "levels": {
    "beginner": 2,
    "intermediate": 3,
    "advanced": 3
  },
  "tags": {
    "life-and-death": 4,
    "ko": 2,
    "ladder": 2
  }
}
```

#### Payload Cost

- **Level master** (9 entries): Adding ~28 tag counts per entry → 9 × 28 × ~20 B = **~5 KB** (negligible)
- **Tag master** (28 entries): Adding ~9 level counts per entry → 28 × 9 × ~20 B = **~5 KB** (negligible)
- **Collection master** (200 entries): Adding ~9 level + ~28 tag counts → 200 × 37 × ~20 B = **~148 KB** raw (acceptable)
- **Daily master** (365 entries): Adding ~9 level + ~10 tag counts → 365 × 19 × ~20 B = **~139 KB** raw (acceptable)

### 4.3 Enriched Collection Catalog (`config/collections.json`)

Add `levels` and `tags` arrays to each collection entry for faceted browsing on the collection listing page:

```json
{
  "slug": "cho-chikun-elementary",
  "name": "Cho Chikun Elementary L&D",
  "description": "...",
  "curator": "Cho Chikun",
  "type": "author",
  "ordering": "manual",
  "tier": "premier",
  "aliases": [...],
  "levels": ["beginner", "elementary", "intermediate"],
  "tags": ["life-and-death", "ko", "eye-shape"]
}
```

**Note**: This is static metadata in the config file. It would be populated from the published view data, either manually or via a build-time script that reads collection view indexes and updates the catalog.

Alternatively, the collection master index enrichment (4.2 above) may make this redundant — the UI can read distributions from the master index instead. The catalog would remain for static metadata (name, description, curator) while the master index provides dynamic puzzle statistics.

**Recommendation**: Use the enriched master index for dynamic counts/distribution. Only add `levels[]` and `tags[]` to `collections.json` if the UI needs to show them on the collection browse page **before** the master index loads (unlikely given the small payload).

### 4.4 JSON Schema Updates

Update `config/schemas/view-index.schema.json`:

```json
"LevelEntry": {
  "type": "object",
  "required": ["path", "level", "tags"],
  "properties": {
    "path": {"type": "string", "pattern": "^sgf/.+\\.sgf$"},
    "level": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": false
}
```

```json
"TagEntry": {
  "type": "object",
  "required": ["path", "level", "tags"],
  "properties": {
    "path": {"type": "string", "pattern": "^sgf/.+\\.sgf$"},
    "level": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": false
}
```

```json
"CollectionEntry": {
  "type": "object",
  "required": ["path", "level", "tags", "sequence_number"],
  "properties": {
    "path": {"type": "string", "pattern": "^sgf/.+\\.sgf$"},
    "level": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "sequence_number": {"type": "integer", "minimum": 1}
  },
  "additionalProperties": false
}
```

**Bump ViewEnvelope version**: `"3.0"` → `"4.0"` (DECIDED). Since this is a big-bang migration, all view files will be regenerated.

**Bump Master Index version**: `"1.0"` → `"2.0"` (DECIDED). All four master indexes (level, tag, collection, daily) use v2.0.

Enriched master index entries:

```json
"MasterIndexEntry": {
  "type": "object",
  "required": ["name", "slug", "paginated", "count"],
  "properties": {
    "name": {"type": "string"},
    "slug": {"type": "string"},
    "paginated": {"type": "boolean"},
    "count": {"type": "integer", "minimum": 0},
    "pages": {"type": "integer", "minimum": 1},
    "levels": {
      "type": "object",
      "additionalProperties": {"type": "integer", "minimum": 0}
    },
    "tags": {
      "type": "object",
      "additionalProperties": {"type": "integer", "minimum": 0}
    }
  },
  "additionalProperties": false
}
```

---

## 5. Frontend Changes Required

### 5.1 TypeScript Type Updates

**`frontend/src/types/indexes.ts`** — Unify entry types:

```typescript
// BEFORE: 3 separate entry shapes
interface LevelEntry { path: string; tags: readonly string[]; }
interface TagEntry   { path: string; level: string; }
interface CollectionEntry { path: string; level: string; sequence_number: number; }

// AFTER: Uniform base + collection extension
interface ViewEntry {
  readonly path: string;
  readonly level: string;
  readonly tags: readonly string[];
}

// LevelEntry and TagEntry are now ViewEntry (aliases for clarity)
type LevelEntry = ViewEntry;
type TagEntry = ViewEntry;

interface CollectionEntry extends ViewEntry {
  readonly sequence_number: number;
}
```

**Master index types** — add distribution fields:

```typescript
interface MasterIndexEntry {
  readonly name: string;
  readonly slug: string;
  readonly paginated: boolean;
  readonly count: number;
  readonly pages?: number;
  readonly levels?: Record<string, number>;  // NEW: level distribution
  readonly tags?: Record<string, number>;    // NEW: tag distribution
}
```

### 5.2 Frontend Pages to Add FilterBars

#### 5.2.1 Technique Solve Page (Tag → filter by Level)

When a user selects a technique (e.g., "ladder"), `CollectionViewPage` currently loads all entries. Add:

1. **Load tag master index** → read `levels` distribution for this tag
2. **Render FilterBar** with level options: `All (21k) | Novice (1.2k) | Beginner (2.8k) | ...`
3. **Filter loaded page entries** client-side: `entries.filter(e => e.level === selectedLevel)`
4. **Pass filtered entries** to `PuzzleSetPlayer`

#### 5.2.2 Training Solve Page (Level → filter by Tag)

When training at a level, `TrainingPage` loads all entries. Add:

1. **Load level master index** → read `tags` distribution for this level
2. **Render FilterBar** with tag options: `All (22k) | Life & Death (3.2k) | Ladder (1.8k) | ...`
3. **Filter loaded page entries** client-side: `entries.filter(e => e.tags.includes(selectedTag))`
4. **Pass filtered entries** to `PuzzleSetPlayer`

#### 5.2.3 Collection Solve Page (Collection → filter by Level and/or Tag)

When viewing a collection, `CollectionViewPage` loads all entries. Add:

1. **Load collection master index** → read `levels` and `tags` distributions
2. **Render two FilterBars**:
   - Level: `All | Beginner (45) | Elementary (72) | ...`
   - Tag: `All | Life & Death (120) | Ko (35) | ...`
3. **Filter loaded entries** client-side: compound filter with AND logic
4. **Pass filtered entries** to `PuzzleSetPlayer`

### 5.3 PuzzleSetPlayer / Loader Changes

Currently `PuzzleSetPlayer` receives a `PuzzleSetLoader` and plays through everything. Two approaches:

**Option A: Filter wrapper around loader** — create a `FilteredPuzzleSetLoader` that wraps any loader and applies client-side filters. Minimal change to PuzzleSetPlayer itself.

**Option B: Filter at the page level** — the page component loads entries, applies filter, then constructs a loader with only the filtered entries. PuzzleSetPlayer remains unchanged.

**Recommendation: Option B** — simpler, no new loader abstraction, filter logic stays in the page component where the FilterBar state lives.

### 5.4 Pagination-Aware Filtering

With paginated views (500 entries per page), filtering happens **per loaded page**. The UI flow:

1. Load page 1 of `views/by-tag/ladder/page-001.json` (500 entries, all have `{path, level, tags}`)
2. Apply filter: `entries.filter(e => e.level === 'beginner')` → yields, say, 67 entries
3. User solves those 67 puzzles
4. Load page 2, filter again → yields 71 entries
5. Continue until all pages exhausted

The **enriched master index** provides the total count upfront ("2,800 beginner ladder puzzles") so the UI can show progress against the filtered total without loading all pages.

### 5.5 Existing Code to Remove (Big-Bang Cleanup)

Since this is a big-bang migration, legacy code can be removed:

| File | Code to Remove | Reason |
|------|---------------|--------|
| `tag-loader.ts` | `TagIndex` type with custom fields | Replace with v4.0 ViewEnvelope types |
| `tag-loader.ts` | `filterPuzzlesByLevel()` | DECIDED: Remove. With uniform entries, filtering is `entries.filter(e => e.level === level)`. Legacy function returns `TagPuzzleEntry` (removed type). |
| `tag-loader.ts` | `filterPuzzlesByRank()` | DECIDED: Remove. Unused and rank-based filtering is subsumed by level filtering |
| `puzzleLoader.ts` | Legacy array/v2.2 format handling in `loadLevelIndex()` | Big-bang means all files are v4.0 |
| `collectionService.ts` | `detectCollectionFormat()` + legacy bare-slug fallback | All collections use v4.0 ViewEnvelope |
| `types/indexes.ts` | Duplicate types from Spec 131 contract | Consolidate to single set of types |
| `types/manifest.ts` | `ViewIndex`, `SkillLevelIndex`, `TagViewIndex` | Never used in v3.0+ world |

---

## 6. Backend Changes Required

### 6.1 `publish.py` — Uniform Entry Construction

**File**: `backend/puzzle_manager/stages/publish.py` (~lines 237-270)

```python
# BEFORE:
level_entry = {"path": rel_path, "tags": game.yengo_props.tags}
tag_entry = {"path": rel_path, "level": level_name}
collection_entry = {"path": rel_path, "level": level_name, "sequence_number": ...}

# AFTER:
base_entry = {"path": rel_path, "level": level_name, "tags": sorted(game.yengo_props.tags)}
level_entry = base_entry
tag_entry = base_entry
collection_entry = {**base_entry, "sequence_number": ...}
```

### 6.2 `pagination_writer.py` — Enriched Master Indexes

**File**: `backend/puzzle_manager/core/pagination_writer.py` (~lines 800-900)

The `_generate_level_master_index()`, `_generate_tag_master_index()`, and `_generate_collection_master_index()` methods need to:

1. Load all entries for each entity (or accumulate counts during append operations)
2. Compute level/tag distribution counts
3. Include `levels` and `tags` dicts in each master index entry

**Implementation approach**: During `append_*_puzzles()`, maintain running distribution counters in `LevelPaginationState`. This avoids re-reading all pages during master index generation.

### 6.3 `pagination_models.py` — Extended State

Add distribution tracking to `LevelPaginationState`:

```python
class LevelPaginationState(BaseModel):
    total: int = 0
    paginated: bool = False
    pages: int = 0
    last_page_count: int = 0
    # NEW: Distribution counters for enriched master indexes
    level_distribution: dict[str, int] = {}   # For tag/collection master indexes
    tag_distribution: dict[str, int] = {}     # For level/collection master indexes
```

### 6.4 JSON Schema Update

**File**: `config/schemas/view-index.schema.json`

- Update `LevelEntry`, `TagEntry`, `CollectionEntry` to all require `path`, `level`, `tags`
- Update `CollectionEntry` to also require `sequence_number`
- Update `MasterIndexEntry` to allow optional `levels` and `tags` distribution objects
- Consider bumping ViewEnvelope version to `"4.0"`

### 6.5 `_update_collection_indexes()` in `publish.py`

The flat-mode collection writer (used when pagination disabled) also needs `tags`:

```python
# In _update_collection_indexes():
collection_entry = {
    "path": rel_path,
    "level": level_name,
    "tags": sorted(game.yengo_props.tags),  # NEW
    "sequence_number": collection_sequence[collection_slug],
}
```

### 6.6 Maintenance/Views Regeneration

**File**: `backend/puzzle_manager/maintenance/views.py`

The view regeneration utility must also produce uniform entries. This is used during repair/rebuild operations.

### 6.7 Test Updates

All tests asserting entry shapes need updating:

| Test File | What to Update |
|-----------|---------------|
| `tests/unit/test_pagination_contracts.py` | Entry shape assertions: add `level` to LevelEntry, `tags` to TagEntry/CollectionEntry |
| `tests/unit/test_pagination_writer.py` | Entry construction in test helpers |
| `tests/integration/test_publish_pagination.py` | Master index shape assertions |
| `tests/unit/test_pagination_rollback.py` | Entry shapes in rollback tests |
| `tests/stages/test_publish_trace.py` | Any entry shape checks |
| `tests/unit/test_collections.py` | Collection entry assertions |
| `tests/integration/test_publish_posix.py` | Entry shape checks |

---

## 7. Implementation Plan (Ordered)

### Phase 1: Backend — Uniform Schema + Enriched Master Indexes

| Step | Task | Files | Tests |
|------|------|-------|-------|
| 1.1 | Update JSON Schema (`view-index.schema.json`) | `config/schemas/view-index.schema.json` | Schema validation tests |
| 1.2 | Update `LevelPaginationState` with distribution counters | `pagination_models.py` | `test_pagination_state.py` |
| 1.3 | Update `publish.py` entry construction to uniform `{path, level, tags}` | `stages/publish.py` | `test_publish_*.py` |
| 1.4 | Update `PaginationWriter._write_flat_file()` / `_write_page()` — no entry changes needed (pass-through) | `pagination_writer.py` | — |
| 1.5 | Update `PaginationWriter.append_*()` to track distributions in state | `pagination_writer.py` | `test_pagination_writer.py` |
| 1.6 | Update `PaginationWriter.generate_master_indexes()` to include distributions | `pagination_writer.py` | `test_pagination_contracts.py` |
| 1.7 | Update `_update_collection_indexes()` (flat-mode) with tags | `stages/publish.py` | `test_collections.py` |
| 1.8 | Update `maintenance/views.py` regeneration | `maintenance/views.py` | Regeneration tests |
| 1.9 | Update rollback code — entry shapes + distribution recompute | `pagination_writer.py` rollback methods | `test_pagination_rollback.py` |
| 1.10 | Add daily entry uniform schema (`{path, level, tags}`) to daily generation | `stages/daily.py` or daily pipeline module | `test_daily_*.py` |
| 1.11 | Generate daily master index at `views/daily/index.json` with distributions | `pagination_writer.py` or daily pipeline | `test_daily_master_index.py` |
| 1.12 | Update all test fixtures and assertions | All test files from §6.7 | Run full test suite |

### Phase 2: Frontend — Type Updates + Legacy Removal

| Step | Task | Files |
|------|------|-------|
| 2.1 | Update TypeScript types in `indexes.ts` — unified `ViewEntry` | `types/indexes.ts` |
| 2.2 | Update `MasterIndexEntry` with distribution fields | `types/indexes.ts` |
| 2.3 | Remove legacy format handling in `puzzleLoader.ts` | `services/puzzleLoader.ts` |
| 2.4 | Remove legacy types in `types/manifest.ts` | `types/manifest.ts` |
| 2.5 | Simplify `tag-loader.ts` — remove custom types, use ViewEnvelope | `lib/puzzle/tag-loader.ts` |
| 2.6 | Remove `filterPuzzlesByLevel()` and `filterPuzzlesByRank()` | `lib/puzzle/tag-loader.ts` |
| 2.7 | Simplify `collectionService.ts` — remove legacy format detection | `services/collectionService.ts` |
| 2.8 | Migrate `loadLevelIndex()` and `loadTagIndex()` to pagination-aware loading | `services/puzzleLoader.ts`, `lib/puzzle/tag-loader.ts` |
| 2.9 | Update spec 131 contract types | `specs/131-frontend-view-schema/contracts/view-types.ts` |
| 2.10 | Run `tsc --noEmit` to verify no type errors | — |

### Phase 3: Frontend — Filter Components + Integration

| Step | Task | Files |
|------|------|-------|
| 3.1 | Create `FilterDropdown` component (single-select dropdown for 10+ options) | `components/shared/FilterDropdown.tsx` |
| 3.2 | Extend `FilterBar` with count badge support | `components/shared/FilterBar.tsx` |
| 3.3 | Create `useFilterState()` hook for coordinated multi-dimension state | `hooks/useFilterState.ts` |
| 3.4 | Add tag FilterBar/Dropdown to training solve page | `TrainingPage.tsx` |
| 3.5 | Add level FilterBar to technique solve page | Technique solve page wrapper |
| 3.6 | Add level + tag filters to collection solve page | `CollectionViewPage.tsx` |
| 3.7 | Update page components to filter entries and pass filtered set to PuzzleSetPlayer | All three pages |
| 3.8 | Show distribution counts in filter labels (from master index) | All pages |
| 3.9 | Update technique browse page to show "X at your level" from master index | `TechniqueFocusPage.tsx` |
| 3.10 | Update training browse page to show tag breakdown from master index | `TrainingSelectionPage.tsx` |

### Phase 4: Rush Play — Level + Tag Selection

| Step | Task | Files |
|------|------|-------|
| 4.1 | Add level selection to Rush setup screen | `RushBrowsePage.tsx` or `PuzzleRushPage.tsx` |
| 4.2 | Add tag selection to Rush setup screen | Same |
| 4.3 | Show "~N puzzles available" from master index distributions | Same |
| 4.4 | Update `getNextPuzzle()` to accept level + tag parameters | `app.tsx` |
| 4.5 | Fix hardcoded `currentLevelRef = 'beginner'` — use selected level | `PuzzleRushPage.tsx` |
| 4.6 | Migrate Rush's `loadLevelIndex()` call to pagination-aware loading | `app.tsx` |
| 4.7 | Handle filtered set exhaustion (warn if < 20 puzzles available) | `PuzzleRushPage.tsx` |

### Phase 5: Republish + Validate

| Step | Task |
|------|------|
| 5.1 | Set `pagination_threshold: 0` (always-paginate) — PENDING DECISION |
| 5.2 | Re-run the full publish pipeline to regenerate all views with new schema |
| 5.3 | Validate all generated JSON against updated schema |
| 5.4 | Run frontend against regenerated data |
| 5.5 | Verify all filter flows work (Training, Technique, Collection, Rush) |
| 5.6 | Verify pagination loading works across all loaders |

---

## 8. Decisions (All Resolved)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Entry schema | Uniform `{path, level, tags}` everywhere | Simplicity > byte savings; client-side filtering needs both dimensions |
| D2 | Migration strategy | Big-bang, no backward compatibility | Per user directive; eliminates legacy code |
| D3 | Filtering approach | Client-side `Array.filter()` per loaded page | <1ms for 500 entries; avoids pre-computed cross-indexes |
| D4 | Master index enrichment | Include level/tag distribution counts in ALL master indexes | Avoids loading all pages just to count; enables rich UI with single fetch |
| D5 | Collection entries | Add `tags` field | Mandatory requirement |
| D6 | Collection catalog enrichment | Defer — master index provides same data | `config/collections.json` stays static metadata; counts come from master index |
| Q1 | ViewEnvelope version | **Bump to `"4.0"`** | Cheap documentation. Reading a JSON file 6 months later, `"4.0"` immediately tells you it's the uniform-schema generation |
| Q2 | Master index version | **Bump to `"2.0"`** | Schema is changing (adding distribution objects). Version documents this. |
| Q3 | Store distributions in `.pagination-state.json`? | **Yes** | At 200k puzzles, recomputing means reading ~2,000 page files. Running counters make `generate_master_indexes()` O(1) instead of O(pages). State file grows by ~2-5 KB — trivial. |
| Q4 | Filter persistence in localStorage? | **None for now** | YAGNI. FilterBar defaults to "All". Add persistence later if users request it. Frontend **must support the capability** of filtering in all dimensions — that's the feature, not persistence. |
| Q5 | Keep `filterPuzzlesByLevel()`? | **Remove** | With uniform entries, filtering is a one-liner: `entries.filter(e => e.level === level)`. The existing function also returns `TagPuzzleEntry` (a legacy type being removed). Rebuild fresh filtering utilities as needed. |
| D7 | Schema name | **Keep `ViewEnvelope`** | No verb-based alternative (PuzzleLens, ViewCast, IndexSlice, PuzzleCut) was more descriptive than the established name. |
| D8 | Daily dimension | **Include daily in all planning** | Daily master index, daily entries with uniform schema, daily considered across all filter infrastructure |
| D9 | Master indexes for ALL dimensions | **Level + Tag + Collection + Daily** — all four get enriched master indexes | Uniform treatment across all dimensions |

---

## 9. Second-Order Impacts / Ripple Effects

### 9.1 Rollback System — Distribution Counter Staleness

The rollback code in `pagination_writer.py` (`remove_puzzles_from_level()`, `remove_puzzles_from_tag()`, `remove_puzzles_from_collection()`) rebuilds indexes after removing puzzles.

**Ripple**: When puzzles are rolled back, the distributions stored in `PaginationState` must be decremented. Currently rollback removes entries and rebuilds — it doesn't track distributions.

**Fix**: The `_rebuild_index_structure()` method must recompute distributions from the remaining entries after a rollback. This is acceptable because rollback already loads all entries to filter them — computing distributions is a trivial O(n) pass during the same loop. The publish log already stores `level` and `tags` per entry (Spec 107/138), which can also be used for decrementing.

**Risk level**: Medium. If we don't handle this, the master index will show wrong counts until the next full publish.

### 9.2 Inventory Manager / Reconciliation

`_update_inventory()` uses `puzzles_by_level` and `puzzles_by_tag` dicts. These dicts' value types change (entries now have `{path, level, tags}` instead of `{path, tags}` or `{path, level}`). The inventory manager doesn't look inside individual entries — it only counts them. **Low impact**, but must verify reconciliation code doesn't destructure entry fields.

### 9.3 Daily Challenge Generation

Daily challenge JSON (`views/daily/`) currently uses `{path, level}` entries (v2.2). **Decision: Add `tags` to daily entries too** — uniform schema applies to all view types including daily. Daily entries become `{path, level, tags}`.

Daily challenges are small (5-10 puzzles). Filtering them by tag within a single day is unlikely, but the data should be there for consistency and for the daily master index to compute tag distributions across dates.

**Bump daily schema version**: `"2.2"` → `"4.0"` to align with the ViewEnvelope version.

### 9.4 Daily Master Index — New Artifact

Currently no daily master index exists. We need one at `views/daily/index.json`:

```json
{
  "version": "2.0",
  "generated_at": "2026-02-17T10:00:00Z",
  "daily": [
    {
      "name": "2026-02-17",
      "slug": "2026-02-17-001",
      "count": 8,
      "levels": {"beginner": 2, "intermediate": 3, "advanced": 3},
      "tags": {"life-and-death": 4, "ko": 2, "ladder": 2}
    }
  ]
}
```

This enables the frontend to show daily challenge previews (e.g., "Today: 8 puzzles — 3 intermediate, 3 advanced") and lets the daily browse page show historical challenges with difficulty breakdowns.

**Backend impact**: The daily generation pipeline (`python -m backend.puzzle_manager daily`) must also produce/update this master index.

### 9.5 `loadFilteredPuzzles()` at Scale

`collectionService.loadFilteredPuzzles(level, tags)` loads **all** level indexes to find matching puzzles. At 200k puzzles across 9 levels, that means loading up to 9 × 44 pages = 396 HTTP requests to build a practice set.

**Fix needed**: Use the enriched master index to identify which levels have the requested tags (count > 0), then only load those levels. Within each level, stop loading pages once enough puzzles are collected (early termination).

### 9.6 `PuzzleSetPlayer` — Filter Change UX

When users change the filter mid-session, what happens?

**Decision**: Reset to the beginning of the filtered set. A filter change means "I want a different set of puzzles." This doesn't lose progress — completion state is saved by puzzle ID separately.

### 9.7 Progress Tracking Per Filter

Training progress is saved per level: `localStorage['yen-go-training-progress']` → `{beginner: {completed: [id1, id2], accuracy: 0.85}}`. Technique progress is saved per tag.

**Ripple**: If a user trains "beginner + ladder" and completes 10 puzzles, then switches to "beginner + all", their completed set should still appear as done. This works naturally because progress is tracked by puzzle ID, not by filter combination. **No state change needed.**

**But**: The progress bar must count completed puzzles **within the filtered set**: `filteredEntries.filter(e => completedIds.has(extractId(e.path))).length`. The total comes from the enriched master index distribution. **Needs implementation in page components.**

### 9.8 Tag-Loader Types Fully Replaced

`tag-loader.ts` defines its own types (`TagListEntry`, `TagIndex`, `TagPuzzleEntry`) completely separate from `indexes.ts`. With the big-bang migration, these get removed and replaced with unified `ViewEntry`/`ViewEnvelope` types.

**Ripple**: Every file that imports from `tag-loader.ts` must be updated:
- `TechniqueFocusPage.tsx`
- `TechniqueList.tsx`
- `TechniqueCard.tsx`
- `tests/unit/tag-index.test.ts`

### 9.9 Collection Browse Page — Better Cards for Free

With enriched master indexes, each collection card can display "180 puzzles — Beginner to Intermediate — Life & Death, Ko" without loading the collection's full view. **Zero extra HTTP requests.** Requires updating `PuzzleCollectionCard` components to accept and display distribution data from the master index.

### 9.10 GitHub Pages Repository Size

At 200k puzzles with uniform entries (~180 B/entry), total raw JSON across all views:
- by-level: 200k × 180 B = **~36 MB**
- by-tag: 200k × 2.5 tags/puzzle × 180 B = **~90 MB** (same puzzle in multiple tag indexes)
- by-collection: ~400k collection assignments × 210 B = **~84 MB**
- by-daily: ~3,650 daily entries × 180 B = **~0.7 MB** (negligible)
- **Total**: ~211 MB of JSON view files in the git repo

GitHub Pages has a **1 GB repository size soft limit** and a **100 MB file size limit**. With pagination at 500 entries (88 KB/page), no single file exceeds the limit. Total repo (~211 MB views + ~200k SGFs) approaches but doesn't hit 1 GB. **Worth monitoring** but not a blocker. Git's internal zlib compression reduces on-disk clone size further.

### 9.11 Gzip Clarification — Not Our Concern

**Gzip is NOT something we control.** The flow:
1. Our pipeline writes **raw uncompressed JSON** → git push → GitHub Pages stores raw JSON
2. Browser requests file → GitHub Pages CDN automatically applies `Content-Encoding: gzip` → browser decompresses transparently

We do **nothing** about gzip. It's a GitHub Pages CDN feature that compresses during HTTP transport. What we control and care about:
- **Raw JSON size** → git repo size + browser memory + JSON.parse() time
- **Page file size** → pagination threshold of 500 entries keeps files at ~88 KB raw

### 9.12 Spec Version Alignment

The codebase currently has a confusing mix: ViewEnvelope v3.0, Daily v2.2, Master Indexes v1.0, Pagination State v1.0, Collection Catalog v3.0.

**Decision**: Only bump versions for schemas that actually change in this migration. Don't create scope creep aligning versions that aren't touched.
- ViewEnvelope: `"3.0"` → `"4.0"` ✓
- Master Index: `"1.0"` → `"2.0"` ✓
- Daily schema: `"2.2"` → `"4.0"` (aligns with ViewEnvelope) ✓
- Pagination State: `"1.0"` → keep (internal, not user-facing)
- Collection Catalog: `"3.0"` → keep (no schema change)

### 9.13 Puzzle Rush — Deep Analysis

#### Current State

Puzzle Rush is an **independent game mode** that does NOT use `PuzzleSetPlayer`. It has its own:
- State machine in `PuzzleRushPage.tsx` (setup → countdown → playing → finished)
- Session management via `useRushSession.ts` (timer, lives, score, streak)
- Puzzle renderer `RushPuzzleRenderer` → `InlinePuzzleSolver` in `app.tsx`
- HUD overlay via `RushOverlay.tsx`

**Data flow**: `getNextPuzzle(level)` → `loadLevelIndex(level)` → picks random entry from `ViewEnvelope<LevelEntry>` → `fetchSGFContent(entry.path)` → parse SGF → render.

**Critical finding**: The level is **hardcoded to `'beginner'`** via `currentLevelRef = useRef<SkillLevel>('beginner')` — never updated. Users can only choose duration (3/5/10 min). There is **no level selection, no tag filtering, no difficulty progression**.

#### Entry Type Consumed

Rush uses `LevelEntry` (`{path, tags}`). With uniform schema, entries become `{path, level, tags}` — the extra `level` field is harmless (Rush already knows the level since it requested it). **No breaking change.**

#### Rush Filtering Opportunity

With enriched master indexes and uniform entries, Rush can unlock a powerful UX:

> *"I want to play intermediate ladder problems for 5 minutes"*

**Setup screen additions** (in `PuzzleRushPage` or `RushBrowsePage`):

| Filter | Source | Default |
|--------|--------|---------|
| Duration | Existing: 3/5/10 min | 3 min |
| Level | Level master index → level names + counts | All |
| Technique/Tag | Tag master index → tag names + counts | All |

**Implementation approach**:
1. `RushBrowsePage` loads level + tag master indexes
2. User selects duration + optional level + optional tag
3. `getNextPuzzle()` changes from single-level loader to:
   - If level selected + no tag: load from `views/by-level/{level}`, filter by tag client-side
   - If tag selected + no level: load from `views/by-tag/{tag}`, random entry
   - If both selected: load from `views/by-level/{level}`, filter `entries.filter(e => e.tags.includes(tag))`
   - If neither: load from random level (use master index for weighted selection)
4. Filtered entries are randomly sampled (existing `usedPuzzleIds` deduplication still works)

**No PuzzleSetPlayer changes needed** — Rush has its own orchestration.

#### Rush-Specific Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Filtered set exhaustion (e.g., only 15 expert ko puzzles) | Medium | Show "X puzzles available" on setup screen using master index distributions; warn if < 20 |
| `loadLevelIndex()` hardcodes flat URL | High | Must migrate to pagination-aware loading (same fix needed elsewhere) |
| Level stuck at 'beginner' | Low (existing bug) | Fix as part of this feature — add level selection |

---

## 10. Architectural Future-Proofing

### 10.1 Should We Always Paginate? (Eliminate Flat Mode)

**Current situation**: Two code paths exist — flat `{name}.json` (≤500 entries) and paginated `{name}/index.json` + `{name}/page-{NNN}.json` (>500). At 200k puzzles, almost every entity will be paginated. The flat path becomes dead weight.

**Analysis**:

| Factor | Always Paginate | Keep Dual Mode |
|--------|----------------|----------------|
| Code paths | **1** (simpler) | 2 (flat + paginated) |
| Backend complexity | Simpler — no `should_paginate()`, no `_transition_to_paginated()` | Current |
| Frontend complexity | Simpler — always `index.json` → `page-001.json` | Must detect + handle both |
| Network requests for small entities | **2** (index + page) instead of 1 (flat) | 1 for small, 2+ for paginated |
| New entity overhead | Consistent — always directory, always works | Must handle flat→paginated transition mid-growth |
| Mental model | Uniform — every entity is a directory | "It depends on count" |

**Breaking paths if always-paginated**:
- `loadLevelIndex()` in `puzzleLoader.ts` — hardcodes `views/by-level/${level}.json` (would 404)
- `loadTagIndex()` in `tag-loader.ts` — hardcodes `views/by-tag/${tag}.json` (would 404)
- These already need migration to use the generic `createPaginationLoader()` path

**Recommendation**: **Yes, always paginate.** The extra HTTP request for small entities (2 instead of 1) is negligible. The simplification value compounds:
- Eliminates `should_paginate()`, `_transition_to_paginated()`, `_append_to_flat()` backend code
- Frontend uses ONE loading path (`detectIndexType()` already tries paginated first)
- New tags/collections/levels automatically work — no flat→paginated transition ever needed
- Change: Set `pagination_threshold: 0` in `PaginationConfig` (or add `always_paginate: true`)

**DECISION NEEDED**: This is a structural change. User must confirm.

### 10.2 New Tags (Fully Config-Driven — No Concern)

Adding a new tag to `config/tags.json`:
1. Pipeline auto-discovers → creates `views/by-tag/{new-tag}/index.json` + pages
2. Master index auto-includes → `{name, slug, count, levels, tags}`
3. Frontend `TechniqueFocusPage` loads from `getTagsConfig()` at runtime → **auto-adapts**
4. FilterBar pills render the new tag → **no code change**

**One exception**: `TAG_DISPLAY_INFO` in `collectionService.ts` is a hardcoded map. New tags won't appear in collection practice set creation unless this map is updated. **Should be refactored to derive from tags.json** (separate cleanup task).

### 10.3 New Collections (Fully Config-Driven — No Concern)

Adding a new collection to `config/collections.json`:
1. Pipeline auto-discovers → creates `views/by-collection/{slug}/` with pages
2. Collection master index auto-includes with distributions
3. Frontend `CollectionsPage` loads from config at runtime → **auto-adapts**
4. **No code change required**

### 10.4 Granular Levels (More Than 9)

**Current state**: 9 levels frozen in `config/puzzle-levels.json` (`"frozen": true`). Frontend types are **code-generated** from this file (`npm run generate-types` → `generated-types.ts` → `LevelSlug` union).

**If levels become more granular** (e.g., splitting "beginner" into sub-levels):

| Impact Area | Severity | Details |
|-------------|----------|---------|
| `config/puzzle-levels.json` | Low | Add entries, regenerate types |
| Pipeline directory structure | Low | New `sgf/{sub-level}/` directories auto-created |
| Backend pipeline | Low | Config-driven, auto-adapts |
| Frontend `FilterBar` UX | **High** | Pill buttons break at 15+ options — needs dropdown component |
| `CATEGORY_LEVELS` maps in `RandomPage`, `TrainingSelectionPage` | **Medium** | Hardcoded groupings — must update manually |
| All existing SGF files | **High** | `YG[beginner]` baked in — can't auto-split without re-running enrichment |

**Better alternative**: Use existing `YX` complexity metrics (`d:depth, r:responses, s:solution-size`) for **intra-level difficulty sorting** instead of creating sub-levels. The data is already in every SGF file.

**Bake-in for this migration**: Design the `FilterBar`/`FilterDropdown` component to handle **arbitrary numbers of options**. Use a dropdown/combobox when count > threshold (e.g., 8). This future-proofs against level proliferation AND large tag counts.

### 10.5 Frontend Components Needed

| Component | Exists? | Purpose | Design |
|-----------|---------|---------|--------|
| `FilterBar` | ✅ Yes | Single-select pill buttons | Works for ≤8 options (levels, categories) |
| `FilterDropdown` | ❌ No | Single-select dropdown/combobox | Needed for 10+ options (tags, collections) |
| `MultiSelectFilter` | ❌ No | Multi-select checkbox group | Needed for "tag1 AND tag2" compound filters |
| `useFilterState()` hook | ❌ No | Coordinated multi-dimension state | Manages `{level, tag, sort}` as a unit |
| `FilterContext` | ❌ No | Context for filter state sharing | Avoids prop-drilling across page → filter → player |
| Count badges in filters | ❌ No | "Beginner (2,800)" in filter option | Shows result counts from master index distributions |
| "Clear All" action | ❌ No | Reset all filters to default | Button or link in filter bar |

### 10.6 Bake-In Summary (What to Build Now vs. Later)

| Bake In NOW | Reason |
|-------------|--------|
| Uniform `{path, level, tags}` everywhere | Foundation for ALL filtering |
| Enriched master indexes with distributions | Enables count badges, Rush setup, browse previews |
| Always-paginated mode | Eliminates dual code paths before scale hits |
| `FilterDropdown` component (single-select) | Needed immediately for tag filter in Training/Collections |
| `useFilterState()` hook | Prevents ad-hoc state management across 5+ pages |
| Count badges in filter options | Key UX differentiator — "2,800" tells users the filter is useful |

| Build LATER | Reason |
|-------------|--------|
| `MultiSelectFilter` (tag1 AND tag2) | YAGNI — single-select covers 95% of use cases |
| Filter URL persistence | YAGNI — decided "None for now" |
| Level sub-splitting | Use `YX` complexity metrics first |
| Rush difficulty progression | Separate feature — Rush filtering is enough for now |

---

## 11. Frontend User Flow Confirmation

The following user flows MUST be enabled by this change. Each row describes a page, the primary dimension (how the user arrived), and the secondary filter(s) they can apply.

### 11.1 Entry Point → Filter Matrix

| Page | Primary Dimension | Filter 1 | Filter 2 | Data Source for Filters |
|------|-------------------|----------|----------|-------------------------|
| **Training** (solve at a level) | Level (e.g., Beginner) | Tag dropdown: "All / Life & Death / Ko / Ladder / ..." | — | Level master index → `tags` distribution for this level |
| **Technique** (solve a technique) | Tag (e.g., Ladder) | Level pills: "All / Novice / Beginner / ..." | — | Tag master index → `levels` distribution for this tag |
| **Collection** (solve a collection) | Collection (e.g., Cho Chikun Elementary) | Level pills: "All / Beginner / Elementary / ..." | Tag dropdown: "All / Life & Death / Ko / ..." | Collection master index → `levels` AND `tags` distributions |
| **Rush** (timed challenge) | Duration (3/5/10 min) | Level pills: "All / Beginner / Intermediate / ..." | Tag dropdown: "All / Ladder / Ko / ..." | Level + Tag master indexes |
| **Daily** (today's challenge) | Date (today) | _(none — curated fixed set)_ | _(none)_ | N/A |

### 11.2 Detailed User Flows

**Flow A: Training → Filter by Tag**
1. User clicks Training → selects "Beginner" → lands on `TrainingPage`
2. Page loads level master index → reads `tags` distribution for "beginner": `{"life-and-death": 320, "ko": 180, "ladder": 450, ...}`
3. FilterBar/Dropdown shows: `All (6,000) | Life & Death (320) | Ko (180) | Ladder (450) | ...`
4. User selects "Ladder" → page filters loaded entries: `entries.filter(e => e.tags.includes('ladder'))`
5. PuzzleSetPlayer receives filtered entries → user solves ladder-only beginner puzzles

**Flow B: Technique → Filter by Level**
1. User clicks Techniques → selects "Ladder" → lands on technique solve page
2. Page loads tag master index → reads `levels` distribution for "ladder": `{"beginner": 2800, "intermediate": 4200, ...}`
3. FilterBar shows: `All (21,000) | Beginner (2,800) | Intermediate (4,200) | ...`
4. User selects "Intermediate" → page filters: `entries.filter(e => e.level === 'intermediate')`
5. PuzzleSetPlayer receives filtered entries

**Flow C: Collection → Filter by Level AND Tag**
1. User clicks Collections → selects "Cho Chikun Elementary" → lands on `CollectionViewPage`
2. Page loads collection master index → reads BOTH `levels` and `tags` distributions
3. Two filter controls:
   - Level pills: `All (180) | Beginner (45) | Elementary (72) | Intermediate (63)`
   - Tag dropdown: `All (180) | Life & Death (120) | Ko (35) | Eye Shape (25)`
4. User selects "Elementary" + "Life & Death" → compound filter: `entries.filter(e => e.level === 'elementary' && e.tags.includes('life-and-death'))`
5. Count comes from **intersection** — not simply `Math.min(72, 120)`. Actual count requires client-side counting of filtered entries per loaded page. The master index gives an upper bound only.

**Flow D: Rush → Level + Tag Selection**
1. User clicks Rush → lands on `RushBrowsePage`
2. Setup screen shows:
   - Duration: `3 min | 5 min | 10 min`
   - Level (optional): `All | Beginner | Intermediate | ...` (from level master index)
   - Technique (optional): `All | Ladder | Ko | ...` (from tag master index)
3. Below filters: "~2,800 puzzles available" (from master index intersection estimate)
4. User selects 5 min + Intermediate + Ladder → starts Rush
5. `getNextPuzzle()` loads from `views/by-level/intermediate/page-{NNN}.json`, filters by `tags.includes('ladder')`, picks random entry

### 11.3 What This Change Does NOT Enable (Explicit Exclusions)

- ❌ Multi-tag AND filtering ("ladder AND ko") — YAGNI, build later if needed
- ❌ Cross-collection search ("find all puzzles tagged 'ko' across all collections") — use Technique page instead
- ❌ Daily challenge filtering — curated fixed sets, filtering doesn't apply
- ❌ Level range selection ("15k-10k") — use single level selection; ranges add complexity for minimal gain
- ❌ Filter persistence in URL or localStorage — decided: YAGNI for now

---

## 12. publish.py — Central Role

`publish.py` is the **single source of truth** for how view index entries are constructed. Every entry shape, every field, every schema decision flows through this file. The data flow:

```
publish.py constructs entries:
  base_entry = {"path": rel_path, "level": level_name, "tags": sorted(tags)}
       ↓
  Passes entries to PaginationWriter:
    append_level_puzzles(level, [base_entry, ...])
    append_tag_puzzles(tag, [base_entry, ...])
    append_collection_puzzles(collection, [{**base_entry, "sequence_number": N}, ...])
       ↓
  PaginationWriter writes to disk:
    views/by-level/{level}/page-{NNN}.json
    views/by-tag/{tag}/page-{NNN}.json
    views/by-collection/{slug}/page-{NNN}.json
       ↓
  PaginationWriter generates master indexes:
    views/by-level/index.json   (with level distributions from running counters)
    views/by-tag/index.json     (with tag distributions from running counters)
    views/by-collection/index.json (with level+tag distributions)
```

This means: **get publish.py right, and everything downstream (PaginationWriter, master indexes, frontend) consumes the correct shape automatically.** The enrichment happens in publish.py; PaginationWriter is a pass-through writer that also maintains distribution counters.

---

## 13. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rollback distribution staleness | Medium | Recompute distributions during `_rebuild_index_structure()` — entries are already loaded |
| `loadFilteredPuzzles()` makes 396 requests at scale | High | Use enriched master index for level/tag discovery; early termination once enough puzzles collected |
| Filter change mid-session in PuzzleSetPlayer | Medium | Reset to beginning of filtered set; completion state saved by puzzle ID (no loss) |
| GitHub Pages repo size at 211 MB | Low | Well under 1 GB limit; monitor growth; pagination keeps individual files small |
| Daily pipeline must update master index | Medium | Add master index update step to daily generation; same pattern as level/tag/collection |
| Tag-loader type removal breaks imports | Low | Big-bang migration — update all importers in Phase 2 |
| Progress bar wrong after filter change | Medium | Recompute progress against filtered set using master index distributions |
| Test suite — entry shape changes touch many files | Low | Uniform schema actually reduces test matrix (one shape to validate); big-bang means all tests update together |
| Rush `loadLevelIndex()` hardcodes flat URL | High | Migrate to pagination-aware loading (same fix as other loaders) |
| Rush filtered set exhaustion (few puzzles match) | Medium | Show available count on setup screen; warn if < 20 |
| FilterBar pill UX with 28+ tags | Medium | Use `FilterDropdown` component for high-count dimensions |
| Compound filter count accuracy | Low | Master index gives upper bound; exact count computed client-side per page |

---

## 14. Files Inventory (All Changes)

### Backend
| File | Change Type |
|------|-------------|
| `config/schemas/view-index.schema.json` | Schema migration |
| `backend/puzzle_manager/stages/publish.py` | Entry construction |
| `backend/puzzle_manager/core/pagination_writer.py` | Master index generation + distribution tracking |
| `backend/puzzle_manager/core/pagination_models.py` | State model extension |
| `backend/puzzle_manager/maintenance/views.py` | View regeneration |
| `backend/puzzle_manager/stages/daily.py` (or daily pipeline module) | Daily entry uniform schema + daily master index generation |
| `backend/puzzle_manager/tests/unit/test_pagination_contracts.py` | Test updates |
| `backend/puzzle_manager/tests/unit/test_pagination_writer.py` | Test updates |
| `backend/puzzle_manager/tests/unit/test_pagination_state.py` | Test updates |
| `backend/puzzle_manager/tests/unit/test_pagination_rollback.py` | Test updates |
| `backend/puzzle_manager/tests/unit/test_collections.py` | Test updates |
| `backend/puzzle_manager/tests/integration/test_publish_pagination.py` | Test updates |
| `backend/puzzle_manager/tests/integration/test_publish_posix.py` | Test updates |
| `backend/puzzle_manager/tests/stages/test_publish_trace.py` | Test updates |

### Frontend
| File | Change Type |
|------|-------------|
| `frontend/src/types/indexes.ts` | Type unification |
| `frontend/src/types/manifest.ts` | Legacy removal |
| `frontend/src/lib/puzzle/tag-loader.ts` | Simplification |
| `frontend/src/lib/puzzle/pagination.ts` | Minor updates |
| `frontend/src/services/puzzleLoader.ts` | Legacy removal |
| `frontend/src/services/puzzleLoaders.ts` | Entry type updates |
| `frontend/src/services/collectionService.ts` | Legacy removal |
| `frontend/src/pages/CollectionViewPage.tsx` | FilterBar integration |
| `frontend/src/pages/TrainingPage.tsx` | FilterBar integration |
| `frontend/src/pages/TechniqueFocusPage.tsx` | Master index display |
| `frontend/src/pages/TrainingSelectionPage.tsx` | Master index display |
| `frontend/src/components/PuzzleSetPlayer/index.tsx` | Filtered subset support |
| `frontend/src/components/shared/FilterBar.tsx` | Extend for count badges |
| `frontend/src/components/shared/FilterDropdown.tsx` | **NEW** — single-select dropdown for high-count dimensions |
| `frontend/src/hooks/useFilterState.ts` | **NEW** — coordinated multi-dimension filter state hook |
| `frontend/src/pages/PuzzleRushPage.tsx` | Add level/tag selection to setup; fix hardcoded 'beginner' |
| `frontend/src/pages/RushBrowsePage.tsx` | Add level/tag filter controls to setup screen |
| `frontend/src/app.tsx` | Update `getNextPuzzle()` to accept level + tag filters |
| `frontend/src/pages/DailyChallengePage.tsx` (or equivalent) | Daily master index consumption + distribution display |
| `specs/131-frontend-view-schema/contracts/view-types.ts` | Type updates |

### Config / Schema
| File | Change Type |
|------|-------------|
| `config/schemas/view-index.schema.json` | Entry + master index schema updates |

---

> **See also**:
> - [Spec 119](../specs/119-view-schema-simplification/spec.md) — Original schema simplification rationale
> - [Spec 131](../specs/131-frontend-view-schema/data-model.md) — Frontend view schema v3.0 data model
> - [Spec 130](../specs/130-view-schema-contract/) — View index JSON schema contract
> - [Spec 106](../specs/106-view-index-pagination/) — View index pagination
