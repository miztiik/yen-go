# Rush Play Enhancement — Implementation Plan

**Last Updated**: 2026-02-17
**Status**: Implementation-Ready — All Decisions Finalized
**Prerequisites**: Phases 0–7 of [plan-compact-schema-filtering.md](./plan-compact-schema-filtering.md)
**Companion Plan**: [plan-compact-schema-filtering.md](./plan-compact-schema-filtering.md)
**Reference**: [entry-compression-proposal.md](./entry-compression-proposal.md)

---

## 1. Executive Summary

Enhance Puzzle Rush from a fixed "random beginner, 3/5/10 min" mode to a **fully configurable timed challenge**: user-selected level, technique, and custom duration (1–30 min). Fix the existing hardcoded `'beginner'` bug. Rush retains its independent architecture — it does NOT use `PuzzleSetPlayer` (D12).

### What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Level selection | Hardcoded `'beginner'` | User picks from level master index |
| Tag/technique filter | None | User picks from tag master index |
| Duration | `3 \| 5 \| 10` min fixed pills | Preset pills (3/5/10) + custom slider (1–30 min) |
| Available count | Unknown | "~2,800 puzzles available" from master index |
| Data format | `LevelEntry {path, tags}` | `CompactEntry {p, l, t, c, x}` decoded via config |
| Loading | Flat URL hardcode → 404 with always-paginate | Pagination-aware numeric-ID loading |

### Why Separate Plan

Rush has its own state machine, rendering pipeline, and session management (`PuzzleRushPage.tsx`, `useRushSession.ts`, `RushOverlay.tsx`, `app.tsx::getNextPuzzle()`). None of these share code with `PuzzleSetPlayer`. The filter component infrastructure from the main plan (Phase 8) is reused, but Rush wiring is self-contained and independently deployable.

---

## 2. Decisions (Rush-Specific)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D12 | Rush refactor to PuzzleSetPlayer | **NO** | 6+ missing features in PuzzleSetPlayer (timer, lives, streak, countdown, game-over, HUD). Incompatible architectures. |
| D13 | Rush scope | **Separate plan** | Self-contained, independently deployable after filtering infrastructure ready |
| D14 | Rush custom time | **Custom pill + slider** | `RushDuration` becomes `number` (seconds, 60–1800). Preset pills for 3/5/10 min + slider for custom. |

---

## 3. Current Architecture (Unchanged by This Plan)

```
RushBrowsePage (setup screen)
  → user picks duration → navigates to PuzzleRushPage

PuzzleRushPage (game mode)
  → state: setup → countdown → playing → finished
  → useRushSession(duration, lives=3)
    → timer, score, streak, mistakes tracking
  → getNextPuzzle(level) in app.tsx
    → loadLevelIndex(level) → picks random entry → fetchSGFContent(entry.path)
  → RushPuzzleRenderer → InlinePuzzleSolver
  → RushOverlay (HUD: timer, score, streak, lives)
```

**Current bugs**:
- `currentLevelRef = useRef<SkillLevel>('beginner')` — NEVER updated, ALL Rush puzzles are beginner
- `loadLevelIndex()` hardcodes flat URL `views/by-level/${level}.json` — will 404 with always-paginate
- `RushDuration = 180 | 300 | 600` — no custom time support

---

## 4. Prerequisites (From Main Plan)

These must be complete before starting Rush implementation:

| Phase | What | Why Rush Needs It |
|-------|------|-------------------|
| **Phase 0** | Config with numeric IDs | Rush uses `levelMap`/`tagMap` to decode entries |
| **Phase 2** | Compact entry format | Rush reads `{p, l, t, c, x}` entries |
| **Phase 3** | Always-paginate | Rush's `loadLevelIndex()` must use paginated paths |
| **Phase 6** | Republished views | Rush needs v4.0 view data to exist |
| **Phase 7** | Frontend types + config pre-fetch + pagination-aware loaders | Rush reuses `configService`, `entryDecoder`, `loadLevelIndex()` (fixed) |
| **Phase 8** | Filter components | Rush setup screen reuses `FilterBar`, `FilterDropdown` |

---

## 5. Implementation Phases

### Phase Dependency Graph

```
Main Plan Phases 0–8 (prerequisites)
  └──→ Phase R1 (Setup Screen) ──→ Phase R2 (Game Logic) ──→ Phase R3 (Custom Duration) ──→ Phase R4 (Visual Testing) ──→ Phase R5 (Docs)
```

**Parallelizable**: Phase R3 (custom duration) is independent of R1/R2 and could be done concurrently if split to a separate feature branch. But given Rush is a single feature area, sequential is cleaner.

### Git Safety: Branch-Per-Phase Workflow

```bash
# Each Rush phase = one feature branch
git checkout main
git checkout -b feature/rush-phase-{N}-{name}
git add path/to/specific/files     # NEVER git add .
git diff --cached --name-only      # verify
git commit -m "feat(rush): phase R{N} - {description}"
git checkout main
git merge --no-ff feature/rush-phase-{N}-{name}
git branch -d feature/rush-phase-{N}-{name}
```

---

### Phase R1: Rush Setup Screen — Level + Tag Selection

**Branch**: `feature/rush-phase-r1-setup-filters`
**Goal**: Add level and tag selection to the Rush setup screen.

| Step | Task | Files |
|------|------|-------|
| R1.1 | Load level master index on `RushBrowsePage` mount — extract level names + counts | `RushBrowsePage.tsx` |
| R1.2 | Load tag master index on mount — extract tag names + counts | `RushBrowsePage.tsx` |
| R1.3 | Add level selection `FilterBar` (pills, ≤9 options): `All \| Novice (1.2k) \| Beginner (2.8k) \| ...` | `RushBrowsePage.tsx` |
| R1.4 | Add tag selection `FilterDropdown` (28+ options): `All \| Life & Death (3.2k) \| Ladder (1.8k) \| ...` | `RushBrowsePage.tsx` |
| R1.5 | Show "~N puzzles available" below filters — intersection estimate from master index distributions | `RushBrowsePage.tsx` |
| R1.6 | Warn if filtered set < 20 puzzles: "Few puzzles match — consider broadening filters" | `RushBrowsePage.tsx` |
| R1.7 | Pass selected `levelId` and `tagId` to `PuzzleRushPage` via navigation state | `RushBrowsePage.tsx`, `PuzzleRushPage.tsx` |
| R1.8 | Run `npm test` + `tsc --noEmit` | — |

**Exit criteria**: Setup screen shows level + tag filters with counts. Selected filters pass to game page.

**Expert review checkpoint**:
- ⬜ UI/UX Expert: Setup screen layout with 3 controls (duration + level + tag) is clean
- ⬜ 1P Go Professional: "Intermediate ladder, 5 min" workflow makes pedagogical sense

---

### Phase R2: Rush Game Logic — Filtered Puzzle Loading

**Branch**: `feature/rush-phase-r2-filtered-loading`
**Goal**: `getNextPuzzle()` respects level and tag selection. Fix hardcoded beginner bug.

| Step | Task | Files |
|------|------|-------|
| R2.1 | **FIX BUG**: Remove `currentLevelRef = useRef<SkillLevel>('beginner')` — use selected level from setup | `PuzzleRushPage.tsx` |
| R2.2 | Update `getNextPuzzle()` signature: `getNextPuzzle(levelId?: number, tagId?: number)` | `app.tsx` |
| R2.3 | Implement loading strategy based on selection: | `app.tsx` |
|      | — Level only: load from `views/by-level/${levelId}/page-NNN.json`, random entry | |
|      | — Tag only: load from `views/by-tag/${tagId}/page-NNN.json`, random entry | |
|      | — Both: load from `views/by-level/${levelId}/page-NNN.json`, filter `e.t.includes(tagId)` | |
|      | — Neither: load from random level (weighted by master index count) | |
| R2.4 | Decode entries via `decodeEntry()` before passing to SGF loader | `app.tsx` |
| R2.5 | Update path reconstruction: `sgf/${e.p}.sgf` (flat batch path) | `app.tsx` |
| R2.6 | Maintain existing `usedPuzzleIds` deduplication — works with new hash-based IDs | `PuzzleRushPage.tsx` |
| R2.7 | Handle page exhaustion: when current page filtered set is empty, load next page | `app.tsx` |
| R2.8 | Handle total exhaustion: if all pages exhausted for filter combo, show "No more puzzles" | `PuzzleRushPage.tsx` |
| R2.9 | Unit test: `getNextPuzzle()` with level-only, tag-only, both, neither | Tests |
| R2.10 | Run `npm test` | — |

**Exit criteria**: Rush loads puzzles matching selected level+tag. Beginner bug fixed. Page exhaustion handled.

**Expert review checkpoint**:
- ⬜ Staff Engineer: Page caching strategy for Rush (does it re-fetch pages on each puzzle?)
- ⬜ 1P Go Professional: Verify filtered set sizes are pedagogically useful (not too small)

---

### Phase R3: Rush Custom Duration

**Branch**: `feature/rush-phase-r3-custom-duration`
**Goal**: Add custom time selection 1–30 min alongside preset pills.

| Step | Task | Files |
|------|------|-------|
| R3.1 | Change `RushDuration` type from `180 \| 300 \| 600` to `number` (seconds, 60–1800) | Type definitions |
| R3.2 | Add custom pill to duration selector: `3 min \| 5 min \| 10 min \| Custom` | `RushBrowsePage.tsx` |
| R3.3 | When "Custom" selected, show slider (1–30 min) with value label | `RushBrowsePage.tsx` |
| R3.4 | Slider increments: 30-second steps from 1–5 min, 1-minute steps from 5–30 min | `RushBrowsePage.tsx` |
| R3.5 | Update `useRushSession(duration)` to accept any valid second count | `useRushSession.ts` |
| R3.6 | Verify timer display works for non-standard durations (e.g., 7:30, 12:00) | `RushOverlay.tsx` |
| R3.7 | Run `npm test` | — |

**Exit criteria**: Custom duration works from 1–30 min. Presets still work. Timer displays correctly.

**Expert review checkpoint**:
- ⬜ UI/UX Expert: Slider UX — visible value, accessible, touch-friendly on mobile

---

### Phase R4: Rush Visual Regression Testing

**Branch**: `feature/rush-phase-r4-visual-testing`
**Goal**: Before/after screenshots for Rush changes.

| Step | Task | Files |
|------|------|-------|
| R4.1 | Run `npm run test:visual` BEFORE Rush changes (baseline should pass) | — |
| R4.2 | Create `RushBrowse-enhanced.visual.spec.ts` — setup screen with level/tag/custom time across 3 viewports × 2 themes | `tests/visual/specs/RushBrowse-enhanced.visual.spec.ts` (**NEW**) |
| R4.3 | Create `RushCustomDuration.visual.spec.ts` — custom slider open, various values | `tests/visual/specs/RushCustomDuration.visual.spec.ts` (**NEW**) |
| R4.4 | Run `npm run test:visual` — verify new specs produce screenshots | — |
| R4.5 | **UI/UX Expert review**: Screenshots approved | Manual |
| R4.6 | Update baselines: `npm run test:visual:update` | — |
| R4.7 | Run `npm run test:visual` — all pass | — |
| R4.8 | Run `npm run test:e2e` — no regressions | — |

**Exit criteria**: 2 new visual specs. All visual + E2E tests pass. UI/UX expert sign-off.

**Expert review checkpoint**:
- ⬜ UI/UX Expert: Rush setup screen before/after approved
- ⬜ UI/UX Expert: Custom slider rendering on mobile/dark mode

---

### Phase R5: Rush Documentation

**Branch**: `feature/rush-phase-r5-docs`
**Goal**: Document Rush enhancements.

| Step | Task | File(s) |
|------|------|---------|
| R5.1 | Document Rush Play enhancements — level/tag selection, custom time | `docs/how-to/frontend/rush-mode.md` (**NEW** or update existing) |
| R5.2 | Update frontend CLAUDE.md with Rush architecture notes | `frontend/CLAUDE.md` |
| R5.3 | Add Rush filter data flow to architecture docs | `docs/architecture/frontend/rush-play.md` |

**Exit criteria**: Rush documented. Architecture updated.

---

## 6. Risks and Mitigations

| Risk | Severity | Mitigation | Phase |
|------|----------|------------|-------|
| Filtered set exhaustion (e.g., only 15 expert ko puzzles) | Medium | Show "X puzzles available" on setup screen; warn if < 20 | R1 |
| `loadLevelIndex()` flat URL → 404 | **Critical** | Fixed in main plan Phase 7 (prerequisite) | — |
| Level stuck at 'beginner' | Low (existing bug) | Fixed in R2.1 | R2 |
| Custom slider inaccessible on mobile | Low | Test across viewports in R4 | R3, R4 |
| Page caching — Rush may reload same page repeatedly | Medium | Cache loaded pages in session; evict on filter change | R2 |
| Rush + filter combo yields 0 puzzles | Medium | Pre-check via master index; disable "Start" if 0 | R1 |

---

## 7. User Flow

### Flow D: Rush → Level + Tag + Custom Duration Selection

1. User clicks **Rush** → lands on `RushBrowsePage`
2. Setup screen shows:
   - **Duration**: `3 min | 5 min | 10 min | Custom` (custom = slider 1–30 min)
   - **Level** (optional): `All | Novice (1.2k) | Beginner (2.8k) | ...` (from level master index)
   - **Technique** (optional): `All | Ladder (1.8k) | Ko (2.1k) | ...` (from tag master index)
3. Below filters: **"~2,800 puzzles available"** (from master index intersection estimate)
4. User selects **Custom (7 min) + Intermediate + Ladder** → taps "Start Rush"
5. Countdown: 3... 2... 1...
6. `getNextPuzzle(140, 24)` loads from `views/by-level/140/page-001.json`
   → filters `entries.filter(e => e.t.includes(24))`
   → decodes random entry → fetches SGF → renders on Goban
7. User solves/fails → next puzzle → timer runs down → game over screen

### What Rush Does NOT Do
- ❌ Difficulty progression during session — separate future feature
- ❌ Multi-tag AND filtering — YAGNI
- ❌ Use PuzzleSetPlayer — own architecture (D12)
- ❌ Save filter preferences — YAGNI (Q4)

---

## 8. Expert Review Checkpoints Summary

| Phase | Reviewer | What |
|-------|----------|------|
| R1 | UI/UX Expert | Setup screen layout with 3 controls |
| R1 | 1P Go Professional | "Intermediate ladder, 5 min" workflow |
| R2 | Staff Engineer | Page caching strategy |
| R2 | 1P Go Professional | Filtered set sizes pedagogically useful |
| R3 | UI/UX Expert | Slider UX — accessible, touch-friendly |
| R4 | UI/UX Expert | Before/after screenshots approved |
| R4 | UI/UX Expert | Mobile + dark mode rendering |

---

## 9. Files Inventory

| File | Change | Phase |
|------|--------|-------|
| `frontend/src/pages/RushBrowsePage.tsx` | Level/tag filters + custom duration + available count | R1, R3 |
| `frontend/src/pages/PuzzleRushPage.tsx` | Fix hardcoded 'beginner', accept level+tag from setup | R2 |
| `frontend/src/app.tsx` | Update `getNextPuzzle()` — level+tag params, paginated loading, flat batch paths | R2 |
| `frontend/src/hooks/useRushSession.ts` | Accept `number` duration (was union type) | R3 |
| `frontend/src/components/rush/RushOverlay.tsx` | Verify timer display for non-standard durations | R3 |
| Type definitions | `RushDuration` → `number` | R3 |
| `tests/visual/specs/RushBrowse-enhanced.visual.spec.ts` | **NEW** | R4 |
| `tests/visual/specs/RushCustomDuration.visual.spec.ts` | **NEW** | R4 |
| `docs/how-to/frontend/rush-mode.md` | **NEW** or update | R5 |

---

> **See also**:
> - [plan-compact-schema-filtering.md](./plan-compact-schema-filtering.md) — Main infrastructure plan (Phases 0–11, prerequisite)
> - [entry-compression-proposal.md](./entry-compression-proposal.md) — Architecture C analysis
> - [multi-dimensional-puzzle-filtering.md](./multi-dimensional-puzzle-filtering.md) — Original research (superseded)
