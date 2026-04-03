# Tasks — Config Panel + Sidebar Redesign (Phase A)

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Option**: OPT-1 Phase A (G-1 through G-7 + config-diff enhancement)
**Last Updated**: 2026-03-14

---

## Task Legend
- `[P]` = Parallelizable with adjacent tasks
- `[D:Tn]` = Depends on task Tn
- Files use relative paths from `tools/puzzle-enrichment-lab/`

---

## Group 1: Bridge API (Backend)

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T1 | **Create config override utility** | NEW: `bridge_config_utils.py` | — | `unflatten_dotted_paths()` + `apply_config_overrides(base, overrides)` + `deep_merge()`. ~40 lines. Pydantic re-validates on construction. |
| T2 | **Unit tests for config override** | NEW: `tests/test_bridge_config.py` | D:T1 | Test: dotted-path resolution, nested merge, Pydantic validation errors (invalid type, out-of-range), empty overrides passthrough, unknown paths ignored. ~8 test cases. |
| T3 | **Add GET /api/config endpoint** | `bridge.py` | — | [P] New endpoint returning `load_enrichment_config().model_dump()`. ~10 lines. |
| T4 | **Extend POST /api/enrich with config_overrides** | `bridge.py` | D:T1 | Add `config_overrides: dict | None = None` to `EnrichRequest`. In endpoint: if overrides → `apply_config_overrides()` → pass to `enrich_single_puzzle(config=merged)`. ~15 lines. |
| T5 | **Verify POST /api/analyze visits wiring** | `bridge.py` | — | [P] **Verified**: `AnalyzeRequest.visits` is already wired end-to-end (line 302: `visits = req.visits or 200`, line 305: `max_visits=visits`). T5 is verify-only — no bridge.py change needed. GUI just needs to pass the value (T16, T17). |

---

## Group 2: CSS & Widget Foundation

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T6 | **Add new CSS variables** | `gui/css/styles.css` | — | [P] Add `--bg-hover`, `--accent-dim`, `--warning` to `:root`. 3 lines. |
| T7 | **Implement widget CSS library** | `gui/css/styles.css` | D:T6 | Range slider (`.config-slider`), number input (`.config-number`), toggle switch (`.config-toggle`), dropdown (`.config-select`), config item layout (`.config-item`, `.config-item-header`, `.config-label`, `.config-value`, `.config-range-labels`). ~120 lines from research Section 4.4. |
| T8 | **Implement accordion CSS** | `gui/css/styles.css` | D:T6 | `.config-panel`, `.config-group`, `.config-group-header`, `.config-group-body`, `.config-chevron`, `.config-group-count`, expand animation. ~50 lines from research Section 4.3. |
| T9 | **Implement stage stepper CSS** | `gui/css/styles.css` | D:T6 | `.stage-stepper`, `.stage-item`, `.stage-dot`, `.stage-line`, `.stage-content`, `.stage-name`, `.stage-time`, status modifiers. ~60 lines from research Section 4.2. |
| T10 | **Implement difficulty weight CSS** | `gui/css/styles.css` | D:T7 | `.config-weights`, `.weights-header`, `.weights-sum`, `.weight-row`, `.weight-label`, `.weight-value`, `.weights-normalize`. ~30 lines from research Section 4.5. |
| T11 | **Implement three-zone sidebar CSS** | `gui/css/styles.css` | D:T6 | `.sidebar-fixed-top`, `.sidebar-scroll`, `.sidebar-fixed-bottom`. Revise `.sidebar` flex layout to support three zones. ~20 lines. |
| T12 | **Config diff visual CSS** | `gui/css/styles.css` | D:T7 | `.config-modified` badge, `.config-default` label, `.config-reset-btn`. ~15 lines. |

---

## Group 3: GUI Components (JavaScript)

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T13 | **Create stage-stepper.js** | NEW: `gui/src/stage-stepper.js` | D:T9 | Replace `pipeline-bar.js` logic. Subscribe to `pipelineStages` state. Render vertical stepper. Export `initStageStepper()`, `resetStepper()`, `advanceStage()`, `markStageError()`, `markAllComplete()`. Each stage gets `onClick` handler (noop Phase A). ~100 lines. |
| T14 | **Create config-panel.js** | NEW: `gui/src/config-panel.js` | D:T7, D:T8, D:T10, D:T12 | Main config panel component. Fetches defaults from `/api/config`. Reads localStorage overrides. Renders 7 accordion groups × 45 params with appropriate widgets. Handles input events. Exports `initConfigPanel()`, `getConfigOverrides()`, `resetToDefaults()`. ~300 lines. |
| T15 | **Add config state to state.js** | `gui/src/state.js` | — | [P] New observables: `configDefaults` (from server), `configOverrides` (user changes), `analyzeVisits` (dropdown). ~10 lines. |
| T16 | **Update sgf-input.js — visits dropdown** | `gui/src/sgf-input.js` | D:T15 | Add `<select>` next to Analyze button with visits options (200/500/1000/2000/5000). Subscribe to `analyzeVisits` state. ~25 lines. |
| T17 | **Update bridge-client.js — config overrides** | `gui/src/bridge-client.js` | D:T15 | `streamEnrichment()`: include `config_overrides` from state in POST body. `analyzePython()`: accept visits from state instead of hardcoded 200. Add `getConfig()` function for `GET /api/config`. ~20 lines. |
| T18 | **Update app.js — wire everything** | `gui/src/app.js` | D:T13, D:T14, D:T16, D:T17 | Import `initStageStepper`, `initConfigPanel`. Replace `initPipelineBar()` call. Wire `getConfigOverrides()` into `handleEnrich()`. Wire `analyzeVisits` into `handleAnalyze()`. Add localStorage load/save. ~40 lines. |
| T19 | **Difficulty weight sliders logic** | `gui/src/config-panel.js` | D:T14 | Sum counter, normalize button, validation. If sum ≠ 100 on enrich → exclude weight overrides + show warning. ~40 lines (inside config-panel.js). |

---

## Group 4: Layout Restructuring

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T20 | **Restructure index.html — three-zone sidebar** | `gui/index.html` | D:T11 | Wrap sidebar contents in `.sidebar-fixed-top`, `.sidebar-scroll`, `.sidebar-fixed-bottom` divs. Remove `<header id="pipeline-bar">`. Add `<div id="stage-stepper">` and `<div id="config-panel">` in scroll zone. ~15 lines changed. |
| T21 | **Delete horizontal pipeline bar** | `gui/src/pipeline-bar.js`, `gui/css/styles.css` | D:T13, D:T20 | **Delete** `gui/src/pipeline-bar.js` entirely (dead code policy: "delete, don't deprecate"). Remove `.pipeline-pills`, `.pill-*`, `#pipeline-bar` CSS selectors. Remove `pipeline-bar.js` import from `app.js` (coordinated with T18). Git history preserves the file. ~50 lines removed CSS + ~100 lines deleted JS. |

---

## Group 5: localStorage Persistence

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T22 | **localStorage load/save** | `gui/src/config-panel.js`, `gui/src/app.js` | D:T14, D:T18 | On init: load from `enrichment-lab-config` key. On change: debounced save (500ms). Reset button clears key. Version field for future migration. ~30 lines. |
| T23 | **Accordion state persistence** | `gui/src/config-panel.js` | D:T22 | Remember which accordion group is expanded across reloads. ~10 lines. |

---

## Group 6: Documentation & Cleanup

| Task | Title | Files | Dependency | Notes |
|------|-------|-------|------------|-------|
| T24 | **Update AGENTS.md** | `AGENTS.md` | D:T18 | [P] Add stage-stepper.js, config-panel.js, bridge_config_utils.py entries. Update bridge.py API surface. |
| T25 | **Update GUI README** | `gui/README.md` | D:T18 | [P] Document config panel usage, localStorage schema, keyboard shortcuts. |
| T26 | **Update tool README** | `README.md` | D:T18 | [P] Mention config panel in capabilities section. |

---

## Execution Order (Critical Path)

```
Phase 1 — Foundation (all parallelizable):
  T1 [config override utility]
  T3 [GET /api/config]     [P]
  T5 [verify analyze visits] [P]
  T6 [CSS variables]       [P]
  T15 [config state]       [P]

Phase 2 — CSS Widgets (depends on T6):
  T7 [widget CSS]
  T8 [accordion CSS]       [P]
  T9 [stepper CSS]         [P]
  T10 [weight CSS]         [P]
  T11 [three-zone CSS]     [P]
  T12 [diff CSS]           [P]

Phase 3 — Backend Integration (depends on T1):
  T2 [config override tests]
  T4 [extend POST /api/enrich]

Phase 4 — GUI Components (depends on Phase 2+3):
  T13 [stage-stepper.js]
  T14 [config-panel.js]    [P]
  T16 [visits dropdown]    [P]
  T17 [bridge-client.js]   [P]

Phase 5 — Layout + Wiring (depends on Phase 4):
  T20 [restructure HTML]
  T18 [wire app.js]
  T21 [remove pill bar]
  T19 [weight slider logic]

Phase 6 — Persistence + Polish (depends on Phase 5):
  T22 [localStorage]
  T23 [accordion state]

Phase 7 — Documentation (parallelizable after Phase 5):
  T24 [AGENTS.md]          [P]
  T25 [GUI README]         [P]
  T26 [tool README]        [P]
```

---

## Effort Estimate Summary

| Group | Tasks | Est. Lines Changed/Created |
|-------|-------|---------------------------|
| Bridge API | T1–T5 | ~75 lines new, ~15 modified |
| CSS | T6–T12 | ~295 lines new CSS |
| GUI Components | T13–T19 | ~535 lines new JS |
| Layout | T20–T21 | ~15 modified HTML, ~50 removed CSS |
| Persistence | T22–T23 | ~40 lines |
| Docs | T24–T26 | ~60 lines |
| **Total** | **26 tasks** | **~1,020 new + ~80 modified** |

---

> **See also**:
> - [30-plan.md](./30-plan.md) — Architecture and design decisions
> - [15-research.md](./15-research.md) — Config param catalog (C-1 to C-45)
> - [15-research-ux.md](./15-research-ux.md) — CSS snippets for all widgets
