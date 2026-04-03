# Filtering UX Implementation Roadmap

**Last Updated**: 2026-03-10

This guide contains actionable recommendations and phased execution for Collections, Technique, and Training UX improvements.

---

> **See also**:
>
> - [Reference: Collections, Technique, Training Filtering Audit](../../reference/frontend/collections-filtering-audit-gaps-2026-02-25.md) - Audit evidence and expert findings
> - [Architecture: Frontend Overview](../../architecture/frontend/overview.md) - Frontend architecture context
> - [How-To: Frontend Local Development](./local-development.md) - Dev workflow

---

## 6. Recommendations & Action Items (Architecture-Aware)

### Three-Level Navigation Model

All three sections follow the same flow. Filtering needs are **different at each level**:

```
Level 1: Home Page  →  Level 2: Browse Page  →  Level 3: Solve Page
                       (filtering/sorting)        (puzzle playing)
```

**Key design principle:** Filtering belongs at the **Browse level** (Level 2). The **Solve level** (Level 3) should be an immersive puzzle-solving experience with minimal chrome. Let the user slice and dice data BEFORE entering the puzzle player, not while solving.

### 6.1 Collections

#### Level 2 — Collections Browse (`/collections`)

| Feature                     | Current     | Recommended                                                                                  | Implementation                                                                                                        |
| --------------------------- | ----------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Text search                 | ✅          | ✅ Keep                                                                                      | —                                                                                                                     |
| Section grouping            | ✅          | ✅ Keep as default view                                                                      | —                                                                                                                     |
| **Sort by**                 | ❌          | Add: Featured (default) / Name / Progress / Recently Played                                  | Sort `collection-progress` by `lastActivity` or `completed.length/totalPuzzles`. Client-side only — no backend changes. |
| **Filter by status**        | ❌          | Add pills: All / In Progress / Completed / Not Started                                       | Read `collection-progress` keys + compare `completed.length` vs `totalPuzzles`. Pure client-side.                     |
| **Type filter**             | ⚠️ Implicit | Keep implicit sections. Add explicit pills only if users request.                            | Sections already serve this purpose. Don't over-engineer.                                                             |
| **Difficulty range filter** | ❌          | ⚠️ Defer — requires collection-level difficulty metadata not currently in `collections.json` | Would need backend pipeline change to compute "primary difficulty" per collection. YAGNI for now.                     |

**"Sort by Recently Played" and "Filter by In Progress" depend on `yen-go-collection-progress.lastActivity` — this field already exists.** These are pure client-side features requiring zero backend or server changes.

#### Level 3 — Collection Solve (`/contexts/collection/{slug}`)

| Feature                              | Current                   | Recommended                                                                                           | Implementation                                                    |
| ------------------------------------ | ------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Level filter                         | ✅                        | ✅ Keep                                                                                               | —                                                                 |
| Tag filter                           | ✅                        | ✅ Keep (single-select is fine for cross-filtering)                                                   | —                                                                 |
| **No filter changes for solve page** | —                         | ✅ Keep it clean — filtering was done at browse level                                                 | —                                                                 |
| **Hydrate progress dots on load**    | ❌ (dots reset on reload) | ✅ Must-fix: On mount, read `collection-progress[id].completed[]` and pre-populate `completedIndexes` | Small change in `PuzzleSetPlayer` or `CollectionViewPage`         |
| **"Jump to next unsolved"**          | ❌                        | ✅ Add button: "Skip to next unsolved" using `completed[]` set                                        | Single button, not a filter. Scans forward from current index.    |
| Jump to problem #                    | ❌                        | ✅ Add "Go to #" input in header                                                                      | Already exists as `ProblemNav` numeric display; extend with input |

**Why no status filter on the solve page:** The solve page is for _solving puzzles sequentially_. A "Skip to next unsolved" button achieves the same goal without fragmenting the puzzle set. The user stays in sequence order (which Cho Chikun recommends) but can efficiently fast-forward past completed problems.

### 6.2 Technique

#### Level 2 — Technique Browse (`/technique`)

| Feature              | Current | Recommended                                                                                  | Implementation                                                               |
| -------------------- | ------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Category filter      | ✅      | ✅ Keep                                                                                      | —                                                                            |
| **Level filter**     | ✅      | ✅ Keep — this is the most important filter on this page                                     | Cross-dimensional data from `useMasterIndexes()` already powers this         |
| Sort by Name/Puzzles | ✅      | ✅ Keep                                                                                      | —                                                                            |
| **Sort by Progress** | ❌      | Add: sort by mastery level (ascending = weakest first)                                       | Read `technique-progress.byTechnique[tag]`, compute accuracy, sort ascending |
| **Sort by Accuracy** | ❌      | Add: lowest accuracy first ("Weakest First")                                                 | Same data source as above                                                    |
| Section emojis       | ❌ Bug  | Replace with SVG icons — `ObjectiveFlagIcon`, `TechniqueKeyIcon`, `TesujiIcon` already exist | Trivial fix                                                                  |
| Text search          | ❌      | ⚠️ Low priority — only 28 techniques. Category filter + level filter covers most needs.      | Defer                                                                        |

**The Technique browse page is already the most complete.** Level filter + category filter + sort = good coverage. Adding "Sort by Accuracy (Weakest First)" is the single most impactful addition — it directly answers "what should I practice next?"

#### Level 3 — Technique Solve (`/contexts/technique/{slug}`)

| Feature                     | Current                             | Recommended                                                                | Implementation                                                                       |
| --------------------------- | ----------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Level filter                | ✅                                  | ✅ Keep                                                                    | —                                                                                    |
| Tag cross-filter            | ✅                                  | ⚠️ Reconsider — confusing UX (you're in "Life & Death" and see other tags) | Either remove or add explanatory text: "Narrow by secondary technique"               |
| **Back label**              | ❌ Bug — says "Back to collections" | Must-fix: "Back to techniques"                                             | Pass `backLabel` prop from `app.tsx`                                                 |
| **Hydrate progress dots**   | ❌                                  | ✅ Same as Collection: read `technique-progress` on mount                  | —                                                                                    |
| **"Skip to next unsolved"** | ❌                                  | ✅ Same pattern as Collection solve                                        | Requires `technique-progress.byTechnique[tag].completed: string[]` (needs migration) |

### 6.3 Training

#### Level 2 — Training Browse (`/training`)

| Feature                            | Current | Recommended                                                               | Implementation                                                                          |
| ---------------------------------- | ------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Category filter (Beginner/Int/Adv) | ✅      | ✅ Keep                                                                   | —                                                                                       |
| **Tag filter**                     | ✅      | ✅ Keep — this IS the "slice by technique" capability the user wants      | Cross-dimensional from `useMasterIndexes()`                                             |
| **Per-technique breakdown**        | ❌      | Add mini visualization on each level card: which techniques mastered/weak | Read `technique-progress` cross-referenced with level → show small stacked bar or radar |
| **Recommended level**              | ❌      | Highlight the first "not-started" or "in-progress" level for new users    | Read `training-progress.byLevel`, find first incomplete                                 |

**Training Browse already has the right architecture** — 9 level cards with category filter + tag cross-filter. The tag filter IS technique-based slicing. What's missing is visibility into per-technique progress within each level.

#### Level 3 — Training Solve (`/contexts/training/{level}`)

| Feature                     | Current | Recommended                                                          | Implementation                        |
| --------------------------- | ------- | -------------------------------------------------------------------- | ------------------------------------- |
| Tag filter                  | ✅      | ✅ Keep                                                              | —                                     |
| Progress bar                | ✅      | ✅ Keep                                                              | —                                     |
| Level complete summary      | ✅      | ✅ Keep                                                              | —                                     |
| **Hydrate progress dots**   | ❌      | ✅ Same pattern: read `training-progress.byLevel[level].completed[]` | Needs migration to add per-puzzle IDs |
| **"Skip to next unsolved"** | ❌      | ✅ Same button pattern                                               | —                                     |
| **No additional filters**   | —       | ✅ Correct — tag filter is sufficient. Keep solve page clean.        | —                                     |

### 6.4 Summary: Required Filtering Per Page

| Page                   | Filters Needed                                                                   | Sort Needed                                             | Status Tracking                            |
| ---------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------ |
| **Collections Browse** | Search ✅ + Status (All/In Progress/Complete/Not Started) + Type (keep sections) | Featured / Name / Progress / Recent                     | Via `collection-progress` — already stored |
| **Collection Solve**   | Level ✅ + Tag ✅ (keep as-is)                                                   | None (sequence order is correct default)                | Hydrate dots + "Skip to unsolved" button   |
| **Technique Browse**   | Category ✅ + Level ✅                                                           | Name ✅ / Puzzles ✅ + **Accuracy** + **Weakest First** | Via `technique-progress` — already stored  |
| **Technique Solve**    | Level ✅ + (reconsider tag cross-filter)                                         | None                                                    | Hydrate dots + "Skip to unsolved"          |
| **Training Browse**    | Category ✅ + Tag ✅                                                             | Fixed difficulty order (correct)                        | Per-technique mini-viz                     |
| **Training Solve**     | Tag ✅                                                                           | None                                                    | Hydrate dots + "Skip to unsolved"          |

---

## 7. Concrete Implementation Plan

### Phase 0: Bug Fixes (Day 1)

| ID  | Fix                                                            | Files                               | Effort   |
| --- | -------------------------------------------------------------- | ----------------------------------- | -------- |
| B1  | Emojis → SVG icons in `TechniqueList.tsx` section headers      | `TechniqueList.tsx`                 | < 1 hour |
| B2  | "Back to techniques" label when navigating from Technique page | `app.tsx`, `CollectionViewPage.tsx` | < 1 hour |
| B3  | Delete deprecated `CategoryFilter`/`SortSelector` exports      | `TechniqueList.tsx`                 | < 30 min |
| B4  | Remove `stats` spurious `useMemo` dependency                   | `TechniqueList.tsx`                 | < 15 min |

### Phase 1: Progress Hydration — Make Existing Data Visible (Days 2-3)

**Goal:** The data is already in localStorage. Make it visible in the UI.

#### P1-1: Hydrate PuzzleSetPlayer from localStorage on mount

**Problem:** `PuzzleSetPlayer` starts with empty `completedIndexes`/`failedIndexes` on every mount, even though `yen-go-collection-progress` has `completed[]` arrays.  
**Solution:**

1. In `CollectionViewPage`, after loader is created, call `loadCollectionProgress(collectionId)` → get `completed[]`
2. Map puzzle IDs to indexes via the loader's entry list
3. Pass `initialCompletedIndexes: Set<number>` prop to `PuzzleSetPlayer`
4. `PuzzleSetPlayer` uses this as initial state for `completedIndexes`

**Result:** Progress dots (green/gray) persist across reloads. User can see where they left off.  
**Effort:** 1 day

#### P1-2: "Skip to Next Unsolved" button

**Problem:** In a 200-puzzle collection where 150 are solved, user must click "Next" 150 times.  
**Solution:** Add a "Skip to unsolved ▶" button in `PuzzleSetPlayer` header. On click, scan forward from current index for the first index NOT in `completedIndexes`.  
**Effort:** Half day  
**Dependencies:** P1-1 (needs hydrated completedIndexes)

#### P1-3: Collections Browse — "In Progress" filter + "Recently Played" sort

**Problem:** 159 collections, no way to find ones you started.  
**Solution:**

1. Read all `collection-progress` entries on `CollectionsPage` mount (already happens via `getAllCollectionProgress()`)
2. Add `FilterBar` with: `All` | `In Progress` | `Completed` | `Not Started`
3. Add sort `FilterBar` with: `Featured` (default) | `Name` | `Recently Played`
4. "In Progress" = has `completed.length > 0 && completed.length < totalPuzzles`
5. "Recently Played" = sort by `lastActivity` descending

**Data source:** `yen-go-collection-progress` — no new storage needed.  
**Effort:** 1 day

### Phase 2: Progress Tracking Migration (Days 4-5)

**Goal:** Extend training and technique progress stores to support per-puzzle ID tracking (same pattern as collections).

#### P2-1: Add `completed: string[]` to training progress

**Current shape:** `{ completed: number, total: number, accuracy: number }` (counts only)  
**New shape:** `{ completed: number, completedIds: string[], total: number, accuracy: number }`  
**Migration:** On first load, existing data retains counts (backward compatible). New solves append to `completedIds[]`.  
**Storage cost:** ~10 KB per level (500 puzzles × 20 bytes/ID)  
**Effort:** Half day

#### P2-2: Add `completed: string[]` to technique progress

**Current shape:** `{ attempted: number, correct: number }`  
**New shape:** `{ attempted: number, correct: number, completedIds: string[] }`  
**Same migration strategy.** Same storage cost.  
**Effort:** Half day

#### P2-3: Add "failed" tracking

**Current:** No failure state persisted anywhere.  
**Solution:** Add `failedIds: string[]` alongside `completedIds` in collection, training, and technique progress stores. A puzzle is "failed" if in `failedIds` but not in `completedIds`. When solved, remove from `failedIds`.  
**Storage cost:** Proportional to failure rate — typically <10% of puzzles = negligible.  
**Effort:** Half day (across all three stores)

### Phase 3: Technique & Training Browse Enhancements (Days 6-8)

#### P3-1: Technique Browse — "Weakest First" and "Accuracy" sort

**Solution:** In `TechniqueFocusPage`, add two sort options using existing `technique-progress` data:

- "Accuracy" → sort ascending by `correct / attempted`
- "Weakest First" → sort by accuracy ascending, then by "most practiced" (so techniques you've tried and failed surface above untouched ones)  
  **Data:** Already in localStorage. Pure client-side.  
  **Effort:** 1 day

#### P3-2: Training Browse — Per-technique mini-visualization

**Solution:** On each level card in `TrainingSelectionPage`, show a small stacked bar or tag-chip set showing technique distribution and progress. Use `useMasterIndexes()` for the level→tag distribution and `technique-progress` for user's accuracy per technique.  
**Effort:** 2 days

#### P3-3: Training Browse — "Recommended Level" indicator

**Solution:** Scan `training-progress.byLevel` from easiest to hardest. First level with `< 70%` progress = recommended. Show a "Start here" or "Continue" badge.  
**Effort:** Half day

### Phase 4: Jump-to-Problem (Day 9)

#### P4-1: "Go to #" input in puzzle header

**Solution:** Add a small numeric input in `PuzzleSetHeader` (next to the "3 / 25" counter). User types a number → loader jumps to that index.  
**Why needed:** Users following a physical book reference ("try problem 47") need direct access.  
**Effort:** 1 day

### Phase 5: Future (Backlog)

| ID  | Feature                                                     | Depends On | Notes                                                                                                     |
| --- | ----------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| F1  | Multi-pass tracking (1st, 2nd, Nth pass through collection) | P2-3       | Add `pass: number` to collection progress + "Reset for new pass" button                                   |
| F2  | Solve time per puzzle                                       | P2-1/P2-2  | `PuzzleCompletion` already has `timeSpentMs`. Need to actually record it in technique/training modes too. |
| F3  | Mobile 5-category level filter                              | —          | Change DDK/SDK/Dan → Beginner/Elementary/Intermediate/Advanced/Dan                                        |
| F4  | Export/import progress                                      | —          | `exportProgress()`/`importProgress()` already exist as APIs. Need UI button in settings.                  |
| F5  | Per-puzzle difficulty stars                                 | —          | Use `cx_depth` from DB query as visual ★/★★/★★★ indicator                                          |
| F6  | IndexedDB migration                                         | P2         | If puzzle count exceeds ~25K, migrate per-puzzle data from localStorage to IndexedDB                      |

---

## 8. Code Bugs & Technical Debt

### Confirmed Bugs

| #   | Bug                                                                            | File                                 | Severity |
| --- | ------------------------------------------------------------------------------ | ------------------------------------ | -------- |
| B1  | Emojis (🏳️, 🔑, ⚡) in section headers — violates "No emojis in production UI" | `TechniqueList.tsx`                  | Must-fix |
| B2  | Back label says "Back to collections" when navigating from Technique page      | `app.tsx` / `CollectionViewPage.tsx` | Must-fix |
| B3  | Deprecated `CategoryFilter`/`SortSelector` still exported (dead code policy)   | `TechniqueList.tsx`                  | Must-fix |
| B4  | Quality route falls back to `HomePageGrid` with no indication                  | `app.tsx`                            | Low      |

### Technical Debt

| #   | Issue                                                                      | File                       | Impact                                        |
| --- | -------------------------------------------------------------------------- | -------------------------- | --------------------------------------------- |
| T1  | `stats` spurious dependency in `useMemo` array                             | `TechniqueList.tsx`        | Unnecessary re-renders                        |
| T2  | 100ms `setInterval` polling for loader readiness                           | `TrainingPage.tsx`         | Race condition risk                           |
| T3  | `filterState` objects created inline (not memoized)                        | Multiple pages             | Child re-renders                              |
| T4  | `completedIndexes`/`failedIndexes` not hydrated from localStorage on mount | `PuzzleSetPlayer`          | Progress lost on reload                       |
| T5  | `collection-progress` and `yen-go-progress` are separate, not synced       | `storageOperations.ts`     | Inconsistent global vs per-context completion |
| T6  | Training/technique progress stores lack per-puzzle ID tracking             | `trainingProgressUtils.ts` | Cannot do status-based filtering              |

---

## 9. Priority Matrix (Architecture-Aware)

```
            IMPACT
            High ┃ P1-1 (Hydrate dots)       P1-3 (Browse sort/filter)
                 ┃ P1-2 (Skip unsolved)      P3-1 (Weakest sort)
                 ┃ B1-B3 (Bug fixes)         P3-2 (Per-technique viz)
                 ┃─────────────────────────────────────────────────────
                 ┃ P2-1 (Training IDs)       P4-1 (Jump to #)
                 ┃ P2-2 (Technique IDs)      P3-3 (Recommended level)
            Low  ┃ P2-3 (Failed tracking)    F1-F6 (Backlog)
                 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                  Low EFFORT                   High EFFORT
```

### Suggested Implementation Order

| Sprint       | Items                                              | Days | Why This Order                                            |
| ------------ | -------------------------------------------------- | ---- | --------------------------------------------------------- |
| **Sprint 1** | B1, B2, B3, B4 (bug fixes)                         | 1    | Zero risk, immediate quality improvement                  |
| **Sprint 2** | P1-1 (hydrate dots), P1-2 (skip unsolved)          | 2    | Highest UX impact; uses existing data, no storage changes |
| **Sprint 3** | P1-3 (browse sort/filter)                          | 1    | Second highest impact; also uses existing data            |
| **Sprint 4** | P2-1 + P2-2 + P2-3 (storage migration)             | 2    | Foundation for technique/training status tracking         |
| **Sprint 5** | P3-1 (weakest-first sort)                          | 1    | Most requested technique browse feature                   |
| **Sprint 6** | P3-2 (per-technique viz), P3-3 (recommended level) | 3    | Polish for training page                                  |
| **Sprint 7** | P4-1 (jump to #)                                   | 1    | Completes the puzzle navigation experience                |
| **Backlog**  | F1–F6                                              | —    | As user demand warrants                                   |

**Total estimated effort: ~11 days for all non-backlog items.**

---

## 10. Summary: What Each Page Gets

### Three-Level View

| Section         | Level 2: Browse                                                                                        | Level 3: Solve                                                                                   |
| --------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| **Collections** | Search ✅ + **Status filter** (All/In Progress/Complete/Not Started) + **Sort** (Featured/Name/Recent) | Level + Tag filters ✅ (keep). Add **hydrated progress dots** + **"Skip to unsolved"** button    |
| **Technique**   | Category ✅ + Level ✅ + Sort (Name/Puzzles + **Accuracy/Weakest First**)                              | Level filter ✅ (keep). Add **hydrated progress dots** + **"Skip to unsolved"**. Fix back label. |
| **Training**    | Category ✅ + Tag ✅ + **Per-technique mini-viz** + **Recommended level badge**                        | Tag filter ✅ (keep). Add **hydrated progress dots** + **"Skip to unsolved"**                    |

### Key Architecture Decisions

1. **No filtering on solve pages** — filtering happens at browse level; solve page has "Skip to unsolved" button instead
2. **Status filter on browse pages only** — Collections Browse gets All/In Progress/Complete/Not Started using existing localStorage data
3. **Training Browse already has technique-based slicing** via the Tag filter dropdown + cross-dimensional counts from `useMasterIndexes()`
4. **Technique Browse already has level-based slicing** via the Level filter pills + cross-dimensional counts
5. **"Failed" tracking** requires a small storage addition but is the only new data model needed
6. **No new database tables** — all status filtering is pure client-side against localStorage
7. **localStorage budget is fine** — even at 10K puzzles with per-puzzle tracking, we're at ~2 MB of 5 MB quota
8. **Export/import for backup** — APIs exist but need UI wiring (Settings page button)

> **Next Steps:** Start with Sprint 1 (bug fixes) and Sprint 2 (hydrate dots + skip to unsolved). These two sprints deliver the highest UX impact with the lowest risk and zero storage changes.
