# Charter — Enrichment Lab GUI v4 (Fresh Build)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-09

---

## Vision

A lightweight, Python-backend-driven GUI for the KataGo puzzle enrichment lab (`tools/puzzle-enrichment-lab/`). Built fresh in `tools/puzzle-enrichment-lab/gui/`. The frontend ONLY receives and displays what the Python pipeline sends — all analysis, solving, validation, and enrichment runs server-side via KataGo. The GUI visualizes the enrichment pipeline in real-time: board position updates, analysis dots (policy priors, winrate, visits), solution tree construction with correct/wrong branch coloring, stage progression indicators, and streaming engine logs. Modeled after the goproblems.com Research(Beta) interface.

This is attempt #4. Prior attempts failed due to scope creep (hybrid browser+bridge analysis), coordinate bugs (Preact Signals vs GhostBan matrix transposition), and 200MB TF.js dependency bloat. This time: **Python does all work, frontend just displays.**

## Goals

| ID | Goal |
|----|------|
| G1 | Visualize the enrichment pipeline progression with stage indicators (9+ stages) |
| G2 | Show the Go board updating in real-time as enrichment proceeds (stones placed, tsumego frame visible) |
| G3 | Display KataGo analysis dots (policy priors, winrate, score, visits) like goproblems.com Research(Beta) — all data from Python, NOT browser-side analysis |
| G4 | Show an interactive solution/refutation tree with correct (green) / wrong (red) branch coloring, annotated with policy priors per node |
| G5 | Support SGF input via paste/upload and output via download |
| G6 | Stream engine logs in a collapsible panel for debugging |
| G7 | Show ac_level indicator (UNTOUCHED/ENRICHED/AI_SOLVED/VERIFIED) to surface KataGo solving boundaries |
| G8 | Trigger `/api/analyze` after `board_state` SSE event to show analysis dots during enrichment |
| G9 | Click a node in the solution tree → board updates to show that position with its analysis data |
| G10 | Interactive analysis — click board to place/remove stones, then [Analyze] to query KataGo on that specific position (separate from enrichment) |

## Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | Browser-side AI / KataGo inference (no TF.js, no WebGL models, no WASM) |
| NG2 | Reviving or modifying gui_deprecated — that code stays as-is |
| NG3 | Hybrid browser+bridge engine architecture |
| NG4 | Production/public deployment — this is a developer tool |
| NG5 | Batch processing UI — single-puzzle observation |
| NG6 | Interactive Go play against KataGo |
| NG7 | Real-time tree-building animation (YAGNI for now) |
| NG8 | Integration with `backend/puzzle_manager/` |

## Constraints

| ID | Constraint |
|----|-----------|
| C1 | Must NOT import from `backend/puzzle_manager/` |
| C2 | Must live inside `tools/puzzle-enrichment-lab/gui/` |
| C3 | gui_deprecated must NOT be modified — user will clean up separately |
| C4 | No changes to existing CLI arguments (additive only) |
| C5 | All analysis data comes from Python via bridge.py API — zero browser-side compute |
| C6 | No TF.js or browser model loading dependencies |
| C7 | Must NOT modify bridge.py API contracts (only additive changes if needed) |
| C8 | Single-user developer tool — no concurrent session handling |

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC1 | User can start the GUI via `python bridge.py` and open `http://localhost:8999` to see the enrichment lab interface |
| AC2 | User can paste/upload SGF and see the position rendered on the board |
| AC3 | User can click "Enrich" and see pipeline stages progressing with status indicators |
| AC4 | Board updates at key pipeline moments (parse, post-frame, post-enrichment) showing stones being placed |
| AC5 | Analysis dots (goproblems.com style) show policy priors, score, visits for candidate moves — data from Python /api/analyze |
| AC6 | Solution/refutation tree is interactive: click a node → board shows that position. Correct=green, wrong=red branches. |
| AC7 | Analysis table shows Order, Move, Prior, Score, Visits, PV (like goproblems.com screenshot) |
| AC8 | Engine logs stream in a collapsible panel |
| AC9 | ac_level indicator shows whether KataGo solved from scratch or validated existing tree |
| AC10 | Running CLI enrichment (`python cli.py enrich --sgf puzzle.sgf --output result.json`) works exactly as before |

## Board Library Candidates

Research identified three candidates for the board + tree rendering:

1. **GhostBan** (npm `ghostban@2.0.0-alpha.16`) — Canvas-based Go board. Used by goproblems.com in production. Already in gui_deprecated. Needs overlay canvas for analysis dots (goproblems.com's `setAnalysis()` is in their private fork, not in npm).

2. **BesoGo** (`tools/sgf-viewer-besogo/`) — Pure SVG Go board + tree panel. Already in the project. Has built-in solution tree (treePanel.js) with SVG node icons and navigation. Tree panel can potentially be customized for correct/wrong coloring. Board display uses SVG (not canvas).

3. **Custom SVG** — Full control but highest effort. YAGNI unless existing libraries can't meet requirements.

The options phase will evaluate these candidates.

## Code Reuse Policy

Developers MAY copy individual modules from `gui_deprecated/` into `gui/`. `gui_deprecated/` is NOT modified or removed as part of this initiative. Useful code (bridge client patterns, SSE streaming logic, analysis table layouts, SVG tree rendering) can be referenced and adapted, but the new GUI is an independent project with its own architecture.

> **See also:**
>
> - [Clarifications](./10-clarifications.md) — User Q&A and deprecation history
> - [Research](../20260309-research-enrichment-lab-gui-v4-feasibility/15-research.md) — Feasibility research
> - [gui_deprecated Architecture](../../../tools/puzzle-enrichment-lab/gui_deprecated/ARCHITECTURE.md) — Prior attempt reference
> - [BesoGo Tree Swap plan](../../../TODO/besogo-solution-tree-swap.md) — Prior BesoGo integration analysis
