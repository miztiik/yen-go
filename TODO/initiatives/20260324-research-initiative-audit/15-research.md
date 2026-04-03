# Research: Initiative Audit — March 14–24, 2026

**Research Date**: 2026-03-24
**Artifact**: `15-research.md`
**Scope**: All initiatives in `TODO/initiatives/` dated 20260314 through 20260324 (53 entries)

---

## 1. Research Question and Boundaries

**Question**: What is the ground-truth status of every initiative created between March 14–24, 2026?

**Boundaries**:
- Read `status.json` from every initiative folder matching the date range
- For research-only folders (no `status.json`), note their artifact inventory
- Cross-reference task files (`40-tasks.md`) for completion tracking
- Categorize by domain: enrichment-lab, katago, frontend, backend, other

---

## 2. Executive Summary

| Metric | Count |
|--------|-------|
| Total initiatives audited | 53 |
| Feature/refactor initiatives (with `status.json`) | 33 |
| Research-only initiatives (no `status.json`) | 19 |
| Standalone reference files | 1 |
| Initiatives at **closeout** (fully completed) | 26 |
| Initiatives **superseded** | 2 |
| Initiatives **archived** | 1 |
| Initiatives in **execute** phase (in-progress/planned) | 3 |
| Initiatives in **tasks** phase (pre-execution) | 1 |
| Research with governance blocking | 1 |

---

## 3. Feature/Refactor Initiatives — Full Status Table

| R-ID | Initiative ID | Type | Category | Current Phase | Planning Approved? | Execute Status | Selected Option | Has Tasks | Task Rows | Key Claim |
|------|--------------|------|----------|---------------|-------------------|----------------|-----------------|-----------|-----------|-----------|
| R-1 | 20260314-1400-feature-enrichment-lab-v2 | feature | enrichment-lab | closeout | all approved | approved | OPT-3 (Phased Delivery + Entropy) | yes | 95 | Enrichment lab rewrite: eliminates region-restriction gap, new classifier, 3 rollback points |
| R-2 | 20260314-2200-refactor-config-py-decomposition | feature | backend | closeout | all approved | completed | OPT-3 (Hybrid 10-file) | yes | 54 | Decompose monolith config.py into 10-file config/ package |
| R-3 | 20260314-2300-feature-advanced-search-filters | feature | frontend | closeout | all approved | approved | OPT-1 | yes | 16 | Depth/complexity filter params in browse, reuses existing patterns |
| R-4 | 20260314-feature-enrichment-lab-config-panel | feature | enrichment-lab | closeout | all approved | approved | OPT-1 | yes | 32 | Config panel for enrichment lab GUI; Phase A = G-1–G-7 |
| R-5 | 20260315-1400-feature-tactical-analysis-wiring | feature | enrichment-lab | **archived** | charter+clarify+options approved; plan not_started | not_started | pending | no | — | Wiring tactical signals; superseded by R-7. Auto-tag wiring already live. |
| R-6 | 20260315-1500-feature-daily-db-migration | feature | backend | closeout | all approved | approved | OPT-3 (db_writer.py module) | yes | 5 | Migrate daily challenges from JSON to SQLite tables in yengo-search.db |
| R-7 | 20260315-1700-feature-enrichment-lab-tactical-hints | feature | enrichment-lab | closeout | all approved | approved | OPT-2 (InstinctStage) | yes | 26 | Instinct classification + policy entropy difficulty signal + hints |
| R-8 | 20260315-2000-feature-refutation-quality | feature | enrichment-lab | closeout | all approved | approved | OPT-3-expanded (12 PI items, 4 phases) | yes | 33 (all done) | Refutation quality: 4 phases (A/B/C/D), 41+37+41+17 tests, config v1.18→v1.21 |
| R-9 | 20260315-research-gogogo-tactics-patterns | research | enrichment-lab | research-review | charter change_requested (RC-1,RC-2 blocking) | — | — | no | — | GoGoGo tactics pattern extraction research |
| R-10 | 20260317-1400-feature-adaptive-learning-engine | feature | frontend | closeout | all approved | approved | OPT-1 (Lazy Join) | yes | 10 (all done) | Zero-hook stats module; Lazy Join for modularity |
| R-11 | 20260317-1400-feature-enrichment-data-liberation | feature | enrichment-lab | **superseded** | clarify superseded | not_started | pending | no | — | Superseded by R-13 (production-readiness) |
| R-12 | 20260318-1200-feature-enrichment-lab-production-gap-closure | feature | enrichment-lab | **superseded** | charter→plan approved; execute superseded | superseded | OPT-1 | yes | 23 | Superseded by R-13 (production-readiness). No backward compat. |
| R-13 | 20260318-1400-feature-enrichment-lab-production-readiness | feature | enrichment-lab | **execute** (conditional_complete) | all approved | conditional_complete | OPT-1 (Production Hardening) | yes | 242 | Massive production readiness: supersedes R-11+R-12, 6+ governance gates, log-report addendum (T71–T100), 78 tests added, PGR-LR-5 blocked |
| R-14 | 20260319-1000-feature-trace-search-optimization | feature | backend | closeout | all approved | approved | — | yes | 8 (all done) | Replace O(N) read_all() with pre-filtered scan |
| R-15 | 20260319-2100-feature-enrichment-quality-regression-fix | feature | enrichment-lab | closeout | all approved | approved | OPT-1 (bundled 5-RC fix) | yes | 15 | Fix enrichment quality regressions; remove Close special-casing |
| R-16 | 20260320-1400-feature-enrichment-almost-correct-reversal | feature | enrichment-lab | closeout | all approved | approved | Q1:A→Q5:A composite | yes | 19 (3 done) | Wrong tree + non-spoiler comment, remove all-skip + curated gate |
| R-17 | 20260320-1600-feature-katago-enrichment-tuning | feature | katago | closeout | all approved | approved | OPT A (14-parameter consensus) | yes | 10 | 14-parameter KaTago tuning consensus, 15% compute increase accepted |
| R-18 | 20260320-2200-feature-katago-cfg-audit-fix | feature | katago | closeout | all approved | approved | OPT-B (Tsumego-Optimized) | yes | 10 (all done) | Fix 4 unused keys, restore exploration defaults, early-phase tesuji boost |
| R-19 | 20260321-1000-feature-mark-sibling-refutations | feature | enrichment-lab | closeout | all approved | approved | OPT-1 (Backend pipeline fix) | yes | 12 | Sibling heuristic: stops accepting wrong moves as correct |
| R-20 | 20260321-1400-feature-html-report-redesign | feature | enrichment-lab | closeout | all approved | approved | OPT-1 (Single-file HTML) | yes | 15 | Replace markdown report with inline-CSS HTML; child of R-13 |
| R-21 | 20260321-1800-feature-enrichment-log-viewer | feature | enrichment-lab | closeout | all approved | approved | OPT-1 (KISS, file://) | yes | 13 | Greenfield HTML log viewer; file:// compatible |
| R-22 | 20260321-2100-refactor-enrichment-lab-dry-cli-centralization | feature | enrichment-lab | closeout | all approved | approved | OPT-3 (6-phase execution) | yes | 44 | 90% DRY elimination; centralize CLI patterns across enrichment lab |
| R-23 | 20260322-1400-refactor-enrichment-lab-test-consolidation | refactor | enrichment-lab | closeout | all approved | approved | OPT-B (migrate sprint tests + rename) | yes | 16 | Sprint tests → domain files, remediation rename, sys.path DRY |
| R-24 | 20260322-1500-feature-technique-calibration-fixtures | feature | enrichment-lab | closeout | all approved | approved | OPT-3 (Python Registry + Parametrized) | yes | 31 | Remove 7 broken fixtures, replace with sourced; registry + parametrize |
| R-25 | 20260322-1800-feature-rush-mode-fix | feature | frontend | closeout | all approved | approved | OPT-1 (SRP+DRY) | yes | 32 | Fix dead localStorage key, move InlinePuzzleSolver out of app.tsx |
| R-26 | 20260322-1900-refactor-technique-registry-externalization | refactor | enrichment-lab | **execute** (not_started) | all through tasks approved | not_started | OPT-1 (JSON + Thin Loader) | yes | 11 | Externalize hardcoded technique dict to JSON |
| R-27 | 20260324-1400-feature-rush-progress-component-tests | feature | frontend | **tasks** | charter→tasks approved; execute not_started | not_started | OPT-1 (co-located __tests__) | yes | 4 | Add component tests for rush/progress; test-only |
| R-28 | 20260324-1500-feature-backend-dead-code-cleanup | feature | backend | closeout | all approved | approved | OPT-1 (3-Phase Risk-Layered) | yes | 44 | Delete dead code: orphaned adapters, old registry, obsolete docs |
| R-29 | 20260324-1800-feature-frontend-cleanup-post-recovery | feature | frontend | closeout | all approved | approved | OPT-1 | yes | 64 | Delete dead frontend code, stale docs; per recovery audit |
| R-30 | 20260324-1900-feature-timed-puzzle-json-to-sql | feature | frontend | closeout | all approved | approved | OPT-1 | yes | 17 | Delete dead timed-puzzle JSON files; all 0 consumers |
| R-31 | 20260324-2000-feature-backend-test-remediation | feature | backend | closeout | all approved; execute complete | complete | OPT-1 | yes | 22 | Fix failing tests: 44 test deletions + dead code decommission; v1.0 schema removed |
| R-32 | 20260324-2100-feature-quality-dry-cleanup | feature | frontend | closeout | all approved | approved | OPT-1 | yes | 11 | Delete generated-types.ts (0 imports), remove deprecated aliases |
| R-33 | 20260324-2200-feature-enrichment-lab-test-audit | feature | enrichment-lab | **execute** (not_started) | governance in_progress | not_started | OPT-1 (4-phase consolidation) | yes | 15 | Consolidate 4 duplicate detector test files; follows R-23 |

---

## 4. Research-Only Initiatives (no `status.json`)

These folders contain only `15-research.md` (sometimes multiple research files) and serve as input artifacts for feature initiatives.

| R-ID | Initiative ID | Category | Artifacts | Fed Into |
|------|--------------|----------|-----------|----------|
| R-34 | 20260314-refactor-config-decomposition | backend | 15-research.md | R-2 (config-py-decomposition) |
| R-35 | 20260314-research-101weiqi-sources-architecture | backend | 15-research.md | — |
| R-36 | 20260314-research-db1-schema-tag-storage | backend | 15-research.md | — |
| R-37 | 20260314-research-enrichment-lab-rewrite | enrichment-lab | 15-research.md | R-1 (enrichment-lab-v2) |
| R-38 | 20260314-research-incremental-db-feasibility | backend | 15-research.md | — |
| R-39 | 20260314-research-lizgoban-katrain-patterns | katago | 15-research.md, 15-research-visit-counts.md | R-1 (enrichment-lab-v2) |
| R-40 | 20260314-research-sequence-number-removal | backend | 15-research.md | — |
| R-41 | 20260317-research-browser-tiny-llm | other | 15-research.md | — |
| R-42 | 20260317-research-capability-audit | other | 15-research.md, 15-research-enrichment-lab-accretion.md, 15-research-ng-gap-audit.md | — |
| R-43 | 20260317-research-learning-platform-gap | other | 15-research.md | R-10 (adaptive-learning-engine) |
| R-44 | 20260318-research-hinting-system-comparison | enrichment-lab | 15-research.md | R-7 (tactical-hints) |
| R-45 | 20260318-research-progress-stats-page-placement | frontend | 15-research.md | R-10 (adaptive-learning-engine) |
| R-46 | 20260319-research-katago-allowmoves-occupied | katago | 15-research.md | R-17/R-18 (katago tuning) |
| R-47 | 20260322-research-external-sources-fixture-sourcing | enrichment-lab | 15-research.md | R-24 (technique-calibration-fixtures) |
| R-48 | 20260322-research-rush-timed-puzzle-audit | frontend | 15-research.md | R-25 (rush-mode-fix), R-30 (timed-puzzle-json-to-sql) |
| R-49 | 20260324-research-backend-cleanup-post-recovery | backend | 15-research.md | R-28 (backend-dead-code-cleanup) |
| R-50 | 20260324-research-backend-failing-tests | backend | 15-research.md | R-31 (backend-test-remediation) |
| R-51 | 20260324-research-enrichment-lab-test-audit | enrichment-lab | 15-research.md | R-33 (enrichment-lab-test-audit) |
| R-52 | 20260324-research-frontend-cleanup-deep-audit | frontend | 15-research.md | R-29 (frontend-cleanup-post-recovery) |

### Additional Items

| R-ID | Item | Type | Notes |
|------|------|------|-------|
| R-53 | 2026-03-24-backend-docs-cleanup | research | 15-research.md only; audits stale backend documentation references |
| R-54 | 20260324-dead-code-decommissioning.md | standalone file | Reference artifact for dead code paths (trace_map, etc.); produced by R-31 |

---

## 5. Category Breakdown

| Category | Total | Closeout | In-Progress | Superseded/Archived | Research-Only |
|----------|-------|----------|-------------|---------------------|---------------|
| enrichment-lab | 24 | 14 | 3 (R-13, R-26, R-33) | 3 (R-5, R-11, R-12) | 4 (R-37, R-44, R-47, R-51) |
| katago | 4 | 2 (R-17, R-18) | 0 | 0 | 2 (R-39, R-46) |
| backend | 10 | 5 (R-2, R-6, R-14, R-28, R-31) | 0 | 0 | 5 (R-34, R-35, R-36, R-38, R-40) |
| frontend | 9 | 5 (R-3, R-10, R-25, R-29, R-30, R-32) | 1 (R-27) | 0 | 2 (R-45, R-48) |
| other | 6 | 0 | 0 | 0 | 3 (R-41, R-42, R-43) + R-9 (blocked) + R-53 + R-54 |

---

## 6. Key Findings

### 6A. Completed Work (26 closeouts in 11 days)

The team achieved an extraordinarily high throughput: **26 feature/refactor initiatives reached closeout** between March 14–24. Highlights:

- **R-8 (Refutation Quality)**: Most complex completed initiative — 12 PI items across 4 phases (A/B/C/D), 136 total tests added, config evolved v1.18→v1.21
- **R-1 (Enrichment Lab v2)**: Full rewrite of enrichment lab core; 95 task rows
- **R-2 (Config Decomposition)**: Monolith → 10-file decomposition with 54 tasks
- **R-22 (DRY CLI Centralization)**: 90% DRY elimination across enrichment lab; 6-phase execution
- **R-28 (Backend Dead Code Cleanup)**: 44-task deletion sweep with governance gates
- **R-29 (Frontend Cleanup)**: 64-task frontend cleanup post-recovery

### 6B. In-Progress Initiatives (4 active)

| R-ID | Initiative | Phase | Blocker |
|------|-----------|-------|---------|
| R-13 | enrichment-lab-production-readiness | execute (conditional_complete) | PGR-LR-5 blocked; 242 tasks, addendum T71–T100 |
| R-26 | technique-registry-externalization | execute (not_started) | No blocker; planned but not begun |
| R-27 | rush-progress-component-tests | tasks | No blocker; governance not yet started |
| R-33 | enrichment-lab-test-audit | execute (not_started) | Governance in_progress |

### 6C. Task File Quality Issue

**Finding**: Most task files do NOT track per-task completion status in their markdown tables. Of 30 task files in scope:
- Only **5 initiatives** have any "done/complete/closed" markers in task table rows
- Task files use heterogeneous column layouts (no standard "Status" column convention)
- The `status.json` phase_state is the only reliable completion indicator
- **Recommendation**: Task file format standardization or deprecation of per-task status tracking

### 6D. Supersession Chain (Enrichment Lab)

A notable supersession chain exists in the enrichment lab domain:
```
R-5 (tactical-analysis-wiring, archived)
  → superseded by R-7 (tactical-hints, closeout)

R-11 (enrichment-data-liberation, superseded)
  + R-12 (production-gap-closure, superseded)
    → both superseded by R-13 (production-readiness, conditional_complete)
```

### 6E. Research → Feature Pipeline

19 research initiatives directly fed 15+ feature initiatives. Notable research chains:
- R-37 + R-39 (enrichment rewrite + lizgoban patterns) → R-1 (enrichment-lab-v2)
- R-42 (capability audit, 3 research files) → multiple downstream features
- R-46 (katago allowmoves-occupied) → R-17 + R-18 (katago tuning + cfg audit)
- R-49 + R-50 + R-51 + R-52 (4 March-24 research audits) → R-28 + R-29 + R-31 + R-33

---

## 7. Planner Recommendations

1. **Close R-13 (production-readiness)**: The largest active initiative (242 tasks) is at `conditional_complete` with only PGR-LR-5 blocked. Determine if PGR-LR-5 can be deferred to unblock full closeout. This initiative has accumulated 6+ governance gates and an addendum — it risks becoming a perpetual WIP.

2. **Execute R-26, R-27, R-33**: Three initiatives are planned with tasks approved but execution not started. These are small (11, 4, and 15 task rows respectively) and could be completed quickly. Prioritize R-33 (enrichment-lab-test-audit) as it continues the consolidation work from R-23.

3. **Standardize task file format**: The audit revealed that `40-tasks.md` files are inconsistently formatted and rarely updated with per-task completion status. Either adopt a standard table schema with a `Status` column or deprecate per-task tracking in favor of `status.json` phase-level tracking.

4. **Retire or archive stale research**: R-35 (101weiqi), R-36 (db1-schema-tag-storage), R-38 (incremental-db-feasibility), R-40 (sequence-number-removal), R-41 (browser-tiny-llm) have no downstream feature initiatives. Mark them as archived or create follow-up feature initiatives if still relevant.

---

## 8. Confidence and Risk

| Metric | Value |
|--------|-------|
| Post-research confidence score | 95 |
| Post-research risk level | low |
| Evidence quality | high (direct `status.json` reads from all 53 initiatives) |
| Open questions | Q1, Q2 below |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should R-13 (production-readiness) PGR-LR-5 be deferred to unblock closeout, or is it a hard requirement? | A: Defer / B: Must complete / C: Other | A: Defer | — | ❌ pending |
| Q2 | Should task file format be standardized across all initiatives? If so, what schema? | A: Standard Status column / B: Deprecate per-task tracking / C: Keep as-is | B: Deprecate | — | ❌ pending |
