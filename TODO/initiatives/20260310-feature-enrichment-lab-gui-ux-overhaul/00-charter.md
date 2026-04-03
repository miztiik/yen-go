# Charter — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Last Updated:** 2026-03-10
**Correction Level:** Level 4 (Large Scale — 4+ files, structure changes)

---

## Summary

The Enrichment Lab GUI, while functional, has significant UX gaps compared to the target reference (GoProblems.com Research(Beta) view). The board shrinks on wide screens, analysis results are disconnected from the visual board, the engine status is misleading, and key features like score overlays and PV hover preview are missing. This initiative brings the GUI to feature parity with the target reference through a phased layout restructure and feature buildout.

## Vision

A research-grade puzzle analysis GUI where the Go board dominates the viewport, analysis results overlay directly on the board intersections, hovering a candidate move previews the full principal variation as numbered stones, and the user always knows the engine state and whose turn it is.

## Goals

| ID  | Goal                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------- |
| G1  | Fix broken features: board SSE updates during enrichment, engine status labels                                    |
| G2  | Restructure layout: fixed-size board dominates viewport, solution tree in separate right panel                    |
| G3  | Add score/prior overlays on board intersections for candidate moves                                               |
| G4  | Add score/prior overlays on solution tree nodes                                                                   |
| G5  | Add PV hover preview: numbered semi-transparent stones on board when hovering analysis table rows                 |
| G6  | Add player-to-move indicator with aggregate stats                                                                 |
| G7  | Improve log panel sizing and engine action button clarity (Enrich vs Analyze tooltips)                            |

## Non-Goals

| ID  | Non-Goal                                                                                             |
| --- | ---------------------------------------------------------------------------------------------------- |
| NG1 | Replacing BesoGo with a different board library (we extend it, not replace it)                       |
| NG2 | Dark theme implementation (current light theme remains)                                              |
| NG3 | Multiple board themes / stone theme selector (GoProblems has this, we don't need it yet)             |
| NG4 | WebGL/GPU-accelerated rendering (BesoGo SVG is sufficient)                                           |
| NG5 | Mobile responsive layout (this is a desktop developer tool)                                          |
| NG6 | Refactoring bridge.py API endpoints (API stays the same, only GUI consumes differently)              |

## Constraints

| ID  | Constraint                                                                               |
| --- | ---------------------------------------------------------------------------------------- |
| C1  | No npm, no build step, no framework — vanilla HTML/CSS/JS ES modules only                |
| C2  | Must NOT import from `backend/puzzle_manager/`                                           |
| C3  | BesoGo loaded as classic `<script>` tags (global namespace) — no modifications to core   |
| C4  | bridge.py API endpoints remain unchanged (additive changes only)                         |
| C5  | All changes scoped to `tools/puzzle-enrichment-lab/gui/`                                 |
| C6  | Score overlays are SVG elements positioned over the BesoGo board (not modifying BesoGo)  |

## Acceptance Criteria

| ID   | Criterion                                                                                                       |
| ---- | --------------------------------------------------------------------------------------------------------------- |
| AC1  | Board maintains a fixed minimum size (500-600px) and dominates viewport on 1920px+ screens                      |
| AC2  | Solution tree renders in a separate right panel, not inside `#besogo-container`                                 |
| AC3  | After analysis, candidate moves show score + visit count overlaid on board intersections                        |
| AC4  | Solution tree nodes display score/prior annotations                                                             |
| AC5  | Hovering an analysis table row shows numbered semi-transparent stones on the board for the PV sequence          |
| AC6  | Hovered candidate's intersection shows a colored score overlay (orange/salmon)                                  |
| AC7  | Player-to-move indicator visible: stone icon + "Black/White to play" + aggregate visits/score                   |
| AC8  | Engine status shows human-readable labels: "Idle", "Starting...", "Ready", "Running...", "Error"                |
| AC9  | Board position updates in real-time during SSE enrichment events (not just on final event)                      |
| AC10 | Log panel default height increased to 300px+ and is resizable                                                   |
| AC11 | Enrich/Analyze buttons have descriptive tooltips explaining what each does                                      |
| AC12 | Analysis table moves to the right panel (below tree), not below the board                                       |
| AC13 | All changes are additive — `rm -rf gui/` still has zero impact on CLI                                           |

## Reference Documents

| Document | Path |
|----------|------|
| Target reference architecture (GoProblems comparison) | `tools/puzzle-enrichment-lab/gui/docs/target-reference-architecture.md` |
| UX issues audit (full issue list with root causes) | `tools/puzzle-enrichment-lab/gui/docs/ux-issues-audit.md` |
| Existing GUI README | `tools/puzzle-enrichment-lab/gui/README.md` |
| Parent initiative (original GUI build) | `TODO/initiatives/2026-03-07-feature-enrichment-lab-gui/` |

## Key Design Decisions

| Decision | Summary |
|----------|---------|
| D1 | Score overlays are SVG elements absolutely positioned over the BesoGo board container (not modifying BesoGo internals) |
| D2 | PV hover preview creates temporary SVG stone elements with opacity + number labels, removed on mouseleave |
| D3 | Solution tree extracted from BesoGo panels — rendered using `panels: []` and a custom tree component in the right panel |
| D4 | Layout restructured to 3-column: sidebar (narrow) + board (fixed-size) + right panel (flex) |
| D5 | Engine status mapped from internal states to UX-friendly labels via a display label function |
| D6 | Board SSE updates wired to intermediate `board_state` events, not just final `enriched_sgf` |
