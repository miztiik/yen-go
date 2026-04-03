# GhostBan Integration Guide

**Last Updated:** 2026-03-08

## Overview

The GUI uses [GhostBan](https://github.com/ghost-go/ghostban) v2.0.0-alpha.16 for Go board rendering. GhostBan handles stone placement, grid drawing, and coordinates. Analysis visualization (colored dots, PV stones, problem frame) is implemented as a custom canvas overlay on top of GhostBan.

## Why Custom Overlay

The npm-published GhostBan alpha.16 does **not** include the `setAnalysis()` API that goproblems.com uses (which runs a forked v3-alpha.155). Instead of depending on an unpublished fork, we render analysis as a second canvas layer.

## GhostBan API Usage

### Initialization

```tsx
const gb = new GhostBan({
  boardSize: 19,
  interactive: true,
  coordinate: true,
  theme: Theme.Flat,
  padding: 15,
  extend: 2,
});
gb.init(containerElement);
```

### Board Updates

```tsx
// boardMat uses Ki enum: Ki.Black=1, Ki.White=-1, Ki.Empty=0
gb.render(boardMat);
```

### Click Detection

GhostBan exposes cursor position after click events:
```tsx
container.addEventListener('click', () => {
  const [x, y] = gb.cursor;
  // x, y are board coordinates (0-indexed)
});
```

## Analysis Overlay

The overlay canvas sits on top of GhostBan with `pointer-events: none`:

### Colored Dots (Analysis)
- Score loss < 0.5 → green (best move)
- Score loss < 2.0 → blue (good)
- Score loss < 5.0 → yellow (acceptable)
- Score loss ≥ 5.0 → red (poor)

### PV Stones (Hover)
- Semi-transparent stones (black/white) with move numbers
- Triggered by hovering analysis table rows
- Written to `hoveredPV` signal

### Problem Frame
- `computeFrame()` finds stone bounding box + margin
- Edge snapping: if within 2 intersections of edge, snap to edge
- Outside-frame intersections dimmed with 50% opacity

## Ki Enum Values

| Value | Meaning |
|-------|---------|
| `Ki.Black` (1) | Black stone |
| `Ki.White` (-1) | White stone |
| `Ki.Empty` (0) | Empty intersection |

> **See also:**
> - [ARCHITECTURE.md](./ARCHITECTURE.md) — Full component diagram
> - [README.md](./README.md) — Setup and usage
