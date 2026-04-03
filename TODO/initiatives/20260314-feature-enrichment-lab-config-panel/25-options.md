# Options — Config Panel + Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Last Updated**: 2026-03-14

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 92 |
| `risk_level` | low |
| `research_invoked` | yes (2 artifacts: technical + UX) |

---

## Options Overview

| OPT-ID | Title | Approach | Complexity | G-8 Treatment |
|--------|-------|----------|------------|---------------|
| OPT-1 | **Phased Delivery: Core Panel → Re-Run** | Phase A delivers G-1 through G-7 (config panel + sidebar redesign + API). Phase B adds G-8 (per-stage re-run). Clear phase boundary. | Medium-High | Hard phase boundary |
| OPT-2 | **Monolithic Delivery: All Goals** | Single delivery of G-1 through G-8 together. Config panel, sidebar, API, and per-stage re-run in one pass. | High | Included |
| OPT-3 | **Config-First, Layout-Later** | Phase A: Config override API + config panel (no layout changes, keep horizontal pills). Phase B: Sidebar redesign + per-stage re-run. Defers the UI restructuring. | Medium | Deferred to Phase B |

---

## OPT-1: Phased Delivery (Core Panel → Re-Run)

### Approach
- **Phase A** (core): Config panel with all 45 params, sidebar redesign with vertical stepper replacing horizontal pills, bridge API extensions (`config_overrides`, `GET /api/config`), visits dropdown, localStorage persistence, difficulty weight sliders — delivers G-1 through G-7
- **Phase B** (re-run): PipelineContext serialization, `from_stage` field, re-run UI triggers in stepper — delivers G-8

### Benefits
| B-ID | Benefit |
|------|---------|
| B-1 | Phase A delivers 90% of user value (fast config iteration) without serialization complexity |
| B-2 | Phase A is self-contained and testable — no dependency on PipelineContext serialization correctness |
| B-3 | Phase B can be deferred, descoped, or handed to a different agent without blocking Phase A |
| B-4 | Aligns with governance recommendation (GV-3: explicit phase boundary for G-8) |

### Drawbacks
| D-ID | Drawback |
|------|----------|
| D-1 | Two delivery cycles — slightly more overhead in governance gates |
| D-2 | Phase B UI integration may require touching Phase A's stepper component |

### Risks
| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-1 | Phase B may never happen if Phase A satisfies user needs | Low | Acceptable — this validates the feature before investing in serialization |
| R-2 | Stepper UI in Phase A needs extensibility hooks for Phase B re-run triggers | Low | Design stepper with `onClick` handler per stage (noop in Phase A, re-run in Phase B) |

### Architecture & Policy Compliance
- Tools module isolation: ✅ Self-contained in `tools/puzzle-enrichment-lab/`
- No build step: ✅ Hand-written CSS, static files
- Config-driven: ✅ All values from `EnrichmentConfig` Pydantic model
- Pydantic validation: ✅ Server-side override validation

### Test Impact
- New tests: bridge API tests for `config_overrides` validation, `GET /api/config` response shape
- Modified tests: none (existing pipeline tests unaffected — config override is additive)
- GUI tests: manual (no automated GUI test infra exists)

### Rollback
- Phase A: Revert bridge API changes + remove GUI files/CSS. Horizontal pill bar restored.
- Phase B: Remove serialization utility + re-run API endpoint. Stepper click handlers become noop.

---

## OPT-2: Monolithic Delivery

### Approach
Single delivery pass implementing all 8 goals (G-1 through G-8) together. Config panel, sidebar redesign, bridge API, persistence, weight sliders, AND PipelineContext serialization + per-stage re-run UI.

### Benefits
| B-ID | Benefit |
|------|---------|
| B-3 | Complete feature delivered at once — no phasing overhead |
| B-4 | Stepper + re-run UI designed holistically (no retrofitting) |

### Drawbacks
| D-ID | Drawback |
|------|----------|
| D-3 | Larger blast radius — serialization bugs could delay the entire config panel |
| D-4 | PipelineContext serialization touches 28 fields, 6 of which need special handling |
| D-5 | Higher risk of scope creep — serialization edge cases (EnrichmentRunState.solution_tree_completeness type audit needed) |
| D-6 | Longer review cycle — governance must approve a larger package |

### Risks
| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-3 | Serialization bugs in AnalysisResponse/Position/SGFNode reconstruction block delivery | Medium | Unit tests for round-trip serialization of each Pydantic model |
| R-4 | `solution_tree_completeness` is typed as `Any` — runtime type audit needed during implementation | Medium | Add explicit type annotation + `.model_dump()` support |

### Rollback
Full revert of all changes — higher impact than phased approach.

---

## OPT-3: Config-First, Layout-Later

### Approach
- **Phase A**: Bridge API only (`config_overrides` field, `GET /api/config`), config panel in sidebar below existing controls, visits dropdown. **Keep horizontal pills unchanged.** Delivers G-1, G-4, G-5, G-6, G-7.
- **Phase B**: Sidebar redesign (vertical stepper, three-zone layout, per-stage re-run). Delivers G-2, G-3, G-8.

### Benefits
| B-ID | Benefit |
|------|---------|
| B-5 | Fastest time to usable config tuning — no layout restructuring in Phase A |
| B-6 | Lower risk Phase A — adding a panel below existing elements is simpler than restructuring sidebar |

### Drawbacks
| D-ID | Drawback |
|------|----------|
| D-7 | Phase A layout feels cramped — horizontal pills waste space above, config panel squeezes below in sidebar |
| D-8 | Phase B is a full sidebar restructure — harder retrofit than designing it right initially |
| D-9 | User explicitly requested removing horizontal pills and vertical stepper (Q4) — Phase A defers this |
| D-10 | Two restructuring passes on the same sidebar — more total work |

### Risks  
| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-5 | Config panel in cramped sidebar (with pills still in header) may not fit 45 params well | Medium | Reduce textarea rows from 6→4, but still tight |
| R-6 | User dissatisfaction — Q4 answer specifically asked for pill removal | High | User alignment risk |

---

## Comparison Matrix

| Criterion | OPT-1 (Phased) | OPT-2 (Monolithic) | OPT-3 (Config-First) |
|-----------|----------------|--------------------|--------------------|
| Delivers config tuning | Phase A | All at once | Phase A |
| Delivers sidebar redesign | Phase A | All at once | Phase B |
| Delivers per-stage re-run | Phase B | All at once | Phase B |
| Respects Q4 (remove pills) | ✅ Phase A | ✅ | ❌ Phase A defers |
| Blast radius | Low (Phase A) | High | Low (Phase A) |
| Total implementation effort | ~Similar to OPT-2 but parallelizable | Highest single batch | Highest total (two sidebar passes) |
| Retrofit risk | Low (stepper extensible by design) | None | Medium (Phase B restructures Phase A) |
| User satisfaction at Phase A | High (core features + new layout) | Highest (everything) | Medium (config only, old layout) |
| Governance risk | Low | Medium | High (Q4 misalignment) |

---

## Recommendation

**OPT-1 (Phased Delivery)** is the recommended option.

**Rationale**:
1. Delivers the highest-value features (config panel + sidebar redesign) in Phase A without serialization complexity risk
2. Respects the user's Q4 decision (remove horizontal pills) in the very first delivery
3. Governance panel (GV-3, GV-5, GV-6) recommended explicit phase boundary for G-8
4. Phase B is well-bounded and can proceed independently or be deferred
5. OPT-3 contradicts the user's explicit sidebar redesign request (Q4)
6. OPT-2 has unnecessary blast radius for a feature that's 90% config panel + layout

---

## Governance RC-2 Items (Addressed)

Per charter governance RC-2:
- **G-8 phase boundary**: OPT-1 makes this explicit — G-8 is Phase B
- **Config diff from defaults**: Added to OPT-1 Phase A as an enhancement — the `GET /api/config` endpoint provides defaults; GUI can compare localStorage values against server defaults and highlight diffs with a visual indicator (dimmed default text below slider, accent color when value ≠ default)

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Goals and constraints
> - [15-research.md](./15-research.md) — Technical feasibility backing each option
> - [15-research-ux.md](./15-research-ux.md) — UX patterns used in all options
> - [70-governance-decisions.md](./70-governance-decisions.md) — Charter approval conditions
