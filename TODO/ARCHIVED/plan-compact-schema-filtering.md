# Compact Schema & Multi-Dimensional Filtering — Implementation Plan v3

**Last Updated**: 2026-02-20
**Status**: GAP REMEDIATION — ~39% Complete (52/~133 steps done, 71 gaps identified, WP11 validated)
**Scale Target**: 150,000-200,000+ puzzles
**Migration Strategy**: Big-bang (no backward compatibility)
**Entry Wire Format**: `{p, l, t, c, x}` — Architecture C (Numeric Wire Format)
**SGF Directory**: Flat batches (`sgf/0001/`, 1000 files/batch)
**Pagination**: Always-paginated (no flat mode)
**ViewEnvelope Version**: 4.0 | **Master Index Version**: 2.0
**Companion Plan**: [plan-rush-play-enhancement.md](./plan-rush-play-enhancement.md)
**Reference (superseded)**: [multi-dimensional-puzzle-filtering.md](./multi-dimensional-puzzle-filtering.md), [entry-compression-proposal.md](./entry-compression-proposal.md)
**Audit Trail**: v2 to v3 gap audit conducted 2026-02-18 (see section 12)

---

## 1. Executive Summary

Enable users to **filter puzzles across multiple dimensions** (level, tag, collection) from any page. Simultaneously **flatten the SGF directory structure**, **compress view entries to ~68 bytes**, and **eliminate flat-mode pagination** — a one-time big-bang migration opportunity.

### v3 Update: Honest Status Assessment

A 108-step audit on 2026-02-18 revealed **64 gaps** across all phases. The data layer (Phases 0-1, most of 2, parts of 3-4) is substantially complete. The critical **D23 numeric directory migration** was never implemented — both backend and frontend still use slug-based view directory paths. Phases 7-10 (frontend types, filtering components, page integration, visual testing) are largely unstarted. This v3 plan documents every gap with a remediation work package.

### Entry Wire Format (Final)

```json
{"p":"0001/fc38f029205dde14","l":130,"t":[12,34,36],"c":[1],"x":[3,2,19,1]}
```

| Key | Meaning | Type | Example | Decoded |
|-----|---------|------|---------|---------|
| `p` | path ref | `string` | `"0001/fc38f029205dde14"` | `sgf/0001/fc38f029205dde14.sgf` |
| `l` | level | `integer` (sparse) | `130` | `elementary` |
| `t` | tags | `integer[]` (sparse) | `[12,34,36]` | `[ko, ladder, net]` |
| `c` | collections | `integer[]` | `[1]` | `[cho-chikun-elementary]` |
| `x` | complexity | `[d,r,s,u]` | `[3,2,19,1]` | depth=3, responses=2, size=19, unique=1 |
| `n` | sequence | `integer` | `42` | (collection entries only) |

### Impact

| Metric | Before | After |
|--------|--------|-------|
| Avg entry | 143 B | **~68 B** (52% smaller) |
| Total views (200k) | ~163 MB | **~75 MB** |
| Git repo (views+SGFs) | ~363 MB | **~275 MB** |
| Page file (500 entries) | ~107 KB | **~50 KB** |
| Code paths (flat+paginated) | 2 | **1** (~300 lines removed) |

---

## 2. Decisions Registry (D1-D31)

| # | Decision | Choice | v3 Status |
|---|----------|--------|-----------|
| D1 | Entry schema | Compact `{p, l, t, c, x}` everywhere | Done |
| D2 | Migration strategy | Big-bang, no backward compatibility | Done |
| D3 | Filtering approach | Client-side `Array.filter()` per loaded page | Not started |
| D4 | Master index enrichment | Level/tag distribution counts in ALL master indexes | Done |
| D5 | Collection entries | Uniform schema + `n` for sequence | PARTIAL |
| D6 | Collection catalog | Defer -- master index provides dynamic counts | Done |
| D7 | Schema name | Keep `ViewEnvelope` | Done |
| D8 | Daily dimension | Included in all planning | Daily master index missing |
| D9 | Master indexes | Level + Tag + Collection + Daily -- all four enriched | 3/4 done (no daily) |
| D10 | Always-paginate | YES -- eliminate flat mode | PARTIAL -- flat fallback in publish.py |
| D11 | YX in entries | YES -- positional array `[d,r,s,u]` | Done |
| D12 | Rush refactor | NO -- keep Rush independent (separate plan) | Done |
| D13 | Rush scope | Separate plan | Done |
| D14 | Rush custom time | Custom pill + slider 1-30 min (in Rush plan) | Done |
| D15 | Flat batch dirs | YES -- `sgf/0001/` | Done |
| D16 | Entry compression | Architecture C -- numeric wire format | Done |
| D17 | Fix hardcoded slugs | YES -- config-driven lookups | NOT DONE |
| D18 | Batch size | 1,000 files/batch (configurable) | Done |
| D19 | Batch naming | Numeric only | Done |
| D20 | Level IDs | Sparse, Go-rank-aligned (110-230) | Done |
| D21 | Tag IDs | Sparse by category (original ranges) | **SUPERSEDED by D30** |
| D22 | Collection IDs | Sequential numeric (1-159+) | Done (config) |
| **D22a** | **Collection view dirs** | **Numeric IDs (v3 amendment)** | NOT DONE |
| D23 | View dir naming | Numeric IDs for level/tag/collection | **CRITICAL -- NOT DONE** |
| D24 | Collection in entries | YES -- `c` field | Done |
| D25 | Tag categories | Original ranges 10-19, 20-49, 50-79 | **SUPERSEDED by D30** |
| Q1 | ViewEnvelope version | `"4.0"` | Done |
| Q2 | Master index version | `"2.0"` | Done |
| Q3 | Distributions in state | YES | Done |
| Q4 | Filter persistence | None for now (YAGNI) | Done |
| Q5 | Keep `filterPuzzlesByLevel()` | Remove -- one-liner | NOT DONE |
| **D26** | **Decode file** | **Create `entryDecoder.ts`, delete `compact-entry.ts`** (v3 new) | Not started |
| **D27** | **Backend state keys** | **Stay as slugs, only filesystem dirs go numeric** (v3 new) | Not started |
| **D28** | **Filter UX pattern** | **FilterBar pills + FilterDropdown for >8 options** (v3 new) | Not started |
| **D29** | **Config source** | **`generated-types.ts` (build-time) for levels/tags, async for collections** (v3 new) | Not started |
| **D30** | **Tag ID rebalance** | **Widen bands: Obj 10-28, Tesuji 30-52, Tech 60-82. Shift tesuji/tech +10. No new tags (YAGNI per Go Pro #3).** (v3.2) | Not started |
| **D31** | **`numericId` -> `id` rename** | **Rename `numericId` to `id` in tags.json and collections.json. Old `id` (slug) becomes `slug`.** (v3.1) | Not started |

---

## 3. Completion Status by Phase

> **Note**: This scorecard reflects the original 108 steps from v2. WP0 (12 steps) and WP11 (13 steps) added in v3.1 bring the total to ~133 steps. Effective completion is ~29%.

### Phase Scorecard

| Phase | Description | Steps | Done | Partial | Not Done | % |
|-------|-------------|-------|------|---------|----------|---|
| **0** | Config Schema Updates | 6 | 6 | 0 | 0 | **100%** |
| **1** | SGF Directory Restructuring | 5 | 5 | 0 | 0 | **100%** |
| **2** | Compact Entry Construction | 9 | 6 | 1 | 2 | **67%** |
| **3** | Always-Paginate Migration | 11 | 5 | 2 | 1 | **55%** |
| **4** | Master Indexes + Distributions | 10 | 8 | 0 | 2 | **80%** |
| **5** | Tests + Old Code Removal | 7 | 4 | 0 | 3 | **57%** |
| **6** | Republish + Validation | 8 | 3 | 1 | 4 | **38%** |
| **7** | Frontend Types + Legacy Removal | 20 | 1 | 4 | 13 | **5%** |
| **8** | Filter Components | 7 | 0 | 0 | 7 | **0%** |
| **9** | Page Integration | 12 | 0 | 1 | 11 | **0%** |
| **10** | Visual Testing | 11 | 0 | 0 | 11 | **0%** |
| **11** | Documentation | 2 | 1 | 0 | 1 | **50%** |
| **TOTAL** | | **108** | **39** | **8** | **55** | **36%** |

---

## 4. Gap Registry (71 Items)

### 4.1 Backend Gaps (19)

| ID | Phase | What's Wrong | Severity | WP |
|----|-------|-------------|----------|-----|
| G1 | 2.5 | `pagination_writer.py` uses `"sequence_number"` not `"n"` in collection entries | **High** | WP2 |
| G2 | 2.6 | `PuzzleRef` model uses `{id, level, path}` not compact format | Medium | WP3 |
| G3 | 2.6 | No daily master index generation code | Medium | WP3 |
| G4 | 3.1 | `_update_indexes_flat()` still alive in publish.py L508-572 | Medium | WP2 |
| G5 | 3.1 | `_update_collection_indexes()` flat fallback in publish.py L574-636 | Medium | WP2 |
| G6 | **3.10** | **`get_level_dir()` uses slug, not numeric ID** (pagination_writer.py L364-372) | **Critical** | WP1 |
| G7 | **3.10** | **`get_tag_dir()` uses slug, not numeric ID** (pagination_writer.py L375-383) | **Critical** | WP1 |
| G8 | 3.10 | Collection dirs use slugs, not numeric IDs (D22a amendment) | **Critical** | WP1 |
| G9 | 4.6 | No `views/daily/index.json` -- daily master index missing | Medium | WP3 |
| G10 | 4.7 | Master index entries missing `"id"` field (numeric ID) | Medium | WP1 |
| G11 | 5.1 | test_pagination_contracts.py uses old `{path, tags}` shapes | Medium | WP2 |
| G12 | 5.1 | test_rollback_integration.py uses old `{path, level, sequence_number}` | Medium | WP2 |
| G13 | 5.1 | test_pagination_benchmark.py uses old `{path, level, tags}` | Medium | WP2 |
| G14 | 5.1 | test_daily_posix.py uses old `{path, level}` | Medium | WP2 |
| G15 | **6.3** | **Published view directories use slugs** (`beginner/`, `ladder/`) | **Critical** | WP1 |
| G16 | 6.3 | `views/by-collection/` directories use slugs | **Critical** | WP1 |
| G17 | 6.7 | Published collection entries have redundant `"sequence_number"` + `"n"` | High | WP2 |
| G18 | 3.10 | `_recover_state_from_files()` reads dir names as slugs -- breaks after numeric | Medium | WP1 |
| G19 | 3.10 | `_rebuild_index_structure()` creates dirs with slug names | Medium | WP1 |

### 4.2 Frontend Gaps (44)

| ID | Phase | What's Wrong | Severity | WP |
|----|-------|-------------|----------|-----|
| G20 | 7.1 | No `configService.ts` -- config pre-fetch missing | **High** | WP4 |
| G21 | 7.4 | Decoded types lose `yx` (complexity) -- no `DecodedEntry` with full fields | Medium | WP4 |
| G22 | 7.5 | No `entryDecoder.ts` -- decode logic in wrong file | Medium | WP4 |
| G23 | 7.6 | `MasterIndexEntry` missing `id: number` field | Medium | WP4 |
| G24 | **7.7** | **`loadLevelIndex()` uses slug URL** -- will 404 after D23 | **Critical** | WP5 |
| G25 | **7.8** | **`loadTagIndex()` uses slug URL** -- will 404 after D23 | **Critical** | WP5 |
| G26 | 7.7 | `VIEW_PATHS` accepts `string` (slug), not `number` (ID) | **Critical** | WP5 |
| G27 | 7.7 | Direct interpolation in collectionService bypasses VIEW_PATHS | **Critical** | WP5 |
| G28 | 7.9 | `filterPuzzlesByLevel()` still in tag-loader.ts L196 | Low | WP6 |
| G29 | 7.9 | `filterPuzzlesByRank()` dead code in tag-loader.ts L212 | Low | WP6 |
| G30 | 7.9 | Legacy `TagPuzzleEntry`, `TagIndex` types in tag-loader.ts | Low | WP6 |
| G31 | 7.10 | `loadLevelIndex()` has Array.isArray() legacy fallback | Low | WP6 |
| G32 | 7.11 | `detectCollectionFormat()` still in collectionService.ts L323 | Low | WP6 |
| G33 | 7.12 | `ViewIndex`, `SkillLevelIndex`, `TagViewIndex` still in manifest.ts | Low | WP6 |
| G34 | 7.13 | `TAG_DISPLAY_INFO` (24 hardcoded tags) in collectionService.ts L48 | Medium | WP6 |
| G35 | 7.14 | `SLUG_OVERRIDES` (14 entries) in slug-formatter.ts L12 | Medium | WP6 |
| G36 | 7.15 | `PUZZLE_TAGS` (18 hardcoded tags) in SettingsPanel.tsx L48 | Medium | WP6 |
| G37 | 7.16 | `CATEGORY_LEVELS` hardcoded in RandomPage.tsx L49 | Medium | WP6 |
| G38 | 7.17 | `LEVEL_CATEGORY` hardcoded in TrainingSelectionPage.tsx L76 | Medium | WP6 |
| G39 | 7.18 | Hardcoded `'beginner'` defaults in 3+ files | Medium | WP6 |
| G40 | 7.18 | Hardcoded `'novice'`/`'elementary'` defaults in 3+ files | Medium | WP6 |
| G41 | 8.1 | No `FilterDropdown` component | **High** | WP7 |
| G42 | 8.2 | `FilterBar` has no `count` badge support | Medium | WP7 |
| G43 | 8.3 | No `useFilterState` hook | **High** | WP7 |
| G44-G52 | 9.1-9.12 | No page filter integration (9 items) | **High** | WP8 |
| G53-G63 | 10.1-10.11 | No visual regression tests for filters (11 items) | Medium | WP9 |

### 4.3 Documentation Gap (1)

| ID | Phase | What's Wrong | WP |
|----|-------|-------------|-----|
| G64 | 11.1 | `docs/concepts/numeric-id-scheme.md` does not exist | WP10 |

### 4.4 Config Gaps (v3.1 — from architect review)

| ID | Source | What's Wrong | Severity | WP |
|----|--------|-------------|----------|-----|
| G65 | D30 | `config/tags.json` tag IDs need band shift (tesuji +10, technique +10) | **High** | WP0 |
| G66 | D31 | `config/tags.json` field `numericId` must rename to `id`, old `id` to `slug` | **High** | WP0 |
| G67 | D31 | `config/collections.json` field `numericId` must rename to `id` | **High** | WP0 |
| G68 | D31 | `backend/puzzle_manager/core/id_maps.py` reads `numericId` -- 5 references | **High** | WP0 |
| G69 | D31 | `frontend/scripts/generate-types.ts` reads `numericId` -- 7 references | **High** | WP0 |
| G70 | D30 | `config/schemas/view-index.schema.json` tag ID range constraints need update | Medium | WP0 |
| G71 | D2 | Big-bang wipe: all published data, state, runtime must be deleted before fresh ingest | **High** | WP0 |

---

## 5. Filtering UX Design

### 5.1 Design Philosophy & Expert Reviews

#### UI/UX Expert Review #1 -- Consistency-First Approach

> **Principle**: Users learn ONE filter interaction pattern and apply it everywhere. The yen-go frontend already established pill-button groups (`FilterBar`) as the primary filter mechanism. Don't introduce a competing paradigm -- extend it.
>
> **Recommendation**: Use `FilterBar` (pills) for dimensions with 8 or fewer options (levels have 9 -- borderline acceptable). Use a new `FilterDropdown` component ONLY when pill overflow becomes a usability problem (28 tags). The dropdown should feel like a "compressed FilterBar" -- same accent color, same `rounded-full` styling, same `min-h-[44px]`.
>
> **Placement**: Filters go in the existing Layer 2 strip (between header and content), always. Left = primary dimension, right = secondary dimension. This matches the Training (category + view toggle), Technique (category + sort), and Random (category + level) patterns.
>
> **Count badges**: Show `"Ladder (42)"` counts on every filter option. Users need to know "is it worth clicking this?" before clicking. Master index distributions provide these counts at zero cost.

#### UI/UX Expert Review #2 -- Progressive Disclosure

> **Principle**: Don't overwhelm beginners. 28 tags in a flat dropdown is too many. Group them by category (Objectives | Tesuji | Techniques) as optgroup-style headers inside the dropdown.
>
> **Recommendation**: FilterDropdown should show category headers (non-selectable) with tags underneath. This mirrors the TechniqueList's category grouping and teaches Go taxonomy simultaneously.
>
> **"Active filters" summary**: When a filter is active, show a small dismissible chip below the filter strip: `"Filtering: Ladder x"`. This prevents "hidden state" confusion where users forget they've filtered.
>
> **Empty state**: When filter combination yields zero results: "No puzzles match -- try removing a filter" with a "Clear all filters" ghost button.

#### 1P Go Professional Review #1 -- Pedagogical Alignment

> **Principle**: Go study follows a natural hierarchy: Level -> Technique -> Specific Pattern. A 15-kyu student studying life-and-death should be able to filter to their level and see only puzzles they can attempt.
>
> **Recommendation**: The primary filter dimension should match the page context:
> - **Training (level-centric)**: Primary = level *(already set)*, Secondary = **tag/technique filter** *(new)*
> - **Technique (tag-centric)**: Primary = tag *(already set)*, Secondary = **level filter** *(new)*
> - **Collections**: Both **level + tag** as secondary filters within the collection
>
> This aligns with how Go teachers assign homework: "Do 20 life-and-death problems at your level."
>
> **Level filter on Technique page**: Use all 9 levels as pills. Students know exactly where they are in the ranking system (30k-9d). Don't collapse into 3 categories -- that loses precision. 9 pills is acceptable for desktop; on mobile, the pills should wrap to 2 rows.

#### 1P Go Professional Review #2 -- Study Flow Optimization

> **Principle**: Filtering should support the three core study modes: (1) systematic progression (level-by-level), (2) weakness targeting (filter to weak techniques at your level), (3) breadth review (cross-level technique practice).
>
> **Recommendation**: The filter should remember context when navigating between pages. If I'm on TechniqueFocusPage filtered to "Elementary" and I click "Ladder", the solve page should know I only want elementary ladder problems.
>
> **Count information is critical**: Showing "Ladder (42 at your level)" directly tells the student how much practice material exists. This motivates or redirects study.
>
> **Skip "Daily" and "Rush" filtering**: Daily challenges are curated by design -- filtering defeats their purpose. Rush mode has its own UX (time pressure, lives) that conflicts with browse filtering. These pages stay as-is.

#### 1P Go Professional Review #3 -- Curriculum Design (v3.2)

> **`killing` tag rejected (YAGNI)**: In Go pedagogy, "life and death" (shikatsu) is ONE discipline. Kill and live are the same skill from two sides. Pro books never separate "killing problems" from "life-and-death problems." The existing `living` tag is already a pedagogically questionable subset. Adding `killing` would create three overlapping objective tags for one discipline. D30 band-widening is approved for future-proofing; forced tag addition is not.
>
> **Training page tag filter placement**: Tag filtering does NOT belong on the Training *selection* page. Students browsing levels think in levels, not techniques. Tag filtering should appear INSIDE the puzzle-solving context — when the student has committed to a level and wants to focus on a specific technique within it.
>
> **9 level pills on mobile**: On 375px mobile, 9 pills produce 3 rows (~200px of chrome) before content. Unacceptable. Use the existing 3-category grouping (Beginner/Intermediate/Advanced) on mobile; expand to 9 pills on desktop only.

#### 1P Go Professional Review #4 -- Competitive Player (v3.2)

> **"All" count must be reactive**: When a cross-filter is active, the "All" pill's count must show the *filtered* total, not the global total. Otherwise it misleads students about available practice material.
>
> **Collections browse should NOT have level/tag filters**: Collections are curated sets with well-defined boundaries. Filtering the browse list adds complexity without matching user intent. Level/tag filters belong inside a collection's puzzle set, not above the collection list. This matches how Go teachers organize problem sets — you pick the set first, then focus within it.
>
> **Pill abbreviations need tooltips**: "U.Int" and "L.Dan" are not standard Go terminology. Add tooltips showing full name + rank range on hover. On mobile, show rank ranges ("10k-6k") instead of abbreviations.

#### UI/UX Expert Review #3 -- Mobile-First Analysis (v3.2)

> **z-index consistency**: FilterDropdown should use `var(--z-dropdown)` design tokens, not hardcoded Tailwind values. Migrate SettingsGear to use design tokens too (add to WP7).
>
> **Focus trap required**: FilterDropdown MUST have a focus trap (WCAG 2.1 AA). Tab should cycle within the dropdown when open. Escape returns focus to trigger button.
>
> **Active filter chip placement**: Chips should be INSIDE the filter strip (inline right), not below it. Placing below creates visual disconnection between filter controls and filter state.

#### UI/UX Expert Review #4 -- Information Architecture (v3.2)

> **"Clear all" conditional**: Show "Clear all filters" ONLY when 2+ filters are active. For single-filter pages, the chip dismiss "x" is sufficient.
>
> **FilterDropdown trigger must show selection**: When a tag is selected, the trigger pill text changes from "Filter by technique" to "{Tag name} ({count})" with accent styling. This eliminates the need to look elsewhere to see active state.
>
> **Filter state persistence**: Filters should persist in URL query parameters (`?level=130`) so the back button preserves filters. This is the simplest mechanism and requires no localStorage. Add to WP8.

### 5.2 Filtering Matrix -- Per Page

| Page | Primary Dimension | Filter 1 (new) | Filter 2 (new) | Component | Data Source |
|------|------------------|-----------------|-----------------|-----------|-------------|
| **Training browse** | Level (existing category pills) | -- | -- | *(no change -- tag filter moves to solve page per Go Pro #3)* | -- |
| **Training solve** | Level (from URL) | Tag FilterDropdown | -- | FilterDropdown (29 tags, grouped) | Level master -> `tags` distribution |
| **Technique** | Tag (existing category pills) | Level FilterBar (9 pills desktop, 3 mobile) | -- | FilterBar with counts, responsive | Tag master -> `levels` distribution |
| **Collections browse** | Collection type (existing search) | -- | -- | *(search only -- per Go Pro #4, level/tag filters inside collection)* | -- |
| **Collection detail** | Collection (from URL) | Level FilterBar | Tag FilterDropdown | Both | Collection master -> both distributions |
| **Random** | Category + Level (existing) | Tag FilterDropdown | -- | FilterDropdown | Level data from loaded entries |
| **Daily** | *(no change)* | -- | -- | -- | Curated, not filterable |
| **Rush** | *(no change)* | -- | -- | -- | Own UX, not filterable |

### 5.3 Component Specifications

#### FilterDropdown (NEW)

**When to use**: >8 options (tags: 28).

**Visual**: Looks like a single FilterBar pill that expands on click.

```
Closed state:
+-----------------------------+
| v  Filter by technique      |  <- rounded-full pill, same as FilterBar pill
+-----------------------------+

Open state:
+=================================+
| ^  Filter by technique          |  <- Open trigger (active if filter selected)
+=================================+
|  * All techniques               |  <- "All" option (clears filter)
|---------------------------------|
|  OBJECTIVES                     |  <- Category header (non-selectable, uppercase, xs, muted)
|    Life & Death (42)            |
|    Ko (18)                      |
|    Living (7)                   |
|    Seki (3)                     |
|---------------------------------|
|  TESUJI PATTERNS                |
|    Snapback (12)                |
|    Ladder (42)                  |  <- Count from master index distribution
|    Net (35)                     |
|    ...                          |
|---------------------------------|
|  TECHNIQUES                     |
|    Capture Race (17)            |
|    Eye Shape (8)                |
|    ...                          |
+=================================+
```

**Styling**:
- Trigger: exactly like a FilterBar pill (`rounded-full`, `min-h-[44px]`, `px-4`, same bg/border tokens)
- When active: accent bg (same as selected FilterBar pill)
- Dropdown panel: `rounded-xl`, `border`, `shadow-xl`, `z-[--z-dropdown]`, `max-h-[400px] overflow-y-auto`
- Category headers: `text-xs uppercase tracking-wider font-bold text-[--color-text-muted] px-4 py-2`
- Options: `px-4 py-2.5 min-h-[44px]` touch targets, hover bg-elevated
- Count badge: `text-xs text-[--color-text-muted]` right-aligned
- Backdrop: `fixed inset-0 z-[999]` transparent click-to-close (same pattern as SettingsGear)
- New icons needed: `ChevronDownIcon`, `CheckIcon` (add to `components/shared/icons/`)

**Accessibility**: `role="listbox"`, `aria-expanded`, `aria-labelledby`, `aria-selected` on active option, `Escape` to close + return focus to trigger, arrow keys to navigate, **focus trap** (Tab cycles within dropdown only, per WCAG 2.1 AA combobox pattern).

**Trigger text**: Idle = "Filter by technique". Active = "{Selected tag} ({count})" with accent bg.

#### FilterBar Extension (count badges)

Add optional `count?: number` to `FilterOption`:

```
+----------+ +--------------+ +--------------+ +-----------+
| All (57) | | Novice (12)  | | Beginner (8) | | Elem (15) | ...
+----------+ +--------------+ +--------------+ +-----------+
```

Count is `text-xs opacity-75` appended to label. When count is 0: option is disabled (`opacity-50`, not clickable).

#### Active Filter Chip

When a filter is applied, show a dismissible chip **inline in the filter strip** (right side, where ViewToggle or sort sits):

```
+------------------------------------------+
|  [FilterBar pills]     Ladder x          |  <- chip inline, not below
+------------------------------------------+
```

`rounded-full px-3 py-1 text-sm bg-accent/10 text-accent border border-accent/30`. The `x` dismisses that filter. "Clear all filters" shown ONLY when 2+ filters are active (per UX Expert #4). If chips overflow the row, wrap to a second line.

#### useFilterState Hook

```typescript
const { levelId, tagId, setLevel, setTag, clearAll, hasActiveFilters,
        levelOptions, tagOptions } = useFilterState({
  levelMaster: LevelMasterEntry[],   // from master index
  tagMaster: TagMasterEntry[],       // from master index
});
```

- `levelOptions`: all levels with counts (if tag selected, counts from tag's `levels` distribution)
- `tagOptions`: all tags with counts (if level selected, counts from level's `tags` distribution)
- Cascading: selecting a level recalculates tag counts, and vice versa
- `clearAll()` resets both to null

### 5.4 Page-by-Page Filter Layout

#### Training Page -- Tag Filter Moves to Solve Page

Training *selection* page: **no change** -- keep it clean with level cards only (per Go Professional #3).

Training *solve* page (inside PuzzleSetPlayer): add tag FilterDropdown above the board.
- FilterDropdown (Filter by technique) -- filters the puzzle set to matching tag
- Active filter chip inline, dismiss returns to full set
- Count budges from level master -> `tags` distribution

**Rationale**: Students on the selection page think in levels, not techniques. Tag filtering belongs INSIDE the puzzle-solving context, where the student is already committed to a level.

#### Technique Page -- Add Level Filter (Responsive)

Layer 2 filter strip adds a level FilterBar on the right:
- Left: FilterBar (All | Objectives | Techniques | Tesuji) -- existing
- Right (desktop >= 768px): FilterBar (All | Nov | Beg | Elem | Int | U.Int | Adv | L.Dan | H.Dan | Exp) -- 9 pills with `shortName`, tooltip shows full name + rank range
- Right (mobile < 768px): FilterBar (All | Beginner | Intermediate | Advanced) -- 3 category pills (same grouping as Training selection page)
- Active filter chip inline in filter strip right side (not below it per UX #3)
- Layer 3: Technique cards with "N at this level" counts

**Behavior**: When a level is selected, technique cards show puzzle count at that level. Techniques with 0 puzzles at that level are dimmed/hidden. All counts reactively update when cross-filter changes (per Go Pro #4).

#### Collections Page -- Search Only on Browse, Filters Inside Detail

Collections *browse* page: **no change** -- keep search bar only (per Go Professional #4). Curated collections have well-defined boundaries; filtering the browse list by level/tag adds complexity without matching user intent.

Collections *detail* page (inside puzzle set): add level FilterBar + tag FilterDropdown.
- Level FilterBar (responsive: 9 pills desktop, 3 mobile) + Tag FilterDropdown
- Active filter chip inline in filter strip
- Filter applies to puzzles within the collection
- Count badges from collection master -> both distributions

**Behavior**: Level + tag act as compound AND filter within the collection. "Clear all" button shown only when 2+ filters active (per UX #4).

---

## 6. Remediation Work Packages

### WP0: Config Pre-work + Big-Bang Wipe (G65-G71) -- v3.1

**Must execute BEFORE all other WPs. Foundational.**

**Branch**: `feature/wp0-config-bigbang`

| Step | Task | Files | Gap |
|------|------|-------|-----|
| 0.1 | Rename `numericId` to `id` in all 29 tag entries; rename old `id` (slug) to `slug` | `config/tags.json` | G66 |
| 0.2 | Rename `numericId` to `id` in all 159 collection entries | `config/collections.json` | G67 |
| 0.3 | Shift tesuji tag IDs +10 (20-42 becomes 30-52) | `config/tags.json` | G65 |
| 0.4 | Shift technique tag IDs +10 (50-72 becomes 60-82) | `config/tags.json` | G65 |
| 0.5 | ~~Add new objective tag `killing`~~ **DROPPED** per Go Professional Review #3 (YAGNI -- life-and-death already covers killing; pedagogically they are the same discipline) | -- | -- |
| 0.6 | Update `id_maps.py` -- read `id` instead of `numericId` (5 references) | `backend/.../core/id_maps.py` | G68 |
| 0.7 | Update `generate-types.ts` -- read `id` instead of `numericId` (7 references) | `frontend/scripts/generate-types.ts` | G69 |
| 0.8 | Run `npm run generate-types` to regenerate `generated-types.ts` for levels and tags | `frontend/src/lib/*/generated-types.ts` | G69 |
| 0.9 | Update `view-index.schema.json` tag ID range constraints to new bands | `config/schemas/view-index.schema.json` | G70 |
| 0.10 | **Wipe published data**: delete `yengo-puzzle-collections/sgf/`, `views/`, `.puzzle-inventory-state/` | Published data | G71 |
| 0.11 | **Wipe runtime**: delete `.pm-runtime/staging/`, `.pm-runtime/state/`, `.pm-runtime/logs/` (keep `raw/`) | Runtime state | G71 |
| 0.12 | **Wipe frontend state**: clear all `yengo:*` localStorage keys EXCEPT `yengo:settings` (preserves theme/sound prefs) | User guidance | G71 |
| 0.13 | **Update test tag IDs**: grep backend+frontend test files for old tag IDs (20,22,24,26,28,30,32,34,36,38,40,42,50,52,54,56,58,60,62,64,66,68,70,72) and update to shifted values (+10) | Test files | G65 |

**Verification**:
```
- [ ] `grep -r "numericId" config/` -> zero matches
- [ ] `grep -r "numericId" backend/puzzle_manager/core/id_maps.py` -> zero matches
- [ ] `grep -r "numericId" frontend/scripts/generate-types.ts` -> zero matches
- [ ] tags.json has NO `killing` tag (YAGNI -- dropped per Go Pro #3)
- [ ] tags.json tesuji IDs start at 30 (snapback), not 20
- [ ] tags.json technique IDs start at 60 (capture-race), not 50
- [ ] `yengo-puzzle-collections/sgf/` does not exist or is empty
- [ ] `yengo-puzzle-collections/views/` does not exist or is empty
- [ ] `tsc --noEmit` passes (generated types correct)
- [ ] `pytest -m unit` passes (id_maps reads new field names)
```

**Exit criteria**: All config files use `id` consistently. Tag bands widened. All published data wiped. Ready for fresh ingest.

---

### WP1: Backend -- Numeric View Directories (G6-G8, G10, G15-G16, G18-G19)

**The #1 blocker. Everything downstream depends on this.**

**Branch**: `feature/wp1-numeric-view-dirs`

| Step | Task | Files | Gap |
|------|------|-------|-----|
| 1.1 | Inject `IdMaps` into `PaginationWriter.__init__()` -- add `id_maps` parameter | `pagination_writer.py` | G6-G8 |
| 1.2 | Change `get_level_dir(level)` to use `str(self._id_maps.level_slug_to_id(level))` | `pagination_writer.py` L364-372 | G6 |
| 1.3 | Change `get_tag_dir(tag)` to use `str(self._id_maps.tag_slug_to_id(tag))` | `pagination_writer.py` L375-383 | G7 |
| 1.4 | Add `get_collection_dir(collection)` using `collection_slug_to_id()` | `pagination_writer.py` | G8 |
| 1.5 | Update `_append_to_paginated()` -- route through new `get_*_dir()` | `pagination_writer.py` L571-577 | G6-G8 |
| 1.6 | Update `_recover_state_from_files()` -- numeric-only dir names to slugs (no mixed-mode needed after big-bang wipe) | `pagination_writer.py` L248-259 | G18 |
| 1.7 | Update `_rebuild_index_structure()` -- directory creation via `get_*_dir()` | `pagination_writer.py` L1076-1079 | G19 |
| 1.8 | Add `"id"` field to all master index entries | `pagination_writer.py` L710-790 | G10 |
| 1.9 | Update master index to emit numeric dir references | `pagination_writer.py` | G15-G16 |
| 1.10 | Update rollback dir iteration -- read numeric dirs, translate to slugs | `rollback.py` L761-810 | G15 |
| 1.11 | Update maintenance/views.py regeneration paths | `maintenance/views.py` | G15-G16 |
| 1.12 | Update `publish.py` -- pass `IdMaps` to `PaginationWriter()` | `stages/publish.py` | G6 |
| 1.13 | Update 12+ test files with slug-based directory assertions to numeric | All pagination tests | G15 |

**Verification**:
```
- [ ] `ls yengo-puzzle-collections/views/by-level/` -> only numeric dirs (110/, 120/, etc.) after fresh publish
- [ ] `ls yengo-puzzle-collections/views/by-tag/` -> only numeric dirs (30/, 32/, etc.)
- [ ] `ls yengo-puzzle-collections/views/by-collection/` -> only numeric dirs (1/, 2/, etc.)
- [ ] Master index entries contain `"id"` field
- [ ] .pagination-state.json keys are slugs (internal)
- [ ] `pytest -m "not (cli or slow)"` passes
```

**Exit criteria**: All backend code produces numeric dirs. State keys stay as slugs. All tests pass. *(Actual dirs created by fresh pipeline run, not by this WP.)*

---

### WP2: Backend Cleanup (G1, G4-G5, G11-G14, G17)

**Branch**: `feature/wp2-backend-cleanup`

| Step | Task | Gap |
|------|------|-----|
| 2.1 | Fix `pagination_writer.py` -- replace `"sequence_number"` with `"n"` | G1, G17 |
| 2.2 | Delete `_update_indexes_flat()` from publish.py L508-572 | G4 |
| 2.3 | Delete `_update_collection_indexes()` flat fallback from publish.py L574-636 | G5 |
| 2.4 | Remove `if pagination_config.enabled` router -- always use paginated path | G4-G5 |
| 2.5 | Create `make_compact_entry()` test helper to DRY fixture construction | G11-G14 |
| 2.6 | Update test_pagination_contracts.py fixtures to `{p, l, t, c, x}` shapes | G11 |
| 2.7 | Update test_rollback_integration.py fixtures to compact shapes | G12 |
| 2.8 | Update test_pagination_benchmark.py fixtures to compact shapes | G13 |
| 2.9 | Update test_daily_posix.py fixtures to compact shapes | G14 |

**Verification**:
```
- [ ] `grep -r "sequence_number" backend/puzzle_manager/ --include="*.py"` -> zero matches (including tests)
- [ ] `grep -r "_update_indexes_flat" backend/puzzle_manager/` -> zero matches
- [ ] Test fixtures use {p, l, t, c, x} shapes only
- [ ] `pytest -m "not (cli or slow)"` green
```

**Exit criteria**: Zero flat-mode code. Zero old entry shapes in tests. *(Published data fixed by WP0 wipe + fresh ingest.)*

---

### WP3: Backend Daily (G2-G3, G9)

**Branch**: `feature/wp3-daily-master`

| Step | Task | Gap |
|------|------|-----|
| 3.1 | Evaluate whether `PuzzleRef` needs compact format or stays as daily-specific model | G2 |
| 3.2 | Create daily master index generator -- `views/daily/index.json` | G3 |
| 3.3 | Include level + tag distributions per daily challenge date | G9 |
| 3.4 | Wire daily master index generation into publish pipeline | G3 |

**Verification**:
```
- [ ] `views/daily/index.json` exists after fresh publish with version "2.0"
- [ ] Daily master index has level + tag distributions
- [ ] `pytest -m "not (cli or slow)"` passes
```

**Exit criteria**: `views/daily/index.json` populated. Backend tests pass.

---

### WP4: Frontend -- `entryDecoder.ts` + `configService.ts` (G20-G23)

**Branch**: `feature/wp4-decode-config`

| Step | Task | Gap |
|------|------|-----|
| 4.1 | Create `services/configService.ts` -- sync for levels/tags, async init for collections | G20 |
| 4.2 | Create `services/entryDecoder.ts` -- port ALL logic from `compact-entry.ts` | G22 |
| 4.3 | Add `DecodedEntry` type with full fields including complexity | G21 |
| 4.4 | Add unified `decodeEntry()` + keep convenience wrappers | G22 |
| 4.5 | Add `id: number` to `MasterIndexEntry` type | G23 |
| 4.6 | Delete `lib/puzzle/compact-entry.ts` -- update all imports | G22 |
| 4.7 | Delete `lib/puzzle/id-maps.ts` -- absorb into `configService.ts` | G20 |
| 4.8 | Port `tests/unit/compact-entry.test.ts` to test `entryDecoder.ts` | G22 |
| 4.9 | Port `tests/unit/id-maps.test.ts` to test `configService.ts` | G20 |
| 4.10 | Update `VIEW_PATHS` -- accept `number` for level/tag/collection path builders | G26 |
| 4.11 | Write unit tests for configService and entryDecoder | -- |

**Verification**:
```
- [ ] `grep -r "compact-entry" frontend/src/` -> zero matches
- [ ] `grep -r "id-maps" frontend/src/` -> zero matches
- [ ] `entryDecoder.ts` exists with DecodedEntry type including complexity
- [ ] `configService.ts` exists with sync level/tag lookups
- [ ] `tsc --noEmit` passes
- [ ] `npm test` passes
```

**Exit criteria**: No `compact-entry.ts` or `id-maps.ts` imports. TypeScript and tests green.

---

### WP5: Frontend -- URL Migration to Numeric IDs (G24-G27)

**Branch**: `feature/wp5-numeric-urls`
**Depends on**: WP1 (backend dirs exist) + WP4 (VIEW_PATHS updated)

| Step | Task | Gap |
|------|------|-----|
| 5.1 | Update `loadLevelIndex()` -- resolve slug to numeric ID | G24 |
| 5.2 | Update `loadTagIndex()` / `loadTagIndexV2()` -- same pattern | G25 |
| 5.3 | Fix direct interpolation in collectionService.ts -- use `VIEW_PATHS` | G27 |
| 5.4 | Fix pagination.ts legacy single-file path | G27 |
| 5.5 | Add `loadLevelMasterIndex()` to puzzleLoader.ts | -- |
| 5.6 | Add `loadCollectionMasterIndex()` to collectionService.ts | -- |

**Verification**:
```
- [ ] `grep -r "by-level/beginner" frontend/src/` -> zero matches
- [ ] VIEW_PATHS accepts number, not string
- [ ] Dev server loads all pages without 404
- [ ] loadLevelMasterIndex() returns data
- [ ] loadCollectionMasterIndex() returns data
```

**Exit criteria**: All view URLs use numeric IDs. Pages load correctly on dev server.

---

### WP6: Frontend -- Legacy Removal + Hardcoded Slugs (G28-G40)

**Branch**: `feature/wp6-legacy-removal`
**Depends on**: WP4 + WP5

| Step | Task | Gap |
|------|------|-----|
| 6.1 | Delete `filterPuzzlesByLevel()`, `filterPuzzlesByRank()` | G28-G29 |
| 6.2 | Delete `TagPuzzleEntry`, `TagIndex` types | G30 |
| 6.3 | Remove `Array.isArray()` legacy fallback from `loadLevelIndex()` | G31 |
| 6.4 | Remove `detectCollectionFormat()` | G32 |
| 6.5 | Delete `ViewIndex`, `SkillLevelIndex`, `TagViewIndex` from manifest.ts | G33 |
| 6.6 | Replace `TAG_DISPLAY_INFO` with `configService.getAllTags()` | G34 |
| 6.7 | Replace `SLUG_OVERRIDES` with config lookups | G35 |
| 6.8 | Replace `PUZZLE_TAGS` with `configService.getAllTags()` | G36 |
| 6.9 | Replace `CATEGORY_LEVELS` with config-derived grouping | G37 |
| 6.10 | Replace `LEVEL_CATEGORY` with config-derived reverse mapping | G38 |
| 6.11 | Replace hardcoded `'beginner'` defaults with config references | G39 |
| 6.12 | Replace hardcoded `'novice'`/`'elementary'` defaults with config references | G40 |

**Verification**:
```
- [ ] `grep -r "TAG_DISPLAY_INFO\|SLUG_OVERRIDES\|PUZZLE_TAGS\|CATEGORY_LEVELS\|LEVEL_CATEGORY" frontend/src/` -> zero
- [ ] `grep -r "'beginner'" frontend/src/ --include="*.ts*" | grep -v generated | grep -v test` -> zero
- [ ] `grep -r "filterPuzzlesByLevel\|filterPuzzlesByRank\|TagPuzzleEntry" frontend/src/` -> zero
- [ ] `grep -r "ViewIndex\|SkillLevelIndex\|TagViewIndex" frontend/src/` -> zero
- [ ] `tsc --noEmit` passes
```

**Exit criteria**: Zero hardcoded slug constants in src/.

---

### WP7: Frontend -- Filter Infrastructure (G41-G43)

**Branch**: `feature/wp7-filter-components`
**Depends on**: WP4 (configService for tag metadata)

| Step | Task | Gap |
|------|------|-----|
| 7.1 | Create `ChevronDownIcon` and `CheckIcon` SVG components | -- |
| 7.2 | Create `FilterDropdown.tsx` -- per section 5.3 spec | G41 |
| 7.3 | Extend `FilterBar` -- add `count?: number` to `FilterOption` | G42 |
| 7.4 | Create `ActiveFilterChip.tsx` -- dismissible chip | -- |
| 7.5 | Create `useFilterState.ts` hook -- per section 5.3 spec | G43 |
| 7.6 | Unit test `FilterDropdown` | -- |
| 7.7 | Unit test `useFilterState` | -- |

**Verification**:
```
- [ ] FilterDropdown.tsx exists with aria-expanded
- [ ] FilterBar accepts count prop
- [ ] useFilterState.ts exists
- [ ] `npm test` -- FilterDropdown and useFilterState tests pass
```

**Exit criteria**: Filter components exist with tests.

---

### WP8: Frontend -- Page Integration (G44-G52)

**Branch**: `feature/wp8-page-integration`
**Depends on**: WP5 (master loaders) + WP7 (filter components)

| Step | Task | Gap |
|------|------|-----|
| 8.1 | Training solve page -- add tag FilterDropdown inside PuzzleSetPlayer chrome | G44 |
| 8.2 | Training solve page -- load level master index for tag distribution counts | G44 |
| 8.3 | Training solve page -- filter puzzle set by tag | G44 |
| 8.4 | TechniqueFocusPage -- add responsive level FilterBar (9 pills desktop, 3 mobile) | G45 |
| 8.5 | TechniqueFocusPage -- load tag master index for level distributions | G45 |
| 8.6 | TechniqueFocusPage -- filter technique cards by level, reactive counts | G45 |
| 8.7 | Collection detail page -- add level FilterBar + tag FilterDropdown inside PuzzleSetPlayer | G46 |
| 8.8 | Collection detail page -- load collection master index for distributions | G46 |
| 8.9 | Collection detail page -- filter collection puzzles by level + tag (compound AND) | G46 |
| 8.10 | RandomPage -- add tag FilterDropdown alongside existing level filter | G47 |
| 8.11 | Add ActiveFilterChip inline in filter strip (not below) on all filter-enabled pages | G48 |
| 8.12 | "Clear all filters" shown only when 2+ filters active (per UX Expert #4) | G49 |
| 8.13 | Filter change mid-session -- reset position, preserve progress | G50 |
| 8.14 | DailyChallengePage -- consume daily master index for info display | G51 |
| 8.15 | Filter state in URL query params (`?level=130&tag=34`) for back-button persistence (per UX #4) | -- |
| 8.16 | Handle empty filter results -- "No puzzles match" + "Clear filters" action | G49 |
| 8.17 | Responsive FilterBar: 9 pills desktop, 3 category pills mobile (per Go Pro #3) | G45 |
| 8.18 | Level pill tooltips: hover shows full name + rank range (per Go Pro #4) | -- |
| 8.19 | Wire RandomPage tag filter to `onSelectRandomPuzzle` callback — pass `tagId` so parent constrains puzzle selection (F7) | -- |
| 8.20 | Wire CollectionViewPage level+tag filter to `CollectionPuzzleLoader` — pass `levelId`/`tagId` so loader filters puzzle set (F8) | -- |

**Verification**:
```
- [ ] Training, Technique, Collections, Random pages render filters
- [ ] Master index distributions power count badges
- [ ] Empty filter state renders "No puzzles match"
- [ ] Filter change resets position without losing progress
- [ ] `npm test` + `tsc --noEmit` pass
```

**Exit criteria**: All 4 browse pages have functional filters.

---

### WP9: Visual Testing (G53-G63)

**Branch**: `feature/wp9-visual-tests`
**Depends on**: WP8

| Step | Task | Gap |
|------|------|-----|
| 9.1 | Run `npm run test:visual` -- verify existing baselines still pass | -- |
| 9.2 | Create `FilterBar-extended.visual.spec.ts` | G53 |
| 9.3 | Create `FilterDropdown.visual.spec.ts` | G54 |
| 9.4 | Create `TrainingPage-filtered.visual.spec.ts` | G55 |
| 9.5 | Create `TechniqueFocus-filtered.visual.spec.ts` | G56 |
| 9.6 | Create `CollectionsPage-filtered.visual.spec.ts` | G57 |
| 9.7 | Create `ActiveFilterChip.visual.spec.ts` | G58 |
| 9.8 | Run all specs across Desktop/Tablet/Mobile x Light/Dark | G59-G63 |
| 9.9 | Update existing baselines for modified pages | -- |

**Verification**:
```
- [ ] 6 new visual spec files exist in tests/visual/specs/
- [ ] `npm run test:visual` passes against updated baselines
- [ ] Mobile + dark mode screenshots reviewed
```

**Exit criteria**: 6 new visual specs. All 39+ visual tests pass.

---

### WP10: Documentation (G64)

**Branch**: `feature/wp10-docs`

| Step | Task | Gap |
|------|------|-----|
| 10.1 | Create `docs/concepts/numeric-id-scheme.md` | G64 |
| 10.2 | Update `docs/architecture/backend/view-index-pagination.md` -- fix `sequence_number`, `pagination_threshold` | -- |
| 10.3 | Update `docs/architecture/backend/integrity.md` -- fix `sequence_number` reference | -- |
| 10.4 | Update `docs/reference/view-index-schema.md` -- fix `sequence_number`, update file references | -- |
| 10.5 | Update `docs/concepts/collections.md` -- fix `sequence_number` (2 occurrences) | -- |
| 10.6 | Update `docs/architecture/frontend/view-index-types.md` -- replace compact-entry/id-maps refs (5 occurrences) | -- |
| 10.7 | Update `docs/architecture/frontend/testing.md` -- fix slug-based view paths | -- |
| 10.8 | Update CLAUDE.md -- replace `compact-entry.ts`/`id-maps.ts` references | -- |
| 10.9 | Update `.github/copilot-instructions.md` -- same | -- |

**Verification**:
```
- [ ] `grep -r "sequence_number" docs/` -> zero matches
- [ ] `grep -r "compact-entry.ts" docs/ CLAUDE.md .github/` -> zero matches
- [ ] `grep -r "id-maps.ts" docs/ CLAUDE.md .github/` -> zero matches
- [ ] `grep -r "numericId" docs/ CLAUDE.md .github/` -> zero matches
- [ ] `docs/concepts/numeric-id-scheme.md` exists
```

**Exit criteria**: All docs reflect v4.0 numeric dir scheme. No stale references.

---

### WP11: Pipeline Validation (Post-Ingest) -- v3.1

**Branch**: N/A (manual validation after fresh pipeline run)
**Depends on**: WP0 (data wiped) + WP1+WP2 (code changes) + fresh pipeline ingest

| Step | Task |
|------|------|
| 11.1 | Run full pipeline: `python -m backend.puzzle_manager run --source {all sources}` |
| 11.2 | Verify view dirs are numeric: `ls views/by-level/`, `ls views/by-tag/`, `ls views/by-collection/` |
| 11.3 | Verify master indexes have `"id"` field and distributions |
| 11.4 | Verify collection entries use `"n"` not `"sequence_number"` |
| 11.5 | **Rollback individual**: rollback latest run, verify puzzle count decreases |
| 11.6 | **Re-ingest after rollback**: re-run pipeline, verify puzzles restored |
| 11.7 | **Rollback bulk**: rollback each run by `--run-id` (no `--all` flag), verify zero puzzles/views/inventory |
| 11.8 | **Rebuild**: `rebuild` from SGF files, verify views match SGF count |
| 11.9 | **Validate**: `validate` passes with zero errors |
| 11.10 | **Inventory check**: `inventory check` matches actual file counts |
| 11.11 | **Trace data**: verify published SGF files contain `YM` property with trace_id, source, run_id |
| 11.12 | **Publish log cross-reference**: `publish-log search --puzzle-id {sample_hash}` returns result |
| 11.13 | Run automated test suite: `pytest tests/integration/test_rollback_posix.py tests/integration/test_inventory_check.py tests/integration/test_inventory_cli.py tests/integration/test_inventory_integration.py tests/integration/test_inventory_publish.py -v` |

**Verification**:
```
- [x] All 13 steps above pass (validated 2026-02-20)
- [x] After rollback+re-ingest cycle: final count matches initial count (1083)
- [x] Trace data (YM property) exists in every published puzzle
- [x] `pytest -m "not slow"` full suite green (1552 passed, 0 failed)
```

**Exit criteria**: Pipeline integrity confirmed. Rollback (individual + bulk per-run-id), rebuild, inventory, trace all functional.

**WP11 Execution Notes (2026-02-20)**:
- `trace` CLI subcommand documented in CLAUDE.md was not implemented; replaced with `publish-log` commands
- `rollback --all` does not exist; bulk rollback done by rolling back each run-id individually
- Test file names updated to match actual files (test_rollback_posix.py, test_inventory_*.py)
- Inventory `--check` has Unicode encoding issue on Windows; use `PYTHONIOENCODING=utf-8`
- After rollback, publish log entries from rolled-back runs are not purged (append-only audit log)
- Each pipeline run produces unique content hashes due to trace_id/run_id in YM metadata

---

## 7. Execution Order & Dependencies

```
WP0 (Config + Big-Bang Wipe) -- FIRST, before everything
  |
  v
WP1 (Backend numeric dirs) --> WP2 (Backend cleanup) --> WP3 (Daily)
        |                              |                      |
WP4 (entryDecoder + configService) ----+                      |
        |                              v                      v
        +-------------------> WP5 (URL migration) --> WP6 (Legacy removal)
                                                            |
                                                       WP7 (Filter components) --> WP8 (Page integration) --> WP9 (Visual)
                                                                                                                    |
                                                                                                               WP10 (Docs)
  [After fresh pipeline ingest]
  WP11 (Pipeline Validation) -- LAST, after data is published
```

**Dependencies (explicit)**:
- WP0 must complete before ALL other WPs (config contract)
- WP4 depends on WP0 (generated-types must reflect new tag IDs)
- WP5 depends on WP1 + WP4
- WP7 depends on WP4
- WP8 depends on WP5 + WP7
- WP11 depends on WP0 + WP1 + WP2 + fresh pipeline run

**Parallelizable**: WP1 + WP4 (different codebases, both after WP0). WP2 + WP4. WP10 after any WP.

**Critical path**: WP0 -> WP1 -> WP5 -> WP8 -> [fresh ingest] -> WP11

---

## 8. Risks and Mitigations

| # | Risk | Severity | Mitigation | WP |
|---|------|----------|------------|-----|
| R1 | `loadLevelIndex()` 404 after D23 | **Critical** | WP5 must execute atomically with WP1 | WP1+WP5 |
| R2 | State recovery breaks with numeric dirs | Medium | `_recover_state_from_files()` translates numeric to slug | WP1 |
| R3 | 12+ test files need fixture updates | Medium | Batch update in WP2, validate with `pytest -m unit` | WP2 |
| R4 | FilterDropdown accessibility | Medium | Keyboard nav + aria roles, follow SettingsGear pattern | WP7 |
| R5 | 9 level pills overflow on mobile | Low | `flex-wrap` in FilterBar -- pills wrap to 2 rows | WP7 |
| R6 | Daily master index complexity | Low | Simple `{version, dates}` structure | WP3 |
| R7 | Tag ID shift breaks cached/staging data | Low | Mitigated by big-bang wipe (WP0). No old numeric IDs survive. SGF `YT` uses slugs, not numeric IDs. | WP0 |

---

## 9. Numeric ID Schemes (Reference)

### 9.1 Level IDs (Sparse, Go-Rank-Aligned)

Kyu=100s, Dan=200s. Gaps of 10 allow insertion.

| ID | Slug | Rank Range | Insert example |
|----|------|-----------|---------------|
| 110 | `novice` | 30k-26k | 100=pre-novice |
| 120 | `beginner` | 25k-21k | 121,125=sub-split |
| 130 | `elementary` | 20k-16k | |
| 140 | `intermediate` | 15k-11k | 141,145,148=3-way split |
| 150 | `upper-intermediate` | 10k-6k | |
| 160 | `advanced` | 5k-1k | 170=approaching-dan |
| 210 | `low-dan` | 1d-3d | |
| 220 | `high-dan` | 4d-6d | |
| 230 | `expert` | 7d-9d | 240=professional |

### 9.2 Tag IDs (Sparse by Category, Pedagogical Order) -- Updated D30

| Range | Category | Tags |
|-------|----------|------|
| **10-28** | Objectives | 10=life-and-death, 12=ko, 14=living, 16=seki *(5 spare even slots: 18,20,22,24,26,28 for future)* |
| **30-52** | Tesuji | 30=snapback, 32=double-atari, 34=ladder, 36=net, 38=throw-in, 40=clamp, 42=nakade, 44=connect-and-die, 46=under-the-stones, 48=liberty-shortage, 50=vital-point, 52=tesuji |
| **60-82** | Techniques | 60=capture-race, 62=eye-shape, 64=dead-shapes, 66=escape, 68=connection, 70=cutting, 72=sacrifice, 74=corner, 76=shape, 78=endgame, 80=joseki, 82=fuseki |
| **84-98** | Future | Reserved for new categories |

### 9.3 Collection IDs (Sequential)

`config/collections.json` uses `id: 1..159+` (renamed from `numericId` per D31). Append-only, never reassigned. View dirs use numeric IDs (D22a).

---

## 10. Systems Architect & Staff Engineer Review

### Review #1 -- Principal Systems Architect

> **v3.0 Assessment**: The v3 plan correctly identifies the D23 gap as the critical blocker. The decision to keep state keys as slugs while filesystem dirs go numeric is the right boundary -- it minimizes blast radius. The `IdMaps` injection into `PaginationWriter` follows the existing dependency injection pattern in the codebase.
>
> **Approved with conditions**:
> 1. WP1+WP5 must deploy atomically (same merge, same publish)
> 2. Update `view-index.schema.json` to require `"id"` in master index entries
> 3. Add a migration test that verifies numeric dir names match IdMaps output
>
> **v3.1 Review (2026-02-18)**:
>
> **Flaw found -- D25 contradicts D30**: Plan marked D25 "Done" but D30 changes the tag ranges. Fixed: D25 now marked SUPERSEDED.
>
> **Flaw found -- Supplement plan was a separate document**: Config rename (D31), tag rebalance (D30), big-bang wipe, verification checklists, and pipeline testing existed outside the main plan. This is the pattern that caused the v2 gap. Fixed: All merged into v3.1 as WP0, WP11, and inline verification blocks.
>
> **Flaw found -- WP1 step 1.14 conflicted with big-bang wipe**: Republish step was moot. Fixed: Removed. WP1 is now code-only; data creation happens via fresh pipeline run.
>
> **Flaw found -- §11 said config was "Done" when D30/D31 change it**: Fixed: Status updated.
>
> **Simplification approved**: `_recover_state_from_files()` no longer needs mixed-mode (slug+numeric) handling. Big-bang wipe means only numeric dirs will exist post-migration.

### Review #2 -- Staff Engineer

> **Assessment**: The gap audit is thorough. 64 gaps is significant but most are low/medium severity cleanup tasks (G28-G40). The critical path is clear: WP1 -> WP5 -> WP8.
>
> **Concern -- Rollback with numeric dirs**: The rollback code iterates directory names. After WP1, it reads `"130"` instead of `"elementary"`. The id-to-slug translation must handle missing mappings gracefully. Add a `try/except` with logging for unknown numeric dir names.
>
> **Concern -- `_recover_state_from_files()` race condition**: If a publish is interrupted after creating some numeric dirs but before updating state, recovery will scan partial numeric dirs. Handle a mix of old (slug) and new (numeric) dir names during transition.
>
> **Concern -- Test fixture volume**: G11-G14 affect 4 test files with 50-100 individual fixture changes. Create a `make_compact_entry()` test helper to DRY fixture construction and future-proof against further schema changes.
>
> **Concern -- `entryDecoder.ts` dual responsibility**: Consider keeping `isCompactEntry()` co-located with the type definition rather than the decoder.
>
> **Approved with conditions**:
> 1. Add graceful fallback in rollback for unknown numeric dir names
> 2. Create a `make_compact_entry()` test helper to DRY fixture construction (evaluate during WP2 -- if <20 fixtures, use raw literals)
> 3. Co-locate `isCompactEntry()` with the type definition rather than the decoder
>
> **v3.1 Review (2026-02-18)**:
>
> **Simplification**: Condition #3 from v3.0 (mixed slug/numeric dir handling) is **withdrawn** -- big-bang wipe eliminates the transition period. Only numeric dirs will exist.
>
> **New concern -- Two planning documents**: The supplement plan was a second document. This is the exact anti-pattern that caused the v2 gap (information in one place, decisions in another). Fixed: All supplement content merged into the main plan as WP0, WP11, D30-D31, G65-G71.
>
> **New concern -- Tag shift breaks test assertions**: Any test that hardcodes `24` for ladder or `50` for capture-race will fail after the +10 shift. WP0 must include a grep + fix pass across test files referencing old tag IDs.
>
> **Approved with addition**: Add step to WP0 to grep for old tag IDs in test files and update them.

---

## 11. Files Inventory (Updated)

### Config (needs WP0 updates -- D30, D31)
| File | Status |
|------|--------|
| `config/puzzle-levels.json` | Done (sparse IDs, v2.0) |
| `config/tags.json` | **Needs update**: rename `numericId` to `id`, shift tesuji/tech +10, add `killing` (D30, D31) |
| `config/collections.json` | **Needs update**: rename `numericId` to `id` (D31) |
| `config/schemas/view-index.schema.json` | **Needs update**: `"id"` in master index entries + new tag ID ranges (D30) |

### Backend
| File | Change | WP | Status |
|------|--------|-----|--------|
| `core/id_maps.py` | Read `id` instead of `numericId` (5 refs) | WP0 | **Needs update** |
| `core/pagination_writer.py` | Inject IdMaps, numeric dirs, fix "sequence_number" to "n", add master index "id" field | WP1, WP2 | Not done |
| `core/pagination_models.py` | No changes needed | -- | Done |
| `stages/publish.py` | Pass IdMaps, delete flat fallback code | WP1, WP2 | Not done |
| `maintenance/views.py` | Numeric dir paths | WP1 | Not done |
| `rollback.py` | Numeric dir iteration with id-to-slug translation | WP1 | Not done |
| `models/daily.py` | Evaluate PuzzleRef compact format | WP3 | Not done |
| Tests (12+ files) | Fixture shapes + dir path assertions | WP1, WP2 | Not done |

### Frontend
| File | Change | WP | Status |
|------|--------|-----|--------|
| `services/configService.ts` | **NEW** -- unified config lookup | WP4 | Not done |
| `services/entryDecoder.ts` | **NEW** -- replaces compact-entry.ts | WP4 | Not done |
| `lib/puzzle/compact-entry.ts` | **DELETE** -- absorbed into entryDecoder | WP4 | Not done |
| `lib/puzzle/id-maps.ts` | **DELETE** -- absorbed into configService | WP4 | Not done |
| `types/indexes.ts` | Update VIEW_PATHS to numeric, add `id` to MasterIndexEntry | WP4 | Not done |
| `services/puzzleLoader.ts` | `loadLevelIndex()` numeric URL + `loadLevelMasterIndex()` | WP5 | Not done |
| `lib/puzzle/tag-loader.ts` | `loadTagIndex()` numeric URL, delete legacy types/functions | WP5, WP6 | Not done |
| `services/collectionService.ts` | Remove detectCollectionFormat, TAG_DISPLAY_INFO, numeric URLs | WP5, WP6 | Not done |
| `lib/slug-formatter.ts` | Remove SLUG_OVERRIDES | WP6 | Not done |
| `components/Settings/SettingsPanel.tsx` | Remove PUZZLE_TAGS | WP6 | Not done |
| `pages/RandomPage.tsx` | Replace CATEGORY_LEVELS, add tag filter | WP6, WP8 | Not done |
| `pages/TrainingSelectionPage.tsx` | Replace LEVEL_CATEGORY, add tag FilterDropdown | WP6, WP8 | Not done |
| `pages/TechniqueFocusPage.tsx` | Add level FilterBar | WP8 | Not done |
| `pages/CollectionsPage.tsx` | Add level FilterBar + tag FilterDropdown | WP8 | Not done |
| `types/manifest.ts` | Delete ViewIndex, SkillLevelIndex, TagViewIndex | WP6 | Not done |
| `components/shared/FilterDropdown.tsx` | **NEW** | WP7 | Not done |
| `components/shared/FilterBar.tsx` | Add count badge | WP7 | Not done |
| `components/shared/ActiveFilterChip.tsx` | **NEW** | WP7 | Not done |
| `components/shared/icons/ChevronDownIcon.tsx` | **NEW** | WP7 | Not done |
| `components/shared/icons/CheckIcon.tsx` | **NEW** | WP7 | Not done |
| `hooks/useFilterState.ts` | **NEW** | WP7 | Not done |

### Visual Tests (NEW)
| File | WP | Status |
|------|-----|--------|
| `tests/visual/specs/FilterBar-extended.visual.spec.ts` | WP9 | Not done |
| `tests/visual/specs/FilterDropdown.visual.spec.ts` | WP9 | Not done |
| `tests/visual/specs/TrainingPage-filtered.visual.spec.ts` | WP9 | Not done |
| `tests/visual/specs/TechniqueFocus-filtered.visual.spec.ts` | WP9 | Not done |
| `tests/visual/specs/CollectionsPage-filtered.visual.spec.ts` | WP9 | Not done |
| `tests/visual/specs/ActiveFilterChip.visual.spec.ts` | WP9 | Not done |

### Documentation
| File | Change | WP | Status |
|------|--------|-----|--------|
| `docs/concepts/numeric-id-scheme.md` | **NEW** | WP10 | Not done |
| `CLAUDE.md` | Update decode/config references | WP10 | Partial |
| `.github/copilot-instructions.md` | Update decode/config references | WP10 | Partial |

---

## 12. Audit Trail

### v2 to v3 Gap Audit (2026-02-18)

**Conducted by**: AI agent, cross-referencing v2 plan steps against actual codebase state.

**Method**:
1. Subagent research for each phase (0-11) checking every step against actual files
2. Backend: read pagination_writer.py, publish.py, pagination_models.py, id_maps.py, maintenance/views.py, rollback.py, daily models; listed actual view directories; read published JSON files
3. Frontend: searched for every component/type/function named in plan; read every loader, every type file, every page component; audited hardcoded slugs
4. Documentation: checked existence of every named doc file

**Finding**: 36% completion (39/108 steps). Critical D23 (numeric view directories) was never implemented. Phases 8-10 were 0% complete. The claim that "both sides agree on the old convention" was flagged as an unacceptable rationalization -- the plan committed to numeric directories and they were not delivered.

**v3 amendments**:
- D22a: Collections also switch to numeric dirs (user decision, overriding original D22)
- D26: Create `entryDecoder.ts`, delete `compact-entry.ts`
- D27: Backend state keys stay as slugs, only filesystem dirs go numeric
- D28: FilterBar pills + FilterDropdown for >8 options
- D29: `generated-types.ts` (build-time) for levels/tags, async for collections
- Expert reviews from 2 UI/UX experts and 2 1P Go professionals documented in section 5.1
- Systems Architect and Staff Engineer reviews documented in section 10

### v3.1 Architect Review Integration (2026-02-18)

**Conducted by**: Principal Systems Architect (purist) + Staff Engineer critical review of v3.0 + supplement plan.

**6 structural flaws found and fixed**:
1. D25 marked "Done" but D30 changes it → D25 now SUPERSEDED by D30
2. `numericId` → `id` rename not tracked in any gap → Added G65-G69, D31
3. Big-bang wipe contradicts WP1 step 1.14 → Removed republish steps, created WP0
4. Tag ID shift has no WP → Created WP0 with 12 steps
5. Verification checklists not in main plan → Added to every WP (WP0-WP11)
6. Pipeline testing has no WP → Created WP11

**New items added**: D30, D31, G65-G71, WP0 (Config + Big-Bang), WP11 (Pipeline Validation)
**Removed items**: WP1 step 1.14, WP2 step 2.10 (moot with big-bang wipe)
**Simplified**: WP1 step 1.6 (no mixed-mode dir handling needed)
**Updated**: §9.2 (new tag ranges), §11 (config status), §7 (dependency graph), §10 (reviews)

### v3.2 Second Architect Review (2026-02-18)

**Conducted by**: Fresh adversarial review by Principal Systems Architect + Staff Engineer.

**6 new issues found and fixed**:

| # | Flaw | Fix |
|---|------|-----|
| 7 | §1 entry example used old tag IDs (`t:[12,24,26]`) — ladder is now 34, net 36 | Updated example to `[12,34,36]` |
| 8 | §3 Phase Scorecard says "100%" for Phase 0, misleading after WP0 additions | Added disclaimer noting WP0/WP11 expand total to ~133 steps |
| 9 | WP0 step 0.12 "wipe frontend state" was vague — which localStorage keys? | Specified: clear all `yengo:*` keys except `yengo:settings` |
| 10 | Header said "64 gaps" but G65-G71 bring total to 71; completion % wrong | Updated to "71 gaps, ~29% complete" |
| 11 | WP4 depends on WP0 (generated-types) but dependency graph didn't show it | Added explicit dependency list to §7 |
| 12 | No risk for tag ID shift breaking cached data | Added R7 noting big-bang wipe mitigates this |

**Staff Engineer additions**:
- WP2 verification now checks tests too (was excluding them with `grep -v test`)
- WP0 step 0.13 added: grep+fix old tag IDs in test files
- `killing` tag: specified full fields (name, description, aliases), noted alias collision with `life-and-death`
- WP10 expanded from 4 steps to 9 steps covering all 9 doc files with stale references
- WP4 steps 4.8-4.9 added: port test files for deleted modules

### v3.2 Go Professional + UX Expert Review (2026-02-18)

**Conducted by**: 2 new 1P Go Professionals (#3 curriculum designer, #4 competitive player) + 2 new UX Experts (#3 mobile-first, #4 information architecture).

**Key decisions changed**:

| Decision | Before | After | Rationale |
|----------|--------|-------|-----------|
| `killing` tag (D30) | Add new tag id:18 | **DROPPED (YAGNI)** | Go Pro #3: life-and-death is ONE discipline, kill/live are same skill |
| Training page filter | Tag dropdown on selection page | **Tag dropdown on solve page** | Go Pro #3: students think in levels on browse, techniques inside puzzles |
| Collections page filter | Level + tag filters on browse page | **Filters inside collection detail only** | Go Pro #4: curated sets have boundaries, filter inside not above |
| Level pills mobile | 9 pills wrapping to 3 rows | **3 category pills on mobile, 9 on desktop** | Go Pro #3: 3 rows of chrome on 375px is unacceptable |
| Active filter chip | Below filter strip | **Inline in filter strip** | UX #3: chip below creates visual disconnection |
| "Clear all" button | Always shown | **Only when 2+ filters active** | UX #4: unnecessary for single-filter pages |
| FilterDropdown trigger | Static "Filter by technique" text | **Shows selected value when active** | UX #4: eliminates need to look elsewhere for state |
| Filter persistence | None (Q4 YAGNI) | **URL query params** | UX #4: back button should preserve filters |
| Focus trap | Not specified | **Added (WCAG 2.1 AA)** | UX #3: required for combobox pattern |

**Steps added**: WP8 steps 8.15 (filter URL params), 8.16 (empty state), 8.17 (responsive pills), 8.18 (tooltips)
**Tag count**: 28 total (unchanged from v2 — `killing` not added)

---

## 13. Original Phase Definitions (Reference Archive)

*The original v2 phase definitions (Phases 0-11) are preserved in git history of this file. The v3 plan reframes the remaining work as 10 Work Packages (WP1-WP10) organized by dependency, with explicit gap IDs linking back to the original phase/step numbers.*

---

> **See also**:
> - [plan-rush-play-enhancement.md](./plan-rush-play-enhancement.md) -- Rush Play feature plan
> - [entry-compression-proposal.md](./entry-compression-proposal.md) -- Architecture analysis (A/B/C comparison)
> - [multi-dimensional-puzzle-filtering.md](./multi-dimensional-puzzle-filtering.md) -- Original research (superseded by this plan)
