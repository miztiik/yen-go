# Architecture: View Index Segmentation

**Last Updated**: 2026-02-01  
**Status**: Design Complete  
**Spec Reference**: [Spec 106](../../../specs/106-view-index-segmentation/spec.md)

---

## Overview

View Index Segmentation is the backend strategy for generating scalable, paginated index files that allow the frontend to efficiently browse large puzzle collections. Instead of loading entire collections into memory, the system uses **append-only batch updates** with a **single-page memory footprint**.

## Design Principles

### 1. Append-Only Writes

Segments (page files) are **immutable** once full. New puzzles are only appended to the **last segment**. This provides:

- **Predictable memory usage**: Only one page (500 puzzles) in memory at a time
- **CDN-friendly**: Full segments can be cached indefinitely
- **Crash resilience**: Partial writes only affect the last segment

### 2. Progressive Structure

Collections start as single files and **automatically migrate** to segmented directories when they exceed the threshold:

```
Small collection (≤500):        Large collection (>500):
views/by-level/beginner.json    views/by-level/intermediate/
                                ├── index.json
                                ├── page-001.json
                                ├── page-002.json
                                └── page-003.json
```

### 3. State Tracking

Segment metadata is persisted to avoid scanning files on every run:

```json
// yengo-puzzle-collections/views/.segment-state.json
{
  "levels": {
    "intermediate": {
      "total": 1250,
      "segments": 3,
      "last_segment_count": 250
    }
  }
}
```

> **Why not `.pm-runtime/state/`?**
> - `.pm-runtime/state/` is cleaned up periodically (45-day retention)
> - Segment state must persist as long as collections exist
> - Colocated with the views it describes
> - Git-tracked for recovery and auditability
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PUBLISH STAGE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │   Puzzle    │    │  SegmentWriter  │    │     Output Files            │  │
│  │   Batch     │───▶│                 │───▶│                             │  │
│  │ (100 items) │    │ append_to_level │    │  views/by-level/            │  │
│  └─────────────┘    │ append_to_tag   │    │  ├── index.json             │  │
│                     │                 │    │  ├── beginner.json          │  │
│                     └────────┬────────┘    │  └── intermediate/          │  │
│                              │             │      ├── index.json         │  │
│                              ▼             │      ├── page-001.json      │  │
│                     ┌─────────────────┐    │      └── page-002.json      │  │
│                     │  SegmentState   │    │                             │  │
│                     │                 │    └─────────────────────────────┘  │
│                     │ index_segments  │                                      │
│                     │     .json       │                                      │
│                     └─────────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Append Flow (Normal Operation)

```
New Puzzles (100)
       │
       ▼
┌──────────────────┐
│ Load State File  │  ← O(1) - Just metadata
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Check if level   │
│ is segmented?    │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
   No        Yes
    │         │
    ▼         ▼
┌────────┐  ┌────────────────┐
│ Single │  │ Load LAST      │  ← O(page_size)
│ file   │  │ segment only   │
│ mode   │  └───────┬────────┘
└───┬────┘          │
    │               ▼
    │         ┌────────────────┐
    │         │ Room in last?  │
    │         └───────┬────────┘
    │            ┌────┴────┐
    │           Yes       No
    │            │         │
    │            ▼         ▼
    │         ┌─────┐   ┌───────────┐
    │         │Append│  │Create new │
    │         │here │   │segment    │
    │         └──┬──┘   └─────┬─────┘
    │            │            │
    └────────────┴────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Update state  │
         │ Update master │
         │ index         │
         └───────────────┘
```

### Structure Transition (Single → Segmented)

When a level exceeds the threshold, the system transitions from single-file to segmented structure:

```
Single File (480 puzzles)
         │
         ▼
Add 100 puzzles → Total 580 > Threshold (500)
         │
         ▼
┌─────────────────────────────┐
│ 1. Load existing puzzles    │
│    from beginner.json       │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. Create segmented dir     │
│    intermediate/            │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. Write segments:          │
│    page-001.json (500)      │
│    page-002.json (80)       │
│    index.json (metadata)    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. Delete single file       │
│ 5. Update state             │
└─────────────────────────────┘
```

> **Note**: No complex migration logic needed. Pipeline is single-threaded, so no race conditions. Existing flat indexes will simply be replaced when this feature is deployed.

---

## File Formats

### Master Index (`views/by-level/index.json`)

```json
{
  "version": "1.0",
  "generated_at": "2026-02-01T10:30:00Z",
  "levels": [
    {
      "name": "beginner",
      "count": 450,
      "paginated": false
    },
    {
      "name": "intermediate",
      "count": 1250,
      "paginated": true,
      "pages": 3
    }
  ]
}
```

### Segment Metadata (`views/by-level/intermediate/index.json`)

```json
{
  "level": "intermediate",
  "total_count": 1250,
  "page_size": 500,
  "pages": 3
}
```

### Segment Page (`views/by-level/intermediate/page-001.json`)

```json
{
  "level": "intermediate",
  "page": 1,
  "total_pages": 3,
  "total_puzzles": 1250,
  "puzzles": [
    {"id": "abc123", "path": "sgf/intermediate/2026/02/batch-001/abc123.sgf"},
    {"id": "def456", "path": "sgf/intermediate/2026/02/batch-001/def456.sgf"}
  ]
}
```

### State File (`yengo-puzzle-collections/views/.segment-state.json`)

```json
{
  "version": "1.0",
  "updated_at": "2026-02-01T10:30:00Z",
  "page_size": 500,
  "levels": {
    "beginner": {
      "total": 450,
      "segmented": false,
      "file": "beginner.json"
    },
    "intermediate": {
      "total": 1250,
      "segmented": true,
      "segments": 3,
      "last_segment_count": 250
    }
  },
  "tags": {
    "snapback": {
      "total": 120,
      "segmented": false,
      "file": "snapback.json"
    }
  }
}
```

---

## Design Decisions

### Why 500 Puzzles Per Page?

| Page Size | File Size | Tradeoffs |
|-----------|-----------|-----------|
| 100 | ~5KB | Too many HTTP requests |
| 500 | ~25KB | Good balance: fast load, reasonable requests |
| 1000 | ~50KB | Slower on mobile, larger memory footprint |
| 2000 | ~100KB | Too large for progressive loading |

**Decision**: 500 provides fast initial load (~25KB) while keeping memory footprint manageable.

### Why Append-Only Instead of Update-in-Place?

| Approach | Pros | Cons |
|----------|------|------|
| **Update-in-place** | Simple logic | Must load entire file, O(N) memory |
| **Append-only** | O(1) append, O(page_size) memory | More complex rollback |

**Decision**: Append-only scales to millions of puzzles without memory issues.

### Why Full Rebuild on Rollback?

| Approach | Pros | Cons |
|----------|------|------|
| **Targeted page update** | Faster rollback | Complex logic, error-prone |
| **Full level rebuild** | Simple, reliable | Slower for large collections |

**Decision**: Rollback is rare; simplicity > performance for this case.

### Why State File Instead of Directory Scan?

| Approach | Pros | Cons |
|----------|------|------|
| **Scan directories** | No state to manage | O(N) on every run |
| **State file** | O(1) lookup | Must keep in sync |

**Decision**: State file with crash recovery (scan as fallback) provides best of both.

---

## Error Handling

### Crash Recovery

If pipeline crashes mid-write:

1. **State file may be stale** → Recover by scanning actual files
2. **Last segment may be partial** → Accept partial (puzzles are valid)
3. **Migration temp dir may exist** → Delete and retry

```python
def _recover_state(self) -> None:
    """Recover from crash by scanning actual files."""
    for level_dir in (self.views_dir / "by-level").iterdir():
        if level_dir.is_dir() and not level_dir.name.startswith('.'):
            # Segmented level - count actual pages
            pages = list(level_dir.glob("page-*.json"))
            # ... update state from actual files
```

### Atomic Operations

All writes use temp-then-rename pattern:

```python
def _atomic_write(self, path: Path, content: str) -> None:
    """Write atomically using temp file."""
    temp = path.with_suffix('.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.replace(path)  # Atomic on POSIX
```

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Append N puzzles | O(N + page_size) | Load last page, write new pages |
| Read state | O(1) | Single JSON file |
| Full rebuild | O(total_puzzles) | Scan all SGF files |
| Migration | O(total_puzzles) | One-time per level |

### Memory Usage

| Collection Size | Current (O(N)) | New (O(page_size)) |
|-----------------|----------------|-------------------|
| 1K puzzles | ~200KB | ~100KB |
| 10K puzzles | ~2MB | ~100KB |
| 100K puzzles | ~20MB | ~100KB |
| 1M puzzles | ~200MB | ~100KB |

---

## Integration Points

### Publish Stage

```python
# stages/publish.py
class PublishStage:
    def _update_indexes(self, puzzles_by_level, puzzles_by_tag, context):
        writer = SegmentWriter(
            views_dir=context.output_dir / "views",
            state_dir=context.state_dir,
            page_size=context.config.views.page_size,
        )
        
        for level, puzzles in puzzles_by_level.items():
            writer.append_to_level(level, puzzles)
        
        for tag, puzzles in puzzles_by_tag.items():
            writer.append_to_tag(tag, puzzles)
        
        writer.update_master_indexes()
```

### Rollback

The current `_update_indexes()` in `rollback.py` only handles flat JSON files. With segmented indexes, it must:

1. Detect if level is segmented (directory vs file)
2. For segmented levels, rebuild ALL segments after removal
3. Update `.segment-state.json`

```python
# rollback.py - UPDATED for segmented indexes
class RollbackManager:
    def _update_indexes(self, entries):
        # Identify affected levels/tags
        affected_levels = {extract_level(e.path) for e in entries}
        
        writer = SegmentWriter(views_dir=self.output_dir / "views")
        
        for level in affected_levels:
            # Get remaining puzzles for this level from SGF files
            remaining_puzzles = self._scan_level_sgf_files(level)
            # Rebuild the level (handles both flat and segmented)
            writer.rebuild_level(level, remaining_puzzles)
        
        # State is automatically updated by SegmentWriter
```

### Frontend

No changes required. Output matches existing types:

```typescript
// Already implemented in frontend/src/types/indexes.ts
interface LevelMasterIndex { ... }
interface PaginatedLevelIndex { ... }
interface LevelPage { ... }
```

**Important**: Frontend must ignore dotfiles when listing indexes. The `.segment-state.json` file should not be loaded as an index.

---

## Second-Order Impacts

### Files Requiring Modification

| File | Change Required |
|------|-----------------|
| `backend/puzzle_manager/pipeline/cleanup.py` | Add `views/.segment-state.json` to `PROTECTED_FILES` pattern |
| `backend/puzzle_manager/rollback.py` | Refactor `_update_indexes()` to handle segmented directories |
| `frontend/src/lib/puzzle/pagination.ts` | Ensure dotfiles are filtered when listing indexes |

### Cleanup Protection

The `PROTECTED_FILES` constant in `cleanup.py` must be updated:

```python
# cleanup.py
PROTECTED_FILES: frozenset[str] = frozenset([
    "puzzle-collection-inventory.json",
    ".segment-state.json",  # NEW: Protect segment state
])
```

### Git Tracking Decision

The `.segment-state.json` file SHOULD be git-tracked because:

1. **Disaster recovery**: If `.pm-runtime/` is deleted, views still work
2. **Auditability**: Track when segment structure changes
3. **Low churn**: Only updates on actual publishes, not every run

### Inventory File Location

The `puzzle-collection-inventory.json` stays at the root of `yengo-puzzle-collections/` because:

- It's a **collection-level** manifest (total counts, sources, audit trail)
- `.segment-state.json` is **view-specific** metadata (pagination state)
- Different scopes = different locations

---

## See Also

- [Spec 106: View Index Segmentation](../../../specs/106-view-index-segmentation/spec.md) - Full specification
- [How-To: Run Pipeline](../../how-to/backend/run-pipeline.md) - Pipeline operations
- [Frontend Pagination](../frontend/pagination.md) - How frontend consumes these indexes
- [Reference: Index Formats](../../reference/index-formats.md) - JSON schema reference
