# Frontend Performance Optimizations

**Created:** 2026-02-24
**Status:** Not Started
**Origin:** Extracted from archived `frontend-perf-audit.md` (completed items removed)

---

## Remaining Items

### Tier 1 — Quick Wins

#### T-PERF-002: Defer audio preload to first user interaction
- **Effort:** 15 min | **Impact:** MEDIUM — 6 fewer network requests on initial load
- **Problem:** `audioService.preload()` called eagerly at module scope in `app.tsx` L90. Fires 6 `HTMLAudioElement` requests before any user interaction.
- **Fix:** Remove eager call. Add lazy init on first `play()` call, or use `document.addEventListener('pointerdown', preload, { once: true })`.
- **Files:** `frontend/src/app.tsx`, `frontend/src/services/audioService.ts`

#### T-PERF-004: Fix layout-triggering CSS transitions
- **Effort:** 30 min | **Impact:** LOW-MEDIUM — smoother 60fps animations
- **Problem:** `transition: all` in `QuickControls.css` L31 and `ProblemNav.css` L76 causes layout reflow during animations.
- **Fix:** Replace `transition: all` with specific GPU-friendly properties (`transform`, `opacity`).
- **Files:** `frontend/src/components/QuickControls/QuickControls.css`, `frontend/src/components/ProblemNav/ProblemNav.css`

### Tier 2 — Medium Wins

#### T-PERF-006: Route-level code splitting
- **Effort:** 2-3 hrs | **Impact:** CRITICAL — 30-40% initial bundle reduction
- **Problem:** `app.tsx` statically imports all page components. Everything ships in one JS chunk.
- **Fix:** Convert static imports to `lazy()` + dynamic `import()` for all pages. Add `<Suspense fallback={<SkeletonLayout />}>`.
- **Files:** `frontend/src/app.tsx`

#### T-PERF-007: Vite manual chunks for vendor splitting
- **Effort:** 30 min | **Impact:** HIGH — ~362KB moved to cacheable vendor chunk
- **Problem:** `vite.config.ts` has no `manualChunks`. The `goban` library is the heaviest dependency.
- **Fix:** Add `build.rollupOptions.output.manualChunks` splitting `goban` and `preact` into vendor chunks.
- **Files:** `frontend/vite.config.ts`

#### T-PERF-008: Decompose `app.tsx` monolith
- **Effort:** 3-4 hrs | **Impact:** MEDIUM — smaller re-render blast radius, prerequisite for T-PERF-006
- **Problem:** `app.tsx` is ~632 lines with routing, navigation, Rush state, puzzle fetching, inline components all mixed together.
- **Fix:** Extract `parseRoute()`/`navigateTo()` into `router.ts`, extract inline components.
- **Files:** `frontend/src/app.tsx` → new `frontend/src/router.ts`, extracted components
