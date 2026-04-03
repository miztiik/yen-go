# Technical Plan: Collection Edition Detection

**Last Updated**: 2026-03-30  
**Implementation Level**: Level 3 (2-3 files backend + frontend)

---

## 1. The Two Problems and Their Fixes

### Problem 1: Content Loss at Ingest

**Current**: `_check_dedup()` in `ingest.py` rejects any puzzle whose `position_hash` already exists in `yengo-content.db`. Cross-source duplicates are silently lost.

**Fix**: If `position_hash` matches but `source` is different → allow through. Same-source duplicates still rejected.

### Problem 2: Interleaved Ordering at Publish

**Current**: Puzzles from multiple sources in the same collection are merged into one flat list. Sort tiebreaker (`content_hash`) scrambles pedagogical order.

**Fix**: At publish, group puzzles by `(collection_slug, source)`. If 2+ sources → create edition sub-collections. Each edition has its own sequence 1-N.

---

## 2. Schema Change: Add `collection_slug` to `yengo-content.db`

### Why

Today, knowing which collection a puzzle belongs to requires parsing the `YL[]` property from the raw SGF text inside `sgf_content`. This is expensive (string parsing for every puzzle) and prevents simple SQL queries for collision detection.

### Change

```sql
ALTER TABLE sgf_files ADD COLUMN collection_slug TEXT;
CREATE INDEX IF NOT EXISTS idx_sgf_collection ON sgf_files(collection_slug);
```

**When populated**: During `build_content_db()` in `content_db.py`. The SGF's `YL[]` value is already parsed upstream — we just write the slug to this column alongside the SGF content.

**Existing entries**: Get `NULL` for `collection_slug`. This is safe — the collision check treats NULL as "no collection" (no collision possible).

**Migration**: The `ALTER TABLE ... ADD COLUMN` is idempotent (SQLite allows it; existing rows get NULL). Add a `_ensure_collection_slug_column()` helper similar to the existing `_ensure_batch_column()` pattern in `content_db.py`.

---

## 3. Problem 1 Fix: Dedup Bypass at Ingest

### Current Code (`ingest.py` line ~265)

```python
def _check_dedup(conn, sgf_content) -> str | None:
    pos = extract_position_data(sgf_content)
    p_hash = canonical_position_hash(...)
    row = conn.execute(
        "SELECT content_hash FROM sgf_files WHERE position_hash = ?",
        (p_hash,),
    ).fetchone()
    return row[0] if row else None  # non-None → REJECT
```

### Proposed Change

```python
@staticmethod
def _check_dedup(conn, sgf_content, *, source_id: str) -> str | None:
    pos = extract_position_data(sgf_content)
    p_hash = canonical_position_hash(...)
    rows = conn.execute(
        "SELECT content_hash, source FROM sgf_files WHERE position_hash = ?",
        (p_hash,),
    ).fetchall()
    if not rows:
        return None  # No match → allow
    for existing_hash, existing_source in rows:
        if existing_source == source_id:
            return existing_hash  # Same source duplicate → reject
    # All matches are from different sources → allow through
    return None
```

**Key points**:
- Stays `@staticmethod` (no `self` parameter) — preserves existing test calling convention
- `fetchall()` not `fetchone()` — handles 3+ sources correctly
- Rejects if ANY existing row matches current source
- Allows if ALL matches are from different sources
- Signature adds `source_id` kwarg — single caller in `run()` method (line ~128) updated: `self._check_dedup(dedup_conn, result.sgf_content, source_id=source.id)`
- 5 existing tests in `test_dedup_detection.py` updated to pass `source_id="test"` kwarg

---

## 4. Problem 2 Fix: Edition Detection at Publish

### Collision Detection at Ingest Startup

Before processing puzzles, ingest does ONE query per collection the current source will contribute to:

```python
# At ingest startup, after loading source config
# Determine which collections this source will contribute to
# (from the source's adapter config or manifest)
for collection_slug in source_collection_slugs:
    count = conn.execute(
        "SELECT COUNT(DISTINCT source) FROM sgf_files "
        "WHERE collection_slug = ? AND source != ?",
        (collection_slug, source_id),
    ).fetchone()[0]
    if count > 0:
        logger.info(
            "Collection %s has entries from %d other source(s) — "
            "editions will be created at publish",
            collection_slug, count,
        )
```

This is informational logging only — the actual edition creation happens at publish. But it gives early visibility into which collections will get editions.

### Edition Creation at Publish

In `_build_search_database()`, after building `all_entries`:

```python
# Step 1: Query yengo-content.db for multi-source collections
multi_source = conn.execute(
    "SELECT collection_slug, source, GROUP_CONCAT(content_hash) "
    "FROM sgf_files "
    "WHERE collection_slug IS NOT NULL "
    "GROUP BY collection_slug, source"
).fetchall()

# Step 2: Find collections with 2+ sources
from collections import defaultdict
col_sources: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
for slug, source, hashes in multi_source:
    col_sources[slug][source] = hashes.split(",")

edition_parents: dict[str, dict[str, list[str]]] = {
    slug: sources for slug, sources in col_sources.items()
    if len(sources) >= 2
}

# Step 3: For each multi-source collection, create editions
for slug, source_map in edition_parents.items():
    parent = next(c for c in collections if c.slug == slug)
    parent_id = parent.collection_id
    parent.attrs["is_parent"] = True
    parent.attrs["edition_ids"] = []

    sorted_sources = sorted(source_map.items(), key=lambda x: len(x[1]), reverse=True)

    for idx, (source_id, puzzle_hashes) in enumerate(sorted_sources):
        edition_id = _edition_id(slug, source_id)  # deterministic hash
        parent.attrs["edition_ids"].append(edition_id)

        edition = CollectionMeta(
            collection_id=edition_id,
            slug=f"{slug}--{source_id}",
            name=parent.name,
            category=parent.category,
            puzzle_count=len(puzzle_hashes),
            attrs={
                "parent_id": parent_id,
                "label": f"Edition {idx + 1} ({len(puzzle_hashes)} puzzles)",
                "type": parent.category or "",
            },
        )
        edition_collections.append(edition)

        # Remap puzzles from parent to edition
        hash_set = set(puzzle_hashes)
        for entry in all_entries:
            if entry.content_hash in hash_set:
                if parent_id in entry.collection_ids:
                    entry.collection_ids.remove(parent_id)
                if edition_id not in entry.collection_ids:
                    entry.collection_ids.append(edition_id)
```

### Edition ID Allocation

```python
def _edition_id(parent_slug: str, source_id: str) -> int:
    """Deterministic, stable across publishes."""
    digest = hashlib.sha256(f"{parent_slug}:{source_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 10_000_000 + 100_000
```

Range 100K–10.1M. Config IDs are 1-200. Collision assertion at publish: `assert edition_id not in config_ids`.

### Shared Utility for Rollback

The edition creation logic is extracted to `backend/puzzle_manager/core/edition_detection.py`:

```python
def create_editions(
    all_entries: list[PuzzleEntry],
    collections: list[CollectionMeta],
    content_db_path: Path,
) -> list[CollectionMeta]:
    """Detect multi-source collections and create edition sub-collections.
    
    Queries yengo-content.db for collection_slug grouping.
    Mutates all_entries (remaps collection_ids).
    Returns new CollectionMeta edition entries to extend into collections.
    
    Called by:
    - publish.py._build_search_database()
    - rollback.py._rebuild_search_db()
    """
```

The content DB path is the only dependency — no config fields, no policy dicts, no position_hash lookups. The function queries the DB directly for the `GROUP BY` result.

### Rollback Wiring

`rollback.py._rebuild_search_db()` calls `create_editions()` after building `entries` and before calling `build_search_db()`. Uses atomic swap pattern (temp file + `os.replace()`) to prevent DB-1 loss on failure.

---

## 5. Frontend: EditionPicker

### CollectionViewPage changes

```typescript
const attrs = JSON.parse(collection.attrs || '{}');

if (attrs.is_parent && Array.isArray(attrs.edition_ids) && attrs.edition_ids.length > 0) {
  const editions = getEditionCollections(collection.collection_id);
  return <EditionPicker editions={editions} parentName={collection.name} />;
}
if (attrs.is_parent) {
  return <EmptyState message="No editions available" />;
}
// Normal puzzle list
```

### New query in puzzleQueryService.ts

```typescript
export function getEditionCollections(parentId: number): CollectionRow[] {
  return query<CollectionRow>(
    `SELECT * FROM collections 
     WHERE json_extract(attrs, '$.parent_id') = ?
     ORDER BY puzzle_count DESC`,
    [parentId],
  );
}
```

### Browse/search filtering

All FTS queries (`searchCollections`, `searchCollectionsByTypes`) add:
```sql
AND json_extract(c.attrs, '$.parent_id') IS NULL
```

Parent collections exempt from `MIN_PUZZLE_COUNT` filter. Show "N editions" badge.

---

## 6. `collection_slug` Population in `build_content_db()`

In `content_db.py`, `build_content_db()` receives `sgf_files: dict[str, str]` (content_hash → SGF text). The SGF text contains `YL[slug:chapter/pos]`. We extract the slug and write it to the new column:

```python
# In build_content_db(), during row construction:
collection_slug = _extract_collection_slug(sgf_content)  # parse YL[] from SGF

rows.append((
    content_hash, sgf_content, position_hash, board_size,
    ..., source, now, batch,
    collection_slug,  # NEW column
))
```

```python
def _extract_collection_slug(sgf_content: str) -> str | None:
    """Extract first collection slug from YL[] property."""
    match = re.search(r'YL\[([^\]:,]+)', sgf_content)
    return match.group(1) if match else None
```

**Note**: A puzzle may belong to multiple collections (`YL[slug1,slug2]`). For the `collection_slug` column, we store the first/primary slug. The full multi-collection membership is handled by `collection_ids` on `PuzzleEntry` during publish (unchanged from today).

For collision detection, matching on ANY shared slug is sufficient — if two sources both contribute to `cho-chikun-elementary`, that's enough to trigger editions for that collection.

---

## 7. Data Model Summary

| Layer | Current | After |
|-------|---------|-------|
| `yengo-content.db` | No `collection_slug` column | New `collection_slug TEXT` + index |
| `yengo-content.db` | One entry per position (dedup rejects) | Multiple entries per position (cross-source allowed) |
| `yengo-search.db` | Collections from config only | Config + synthetic edition sub-collections in `attrs` |
| `collections.json` | No edition-related fields | **Unchanged** |
| SGF files | `YL[slug:ch/pos]` | **Unchanged** |
| Frontend | Shows puzzle list for every collection | Shows EditionPicker for parent collections |

---

## 8. Risks & Mitigations

| R_ID | Risk | Mitigation |
|------|------|------------|
| R1 | Edition ID collision | Hash in 10M range + assertion. Config IDs 1-200. |
| R2 | NULL `collection_slug` on legacy entries | Treated as "no collection" — excluded from collision detection |
| R3 | Puzzle in multiple collections (multi-slug YL) | `collection_slug` stores first slug. Full membership via `collection_ids` at publish. |
| R4 | Rollback failure loses `yengo-search.db` | Atomic swap: temp file + `os.replace()` |
| R5 | Progress orphaning when parent splits to editions | Document in EditionPicker UI: "Progress tracked per edition" |

---

## 9. Rollback Strategy

Fully additive. Revert code changes → next publish builds `yengo-search.db` without editions. `yengo-content.db` retains the `collection_slug` column (harmless). Cross-source entries in content DB remain (harmless — dedup revert would prevent future duplicates but existing ones stay).

---

## 10. Evolution Path

Future improvements (if needed) are tracked as research, not planned work. No v2 scope is committed.

> **See also**:
> - [40-tasks.md](40-tasks.md) — Task decomposition
> - [20-analysis.md](20-analysis.md) — Analysis
