# Tasks — Enrichment Lab GUI v4 (OPT-1R Revised)

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Selected Option:** OPT-1R (GhostBan Board + BesoGo Tree + No Build Step)  
**Last Updated:** 2026-03-10 (Revision 2)

---

## Task Dependency DAG

```
T1 (scaffold+serve) → T2 (state) → T3 (board+interactive) ──→ T6 (SSE+analyze wiring) → T8 (integration)
                           │              │                          │
                           │              └→ T5 (analysis table)─→ T8
                           │
                           └→ T4 (BesoGo tree mods) ──────────→ T8
                           │
T7 (pipeline-bar) ──────────────────────────────────────────→ T8
T9 (log-panel) ─────────────────────────────────────────────→ T8
T10 (sgf-input) ────────────────────────────────────────────→ T8

T8 → T11 (styles) → T12 (docs) → T13 (regression)
```

**[P] = can execute in parallel**

---

## Phase 0: ID Format Alignment (Pre-Requisite)

### T0: Align run_id format with backend pipeline

**Depends on:** None  
**Files:** `tools/puzzle-enrichment-lab/models/ai_analysis_result.py`

**Problem:** The enrichment lab's `generate_run_id()` produces `YYYYMMDD-HHMMSS-XXXXXXXX` (23 chars, uppercase hex) while the backend pipeline uses `YYYYMMDD-xxxxxxxx` (17 chars, lowercase hex). For future integration, these must match.

**Fix:** Change `generate_run_id()` (line 40-46) from:
```python
def generate_run_id() -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(4).upper()}"
```
to:
```python
def generate_run_id() -> str:
    """Generate a run_id: YYYYMMDD-xxxxxxxx.
    
    Matches backend/puzzle_manager run_id format for seamless integration.
    """
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%d}-{secrets.token_hex(4)}"
```

**Verification:** `trace_id` already matches (both use `uuid4().hex[:16]`). `puzzle_id` already uses GN/YENGO format (set at publish, not enrichment lab's responsibility).

| ID | Backend (puzzle_manager) | Enrichment Lab (after fix) | 
|----|--------------------------|---------------------------|
| trace_id | `uuid4().hex[:16]` (16 lowercase hex) | Same |
| run_id | `YYYYMMDD-{token_hex(4)}` (17 chars) | Same |
| puzzle_id | `YENGO-{SHA256[:16]}` (set at publish) | Uses GN from SGF |

---

## Phase 1: Scaffold

### T1: Project Scaffold + StaticFiles Serving

**Depends on:** None  
**Files:** `gui/index.html`, `gui/lib/ghostban.min.js`, `gui/lib/besogo/*.js`, bridge.py (2 lines)

- Create `tools/puzzle-enrichment-lab/gui/` directory
- Copy `ghostban.min.js` from `gui_deprecated/node_modules/ghostban/build/index.min.js` → `gui/lib/ghostban.min.js`
- Copy BesoGo JS files from `tools/sgf-viewer-besogo/js/` → `gui/lib/besogo/` (7 files: besogo.js, editor.js, gameRoot.js, svgUtil.js, parseSgf.js, loadSgf.js, treePanel.js)
- Create `gui/index.html` with `<script>` tags loading all libs + app modules. Layout skeleton (sidebar + main + log).
- Add 2 lines to bridge.py: `from fastapi.staticfiles import StaticFiles` + `app.mount("/", ...)` (AFTER all API routes)
- Verify: `python bridge.py` → open `http://localhost:8999` → see GUI skeleton

### T2: State Management Module

**Depends on:** T1  
**Files:** `gui/src/state.js`

- Implement `createState(initial)` → `{ get, set, subscribe }` observable
- Export atoms: `boardState`, `analysisResult`, `pipelineStages`, `logLines`, `enrichResult`, `sgfText`, `runInfo`

---

## Phase 2: Core Components [P]

### T3: GhostBan Board + Overlay + Interactive Stone Placement [P]

**Depends on:** T2  
**Files:** `gui/src/board.js`

- Initialize GhostBan: `boardSize`, `coordinate: true`, `interactive: true`
- Subscribe to `boardState` → convert stone lists to GhostBan Ki matrix (`mat[x][y]` — column-major, NO transposition)
- Overlay canvas for analysis dots (score-loss coloring: green/lightgreen/yellow/red)
- **Interactive mode**: click handler toggles intersection (empty → black → white → empty). Tracks modifications to `boardMat`.
- Subscribe to `analysisResult` → draw dots with score lead labels

### T4: BesoGo Tree Modifications [P]

**Depends on:** T2  
**Files:** `gui/lib/besogo/treePanel.js` (modify copy)

- Modify `finishPath(path, color)` → accept optional `branchClass` parameter
- Modify `makeNodeIcon(node, x, y)` → append `<text>` SVG element with winrate/visits label if node has analysis data
- Modify `recursiveTreeBuild()` → inspect `node.comment` (C[] property) for "Correct"/"Wrong" → assign CSS class
- Add CSS: `.branch-correct { stroke: #22c55e; }`, `.branch-wrong { stroke: #ef4444; }`
- Wire: BesoGo editor `navChange` → update `boardState` (click tree node → board updates)

### T5: Analysis Table [P]

**Depends on:** T2  
**Files:** `gui/src/analysis-table.js`

- Subscribe to `analysisResult` → render table
- Columns: Order, Move (human-readable), Prior (%), Score (+/-), Visits, PV (5 moves)
- Row hover → highlight analysis dot on board overlay
- Dark theme styling

### T7: Pipeline Stage Bar [P]

**Depends on:** T2  
**Files:** `gui/src/pipeline-bar.js`

- 10 pill boxes matching enrichment stages (parse_sgf through enriched_sgf)
- 4 states: gray (pending) → blue-pulse (active) → green (success) → red (error)
- Run info display: `run_id`, `trace_id`, `ac_level` badge (shown after `complete` event)
- Stage detail tooltips: validation_status, refutation_count, difficulty_level (from `teaching_enrichment` event data)

### T9: Log Panel [P]

**Depends on:** T2  
**Files:** `gui/src/log-panel.js`

- Collapsible panel at bottom
- Subscribe to `logLines` → append with timestamp
- Auto-scroll, clear button, collapse toggle

### T10: SGF Input Panel [P]

**Depends on:** T2  
**Files:** `gui/src/sgf-input.js`

- Textarea for paste, file upload, download button
- [Enrich] button → triggers SSE enrichment flow
- [Analyze] button → triggers single position analysis
- [Cancel] button → abort enrichment

---

## Phase 3: Wiring

### T6: Bridge Client + SSE → Board Wiring

**Depends on:** T3  
**Files:** `gui/src/bridge-client.js`, `gui/src/app.js` (partial)

- `analyzePython(board, currentPlayer, options)` → POST `/api/analyze` → return result
- `streamEnrichment(sgfText, signal)` → POST `/api/enrich` → async generator yielding SSE events
- Cancel-previous pattern (AbortController)
- Wiring logic:
  - `board_state` SSE → update `boardState` → trigger `analyzePython()` for analysis dots
  - `enriched_sgf` (complete) → load SGF into BesoGo editor → tree builds
  - `complete` → update `enrichResult`, `runInfo` (run_id, trace_id, ac_level), analysis table
  - All SSE events → update `pipelineStages` (stage status) + append to `logLines`
  - `teaching_enrichment` → show level, refutation count, hints count in stage tooltip

---

## Phase 4: Integration & Polish

### T8: Full Integration + Keyboard Shortcuts

**Depends on:** T6, T4, T7, T9, T10  
**Files:** `gui/src/app.js`

- Wire all components together
- [Enrich] button → `streamEnrichment()` SSE loop → pipeline-bar + board + tree + log
- [Analyze] button → `analyzePython()` with current board position → analysis dots
- Interactive: click board to place stone → [Analyze] → see analysis from that position
- Tree node click → board navigates → analysis table updates
- Keyboard shortcuts: Arrow Left/Right (tree nav), Home/End (first/last)
- Error handling: errors → log panel + pipeline-bar stage → red

### T11: Styles + Dark Theme

**Depends on:** T8  
**Files:** `gui/css/styles.css`

- Dark theme (goproblems.com Research(Beta) aesthetic)
- CSS Grid layout: sidebar + main + log
- Pipeline bar pill styling (colored circles with labels)
- Analysis table dark styling
- BesoGo tree container styling + branch coloring CSS

---

## Phase 5: Quality

### T12: Documentation

**Depends on:** T11  
**Files:** `gui/README.md`, `gui/COORDINATES.md`, `tools/puzzle-enrichment-lab/README.md`, `docs/architecture/tools/enrichment-lab-gui.md`

- DOC-1: gui/README.md (quick start, architecture)
- DOC-2: Update lab README (add GUI section)
- DOC-3: gui/COORDINATES.md (coordinate contract)
- DOC-4: Replace enrichment-lab-gui.md with OPT-1R architecture

### T13: Regression Verification

**Depends on:** T12  
**Files:** None (test runs only)

- `pytest tests/test_enrich_single.py tests/test_cli_overrides.py` → all pass
- `python cli.py enrich --sgf <puzzle> --output result.json` → works unchanged
- `python bridge.py` → starts, serves GUI at `/`, API at `/api/*`
- Manual AC checklist (AC1-AC10 + interactive analysis)

---

## Parallel Execution Map

```
Phase 1 (sequential):  T1 → T2
Phase 2 (parallel):    [P] T3, T4, T5, T7, T9, T10
Phase 3 (sequential):  T6 (needs T3)
Phase 4 (sequential):  T8 → T11
Phase 5 (sequential):  T12 → T13
```

---

## Estimated Scope

| Directory | Files | Lines (est.) |
|-----------|-------|-------------|
| `gui/` (root) | 1 (index.html) | ~60 |
| `gui/lib/` | 1 (ghostban.min.js) + 7 (besogo/*.js, 1 modified) | ~50 lines of mods |
| `gui/src/` | 8 (app.js, state.js, board.js, analysis-table.js, pipeline-bar.js, log-panel.js, sgf-input.js, bridge-client.js) | ~700-900 |
| `gui/css/` | 1 (styles.css) | ~150 |
| `gui/` docs | 2 (README.md, COORDINATES.md) | ~100 |
| bridge.py | 2 lines added | ~2 |
| **Total new/modified** | ~20 files | **~900-1100 lines** |

> **See also:**
>
> - [Plan](./30-plan.md) — Architecture, data flow, coordinate contract
> - [Charter](./00-charter.md) — Goals and acceptance criteria
> - [Options](./25-options.md) — OPT-1R selection rationale
