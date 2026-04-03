# Snapshot-Centric Query Architecture — Plan V2

**Last Updated**: 2026-02-22
**Status**: P0–P5 Implemented — Awaiting Review
**Related**: `TODO/multi-dimensional-puzzle-filtering.md`, `TODO/entry-compression-proposal.md`
**Scale Target**: up to 500,000 puzzles within 1 GB GitHub Pages storage
**Migration Strategy**: Big-bang (no backward compatibility required)
**Prerequisite**: Compact numeric entry format (Architecture C) already implemented

---

## 0. Governance, Execution, and Tracking (Mandatory)

### 0.1 Phase-Gate Workflow (Strict Sequence)

Every phase must complete this mandatory gate before the next phase can start:

1. **Implementation complete for phase**
2. **Systems Architect Review**
3. **Fix all architect findings**
4. **Principal Staff Software Engineer Review**
5. **Fix all staff findings**
6. **Gate close: phase marked DONE**

Rules:
- Reviews are **sequential, never parallel**.
- No downstream phase work starts until current phase gate is closed.
- Any reopened finding reverts phase to `IN REVIEW`.

### 0.1.1 Definition of Done per Phase Gate (Objective Pass/Fail)

Each phase must satisfy all criteria in order. Any failed criterion blocks progression.

#### A) Ready for Systems Architect Review

Pass only if all are true:

- Phase scope tasks are implemented and mapped to task IDs in this plan.
- Unit/integration checks for phase scope are green.
- Architecture artifacts are updated (contracts, schemas, and diagrams if changed).
- No unresolved TODO/FIXME in touched phase-scope files.
- Runtime complexity and data-shape impacts are documented for phase scope.

#### B) Ready for Principal Staff Software Engineer Review

Pass only if all are true:

- All architect review findings are resolved and verified.
- New/updated tests cover functional and edge-case behavior introduced by phase.
- Operational constraints are validated (bounded fetch strategy, no all-pages scans).
- Failure-mode behavior is documented and testable (empty intersections, missing metadata, stale cursor).
- Code/doc changes are internally consistent with naming and route contracts.

#### C) Gate Close (Phase DONE)

Pass only if all are true:

- All staff review findings are resolved and verified.
- Phase tracking table row is updated to DONE with review dates and owners.
- Decision records required by the phase are completed (for P0, canonical ADR below).
- No open blocker labeled for that phase.
- Exit criteria evidence is linked (test outputs, review notes, artifacts).

#### D) Fail Conditions (Automatic Reopen)

Any of the following reopens the phase to `IN REVIEW`:

- Regressions detected in phase-owned behaviors.
- New unresolved review finding linked to phase scope.
- Contract drift between plan, schema, and implementation.
- Missing evidence for a previously claimed pass criterion.

### 0.2 Phase Tracking Table

| Phase | Scope | Impl Status | Architect Review | Architect Fixes | Staff Review | Staff Fixes | Gate Status | Owner | Notes |
|------|-------|-------------|------------------|-----------------|-------------|-------------|------------|-------|-------|
| P0 | Naming + contracts + deployment topology | DONE | NOT STARTED | NOT STARTED | NOT STARTED | NOT STARTED | OPEN | Agent | 2026-02-21: terminology doc, topology ADR (repo-static), system-overview updated |
| P1 | Backend snapshot shard writer + pipeline wiring | DONE | DONE | DONE | DONE | DONE | **CLOSED** | Agent | 2026-02-21: shard_models, shard_key, shard_writer, snapshot_builder, quality in id_maps/publish, 119 tests. 2026-02-22: Pipeline wiring complete (V2-T04B/C/D/E). Architect review: 4 blocking findings fixed — (F1) SnapshotValidationError caught in publish.py. (F2) Old snapshot cleanup after activation. (F3) Dead PaginationConfig removed. (F4) compact_entry dict eliminated. Staff review: 1 blocking finding fixed — (S1) Incremental test verifies old snapshot removal. 1641 tests pass. |
| P2 | Frontend query planner + loaders | DONE | DONE | DONE | NOT STARTED | NOT STARTED | OPEN | Agent | 2026-02-21: P2 impl (141 tests). 2026-02-22: Architect review PASS (no blocking findings). Big-bang 3-silo removal: deleted level-loader, tag-loader, pagination, usePaginatedPuzzles, useMasterIndexes, useFilterState + 7 old test files. Rewrote puzzleLoaders to use shard system. Stripped indexes.ts, puzzleLoader.ts, collectionService.ts. Fixed all page imports. |
| P3 | Routing + canonical URL normalization | DONE | DONE | DONE | NOT STARTED | NOT STARTED | OPEN | Agent | 2026-02-22: P3 impl (77 tests). New route system: /contexts/{dim}/{slug} for training/technique/collection/quality, /modes/{name} for daily/random/rush. Canonical URL module with compact filter keys (l,t,c,q), offset, id. useCanonicalUrl + useShardFilters hooks. Rewrote app.tsx router. Reconnected all 5 P3-stubbed pages. Deleted useFilterParams. Updated AppHeader for client-side nav. Architect review: 3 blocking findings fixed — (F1) canonicalize now preserves unknown params per §3.2. (F2) useCanonicalUrl setters use refs to eliminate stale closures + stabilize callback identity. (F3) CollectionViewPage handlePuzzleChange uses useCanonicalUrl setOffset/setId instead of manual URL writes. Also fixed: (F4) RushBrowsePage masterLoaded=false until real counts wired. (F6) Static import for tagSlugToId in CollectionViewPage. |
| P4 | Reconcile/rollback + atomic publish switch + pipeline wiring | DONE | DONE | DONE | DONE | DONE | **CLOSED** | Agent | 2026-02-22: P1 wiring + P4 combined. SnapshotBuilder wired into PublishStage.run() with incremental entry merge. PaginationWriter removed from publish. ShardWriter assigns collection n. Entry reconstruction from level shards. Atomic writes for pointer/manifest/state. Rollback refactored to snapshot rebuild. Cleanup updated for snapshots. Architect review 2026-02-22: PASS (4 findings fixed). Staff review 2026-02-22: PASS (1 finding fixed). 1641 tests pass. |
| P5 | Legacy code removal + full validation | DONE | DONE | DONE | DONE | DONE | **CLOSED** | Agent | 2026-02-22: Frontend old loaders removed in P2. Backend: PaginationWriter + pagination_models + PaginationConfig deleted. 6 old test files deleted. core/__init__.py re-exports cleaned. Stale comments updated. Architect review 2026-02-22: PASS. Staff review 2026-02-22: PASS (stale comment fixed). 1641 tests pass. |

### 0.3 Task Tracking Table

| Task ID | Description | Phase | Status | Reviewer Blocker | Depends On |
|--------|-------------|-------|--------|------------------|------------|
| V2-T01 | Terminology + schema contract update | P0 | DONE | None | - |
| V2-T02 | Deployment topology decision record | P0 | DONE | None | - |
| V2-T03 | Snapshot manifest + shard models | P1 | DONE | None | V2-T01 |
| V2-T04 | Shard writer + pairwise matrix generation | P1 | DONE | None | V2-T03 |
| V2-T05 | Unassigned bucket support (`none`) | P1 | DONE | None | V2-T03 |
| V2-T06 | Frontend query planner with bounded complexity | P2 | DONE | None | V2-T04 |
| V2-T07 | Exact vs derived count tier UX contract | P2 | DONE | None | V2-T06 |
| V2-T08 | Canonical router + URL normalization | P3 | DONE | None | V2-T06 |
| V2-T09 | Atomic snapshot switch + cache invalidation | P4 | DONE | None | V2-T04 |
| V2-T10 | Reconcile/rollback shard rebuild strategy | P4 | DONE | None | V2-T04 |
| V2-T11 | Big-bang removal of old view system | P5→P2 | DONE | None | V2-T08 |
| V2-T12 | E2E verification at scale envelopes | P5 | NOT STARTED | None | V2-T11 |
| V2-T13 | Quality dimension (`q`) rollout | P1/P2 | DONE | None | V2-T04 |
| V2-T14 | Page navigator + jump-to-puzzle component | P2 | DONE | None | V2-T06 |

**Tasks added during architect/staff review:**

| Task ID | Description | Phase | Status | Reviewer Blocker | Depends On |
|--------|-------------|-------|--------|------------------|------------|
| V2-T03B | Shard key computation module | P1 | DONE | None | V2-T03 |
| V2-T06A | Manifest + shard meta loader service | P2 | DONE | None | V2-T04 |
| V2-T06B | Shard page loader + entry decoder | P2 | DONE | None | V2-T06A |
| V2-T04B | Wire SnapshotBuilder into PublishStage + incremental entry merge | P1/P4 | DONE | None | V2-T04 |
| V2-T04C | Remove PaginationWriter call from PublishStage | P1/P4 | DONE | None | V2-T04B |
| V2-T04D | ShardWriter collection `n` assignment during page gen | P1/P4 | DONE | None | V2-T04 |
| V2-T04E | Entry reconstruction from existing level shards | P1/P4 | DONE | None | V2-T04 |
| V2-T10B | Update cleanup.py for snapshot-aware output | P4 | DONE | None | V2-T04C |
| V2-T10C | Update StageContext with snapshot paths | P4 | DONE | None | V2-T04B |
| V2-T16 | Delete PaginationWriter + pagination_models + old tests | P5 | DONE | None | V2-T10 |

---

## 1. Terminology Decision: “Snapshots” vs “Fragments”

### Decision

Use **Snapshot** as the primary architectural term.

- **Snapshot** = immutable release boundary of the searchable puzzle corpus.
- **Shard** = physical data unit inside a snapshot (previously called fragment).

### Rationale

- “Snapshot” better communicates evolution, rollback, de-evolution, and deterministic publishing.
- “Fragment” is still useful as an internal implementation term but not ideal as the product-facing architecture name.
- This plan adopts: **Snapshot-Centric Query Architecture** with **query shards**.

---

## 2. Executive Summary

Replace the current 3-silo view system (`by-level/`, `by-tag/`, `by-collection/`) with immutable snapshot releases that contain precomputed query shards for 1D and 2D intersections. The frontend uses a deterministic query planner to resolve filters to the most selective shard set using compact URL keys.

Critical-gap fixes included in V2:
- Mandatory snapshoting (no deferred snapshot model)
- Explicit support for missing metadata via `none` buckets
- Exact count guarantees for 1D/2D and explicit derived-count policy for higher dimensions
- Canonical URL normalization rules for deep-link consistency
- Atomic publish switch to avoid mixed-state reads
- Cache invalidation keyed by snapshot/build checksums
- Complexity contract clarified: bounded O(k) fetches, not blanket O(1) claims
- Quality dimension (`q`) included in V2 backend and frontend scope

---

## 3. Architecture Contracts (V2)

### 3.1 Directory Layout (Shared SGF + Snapshot Views)

SGF files are **shared** at the top level — not duplicated per snapshot. They are content-addressed (filename = content hash) and append-only, so they are safe to share across snapshot versions. Snapshot directories contain only the manifest and query shard views.

```
yengo-puzzle-collections/
  sgf/                                    # SHARED — not snapshot-scoped
    0001/
      abcdef1234567890.sgf
    0002/
      fc38f029a1b2c3d4.sgf
  snapshots/
    {snapshot_id}/
      manifest.json
      views/
        .shard-state.json
        shards/
          l120/
            meta.json
            page-001.json
          l120-t36/
            meta.json
            page-001.json
          c6-l120/
            meta.json
            page-001.json
  active-snapshot.json
```

`active-snapshot.json` is the single pointer updated after successful publish validation.

#### 3.1.1 Frontend Bootstrap Sequence

GitHub Pages is a static CDN — there is no runtime atomic file swap. The "atomic switch" means:
1. Pipeline builds the new snapshot fully in a staging directory.
2. Pipeline validates checksums and cardinality invariants.
3. Pipeline writes `active-snapshot.json` with the new snapshot ID.
4. All artifacts are committed and pushed in a single git push.

**Frontend boot sequence (2 network hops before first shard load):**

```
1. App loads → fetch active-snapshot.json → get snapshot_id
2. Construct base path: snapshots/{snapshot_id}/
3. Fetch manifest.json from that base path
4. Query planner resolves shard key from route + filters
5. Fetch shard meta.json (if needed for cascading counts)
6. Fetch shard page-NNN.json
```

**Mitigation for the extra round-trip:**
- `active-snapshot.json` is tiny (~50 bytes) — cache with short TTL (e.g., 60s).
- Alternative: embed `snapshot_id` into the HTML at Vite build time (`import.meta.env.VITE_SNAPSHOT_ID`). Eliminates hop 1 entirely but requires rebuild on every publish. Decision deferred to V2-T02 (deployment topology).

**Why SGF is shared (not snapshot-scoped):**

| Concern | Shared SGF | Snapshot-scoped SGF |
|---------|-----------|--------------------|
| Storage at 500K | 240 MB (once) | 240 MB × N snapshots |
| Rollback safety | Content-addressed: old SGF files are never modified or deleted | Each snapshot is self-contained |
| Publish workflow | SGF written to `sgf/` first, then snapshot views built referencing them | SGF copied into snapshot dir |
| Reclassification | SGF file stays at same path; only shard entries change | SGF file stays at same path |
| Garbage collection | Orphaned SGFs (not referenced by active snapshot) can be cleaned periodically | Delete entire old snapshot dir |

**Invariant:** Every `p` field in a shard entry (e.g., `"0001/fc38f029"`) resolves to `sgf/0001/fc38f029.sgf` — a path independent of snapshot ID. The frontend constructs SGF URLs without snapshot scoping.

### 3.2 URL Grammar (Canonical)

```
/contexts/{dimension}/{slug}[?l=...][&t=...][&c=...][&q=...][&match=all|any][&offset={n}][&id={puzzleId}]
```

There is **no `/search` route** and **no `snapshot` URL param**. Every query is anchored to a context (a primary dimension). The active snapshot is an implementation detail resolved at boot time (§3.1.1), not a URL-visible concept.

#### 3.2.0 Dimension Path Names and Value Format

| URL dimension | Data dimension | Path value format | Example URL |
|--------------|---------------|-------------------|-------------|
| `training` | level | **slug** (human-readable) | `/contexts/training/beginner` |
| `technique` | tag | **slug** (human-readable) | `/contexts/technique/net` |
| `collection` | collection | **slug** (human-readable) | `/contexts/collection/cho-chikun-life-death-elementary` |
| `quality` | quality | **slug** (human-readable) | `/contexts/quality/standard` |

**Path uses slugs; query params use numeric IDs.** This gives human-readable URLs for browsing while keeping filter params compact:

```
/contexts/training/beginner?t=36,10&q=3&offset=42&id=fc38f029
```

**Frontend resolution:** slug → numeric ID via `configService` lookup → shard key construction (`beginner` → `120` → `l120`).

URL semantics:
- `offset` is the zero-based navigation position in the resolved filtered result set.
- `id` is the puzzle identifier for the currently displayed board puzzle. It is appended to the context URL when a puzzle is being shown on the board.
- Deterministic canonical base = route + sorted filter params + `offset`; `id` is required when a specific puzzle is being shown on board.

**Why no standalone `/puzzles/{id}` or `/search?id=` route:**
- Puzzle IDs are content hashes — no human can guess or type them.
- Users always enter via a context dimension (collection, technique, training level).
- Searching all shards for a puzzle ID is O(N) — does not scale at 500K puzzles.
- The `&id=` param on a context route is sufficient: it identifies the board puzzle *within* the already-resolved shard context.

URL contract decisions (locked):
- All canonical routes are context-based: `/contexts/{dimension}/{slug}`.
- Path segments use **slugs** (human-readable). Query filter params use **numeric IDs** (compact).
- No standalone `/puzzles/{id}` canonical route. No `/search` route. No `snapshot` param.
- `id` is appended as query param on context routes when board puzzle identity must be explicit.
- `id` value must use the stable puzzle identifier format defined by schema contract; do not expose raw storage hashes as public-facing URL identifiers.
- `offset` may be omitted when not required for shareability; when present, it is part of deterministic replay within the active snapshot.
- Compact keys are mandatory for dimension filters: `l`, `t`, `c`, `q`.

Canonicalization rules:
- query params sorted deterministically
- duplicate IDs removed and sorted ascending
- unknown future params preserved (pass-through)
- normalized URL written back via `replaceState`

### 3.2.1 Navigation Model: `offset` (Not Page Cursor)

The URL uses `offset` — the **zero-based puzzle position** in the resolved shard result set — not a page-level cursor.

**Why offset, not page cursor:**

| Concern | `cursor=p{N}` (page-level) | `offset={n}` (puzzle-position) |
|---------|---------------------------|-------------------------------|
| Human meaning | "I'm on page 8" | "I'm looking at puzzle 3756" |
| Page-size coupling | URL breaks if `page_size` changes between snapshots | Stable across page-size changes |
| Deep-link precision | Points to a page of 500 entries | Points to exact puzzle position |
| Frontend computation | Trivial | `page = floor(offset / page_size) + 1`, `index = offset % page_size` |
| Shareable across snapshots | Position within page may shift | Position within shard may shift (both are snapshot-scoped) |

**Frontend page resolution from offset:**

```
offset = 3756
page_size = 500 (from manifest)
page_number = floor(3756 / 500) + 1 = 8
index_within_page = 3756 % 500 = 256
fetch: shards/l120/page-008.json → entry at position 256
```

**When offset is omitted:** URL represents the shard/filter combination without a specific puzzle position (e.g., landing on the first puzzle of page 1). Offset is written to the URL only when a specific puzzle is being displayed.

**`id` param relationship:** When `offset` and `id` are both present, they are redundant by design — `id` is the puzzle identifier at that offset.

**Cross-snapshot mismatch handling (bounded):** If a snapshot changes and the puzzle at the recorded `offset` differs from `id`, the frontend:
1. Checks current page and adjacent pages (±2 pages, max 5 pages scanned).
2. If `id` is found within that window → update `offset` to the new position.
3. If `id` is NOT found within the window → show "Puzzle moved or removed" message, reset to `offset=0`.
4. **Never** scan the entire shard — this would violate §4.1's bounded-fetch contract.

### 3.3 Missing Metadata Policy (Required)

All dimensions include explicit `none` bucket IDs:
- `level=0` (unassigned level)
- `tag=0` (untagged)
- `collection=0` (no collection)
- `quality=0` (unassigned quality)

This ensures every puzzle is queryable even when only partial metadata exists.

**Materialization rule:** `none` bucket shards (e.g., `l0`, `t0`) are only written to disk if their count > 0. The `null_buckets` declaration in the manifest always exists (for schema completeness), but empty shards are never generated. Given current pipeline guarantees (every puzzle has ≥1 level and ≥1 tag), `l0` and `t0` will typically be empty and skipped. `c0` and `q0` will have real entries (most puzzles have no collection; quality is not yet assigned).

---

## 4. Performance Contract (Precise)

### 4.1 Runtime Complexity

- **Puzzle SGF fetch**: network O(1), compute O(1) — path `sgf/{batch}/{hash}.sgf` resolved from shard entry `p` field
- **Single-select 1D/2D query**: network O(1) shard fetch
- **Multi-select query**: network O(k) shard fetches for selected values; compute O(k + merge)
- **No runtime path may require loading all pages of a large corpus**
- **No puzzle-ID search across shards** — puzzle identity is always resolved within a context-anchored shard

Where `k` is number of resolved shards chosen by planner.

### 4.2 Count Accuracy Contract

- 1D and 2D counts: **exact**
- 3D+ counts: either
  - exact from optional hot 3D materializations, or
  - explicitly labeled **derived** (never shown as exact)

No silent approximation.

### 4.4 Failure Modes

| Failure | Frontend Behavior |
|---------|------------------|
| `active-snapshot.json` fetch fails | Show offline/error screen with retry button. No shard navigation possible. |
| `manifest.json` fetch fails | Same as above — manifest is required for all shard resolution. |
| Shard `meta.json` fetch fails | Cascading filter counts unavailable. Show filters without counts. Shard pages still loadable. |
| Shard page `page-NNN.json` 404 | Show "Page unavailable" message on that page. Adjacent pages still navigable. |
| SGF file missing (`sgf/{batch}/{hash}.sgf` 404) | Show "Puzzle unavailable" placeholder in puzzle player. Skip entry in navigation sequence. |
| `offset` exceeds shard `count` | Clamp to last valid offset: `min(offset, count - 1)`. |
| `offset` + `id` mismatch (snapshot changed) | Bounded search: check current page ±2 pages. If not found, reset to offset=0. |
| Empty shard (0 puzzles match filter) | Show "No puzzles match" with suggested alternative filters derived from parent shard meta distributions. |
| Unknown dimension slug in URL path | Show 404 page. |
| Unknown filter param in URL query | Ignore and preserve (pass-through for future dimensions). |

### 4.3 Query Planner Contract

Planner selects shard strategy by strict decision tree:

```
1. Compute exact shard key from active filters (e.g., {level:120, tag:36} → "l120-t36")
2. if manifest.shards[key] exists → DIRECT: fetch that shard (O(1))
3. else if multi-select → MERGE: fetch each single-value shard in parallel, merge client-side (O(k))
4. else → FALLBACK: fetch nearest broader shard, post-filter client-side (O(1) fetch + O(n) filter)
```

Tie-breaker for fallback: prefer the shard with lowest entry count (from manifest `shards[key].count`).

The planner is a simple lookup + fallback chain, not an optimizer. The shard count at current taxonomy is bounded (~2,000–3,000 non-empty 2D shards), so exhaustive candidate evaluation is unnecessary.

> **Deferred:** If shard counts exceed 10,000+ (e.g., 5+ dimensions with 50+ values each), revisit with a cost-function-based optimizer. Until then, the 3-step decision tree is sufficient.

---

## 5. Storage Budget (500K Puzzles)

| Component | Raw Size | Notes |
|-----------|--------:|-------|
| SGF files (500K × 480 B avg) | 240 MB | **Shared** — single copy at `sgf/`, not per-snapshot |
| Snapshot shard pages (1D + 2D compact) | ~340 MB | Array encoding + context elision (per active snapshot) |
| Snapshot manifest + shard metas | ~2 MB | Scales with taxonomy |
| Shard state + inventory | < 2 MB | Tiny |
| Operational logs in deployed site | 0 MB | Keep outside deployed artifact |
| **Total** | **~584 MB** | Within 1 GB target |

**File count budget (500K puzzles):**

| Component | File Count | Notes |
|-----------|----------:|---------|
| SGF files | 500,000 | In ~250 batch dirs (2000/dir) |
| Shard page files | ~8,000 | 1D + non-empty 2D shards, variable pages each |
| Shard meta files | ~3,000 | One per non-empty shard |
| Manifest + state | 3 | `active-snapshot.json`, `manifest.json`, `.shard-state.json` |
| **Total** | **~511,000** | Within GitHub Pages soft limit (~100K tracked, no hard cap for deployed) |

**Storage scaling note:** Because SGF is shared (not snapshot-scoped), multiple concurrent snapshots add only ~342 MB each (views + manifest), not another 240 MB of SGF. However, on GitHub Pages the recommendation is to keep **only 1 active snapshot deployed** and retain prior snapshots in git history only (rollback = checkout prior commit's snapshot views). This keeps deployed size at ~584 MB even at 500K scale.

---

## 6. Snapshot Shard Schema

### 6.1 Shard Naming (Deterministic)

Shard key = sorted dimension prefixes joined by `-`:

| Prefix | Dimension | Example |
|--------|-----------|---------|
| `l` | level | `l120` |
| `t` | tag | `t36` |
| `c` | collection | `c6` |
| `q` | quality | `q3` |
| `d` | depth (future) | `d3` |

### 6.2 Page Format (Array Compact)

All shard pages use array-of-arrays encoding with a `schema` header declaring field order. Context elision removes fields that are implicit from the shard key.

#### 6.2.1 Level 1D Shard (`l120/page-001.json`)

Level is elided — implicit from shard key `l120`.

```json
{
  "type": "shard",
  "shard": "l120",
  "page": 1,
  "schema": ["p", "t", "c", "x", "q"],
  "entries": [
    ["0001/fc38f029", [10],     [6, 47], [1, 2, 11, 1], 3],
    ["0001/8f76cef5", [10, 36], [6],     [1, 2, 14, 1], 2],
    ["0002/a4c9e312", [36, 60], [],      [2, 3, 19, 2], 1]
  ]
}
```

Note: `c` may be `[]` (no collection). `t` always has at least one entry (pipeline guarantees ≥1 tag; `[0]` if truly untagged via `none` bucket). `q` is the quality level (1–5; 0 if unassigned).

#### 6.2.2 Tag 1D Shard (`t36/page-001.json`)

Tag is NOT elided — puzzles have multiple tags, so `t` array retains all tags for client-side multi-tag filtering.

```json
{
  "type": "shard",
  "shard": "t36",
  "page": 1,
  "schema": ["p", "l", "t", "c", "x", "q"],
  "entries": [
    ["0001/fc38f029", 120, [10, 36], [6, 47], [1, 2, 11, 1], 3],
    ["0003/bb91f004", 160, [36, 60], [],       [3, 1,  8, 1], 2]
  ]
}
```

#### 6.2.3 Level×Tag 2D Shard (`l120-t36/page-001.json`)

Level is elided (implicit from shard key). `t` retains all tags.

```json
{
  "type": "shard",
  "shard": "l120-t36",
  "page": 1,
  "schema": ["p", "t", "c", "x", "q"],
  "entries": [
    ["0001/fc38f029", [10, 36], [6, 47], [1, 2, 11, 1], 3],
    ["0001/8f76cef5", [36],     [6],     [1, 2, 14, 1], 2]
  ]
}
```

#### 6.2.4 Collection 1D Shard (`c6/page-001.json`)

Collection shards include the `n` field — the **1-indexed sequence number** assigned at publish time. This provides deterministic "Jump to puzzle #N" navigation within collections.

```json
{
  "type": "shard",
  "shard": "c6",
  "page": 1,
  "schema": ["p", "l", "t", "c", "x", "q", "n"],
  "entries": [
    ["0001/fc38f029", 120, [10],     [6, 47], [1, 2, 11, 1], 3, 1],
    ["0001/8f76cef5", 120, [10, 36], [6, 47], [1, 2, 14, 1], 2, 2],
    ["0002/d7e45a01", 130, [36, 60], [6],     [2, 1, 15, 1], 1, 3]
  ]
}
```

`n` is unique per collection, contiguous (no gaps), and 1-indexed. **`n` is repacked on every publish** — when puzzles are added or removed from a collection, all `n` values are reassigned contiguously (1, 2, 3, ..., count). This means `n` is NOT stable across publishes; saved references to "puzzle #347" may point to a different puzzle after a new publish. This is acceptable because:
- Collection URLs use `offset` (not `n`) for position within the filtered shard.
- `n` is a display/navigation aid ("puzzle 42 of 900"), not a persistent identifier.
- The `&id=` param on the URL persists the actual puzzle identity across publishes.

#### 6.2.5 Collection×Level 2D Shard (`c6-l120/page-001.json`)

Level is elided. Collection `n` is retained for navigation. `n` is the **global collection position** (from the full `c6` shard), not the position within this filtered subset.

```json
{
  "type": "shard",
  "shard": "c6-l120",
  "page": 1,
  "schema": ["p", "t", "c", "x", "q", "n"],
  "entries": [
    ["0001/fc38f029", [10],     [6, 47], [1, 2, 11, 1], 3, 1],
    ["0001/8f76cef5", [10, 36], [6, 47], [1, 2, 14, 1], 2, 2]
  ]
}
```

Note: In `c6-l120`, puzzle with `n=1` is collection puzzle #1 globally. If the full `c6` shard has 900 puzzles and only 854 are level 120, the 2D shard contains 854 entries with non-contiguous `n` values (e.g., 1, 2, 4, 5, 8...). "Jump to #N" from a filtered collection view navigates to the full `c6` context.
```

#### 6.2.6 Quality 1D Shard (`q3/page-001.json`)

Quality is elided. Full entry with all other dimensions.

```json
{
  "type": "shard",
  "shard": "q3",
  "page": 1,
  "schema": ["p", "l", "t", "c", "x"],
  "entries": [
    ["0001/fc38f029", 120, [10, 36], [6, 47], [1, 2, 11, 1]],
    ["0003/bb91f004", 160, [36, 60], [],       [3, 1,  8, 1]]
  ]
}
```

Note: `q` is elided in quality-keyed shards (implicit from shard key `q3`). In all other shards, `q` is an explicit field in the entry schema.
```

### 6.3 Manifest Schema (Minimum)

The manifest is the global table of contents. It lists all shards with their count, page count, and checksum. It does **not** contain cross-tabulation counts (those live in shard metas — §6.4).

```json
{
  "version": "2.0",
  "snapshot_id": "20260221-a1b2c3d4",
  "build_id": "20260221-a1b2c3d4",
  "dimensions": ["level", "tag", "collection", "quality"],
  "null_buckets": {"level": 0, "tag": 0, "collection": 0, "quality": 0},
  "page_size": 500,
  "total_puzzles": 500000,
  "shards": {
    "l120":     {"count": 55000, "pages": 110, "checksum": "a3f8..."},
    "l120-t36": {"count": 31000, "pages": 62,  "checksum": "b7d2..."},
    "c6":       {"count": 900,   "pages": 2,   "checksum": "e4c1..."},
    "c6-l120":  {"count": 854,   "pages": 2,   "checksum": "f9a3..."},
    "q3":       {"count": 15000, "pages": 30,  "checksum": "c2e8..."}
  },
  "count_tiers": {"1d": "exact", "2d": "exact", "3d_plus": "derived"}
}
```

**Manifest size at scale:** At 500K puzzles with 9 levels × 28 tags × 159 collections × 5 quality levels, the theoretical 2D shard count is ~7,100. However, many intersections are empty. Only non-empty shards are listed. Estimated non-empty 2D shards: ~2,000–3,000. Manifest size: ~120–180 KB.

**Materialization policy:** 2D shards are generated only when intersection count ≥ 1. Empty intersections (e.g., `c147-q5` with 0 puzzles) produce no shard directory and no manifest entry.

**Why no TOC in manifest:** Cross-tabulation counts (e.g., "level 120 has 31,000 puzzles with tag 36") are stored in shard metas (§6.4), not the manifest. This avoids data duplication and consistency risk. The frontend loads the relevant shard meta lazily when cascading filter counts are needed.
```

### 6.4 Shard Meta Schema

Each shard directory contains a `meta.json` with summary statistics and per-dimension distribution maps. Shard metas are the **single source of truth** for cascading filter counts — the manifest does not duplicate this data.

```json
{
  "shard": "l120",
  "count": 55000,
  "pages": 110,
  "page_size": 500,
  "checksum": "a3f8c9d1",
  "schema": ["p", "t", "c", "x", "q"],
  "distributions": {
    "tag":        { "10": 22000, "36": 31000, "60": 500, "12": 800, "0": 700 },
    "collection": { "6": 854, "47": 854, "21": 40, "0": 53252 },
    "quality":    { "1": 5000, "2": 30000, "3": 15000, "0": 5000 }
  }
}
```

**`schema` in meta (not in pages):** The `schema` field declares the field order for all page entries in this shard. Page files do not repeat the schema — they reference the same order declared in `meta.json`. This saves ~30 bytes per page × ~10K pages = ~300 KB at scale.

**Usage:** When a user is viewing shard `l120` and selects tag filter `t36`, the frontend reads `meta.distributions.tag["36"] = 31000` to display the cascading count without fetching the `l120-t36` shard pages.

**Distribution keys:** Every dimension NOT part of the shard key gets a distribution map. A level shard has tag/collection/quality distributions. A 2D shard (`l120-t36`) has only collection/quality distributions.

**`none` bucket:** The `"0"` key in each distribution represents puzzles with no assignment in that dimension (e.g., `"0": 53252` means 53,252 puzzles in `l120` with no collection).

**Manifest vs shard meta:** The manifest TOC provides global cross-tabulation counts across all shards. Shard meta provides local distributions within a single shard. Both are exact for 1D and 2D queries.

---

## 7. Data Churn and Evolution Strategy

| Event | V2 Behavior |
|-------|-------------|
| Puzzle add/remove/reclassify | Rebuild affected shards and TOC; publish new snapshot |

The shard writer maintains a **reverse index** (`puzzle_id → [shard_keys]`) in shard state. On reclassification (e.g., level change 120→130), the system identifies all affected shards in O(1) without scanning all shards: remove entry from old shards (`l120`, `l120-t*`, `c*-l120`), add to new shards (`l130`, `l130-t*`, `c*-l130`), rebuild affected shard pages and metas.
| Rollback/de-evolution | Rebuild shards with corrected input under new snapshot, or restore prior snapshot views from git history. SGF files are unaffected (shared, append-only, content-addressed). |
| New dimension introduction | Add dimension catalog + 1D/2D shards, no route redesign |
| Taxonomy changes | Regenerate shards under new snapshot; old snapshot preserved |

### Atomic Publish Switch (Required)

1. Build snapshot fully in staging output
2. Validate checksums + cardinality invariants
3. Write snapshot artifacts
4. Atomically switch `active-snapshot.json`

No partial-live snapshot states allowed.

---

## 8. Deployment Topology Decision (P0 Required)

Before implementation, lock one of these modes:

1. **Bundled-static mode**: snapshot views + SGF copied into deployed web artifact.
2. **Repo-static mode**: frontend reads directly from repository-hosted static paths.

This plan assumes one canonical mode only. Mixed mode is disallowed.

### 8.1 Embedded ADR-Lite (Topology Lock)

Use this section as the mandatory decision record for P0 when a separate ADR file is not yet created.

Canonical ADR location: `docs/architecture/snapshot-deployment-topology.md`

#### Decision Status

- Status: **PENDING**
- Decision Owner: **TBD**
- Decision Date: **TBD**
- Effective Snapshot Version: **TBD**

#### Decision Options (Choose Exactly One)

1. **Bundled-static mode**
  - Snapshot views + SGF are copied into the deployed frontend artifact.
  - Runtime fetch base is artifact-local.

2. **Repo-static mode**
  - Frontend fetches snapshot views + SGF from repository-hosted static paths.
  - Runtime fetch base is repository/CDN path.

#### Non-Negotiable Acceptance Criteria

- One canonical fetch base only (no dual-path fallback in production).
- `manifest`, `views`, and `sgf` are served from the same topology mode.
- SGF path (`sgf/`) is shared and NOT snapshot-scoped — both modes must resolve `sgf/{batch}/{hash}.sgf` from the same root as snapshot views.
- Cache invalidation strategy is defined for this mode (`snapshot_id` + checksums for views; SGF is content-addressed and immutable, so infinitely cacheable).
- CI/CD explicitly packages only required artifacts for the selected mode.
- Router and URL examples in this plan are validated against the selected mode.

#### Decision Log

| Field | Value |
|------|-------|
| Selected Option | TBD |
| Why this option | TBD |
| Rejected option | TBD |
| Trade-offs accepted | TBD |
| CI/CD changes required | TBD |
| Runtime constants to update | TBD |

#### Phase Gate Rule

P0 cannot be marked DONE until this ADR-lite section is fully completed and signed off in sequence:

1. Systems Architect Review → fixes complete
2. Principal Staff Software Engineer Review → fixes complete

---

## 9. Implementation Tasks (Plan V2)

### P0: Contracts and topology

**V2-T01: Rename architecture contract to snapshot/shard terminology**
- Update docs and symbols (`fragment` → `shard` where external-facing)
- Keep internal aliases only if required during implementation

**V2-T02: Deployment topology decision record**
- Create/update canonical ADR in `docs/architecture/snapshot-deployment-topology.md`
- Confirm where snapshot artifacts are served from in production

### P1: Backend snapshot/shard core

**V2-T03: Snapshot manifest and shard models**
- Create/extend models with `snapshot_id`, `null_buckets`, checksums, count tiers

**V2-T03B: Shard key computation module**
- Core function: given compact entry `{l:120, t:[10,36], c:[6], q:3}` → produce all shard keys: `["l120", "t10", "t36", "c6", "q3", "l120-t10", "l120-t36", "c6-l120", "c6-t10", "c6-t36", "l120-q3", ...]`
- Respect sorted dimension prefix ordering (`c` < `l` < `q` < `t`)
- Handle edge cases: empty `c` (→ `c0`), `none` buckets, single-tag puzzles
- Apply materialization threshold: skip 2D keys for intersections known to be empty (optional optimization)
- Maintain reverse index: `puzzle_id → [shard_keys]` for efficient reclassification
- Unit tests: all fanout combinations, none-bucket entries, multi-tag/multi-collection entries

**V2-T04: Shard writer and pairwise matrix generator**
- Generate 1D + 2D shards and exact pairwise TOC counts

**V2-T05: Unassigned bucket generation**
- Ensure all puzzles map to each dimension via concrete `none` value

**V2-T13A: Quality (`q`) backend rollout**
- Add `quality` to manifest dimension registry and null bucket map.
- Generate `q` 1D shards and selected 2D shards involving `q` per materialization policy.
- Extend TOC/count matrices with quality cross-counts.

### P2: Frontend planner and loaders

**V2-T06: Deterministic query planner**
- Implement 3-step decision tree: direct shard → merge → fallback (§4.3)
- Tie-break by lowest entry count from manifest
- Bounded complexity: O(k) fetches max, no all-pages scans

**V2-T06A: Manifest + shard meta loader service**
- Fetch `active-snapshot.json` on app init → resolve snapshot base path
- Fetch `manifest.json` from snapshot base → cache in memory
- Expose: `getShardInfo(key)` (from manifest), `getShardMeta(key)` (lazy-fetched from shard `meta.json`)
- Handle manifest fetch failure: show offline error with retry button
- Handle stale `active-snapshot.json`: compare cached `snapshot_id` on periodic check

**V2-T06B: Shard page loader + entry decoder**
- Fetch shard page JSON from `shards/{key}/page-NNN.json`
- Read `schema` from shard meta (fetched via V2-T06A), decode array-of-arrays entries using schema field order
- Reconstruct elided fields from shard key (e.g., in `l120` shard, inject `l=120` into every entry)
- Provide `DecodedEntry[]` to puzzle player / page navigator
- Handle page 404: show "page unavailable" placeholder, do not crash
- Handle missing SGF: show "puzzle unavailable" placeholder for that entry
- Unit tests for all shard formats in §6.2

**V2-T07: Count-tier UX contract**
- Render exact/derived labels from manifest metadata

**V2-T13B: Quality (`q`) frontend rollout**
- Parse compact `q` filter param in URL and include it in canonicalization.
- Use manifest dimension registry to include `q` in resolver selection.
- Add quality filter control in UI using same deterministic filter pipeline.

**V2-T14: Page navigator + jump-to-puzzle component**
- Create `PageNavigator` component with page selector: `[< Prev] [1] [2] ... [8] ... [20] [Next >]`
- "Jump to puzzle #" input: computes target page from puzzle number via `floor(n / page_size) + 1`
- For collections: use stable sequence number `n` for "Jump to puzzle #N" (puzzle 347 → page 1, position 347)
- For non-collection shards: use offset-based jump (puzzle 3756 → page 8, position 256 within page)
- Updates URL `offset` param on page/puzzle change
- Accessible: `aria-label` on all controls, keyboard navigation, focus management
- Unit tests: page calculation, boundary cases (first/last page), empty shard state

### P3: Routing and canonical links

**V2-T08: Router rewrite with canonicalization**
- Add `/contexts/{dimension}/{value}` routes (training, technique, collection)
- No `/search` route — all navigation is context-anchored
- Enforce deterministic query ordering, compact filter keys, and `offset` semantics
- Require `id` query param when board is rendering a specific puzzle
- Enforce URL contract: no standalone `/puzzles/{id}` canonical route; all canonical routes are context-based.
- Enforce stable public identifier format for `id` query param (non-raw-hash contract).

### P4: Reconcile, rollback, and cache safety + pipeline wiring

**V2-T04B: Wire SnapshotBuilder into PublishStage.run() (DONE)**
- Added imports: `ShardEntry` from `shard_models`, `SnapshotBuilder` from `snapshot_builder`
- Accumulates flat `list[ShardEntry]` during per-file loop (replacing 3 dicts + collection_sequence)
- After per-file loop: loads existing entries from active snapshot, merges (new wins on collision), builds full snapshot
- Output: `snapshots/{id}/manifest.json`, shard pages, `active-snapshot.json`
- Zero new entries → skip snapshot creation, existing snapshot untouched

**V2-T04C: Remove PaginationWriter call from PublishStage (DONE)**
- Deleted `_update_indexes_paginated()` method and its call
- Removed `puzzles_by_collection`, `collection_sequence` dicts
- Removed `PaginationWriter` and `PaginationConfig` imports
- `views/by-level/`, `views/by-tag/`, `views/by-collection/` no longer produced

**V2-T04D: ShardWriter collection `n` assignment during page gen (DONE)**
- ShardWriter processes 1D collection shards first, assigns `n=1,2,3...` sorted by path
- Stores `puzzle_id → n` mapping per collection context
- 2D collection shards carry global `n` from 1D pass
- Entries arrive with `n=None`; ShardWriter fills in. Pre-set `n` is overridden.

**V2-T04E: Entry reconstruction from existing level shards (DONE)**
- `SnapshotBuilder.load_active_snapshot_id()` reads `active-snapshot.json`
- `SnapshotBuilder.load_existing_entries(snapshot_id)` reads all 1D level shard pages, decodes array-of-arrays back to `ShardEntry` objects
- Re-injects elided level field from shard key. Sets `n=None` for ShardWriter reassignment.
- At 500K puzzles: ~1000 page files, ~50MB, <5s on SSD

**V2-T09: Atomic snapshot switch + validation before activation (DONE)**
- `manifest.json`, `active-snapshot.json`, `.shard-state.json` written via `atomic_write_json()`
- `_validate_snapshot()` expanded: checks shard directories exist, meta.json exists, page file counts match manifest
- Validation failure raises `SnapshotValidationError` — `active-snapshot.json` NOT updated
- Immutable snapshot directories provide crash safety: old snapshot stays intact if build fails

**V2-T10: Rollback refactored to snapshot rebuild (DONE)**
- `RollbackManager._rebuild_snapshot()` loads existing entries, filters out deleted IDs, builds new snapshot
- All puzzles deleted → `remove_active_pointer()` removes `active-snapshot.json`
- `PaginationWriter` and `PaginationConfig` imports removed from `rollback.py`
- `RollbackResult.indexes_updated` replaced with `snapshot_rebuilt: bool`

**V2-T10B: Update cleanup.py for snapshot-aware output (DONE)**
- `clear_pagination_state()` replaced with `clear_snapshot_state()`: deletes `active-snapshot.json` + `snapshots/` directory
- `cleanup_target("puzzles-collection")` now cleans `snapshots/` instead of `views/by-*`
- `.pagination-state.json` removed from `PROTECTED_FILES`
- Legacy `views/` cleanup preserved for backward compat

**V2-T10C: Update StageContext with snapshot paths (DONE)**
- Added `snapshots_dir` property: `output_dir / "snapshots"`
- Added `active_snapshot_path` property: `output_dir / "active-snapshot.json"`
- `views_dir` kept for daily challenges only

### P5: Big-bang cutover and validation

**V2-T11: Remove old 3-silo view code and routes**
- Delete old generators, loaders, and routes (big-bang)

**V2-T12: End-to-end validation**
- Unit, integration, and UI deep-link tests
- Scale smoke tests at low/medium/high cardinality distributions

**V2-T16: Delete PaginationWriter + pagination_models + old tests (DONE)**
- Deleted `pagination_writer.py` (998 lines) and `pagination_models.py`
- Removed re-exports from `core/__init__.py`
- Deleted 6 test files: test_pagination_contracts, test_pagination_state, test_compact_entries, test_numeric_dir_recovery, test_pagination_benchmark, test_publish_pagination
- Updated cleanup tests to use `clear_snapshot_state` instead of `clear_pagination_state`

---

## 10. Dependency Graph (V2)

```
P0:
  V2-T01 ──→ V2-T03
  V2-T02 ──→ V2-T04, V2-T08

P1:
  V2-T03 ──→ V2-T03B ──→ V2-T04 ──→ V2-T05

P1/P4 (pipeline wiring):
  V2-T04 ──→ V2-T04E ──→ V2-T04B ──→ V2-T04C
  V2-T04 ──→ V2-T04D
  V2-T04B ──→ V2-T09
  V2-T04E ──→ V2-T10
  V2-T04C ──→ V2-T10B
  V2-T04B ──→ V2-T10C
  V2-T10 ──→ V2-T16

P2:
  V2-T04 ──→ V2-T06A ──→ V2-T06B
  V2-T06A ──→ V2-T06 ──→ V2-T07
  V2-T06 ──→ V2-T14

P3:
  V2-T06 ──→ V2-T08

P5:
  V2-T08 ──→ V2-T11 ──→ V2-T12
  V2-T16 ──↗

Quality rollout:
  V2-T04 ──→ V2-T13A ──→ V2-T13B
```

---

## 11. Explicitly Addressed Critical Gaps

| Gap | V2 Resolution |
|-----|---------------|
| Approximate cross-counts ambiguity | Count tiers introduced; no silent approximations |
| Snapshoting deferred | Snapshoting made mandatory in core plan |
| Missing metadata handling | Required `none` buckets for each dimension (materialized only if count > 0) |
| Incorrect O(1) blanket claims | Complexity contract now O(1)/O(k) by query type |
| Deployment ambiguity | P0 topology decision and ADR mandatory |
| URL fragmentation risk | Canonical normalization contract required; slugs in path, numeric IDs in params |
| Mixed-state publish risk | Active snapshot pointer switch + bootstrap sequence documented |
| Cache staleness | Snapshot/checksum-based invalidation required |
| Manifest/meta data duplication | TOC removed from manifest; shard metas are SSOT for distributions |
| Unbounded offset-id fallback | Bounded to ±2 pages; reset to offset=0 on miss |
| Missing quality field in entries | `q` added to all non-quality-keyed shard entry schemas |
| Missing failure mode contracts | §4.4 defines behavior for 10 failure scenarios |
| Missing frontend loader tasks | V2-T06A (manifest loader) and V2-T06B (page loader) added |
| Missing shard key algorithm task | V2-T03B (shard key computation module) added |
| SnapshotBuilder not wired into pipeline | V2-T04B: PublishStage.run() now calls SnapshotBuilder with incremental entry merge |
| No incremental publish support | V2-T04E: Entry reconstruction from existing level shards. No registry file needed — level shard pages ARE the entry store |
| PaginationWriter still used in publish | V2-T04C: Completely removed. publish.py no longer produces views/by-* output |
| Collection n assigned pre-shard | V2-T04D: ShardWriter assigns n during 1D collection shard page gen, carries into 2D |
| Non-atomic writes for critical state | V2-T09: manifest.json, active-snapshot.json, .shard-state.json all use atomic_write_json() |
| Rollback used PaginationWriter | V2-T10: Rollback rebuilt as snapshot rebuild — load entries, filter, rebuild |
| Backend cleanup referenced old views | V2-T10B: clear_snapshot_state() replaces clear_pagination_state(). Cleans snapshots/ + active-snapshot.json |

---

## 12. Out of Scope (Still Deferred)

- Standalone `/search` route (all queries are context-anchored; global search would require an inverted index)
- Snapshot pinning in URL (active snapshot is resolved at boot, not exposed in URL; add as debug feature if needed)
- Thumbnail/grid UX enhancements
- Daily challenge format redesign
- Cost-function-based query optimizer (deferred until shard count exceeds 10,000+)
