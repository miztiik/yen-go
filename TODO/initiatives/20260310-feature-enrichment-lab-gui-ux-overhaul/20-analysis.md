# Analysis — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Last Updated:** 2026-03-10

---

## Current State Assessment

The GUI was built in initiative `2026-03-07-feature-enrichment-lab-gui` as a "lightweight visual pipeline observer." It successfully delivers: BesoGo SVG board, solution tree with correct/wrong coloring, streaming logs, SGF I/O, and the Enrich/Analyze workflow via bridge.py. However, the UX was deprioritized in favor of functional completeness.

### Current Layout

```
+---------+-------------------------------------------+
| SIDEBAR | BOARD (besogo)        | TREE  | PRIORS   |
| SGF     |                       | panel | panel    |
| input   |                       |       |          |
| Upload  +-----------------------+-------+----------+
| Enrich  | Status bar                                |
| Analyze | Analysis table                            |
| Cancel  +-------------------------------------------+
| Engine  | LOG PANEL (collapsed by default)           |
+---------+-------------------------------------------+
```

**Board library:** BesoGo (vanilla JS, SVG, loaded as classic `<script>` tags into global namespace)
**Modules:** All `gui/src/*.js` are ES modules. No npm, no build step.
**Server:** bridge.py (FastAPI on port 8999) serves static files + API on single origin.

---

## Issue Inventory

Full details in `gui/docs/ux-issues-audit.md`. Summary below:

### Critical (Broken)

| ID | Issue | Impact |
|----|-------|--------|
| C1 | Board doesn't update during SSE enrichment events | Defeats "visual observer" purpose |
| C2 | Engine status shows "not_started" — misleading | Users think something is broken |

### Major (UX Gaps vs GoProblems Reference)

| ID | Issue | GoProblems Has |
|----|-------|----------------|
| M1 | Board shrinks on wide screens (tiny board, huge empty space) | Fixed-size board dominating viewport |
| M2 | Solution tree steals board width (inside same flex container) | Tree in separate right panel |
| M3 | No score/prior overlays on board or solution tree | Colored circles with score + visits on intersections and tree nodes |
| M4 | No PV hover preview (move sequences as text only) | Numbered semi-transparent stones on board when hovering candidate row |
| M5 | No player-to-move indicator | Stone icon + "Current Player: B" + aggregate stats |
| M6 | Log panel too small (200px max) | N/A but needs ~300px and resizable |
| M7 | Enrich vs Analyze — no explanation | Tooltips explain each action |

### Minor (Polish)

| ID | Issue |
|----|-------|
| m1 | Analysis table below board instead of right panel |
| m2 | Flat stone rendering (no gradients) |
| m3 | SGF textarea always visible |

---

## Root Cause Analysis

### Board Shrinking (M1 + M2)

The root cause is a compound layout problem:

1. **CSS**: `.main-area` uses `flex: 1` with no `min-width` on `#besogo-container`. Board can shrink to any size.
2. **BesoGo**: `besogo.create()` with `panels: ['tree']` creates a `.besogo-panels` div as a sibling inside the container. With `orient: 'landscape'`, panels sit to the right of the board, eating horizontal space.
3. **Policy panel**: Appended inside `.besogo-panels` column, further reducing board width.
4. **Result**: Board width = container width - tree panel - policy panel. On wide screens, this can mean a 300px board in a 1920px viewport.

**Fix approach**: Set `panels: []` in BesoGo config (removes internal panels). Build a custom right panel in the HTML layout outside `#besogo-container`. Move tree, policy priors, and analysis table into this right panel. Set `min-width: 520px` on the board container.

### SSE Board Updates (C1)

`processSSEEvent()` in `app.js` only calls `sgfText.set(data.sgf)` on the final `enriched_sgf` event when `status === 'complete'`. Intermediate `board_state` events are logged but don't update the board.

**Fix approach**: On `board_state` events, extract position data and update the board. On `analysis` events, update overlays.

### Engine Status (C2)

`/api/health` returns raw internal state: `"not_started"`, `"starting"`, `"ready"`, `"error"`. The GUI displays this literally.

**Fix approach**: Map internal states to UX-friendly labels:
- `not_started` → "Idle" (with neutral icon)
- `starting` → "Starting..." (with spinner)
- `ready` → "Ready" (with green dot)
- `running` → "Running..." (with pulse animation)
- `error` → "Error" (with red icon)

---

## Affected Files

| File | Changes |
|------|---------|
| `gui/index.html` | Layout restructure: add right panel column |
| `gui/css/styles.css` | Major: 3-column layout, board min-width, right panel styles, overlay styles |
| `gui/src/app.js` | SSE event handling for board updates, engine status mapping |
| `gui/src/analysis-table.js` | PV hover handlers, move to right panel, table restructure |
| `gui/src/board.js` | Score overlay rendering (SVG), PV preview rendering |
| `gui/src/policy-panel.js` | Move to right panel container |
| `gui/src/sgf-input.js` | Button tooltips, engine status display labels |
| `gui/src/log-panel.js` | Height increase, resize handle |
| `gui/src/state.js` | Possibly new state atoms for overlay data |
| **New:** `gui/src/board-overlay.js` | Score overlay + PV preview SVG rendering module |
| **New:** `gui/src/status-bar.js` | Player-to-move indicator + aggregate stats |

**Total: 10-11 files** (8 modified, 2-3 new modules)

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| BesoGo SVG DOM structure changes break overlay positioning | Medium | Overlays use absolute positioning relative to container, not BesoGo internals |
| Removing BesoGo `panels: ['tree']` breaks tree functionality | Low | Tree data comes from the editor state, not the panel. Custom tree can read same state. |
| Board overlay coordinate mapping off-by-one | Medium | Test with known positions. BesoGo 1-indexed coords well documented in board.js |
| PV hover events fire too rapidly, causing flicker | Low | Debounce mouseenter/mouseleave with 50ms delay |
| Layout changes break on unusual screen sizes | Low | Desktop-only tool. Test at 1920px, 1440px, 1280px. |
