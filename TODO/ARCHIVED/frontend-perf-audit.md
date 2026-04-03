# Frontend Performance Audit — Action Plan

> **Created:** 2026-02-15  
> **Status:** Ready for implementation  
> **Baseline:** 524.64 KB raw JS / 141.27 KB gzip, 103 modules (from specs/129 baseline)

---

## How to Use This File

1. **Pick a tier** — Start from Tier 1 (quick wins) and work down.
2. **Before ANY change:**
   - Run `cd frontend && npx playwright test` (full Playwright suite) and save the report as the **BEFORE** snapshot.
   - Run `cd frontend && npm test` (Vitest unit tests) — all must pass.
   - Run `cd frontend && npm run build` and record the bundle sizes from Vite output.
3. **Implement the change** following the description and affected files listed.
4. **After the change:**
   - Run `cd frontend && npm test` — fix any broken tests. **Update tests if component APIs changed.**
   - Run `cd frontend && npx playwright test` — compare against BEFORE snapshot. Fix any visual regressions.
   - Run `cd frontend && npm run build` — record new bundle sizes. Compare against BEFORE.
   - If the change removes components: delete associated test files and update barrel `index.ts` re-exports.
5. **Commit** using selective `git add` (never `git add .`). Follow Git Safety Rules from CLAUDE.md.
6. **Mark the item as DONE** in this file with the date and measured impact.

### Mandatory Testing Protocol

| Phase | Command | Purpose |
|-------|---------|---------|
| **BEFORE** | `npx playwright test --reporter=html` | Baseline visual/E2E snapshot |
| **BEFORE** | `npm test` | Baseline unit test pass |
| **BEFORE** | `npm run build 2>&1 \| tee build-before.log` | Baseline bundle size |
| **AFTER** | `npm test` | Confirm no unit test regressions; update tests for changed APIs |
| **AFTER** | `npx playwright test --reporter=html` | Confirm no visual/E2E regressions |
| **AFTER** | `npm run build 2>&1 \| tee build-after.log` | Measure bundle size delta |

> **Non-negotiable:** Every item MUST have a before/after Playwright comparison. No exceptions. If a Playwright test doesn't exist for the affected area, write one BEFORE making the change so you have a baseline.

---

## Tier 1 — Quick Wins (High Impact, Low Effort)

### T-PERF-001: Add `memo()` to hot components
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** HIGH — eliminates most unnecessary re-renders
- **Problem:** Zero components use Preact's `memo()`. Every parent re-render cascades unconditionally through all children. `SolverView` (514 lines, goban lifecycle) is the worst offender.
- **Affected files:**
  - `frontend/src/components/Solver/SolverView.tsx` — wrap export in `memo()`
  - `frontend/src/components/Home/HomeTile.tsx` — wrap export in `memo()`
  - `frontend/src/pages/PuzzleRushPage.tsx` — add memo boundary between timer UI and puzzle board
  - `frontend/src/components/Transforms/TransformBar.tsx` — wrap export in `memo()`
- **Downstream impact:** None — `memo()` is additive, doesn't change component API.
- **Test updates:** Add test cases verifying components don't re-render when props are unchanged (use `vitest` spy on render).
- **Playwright:** Run puzzle-solving and home page E2E tests before/after.

### T-PERF-002: Defer audio preload to first user interaction
- [ ] **Status:** TODO
- **Effort:** 15 min | **Impact:** MEDIUM — 6 fewer network requests on initial load
- **Problem:** `audioService.preload()` at module scope in `app.tsx` L45 fires 6 `HTMLAudioElement` requests before any user interaction.
- **Affected files:**
  - `frontend/src/app.tsx` L45 — remove `audioService.preload()` call
  - `frontend/src/services/audioService.ts` — add lazy init on first `play()` call, or use `document.addEventListener('pointerdown', preload, { once: true })`
- **Downstream impact:** First sound effect may have ~50ms delay on very first interaction. Acceptable.
- **Test updates:** Update `audioService` unit tests for lazy initialization behavior.
- **Playwright:** Home page load test — verify no audio network requests in devtools.

### T-PERF-003: Fix HomePageGrid triple re-render waterfall
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** MEDIUM — 3→1 re-renders, ~200ms faster home mount
- **Problem:** `HomePageGrid.tsx` L108-131 makes 3 sequential `setState` calls with 2 serialized async fetches.
- **Affected files:**
  - `frontend/src/pages/HomePageGrid.tsx` — batch async calls with `Promise.all`, single `setState`
- **Downstream impact:** None — same data, different timing.
- **Test updates:** Update HomePageGrid unit tests for batched loading behavior.
- **Playwright:** Home page E2E test — verify tiles render in single paint.

### T-PERF-004: Fix layout-triggering CSS transitions
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** LOW-MEDIUM — smoother 60fps animations
- **Problem:** `transition: all` in 5 places, `top`/`left`/`width` transitions in 3 places cause layout reflow during animations.
- **Affected files:**
  - `frontend/src/styles/app.css` L607, L747, L964 — replace with specific GPU-friendly properties
  - `frontend/src/components/QuickControls/QuickControls.css` L31 — replace `all` with specific properties
  - `frontend/src/components/ProblemNav/ProblemNav.css` L76 — replace `all` with specific properties
  - `frontend/src/pages/ReviewPage.css` L47 — replace `all` (also dead CSS, see T-PERF-006)
  - `frontend/src/components/PuzzleList/LoadMore.css` L29 — replace `width` with `transform: scaleX()`
- **Downstream impact:** Visual appearance must be identical. Only animation performance changes.
- **Test updates:** None needed for unit tests. CSS-only change.
- **Playwright:** Run visual comparison on any page with animated elements.

### T-PERF-005: Delete orphan CSS files
- [ ] **Status:** TODO
- **Effort:** 10 min | **Impact:** LOW — ~100 lines of dead CSS removed
- **Problem:** 3 CSS files have no matching component.
- **Files to DELETE:**
  - `frontend/src/pages/AchievementsPage.css` — no AchievementsPage.tsx exists
  - `frontend/src/pages/ReviewPage.css` — no ReviewPage.tsx exists
  - `frontend/src/components/PuzzleList/VirtualList.css` — marked removed in spec 124
- **Downstream impact:** None — files are never imported.
- **Test updates:** None.
- **Playwright:** Full suite to confirm no visual regressions.

---

## Tier 2 — Medium Wins (High Impact, Moderate Effort)

### T-PERF-006: Route-level code splitting
- [ ] **Status:** TODO
- **Effort:** 2-3 hrs | **Impact:** CRITICAL — **30-40% initial bundle reduction**
- **Problem:** `app.tsx` L7-20 statically imports all 11 page components. Everything ships in one JS chunk.
- **Affected files:**
  - `frontend/src/app.tsx` — convert static imports to `lazy()` + dynamic `import()` for all pages
  - Add `<Suspense fallback={<SkeletonLayout />}>` wrapper around route content
- **Downstream impact:** Pages load on navigation instead of upfront. First navigation to a new page has a brief loading state. All page component APIs remain unchanged.
- **Coordination:** Spec 129 Phase 15 plans this but hasn't started. This implements it.
- **Test updates:** Add tests for lazy loading behavior. Update any tests that expect synchronous page availability.
- **Playwright:** MANDATORY — test every route transition. Verify loading states appear and resolve correctly.

### T-PERF-007: Vite manual chunks for `goban` vendor splitting
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** HIGH — ~362KB moved to cacheable vendor chunk
- **Problem:** `vite.config.ts` has no `manualChunks`. The `goban` library is the heaviest dependency.
- **Affected files:**
  - `frontend/vite.config.ts` — add `build.rollupOptions.output.manualChunks` splitting `goban` and `preact` into vendor chunks
- **Downstream impact:** None — transparent to application code. Only affects cache behavior.
- **Test updates:** None.
- **Playwright:** Full suite — verify no loading regressions.

### T-PERF-008: Decompose `app.tsx` monolith
- [ ] **Status:** TODO
- **Effort:** 3-4 hrs | **Impact:** MEDIUM — smaller re-render blast radius, prerequisite for T-PERF-006
- **Problem:** `app.tsx` is 773 lines with 15+ concerns: routing, navigation, Rush state, puzzle fetching, 2 inline components.
- **Affected files:**
  - `frontend/src/app.tsx` — extract the following:
  - NEW: `frontend/src/router.ts` — `parseRoute()`, `navigateTo()`, route type definitions
  - NEW: `frontend/src/components/InlinePuzzleSolver.tsx` — extract from app.tsx L171-215
  - NEW: `frontend/src/components/RushPuzzleRenderer.tsx` — extract from app.tsx L217-256
- **Downstream impact:** All imports of route utilities need updating. Pages are unaffected (they receive props, don't import from app.tsx).
- **Test updates:** Create unit tests for extracted `parseRoute()` and `navigateTo()`. Update any app.tsx-level tests.
- **Playwright:** Full suite — routing behavior must be identical.

### T-PERF-009: Remove redundant Google Fonts CSS @import
- [ ] **Status:** TODO
- **Effort:** 10 min | **Impact:** LOW-MEDIUM — eliminates redundant external request
- **Problem:** `app.css` L10 has `@import url(fonts.googleapis.com/...)` AND `index.html` has a non-blocking `<link rel="preload">`. The CSS @import is redundant and can be render-blocking.
- **Affected files:**
  - `frontend/src/styles/app.css` L10 — remove the `@import` line
- **Downstream impact:** Font still loads via index.html `<link>`. Consider self-hosting for true offline-first.
- **Test updates:** None.
- **Playwright:** Visual test on a page with text — verify font renders correctly.

---

## Tier 3 — Dead Code Cleanup (~4,200 lines)

### T-PERF-010: Delete dead component directories
- [x] **Status:** DONE (2026-02-15) — UI overhaul phase-5
- **Effort:** 1 hr | **Impact:** MEDIUM — ~3,500 lines removed, cleaner tree-shaking
- **Directories DELETED:**
  - `frontend/src/components/ChallengeList/` (8 files, 1,802 lines)
  - ~~`frontend/src/components/ProblemNav/`~~ — **NOT deleted: ALIVE** (imported by PuzzleSetPlayer, resurrected in UI-034)
  - `frontend/src/components/Level/` (4 files, 568 lines)
  - `frontend/src/components/Feedback/` (2 files, 205 lines)
- **Individual files DELETED:**
  - `frontend/src/components/ComplexityIndicator.tsx`
  - `frontend/src/components/QualityBadge.tsx`
  - `frontend/src/components/QualityBreakdown.tsx`
  - `frontend/src/components/QualityFilter.tsx`
  - `frontend/src/components/Progress/Dashboard.tsx`
  - `frontend/src/components/Progress/AchievementList.tsx`
  - `frontend/src/components/Solver/MoveExplorer.tsx`
  - `frontend/src/components/PuzzleList/VirtualList.tsx`
  - `frontend/src/components/shared/AnswerBanner.tsx`
  - `frontend/src/components/shared/SideToMove.tsx` — dead (SolverView uses inline rendering)
  - `frontend/src/components/shared/StatusIcon.tsx`
  - `frontend/src/components/shared/RankBadge.tsx`
- **Barrel updates:** `components/index.ts`, `components/Progress/index.ts` updated.
- **Test files deleted:** 13 dead test files removed.
- **Playwright:** Full suite — no visual changes expected.

### T-PERF-011: Delete dead hooks, services, models, types
- [x] **Status:** DONE (2026-02-15) — UI overhaul phase-5
- **Effort:** 30 min | **Impact:** LOW — ~700 lines removed
- **Files DELETED:**
  - `frontend/src/hooks/useBoardMarkers.ts`
  - `frontend/src/hooks/usePrefetch.ts`
  - `frontend/src/hooks/useProgressTracker.ts`
  - `frontend/src/services/achievementEngine.ts`
  - `frontend/src/services/qualityConfig.ts`
  - `frontend/src/models/rush.ts`
  - `frontend/src/types/mastery.ts`
  - `frontend/src/types/source-registry.ts`
  - `frontend/src/utils/statusMapping.ts`
  - `frontend/src/pages/MyCollectionsPage.tsx`
- **Barrel updates:** `types/index.ts` source-registry re-exports removed.
- **Orphan CSS deleted:** `AchievementsPage.css`, `ReviewPage.css`, `VirtualList.css`
- **Test files deleted:** Corresponding test files removed.
- **Playwright:** Full suite.

---

## Tier 4 — Architectural Improvements (High Effort)

### T-PERF-012: Resolve dual service worker conflict
- [ ] **Status:** TODO
- **Effort:** 3-4 hrs | **Impact:** MEDIUM — eliminates potential cache corruption
- **Problem:** Custom `sw.ts` (368 lines) AND VitePWA workbox auto-generated SW coexist. Potential double-caching and strategy conflicts.
- **Decision needed:** Keep one, delete the other. Custom SW has more specific caching strategies; workbox has better lifecycle management.
- **Affected files:**
  - `frontend/src/sw.ts` — delete if choosing workbox, or enhance if keeping custom
  - `frontend/vite.config.ts` L98-160 — remove VitePWA SW config if keeping custom
- **Test updates:** Add SW-specific tests (cache hit/miss, offline behavior).
- **Playwright:** Test offline mode, page refresh after deploy, cache invalidation.

### T-PERF-013: Split `puzzleLoader.ts` monolith (995 lines)
- [ ] **Status:** TODO
- **Effort:** 4-6 hrs | **Impact:** MEDIUM — better tree-shaking, parallel search
- **Problem:** Single 995-line module handles SGF fetching, parsing, caching, index loading, manifest loading. Serial level search (up to 9 sequential network requests).
- **Affected files:**
  - `frontend/src/services/puzzleLoader.ts` — split into focused modules
  - 12+ consumers need import updates
- **Test updates:** Comprehensive. Each new module needs its own test file.
- **Playwright:** All puzzle-loading flows.

### T-PERF-014: Clean up `types/index.ts` runtime value re-exports
- [ ] **Status:** TODO
- **Effort:** 2-3 hrs | **Impact:** LOW-MEDIUM — better tree-shaking
- **Problem:** `types/index.ts` re-exports ~50+ symbols including runtime values (`DEFAULT_PREFERENCES`, `createDefaultProgress`). Any type-only import pulls in implementation code.
- **Affected files:**
  - `frontend/src/types/index.ts` — split type-only vs runtime exports
  - All consumers importing from `@types/` — update to import from specific sub-modules
- **Test updates:** Update import paths in test files.
- **Playwright:** Full suite.

### T-PERF-015: Merge/rename `puzzleLoader.ts` vs `puzzleLoaders.ts`
- [ ] **Status:** TODO
- **Effort:** 1 hr | **Impact:** LOW — reduces cognitive overhead
- **Problem:** Two confusingly named files: `puzzleLoader.ts` (995 lines, low-level) and `puzzleLoaders.ts` (403 lines, class wrappers).
- **Affected files:** Both files + all import sites.
- **Test updates:** Update import paths.
- **Playwright:** All puzzle-loading flows.

### T-PERF-016: Collapse `progressTracker.ts` re-export chain
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** LOW — cleaner dependency graph
- **Problem:** `progressTracker.ts` → `progress/index.ts` → 3 implementation files. Extra barrel hop.
- **Affected files:**
  - `frontend/src/services/progressTracker.ts` — inline or delete
  - ~20 import sites — point to `progress/` directly
- **Test updates:** Update import paths in tests.
- **Playwright:** Progress tracking flows.

---

## Tier 5 — Tooling & Observability

### T-PERF-017: Add bundle analysis tooling
- [ ] **Status:** TODO
- **Effort:** 10 min | **Impact:** HIGH (enables all other decisions)
- **Do this FIRST before any other optimization.**
- **Affected files:**
  - `frontend/package.json` — add `rollup-plugin-visualizer` as devDependency
  - `frontend/vite.config.ts` — add visualizer plugin (generates `stats.html` on build)
- **Test updates:** None.
- **Playwright:** None.

### T-PERF-018: Add performance budget enforcement
- [ ] **Status:** TODO
- **Effort:** 1 hr | **Impact:** MEDIUM — prevents regressions
- **Affected files:**
  - `frontend/package.json` — add `size-limit` as devDependency
  - NEW: `frontend/.size-limit.json` — set budget (target: ≤400 KB JS gzipped after optimizations)
  - `frontend/vite.config.ts` — add `build.chunkSizeWarningLimit`
- **Test updates:** Add `size-limit` to CI/pre-commit.
- **Playwright:** None.

### T-PERF-019: Strip console statements in production
- [ ] **Status:** TODO
- **Effort:** 30 min | **Impact:** LOW — cleaner production output
- **Problem:** 91 console statements (44 error, 21 warn, 17 log, 9 debug) in production code.
- **Affected files:**
  - `frontend/vite.config.ts` — add `esbuild: { drop: ['console', 'debugger'] }` for production builds
  - OR add `esbuild: { pure: ['console.log', 'console.debug'] }` to keep error/warn
- **Test updates:** None.
- **Playwright:** Verify pages still function without console output.

---

## Coordination Notes

- **Spec 129 Phase 15** overlaps with T-PERF-006 (code splitting) and T-PERF-007 (vendor chunks). If Phase 15 starts, reference these items.
- **Spec 131** overlaps with T-PERF-006 and T-PERF-007 (goban lazy-loading). Coordinate to avoid conflicts.
- **Dead code (Tier 3)** is residual after spec 129 Phases 1-3. These 24 files were either missed or created by subsequent refactoring in Phases 4-7.
- Items marked with `Decision needed` require user input before implementation.

## Measured Baselines (Record Here)

| Metric | Before | After T-PERF-XXX | Date |
|--------|--------|-------------------|------|
| Total JS (raw) | 524.64 KB | | |
| Total JS (gzip) | 141.27 KB | | |
| Total CSS (raw) | 39.24 KB | | |
| Total CSS (gzip) | 9.07 KB | | |
| Modules transformed | 103 | | |
| Source files | ~335 | | |
| Source LOC | ~72,625 | | |
| Playwright tests passing | TBD | | |
| Lighthouse Performance | TBD | | |
