# Plan — Config Panel + Sidebar Redesign (Phase A)

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Selected Option**: OPT-1 (Phased Delivery)
**Scope**: Phase A — Goals G-1 through G-7 + config-diff enhancement
**Last Updated**: 2026-03-14

---

## Architecture Overview

### Current State
```
Browser ──POST /api/enrich {sgf}──> bridge.py ──> enrich_single_puzzle(sgf, engine, config=None)
                                                   └─> loads default EnrichmentConfig from file
```

### Target State (Phase A)
```
Browser ──POST /api/enrich {sgf, config_overrides}──> bridge.py
  │                                                      │
  │                                                      ├─> base = load_enrichment_config()
  │                                                      ├─> merged = apply_overrides(base, overrides)
  │                                                      └─> enrich_single_puzzle(sgf, engine, config=merged)
  │
  ├──GET /api/config──> bridge.py ──> config.model_dump() (for defaults + diff)
  │
  └──localStorage──> config state persistence + diff computation
```

### File Impact Map

| Area | Files Modified | Files Created |
|------|---------------|---------------|
| **Bridge API** | `bridge.py` | — |
| **GUI Layout** | `gui/index.html`, `gui/css/styles.css` | — |
| **GUI Components** | `gui/src/app.js`, `gui/src/sgf-input.js`, `gui/src/pipeline-bar.js`, `gui/src/bridge-client.js` | `gui/src/config-panel.js`, `gui/src/stage-stepper.js` |
| **GUI State** | `gui/src/state.js` | — |
| **Config Override** | — | `bridge_config_utils.py` (apply_overrides utility) |
| **Tests** | — | `tests/test_bridge_config.py` |

Total: ~8 files modified, ~3 files created.

---

## Design Decisions

### DD-1: Config Override Transport
Config overrides are sent as a flat JSON dict of dotted paths → values:
```json
{
  "config_overrides": {
    "visit_tiers.T1.visits": 1000,
    "refutations.delta_threshold": 0.05,
    "ai_solve.thresholds.t_good": 0.03,
    "deep_enrich.escalate_to_referee": false
  }
}
```
**Rationale**: Flat dotted-path dict is simpler than nested JSON. The bridge utility resolves paths and builds the nested Pydantic model. Only changed values are sent — omitted values use server defaults.

### DD-2: Config Merge Strategy
```python
def apply_config_overrides(base: EnrichmentConfig, overrides: dict) -> EnrichmentConfig:
    """Apply dotted-path overrides to a base config."""
    nested = unflatten_dotted_paths(overrides)  # {"visit_tiers": {"T1": {"visits": 1000}}}
    base_dict = base.model_dump()
    deep_merge(base_dict, nested)
    return EnrichmentConfig(**base_dict)  # Pydantic re-validates all constraints
```
**Rationale**: Re-constructing through `EnrichmentConfig(**merged)` triggers Pydantic validators (ge/le/type constraints). Invalid overrides → `ValidationError` → 422 to client.

### DD-3: Sidebar Three-Zone Layout
```
┌──────────────────────┐ ← Fixed zone (top)
│ SGF Input + Buttons   │    - Textarea (4 rows), Upload/Download, Enrich/Analyze/Cancel
│ Engine Status         │    - Visits dropdown next to Analyze
│ Analyze Visits: [▼]  │
├──────────────────────┤ ← Scroll zone (middle)
│ Stage Stepper         │    - 10 stages, vertical connected-dot pattern
│ Config Accordion      │    - 7 groups, collapsible, 45 params total
├──────────────────────┤ ← Fixed zone (bottom)
│ Run Info (pinned)     │    - run_id, trace_id, ac_level
└──────────────────────┘
```

### DD-4: Vertical Stage Stepper
Replaces `<header id="pipeline-bar">` (horizontal pills). Moves into the sidebar scroll zone. GitHub Actions–style connected dots with timing display. Each stage gets an `onClick` handler (noop in Phase A, reserved for Phase B re-run).

### DD-5: Config Accordion Groups (7 groups, 45 params)
| Group | Params | Source Config |
|-------|--------|--------------|
| Analysis & Engine | C-1 to C-9 (9 params) | `visit_tiers.*`, `deep_enrich.*`, `analysis_defaults.*` |
| Refutations | C-10 to C-21 (12 params) | `refutations.*`, `refutation_escalation.*` |
| AI-Solve / Solution Tree | C-22 to C-29 (8 params) | `ai_solve.thresholds.*`, `ai_solve.solution_tree.*` |
| Validation | C-30 to C-33 (4 params) | `tree_validation.*` |
| Difficulty | C-34 to C-40 (7 params) | `difficulty.structural_weights.*`, `difficulty.*` |
| Teaching | C-41 to C-43 (3 params) | `teaching.*` |
| Ko Analysis | C-44 to C-45 (2 params) | `ko_analysis.*` |

Default: all groups collapsed. Only one group expanded at a time (auto-collapse siblings).

### DD-6: Config Diff from Defaults
When a value differs from the server default (from `GET /api/config`):
- Slider thumb uses accent color (already default)
- Label shows `(modified)` badge in yellow
- Below the slider: "default: {value}" in dim text
- Reset button (×) per modified param returns to default

### DD-7: Difficulty Weight Sliders (sum=100)
- 5 independent sliders (solution_depth, branch_count, local_candidates, refutation_count, proof_depth)
- Sum counter at top of group: "Weights: 100%" in green, or "Weights: 87%" in red
- If sum ≠ 100 when Enrich is clicked: **don't send weight overrides** — server uses defaults. Show warning toast.
- Normalize button: redistributes proportionally to sum=100 (with rounding remainder to largest)

### DD-8: Visits Dropdown
Next to Analyze button, a `<select>` with options: 200, 500, 1000, 2000, 5000. Default: 200. Value passed to `analyzePython()` as `visits` parameter. Dropdown stored in localStorage.

### DD-9: localStorage Schema
```json
{
  "enrichment-lab-config": {
    "overrides": { "visit_tiers.T1.visits": 1000, ... },
    "analyze_visits": 500,
    "accordion_state": { "analysis": true, "refutations": false, ... },
    "version": 1
  }
}
```
On load: fetch `GET /api/config` for defaults, merge localStorage overrides, render widgets. Version field allows future schema migration.

### DD-10: CSS Strategy
Continue hand-written CSS with existing CSS custom properties. Add 2-3 new variables:
- `--bg-hover: rgba(255,255,255,0.03)` — accordion header hover
- `--accent-dim: rgba(79, 195, 247, 0.3)` — slider focus ring
- `--warning: #fbbf24` — modified badge, weight sum warning

Widget CSS from research (15-research-ux.md Section 4.4): slider, toggle, number input, dropdown, stepper, accordion. Approximately 200 lines of new CSS.

---

## Risks & Mitigations

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-1 | 45 params in 180-260px sidebar feel cramped | Low | Accordion (1 group open at a time). Collapsed: 7 headers × 28px = 196px. |
| R-2 | Slider precision at low width | Low | Clickable value converts to number input for exact entry |
| R-3 | Config merge edge cases (deeply nested dict) | Low | Pydantic re-validates after merge; integration tests cover dotted-path resolution |
| R-4 | Old pipeline-bar.js still has references if partially removed | Low | Full removal of horizontal pill bar + module; stepper replaces it completely |
| R-5 | localStorage stale if server config file changes | Low | On each load, fetch `GET /api/config` → compare versions → reset stale keys |

---

## Documentation Plan

| doc_action | file | why_updated |
|------------|------|-------------|
| update | `tools/puzzle-enrichment-lab/AGENTS.md` | New modules: config-panel.js, stage-stepper.js, bridge_config_utils.py. Updated bridge.py API surface. |
| update | `tools/puzzle-enrichment-lab/gui/README.md` | Document config panel usage, keyboard shortcuts, localStorage schema |
| update | `tools/puzzle-enrichment-lab/README.md` | Mention GUI config panel capability in tool overview |

---

> **See also**:
> - [25-options.md](./25-options.md) — OPT-1 selected
> - [15-research.md](./15-research.md) — 45 param catalog, stage map, API analysis
> - [15-research-ux.md](./15-research-ux.md) — Widget CSS, sidebar wireframe, accordion patterns
> - [40-tasks.md](./40-tasks.md) — Ordered task list
