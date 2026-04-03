# Architecture: Enrichment Lab GUI (v4 — OPT-1R)

**Last Updated:** 2026-03-14 (v4.2 — Config Panel + Sidebar Redesign)

---

## Purpose

The enrichment lab GUI (`tools/puzzle-enrichment-lab/gui/`) is a lightweight visual pipeline observer for KataGo puzzle enrichment. Python does all analysis — the GUI only receives and displays results via the bridge.py FastAPI server.

**Prior attempts:** Three earlier GUI approaches failed due to: (1) hybrid browser+bridge analysis confusion, (2) Preact Signals ↔ GhostBan coordinate transposition bugs, (3) 200MB TF.js dependency bloat. v4 (OPT-1R) eliminated all three root causes. v4.1 replaced the GhostBan canvas board with BesoGo, unifying board rendering, Go rules, and tree navigation in a single library.

---

## Design Decisions

### D1: Python Does All Analysis

All KataGo analysis, enrichment, validation, and difficulty estimation runs server-side in Python. The frontend has ZERO browser-side AI (no TF.js, no WebGL models, no WASM inference). Data flows from bridge.py API to the GUI via HTTP responses and SSE events.

### D2: No Build Step, No npm Dependencies

The GUI uses vanilla JS with ES modules (`<script type="module">`) and BesoGo JS files copied from `tools/sgf-viewer-besogo/`. No npm, no Vite, no package.json, no node_modules. Startup: `python bridge.py`.

### D3: Single Origin via StaticFiles

bridge.py serves GUI static files via FastAPI `StaticFiles` mount, eliminating CORS entirely. Both API and GUI on `http://localhost:8999`.

### D4: Coordinate Contract (Root Cause Prevention)

BesoGo uses 1-indexed `(col, row)` coordinates internally. `board.js` exports `getCurrentBoard()` which maps BesoGo stone values (`-1`=black, `1`=white) into an API-ready 2D array for `/api/analyze`. This prevents the coordinate transposition bug that caused gui_deprecated to fail.

### D5: BesoGo Board + Tree (unified)

v4.1 replaced the previous GhostBan canvas + separate BesoGo tree with a single `besogo.create()` call that provides:
- SVG Go board with kaya-wood theme
- Full Go rule enforcement (captures, ko, suicide prevention)
- SGF parsing and move-tree navigation
- Solution tree panel synced to board position
- Stone placement via click (auto tool)

The prior GhostBan approach lacked Go rules and could not sync with the tree. Unifying on BesoGo eliminates the two-library coordination problem.

### D6: BesoGo Tree Panel (branch coloring)

Solution tree uses BesoGo's `treePanel.js` (copied from `tools/sgf-viewer-besogo/`), modified (~50 lines) for:
- Correct branch coloring (green) from SGF C[] "Correct" comment
- Wrong branch coloring (red) from SGF C[] "Wrong"/"Refutation" comment
- Colored ring around nodes for visual correctness indication

### D7: Two Independent Workflows

| Workflow | API | Purpose |
|----------|-----|---------|
| **Enrich** | `POST /api/enrich` (SSE) | Full 10-stage pipeline with stage-by-stage progress |
| **Analyze** | `POST /api/analyze` | Single KataGo query on any board position (~1-3s) |

### D8: ID Format Alignment

`run_id` uses `YYYYMMDD-xxxxxxxx` format matching the backend `puzzle_manager` pipeline for seamless future integration. `trace_id` uses `uuid4().hex[:16]` (same as backend).

### D9: Config Override Transport (v4.2)

Config overrides are sent as a flat JSON dict of dotted paths → values. The bridge utility (`bridge_config_utils.py`) resolves paths, deep-merges into the base `EnrichmentConfig`, and re-constructs through Pydantic to trigger all validators. `GET /api/config` returns `model_dump()` for client-side default resolution.

### D10: Three-Zone Sidebar (v4.2)

The sidebar is split into three zones: fixed-top (SGF input + engine status — always visible), scrollable-middle (stage stepper + config accordion), and fixed-bottom (run metadata). This follows the Grafana sidebar pattern to keep primary actions accessible while allowing config sections to scroll.

### D11: Config Panel Accordion (v4.2)

45 enrichment parameters are organized in 7 accordion groups (Analysis, Refutations, AI-Solve, Validation, Difficulty, Teaching, Ko). Only one group expands at a time. Each parameter renders as slider, toggle, number input, or dropdown. Modified values show a yellow badge, default label, and per-param reset button. Difficulty weights (sum=100) have a normalize button; invalid sums are excluded from overrides.

---

## Component Map

```
gui/
├── index.html              # Entry point
├── lib/besogo/             # BesoGo board + tree (9 files, treePanel.js modified)
│   ├── besogo.js           # Entry point — besogo.create()
│   ├── editor.js           # Core editor state & listeners
│   ├── gameRoot.js         # Game tree node model
│   ├── parseSgf.js         # SGF string → tree parser
│   ├── loadSgf.js          # Tree → editor loader
│   ├── boardDisplay.js     # SVG board rendering
│   ├── coord.js            # Coordinate label systems
│   ├── treePanel.js        # Solution tree (modified: branch coloring)
│   └── svgUtil.js          # SVG helpers
├── src/
│   ├── app.js              # Main orchestrator + SSE event processing
│   ├── state.js            # Observable state atoms (config, overrides, visits)
│   ├── board.js            # BesoGo wrapper — initBoard, loadSgf, getEditor, getCurrentBoard
│   ├── bridge-client.js    # HTTP + SSE client (incl. getConfig, config overrides)
│   ├── stage-stepper.js    # Vertical 10-stage pipeline stepper with timing
│   ├── config-panel.js     # 45-param accordion config panel with localStorage
│   ├── analysis-table.js   # Candidate moves table
│   ├── sgf-input.js        # SGF I/O + action buttons + visits dropdown
│   ├── policy-panel.js     # Policy prior bar chart
│   ├── board-overlay.js    # SVG overlay for score dots and PV preview
│   ├── player-indicator.js # Player-to-move + aggregate stats
│   └── log-panel.js        # Streaming log viewer
├── css/styles.css          # Dark theme + kaya-wood board theme
└── README.md               # Quick start + architecture summary
```

## Rollback

`rm -rf tools/puzzle-enrichment-lab/gui/` + remove StaticFiles mount from bridge.py (2 lines). <2 minutes.

> **See also:**
> - [gui/README.md](../../../tools/puzzle-enrichment-lab/gui/README.md) — Quick start
> - [Initiative artifacts](../../../TODO/initiatives/20260309-1000-feature-enrichment-lab-gui-v4/) — Full planning package
