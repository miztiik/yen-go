# Analysis — Enrichment Lab GUI v4 (OPT-1R Revised)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-10 (Revision 2)

---

## Planning Metadata

| Field | Value |
|-------|-------|
| `planning_confidence_score` | 85 (post-revision — simpler plan = higher confidence) |
| `risk_level` | low |
| `research_invoked` | Yes |

---

## 1. Charter ↔ Plan Coverage

| Charter Item | Plan Coverage | Task(s) | Status |
|--------------|---------------|---------|--------|
| G1: Pipeline stage progression | 10-stage pill bar with green/red/gray/blue states | T7, T8 | ✅ |
| G2: Real-time board updates | SSE board_state → GhostBan canvas | T3, T6 | ✅ |
| G3: Analysis dots | /api/analyze → overlay canvas | T3, T6 | ✅ |
| G4: Interactive solution tree | BesoGo treePanel with correct/wrong coloring | T4, T8 | ✅ |
| G5: SGF I/O | SGF input panel | T10 | ✅ |
| G6: Log panel | Collapsible log panel | T9 | ✅ |
| G7: ac_level indicator | Badge in pipeline bar after complete event | T7, T6 | ✅ |
| G8: Analysis dots during enrichment | board_state SSE → /api/analyze trigger | T6 | ✅ |
| G9: Click tree → board | BesoGo navChange → boardState update | T4, T8 | ✅ |
| G10: Interactive analysis (NEW) | Click board → place stone → [Analyze] → dots | T3, T6, T8 | ✅ |
| Pipeline details (teaching, hints, level) | teaching_enrichment event data shown in stage tooltip | T7 | ✅ |
| run_id for troubleshooting | Displayed below pipeline bar from complete event | T7 | ✅ |

---

## 2. Accidental Complexity Elimination

| OPT-1 Component | OPT-1R Replacement | Lines Saved |
|------------------|--------------------|-------------|
| Custom SVG tree (~300 lines) | BesoGo treePanel.js + ~50 lines mods | ~250 |
| Vite config + package.json | bridge.py StaticFiles (2 lines) | ~30 + entire node_modules |
| npm install + ghostban package | ghostban.min.js as static file | 0 npm deps |
| Vitest test framework | Manual testing (proportional for dev tool) | ~300 lines test scaffolding |
| **Total** | | **~600-700 lines + 0 npm deps** |

---

## 3. Ripple Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | bridge.py | 2 additive lines (StaticFiles mount) | C7-compliant. After all API routes. | T1 | ✅ addressed |
| RE-2 | upstream | enrich_single.py | None | progress_cb unchanged | T6 | ✅ addressed |
| RE-3 | upstream | SingleEngineManager | Serialized queries delay /api/analyze during pipeline | 1-3s acceptable | T6 | ✅ addressed |
| RE-4 | downstream | CLI | None | AC10 verified in T13 | T13 | ✅ addressed |
| RE-5 | lateral | gui_deprecated | None | Untouched (C3) | N/A | ✅ addressed |
| RE-6 | lateral | frontend/ | None | No imports (C1, C2) | N/A | ✅ addressed |
| RE-7 | lateral | sgf-viewer-besogo/ | Files COPIED not modified | Original untouched | T1 | ✅ addressed |

---

## 4. Findings

| finding_id | severity | description |
|------------|----------|-------------|
| F1 | INFO | OPT-1R eliminates all npm dependencies. Startup is single command: `python bridge.py` |
| F2 | INFO | BesoGo tree mods are ~50 lines to 3 functions (finishPath, makeNodeIcon, recursiveTreeBuild) |
| F3 | LOW | GhostBan .min.js is pinned copy from gui_deprecated — no upstream sync mechanism needed |
| F4 | INFO | Interactive analysis (G10) adds ~20 lines to board.js — proportional to value |
| F5 | INFO | Pipeline bar shows run_id from complete event — directly answers troubleshooting need |
