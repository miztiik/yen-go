# Charter — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Last Updated:** 2026-03-11
**Correction Level:** Level 4 (Large Scale — 4+ files, structure changes)
**Supersedes:** `20260310-feature-enrichment-lab-gui-ux-overhaul` (never executed)

---

## Summary

The Enrichment Lab GUI (a vanilla JS desktop tool for visual KataGo puzzle enrichment) is functionally complete but has critical bugs and significant UX gaps compared to the target reference (GoProblems.com Research(Beta) view). The board shrinks on wide screens, the solution tree steals board width, the board doesn't update during enrichment SSE events, the engine status is misleading, and key features like score overlays and PV hover preview are missing.

This initiative fixes the broken features, restructures the layout to give the board visual dominance, and adds analysis visualization features (score overlays, PV hover preview, player indicator) — bringing the GUI to feature parity with GoProblems.com.

## Vision

A research-grade puzzle analysis GUI where the Go board dominates the viewport at a fixed size, analysis results overlay directly on board intersections as colored score circles, hovering a candidate move previews the full principal variation as numbered semi-transparent stones, and the user always knows the engine state and whose turn it is.

## Goals

| ID  | Goal                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------- |
| G1  | Fix broken features: board SSE updates during enrichment, engine status labels                                    |
| G2  | Restructure layout: fixed-size board dominates viewport, solution tree in separate right panel                    |
| G3  | Add score/prior overlays on board intersections for candidate moves (top 5-8)                                     |
| G4  | Add score/prior overlays on solution tree nodes                                                                   |
| G5  | Add PV hover preview: numbered semi-transparent stones on board when hovering analysis table rows                 |
| G6  | Add player-to-move indicator with aggregate stats (visits, score)                                                 |
| G7  | Improve log panel sizing and engine action button clarity (Enrich vs Analyze tooltips)                            |

## Non-Goals

| ID  | Non-Goal                                                                                             |
| --- | ---------------------------------------------------------------------------------------------------- |
| NG1 | Replacing BesoGo with a different board library (we extend it via overlay, not replace it)            |
| NG2 | Dark theme implementation (current dark theme is fine)                                                |
| NG3 | Multiple board themes / stone theme selector                                                         |
| NG4 | WebGL/GPU-accelerated rendering (BesoGo SVG is sufficient)                                           |
| NG5 | Mobile responsive layout (this is a desktop developer tool, min 1280px)                              |
| NG6 | Refactoring bridge.py API endpoints (API stays the same, only GUI consumes differently)              |
| NG7 | Framework migration (no npm, no build step, no framework — vanilla JS ES modules only)               |

## Constraints

| ID  | Constraint                                                                               |
| --- | ---------------------------------------------------------------------------------------- |
| C1  | No npm, no build step, no framework — vanilla HTML/CSS/JS ES modules only                |
| C2  | Must NOT import from `backend/puzzle_manager/`                                           |
| C3  | BesoGo loaded as classic `<script>` tags (global namespace) — no modifications to BesoGo core files |
| C4  | bridge.py API endpoints remain unchanged (additive GUI-side changes only)                |
| C5  | All changes scoped to `tools/puzzle-enrichment-lab/gui/`                                 |
| C6  | Score overlays are SVG elements positioned over the BesoGo board container (separate layer) |
| C7  | `rm -rf gui/` must have zero impact on CLI — GUI is additive                             |

## Acceptance Criteria

| ID   | Criterion                                                                                                       |
| ---- | --------------------------------------------------------------------------------------------------------------- |
| AC1  | Board maintains a fixed minimum size (~520px) and dominates viewport on 1920px+ screens                         |
| AC2  | Solution tree renders in a separate right panel, not inside `#besogo-container`                                 |
| AC3  | After analysis, candidate moves show score + visit count overlaid on board intersections (top 5-8)              |
| AC4  | Solution tree nodes display score/prior annotations (tooltip on hover)                                          |
| AC5  | Hovering an analysis table row shows numbered semi-transparent stones on the board for the PV sequence          |
| AC6  | Hovered candidate's intersection shows a colored score overlay (orange/salmon)                                  |
| AC7  | Player-to-move indicator visible: stone icon + "Black/White to play" + aggregate visits/score                   |
| AC8  | Engine status shows human-readable labels: "Idle", "Starting...", "Ready", "Running...", "Error"                |
| AC9  | Board position updates in real-time during SSE enrichment events (not just on final event)                      |
| AC10 | Log panel default height increased to 300px+ and is resizable via CSS `resize: vertical`                        |
| AC11 | Enrich/Analyze buttons have descriptive tooltips explaining what each does                                      |
| AC12 | Analysis table moves to the right panel (below tree), not below the board                                       |
| AC13 | All changes are additive — `rm -rf gui/` still has zero impact on CLI                                           |

## Reference Documents

| Document | Path |
|----------|------|
| Target reference architecture (GoProblems comparison) | `tools/puzzle-enrichment-lab/gui/docs/target-reference-architecture.md` |
| UX issues audit (full issue list with root causes) | `tools/puzzle-enrichment-lab/gui/docs/ux-issues-audit.md` |
| GoProblems PV hover reference screenshot | `tools/puzzle-enrichment-lab/gui/docs/ui_references/pv_hove_stone_number_scores.png` |
| Existing GUI README | `tools/puzzle-enrichment-lab/gui/README.md` |
| Prior UX overhaul initiative (never executed) | `TODO/initiatives/20260310-feature-enrichment-lab-gui-ux-overhaul/` |

## Key Design Decisions

| Decision | Summary |
|----------|---------|
| D1 | Score overlays are SVG elements absolutely positioned over the BesoGo board container (not modifying BesoGo internals) |
| D2 | PV hover preview creates temporary SVG stone elements with opacity + number labels, removed on mouseleave |
| D3 | Solution tree extracted from BesoGo — create with `panels: ['tree']` then DOM-relocate into right panel |
| D4 | Layout restructured to 3-column CSS grid: sidebar (220px) + board (minmax 520px) + right panel (320px) |
| D5 | Engine status mapped from internal states to UX-friendly labels via a display label function |
| D6 | Board SSE updates wired to intermediate `board_state` events, not just final `enriched_sgf` |
| D7 | Overlay SVG matches board dimensions via ResizeObserver, pointer-events: none for click passthrough |
