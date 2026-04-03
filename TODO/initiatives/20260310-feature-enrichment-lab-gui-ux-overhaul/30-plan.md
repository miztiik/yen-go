# Plan — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Selected Option:** A — Overlay-on-BesoGo
**Last Updated:** 2026-03-10

---

## Implementation Strategy

Five phases, executed sequentially with internal parallelism:

### Phase 1: Critical Fixes (T1-T2)
Fix the two broken features first — SSE board updates and engine status labels. These are independent and can be done in parallel. This phase has immediate user impact with no layout risk.

### Phase 2: Layout Restructure (T3-T8)
Restructure from 2-column (sidebar + main) to 3-column (sidebar + board + right panel). This is the foundation for all overlay and panel features. T3 (CSS) and T4 (HTML) are parallel. T5-T7 (move panels to right column) depend on T4. T8 (cleanup) is last.

### Phase 3: Board Overlays (T9-T11)
Build the overlay module and implement score dots and PV hover. T9 (overlay module) can start in parallel with Phase 2 panel moves. T10 (scores) and T11 (PV hover) are sequential after T9.

### Phase 4: Status & Polish (T12-T15)
Player indicator, log panel resize, button tooltips, tree annotations. All mostly independent.

### Phase 5: Validation (T16-T17)
Manual smoke test across the full workflow. Documentation update.

---

## Architecture

### Overlay Layer Architecture

```
┌──────────────────────────────────┐
│ #besogo-container (position:rel) │
│ ┌──────────────────────────────┐ │
│ │ BesoGo SVG (board)           │ │  ← Existing, untouched
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ Overlay SVG (position:abs)   │ │  ← NEW: score dots, PV preview
│ │  - score circles             │ │
│ │  - PV numbered stones        │ │
│ │  - hover highlights          │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

The overlay SVG is absolutely positioned over the board, matching its dimensions via ResizeObserver. Pointer events are set to `none` so clicks pass through to BesoGo.

### Layout Grid

```
┌─────────┬──────────────────┬──────────────┐
│ sidebar  │  board (fixed)   │  right panel │
│ 220px    │  minmax(520,1fr) │  320px       │
│          │                  │              │
│ SGF I/O  │  BesoGo SVG      │ Player Info  │
│ Engine   │  + Overlay SVG   │ Mini Tree    │
│ Status   │                  │ Policy Bars  │
│          │                  │ Analysis Tbl │
├─────────┴──────────────────┴──────────────┤
│ Log Panel (collapsible, resizable)         │
└────────────────────────────────────────────┘
```

### Coordinate Mapping

BesoGo's SVG board has:
- A viewBox that encompasses the whole board + margins
- Each intersection at a predictable grid position

The overlay module reads the BesoGo container's dimensions and computes:
```javascript
const margin = containerWidth * 0.04;  // ~4% margin
const cellSize = (containerWidth - 2 * margin) / (boardSize - 1);
function gtpToPixel(col, row, boardSize) {
  const x = margin + col * cellSize;
  const y = margin + (boardSize - 1 - row) * cellSize;
  return { x, y };
}
```

Exact values will be calibrated against BesoGo's rendered grid during T9 implementation.

---

## API Changes

None. All bridge.py endpoints remain unchanged. The GUI consumes existing SSE events and analysis responses more completely.

---

## Rollback Strategy

All changes are in `gui/` directory. Rollback = `git checkout -- tools/puzzle-enrichment-lab/gui/`. No impact on CLI, backend, or any other subsystem.
