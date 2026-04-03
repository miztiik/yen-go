# Tasks — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Last Updated:** 2026-03-11

---

## Task Dependency Graph

```
Phase 1: Critical Fixes (independent, parallelizable)
  T1 (SSE board updates) ─────────────────────────────────┐
  T2 (engine status labels) ───────────────────────────────┤
                                                           │
Phase 2: Layout Restructure                                │
  T3 (3-column CSS grid) ─────────────────────────────────┤
  T4 (right panel HTML) ──────────────────┬────────────────┤
                                          ├─ T5 (tree → right panel)
                                          ├─ T6 (analysis table → right panel)
                                          ├─ T7 (policy priors → right panel)
                                          └─ T8 (finalize BesoGo panel removal)
                                                           │
Phase 3: Board Overlays                                    │
  T9 (board-overlay.js module) ────────────┬───────────────┤
                                           ├─ T10 (score overlays)
                                           └─ T11 (PV hover preview)
                                                           │
Phase 4: Status & Polish                                   │
  T12 (player indicator) ─────────────────────────────────┤
  T13 (log panel resize) ─────────────────────────────────┤
  T14 (button tooltips) ──────────────────────────────────┤
  T15 (tree node annotations) ────────────────────────────┤
                                                           │
Phase 5: Validation                                        │
  T16 (smoke test) ───────────────────────────────────────┤
  T17 (docs update) ──────────────────────────────────────┘
```

---

## Phase 1: Critical Fixes

### T1: Fix board updates during SSE enrichment events

**Files:** `gui/src/app.js`
**Issue:** C1 (board doesn't update during enrichment)
**Depends on:** —
**Parallel:** [P] with T2
**AC:** AC9

Currently `processSSEEvent()` only updates the board on the final `enriched_sgf` event (`status === 'complete'`). The `board_state` event at line 107-109 logs a message but does not update the BesoGo board.

**Changes:**
1. In the `board_state` case, if `data.sgf` is present, call `sgfText.set(data.sgf)` to update the board
2. If `data` contains position data without SGF (board array + stone positions), construct a minimal SGF from it or use `loadSgf()` with position data
3. On `analysis` events that contain intermediate results, update `analysisResult` state

**Verification:** Load an SGF → click Enrich → observe board updating at intermediate stages (parse, validate, refute, etc.)

---

### T2: Fix engine status with human-readable labels

**Files:** `gui/src/sgf-input.js`, `gui/src/app.js`
**Issue:** C2 (engine status misleading)
**Depends on:** —
**Parallel:** [P] with T1
**AC:** AC8

**Changes:**
1. Create a status label mapping function in `app.js`:
   ```javascript
   function engineStatusLabel(raw) {
     const labels = {
       'not_started': 'Idle',
       'starting': 'Starting...',
       'ready': 'Ready',
       'running': 'Running...',
       'error': 'Error',
       'enriching': 'Enriching...',
       'analyzing': 'Analyzing...',
     };
     return labels[raw] || raw;
   }
   ```
2. Apply in the health check handler (`app.js:50-53`): `modelEl.textContent = engineStatusLabel(health.status)`
3. Add CSS classes for visual differentiation: green dot for Ready, pulse for Running, red for Error

**Verification:** Load page → shows "Idle". Click Analyze → shows "Running..." → shows "Ready" after completion.

---

## Phase 2: Layout Restructure

### T3: Restructure CSS to 3-column grid layout

**Files:** `gui/css/styles.css`
**Issue:** M1 (board shrinks)
**Depends on:** —
**Parallel:** [P] with T4
**AC:** AC1

**Changes:**
1. Replace `.layout` flexbox with CSS grid:
   ```css
   .layout {
     display: grid;
     grid-template-columns: 220px minmax(520px, 1fr) 320px;
     grid-template-rows: 1fr;
     gap: 12px;
     padding: 8px 12px;
     height: calc(100vh - var(--pipeline-bar-height, 50px) - var(--log-panel-height, 200px));
   }
   ```
2. Set `#besogo-container` with `min-width: 520px; aspect-ratio: 1;` to maintain square board
3. Add `.right-panel` styles: scrollable, stacked vertical layout for tree + policy + analysis
4. Remove `max-width: 1600px` from `.layout` (grid handles widths)

**Verification:** Resize browser from 1280px to 1920px+ → board stays >=520px, right panel stays ~320px.

---

### T4: Add right panel HTML structure

**Files:** `gui/index.html`
**Issue:** M2, m1
**Depends on:** —
**Parallel:** [P] with T3
**AC:** AC2, AC12

**Changes:**
1. Add a `<aside class="right-panel">` after `<main>`:
   ```html
   <aside class="right-panel">
     <div id="player-indicator"></div>
     <div id="solution-tree-panel"></div>
     <div id="policy-priors"></div>
     <div id="analysis-table"></div>
   </aside>
   ```
2. Remove `<div id="analysis-table"></div>` from inside `<main>`
3. The `#policy-priors` div is now pre-placed in the right panel (currently dynamically created in `board.js`)

**Verification:** Page loads. DevTools shows 3-column grid structure with right panel present.

---

### T5: Move solution tree to right panel

**Files:** `gui/src/board.js`
**Issue:** M2
**Depends on:** T4
**Parallel:** [P] with T6, T7
**AC:** AC2

**Changes:**
1. Keep `panels: ['tree']` in BesoGo config (so BesoGo creates and manages the tree internally)
2. After `besogo.create()`, locate the tree panel DOM node: `container.querySelector('.besogo-tree')` (or the parent `.besogo-panels`)
3. Relocate it: `document.getElementById('solution-tree-panel').appendChild(treePanelElement)`
4. This preserves all BesoGo tree rendering (correct/wrong coloring, navigation) while placing it in the right panel

**Verification:** Solution tree renders inside the right panel. Board takes full width of its grid column.

---

### T6: Move analysis table to right panel

**Files:** `gui/src/app.js`
**Issue:** m1
**Depends on:** T4
**Parallel:** [P] with T5, T7
**AC:** AC12

**Changes:**
1. In `app.js`, `initAnalysisTable()` call already takes a container element. Since T4 places `#analysis-table` in the right panel, this should work automatically.
2. Add CSS for the table inside the right panel: compact font size, scrollable overflow, max-height.

**Verification:** Analysis table renders in the right panel below the tree.

---

### T7: Move policy priors to right panel

**Files:** `gui/src/board.js`, `gui/src/policy-panel.js`
**Issue:** M2 (related)
**Depends on:** T4
**Parallel:** [P] with T5, T6

**Changes:**
1. Remove the code in `board.js:94-104` that dynamically creates `#policy-priors` inside `.besogo-panels`
2. Since T4 pre-places `#policy-priors` in the right panel HTML, `initPolicyPanel()` will resolve it by ID as it already does (`getPanel()` returns `document.getElementById(PANEL_ID)`)
3. Verify CSS styling works in the new container

**Verification:** Policy priors bar chart renders in the right panel.

---

### T8: Finalize BesoGo panel removal

**Files:** `gui/src/board.js`, `gui/css/styles.css`
**Depends on:** T5, T6, T7

**Changes:**
1. Once tree is relocated and policy priors are in the right panel, the `.besogo-panels` div should be empty or hidden
2. If the tree was relocated, `.besogo-panels` may contain only an empty div. Hide it: `.besogo-panels { display: none; }` or set `width: 0`
3. Alternatively, if T5 relocates the entire `.besogo-panels` to the right panel, remove the hiding CSS
4. Verify board takes 100% of its grid cell with no internal panel splitting

**Verification:** Board fills its entire grid column. No internal horizontal splitting.

---

## Phase 3: Board Overlays

### T9: Create board-overlay.js module

**Files:** `gui/src/board-overlay.js` (NEW)
**Depends on:** T3 (board positioning must be stable)
**Parallel:** [P] with T5-T8 (can start before panel moves complete)
**AC:** AC3, AC5, AC6

Create a new ES module for rendering SVG overlays on top of the BesoGo board.

**Public API:**
```javascript
export function initBoardOverlay(boardContainer) { ... }
export function showScoreOverlays(candidates, boardSize) { ... }
export function showPVPreview(pvMoves, boardSize, startColor) { ... }
export function clearOverlays() { ... }
export function clearPVPreview() { ... }
```

**Implementation:**
1. Create an absolutely positioned `<svg>` element covering the board container, z-index above BesoGo, `pointer-events: none`
2. Coordinate mapping: `(gtpCol, gtpRow)` → `(svgX, svgY)`. Must match BesoGo's grid layout.
3. Use `ResizeObserver` to keep overlay dimensions synced with the board container
4. Subscribe to `analysisResult` state atom to auto-render overlays when analysis arrives

**Verification:** Manually call `showScoreOverlays()` with test data → circles appear at correct intersections.

---

### T10: Render score overlays on board intersections

**Files:** `gui/src/board-overlay.js`, `gui/src/app.js`
**Issue:** M3
**Depends on:** T9
**AC:** AC3

**Changes:**
1. When `analysisResult` updates, call `showScoreOverlays(result.moves.slice(0, 8), result.boardSize)`
2. Each candidate rendered as:
   - Colored circle at the intersection (~70% of cell size)
   - Score value as text inside the circle (e.g., "-52.8")
   - Visit count as smaller text below (e.g., "392")
   - Color: green (#22c55e) for rank 1, blue (#60a5fa) for alternatives
3. Limit to top 5-8 candidates to avoid clutter
4. When analysis clears, remove overlays

**Verification:** Click Analyze → score circles appear on board at candidate intersections with correct positions.

---

### T11: PV hover preview with numbered stones

**Files:** `gui/src/board-overlay.js`, `gui/src/analysis-table.js`
**Issue:** M4
**Depends on:** T9, T6 (analysis table must be wired)
**AC:** AC5, AC6

**Changes:**
1. In `analysis-table.js`, add `mouseenter`/`mouseleave` handlers on each `<tr>`:
   - `mouseenter`: Read PV moves from row data. Call `showPVPreview(pvMoves, boardSize, startColor)`.
   - `mouseleave`: Call `clearPVPreview()`.
2. In `board-overlay.js`, `showPVPreview()` renders:
   - Semi-transparent stones (opacity 0.6) at each PV intersection
   - Black/white alternating based on `startColor` and move index
   - A number label (1, 2, 3...) centered on each stone
   - First stone (the candidate) gets a highlighted border
3. Show orange/salmon score overlay on the candidate's intersection
4. Debounce mouseenter with ~50ms to prevent flicker

**Verification:** Hover over analysis row → numbered stones appear on board. Mouse leaves → stones disappear.

---

## Phase 4: Status & Polish

### T12: Add player-to-move indicator

**Files:** `gui/src/player-indicator.js` (NEW), `gui/src/app.js`
**Issue:** M5
**Depends on:** T4 (right panel must exist)
**Parallel:** [P] with T13, T14
**AC:** AC7

**Changes:**
1. Create `player-indicator.js` module:
   - Renders inside `#player-indicator` in the right panel
   - Shows filled circle (black or white SVG) + "Black to play" / "White to play"
   - Shows aggregate stats: "Visits: {rootVisits} | Score: {rootScore}" from analysis result
2. Subscribe to `analysisResult` and `boardState` state atoms
3. Wire the module in `app.js` bootstrap

**Verification:** Load a puzzle → "Black to play" with black circle. After analysis → aggregate stats shown.

---

### T13: Increase log panel height and make resizable

**Files:** `gui/css/styles.css`, `gui/src/log-panel.js`
**Issue:** M6
**Depends on:** T3 (layout must be restructured)
**Parallel:** [P] with T12, T14
**AC:** AC10

**Changes:**
1. Increase `#log-panel` max-height from 200px to 400px
2. Increase `.log-content` max-height from 160px to 350px
3. Add `resize: vertical; overflow: auto;` to `.log-content` for user-resizable panel
4. When collapsed, show only the header bar

**Verification:** Log panel is visibly larger (~300px). User can drag to resize the content area.

---

### T14: Add Enrich/Analyze button tooltips

**Files:** `gui/src/sgf-input.js`
**Issue:** M7
**Depends on:** —
**Parallel:** [P] with T12, T13
**AC:** AC11

**Changes:**
1. Add `title` attributes to the action buttons in the `render()` function:
   - Enrich: `"Run full 10-stage pipeline: parse → validate → refute → difficulty → teach → build SGF"`
   - Analyze: `"Quick KataGo analysis of current board position (~1-3s)"`
   - Cancel: `"Cancel the current enrichment pipeline run"`

**Verification:** Hover over Enrich button → tooltip appears with pipeline description.

---

### T15: Add score annotations to solution tree nodes

**Files:** `gui/src/board-overlay.js` or custom tree post-processor
**Issue:** M3 (tree part)
**Depends on:** T5 (tree in right panel), T10 (overlay module working)
**AC:** AC4

**Changes:**
1. After analysis, add tooltips to tree nodes showing score/prior data
2. Approach: query tree node SVG elements in `#solution-tree-panel`, attach `title` attributes with formatted score info
3. Alternative: add small score text labels adjacent to tree node circles

**Verification:** Hover a tree node → tooltip shows score, visits, prior for that position.

---

## Phase 5: Validation

### T16: Manual smoke test (full workflow)

**Files:** —
**Depends on:** T1-T15
**AC:** All

Test checklist:
1. Start bridge.py, open `http://localhost:8999`
2. Paste/upload an SGF puzzle
3. Verify 3-column layout: sidebar, board (large), right panel
4. Click Analyze → score overlays appear on board intersections
5. Hover analysis table row → numbered PV stones appear on board
6. Mouse leaves row → PV stones disappear
7. Player-to-move indicator shows correct color and stats
8. Click Enrich → board updates at each pipeline stage
9. Engine status transitions: Idle → Enriching... → Ready
10. Solution tree renders in right panel with correct/wrong coloring
11. Log panel is larger, can be resized
12. Resize browser from 1280px to 1920px → board stays large, right panel adapts
13. Keyboard navigation (arrow keys, Home/End) still works
14. SGF download works after enrichment

---

### T17: Update documentation

**Files:** `gui/README.md`, `gui/docs/target-reference-architecture.md`
**Depends on:** T16

**Changes:**
1. Update `gui/README.md`: add new features to feature list, update layout description, add new files to key files table
2. Check off completed items in `gui/docs/target-reference-architecture.md` GoProblems Feature Parity Checklist
3. Update the current layout ASCII diagram to reflect the 3-column structure

**Verification:** README accurately describes the current GUI post-update.

---

## Parallel Execution Map

```
Time ────────────────────────────────────────────>

Phase 1:  [T1] ****  (SSE board updates)
          [T2] ****  (engine status labels)

Phase 2:  [T3] ********  (CSS layout)
          [T4] ****      (HTML right panel)
                    [T5] ****  (tree → right panel)
                    [T6] **    (analysis → right panel)    [P]
                    [T7] **    (policy → right panel)      [P]
                        [T8] **  (finalize panel removal)

Phase 3:  [T9] ********  (overlay module)                  [P with T5-T8]
                    [T10] ****  (score overlays)
                          [T11] ******  (PV hover)

Phase 4:  [T12] ****  (player indicator)                   [P with T9-T11]
          [T13] **    (log panel)                           [P]
          [T14] **    (tooltips)                            [P]
                [T15] ****  (tree annotations)

Phase 5:              [T16] ****  (smoke test)
                            [T17] **  (docs)
```

---

## Effort Summary

| Phase | Tasks | Estimated Effort |
|-------|-------|-----------------|
| Phase 1: Critical Fixes | T1, T2 | 2h |
| Phase 2: Layout Restructure | T3, T4, T5, T6, T7, T8 | 4h |
| Phase 3: Board Overlays | T9, T10, T11 | 5h |
| Phase 4: Status & Polish | T12, T13, T14, T15 | 3h |
| Phase 5: Validation | T16, T17 | 1h |
| **Total** | **17 tasks** | **~15h** |

---

## Compatibility Strategy

- **No API changes** — bridge.py endpoints unchanged
- **No BesoGo core modifications** — overlays are a separate SVG layer; tree is DOM-relocated, not modified
- **No CLI impact** — `rm -rf gui/` still safe (AC13)
- **Additive only** — 2 new files (`board-overlay.js`, `player-indicator.js`), 9 modified files
- **No framework/build step introduced** — vanilla JS ES modules (C1)
