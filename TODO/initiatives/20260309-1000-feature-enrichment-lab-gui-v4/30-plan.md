# Plan — Enrichment Lab GUI v4 (OPT-1R Revised)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Selected Option:** OPT-1R (GhostBan Board + BesoGo Tree + No Build Step)  
**Last Updated:** 2026-03-10 (Revision 2 — accidental complexity eliminated)

---

## Revision Summary

OPT-1 (2026-03-09) had accidental complexity: custom SVG tree (~300 lines) when BesoGo treePanel exists, and Vite+npm when bridge.py can serve static files directly. OPT-1R saves ~400-500 lines, eliminates all npm dependencies, and reduces startup to `python bridge.py`.

New features added in revision:
- **G10: Interactive analysis** — click board to place/remove stones → [Analyze] → KataGo analysis dots (separate from enrichment)
- **Pipeline bar enhancements** — run_id display for troubleshooting, detailed stage outputs (level, hints count, teaching comments)

---

## Architecture

### Component Diagram

```
bridge.py (FastAPI :8999) — serves API + GUI static files on single origin
 │
 ├── /api/analyze    → Interactive KataGo analysis
 ├── /api/enrich     → Full pipeline (SSE)
 ├── /api/cancel     → Cancel enrichment
 ├── /api/health     → Engine status
 └── /*              → gui/ static files (StaticFiles mount)
```

```
┌──────────────────────────────────────────────────────────────────────┐
│  Pipeline Bar (10 stages, pill boxes: gray→blue-pulse→green/red)    │
│  + run_id (log filename) + trace_id + ac_level badge                │
├──────────────────┬───────────────────────────────────────────────────┤
│  Sidebar         │  Main Area                                       │
│                  │                                                   │
│  SGF Input       │  ┌─────────────┐  ┌────────────────────────┐     │
│  (paste/upload/  │  │ GhostBan    │  │ BesoGo Tree Panel      │     │
│   download)      │  │ Board +     │  │ (correct=green,        │     │
│                  │  │ Overlay     │  │  wrong=red,             │     │
│  [Enrich]        │  │ Canvas      │  │  policy prior labels)  │     │
│  [Analyze]       │  │             │  │                         │     │
│  [Cancel]        │  │ INTERACTIVE │  │  Click node → board     │     │
│                  │  │ click to    │  │  navigates to position  │     │
│  Engine Status   │  │ place stone │  └────────────────────────┘     │
│  (model,ac_level)│  └─────────────┘                                 │
│                  │  Status Bar (turn, score, visits, winrate)        │
│                  │  Analysis Table (Order,Move,Prior,Score,Vis,PV)   │
├──────────────────┴───────────────────────────────────────────────────┤
│  Log Panel (collapsible) — streaming engine logs, auto-scroll        │
└──────────────────────────────────────────────────────────────────────┘
```

### Two Distinct Workflows

| Workflow | Trigger | API | What Happens |
|----------|---------|-----|-------------|
| **Enrich** | [Enrich] button | `POST /api/enrich` (SSE) | Full 10-stage pipeline. Pill boxes turn green/red. Board updates. Tree built at completion. |
| **Analyze** | [Analyze] button | `POST /api/analyze` | Single KataGo query on current board position. Analysis dots appear. Quick (~1-3s). No pipeline stages. |

User can: Load SGF → Enrich → watch pipeline → OR → click board to place stone → Analyze → see policy priors from that position. These are independent workflows.

### Pipeline Stage Bar Specification

| # | Stage ID | Label | SSE Event | Data Shown |
|---|----------|-------|-----------|------------|
| 1 | parse_sgf | Parse SGF | `parse_sgf` | puzzle_id |
| 2 | extract_solution | Extract Solution | `extract_solution` | has_solution? |
| 3 | build_query | Tsumego Frame | `build_query` | board_size, num_stones |
| 4 | katago_analysis | KataGo Analysis | `katago_analysis` | (spinner) |
| 5 | validate_move | Validate Move | `validate_move` | |
| 6 | generate_refutations | Refutations | `generate_refutations` | correct_move, solution_depth |
| 7 | estimate_difficulty | **Level ID** | `estimate_difficulty` | |
| 8 | assemble_result | Assemble | `assemble_result` | |
| 9 | teaching_enrichment | **Hints + Comments** | `teaching_enrichment` | validation_status, refutation_count, difficulty_level |
| 10 | enriched_sgf | Build SGF | `enriched_sgf` | complete/failed |

**Pill states**: gray (pending) → blue-pulse (active) → green (success) → red (error)

**Run info bar** (below pipeline): After `complete` event, show:
- `run_id`: `YYYYMMDD-xxxxxxxx` format (matches backend pipeline for seamless integration) — identifies log file for troubleshooting
- `trace_id`: `uuid4().hex[:16]` (16-char lowercase hex, same as backend) — unique per puzzle
- `ac_level` badge: 0=UNTOUCHED, 1=ENRICHED, 2=AI_SOLVED, 3=VERIFIED

**ID format alignment note:** T0 (pre-requisite task) aligns the lab's `generate_run_id()` with the backend's `YYYYMMDD-xxxxxxxx` format. `trace_id` already matches. `puzzle_id` (YENGO-{hash}) is set at publish stage, not the enrichment lab's responsibility.

### State Management

No framework. All `gui/src/*.js` files loaded as `<script type="module">` (native ES module `import`/`export`, no bundler). GhostBan and BesoGo loaded as classic `<script>` tags (global namespace: `GhostBan`, `besogo`).

```javascript
// state.js — Simple observable state (no framework)
function createState(initial) {
  let value = initial; const subs = new Set();
  return {
    get: () => value,
    set: (v) => { value = v; subs.forEach(fn => fn(value)); },
    subscribe: (fn) => { subs.add(fn); return () => subs.delete(fn); }
  };
}
```

### Coordinate Contract (Root Cause Prevention)

API `{x, y}` → directly `mat[x][y]` for GhostBan (column-major). NO intermediate `mat[row][col]`.

### Bridge.py Change (C7-Compliant — 2 additive lines)

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=str(_lab_root / "gui"), html=True), name="gui")
```

Must be AFTER all `/api/*` route definitions.

### BesoGo Tree Modifications (~50 lines)

Copy 7 files from `tools/sgf-viewer-besogo/js/`. Modify `treePanel.js`:
1. `finishPath()` → accept optional CSS class for correct/wrong coloring
2. `makeNodeIcon()` → append `<text>` with policy prior (winrate/visits)
3. `recursiveTreeBuild()` → inspect C[] comment for "Correct"/"Wrong" → apply CSS class

### Interactive Board Analysis (~20 lines)

GhostBan `interactive: true` + click handler toggles stones (empty → black → white → empty). [Analyze] button sends current board to `/api/analyze`.

---

## Risks and Mitigations

| ID | Risk | Prob | Mitigation |
|----|------|------|------------|
| R1 | BesoGo tree mods exceed ~50 lines | Low | finishPath/makeNodeIcon are clean extension points |
| R2 | GhostBan .min.js doesn't work as script tag | Low | Verified UMD bundle. Fallback: unminified source |
| R3 | StaticFiles mount conflicts with API | Low | FastAPI routes take priority over catch-all |
| R4 | Engine serialization delays analysis during enrichment | Low | 1-3s acceptable. "Analyzing..." indicator |

## Rollback Plan

`rm -rf gui/` + remove 2 StaticFiles lines from bridge.py. <2 minutes.

## Documentation Plan

### Files to Create

| ID | File | Why |
|----|------|-----|
| DOC-1 | `gui/README.md` | Quick start (`python bridge.py`), architecture |
| DOC-3 | `gui/COORDINATES.md` | Coordinate contract — root cause prevention |

### Files to Update

| ID | File | Why |
|----|------|-----|
| DOC-2 | `tools/puzzle-enrichment-lab/README.md` | Add GUI startup section |
| DOC-4 | `docs/architecture/tools/enrichment-lab-gui.md` | **REPLACE** old content with OPT-1R |

### Cross-Reference Coverage

No updates needed to `docs/how-to/`, `docs/concepts/`, `docs/reference/`.

## Test Strategy

| ID | Scope | Tool |
|----|-------|------|
| TEST-1 | Pipeline bar stages turn green/red correctly | Manual |
| TEST-2 | run_id + ac_level display after enrichment | Manual |
| TEST-3 | Interactive analysis: place stone → analyze → dots | Manual |
| TEST-4 | Tree click → board navigates | Manual |
| TEST-5 | AC1-AC10 + new ACs checklist | Manual |
| TEST-6 | CLI regression: `pytest tests/test_enrich_single.py tests/test_cli_overrides.py` | pytest |

> **See also:**
>
> - [Charter](./00-charter.md) — Goals, constraints
> - [Options](./25-options.md) — OPT-1R selection rationale
> - [Tasks](./40-tasks.md) — Task breakdown
