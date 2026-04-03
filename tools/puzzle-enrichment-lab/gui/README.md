# Enrichment Lab GUI

Lightweight visual observer for the KataGo puzzle enrichment pipeline. Python does all analysis — the GUI only receives and displays results.

## Quick Start

```bash
cd tools/puzzle-enrichment-lab
python bridge.py --katago katago/katago.exe --katago-config katago/tsumego_analysis.cfg
```

Open `http://localhost:8999` in your browser.

## Features

- **Pipeline Progress** — Vertical stage stepper (gray → blue-pulse → green/red) with per-stage timing, run_id + trace_id + ac_level
- **Go Board** — BesoGo SVG board with kaya-wood theme, Go rules (captures, ko), and stone placement; fixed min-width (520px) dominating the viewport
- **Score Overlays** — Top 5-8 candidate moves shown as colored circles on board intersections with score value and visit count
- **PV Hover Preview** — Hover analysis table rows to see numbered semi-transparent stones on the board showing the principal variation
- **Solution Tree** — BesoGo SVG tree in right panel with correct (green) / wrong (red) branch coloring and score tooltips
- **Player Indicator** — Shows player-to-move (black/white stone icon) with aggregate visits and score from analysis
- **Policy Priors** — Bar chart of KataGo move priors in the right panel
- **Interactive Analysis** — Click board to place/remove stones, then [Analyze] for KataGo analysis
- **Config Panel** — 45-parameter accordion panel (7 groups) with real-time overrides, difficulty weight normalization, config diff display, and localStorage persistence
- **Visits Dropdown** — Quick KataGo analysis visit selector (200/500/1000/2000/5000) in the sidebar
- **SGF I/O** — Paste, upload, or download SGF files
- **Log Panel** — Streaming engine logs (300px+, resizable) with auto-scroll
- **Real-time SSE Updates** — Board updates at each enrichment pipeline stage, not just on completion
- **Engine Status** — Human-readable labels (Idle, Ready, Running..., Error) with colored dot indicators

## Two Workflows

| Workflow | Trigger | API | Purpose |
|----------|---------|-----|---------|
| **Enrich** | [Enrich] button | `POST /api/enrich` (SSE) | Full 10-stage pipeline: parse → validate → refute → difficulty → teach → build SGF |
| **Analyze** | [Analyze] button | `POST /api/analyze` | Single KataGo query on current board position (~1-3s) |

## Architecture

```
bridge.py (FastAPI :8999) — serves API + GUI static files on single origin
 ├── /api/analyze    → Interactive KataGo analysis
 ├── /api/enrich     → Full pipeline (SSE); accepts config_overrides
 ├── /api/config     → Returns default enrichment config (JSON)
 ├── /api/cancel     → Cancel enrichment
 ├── /api/health     → Engine status
 └── /*              → gui/ static files
```

All `gui/src/*.js` files use ES module `import`/`export`. BesoGo is loaded as classic `<script>` tags (global namespace).

## Key Files

| File | Purpose |
|------|---------|
| `src/app.js` | Main orchestrator, SSE event processing, keyboard shortcuts |
| `src/board.js` | BesoGo wrapper — initBoard, loadSgf, getEditor, getCurrentBoard, post-create hooks |
| `src/board-overlay.js` | SVG overlay for score dots, PV hover preview, tree annotations |
| `src/player-indicator.js` | Player-to-move indicator with aggregate analysis stats |
| `src/bridge-client.js` | HTTP + SSE client for bridge.py; `getConfig()`, `streamEnrichment` with config_overrides |
| `src/stage-stepper.js` | Vertical stage stepper with per-stage timing (replaces pipeline-bar.js) |
| `src/config-panel.js` | 45-param accordion config panel: weight normalization, config diff, localStorage persistence |
| `src/analysis-table.js` | Candidate moves table with PV hover handlers |
| `src/sgf-input.js` | SGF paste/upload/download + Enrich/Analyze/Cancel buttons + visits dropdown |
| `src/policy-panel.js` | Policy prior bar chart |
| `src/log-panel.js` | Collapsible streaming log viewer |
| `src/state.js` | Observable state atoms: `configDefaults`, `configOverrides`, `analyzeVisits`, etc. |
| `lib/besogo/treePanel.js` | Modified for correct/wrong branch coloring |
| `lib/besogo/boardDisplay.js` | SVG board rendering |
| `lib/besogo/coord.js` | Coordinate label systems |

## Layout

```
+---------------------------------------------------+
| HEADER (compact, top)                              |
+----------+----------------------+-----------------+
| SIDEBAR  | BOARD (fixed         | RIGHT PANEL     |
|          | min 520px, dominant) | 320px           |
| fixed-top|                      |                 |
|  SGF I/O | BesoGo SVG           | Player Indicator|
|  Visits  | + Score Overlay SVG  | Solution Tree   |
|  Engine  |   (pointer-events:   | Policy Priors   |
|          |    none)             | Analysis Table  |
| scroll   |                      |  (scrollable)   |
|  Stepper |                      |                 |
|  Config  |                      |                 |
|  Panel   |                      |                 |
|          |                      |                 |
| fixed-bot|                      |                 |
|  Run Info|                      |                 |
+----------+----------------------+-----------------+
| LOG PANEL (300px+, collapsible, resizable)         |
+---------------------------------------------------+
```

The sidebar uses a **three-zone layout**: fixed-top (SGF input + engine status + visits dropdown), scrollable middle (stage stepper + config panel), and fixed-bottom (run info).

## Config Panel

The config panel exposes all 45 enrichment parameters organized in **7 accordion groups** (Difficulty, Refutations, Technique Detection, Solution Tree, AI Solve, Teaching, Analysis). Each parameter shows the current value, a "modified" badge when changed from default, and the default value for reference. Per-parameter reset buttons restore individual values.

**Weight sliders** (difficulty weighting group) enforce `sum = 100` with a normalize button.

**Config diff** is shown before enrichment: only parameters that differ from the server defaults are sent as `config_overrides` in `POST /api/enrich`.

### localStorage Schema

Config state persists under the `enrichment-lab-config` key:

```json
{
  "version": 1,
  "overrides": { "difficulty.weights.depth": 30, ... },
  "analyze_visits": 500,
  "accordion_state": { "difficulty": true, "refutations": false, ... }
}
```

## Design Decisions

- **No npm, no build step, no framework** — eliminates the accidental complexity that caused 3 prior GUI failures
- **bridge.py serves static files** via FastAPI `StaticFiles` — single origin, zero CORS
- **Coordinate contract** — BesoGo uses 1-indexed `(col, row)` internally. `board.js` maps stone values (`-1`=black, `1`=white) into API-ready 2D arrays for `/api/analyze`.
- **ID format** — `run_id` uses `YYYYMMDD-xxxxxxxx` format matching the backend pipeline for seamless integration

> **See also:**
> - [Architecture](../../../docs/architecture/tools/enrichment-lab-gui.md) — Full architecture decision record
