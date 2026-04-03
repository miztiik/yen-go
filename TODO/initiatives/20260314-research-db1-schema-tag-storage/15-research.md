# Research: DB-1 Schema — Tag Storage, YQ/YX Field Design

**Last Updated**: 2026-03-14
**Initiative**: `20260314-research-db1-schema-tag-storage`
**Scope**: Evaluate many-to-many `puzzle_tags` vs boolean columns; assess YQ/YX field storage; validate filtering capabilities

---

## 1. Research Question & Boundaries

**Question**: Is the current DB-1 schema optimal for tag filtering, or should tags become boolean columns on the `puzzles` table? Are YQ and YX metrics stored as individual filterable columns or packed? Does the schema support all expected filtering use cases?

**Boundaries**:
- DB-1 only (browser-side search DB). No DB-2 changes.
- Schema at current scale (9K puzzles, targeting 750K).
- Must comply with Holy Laws (static file, sql.js WASM, no runtime backend).

---

## 2. Internal Code Evidence

### 2.1 Tag Inventory (config/tags.json v8.3)

| R-ID | Fact | Value |
|------|------|-------|
| R-1 | Total tag count | **28 tags** |
| R-2 | Category: Objectives | 4 tags (IDs 10-16): life-and-death, ko, living, seki |
| R-3 | Category: Tesuji | 12 tags (IDs 30-52): snapback, double-atari, ladder, net, throw-in, clamp, nakade, connect-and-die, under-the-stones, liberty-shortage, vital-point, tesuji |
| R-4 | Category: Techniques | 12 tags (IDs 60-82): capture-race, eye-shape, dead-shapes, escape, connection, cutting, sacrifice, corner, shape, endgame, joseki, fuseki |
| R-5 | Reserved range | IDs 84-98 (8 slots for future tags) |
| R-6 | Tag nature | Boolean (yes/no). A puzzle either has a tag or doesn't. No graduated/numeric values. |
| R-7 | Growth rate | Slow. v6.0→v8.3 added 10 tags over ~3 months. Taxonomy is stabilizing. |
| R-8 | Tag immutability | IDs are append-only. Existing IDs never change. |

### 2.2 Current Schema (db_builder.py)

| R-ID | Component | Implementation |
|------|-----------|----------------|
| R-9 | `puzzles` table | 10 columns: `content_hash`, `batch`, `level_id`, `quality`, `content_type`, `cx_depth`, `cx_refutations`, `cx_solution_len`, `cx_unique_resp`, `attrs` |
| R-10 | `puzzle_tags` table | Many-to-many: `(content_hash TEXT, tag_id INTEGER)`, composite PK |
| R-11 | Indexes on `puzzle_tags` | `idx_tags_tag` on `tag_id`, `idx_tags_hash` on `content_hash` |
| R-12 | `attrs` column | `TEXT DEFAULT '{}'` — JSON blob for extensibility. Currently **always empty `{}`** in production. |
| R-13 | YQ storage | `quality` INTEGER column (0-5). Single scalar extracted from`YQ[q:N;...]`. Sub-fields `rc`, `hc`, `ac` are **not stored** in DB-1. |
| R-14 | YX storage | 4 separate INTEGER columns: `cx_depth`, `cx_refutations`, `cx_solution_len`, `cx_unique_resp`. Fully decomposed. |
| R-15 | YX sub-field `w` (width) | **Not stored** in DB-1 (exists in YX string but not extracted). |
| R-16 | YX sub-field `a` (avg refutation depth) | **Not stored** in DB-1. |

### 2.3 Frontend Query Patterns (puzzleQueryService.ts)

| R-ID | Query Pattern | SQL Used | Analysis |
|------|---------------|----------|----------|
| R-17 | AND intersection (tag1 AND tag2) | `content_hash IN (SELECT content_hash FROM puzzle_tags WHERE tag_id IN (?,?) GROUP BY content_hash HAVING COUNT(DISTINCT tag_id) = ?)` | Correct relational-division pattern. Works for any N tags. |
| R-18 | Single tag filter | `JOIN puzzle_tags pt ON p.content_hash = pt.content_hash WHERE pt.tag_id = ?` | Standard indexed join. |
| R-19 | Tag counts (global) | `SELECT tag_id, COUNT(*) as cnt FROM puzzle_tags GROUP BY tag_id` | Full table scan of ~25K rows (9K puzzles × ~2.8 tags avg). |
| R-20 | Tag counts (filtered) | `SELECT pt2.tag_id, COUNT(DISTINCT p.content_hash) as cnt FROM puzzles p ... JOIN puzzle_tags pt2 ON p.content_hash = pt2.content_hash ${whereClause} GROUP BY pt2.tag_id` | Most complex query: re-joins puzzle_tags after filtering puzzles by other dimensions. |
| R-21 | Cross-tab (tags × levels) | `SELECT p.level_id, pt.tag_id, COUNT(*) as cnt FROM puzzles p JOIN puzzle_tags pt ... GROUP BY p.level_id, pt.tag_id` | Full cross-product aggregation. |
| R-22 | Quality filter | `p.quality >= ?` | Direct column comparison. Works today. |
| R-23 | Depth filter | `p.cx_depth >= ?` and `p.cx_depth <= ?` | Direct column range. Works today. |

---

## 3. External References

### 3.1 SQLite Column Limits and Performance

| E-ID | Fact | Source |
|------|------|--------|
| E-1 | SQLite maximum columns per table: **2,000** (compile-time default). Can be raised to 32,767. | SQLite documentation: `SQLITE_MAX_COLUMN` |
| E-2 | SQLite row size limit: ~1 GB. But wide rows cause B-tree page overflow, reducing scan performance. | SQLite internals documentation |
| E-3 | sql.js WASM: full SQLite compiled to WebAssembly. No column-limit differences from native. | sql.js GitHub repository |
| E-4 | Boolean columns in SQLite stored as INTEGER (0/1). Each uses 1-2 bytes varint on disk. | SQLite type affinity documentation |

### 3.2 Many-to-Many vs Boolean Columns — Industry Patterns

| E-ID | Pattern | When Recommended | Source |
|------|---------|-----------------|--------|
| E-5 | Many-to-many junction table | Tags are dynamic, count is unbounded, or grows frequently. Standard for user-generated tagging (SO, GitHub). | PostgreSQL wiki, SQLite best practices |
| E-6 | Boolean/bitmap columns | Tags are fixed, small count (<50), and the system needs maximum single-table scan performance. Common in analytics schemas. | ClickHouse/Redshift column-per-flag patterns |
| E-7 | Bitfield INTEGER | Compact (<64 tags), single column, bit-manipulation queries. Hard to read, no SQL standard. | Custom game engines, feature-flag systems |
| E-8 | JSON array column | Flexible but poor query performance. Requires `json_each()` in SQLite. Not indexable efficiently. | SQLite JSON1 extension docs |

### 3.3 In-Memory SQLite Performance Characteristics

| E-ID | Fact | Relevance |
|------|------|-----------|
| E-9 | In-memory SQLite (as used by sql.js) eliminates all disk I/O. JOIN performance is dominated by CPU, not I/O. | All Yen-Go queries run in-memory. |
| E-10 | For <100K rows, most SQLite queries complete in <5ms in-memory regardless of JOIN count. | At 9K puzzles, current performance is not a concern. |
| E-11 | At 750K puzzles with ~2M junction rows, many-to-many JOINs may take 20-50ms for complex filtered counts. Still acceptable for UI. | Scale ceiling is relevant. |

---

## 4. Candidate Approaches for Yen-Go

### Approach A: Keep Many-to-Many (Current)

```sql
-- Schema: unchanged
CREATE TABLE puzzle_tags (
    content_hash TEXT NOT NULL REFERENCES puzzles(content_hash),
    tag_id       INTEGER NOT NULL,
    PRIMARY KEY (content_hash, tag_id)
);
-- Query: "puzzles with ladder AND ko"
SELECT p.* FROM puzzles p
WHERE p.content_hash IN (
    SELECT content_hash FROM puzzle_tags
    WHERE tag_id IN (12, 34)
    GROUP BY content_hash
    HAVING COUNT(DISTINCT tag_id) = 2
);
```

| Criterion | Assessment |
|-----------|------------|
| Adding new tag | Add rows to `puzzle_tags`. No schema change. |
| AND/OR queries | AND via HAVING trick (working today). OR via `IN()`. |
| Storage at 750K puzzles (~2.1M tag rows) | ~40 MB junction table (content_hash TEXT × 2.8 avg tags). |
| Browser query time | <5ms at 9K; estimated 20-50ms at 750K for complex filtered counts. |
| Incremental INSERT | Straightforward: `INSERT INTO puzzle_tags (hash, tag_id)` per tag. |
| Schema migration on tag add | None required. |
| Code change on tag add | None. Tags loaded from `config/tags.json` at runtime. |

### Approach B: Boolean Columns on `puzzles` Table

```sql
-- Schema: 28 new columns
ALTER TABLE puzzles ADD COLUMN tag_10 INTEGER DEFAULT 0; -- life-and-death
ALTER TABLE puzzles ADD COLUMN tag_12 INTEGER DEFAULT 0; -- ko
-- ... 26 more ...
ALTER TABLE puzzles ADD COLUMN tag_82 INTEGER DEFAULT 0; -- fuseki

-- Query: "puzzles with ladder AND ko"
SELECT * FROM puzzles WHERE tag_34 = 1 AND tag_12 = 1;
```

| Criterion | Assessment |
|-----------|------------|
| Adding new tag | **Requires schema migration**: `ALTER TABLE ADD COLUMN`. Rebuilds entire DB. |
| AND/OR queries | Trivially simple: `WHERE tag_34 = 1 AND tag_12 = 1`. |
| Storage at 750K puzzles | +28 bytes/row (1 byte per boolean) = ~21 MB. Slightly smaller than junction. |
| Browser query time | Faster single-table scans. No JOIN overhead. ~2-10ms at 750K. |
| Incremental INSERT | Must set all 28 tag columns per puzzle INSERT. Column list grows with tags. |
| Schema migration on tag add | **Breaking change**: new column in `puzzles`, new column in INSERT statements, new column in `PuzzleEntry` dataclass. |
| Code change on tag add | Backend `db_builder.py`, `db_models.py`, `seed_sample_db.py`, frontend `PuzzleRow` type, `puzzleQueryService.ts` queries — all need updates. |

### Approach C: Bitfield INTEGER Column

```sql
-- Schema: single column
ALTER TABLE puzzles ADD COLUMN tag_bits INTEGER DEFAULT 0;
-- tag_10 = bit 0, tag_12 = bit 1, tag_14 = bit 2, ...

-- Query: "puzzles with ladder (bit 5) AND ko (bit 1)"
SELECT * FROM puzzles WHERE (tag_bits & 34) = 34;  -- 34 = (1<<5) | (1<<1)
```

| Criterion | Assessment |
|-----------|------------|
| Adding new tag (up to 63) | Just assign next bit. No schema change. |
| AND/OR queries | Bitwise AND/OR. Fast but non-standard, hard to read. |
| Storage at 750K puzzles | +8 bytes/row = ~6 MB. Most compact. |
| Browser query time | Single column check. ~2ms at 750K. |
| Schema migration on tag add | None (up to 63 tags). |
| Code change on tag add | Bit position mapping in config. Moderate complexity. |
| Downsides | Not human-readable. `EXPLAIN` is opaque. Counting tags per puzzle requires `popcount`. No SQLite built-in popcount. |

---

## 5. Comparison Table

| R-ID | Criterion | A: Many-to-Many (current) | B: Boolean Columns | C: Bitfield |
|------|-----------|--------------------------|--------------------| ------------|
| C-1 | Schema flexibility | Best: no migration | Worst: migration per tag | Good to 63 tags |
| C-2 | Query simplicity | Moderate (HAVING trick) | Best (direct WHERE) | Moderate (bitwise) |
| C-3 | AND intersection | Correct but complex | Trivial | Trivial |
| C-4 | OR union | `tag_id IN (...)` | `tag_X = 1 OR tag_Y = 1` | `(bits & mask) != 0` |
| C-5 | Tag count aggregation | `GROUP BY tag_id` (natural) | 28 separate COUNTs (verbose) | Requires bit extraction |
| C-6 | Cross-tab (tag × level) | Natural JOIN + GROUP BY | 28× UNION or CASE expressions | Very complex |
| C-7 | Storage at 750K | ~40 MB junction | ~21 MB boolean overhead | ~6 MB single column |
| C-8 | Browser perf at 750K | 20-50ms complex | 2-10ms simple | 2-5ms |
| C-9 | Code coupling to tag list | None (config-driven) | Tight (every tag = column) | Medium (bit mapping) |
| C-10 | Incremental INSERT | Simple: N separate rows | 1 row, 28+ columns | 1 row, 1 column |
| C-11 | Index support | Composite PK + tag_id index | Per-column indexes (28!) | Single column (limited) |
| C-12 | getTagCounts() | 1 query, natural | 28 separate COUNT(CASE) | Complex bit extraction |
| C-13 | getFilterCounts() | Working today (R-20) | Would need 28 CASE/SUM cols | Very difficult |
| C-14 | Yen-Go principle: config-driven | Full compliance | Violates: hardcoded columns | Partial compliance |

---

## 6. YQ and YX Field Storage Assessment

### Current YQ Storage

| R-ID | Field | In DB-1? | Filterable? |
|------|-------|----------|-------------|
| R-24 | `q` (quality level 0-5) | **Yes** — `puzzles.quality` INTEGER column | Yes: `WHERE quality >= 3` |
| R-25 | `rc` (refutation count) | **No** | No |
| R-26 | `hc` (human comment level 0-2) | **No** | No |
| R-27 | `ac` (AI completion level 0-3) | **No** | No |

**Assessment**: Only `q` is extracted. The sub-fields `rc`, `hc`, `ac` are in the SGF `YQ` string but not in DB-1.

### Current YX Storage

| R-ID | Field | In DB-1? | Column | Filterable? |
|------|-------|----------|--------|-------------|
| R-28 | `d` (depth) | **Yes** | `cx_depth` | Yes: `WHERE cx_depth >= 2` |
| R-29 | `r` (refutations) | **Yes** | `cx_refutations` | Yes |
| R-30 | `s` (solution_len) | **Yes** | `cx_solution_len` | Yes |
| R-31 | `u` (unique_resp) | **Yes** | `cx_unique_resp` | Yes |
| R-32 | `w` (width, optional) | **No** | Not stored | No |
| R-33 | `a` (avg refutation depth, optional) | **No** | Not stored | No |

**Assessment**: The 4 core YX fields are fully decomposed into separate indexed columns — the right design. The optional fields `w` and `a` are not stored; they can be added as columns later or put in `attrs` JSON.

### `attrs` JSON Column

| R-ID | Fact |
|------|------|
| R-34 | `attrs TEXT DEFAULT '{}'` exists on both `puzzles` and `collections` tables. |
| R-35 | Currently **always empty `{}`** in production (no code populates it). |
| R-36 | Designed as an escape hatch for future fields without schema migration. |
| R-37 | Filterable via `json_extract(attrs, '$.ko_context')` but NOT indexable efficiently. |

---

## 7. Future Extensibility

### Scenario: Add new tag "snapback" (already exists, but as example of any new tag)

| Approach | Steps Required |
|----------|----------------|
| A: Many-to-many | 1. Add tag to `config/tags.json` with new ID. 2. Pipeline re-tags puzzles. 3. INSERT rows into `puzzle_tags`. **Zero schema changes.** |
| B: Boolean columns | 1. Add tag to config. 2. `ALTER TABLE puzzles ADD COLUMN tag_NN`. 3. Update `db_builder.py` INSERT statement. 4. Update `PuzzleEntry` dataclass. 5. Update frontend `PuzzleRow` type. 6. Update all query functions. **6+ file changes.** |
| C: Bitfield | 1. Add tag to config with bit position. 2. Update bit-mapping config. **Moderate.** |

### Scenario: Add YQ sub-field "ai_verified" for filtering

| Approach | Steps |
|----------|-------|
| Add column | `ALTER TABLE puzzles ADD COLUMN yq_ac INTEGER DEFAULT 0`. Add to INSERT. Frontend gains `WHERE yq_ac >= 2`. |
| Use attrs | `UPDATE puzzles SET attrs = json_set(attrs, '$.ac', 2)`. Frontend: `json_extract(attrs, '$.ac') >= 2`. Not indexable. |
| **Recommendation** | Add as column if filterable; put in `attrs` if display-only. |

### Scenario: Add "estimated_time_seconds" computed field

| Approach | Steps |
|----------|-------|
| Add column | `ALTER TABLE puzzles ADD COLUMN est_time_s INTEGER`. Natural range filter: `WHERE est_time_s BETWEEN 30 AND 120`. |
| Use attrs | `json_extract(attrs, '$.est_time_s')`. Functional but slow at scale. |
| **Recommendation** | Column — this is a filterable numeric field. |

---

## 8. Risks, License/Compliance Notes, Rejection Reasons

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| RK-1 | Boolean columns (B) violate Yen-Go's config-driven principle. Every new tag requires code changes across 6+ files. | High | Reject Approach B. |
| RK-2 | At 750K puzzles, junction table grows to ~2M rows. Complex filtered tag counts could reach 50ms. | Medium | Acceptable for in-memory. Add covering indexes if needed. |
| RK-3 | Bitfield (C) is brittle when tag IDs are sparse (10, 12, 14... 82). Bit position ≠ tag ID. Adds a mapping layer. | Medium | Reject Approach C — complexity outweighs savings. |
| RK-4 | `attrs` JSON is not indexable. If heavily used for filtering, query times degrade at scale. | Low | Use `attrs` only for display/extensibility. Promote to column when filtering is needed. |
| RK-5 | No license/compliance issues. All approaches use standard SQLite features. | None | N/A |

---

## 9. Planner Recommendations

1. **Keep the many-to-many `puzzle_tags` table (Approach A).** It is the correct design for 28 boolean tags with slow growth, config-driven architecture, and complex aggregation queries (tag counts, cross-tabs). The frontend already has working, correct SQL for AND intersection, OR union, and filtered counts. No changes needed.

2. **YQ/YX storage is correct as-is.** The 4 core YX fields are separate indexed columns (good for range filters). Quality is a separate column (good for `>=` filters). Promote `hc`/`ac` sub-fields to columns only when the frontend needs to filter by them — don't pre-optimize.

3. **Use `attrs` JSON as the escape hatch for new display-only fields** (e.g., `ko_context`, `move_order`, `corner_position`). Promote to a proper column when filtering becomes a requirement. This avoids premature schema migration.

4. **If performance becomes an issue at 750K+**, add a covering index: `CREATE INDEX idx_tags_covering ON puzzle_tags(tag_id, content_hash)` to eliminate table lookups for tag-filtered queries. Do not flatten to boolean columns — the complexity cost far exceeds the performance gain in an in-memory database.

---

## 10. Confidence & Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | **92** |
| `post_research_risk_level` | **low** |
| Notes | High confidence because the current schema is already implemented, tested, and matches standard relational patterns. The tag count (28) is well within many-to-many efficiency thresholds. Performance risk only emerges at 750K+ and is mitigable with indexes. |
