# Research Brief: Rush/Timed Puzzle Feature Audit

**Initiative**: `20260322-research-rush-timed-puzzle-audit`
**Research Date**: 2026-03-22
**Status**: Complete

---

## 1. Research Question & Boundaries

**Question**: What is the current state of the Rush/timed puzzle feature — rendering, CSS theming, and gameplay — and what specific issues exist that cause broken rendering, misaligned CSS, and non-functional gameplay?

**Boundaries**:
- Scope: Frontend Rush-related code only (`frontend/src/`)
- Comparison baseline: Standard puzzle solver (`SolverView`, `PuzzleSetPlayer`)
- NOT in scope: Backend `daily/timed.py`, future feature design

---

## 2. Complete File Inventory

### R-1: Rush-Specific Source Files

| ID | File | Purpose | Lines |
|----|------|---------|-------|
| F-1 | `frontend/src/pages/PuzzleRushPage.tsx` | Game mode page: setup → countdown → playing → finished | ~400 |
| F-2 | `frontend/src/pages/RushBrowsePage.tsx` | Pre-game setup: duration cards, level/tag filters, rules | ~415 |
| F-3 | `frontend/src/components/Rush/RushOverlay.tsx` | In-game HUD: timer, lives, score, streak, pause/game-over overlays | ~177 |
| F-4 | `frontend/src/components/Rush/index.ts` | Barrel export | 8 |
| F-5 | `frontend/src/hooks/useRushSession.ts` | Timer countdown, lives, score, streak logic | ~250 |
| F-6 | `frontend/src/types/goban.ts` (lines 66-80) | `RushDuration`, `RushSessionState` types | ~15 |
| F-7 | `frontend/src/app.tsx` (lines 33-500) | `RushPuzzle`, `RushPuzzleRenderer`, `InlinePuzzleSolver`, `getNextPuzzle`, route wiring | ~470 |

### R-2: Rush-Related Test Files

| ID | File | Purpose |
|----|------|---------|
| T-1 | `frontend/tests/e2e/rush-start.spec.ts` | E2E: browse screen, duration selection, countdown |
| T-2 | `frontend/tests/e2e/rush-correct.spec.ts` | E2E: scoring, lives, streak after correct answers |
| T-3 | `frontend/tests/e2e/rush-wrong.spec.ts` | E2E: wrong answer life deduction |
| T-4 | `frontend/tests/e2e/rush-game-over.spec.ts` | E2E: game over conditions |
| T-5 | `frontend/tests/visual/specs/rush.visual.spec.ts` | Visual regression for Rush page |
| T-6 | `frontend/tests/visual/specs/rush-modal.visual.spec.ts` | Visual regression for Rush modals |

### R-3: CSS/Theme Files

| ID | File | Lines | Purpose |
|----|------|-------|---------|
| S-1 | `frontend/src/styles/app.css` (lines 162-165) | Light mode Rush CSS vars | `--color-mode-rush-{border,bg,text,light}` |
| S-2 | `frontend/src/styles/app.css` (lines 378-381) | Dark mode Rush CSS vars | Same tokens, adapted for dark |
| S-3 | `frontend/src/styles/app.css` (lines 440-446) | `[data-mode="rush"]` accent cascade | Sets `--color-accent`, `--color-accent-border`, `--color-accent-container` |

### R-4: Shared Infrastructure Used by Rush

| ID | Module | Used By Rush? | How |
|----|--------|---------------|-----|
| I-1 | `services/puzzleLoader.ts` (`fetchSGFContent`) | Yes | `RushPuzzleRenderer` in `app.tsx` loads SGF |
| I-2 | `services/puzzleQueryService.ts` | Yes | `getNextPuzzle()` uses `getPuzzlesByLevel`, `getPuzzlesByTag`, `getPuzzlesFiltered` |
| I-3 | `services/sqliteService.ts` | Yes | Database init for puzzle queries |
| I-4 | `services/configService.ts` | Yes | `levelIdToSlug`, `levelSlugToId`, `tagSlugToId`, `getAllLevels`, `getOrderedTagCategories` |
| I-5 | `hooks/useGoban.ts` | Yes | `InlinePuzzleSolver` creates Goban instance |
| I-6 | `hooks/usePuzzleState.ts` | Yes | `InlinePuzzleSolver` tracks solve state |
| I-7 | `components/GobanContainer/` | Yes | Board rendering in `InlinePuzzleSolver` |
| I-8 | `services/progress/` | Yes | `recordRushScore()` persists scores |
| I-9 | `lib/routing/routes.ts` | Yes | `modes-rush` route type |
| I-10 | `components/Layout/PageLayout.tsx` | **Partial** | `RushBrowsePage` uses it; `PuzzleRushPage` does NOT |
| I-11 | `components/shared/PageHeader.tsx` | **RushBrowsePage only** | Play page has custom header |
| I-12 | `components/shared/Button.tsx` | Yes | Used in `PuzzleRushPage` for actions |

---

## 3. Component Hierarchy & Data Flow

```
HomePageGrid
  └─ HomeTile (variant="rush") → onNavigateRush() → route = { type: 'modes-rush' }

App (route dispatcher)
  ├─ rushDuration === null → RushBrowsePage
  │   ├─ PageLayout (mode="rush") → data-mode="rush" → CSS accent cascade ✅
  │   ├─ PageHeader (title, icon, stats)
  │   ├─ Duration cards (3/5/10 min + custom slider)
  │   ├─ FilterBar (level) + FilterDropdown (technique)
  │   └─ Rules section
  │   └─ onStartRush(duration, levelId, tagId) → sets rushDuration/rushLevelId/rushTagId
  │
  └─ rushDuration !== null → PuzzleRushPage
      ├─ Raw <div data-mode="rush"> → NOT wrapped in PageLayout ⚠️
      ├─ Setup screen (if durationMinutes undefined) — DEAD CODE ⚠️
      ├─ Countdown screen (3…2…1)
      ├─ Playing screen
      │   ├─ RushOverlay (timer, lives, score, streak, pause/game-over)
      │   ├─ Board container → renderPuzzle() prop
      │   │   └─ RushPuzzleRenderer (app.tsx)
      │   │       └─ InlinePuzzleSolver (app.tsx)
      │   │           ├─ useGoban(sgf, treeRef) → Goban instance
      │   │           ├─ usePuzzleState(goban) → solve state machine
      │   │           └─ GobanContainer → board rendering
      │   └─ Controls (Skip, Quit)
      └─ Finished screen (score, stats, Play Again / Go Home)
```

---

## 4. Specific Issues Found

### Issue Category A: CSS / Rendering

| ID | Issue | Severity | Evidence |
|----|-------|----------|----------|
| CSS-1 | **PuzzleRushPage does NOT use PageLayout** — uses raw `<div>` with `data-mode="rush"`. Misses PageLayout's grid scaffolding, consistent padding, and variant-based layout. `RushBrowsePage` correctly uses `<PageLayout variant="single-column" mode="rush">`. | High | `PuzzleRushPage.tsx:193` vs `RushBrowsePage.tsx:176` |
| CSS-2 | **Emoji usage in production UI** — `🔥` in "Puzzle Rush" title (line 195), "Play Again" button (line 384), and streak indicator in `RushOverlay.tsx` (line 115). Project rule: "No emojis in production UI — All icons are SVG components." | Medium | `PuzzleRushPage.tsx:195,384`, `RushOverlay.tsx:115` |
| CSS-3 | **Emoji in pause button** — `⏸` character used as pause icon (`RushOverlay.tsx:141`). Should use SVG `PauseIcon` from `components/shared/icons/`. | Low | `RushOverlay.tsx:141` |
| CSS-4 | **RushOverlay positioning assumes `relative` parent** — Uses `absolute inset-0` for paused/game-over overlays. The parent `PuzzleRushPage` div has `relative`, but the overlay is a sibling of the playing content, not a wrapper — the overlay covers only the RushOverlay bar area, not the full page. | High | `RushOverlay.tsx:132,148` — overlays are inside the HUD bar's div but use `absolute inset-0` |
| CSS-5 | **Board container aspect ratio constrained but no resize integration** — Board uses `aspect-square w-full max-w-[500px]` but doesn't integrate with GobanContainer's ResizeObserver properly. Other modes (SolverView) use the `solver-board-col` CSS class with proper sizing. | Medium | `PuzzleRushPage.tsx:270` |
| CSS-6 | **No PageLayout scrolling/overflow handling** — PuzzleRushPage uses `min-h-[calc(100vh-3.5rem)]` assuming the header height. If header height changes, layout breaks. `PageLayout` handles this generically. | Low | `PuzzleRushPage.tsx:193` |

### Issue Category B: Gameplay / Logic

| ID | Issue | Severity | Evidence |
|----|-------|----------|----------|
| GP-1 | **Dual best-score systems** — `app.tsx:40-46` reads from `localStorage('yen-go-rush-best-score')` but `PuzzleRushPage` writes via `recordRushScore()` which uses progress system's `rushHighScores` array. `getBestScore()` in `app.tsx` reads a **different key** than what gets written. The best score passed to `RushBrowsePage` may always be `null`. | Critical | `app.tsx:40-46` (reads `yen-go-rush-best-score`) vs `progressCalculations.ts:387` (writes to `statistics.rushHighScores`) |
| GP-2 | **PuzzleRushPage has dead setup screen** — When `durationMinutes` is provided (always true when coming from App router), the page starts in `countdown` state. But it still contains a full setup UI (duration selection, Start Rush button) that should be in `RushBrowsePage`. This dead code path only triggers if `durationMinutes` is `undefined`. | Medium | `PuzzleRushPage.tsx:99-101,195-237` |
| GP-3 | **Wrong answer threshold hardcoded** — `InlinePuzzleSolver` triggers `onComplete(false)` after 3 wrong attempts (`wrongAttempts >= 3`). But Rush should fail on first wrong move (costs a life), not give 3 retries per puzzle. This means a player can make 2 wrong moves per puzzle without penalty. | High | `app.tsx:166-168` — `puzzleState.wrongAttempts >= 3` |
| GP-4 | **`isGameOver` checked after loadNextPuzzle** — In `handleSkip`, `isGameOver` is checked after `actions.skip()` which decrements lives. But React state updates are async; `isGameOver` may not yet reflect the new lives count. Same issue in the puzzle completion callback. | Medium | `PuzzleRushPage.tsx:155-160`, `PuzzleRushPage.tsx:290-298` |
| GP-5 | **Skip costs 1 life but button disabled at `lives <= 1`** — Skip is disabled when lives ≤ 1, which means skip is unavailable with 1 life. This is possibly intentional (prevent self-defeat) but inconsistent with the "Skip costs 1 life" messaging. | Low | `PuzzleRushPage.tsx:306-310` |
| GP-6 | **Puzzle pool exhaustion with no feedback** — When `usedPuzzleIds` exhausts all puzzles, the pool silently resets. User may solve the same puzzle twice without knowing. No "pool reset" feedback. | Low | `app.tsx:430-433` |
| GP-7 | **`masterLoaded` always `false` in RushBrowsePage** — Line 100: `const masterLoaded = false;` means the filter section (`{masterLoaded && ...}`) never renders. Filters are non-functional. Level/tag filtering on the browse page is completely hidden. | Critical | `RushBrowsePage.tsx:100` |
| GP-8 | **Countdown doesn't cancel on unmount** — The countdown `setInterval` in `useEffect` has a `clearInterval` return, but `handleGameStart` is called inside `setCountdownValue`, which is a state updater — the async nature could lead to double-start if React batches poorly. | Low | `PuzzleRushPage.tsx:119-128` |

### Issue Category C: Architecture / Code Quality

| ID | Issue | Severity | Evidence |
|----|-------|----------|----------|
| AQ-1 | **Massive app.tsx bloat** — ~470 lines of Rush-specific code live in `app.tsx` including `RushPuzzle` type, `getBestScore()`, `loadRushTagEntries()`, `loadLevelIndex()`, `RushPuzzleRenderer`, `InlinePuzzleSolver`, `getNextPuzzle`, `renderPuzzle`. This violates SRP and makes the file enormous. | High | `app.tsx:33-500` |
| AQ-2 | **`RushPuzzle` type defined twice** — Once in `app.tsx:34` and again in `PuzzleRushPage.tsx:32`. Both extend `CollectionPuzzleEntry`. | Medium | `app.tsx:34`, `PuzzleRushPage.tsx:32` |
| AQ-3 | **InlinePuzzleSolver not reusable** — Defined as a component inside `app.tsx` (not exported from a module). `RandomChallengePage` also uses it via `renderRandomPuzzle`. Should be extracted to a shared component. | High | `app.tsx:148-174`, `app.tsx:505-513` |
| AQ-4 | **No dedicated Rush service** — Puzzle loading, filtering, and pool management are all inline in `app.tsx` callbacks. Other modes have dedicated services (`dailyChallengeService`, `collectionService`). | Medium | `app.tsx:360-450` |
| AQ-5 | **E2E tests reference `/puzzle-rush` path but route is `/modes/rush`** — `rush-start.spec.ts:15` navigates to `/puzzle-rush` but the actual route is `/modes/rush` per `routes.ts`. Tests may not reach the Rush page. | High | `rush-start.spec.ts:15` vs `routes.ts:101` |

---

## 5. Code Duplication Analysis

### R-5: Rush vs Standard Puzzle Solver

| Aspect | Standard (`SolverView`) | Rush (`InlinePuzzleSolver`) | Shared? |
|--------|-------------------------|-------------------------------|---------|
| SGF loading | `puzzleLoader.loadPuzzle(entry)` | `fetchSGFContent(puzzle.path)` | Different entry points |
| Board creation | `useGoban(sgf, treeRef, config)` | `useGoban(sgf, treeRef)` | Same hook, Rush missing config |
| Solve state | `usePuzzleState(goban)` | `usePuzzleState(goban)` | ✅ Same |
| Board display | `GobanContainer` with `solver-board-col` | `GobanContainer` with inline Tailwind | Different styling approach |
| Hints | 3-tier hint system (`useHints`) | None | Not shared |
| Transforms | Board rotation/flip (`useTransforms`) | None | Not shared |
| Auto-advance | Configurable via `PuzzleSetPlayer` | Custom via `completedRef` + `useEffect` | Different |
| Audio | Via `puzzleState` callbacks | Not integrated | Missing |
| Progress tracking | `recordCompletion()` per puzzle | `recordRushScore()` aggregate only | Different granularity |
| Wrong handling | Immediate feedback, retry | 3-retry threshold then fail | Different (see GP-3) |
| Solution reveal | `SolutionReveal` modal | None | Not applicable |

**Key observation**: `InlinePuzzleSolver` is a ~30-line minimal reimplementation that duplicates core patterns from `SolverView` without the full feature set. It lacks audio feedback, transform support, hints, and proper sizing.

---

## 6. Shared Infrastructure Analysis

### R-6: What Rush Uses vs Should Use

| Infrastructure | Rush Uses? | Should Use? | Gap |
|---------------|------------|-------------|-----|
| `PageLayout` with mode | Browse page ✅, Play page ❌ | Both | Play page needs PageLayout wrapping |
| `PageHeader` | Browse page ✅, Play page ❌ | Browse only (play has HUD) | OK |
| `SolverView` | ❌ (uses `InlinePuzzleSolver`) | Consider — SolverView has hints/transforms | Partial — Rush needs minimal solver |
| `PuzzleSetPlayer` | ❌ | No — Rush has different flow (no set, stream) | OK |
| `audioService` | ❌ | Yes — correct/wrong sounds expected | Missing audio integration |
| `useHints` | ❌ | No — Rush is speed mode, hints defeat purpose | OK |
| `useTransforms` | ❌ | Optional — board flip/rotate could help | Low priority |
| `progress/recordCompletion` | ❌ (uses `recordRushScore` only) | Consider — per-puzzle tracking for analytics | Enhancement opportunity |
| `configService` (level/tag resolution) | ✅ | ✅ | OK |
| `sqliteService` + query service | ✅ | ✅ | OK |

---

## 7. AGENTS.md Coverage

The `frontend/src/AGENTS.md` documents Rush components:

- **Pages**: `pages/PuzzleRushPage.tsx` — "Timed rush mode" (line 31)
- **Hooks**: `hooks/useRushSession.ts` — "Rush mode timer + session state" (line 52)
- **Missing**: `RushBrowsePage`, `RushOverlay`, `InlinePuzzleSolver` (in app.tsx), `RushPuzzleRenderer` (in app.tsx) are not documented in AGENTS.md

---

## 8. Planner Recommendations

1. **[CRITICAL] Fix best-score data mismatch (GP-1)**: Replace the inline `getBestScore()` in `app.tsx` that reads `yen-go-rush-best-score` with a call to `getRushHighScore()` from `services/progress/progressCalculations.ts` which reads the actual stored scores. This is a one-line fix that immediately restores the "Best Score" display on `RushBrowsePage`.

2. **[CRITICAL] Enable filters on RushBrowsePage (GP-7)**: The line `const masterLoaded = false;` completely hides all filter UI. Wire up actual puzzle count data from SQLite (similar to how `TechniqueBrowsePage` and `CollectionsBrowsePage` load counts) or set `masterLoaded = true` and populate level/tag counts.

3. **[HIGH] Fix wrong-answer threshold for Rush (GP-3)**: `InlinePuzzleSolver` gives 3 retries before counting a puzzle as failed. In Rush mode, first wrong move should cost a life and advance. Either: (a) pass a `maxAttempts` prop to `InlinePuzzleSolver` (Rush=1, Random=3), or (b) create a Rush-specific solver variant.

4. **[HIGH] Extract Rush code from app.tsx (AQ-1, AQ-2, AQ-3)**: Move `InlinePuzzleSolver` to `components/shared/InlineSolver/`, `RushPuzzleRenderer` to `components/Rush/`, puzzle loading to `services/puzzleRushService.ts`, and `RushPuzzle` type to `models/collection.ts`. This is a Level 3 correction — refactor that touches 3-4 files but no behavior change.

5. **[MEDIUM] Wrap PuzzleRushPage in PageLayout (CSS-1)**: Replace the raw `<div data-mode="rush">` with `<PageLayout variant="single-column" mode="rush">` for consistent layout, scroll handling, and CSS variable cascade — matching `RushBrowsePage`'s approach.

6. **[MEDIUM] Replace emojis with SVG icons (CSS-2, CSS-3)**: Replace `🔥` with `FireIcon` SVG, `⏸` with `PauseIcon` SVG, per the "No emojis in production UI" design rule.

7. **[MEDIUM] Fix RushOverlay absolute positioning (CSS-4)**: The paused/game-over overlays use `absolute inset-0` inside the HUD bar, but they need to cover the entire page. Move overlays outside the bar or restructure the component hierarchy.

---

## 9. Confidence & Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 90 |
| `post_research_risk_level` | medium |

**Confidence notes**: All Rush source files were read in full. The dual best-score issue (GP-1) and disabled filters (GP-7) are unambiguous bugs. The 3-retry threshold (GP-3) requires confirmation of design intent.

**Risk notes**: Main risk is the `app.tsx` refactoring (recommendation 4) — it's a large file with many interconnected callbacks. Extracting Rush code must be done carefully to avoid breaking Random mode which shares `InlinePuzzleSolver` and `RushPuzzleRenderer`.

---

## 10. Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should Rush give 1 attempt per puzzle (fail on first wrong move) or keep the 3-retry system with life cost on final failure? | A: 1 attempt (strict Rush), B: 3 attempts (current), C: Configurable | A (strict Rush) | | ❌ pending |
| Q2 | Should the E2E tests be updated to use `/modes/rush` path (matching actual routing) or should a redirect be added? | A: Fix test paths, B: Add redirect | A | | ❌ pending |
| Q3 | Should `InlinePuzzleSolver` include audio feedback (correct/wrong sounds)? | A: Yes, B: No (speed mode should be silent), C: User preference | A | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260322-research-rush-timed-puzzle-audit/
artifact: 15-research.md
top_recommendations:
  - Fix best-score data mismatch (GP-1) — critical one-line fix
  - Enable filters on RushBrowsePage (GP-7) — masterLoaded = false disables all filtering
  - Fix wrong-answer threshold for Rush (GP-3) — 3 retries defeats Rush purpose
  - Extract Rush code from app.tsx (AQ-1) — SRP violation, ~470 lines of Rush code in root component
open_questions:
  - Q1: Rush attempt count per puzzle (1 vs 3)
  - Q2: E2E test path mismatch
  - Q3: Audio feedback in Rush
post_research_confidence_score: 90
post_research_risk_level: medium
```
