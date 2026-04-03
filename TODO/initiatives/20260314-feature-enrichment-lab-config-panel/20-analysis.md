# Analysis — Config Panel + Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Last Updated**: 2026-03-14

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 92 |
| `risk_level` | low |
| `research_invoked` | yes (2 artifacts: 15-research.md technical, 15-research-ux.md UX) |

---

## 1. Cross-Artifact Consistency

| F-ID | Check | Status | Notes |
|------|-------|--------|-------|
| F-1 | Charter goals (G-1–G-7) all covered by tasks | ✅ | G-1→T14; G-2→T13,T21; G-3→T11,T20; G-4→T1,T3,T4; G-5→T5,T16; G-6→T22,T23; G-7→T19 |
| F-2 | Must-hold constraints from governance all addressed | ✅ | MH-1(all 45 params)→T14; MH-2(stepper onClick)→T13; MH-3(config-diff)→T12,T14; MH-4(GET /api/config model_dump)→T3 |
| F-3 | Config-diff enhancement (RC-2) planned | ✅ | DD-6 in plan, T12 (CSS), T14 (JS logic) |
| F-4 | No tasks without a charter goal | ✅ | All tasks trace to G-1 through G-7 or documentation (G-implicit) |
| F-5 | Status.json consistent with phase | ✅ | phase: plan, options: approved, selected_option_id: OPT-1 |
| F-6 | Phase B (G-8) excluded from tasks | ✅ | No serialization or from_stage tasks in 40-tasks.md |
| F-7 | Governance decisions recorded | ✅ | Gates 1+2 in 70-governance-decisions.md |
| F-8 | Research findings consumed by plan | ✅ | DD-1 uses D-3 flow; DD-3 uses wireframe 4.1; DD-5 uses Section B catalog; CSS uses 4.2-4.5 |

---

## 2. Coverage Map

| Charter Goal | Plan Section | Task(s) | Test Coverage |
|-------------|-------------|---------|---------------|
| G-1: 45 config params | DD-5 (accordion groups) | T14 (config-panel.js) | Manual: verify all 45 render + override |
| G-2: Vertical stepper | DD-4 (stepper design) | T13, T21 | Manual: verify stage transitions |
| G-3: Three-zone sidebar | DD-3 (layout) | T11, T20 | Manual: verify scroll/fixed zones |
| G-4: Bridge API | DD-1, DD-2 (override) | T1, T2, T3, T4 | T2: automated unit tests (8 cases) |
| G-5: Visits dropdown | DD-8 | T5, T16 | Manual: verify dropdown → analyze |
| G-6: localStorage | DD-9 (schema) | T22, T23 | Manual: verify persist + reset |
| G-7: Weight sliders | DD-7 (sum=100) | T19 | Manual: verify sum counter, normalize, warning |
| Enhancement: config-diff | DD-6 | T12, T14 | Manual: verify modified badge + default label |

**Automated test coverage**: Only T2 (bridge config override) has automated tests. GUI components rely on manual testing — no automated GUI test infrastructure exists for the enrichment lab.

---

## 3. Unmapped Task Analysis

All 26 tasks are mapped to charter goals. No orphan tasks.

| Category | Count | Tasks |
|----------|-------|-------|
| Mapped to goals | 23 | T1–T23 |
| Documentation | 3 | T24–T26 (standard for any code change) |
| Unmapped | 0 | — |

---

## 4. Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|-----------|------------|--------|
| RE-1 | lateral | `gui/src/pipeline-bar.js` — removal | Low: module is imported by app.js; removal must be clean | T21 removes import from app.js + deletes/guts module | T21 | ✅ addressed |
| RE-2 | lateral | `gui/css/styles.css` — pill CSS removal | Low: `.pill-*` classes only used by pipeline-bar | T21 removes all `.pill-*` selectors | T21 | ✅ addressed |
| RE-3 | upstream | `config/__init__.py` — `load_enrichment_config()` | None: function is read-only, not modified | T3 calls it; T1 uses its output | T1, T3 | ✅ addressed |
| RE-4 | downstream | `analyzers/enrich_single.py` — `config` param | None: already supports optional `config` kwarg | T4 passes merged config through existing path | T4 | ✅ addressed |
| RE-5 | lateral | `gui/src/app.js` — import changes | Low: adding 2 new imports, removing 1 (pipeline-bar) | T18 handles all import changes | T18 | ✅ addressed |
| RE-6 | lateral | `gui/src/state.js` — new observables | None: additive change, no existing state affected | T15 adds 3 new atoms | T15 | ✅ addressed |
| RE-7 | downstream | `gui/index.html` — structure change | Low: removing `<header>`, restructuring `<aside>` | T20 is a focused HTML change (~15 lines) | T20 | ✅ addressed |
| RE-8 | upstream | `EnrichmentConfig.model_dump()` — size | Low: full dump is ~50KB JSON for 45 params; fine for single GET | Monitor in testing; cache client-side | T3 | ✅ addressed |
| RE-9 | lateral | Existing tests in `tests/` | None: no existing tests import bridge.py config logic | T2 creates new tests only | T2 | ✅ addressed |
| RE-10 | downstream | Phase B (G-8 re-run) — stepper extensibility | Low: T13 adds onClick noop handler per stage | Phase B executor will enhance onClick | T13 | ✅ addressed |

---

## 5. Severity-Based Findings

| F-ID | Severity | Finding | Resolution |
|------|----------|---------|------------|
| F-9 | **Info** | GUI has no automated test infrastructure — all GUI changes are manual testing | Acceptable for a developer tool. Document manual test checklist in T25. |
| F-10 | **Info** | Config panel at 300 lines is the largest new JS module | Manageable; well-structured with clear sections (fetch defaults, render groups, handle events, diff logic) |
| F-11 | **Low** | `model_dump()` response on `GET /api/config` may expose internal field names that differ from dotted-path convention | Verify field names match dotted-path keys in T2 integration tests |
| F-12 | **Low** | `pipeline-bar.js` removal (T21) must also update keyboard shortcut references in app.js if any exist | Verify during T18 (app.js wiring) |
| F-13 | **Info** | 295 lines of new CSS could make styles.css large (~600+ lines total) | Acceptable for a single-tool CSS file. Could split into `config-widgets.css` in Phase B if needed. |

---

## 6. Risk Register (Plan-Level)

| R-ID | Risk | Severity | Probability | Mitigation | Owner Task |
|------|------|----------|-------------|-----------|------------|
| R-1 | 45 params in 180px sidebar cramped | Low | Low | Accordion (1 open at a time); collapsible | T14, T8 |
| R-2 | Config merge produces unexpected results | Low | Low | Pydantic re-validates; T2 tests edge cases | T1, T2 |
| R-3 | Horizontal pill bar removal breaks layout | Low | Low | Stepper is a complete replacement; HTML restructure is surgical | T13, T20, T21 |
| R-4 | localStorage bloat from large overrides object | Very Low | Very Low | ~45 params × ~20 bytes each = ~1KB max | T22 |
| R-5 | CSS specificity conflicts between new widgets and existing styles | Low | Medium | New CSS uses `.config-*` namespace; no overlap with existing `.btn`, `.status-box` | T7–T12 |

---

> **See also**:
> - [30-plan.md](./30-plan.md) — Design decisions
> - [40-tasks.md](./40-tasks.md) — Task list
> - [00-charter.md](./00-charter.md) — Goals and constraints
