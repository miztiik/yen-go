# Options — Enrichment Lab GUI v4 (Revised)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-10 (Revision 2 — accidental complexity elimination)

---

## Revision History

- **v1 (2026-03-09):** 3 options proposed. OPT-1 (GhostBan + Custom SVG Tree + Vanilla JS + Vite) selected unanimously.
- **v2 (2026-03-10):** User identified accidental complexity in OPT-1. Two unnecessary layers:
  1. **Custom SVG tree (~300 lines)** when BesoGo's treePanel.js exists in the repo and only needs ~50 lines of coloring mods
  2. **Vite + npm** when bridge.py can serve GUI static files directly via FastAPI `StaticFiles` (zero CORS, zero build step)
  
  Plan revised to **OPT-1R** combining best of OPT-1 (GhostBan canvas board) + OPT-2 (BesoGo tree, no build step).

---

## OPT-1R: GhostBan Board + BesoGo Tree + No Build Step (Revised)

**Board:** GhostBan canvas board (copied from gui_deprecated's `node_modules/ghostban/build/index.min.js`) with overlay canvas for analysis dots  
**Tree:** BesoGo treePanel.js (copied from `tools/sgf-viewer-besogo/js/`) — modified for correct/wrong branch coloring + policy prior annotations  
**Stack:** Vanilla JS with `<script>` tags — NO npm, NO Vite, NO build step  
**Serving:** bridge.py serves GUI static files via FastAPI `StaticFiles` — single origin, zero CORS  
**Interactive Analysis:** Click board to place/remove stones → click "Analyze" → `/api/analyze` → analysis dots (separate from enrichment)

### Architecture

```
gui/
├── index.html              # Entry point, loads all scripts
├── lib/
│   ├── ghostban.min.js     # GhostBan board renderer (copied from npm cache)
│   └── besogo/             # BesoGo modules (copied from sgf-viewer-besogo)
│       ├── besogo.js       # Namespace
│       ├── editor.js       # Editor state machine
│       ├── gameRoot.js     # Game tree data structure
│       ├── svgUtil.js      # SVG helpers
│       ├── parseSgf.js     # SGF parser
│       ├── loadSgf.js      # SGF loader
│       └── treePanel.js    # Tree panel (MODIFIED: correct/wrong coloring + policy labels)
├── src/
│   ├── app.js              # Main orchestrator + keyboard shortcuts
│   ├── state.js            # Simple observable state (no framework)
│   ├── board.js            # GhostBan board + overlay canvas + interactive stone placement
│   ├── analysis-table.js   # Analysis candidates table
│   ├── pipeline-bar.js     # 10-stage pipeline with green/red/active pills + run_id
│   ├── log-panel.js        # Collapsible log viewer
│   ├── sgf-input.js        # Paste/upload/download
│   └── bridge-client.js    # HTTP + SSE client for bridge.py
└── css/
    └── styles.css          # Dark theme (vanilla CSS)
```

### Why This Eliminates Accidental Complexity

| Problem in OPT-1 | OPT-1R Fix | Lines Saved |
|-------------------|------------|-------------|
| Custom SVG tree (~300 lines) | BesoGo treePanel.js + ~50 lines of coloring mods | ~250 lines |
| Vite for dev proxy | bridge.py serves static files (2 lines of Python) | Entire Vite config + package.json |
| npm + node_modules | GhostBan .min.js as static file + BesoGo .js files | ~20MB node_modules eliminated |
| GhostBan import resolution | `<script src="lib/ghostban.min.js">` | No module bundler needed |

### Bridge.py Change (C7-compliant — additive only)

```python
# Add 2 lines to bridge.py
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="gui", html=True), name="gui")
```

Single origin `http://localhost:8999` serves both API and GUI. Zero CORS.

### Benefits

| ID | Benefit |
|----|---------|
| B1 | **Zero build step.** `python bridge.py` → open browser → done. |
| B2 | **Zero npm dependencies.** GhostBan is a 120KB .min.js file. BesoGo is ~10 JS files. |
| B3 | **GhostBan canvas board** reproduces goproblems.com look (validated in production). |
| B4 | **BesoGo tree already has** recursive layout, SVG node icons, click navigation, scrolling. Only needs ~50 lines for coloring + policy annotations. |
| B5 | **Single origin** — no CORS, no proxy config, no Vite. |
| B6 | **True disposability.** `rm -rf gui/` and remove 2 lines from bridge.py. |
| B7 | **Interactive analysis mode.** GhostBan `interactive: true` + click handler → place stone → `/api/analyze` → dots. Completely separate from enrichment. |

### Risks

| ID | Risk | Probability | Mitigation |
|----|------|-------------|------------|
| R1 | BesoGo tree mods for coloring take more than ~50 lines | Low | treePanel.js `finishPath()` and `makeNodeIcon()` are clean extension points |
| R2 | GhostBan .min.js doesn't export expected API from `<script>` tag | Low | Already verified as UMD bundle — `window.GhostBan` exists |
| R3 | Two static-file copies (GhostBan + BesoGo) need updating | Low | Pinned versions, developer tool, no upstream tracking needed |

### Complexity: ~800-1000 lines new/modified code | 0 npm dependencies | 2 lines bridge.py change

---

## Superseded Options (from v1)

- **OPT-1 (original):** GhostBan + Custom SVG Tree + Vanilla JS + Vite — had accidental complexity (custom tree, unnecessary Vite)
- **OPT-2:** BesoGo Full + No Build — lacked analysis dots (no canvas overlay)
- **OPT-3:** GhostBan + Preact + Vite — HIGH risk of coordinate bugs (repeats gui_deprecated failure)

> **See also:**
>
> - [Charter](./00-charter.md) — Goals, non-goals, constraints
> - [Clarifications](./10-clarifications.md) — User decisions and deprecation causes
> - [Research](./15-research.md) — Board library evaluation, SSE catalog
