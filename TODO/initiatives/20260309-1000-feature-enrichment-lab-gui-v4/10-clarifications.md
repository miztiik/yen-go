# Clarifications — Enrichment Lab GUI v4 (Fresh Build)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-09

---

## Round 1 (2026-03-09)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Revive gui_deprecated or start fresh? | A: Revive / B: Fresh build / C: Other | A | **B: Start fresh.** gui_deprecated was a hybrid (browser TF.js + bridge) that tried to recreate board analysis using WebGL/model loading. The new GUI is NOT that — it only displays what Python sends. Also, gui_deprecated had persistent coordinate/signal interpretation bugs between Preact Signals and GhostBan board coordinates that led to deprecation. | ✅ resolved |
| Q2 | Remove TF.js browser engine? | A: Remove (bridge-only) / B: Keep dual / C: Other | A | **N/A — moot since Q1=B (fresh build).** No TF.js, no browser engine. All analysis runs in Python/KataGo. Frontend receives and displays results only. | ✅ resolved |
| Q3 | Board library: keep GhostBan? | A: GhostBan + overlay / B: Custom SVG / C: goban / D: Other | A | **A (with caveats): Use GhostBan** if it can reproduce the goproblems.com look and feel. Frontend only receives and displays what Python sends. No board-side analysis. Research also noted BesoGo (tools/sgf-viewer-besogo/) as a candidate for the solution tree panel specifically. | ✅ resolved |
| Q4 | Solution tree visualization approach? | A: SVG tree as-is / B: Add policy priors / C: Replace / D: Other | B | **B: Add policy priors (visits, winrate, score per branch)** like the goproblems.com screenshots. Clicking a move in the tree loads it on the board and displays the appropriate policy priors. BesoGo's treePanel.js is also an option to consider for tree rendering. Must animate correct (green) and wrong (red) branches with right colors. | ✅ resolved |
| Q5 | Log streaming approach? | A: Scrollable div below board / B: Collapsible drawer / C: Side panel / D: Other | A | **B: Collapsible div** — simplest approach, just visualize logs so user can quickly identify what's happening. | ✅ resolved |
| Q6 | Remove gui_deprecated? | A: Remove, replace / B: Keep alongside / C: Rename | A | **B: Leave gui_deprecated as-is.** User will clean it up later. New GUI goes in `gui/` directory. | ✅ resolved |
| Q7 | KataGo solving visualization scope? | A: ac_level indicator / B: Analysis dots during enrichment / C: Animate tree-building / D: A+B | D | **D: A+B** — ac_level indicator + analysis dots during enrichment. Skip real-time tree animation for now. | ✅ resolved |
| Q8 | Where should the GUI directory live? | A: gui/ / B: gui_v4/ / C: Other | A | **A: `tools/puzzle-enrichment-lab/gui/`** — no version suffix. | ✅ resolved |

---

## Round 2 — Governance-Mandated Investigation (2026-03-09)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q9 | **Engine concurrency (RC-3):** Can `/api/analyze` run while pipeline enrichment is active? `SingleEngineManager` is a singleton. If it serializes, G8 (analysis dots during enrichment) needs a fallback. | A: Concurrent (engine multiplexes) / B: Serialized (analyze after enrichment completes) / C: Analyze between pipeline stages / D: Unknown — investigate | Investigate during options phase. Fallback: trigger analyze only after enrichment completes. | Serialized via threading.Lock(). Requests queue, don’t fail. 1-3s delay acceptable. | ✅ resolved (Decision 1 RC-3) |
| Q10 | **Frontend tech stack:** What framework for the fresh build? | A: Preact + Signals + Vite / B: Vanilla JS + Vite / C: Vanilla JS (no build step) / D: Other | Decide in options phase | OPT-1R: Vanilla JS + no build step. bridge.py serves static files. | ✅ resolved (OPT-1R) |

---

## Key Decisions Captured

### Why gui_deprecated was deprecated (DOCUMENT THIS)

gui_deprecated was deprecated for the following reasons:
1. **Hybrid architecture mismatch**: It tried to be a hybrid browser+bridge tool — loading KataGo models via TF.js WebGL AND connecting to the Python bridge. This created constant confusion about which engine was active and what signals meant.
2. **Coordinate/signal interpretation bugs**: There were persistent bugs in coordinate translation between Preact Signals state and GhostBan's board coordinate system. GhostBan uses column-major mat[col][row], while board data was mat[row][col]. The transposition logic in GoBoardPanel.tsx was fragile and caused display bugs.
3. **Scope creep**: The GUI was trying to recreate analysis capabilities (model loading, WebGL inference) that belong in Python, not in the browser.

### Fresh build principles (from user)

1. **Python does ALL analysis.** Frontend only receives and displays results from Python/KataGo via the bridge API.
2. **No browser-side AI.** No TF.js, no WebGL model loading, no WASM inference.
3. **Keep it simple.** This is a visualization tool for the enrichment pipeline, not a standalone analysis platform.
4. **Can copy code** from gui_deprecated but NOT revive that project structure.
5. **Board library options open**: GhostBan and BesoGo (tools/sgf-viewer-besogo/) are both candidates. BesoGo has a tree panel with SVG rendering and is already in the project.

### Backward compatibility

- **Not required.** This is a new additive feature.
- gui_deprecated stays as-is (user cleanup later).
- The existing bridge.py and enrich_single.py progress_cb remain unchanged.
