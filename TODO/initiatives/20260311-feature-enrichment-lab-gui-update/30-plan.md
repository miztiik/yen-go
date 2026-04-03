# Plan — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Selected Option:** A — Overlay-on-BesoGo with DOM Relocation
**Last Updated:** 2026-03-11

---

## Implementation Strategy

Five phases, executed sequentially with internal parallelism where possible:

| Phase | Name | Tasks | Purpose |
|-------|------|-------|---------|
| 1 | Critical Fixes | T1, T2 | Fix the two broken features — immediate user impact, no layout risk |
| 2 | Layout Restructure | T3-T8 | 3-column grid with board dominating, panels in right column |
| 3 | Board Overlays | T9-T11 | SVG overlay layer, score dots, PV hover preview |
| 4 | Status & Polish | T12-T15 | Player indicator, log panel resize, tooltips, tree annotations |
| 5 | Validation | T16-T17 | Manual smoke test, documentation update |

---

## Architecture

### Overlay Layer Architecture

```
+---------------------------------+
| #besogo-container (position:rel)|
| +-----------------------------+ |
| | BesoGo SVG (board)          | |  ← Existing, untouched
| +-----------------------------+ |
| +-----------------------------+ |
| | Overlay SVG (position:abs)  | |  ← NEW: score dots, PV preview
| |  - score circles            | |
| |  - PV numbered stones       | |
| |  - hover highlights         | |
| +-----------------------------+ |
+---------------------------------+
```

The overlay SVG is absolutely positioned over the board, matching its dimensions via `ResizeObserver`. Pointer events are set to `none` so all clicks pass through to BesoGo.

### Target Layout (3-Column CSS Grid)

```
+----------+----------------------+-----------------+
| sidebar  |  board (fixed)       |  right panel    |
| 220px    |  minmax(520px, 1fr)  |  320px          |
|          |                      |                 |
| SGF I/O  |  BesoGo SVG          | Player Info     |
| Engine   |  + Overlay SVG       | Solution Tree   |
| Status   |                      | Policy Priors   |
|          |                      | Analysis Table  |
+----------+----------------------+-----------------+
| Log Panel (300px+, collapsible, resizable)        |
+---------------------------------------------------+
```

### Coordinate Mapping (Overlay → Board)

BesoGo's SVG board uses a viewBox with margins and evenly spaced grid intersections. The overlay module computes pixel positions from GTP coordinates:

```javascript
// Calibrate against BesoGo's rendered grid
const boardSvg = container.querySelector('.besogo-svg-board');
const viewBox = boardSvg?.viewBox?.baseVal;
// Derive margin and cellSize from viewBox dimensions and boardSize
function gtpToPixel(col, row, boardSize, containerWidth) {
  const margin = containerWidth * 0.04;  // ~4% margin
  const cellSize = (containerWidth - 2 * margin) / (boardSize - 1);
  return {
    x: margin + col * cellSize,
    y: margin + (boardSize - 1 - row) * cellSize,
  };
}
```

Exact calibration values will be determined during T9 implementation by measuring against BesoGo's rendered grid.

### State Flow (Overlay Updates)

```
analysisResult (state atom)
  ├── → analysis-table.js (renders table, attaches hover handlers)
  ├── → policy-panel.js (renders bar chart)
  ├── → board-overlay.js (renders score circles on board)
  └── → player-indicator.js (renders player + aggregate stats)

mouseenter on table row → board-overlay.showPVPreview(pvMoves)
mouseleave on table row → board-overlay.clearPVPreview()
```

---

## API Changes

None. All bridge.py endpoints remain unchanged. The GUI consumes existing SSE events and analysis responses more completely.

---

## Documentation Plan

| Action | File | What | Why |
|--------|------|------|-----|
| Update | `gui/README.md` | Add new features, update layout description, update key files table | Accurate documentation |
| Update | `gui/docs/target-reference-architecture.md` | Check off completed items in GoProblems parity checklist | Track progress |

---

## Rollback Strategy

All changes are scoped to `tools/puzzle-enrichment-lab/gui/`. Rollback = `git checkout -- tools/puzzle-enrichment-lab/gui/`. No impact on CLI, backend, pipeline, or any other subsystem.

---

## Test Strategy

Manual testing only (no automated test framework for vanilla JS GUI):

1. Load GUI at `http://localhost:8999`
2. Paste/upload SGF puzzle
3. Verify 3-column layout at various viewport widths (1280px, 1440px, 1920px)
4. Click Analyze → verify score overlays appear on board
5. Hover analysis table rows → verify PV preview stones
6. Click Enrich → verify board updates during pipeline stages
7. Verify engine status transitions
8. Verify keyboard navigation still works
