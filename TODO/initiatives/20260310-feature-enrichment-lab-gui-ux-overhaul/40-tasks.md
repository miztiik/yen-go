# Tasks — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Last Updated:** 2026-03-10

---

## Task Dependency Graph

```
Phase 1: Critical Fixes (independent)
  T1 (SSE board updates) ─────────────────┐
  T2 (engine status labels) ──────────────┤
                                           │
Phase 2: Layout Restructure               │
  T3 (3-column layout CSS) ───────────────┤
  T4 (right panel HTML) ──────────────────┼──► T5 (move tree to right panel)
                                           │         │
                                           │         ├──► T6 (move analysis table to right panel)
                                           │         ├──► T7 (move policy priors to right panel)
                                           │         └──► T8 (remove BesoGo panels: [])
                                           │
Phase 3: Board Overlays                    │
  T9 (board-overlay.js module) ────────────┤
  T10 (score overlays on board) ───────────┤
  T11 (PV hover preview) ─────────────────┤
                                           │
Phase 4: Status & Polish                   │
  T12 (player-to-move indicator) ──────────┤
  T13 (log panel resize) ─────────────────┤
  T14 (button tooltips) ──────────────────┤
  T15 (tree node score annotations) ──────┘
                                           │
Phase 5: Validation                        │
  T16 (manual smoke test) ────────────────┘
  T17 (docs update)
```

---

## Phase 1: Critical Fixes

### T1: Fix board updates during SSE enrichment events

**Files:** `gui/src/app.js`
**Issue:** C1
**Depends on:** —
**Parallel:** [P] with T2

`processSSEEvent()` only updates the board on the final `enriched_sgf` event (`status === 'complete'`). Intermediate `board_state` events log a message but don't call `loadSgf()` or update the board.

Changes:
1. In the SSE event handler, when `event.type === 'board_state'` and `event.data` contains position/SGF data, call the board update function.
2. When `event.type === 'analysis'` and `event.data` contains moves/scores, update the analysis table and trigger overlay rendering.
3. When `event.type === 'stage_update'`, update the pipeline bar (already works).

**Verification:** Load an SGF, click Enrich, observe board updating at intermediate stages (parse, validate, refute, etc.).

---

### T2: Fix engine status with human-readable labels

**Files:** `gui/src/sgf-input.js`, `gui/src/app.js`
**Issue:** C2
**Depends on:** —
**Parallel:** [P] with T1

Changes:
1. Create a status label mapping function:
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
2. Apply this mapping wherever the engine status is rendered in the UI.
3. Add a CSS class per status for visual differentiation (green dot for Ready, pulse for Running, red for Error).

**Verification:** Load page → shows "Idle". Click Analyze → shows "Running..." → shows "Ready" after completion.

---

## Phase 2: Layout Restructure

### T3: Restructure CSS to 3-column layout with fixed-size board

**Files:** `gui/css/styles.css`
**Issue:** M1
**Depends on:** —
**Parallel:** [P] with T4

Changes:
1. Replace current `.layout` flex with a 3-column CSS grid:
   ```css
   .layout {
     display: grid;
     grid-template-columns: 220px minmax(520px, 1fr) 320px;
     grid-template-rows: 1fr;
     gap: 0;
     height: calc(100vh - <header-height> - <log-height>);
   }
   ```
2. Set `#besogo-container` to fixed min-width (520px) so the board never shrinks below a usable size.
3. Add `.right-panel` styles: scrollable, stacked layout for tree + analysis + priors.
4. Ensure the board container has `aspect-ratio: 1` or height matching width for square rendering.

**Verification:** Resize browser from 1280px to 1920px+ — board stays >=520px, right panel stays ~320px.

---

### T4: Add right panel HTML structure

**Files:** `gui/index.html`
**Issue:** M2, m1
**Depends on:** —
**Parallel:** [P] with T3

Changes:
1. Add a `<aside class="right-panel">` element inside `.layout`, after `<main>`:
   ```html
   <aside class="right-panel">
     <div id="player-indicator"></div>
     <div id="solution-tree-panel"></div>
     <div id="policy-priors"></div>
     <div id="analysis-table"></div>
   </aside>
   ```
2. Remove `<div id="analysis-table">` from inside `<main>`.
3. The `#policy-priors` div is now in the right panel (currently it's dynamically created inside BesoGo panels).

**Verification:** Page loads with 3-column structure visible in DevTools.

---

### T5: Move solution tree to right panel

**Files:** `gui/src/board.js`, `gui/index.html`
**Issue:** M2
**Depends on:** T4

Changes:
1. In `initBoard()`, change BesoGo config from `panels: ['tree']` to `panels: []` — removes the tree panel from inside the board container.
2. After BesoGo creates, extract the tree rendering logic. Options:
   - (a) Let BesoGo still create a tree panel but move the DOM node into `#solution-tree-panel` after creation.
   - (b) Use `panels: ['tree']` but override the panel container via BesoGo config or post-init DOM manipulation.
3. Preferred approach: Use option (a) — create with `panels: ['tree']`, then `document.getElementById('solution-tree-panel').appendChild(treePanelElement)` to relocate it.

**Verification:** Tree renders inside the right panel. Board takes full width of its column.

---

### T6: Move analysis table to right panel

**Files:** `gui/src/analysis-table.js`, `gui/src/app.js`
**Issue:** m1
**Depends on:** T4
**Parallel:** [P] with T5, T7

Changes:
1. `initAnalysisTable()` already takes a container element. In `app.js`, change the container reference from the main-area div to `document.getElementById('analysis-table')` in the right panel.
2. Add CSS for the table inside the right panel: compact font size, scrollable overflow.

**Verification:** Analysis table renders in the right panel below the tree.

---

### T7: Move policy priors to right panel

**Files:** `gui/src/policy-panel.js`
**Issue:** M2 (related)
**Depends on:** T4
**Parallel:** [P] with T5, T6

Changes:
1. `initPolicyPanel()` looks up `#policy-priors` by ID. Since T4 places this div in the right panel, the panel should automatically render there.
2. Remove any code that dynamically creates or appends the policy panel into BesoGo's `.besogo-panels`.
3. Verify CSS styling works in the new container.

**Verification:** Policy priors bar chart renders in the right panel.

---

### T8: Remove BesoGo internal panels

**Files:** `gui/src/board.js`
**Depends on:** T5, T6, T7

Changes:
1. Once tree, policy, and analysis are all in the right panel, confirm `panels: []` in the BesoGo config.
2. Remove any leftover code that positions elements inside `.besogo-panels`.
3. Verify `.besogo-panels` div either doesn't exist or is empty/hidden.

**Verification:** Board takes 100% of its grid cell. No internal panel splitting.

---

## Phase 3: Board Overlays

### T9: Create board-overlay.js module

**Files:** `gui/src/board-overlay.js` (NEW)
**Depends on:** T3 (needs board positioning stable)
**Parallel:** [P] with T5-T8

Create a new module responsible for rendering SVG overlays on top of the BesoGo board.

Public API:
```javascript
export function initBoardOverlay(boardContainer) { ... }
export function showScoreOverlays(candidates, boardSize) { ... }
export function showPVPreview(pvMoves, boardSize, startColor) { ... }
export function clearOverlays() { ... }
export function clearPVPreview() { ... }
```

Implementation:
1. Create an absolutely positioned SVG element that covers the board exactly and sits on top via z-index.
2. Coordinate mapping: `(gtpCol, gtpRow)` → `(svgX, svgY)`. Must match BesoGo's grid layout.
   - BesoGo uses 1-indexed coords. Board margin and cell size can be extracted from the SVG viewBox or computed from container dimensions.
3. The overlay SVG must resize when the board resizes (ResizeObserver).
4. Subscribe to `analysisResult` state atom to auto-render overlays when analysis arrives.

**Verification:** Manually call `showScoreOverlays()` with test data — circles appear at correct intersections.

---

### T10: Render score overlays on board intersections

**Files:** `gui/src/board-overlay.js`, `gui/src/app.js`
**Issue:** M3
**Depends on:** T9

Changes:
1. When `analysisResult` updates, call `showScoreOverlays(result.moves, result.boardSize)`.
2. Each candidate rendered as:
   - A colored circle at the intersection (sized ~70% of cell)
   - Score value as text inside the circle (e.g., "-52.8")
   - Visit count as smaller text below (e.g., "1")
   - Color: green (#22c55e) for best move (rank 1), blue (#60a5fa) for alternatives, orange (#f97316) for hovered
3. Limit to top 5-8 candidates to avoid clutter.
4. When analysis clears, remove overlays.

**Verification:** Click Analyze → score circles appear on board at candidate intersections.

---

### T11: PV hover preview with numbered stones

**Files:** `gui/src/board-overlay.js`, `gui/src/analysis-table.js`
**Issue:** M4
**Depends on:** T9, T6

Changes:
1. In `analysis-table.js`, add `mouseenter`/`mouseleave` handlers on each `<tr>`:
   - `mouseenter`: Read the PV moves from the row data. Call `showPVPreview(pvMoves, boardSize, startColor)`.
   - `mouseleave`: Call `clearPVPreview()`.
2. In `board-overlay.js`, `showPVPreview()` renders:
   - Semi-transparent stones (opacity 0.6) at each PV intersection
   - Black/white alternating based on `startColor` and move index
   - A number label (1, 2, 3...) centered on each stone
   - The first stone (the candidate itself) also gets a highlighted border
3. Add a score overlay on the candidate's intersection (orange/salmon circle with score text).
4. Debounce mouseenter with ~50ms to prevent flicker on fast mouse movement.

**Verification:** Hover over analysis table row → numbered stones appear on board. Mouse leaves → stones disappear.

---

## Phase 4: Status & Polish

### T12: Add player-to-move indicator

**Files:** `gui/src/status-bar.js` (NEW or extend existing), `gui/src/app.js`
**Issue:** M5
**Depends on:** T4
**Parallel:** [P] with T9-T11

Changes:
1. Create or extend the status bar to show:
   - A filled circle (SVG) matching the current player color (black or white)
   - Text: "Black to play" or "White to play"
   - Aggregate stats: "Visits: 396 | Score: -0.0" (from analysis result)
2. Render inside `#player-indicator` in the right panel.
3. Subscribe to `boardState` and `analysisResult` state atoms.
4. Update when the board position changes (new puzzle loaded, navigation in tree).

**Verification:** Load a puzzle → "Black to play" shown with black circle. Navigate tree → updates.

---

### T13: Increase log panel height and make resizable

**Files:** `gui/css/styles.css`, `gui/src/log-panel.js`
**Issue:** M6
**Depends on:** T3
**Parallel:** [P] with T12, T14

Changes:
1. Increase `#log-panel` max-height from 200px to 400px.
2. Increase `.log-content` max-height from 160px to 350px.
3. Add `resize: vertical; overflow: auto;` to `.log-content` for user-resizable panel.
4. When collapsed, panel shows only the header bar (compact).

**Verification:** Log panel is visibly larger. Can drag to resize.

---

### T14: Add Enrich/Analyze button tooltips

**Files:** `gui/src/sgf-input.js`
**Issue:** M7
**Depends on:** —
**Parallel:** [P] with T12, T13

Changes:
1. Add `title` attributes to the Enrich and Analyze buttons:
   - Enrich: `"Run full 10-stage pipeline: parse → validate → refute → difficulty → teach → build SGF"`
   - Analyze: `"Quick KataGo analysis of current board position (~1-3s)"`
   - Cancel: `"Cancel the current enrichment pipeline run"`
2. Optionally add a small `(?)` info icon next to the header that shows a popover explanation.

**Verification:** Hover over Enrich button → tooltip appears with description.

---

### T15: Add score annotations to solution tree nodes

**Files:** `gui/src/board-overlay.js` or custom tree renderer
**Issue:** M3 (tree part)
**Depends on:** T5 (tree in right panel)

Changes:
1. After analysis, annotate tree nodes with score/prior data from the analysis result.
2. Options:
   - (a) Modify the tree node rendering to include a small score label next to each node circle.
   - (b) Add tooltip on tree node hover showing: move, score, visits, prior.
3. Start with (b) as it's lower risk and doesn't require modifying BesoGo's tree rendering.

**Verification:** Hover a tree node → tooltip shows score info.

---

## Phase 5: Validation

### T16: Manual smoke test (full workflow)

**Files:** —
**Depends on:** T1-T15

Test checklist:
1. [ ] Start bridge.py, open http://localhost:8999
2. [ ] Paste/upload an SGF puzzle
3. [ ] Verify 3-column layout: sidebar, board (large), right panel
4. [ ] Click Analyze → score overlays appear on board intersections
5. [ ] Hover analysis table row → numbered PV stones appear on board
6. [ ] Mouse leaves row → PV stones disappear
7. [ ] Player-to-move indicator shows correct color
8. [ ] Click Enrich → board updates at each stage
9. [ ] Engine status transitions: Idle → Enriching... → Ready
10. [ ] Solution tree renders in right panel with correct/wrong coloring
11. [ ] Log panel is larger, can be resized
12. [ ] Resize browser from 1280px to 1920px → board stays large, right panel adapts

---

### T17: Update documentation

**Files:** `gui/README.md`, `gui/docs/target-reference-architecture.md`
**Depends on:** T16

Changes:
1. Update `gui/README.md` with new feature list and layout description.
2. Check off completed items in `gui/docs/target-reference-architecture.md` checklist.
3. Update screenshots/diagrams if applicable.

---

## Effort Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1: Critical Fixes | T1, T2 | 2h |
| Phase 2: Layout Restructure | T3, T4, T5, T6, T7, T8 | 4h |
| Phase 3: Board Overlays | T9, T10, T11 | 5h |
| Phase 4: Status & Polish | T12, T13, T14, T15 | 3h |
| Phase 5: Validation | T16, T17 | 1h |
| **Total** | **17 tasks** | **~15h** |

---

## Parallel Execution Map

```
Time ──────────────────────────────────────────────────────────►

Phase 1:  [T1] ████  (SSE board updates)
          [T2] ████  (engine status labels)

Phase 2:  [T3] ████████  (CSS layout)
          [T4] ████      (HTML right panel)
                    [T5] ████  (tree → right panel)
                    [T6] ██    (analysis table → right panel)  [P with T5]
                    [T7] ██    (policy → right panel)          [P with T5, T6]
                        [T8] ██  (remove BesoGo panels)

Phase 3:  [T9] ████████  (overlay module)          [P with T5-T8]
                    [T10] ████  (score overlays)
                          [T11] ██████  (PV hover)

Phase 4:  [T12] ████  (player indicator)           [P with T9-T11]
          [T13] ██    (log panel)                   [P with T12]
          [T14] ██    (tooltips)                    [P with T12, T13]
                [T15] ████  (tree score annotations)

Phase 5:              [T16] ████  (smoke test)
                            [T17] ██  (docs)
```

---

## Compatibility Strategy

- **No API changes** — bridge.py endpoints remain unchanged
- **No BesoGo core modifications** — overlays are separate SVG layer
- **No CLI impact** — `rm -rf gui/` still safe
- **Additive only** — new files (board-overlay.js, status-bar.js), modified existing files
- **No framework/build step introduced** — vanilla JS ES modules
