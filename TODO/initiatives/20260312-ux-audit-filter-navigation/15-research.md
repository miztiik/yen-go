# UX Audit — Filter & Navigation Gaps (DDK + SDK Personas)

**Initiative:** `20260312-ux-audit-filter-navigation`  
**Date:** 2026-03-12  
**Mode:** Feature-Researcher  
**Confidence after research:** 88 / 100  
**Risk level:** Medium

---

## 1. Research Question and Boundaries

**Question:** From the perspective of two learner personas (DDK casual player and SDK serious learner), what are the most impactful UX gaps in Yen-Go's filter system, navigation flow, and state persistence across the 5 main pages?

**In scope:**
- Filter correctness (wired vs. cosmetic), URL-sync behaviour, consistency across pages
- Navigation back-button destinations
- State persistence across back/forward navigation
- Missing features relevant to practice workflows (bookmarks, resume, sort)
- Direct URL shareability

**Out of scope:**
- Goban rendering, puzzle difficulty calibration, SGF content
- Backend/pipeline changes
- PWA/offline features

---

## 2. Internal Code Evidence

### E-1 — CollectionViewPage: back button hardwired to Home, not /collections

**File:** [frontend/src/app.tsx](../../../frontend/src/app.tsx#L522-L526)  
```tsx
<CollectionViewPage
  collectionId={route.slug}
  startIndex={route.offset}
  onBack={handleBackToHome}   // ← goes to { type: 'home' }, NOT 'collections-browse'
/>
```
`handleBackToHome` (line 244) always routes to `{ type: 'home' }`. No variant routes to `collections-browse`. When a user navigates Home → Collections → Collection → Back, they land on Home instead of the Collections list. Confirmed: the `technique` dimension at line 536 correctly routes back to `technique-browse`, so the pattern exists but was not applied to `collection`.

### E-2 — TechniqueFocusPage: category & sort filters are local state only (lost on back-nav)

**File:** [frontend/src/pages/TechniqueFocusPage.tsx](../../../frontend/src/pages/TechniqueFocusPage.tsx#L74-L75)  
```tsx
const [categoryFilter, setCategoryFilter] = useState<string>('technique');
const [sortBy, setSortBy] = useState<string>('name');
```
Only `filters.l` (level IDs) are URL-synced via `useCanonicalUrl`. Category and sort are in-memory only. Browser back/forward loses them.

### E-3 — TrainingSelectionPage: category filter is local state only

**File:** [frontend/src/pages/TrainingSelectionPage.tsx](../../../frontend/src/pages/TrainingSelectionPage.tsx#L114)  
```tsx
const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
```
Tag filter IS URL-synced via `useCanonicalUrl`. Category (Beginner/Intermediate/Advanced) resets on every navigation. Inconsistent with tag persistence.

### E-4 — CollectionsPage: text search is local state only, no level/tag/sort filters

**File:** [frontend/src/pages/CollectionsPage.tsx](../../../frontend/src/pages/CollectionsPage.tsx#L246)  
```tsx
const [searchTerm, setSearchTerm] = useState('');
```
No URL sync. No level filter, no tag filter, no sort control. The `ContentTypeFilter` is rendered but **does not affect the collections grid** — collections come from `collectionService` which is independent of content-type shard data. The filter changes a global preference but produces zero visible effect on CollectionsPage.

### E-5 — ContentTypeFilter: counts prop absent on 3 of 5 pages

**CollectionsPage** (line 345): `<ContentTypeFilter />` — no `counts` prop  
**TechniqueFocusPage** — no shard meta loaded, so no counts available to pass  
**TrainingSelectionPage** — no shard meta, no counts  
**CollectionViewPage** — uses `useShardFilters` → counts from shard meta ✅  
**TrainingPage** — uses `useShardFilters` → counts from shard meta ✅  

On pages without counts, the filter renders without badges, giving no affordance about how many puzzles each type contains.

### E-6 — No shorthand route for /collection/{slug}

**File:** [frontend/src/lib/routing/routes.ts](../../../frontend/src/lib/routing/routes.ts#L42-L55)  
Only `/contexts/collection/{slug}` is registered. No `/collection/{slug}` alias. Sharing a collection URL requires knowing the full internal path. The `CONTEXT_RE` pattern is `/^\/contexts\/(training|technique|collection|quality)\/([^/?#]+)$/`.

### E-7 — No bookmarks, favorites, or recently-played feature

Code search across all `frontend/src/**/*.tsx` for `bookmark|recently.*played|favorite|history` returned zero relevant matches (only RushOverlay `resume` and DailyBrowsePage `recent history` of dates). No persistent cross-session "resume where I left off" for collections or training.

### E-8 — CollectionViewPage: position not persisted between sessions

**File:** [frontend/src/pages/CollectionViewPage.tsx](../../../frontend/src/pages/CollectionViewPage.tsx#L92-L97)  
`completedIds` is loaded from `progressTracker`, but `startIndex` only comes from `route.offset` (URL param). If the user closes the browser mid-collection, there is no restore-last-position logic. `useAutoAdvance` auto-advances during a session but doesn't write a persistent cursor.

### E-9 — CollectionsPage: ContentTypeFilter has no functional effect

**File:** [frontend/src/pages/CollectionsPage.tsx](../../../frontend/src/pages/CollectionsPage.tsx#L345)  
`ContentTypeFilter` changes the global `useContentType` value, but `CollectionsPage` does not read `useContentType()` anywhere in the component. The collections grid is filtered exclusively by `searchTerm` and `SECTIONS` type groupings.

### E-10 — TechniqueFocusPage: default category initialises to `'technique'`, not `'all'`

**File:** [frontend/src/pages/TechniqueFocusPage.tsx](../../../frontend/src/pages/TechniqueFocusPage.tsx#L74)  
```tsx
const [categoryFilter, setCategoryFilter] = useState<string>('technique');
```
A DDK user opening the Technique browser for the first time sees only `technique` category. The `tesuji` and `objective` categories are hidden until they explicitly click "All" or the category filter. This is an invisible default — the label on the FilterBar will show `'technique'` pre-selected, which is not "all by default."

---

## 3. External References

| R-id | Reference | Relevance to Yen-Go |
|------|-----------|---------------------|
| R-1 | [Nielsen Norman Group — Filters in UX](https://www.nngroup.com/articles/filters-vs-facets/) — Facets vs. Filters | Facets (server-side counts per option) outperform cosmetic filters (no counts) in discoverability; badge counts reduce "filter leads to zero results" anxiety |
| R-2 | [Duolingo "Keep your streak" UX](https://blog.duolingo.com/streak-saver/) — streak & resume patterns | Daily streak + "resume last lesson" significantly improves 7-day retention in language learning apps; analogous to puzzle apps |
| R-3 | [Chess.com puzzle filter design](https://www.chess.com/puzzles) — technique + difficulty cross-filter | Cross-filter (technique × level) is the primary navigation pattern for SDK-equivalent learners; absence forces manual browsing |
| R-4 | [URL state management — web.dev, History API](https://developer.chrome.com/docs/web-platform/url-pattern/) | `history.replaceState` for filter changes (already used in `useCanonicalUrl`) is the correct pattern; extending it to category/sort avoids session loss without polluting back stack |

---

## 4. Candidate Adaptations for Yen-Go

| R-id | Adaptation | Complexity | Constraint Alignment |
|------|-----------|------------|---------------------|
| A-1 | **Fix back button**: change `onBack={handleBackToHome}` to `onBack={handleNavigateCollections}` in `collection` dimension branch in app.tsx | Level 1 (1 line, 1 file) | No new deps, pure routing fix; same pattern exists for `technique` dimension at line 536 |
| A-2 | **URL-sync category + sort in TechniqueFocusPage**: add `cat` and `s` params to `useCanonicalUrl` extension or store in URL search via `history.replaceState` directly | Level 2 (1-2 files, adds 2 URL params) | `useCanonicalUrl` already handles `l` and `t`; needs new param keys |
| A-3 | **URL-sync category in TrainingSelectionPage** | Level 1 (1 file, mirror `cat` param) | Same approach as A-2 |
| A-4 | **Wire ContentTypeFilter to CollectionsPage**: read `useContentType()` and filter collections by their `type` field mapping to content-type taxonomy | Level 2 (1-2 files, define type→contentType mapping) | May be complex since collection types (`author`, `graded`, etc.) don't map 1:1 to content-type IDs 1-3 |
| A-5 | **Add counts to ContentTypeFilter on browse pages**: pass shard meta distribution to `<ContentTypeFilter counts={...} />` on TechniqueFocusPage and TrainingSelectionPage | Level 2 (load shard meta per page) | `useShardFilters` already does this for context pages; browse pages need a lighter equivalent |
| A-6 | **URL-sync search term in CollectionsPage**: add `q` search param via `history.replaceState` | Level 1 (1 file) | Low risk; `useCanonicalUrl` already handles `q` for quality — use a distinct param key like `s` |
| A-7 | **Add sort + difficulty range filter to CollectionsPage**: sort by name / puzzle count / progress; filter by difficulty band | Level 3 (component + service changes) | Requires aggregating level distributions per collection — feasible from collection master index |
| A-8 | **"Resume" last position per collection**: write last `offset` to localStorage on advance; read it as `startIndex` default | Level 2 (1-2 files) | Aligns with local-first principle; no backend needed |
| A-9 | **Shorthand URL `/collection/{slug}`**: add alias pattern to `parseRoute` | Level 1 (1 file) | Pure routing, backward-compatible |
| A-10 | **Fix TechniqueFocusPage default category**: change `useState('technique')` to `useState('all')` | Level 0 (1 line) | Behavioural default fix — presents complete catalogue on first visit |

---

## 5. Risks, License / Compliance Notes, and Rejection Reasons

| R-id | Risk | Level | Notes |
|------|------|-------|-------|
| RI-1 | A-4 (wire ContentTypeFilter to collections) may surface "0 results" for some content-types if collection type→content-type mapping is ambiguous | Medium | Needs explicit taxonomy alignment; consider deferring |
| RI-2 | A-7 (difficulty filter on CollectionsPage) requires level-distribution data per collection from master index | Medium | Data exists in shard meta but aggregation logic is non-trivial |
| RI-3 | Adding `cat`/`s` URL params (A-2, A-3) pollutes canonical URL space; planner should verify no clash with existing `c` (collection ID) param | Low | `c` is numeric collection ID; `cat` is string — no collision |
| RI-4 | A-8 (resume position) writes to localStorage; must not conflict with existing `completedIds` or `progressTracker` keys | Low | Use a distinct namespaced key like `yengo:resume:{collectionSlug}` |

No external library additions required for any candidate. All adaptations use existing patterns.

---

## 6. Planner Recommendations

### Severity-Ranked Issue Table

| # | Issue | Severity | Affected Pages | Evidence |
|---|-------|----------|---------------|----------|
| I-1 | CollectionViewPage back button → Home (not /collections) | **Critical** | CollectionViewPage | E-1 |
| I-2 | ContentTypeFilter on CollectionsPage has zero visual effect | **Critical** | CollectionsPage | E-4, E-9 |
| I-3 | Category filter on TechniqueFocusPage and TrainingSelectionPage lost on back | **High** | TechniqueFocusPage, TrainingSelectionPage | E-2, E-3 |
| I-4 | Collections search not URL-synced (lost on back) | **High** | CollectionsPage | E-4 |
| I-5 | ContentTypeFilter renders without counts on 3/5 pages | **High** | CollectionsPage, TechniqueFocusPage, TrainingSelectionPage | E-5 |
| I-6 | TechniqueFocusPage defaults to `'technique'` category — hides tesuji/objective | **High** | TechniqueFocusPage | E-10 |
| I-7 | No level/tag/sort filter on CollectionsPage | **Medium** | CollectionsPage | E-4 |
| I-8 | No "resume last position" for collections | **Medium** | CollectionViewPage | E-8 |
| I-9 | No shorthand /collection/{slug} URL | **Medium** | Routing | E-6 |
| I-10 | No bookmarks/favorites feature | **Low** | App-wide | E-7 |

---

### Persona A — DDK Casual Player Journey Friction Map

```
Home → [Training] → TrainingSelectionPage
  1. Clicks "Beginner" category pill                  ← pill resets on any back nav (I-3)
  2. Selects "Intermediate" level card
     → TrainingPage (level context)
  3. Presses Back                                     ← returns to TrainingSelectionPage ✅
  4. Presses Back again                               ← returns to Home ✅ (correct)

Home → [Technique] → TechniqueFocusPage
  1. First view shows only "technique" category        ← tesuji hidden by default (I-6)
  2. Selects "Ladder" technique → CollectionViewPage
  3. Presses Back                                     ← returns to TechniqueFocusPage ✅ (fixed in techniques)
  4. Changes sort to "Puzzles"                        ← sort resets on back/forward (I-3)

Home → [Collections] → CollectionsPage
  1. Types "Cho" in search box                       ← search lost on back (I-4)
  2. Clicks ContentTypeFilter "Curated"               ← filter does NOTHING (I-2)
  3. Clicks "Cho Chikun..." card → CollectionViewPage
  4. Presses Back                                     ← goes to Home (I-1) ← BREAKS WORKFLOW
  5. Has to re-navigate to Collections, re-type "Cho" ← double friction
```

### Persona B — SDK Serious Learner Journey Friction Map

```
Home → [Technique] → TechniqueFocusPage
  1. Sets level filter "Upper-Intermediate" (URL ✅)
  2. Sets category "Tesuji"                           ← need to click past default 'technique' (I-6)
  3. Sorts by "Puzzles"                               ← sort not URL-synced, lost on any nav (I-3)
  4. Selects "Ladder" → CollectionViewPage
     - Uses Level + Tag compound filter               ← ✅ works via useShardFilters
  5. Browser refresh                                  ← level filter preserved via URL ✅
     But: returns to position 0 in puzzle list        ← no resume (I-8)

Home → [Collections] → CollectionsPage
  1. Wants to filter "Author" collections by difficulty "Advanced"
     → No difficulty filter available                 ← (I-7)
  2. Clicks ContentTypeFilter "Curated"               ← no effect (I-2)
  3. Selects Cho Chikun collection → CollectionViewPage
  4. Presses Back                                     ← Home (I-1) — must re-browse entire list
  5. Wants to share URL with study partner
     → /contexts/collection/cho-chikun-life-death-elementary — no short alias (I-9)
```

---

### Decision-Ready Recommendations

**Rec-1 (Quick Win, Critical):** Fix collection back button in [app.tsx](../../../frontend/src/app.tsx#L522-L526) — change `onBack={handleBackToHome}` to route back to `collections-browse`, mirroring the technique dimension fix at line 536. 1-line change, Level 1.

**Rec-2 (Quick Win, Critical):** Suppress or re-wire `ContentTypeFilter` on CollectionsPage — either (a) remove it from CollectionsPage until it has a functional effect, or (b) define a collection type → content-type mapping and filter the grid. Option (a) is Level 0; option (b) is Level 2. Recommend (a) first to eliminate user confusion, (b) as follow-on.

**Rec-3 (Quick Win, High):** Fix TechniqueFocusPage default category from `'technique'` to `'all'` ([TechniqueFocusPage.tsx](../../../frontend/src/pages/TechniqueFocusPage.tsx#L74)). 1-line change, Level 0. Unblocks DDK users from discovering tesuji-family puzzles.

**Rec-4 (Strategic, High):** URL-sync `categoryFilter` on TechniqueFocusPage and TrainingSelectionPage. Extend `useCanonicalUrl` with a `cat` string param (or store in URL via `replaceState`). Level 2. Eliminates the largest category of state-loss frustration for returning users. Can be implemented alongside URL-syncing the search term on CollectionsPage (same pattern, same PR).

---

## 7. Confidence and Risk Update

| Dimension | Score |
|-----------|-------|
| Internal evidence completeness | High — all 5 pages read, routing confirmed, hook behaviour confirmed |
| External pattern alignment | Medium — references are well-known but Yen-Go constraints limit direct adoption |
| Implementation risk | Low for I-1, I-2, I-6 (Level 0–1); Medium for I-3, I-4, I-7 (Level 2–3) |
| Regression risk | Low — changes are isolated to routing and filter state; no shared business logic affected |

**Post-research confidence score:** 88 / 100  
**Post-research risk level:** Low (for Rec-1/2/3) → Medium (for Rec-4 and beyond)

---

*Last Updated: 2026-03-12*
