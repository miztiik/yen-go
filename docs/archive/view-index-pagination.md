# Architecture: View Index Pagination (ARCHIVED)

**Last Updated**: 2026-03-14
**Status**: ❌ **ARCHIVED** — Superseded by SQLite Index Architecture

> **This document describes the old `PaginationWriter` + `views/by-level/by-tag/by-collection/` system which has been fully replaced.**
>
> The publish pipeline now uses `db_builder.build_search_db()` to produce `yengo-search.db` (SQLite).
> `PaginationWriter`, `pagination_models`, `SnapshotBuilder`, `ShardWriter`, and `shard_models` have all been deleted from the codebase.
>
> **See instead**:
>
> - [Concepts: SQLite Index Architecture](../../concepts/sqlite-index-architecture.md) — Canonical terminology
> - [Architecture: System Overview](../system-overview.md) — Current directory layout
> - [Architecture: Database Deployment Topology](../database-deployment-topology.md) — Deployment ADR

---

## Historical Context

The old view system used `PaginationWriter` to produce three append-only paginated directory structures:

- `views/by-level/{numeric_id}/page-NNN.json`
- `views/by-tag/{numeric_id}/page-NNN.json`
- `views/by-collection/{numeric_id}/page-NNN.json`

With master index files (`views/by-*/index.json`) and a `.pagination-state.json` tracking file.

This was replaced by the snapshot-centric architecture because:

1. **No cross-dimensional filtering** — filtering by level+tag required loading both views and merging client-side
2. **Append-only limitation** — couldn't efficiently remove or reclassify entries
3. **No atomic publish** — partial writes during crashes left inconsistent state
4. **Unbounded memory for recovery** — filesystem scan on state corruption read every page

The current system uses SQLite databases (`yengo-search.db` for frontend queries, `yengo-content.db` for dedup). See [Concepts: SQLite Index Architecture](../../concepts/sqlite-index-architecture.md).

This document describes the architecture for scalable view index pagination in the Yen-Go puzzle pipeline. The design enables O(page_size) memory usage for append operations, supporting collections of 100K+ puzzles.

## Implementation Summary

The pagination system is implemented in:

| Component            | Location                                           | Purpose               |
| -------------------- | -------------------------------------------------- | --------------------- |
| `PaginationConfig`   | `backend/puzzle_manager/models/config.py`          | Configuration model   |
| `PaginationState`    | `backend/puzzle_manager/core/pagination_models.py` | State tracking models |
| `PaginationWriter`   | `backend/puzzle_manager/core/pagination_writer.py` | Core pagination logic |
| Publish integration  | `backend/puzzle_manager/stages/publish.py`         | Pipeline integration  |
| Rollback integration | `backend/puzzle_manager/rollback.py`               | Rollback support      |

### Key Methods

```python
# Append operations - O(page_size) memory
writer.append_level_puzzles(level, puzzles)
writer.append_tag_puzzles(tag, puzzles)

# Rollback operations
writer.remove_puzzles_from_level(level, puzzle_ids)
writer.remove_puzzles_from_tag(tag, puzzle_ids)
writer.remove_puzzles_from_collection(collection, puzzle_ids)  # Spec 138
writer.rebuild_level(level, remaining_puzzles)
writer.rebuild_tag(tag, remaining_puzzles)

# Navigation
writer.generate_master_indexes()
```

### Test Coverage

| Test File                                | Tests | Coverage                 |
| ---------------------------------------- | ----- | ------------------------ |
| `test_pagination_writer.py`              | 24    | Core operations          |
| `test_pagination_contracts.py`           | 12    | Output format validation |
| `test_pagination_rollback.py`            | 13    | Rollback operations      |
| `test_pagination_state.py`               | 14    | Crash recovery           |
| `integration/test_publish_pagination.py` | 12    | End-to-end scenarios     |

## Historical Context (Pre-v4.0)

### Previous Approach

Before pagination, `_update_indexes()` in `publish.py` loaded the entire index into memory:

```python
# Previous O(N) implementation
def _update_indexes(self, puzzles: list[dict]) -> None:
    for view in ['by-level', 'by-tag']:
        index_path = self.views_dir / view / f'{name}.json'
        existing = json.loads(index_path.read_text())  # Load ALL
        all_puzzles = existing + puzzles              # Merge ALL
        index_path.write_text(json.dumps(all_puzzles)) # Write ALL
```

**Issues that motivated pagination**:

- Memory: O(N) where N = total puzzles
- Performance: Full rewrite on every append
- Scalability: Degrades as collection grows

### Current Approach

Append-only pagination with O(page_size) memory:

```python
# New implementation - O(page_size) memory
def append_puzzles(self, level: str, puzzles: list[dict]) -> None:
    state = self.load_state(level)
    last_page = self.load_last_page(level, state)  # Load ONE page
    last_page.extend(puzzles)                       # Append
    self.save_pages(level, last_page, state)        # Write ONE page (usually)
```

---

## Design Decisions

### DD-001: Append-Only Page Strategy

**Decision**: Only the last page is mutable; previous pages are immutable.

**Rationale**:

- Enables O(page_size) memory usage
- Simplifies concurrent access (no mid-file modifications)
- Previous pages serve as stable cache targets

**Trade-offs**:

- Cannot delete individual puzzles from middle pages
- Rollback requires full rebuild of affected levels

---

### DD-002: State Colocated with Data

**Decision**: Store pagination state in `views/.pagination-state.json`, not `.pm-runtime/state/`.

**Rationale**:

- `.pm-runtime/state/` has 45-day cleanup retention
- State should live as long as the data it describes
- Git-tracked for disaster recovery
- Simpler mental model (state is part of output)

**Trade-offs**:

- State file visible in output directory (mitigated: dotfile naming)
- Must handle concurrent access if ever needed (currently single-threaded)

---

### DD-003: 500 Puzzle Page Size

**Decision**: Default page size of 500 puzzles per page.

**Rationale**:

- 500 × ~200 bytes = ~100KB per page (reasonable HTTP payload)
- Balances memory efficiency with I/O overhead
- User-configured to 500 (original suggestion was 1000)

**Trade-offs**:

- More pages to manage for large collections
- Slightly more I/O operations

---

### DD-004: Always-Paginated (v4.0)

**Decision**: All views are always paginated regardless of entry count. No flat file mode.

**Rationale** (updated v4.0):

- Eliminates dual-format complexity in frontend and backend
- Frontend only needs one code path (directory structure)
- Consistent URL patterns for caching
- Small collections simply have 1 page

**History**: Originally threshold-based (≤500 flat, >500 paginated). Migrated to always-paginated in v4.0 to reduce code complexity. The `enabled` and `pagination_threshold` fields were removed from `PaginationConfig`, and `paginated` was removed from `LevelPaginationState`.

---

### DD-005: Full Rebuild on Rollback

**Decision**: Rollback rebuilds affected level indexes from remaining SGF files.

**Rationale**:

- Simpler than tombstone/delta tracking
- Guarantees consistency with actual file state
- Avoids complex page rewriting logic

**Trade-offs**:

- Slower rollback for large levels
- Temporary memory spike during rebuild

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PUBLISH STAGE                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐ │
│  │  Staging     │────▶│ PaginationWriter │────▶│   views/    │ │
│  │  SGF files   │     │                  │     │  (output)   │ │
│  └──────────────┘     └────────┬─────────┘     └─────────────┘ │
│                                │                                │
│                                ▼                                │
│                    ┌────────────────────────┐                   │
│                    │ .pagination-state.json │                   │
│                    │  (in views/ directory) │                   │
│                    └────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        ROLLBACK FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐ │
│  │  Publish Log │────▶│  RollbackManager │────▶│  Paginated  │ │
│  │  (affected   │     │                  │     │  Directory  │ │
│  │   puzzles)   │     └────────┬─────────┘     └──────┬──────┘ │
│  └──────────────┘              │                      │        │
│                                │                      ▼        │
│                         ┌──────┴───────┐       ┌────────────┐  │
│                         │ Remove IDs   │       │ Scan SGFs  │  │
│                         │ from entries │       │ & Rebuild  │  │
│                         └──────┬───────┘       └─────┬──────┘  │
│                                │                     │         │
│                                ▼                     ▼         │
│                         ┌────────────────────────────────┐     │
│                         │ Update state & master indexes  │     │
│                         └────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Append Flow (Normal Publish)

```
1. Publish stage receives batch of new puzzles
2. For each affected level:
   a. Load pagination state from .pagination-state.json
   b. Load ONLY last page
   c. Append compact entries {p, l, t, c, x}
   d. If page full, create new page
   e. Write affected pages only
3. Update .pagination-state.json
4. Update master index (by-level/index.json) with v2.0 distribution counters
```

### Rollback Flow

```
1. RollbackManager receives list of puzzle IDs to remove
2. Read publish log entries for affected puzzles
3. Group by level (from entry.level)
4. For each affected level:
   a. Scan remaining SGF files in level directory
   b. Rebuild all pages using PaginationWriter
   c. Update .pagination-state.json
5. For each affected tag (from entry.tags):
   - Same rebuild logic as levels
6. For each affected collection (from entry.collections):
   - Remove entries, renumber `n` (sequence) values
7. Update master indexes
8. Update inventory counts
```

> **Spec 138**: Publish log now includes `level`, `tags`, `collections` fields,
> enabling targeted rollback without filesystem scanning. Legacy entries without
> these fields fall back to path-based level extraction.

---

## Component Design

### PaginationWriter

**Location**: `backend/puzzle_manager/core/pagination_writer.py`

**Responsibilities**:

- Load/save pagination state
- Append puzzles to levels/tags
- Generate master indexes with distribution counters

**Key Methods**:

```python
class PaginationWriter:
    def __init__(self, views_dir: Path, config: PaginationConfig)

    def append_level_puzzles(self, level: str, puzzles: list[dict]) -> None
    def append_tag_puzzles(self, tag: str, puzzles: list[dict]) -> None
    def rebuild_level(self, level: str, puzzle_ids: list[str]) -> None
    def rebuild_tag(self, tag: str, puzzle_ids: list[str]) -> None
    def generate_master_indexes(self) -> None

    def _load_state(self) -> PaginationState
    def _save_state(self, state: PaginationState) -> None
    def _recover_state_from_files(self) -> PaginationState
```

### PaginationState

**Location**: `backend/puzzle_manager/core/pagination_models.py`

```python
@dataclass
class LevelPaginationState:
    total: int
    pages: int = 1
    last_page_count: int = 0

@dataclass
class PaginationState:
    version: str = "1.0"
    updated_at: str = ""
    page_size: int = 500
    levels: dict[str, LevelPaginationState] = field(default_factory=dict)
    tags: dict[str, LevelPaginationState] = field(default_factory=dict)
```

### PaginationConfig

**Location**: `backend/puzzle_manager/models/config.py`

```python
@dataclass
class PaginationConfig:
    page_size: int = 500
```

---

## Output Format

### Master Index v2.0 (`by-level/index.json`)

```json
{
  "version": "2.0",
  "generated_at": "2026-02-01T10:30:00Z",
  "levels": [
    {
      "name": "beginner",
      "slug": "beginner",
      "id": 120,
      "count": 200,
      "pages": 1,
      "tags": { "36": 15, "60": 8 }
    },
    {
      "name": "intermediate",
      "slug": "intermediate",
      "id": 140,
      "count": 1200,
      "pages": 3,
      "tags": { "36": 120, "60": 80 }
    }
  ]
}
```

### Directory Index (`by-level/140/index.json`)

```json
{
  "type": "level",
  "name": "intermediate",
  "total_count": 1200,
  "page_size": 500,
  "pages": 3
}
```

### Page File (`by-level/140/page-001.json`)

Compact entries with numeric IDs:

```json
{
  "type": "level",
  "name": "intermediate",
  "page": 1,
  "entries": [
    {
      "p": "0001/1e9b57de9becd05f",
      "l": 140,
      "t": [36, 60],
      "c": [2],
      "x": [1, 2, 25, 1]
    }
  ]
}
```

### State File (`views/.pagination-state.json`)

```json
{
  "version": "1.0",
  "updated_at": "2026-02-01T10:30:00Z",
  "page_size": 500,
  "levels": {
    "intermediate": {
      "total": 1200,
      "pages": 3,
      "last_page_count": 200
    },
    "beginner": {
      "total": 200,
      "pages": 1,
      "last_page_count": 200
    }
  },
  "tags": {
    "snapback": {
      "total": 600,
      "pages": 2,
      "last_page_count": 100
    }
  }
}
```

---

## Integration Points

### Publish Stage Integration

**File**: `backend/puzzle_manager/stages/publish.py`

Replace `_update_indexes()` with PaginationWriter:

```python
def _update_indexes(self, puzzles: list[dict]) -> None:
    writer = PaginationWriter(self.views_dir, self.config.pagination)

    # Group by level
    by_level = defaultdict(list)
    for puzzle in puzzles:
        by_level[puzzle['level']].append(puzzle)

    for level, level_puzzles in by_level.items():
        writer.append_level_puzzles(level, level_puzzles)

    # Similar for tags
    writer.generate_master_indexes()
```

### Rollback Integration

**File**: `backend/puzzle_manager/rollback.py`

Rollback rebuilds always-paginated views:

```python
def _update_indexes(self, removed_ids: set[str], affected_levels: set[str]) -> None:
    writer = PaginationWriter(self.views_dir, self.config.pagination)

    for level in affected_levels:
        # Always paginated: rebuild from remaining SGF files
        remaining_ids = self._scan_level_sgf_files(level, removed_ids)
        writer.rebuild_level(level, remaining_ids)

    writer.generate_master_indexes()
```

### Cleanup Integration

**File**: `backend/puzzle_manager/pipeline/cleanup.py`

Add `.pagination-state.json` to protected files:

```python
PROTECTED_FILES = [
    '.gitkeep',
    'README.md',
    '.pagination-state.json',  # NEW: Pagination state must persist
]
```

---

## Error Handling

### State Corruption Recovery

If `.pagination-state.json` is corrupted or missing:

1. Log warning about missing/corrupt state
2. Scan file system to reconstruct state
3. For each level/tag directory:
   - Count pages
   - Read last page to get entry count
4. Write recovered state file
5. Continue with operation

### Page Write Failure

If page write fails mid-operation:

1. State file NOT updated (atomic write pattern)
2. Next run detects mismatch (pages on disk vs state)
3. Recovery scan corrects state
4. Operation retries successfully

---

## Performance Characteristics

| Operation           | Memory           | Time   | I/O        |
| ------------------- | ---------------- | ------ | ---------- |
| Append 100 to empty | O(100)           | <100ms | 2 writes   |
| Append 100 to 10K   | O(500)           | <200ms | 1-2 writes |
| Rebuild 500 entries | O(500)           | <500ms | 1 write    |
| Full rebuild 10K    | O(500)           | <5s    | 20 writes  |
| State recovery      | O(levels × tags) | <5s    | Reads only |

---

## Implementation History

### Phase 1: Core (Completed)

1. Created `pagination_writer.py` and `pagination_models.py`
2. Added `PaginationConfig` to config model
3. Wrote comprehensive unit tests

### Phase 2: Publish Integration (Completed)

1. Modified `publish.py` to use PaginationWriter
2. All views are always-paginated (no flat mode)
3. Numeric view directory names via `IdMaps`

### Phase 3: Rollback Integration (Completed)

1. Refactored `rollback.py` to rebuild paginated directories
2. Added rebuild logic for paginated levels
3. State file updated after rollback

### Phase 4: Cleanup Protection (Completed)

1. Added `.pagination-state.json` to PROTECTED_FILES
2. Verify cleanup doesn't affect pagination

---

## Testing Strategy

Test specification covers unit tests, state management tests, structure transition tests, and rollback integration tests.

**Key test categories**:

1. Unit tests for PaginationWriter
2. State management tests
3. Structure transition tests
4. Rollback integration tests
5. Frontend compatibility tests
6. Performance benchmarks
