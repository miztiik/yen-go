# Research Brief: Playing Mode DRY/SRP/SOLID/KISS Compliance Audit

**Date**: 2026-03-29
**Initiative**: `20260329-research-playing-mode-dry-audit`
**Status**: Complete

---

## 1. Research Question and Boundaries

**Question**: Which of the frontend's puzzle-playing modes comply with the shared `PuzzleSetPlayer → SolverView` architecture, and which bypass it with custom implementations?

**Scope**:
- All routed playing modes in `frontend/src/app.tsx`
- Board rendering path, layout pattern, PuzzleSetPlayer usage, board sizing for each
- Identification of duplicated components across modes

**Out of scope**: Browse/selection pages (RushBrowsePage, TrainingBrowsePage, etc.), non-puzzle pages (Progress, Learning, Home).

---

## 2. Internal Code Evidence

### 2.1 Canonical Architecture (the "golden path")

The shared architecture is a 3-layer stack:

| R-1 | Layer | Component | File | Purpose |
|-----|-------|-----------|------|---------|
| R-1a | Sequencer | `PuzzleSetPlayer` | `components/PuzzleSetPlayer/index.tsx` | Manages puzzle loading, pagination, completion tracking, auto-advance, progress hydration |
| R-1b | Solver | `SolverView` | `components/Solver/SolverView.tsx` | 2-column OGS-style layout (board + sidebar), transforms, hints, undo/reset, solution reveal, keyboard shortcuts |
| R-1c | Board | `GobanContainer` | `components/GobanContainer.tsx` | Mounts goban DOM element, responsive sizing via CSS (`solver-layout` / `puzzle-layout`) |

**Rendering chain**: Page → `PuzzleSetPlayer` → `SolverView` → `GobanContainer`

SolverView uses `.solver-layout` CSS (app.css L715–860) for responsive 2-column board + sidebar at 62/38% split on desktop, stacked on mobile.

### 2.2 Alternative Rendering Chain (Rush/Random bypass)

| R-2 | Layer | Component | File | Purpose |
|-----|-------|-----------|------|---------|
| R-2a | SGF Loader | `RushPuzzleRenderer` | `components/Rush/RushPuzzleRenderer.tsx` | Fetches SGF, renders via InlineSolver |
| R-2b | Minimal Solver | `InlineSolver` | `components/shared/InlineSolver/InlineSolver.tsx` | Bare-bones goban + move validation, no sidebar, no hints, no transforms |
| R-2c | Board | `GobanContainer` | Same as canonical | Same board mount, but no layout framework around it |

**Rendering chain**: Page → `RushPuzzleRenderer` → `InlineSolver` → `GobanContainer`

### 2.3 Legacy Components (Dead Code)

| R-3 | Component | File | Status |
|-----|-----------|------|--------|
| R-3a | `PuzzleSolvePage` | `pages/PuzzleSolvePage.tsx` | **Not routed** — uses `GobanRenderer`, `PuzzleChrome`, `PageLayout variant="puzzle"` directly. Appears to be pre-SolverView dead code. |
| R-3b | `ReviewPage` | `pages/ReviewPage.tsx` | **Not routed** — uses `preact-iso`, separate review controller. Dead code. |
| R-3c | `RushMode` | `components/Rush/RushMode.tsx` | Uses `Board` component directly (not GobanContainer). References old puzzle model. Likely superseded by PuzzleRushPage + InlineSolver. |
| R-3d | `TrainingPage` | `pages/TrainingPage.tsx` | Duplicate of `TrainingViewPage.tsx` — both use PuzzleSetPlayer. One is likely dead. |

---

## 3. Compliance Matrix

| R-4 | Mode | Route Type | Page Component | Uses PuzzleSetPlayer? | Uses SolverView? | Board Rendering | Layout Pattern | Board Sizing | Compliant? | Issues |
|-----|------|------------|----------------|----------------------|-------------------|-----------------|----------------|-------------|------------|--------|
| R-4a | **Collection** | `context/collection` | `CollectionViewPage` | **Yes** | **Yes** (via PSP) | GobanContainer → solver-layout CSS | PSP manages layout internally | Responsive CSS vars (62/38 split) | **Yes** | — |
| R-4b | **Technique** | `context/technique` | `TechniqueViewPage` | **Yes** | **Yes** (via PSP) | GobanContainer → solver-layout CSS | PSP manages layout internally | Responsive CSS vars | **Yes** | — |
| R-4c | **Training** | `context/training` | `TrainingViewPage` | **Yes** | **Yes** (via PSP) | GobanContainer → solver-layout CSS | PSP manages layout internally | Responsive CSS vars | **Yes** | — |
| R-4d | **Daily Standard** | `modes-daily-date` | `DailyChallengePage` | **Yes** | **Yes** (via PSP) | GobanContainer → solver-layout CSS | `PageLayout mode="daily"` wraps PSP | Responsive CSS vars | **Yes** | — |
| R-4e | **Daily Timed** | `modes-daily-date?mode=timed` | `DailyChallengePage` | **Yes** | **Yes** (via PSP, `failOnWrong=true`) | GobanContainer → solver-layout CSS | Same as standard daily | Responsive CSS vars | **Yes** | — |
| R-4f | **Smart Practice** | `smart-practice` | `SmartPracticePage` | **Yes** | **Yes** (via PSP) | GobanContainer → solver-layout CSS | `<div>` wrapper → PSP | Responsive CSS vars | **Yes** | Wrapping `<div>` instead of `PageLayout` (minor inconsistency) |
| R-4g | **Puzzle Rush** | `modes-rush` | `PuzzleRushPage` | **No** | **No** | `RushPuzzleRenderer` → `InlineSolver` → `GobanContainer` | `PageLayout variant="single-column" mode="rush"` + custom flex layout | Hardcoded `max-w-[600px]`, custom flex sizing | **No** | Bypasses PuzzleSetPlayer entirely; builds own sequencer, timer, results screen; no sidebar, no hints, no transforms |
| R-4h | **Random Challenge** | `modes-random` | `RandomChallengePage` | **No** | **No** | `RushPuzzleRenderer` → `InlineSolver` → `GobanContainer` (injected via `renderPuzzle` from App.tsx) | `PageLayout mode="random"` + `PageLayout.Content` + custom header/results | Full-width, `max-w-[800px]` container | **No** | Bypasses PuzzleSetPlayer; builds own sequencer, results screen; no sidebar, no hints, no transforms |

---

## 4. Duplicated Components Across Modes

| R-5 | Duplicated Concern | Canonical Location | Rush Implementation | Random Implementation |
|-----|-------------------|-------------------|---------------------|----------------------|
| R-5a | **Puzzle sequencing** | `PuzzleSetPlayer` (index tracking, load, advance, skip) | `PuzzleRushPage` + `useRushSession` + `App.getNextPuzzle` | `RandomChallengePage` state machine + `App.getRandomPuzzle` |
| R-5b | **SGF loading** | `PuzzleSetLoader.getPuzzleSgf()` (with prefetch, retry) | `RushPuzzleRenderer` (inline `fetchSGFContent` call, no prefetch) | Same `RushPuzzleRenderer` (shared with Rush) |
| R-5c | **Results/summary screen** | `PuzzleSetPlayer.renderSummary()` callback | `PuzzleRushPage` finished state (inline JSX, ~50 lines) | `RandomChallengePage` result state (inline JSX, ~40 lines) |
| R-5d | **Accuracy calculation** | Various pages import `getAccuracyColorClass` (shared util ✓) | Manual `Math.round((solved/total) * 100)` inline | Same manual calculation |
| R-5e | **Board rendering** | `SolverView` (2-column, hints, transforms, undo, review) | `InlineSolver` (board-only, wrong attempt counter, no sidebar) | Same `InlineSolver` via `RushPuzzleRenderer` |
| R-5f | **Progress recording** | `onPuzzleComplete` callback in PSP → page-level handler | `recordRushScore()` called directly in page | No progress recording |
| R-5g | **Custom header** | `PuzzleSetHeader` (shared component) | `RushOverlay` (timer, lives, score, skip/quit) | Gradient header bar (inline JSX) |

### Key Observation: App.tsx Rendering Indirection

Both Rush and Random modes use a **render-prop injection pattern** where `App.tsx` creates `renderPuzzle` / `renderRandomPuzzle` callbacks that wrap `RushPuzzleRenderer`, then passes these down to the page components. This adds an extra layer of indirection that the compliant modes avoid — those modes let `PuzzleSetPlayer` handle rendering internally via `SolverView`.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-6 | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| R-6a | Rush mode has fundamentally different UX (countdown, lives, timed skip) that may not fit PuzzleSetPlayer's sequential model | Medium | PuzzleSetPlayer already supports `failOnWrong` for Daily Timed. Rush needs a superset: timer overlay, lives counter, streak bonus. Could be an additional `mode` in PuzzleSetPlayer or a wrapper. |
| R-6b | Random mode is "infinite sequential" (no fixed puzzle set), which conflicts with PuzzleSetPlayer's pre-loaded finite set model | Medium | PuzzleSetPlayer requires a `PuzzleSetLoader` with known total. Random would need a streaming/unbounded loader variant or remain a separate path with shared sub-components. |
| R-6c | InlineSolver intentionally strips features (no hints, no sidebar, no transforms) for speed-focused modes | Low | SolverView could accept a `minimal` or `rushMode` prop to hide sidebar/hints. This would be a simpler adaptation than maintaining two parallel solving components. |
| R-6d | Refactoring Rush may break the existing test suite (`rush.test.ts`, `rush-score.test.tsx`, `rush-results.test.tsx`, `rushMode.test.tsx`) | Medium | Tests are well-isolated; refactoring should update them in the same PR. |
| R-6e | Dead code (PuzzleSolvePage, ReviewPage, RushMode, TrainingPage) clutters the codebase and creates confusion about which components are canonical | Low | Can be cleaned up independently (Level 2–3 correction). |

---

## 6. External References

| R-7 | Reference | Relevance |
|-----|-----------|-----------|
| R-7a | [OGS puzzle interface](https://online-go.com/) | Yen-Go explicitly follows OGS patterns for board rendering; the 2-column solver layout is derived from OGS. All compliant modes align. Rush/Random deviate. |
| R-7b | [chess.com Puzzle Rush](https://www.chess.com/puzzles/rush) | Chess equivalent of Puzzle Rush — uses same board component as normal puzzles but with timer/lives overlay and stripped sidebar. Validates the "same board, reduced chrome" pattern. |
| R-7c | [Lichess Puzzle Storm](https://lichess.org/storm) | Similar to chess.com Rush — reuses board component with minimal UI overlay. Demonstrates the "shared board + mode-specific overlay" pattern at production scale. |
| R-7d | Compound Component pattern (React patterns) | PuzzleSetPlayer already uses render-prop callbacks (`renderHeader`, `renderNavigation`, `renderSummary`). This pattern is extensible for Rush mode's timer overlay and Random mode's infinite loading. |

---

## 7. Candidate Adaptations for Yen-Go

### Option A: Extend PuzzleSetPlayer with Rush/Random modes

Add `rushMode` and `randomMode` support to PuzzleSetPlayer:
- New `PuzzleStreamLoader` interface for infinite/random puzzles (extends `PuzzleSetLoader` with unbounded `getTotal()`)
- SolverView gains a `variant="minimal"` prop (hides sidebar, hints, transforms)
- Rush timer/lives/score rendered via `renderHeader` callback (already supported)
- Rush results via `renderSummary` callback (already supported)

**Pros**: Maximum DRY, single rendering pipeline, all modes benefit from SolverView improvements (transforms, viewport cropping, etc.)
**Cons**: PuzzleSetPlayer becomes more complex; Rush's "speed" UX may suffer from SolverView's full initialization overhead.

### Option B: Extract shared sub-components, keep separate pages

Keep PuzzleRushPage/RandomChallengePage as separate pages but:
- Replace `InlineSolver` with `SolverView variant="minimal"` for consistent board rendering
- Extract shared results screen component from Rush/Random (eliminate R-5c duplication)
- Keep Rush's own sequencer (lives/timer logic is genuinely different from sequential solving)

**Pros**: Less risk, preserves Rush-specific optimizations, simpler changes
**Cons**: Sequencing logic remains duplicated; future modes would still need custom pages.

### Option C: Hybrid — PuzzleSetPlayer for Random, standalone for Rush

Random mode is close enough to Daily (sequential puzzles, no timer) to use PuzzleSetPlayer with a streaming loader. Rush mode's timer/lives/scoring is genuinely unique enough to warrant its own page, but with shared sub-components.

**Pros**: Pragmatic balance — fixes the easier case (Random) fully, reduces Rush duplication via shared components
**Cons**: Two architectural patterns remain.

---

## 8. Planner Recommendations

1. **R-REC-1 (High priority)**: Adopt **Option C (Hybrid)** — migrate Random Challenge to PuzzleSetPlayer (it's close to Daily Timed in structure), keep Rush as separate page but replace InlineSolver with SolverView `variant="minimal"`. This eliminates the most duplication with lowest risk.

2. **R-REC-2 (Medium priority)**: Delete dead code — PuzzleSolvePage, ReviewPage, RushMode (old), and one of TrainingPage/TrainingViewPage. This is a Level 2 change that removes ~1,200 lines of confusion. Should happen before or alongside the refactor.

3. **R-REC-3 (Low priority, future)**: After validating Option C, evaluate whether Rush should also migrate to PuzzleSetPlayer with an `InfiniteLoader` + timer mode. This is a larger architectural decision (Level 4) that should be deferred until the simpler migration proves the pattern.

4. **R-REC-4 (Immediate)**: Extract shared `SessionResults` component from Rush/Random results screens. Both build nearly identical result cards (score, accuracy, action buttons). This is a Level 1 extraction that can happen independently.

---

## 9. Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should SolverView support a `variant="minimal"` prop (board-only, no sidebar/hints), or should InlineSolver be promoted as the official "minimal solver" and given SolverView's responsive sizing? | A: SolverView minimal variant / B: Promote InlineSolver / C: New shared component | A: SolverView minimal variant (single code path, all improvements flow through) | | ❌ pending |
| Q2 | Is the Random mode's "infinite sequential" pattern needed by future modes (e.g., spaced repetition, retry queue)? If so, building a `StreamingLoader` abstraction is worth the investment now. | A: Yes, build StreamingLoader / B: No, Random-specific adapter is fine / C: Defer decision | A: Yes — retry queue and spaced repetition will need similar patterns | | ❌ pending |
| Q3 | Should dead code cleanup (R-REC-2) be a prerequisite for the refactor, or can it happen in parallel? | A: Prerequisite / B: Parallel / C: After | B: Parallel — separate PR, no dependency | | ❌ pending |
| Q4 | TrainingPage.tsx vs TrainingViewPage.tsx — which is canonical? TrainingViewPage is routed in App.tsx; TrainingPage is not imported in App.tsx. Confirm TrainingPage is dead code. | A: TrainingPage is dead / B: Need to check further | A: TrainingPage is dead (not imported in App.tsx) | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260329-research-playing-mode-dry-audit/
artifact: 15-research.md
top_recommendations:
  - "R-REC-1: Hybrid approach — Random to PuzzleSetPlayer, Rush keeps separate page with shared sub-components"
  - "R-REC-2: Delete dead code (PuzzleSolvePage, ReviewPage, RushMode, TrainingPage) — ~1,200 lines"
  - "R-REC-3: Evaluate Rush → PuzzleSetPlayer migration after Random migration proves the pattern"
  - "R-REC-4: Extract shared SessionResults component from Rush/Random results screens"
open_questions:
  - "Q1: SolverView minimal variant vs InlineSolver promotion"
  - "Q2: StreamingLoader abstraction for infinite puzzle modes"
  - "Q3: Dead code cleanup sequencing"
  - "Q4: TrainingPage.tsx dead code confirmation"
post_research_confidence_score: 88
post_research_risk_level: medium
```
