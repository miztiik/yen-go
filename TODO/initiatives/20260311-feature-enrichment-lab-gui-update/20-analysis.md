# Analysis — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Last Updated:** 2026-03-11

---

## Current State Assessment

The GUI was built in initiative `2026-03-07-feature-enrichment-lab-gui` and refined in `20260309-1000-feature-enrichment-lab-gui-v4`. It is a vanilla HTML/CSS/JS application served by `bridge.py` (FastAPI on port 8999) alongside KataGo analysis API endpoints. It successfully delivers:

- BesoGo SVG board with kaya-wood theme, Go rules, captures, ko
- Solution tree with correct (green) / wrong (red) branch coloring
- 10-stage pipeline progress bar with animated pill states
- Streaming SSE log panel
- SGF paste/upload/download
- Enrich (full pipeline) and Analyze (quick KataGo query) workflows
- Policy priors bar chart
- Keyboard navigation (arrow keys, Home/End)

### Architecture Summary

| Component | Technology | Notes |
|-----------|-----------|-------|
| Board rendering | BesoGo (vanilla JS, SVG, global namespace) | Loaded via classic `<script>` tags |
| App modules | ES modules (`gui/src/*.js`) | Simple observable state atoms, no framework |
| Styling | Single `gui/css/styles.css` | Dark theme, CSS custom properties |
| Server | `bridge.py` (FastAPI) | Serves static files + API on port 8999 |
| Communication | REST + SSE | `/api/analyze` (POST), `/api/enrich` (SSE), `/api/health` (GET) |

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

### File Inventory (10 source files)

| File | Lines | Purpose |
|------|-------|---------|
| `gui/index.html` | 53 | Layout structure, script loading |
| `gui/css/styles.css` | 462 | All styling (dark theme, layout, components) |
| `gui/src/app.js` | 219 | Main orchestrator, SSE event processing, keyboard shortcuts |
| `gui/src/board.js` | 106 | BesoGo wrapper — init, load SGF, get board state |
| `gui/src/state.js` | 44 | Observable state atoms (boardState, analysisResult, etc.) |
| `gui/src/bridge-client.js` | 113 | HTTP + SSE client for bridge.py |
| `gui/src/analysis-table.js` | 56 | Candidate moves table (Order, Move, Prior, Score, Visits, PV) |
| `gui/src/sgf-input.js` | 103 | SGF I/O + Enrich/Analyze/Cancel buttons |
| `gui/src/log-panel.js` | 56 | Collapsible streaming log viewer |
| `gui/src/pipeline-bar.js` | 116 | 10-stage progress bar with run_id/trace_id |
| `gui/src/policy-panel.js` | 67 | Policy prior bar chart |

---

## Issue Inventory

Full details in `gui/docs/ux-issues-audit.md`. Summary below:

### Critical (Broken)

| ID | Issue | Root Cause | Impact |
|----|-------|-----------|--------|
| C1 | Board doesn't update during SSE enrichment events | `processSSEEvent()` in `app.js` only calls `sgfText.set(data.sgf)` on final `enriched_sgf` event with `status === 'complete'`. Intermediate `board_state` events log a message but don't update the board. | User cannot visually follow enrichment in real-time. Defeats "visual observer" purpose. |
| C2 | Engine status shows "not_started" — misleading | `/api/health` returns `"not_started"` when engine hasn't been lazily initialized. GUI displays this literally. | User thinks something is broken. Reads as an error, not "waiting for first use." |

### Major (UX Gaps vs GoProblems Reference)

| ID | Issue | GoProblems Has | Root Cause |
|----|-------|----------------|-----------|
| M1 | Board shrinks dramatically on wide screens | Fixed-size board dominating viewport | CSS `flex: 1` on `.main-area`, no `min-width` on `#besogo-container`. BesoGo sizes to container. |
| M2 | Solution tree steals board width | Tree in separate right panel | `besogo.create()` with `panels: ['tree']` creates tree inside board container. `orient: 'landscape'` puts panels right of board. |
| M3 | No score/prior overlays on board or tree | Colored circles with score + visits on intersections and tree nodes | No overlay layer exists. Analysis results only shown in table and policy bar chart. |
| M4 | No PV hover preview | Numbered semi-transparent stones on board when hovering candidate row | No mouse event handlers on analysis table rows. |
| M5 | No player-to-move indicator | Stone icon + "Current Player: B/W" + aggregate stats | `#status-bar` exists but is empty. `boardState.currentPlayer` not rendered. |
| M6 | Log panel too small (200px max) | N/A | `max-height: 200px` on `#log-panel`, `max-height: 160px` on `.log-content`. |
| M7 | Enrich vs Analyze — no explanation | N/A | Buttons have no `title` attribute or description text. |

### Minor (Polish)

| ID | Issue |
|----|-------|
| m1 | Analysis table below board instead of right panel |
| m2 | Flat stone rendering (no gradients) — cosmetic |
| m3 | SGF textarea always visible in sidebar |
| m4 | Pipeline bar pill labels verbose |

---

## Root Cause Analysis

### Board Shrinking (M1 + M2) — Compound Layout Problem

The layout uses flexbox with `.main-area { flex: 1 }` and `#besogo-container { flex: 1 1 auto; min-height: 400px; max-height: calc(100vh - 200px) }`. There is no `min-width` constraint.

BesoGo's `create()` with `panels: ['tree']` and `orient: 'landscape'` creates a `.besogo-panels` div as a sibling inside the container, splitting horizontal space. The policy priors panel is also appended inside `.besogo-panels` (see `board.js:94-104`).

**Result:** `board width = container width - tree panel - policy panel`. On wide screens, the board can be tiny while empty space dominates.

**Fix approach:** 3-column CSS grid layout. Set `panels: []` or relocate the tree panel DOM node into a right panel. Set `min-width: 520px` on the board column.

### SSE Board Updates (C1) — Incomplete Event Handling

In `app.js:107-109`, the `board_state` event handler only calls `advanceStage('build_query')` and `appendLog()`. It does NOT update the board position. The board only updates on the final `enriched_sgf` event (`app.js:123-126`).

**Fix approach:** On `board_state` events containing position data, update the BesoGo board to show the current position being analyzed.

### Engine Status (C2) — Raw Internal State Exposed

`/api/health` returns raw states: `"not_started"`, `"starting"`, `"ready"`, `"error"`. The GUI displays these literally in `app.js:50-53`.

**Fix approach:** Map to human-readable labels: `not_started` → "Idle", `starting` → "Starting...", `ready` → "Ready", `running` → "Running...", `error` → "Error".

---

## Affected Files

| File | Change Type | Scope |
|------|-------------|-------|
| `gui/index.html` | Modified | Add right panel `<aside>` element, relocate `#analysis-table` |
| `gui/css/styles.css` | Major modification | 3-column grid layout, board min-width, right panel styles, overlay styles, log panel sizing |
| `gui/src/app.js` | Modified | SSE board_state event handling, engine status mapping, overlay wiring |
| `gui/src/board.js` | Modified | Change BesoGo config (`panels: []` or relocate tree), remove policy panel injection |
| `gui/src/analysis-table.js` | Modified | Add PV hover mouseenter/mouseleave handlers |
| `gui/src/policy-panel.js` | Minor modification | CSS adjustments for right panel container |
| `gui/src/sgf-input.js` | Modified | Add button tooltips (`title` attributes) |
| `gui/src/log-panel.js` | Modified | Increase default height, add resize capability |
| `gui/src/state.js` | Minor modification | Possibly add overlay-related state atoms |
| **NEW:** `gui/src/board-overlay.js` | New file | SVG overlay layer: score circles, PV preview stones, coordinate mapping |
| **NEW:** `gui/src/player-indicator.js` | New file | Player-to-move display component |

**Total: 11 files** (9 modified, 2 new)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| BesoGo SVG DOM structure changes break overlay positioning | Medium | High | Overlays use absolute positioning relative to container, not BesoGo internals. ResizeObserver keeps sync. |
| Removing BesoGo `panels: ['tree']` breaks tree display | Low | High | Alternative: create with `panels: ['tree']` then DOM-relocate the tree node into right panel post-init. |
| Board overlay coordinate mapping off-by-one | Medium | Medium | Test with known positions. BesoGo 1-indexed coords documented. Calibrate against rendered grid. |
| PV hover events fire too rapidly, causing flicker | Low | Low | Debounce mouseenter/mouseleave with 50ms delay. |
| Layout changes break on unusual screen sizes | Low | Low | Desktop-only tool with 1280px minimum. Test at 1920px, 1440px, 1280px. |

---

## Dependency on Other Initiatives

| Initiative | Relationship |
|-----------|-------------|
| `20260311-1600-feature-enrichment-lab-consolidation` | Independent — that initiative is backend/pipeline focused (Benson gate, ko detection, docs). No GUI overlap. |
| `20260310-feature-enrichment-lab-gui-ux-overhaul` | **Superseded** — this initiative replaces it with updated analysis and fresh task breakdown. |
