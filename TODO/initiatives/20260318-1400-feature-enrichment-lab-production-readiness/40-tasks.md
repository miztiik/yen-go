# Tasks — OPT-1 Phased Activation (Amended)

> Initiative: `20260318-1400-feature-enrichment-lab-production-readiness`
> Last Updated: 2026-03-20
> Amendment: Doc structure fixed (three-tier compliance), governance gates added per phase, score recovery tasks added, parallelism maximized.
> Addendum: Log-Report tasks (T71-T90 + PGR-LR gates) added 2026-03-20 per GOV-PLAN-REVISE. Execution completed 2026-03-20 (T74-T92, T95-T100).

---

## Execution Governance Protocol

Each phase has a **Phase Gate Review (PGR)** before the next phase unlocks. The PGR:
1. Runs validation matrix checks for the phase
2. Updates `status.json` `phase_state` with pass/fail
3. Updates `70-governance-decisions.md` with phase gate result
4. Executor may self-approve PGR for Phases 0-2 (low/medium risk)
5. Phases 3-6 require governance panel invocation (feature activation + calibration)

| PGR | Gate | Approval | Unlocks |
|-----|------|----------|---------|
| PGR-0 | Phase 0 complete: models + config ready | Self-approve (executor) | Phase 1, Phase 2, Phase 3 (parallel start) |
| PGR-1 | Phase 1 complete: signals + observability wired | Self-approve (executor) | Phase 4 (feature activation) |
| PGR-2 | Phase 2 complete: diagnostics wired | Self-approve (executor) | Phase 5 (debug artifacts) |
| PGR-3 | Phase 3 complete: hinting consolidated | Self-approve (executor) | Phase 7 (docs — hinting section) |
| PGR-4a | Phase 4 sub-gate: Phase 1a-1c activation verified | Governance-Panel | Phase 4 Phase 2 activation |
| PGR-4b | Phase 4 sub-gate: Phase 2 budget verified | Governance-Panel | Phase 6 calibration |
| PGR-5 | Phase 5 complete: tests + debug artifacts | Self-approve (executor) | Phase 7 (docs — CLI section) |
| PGR-6 | Phase 6 complete: calibration + Phase 3 activation | Governance-Panel | Phase 7 (docs — quality/calibration section), Phase 8 |
| PGR-7 | Phase 7 complete: all docs written | Self-approve (executor) | Phase 8 (cleanup) |
| PGR-8 | Phase 8 complete: all tasks done | Governance-Panel (final closeout) | Initiative complete |

---

## Dependency-Ordered Task Graph

### Phase 0: Infrastructure & Foundation [NO DEPS — START IMMEDIATELY]

All tasks in Phase 0 can execute in parallel (PG-1).

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T1 | Add `quality_weights` section to `config/katago-enrichment.json` | `config/katago-enrichment.json` | — | [P] | not_started |
| T2 | Add `policy_entropy` + `correct_move_rank` fields to `DifficultySnapshot` model | `tools/puzzle-enrichment-lab/models/ai_analysis_result.py` | — | [P] | not_started |
| T3 | Create `PuzzleDiagnostic` Pydantic model | `tools/puzzle-enrichment-lab/models/diagnostic.py` (new) | — | [P] | not_started |
| T4 | Instantiate `ai_solve=AiSolveConfig()` default (currently `None`) | `tools/puzzle-enrichment-lab/config/__init__.py` | — | [P] | not_started |
| T5 | Populate `elo_anchor.calibrated_rank_elo` from KaTrain MIT data | `tools/puzzle-enrichment-lab/config/__init__.py`, data file | T4 | no | not_started |
| T9 | Extend `_build_yx()` with `a:`, `b:`, `t:` fields | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | — | [P] | not_started |
| T22 | Port backend hint test scenarios into lab test suite (TDD — red phase) | `tools/puzzle-enrichment-lab/tests/test_hint_generator.py` | — | [P] | not_started |
| T38 | Audit: which of 28 detector families have rotation tests | `tools/puzzle-enrichment-lab/tests/test_detectors_*.py` | — | [P] | not_started |
| T43 | Populate `golden-calibration/labels.json` with Cho answer keys | `tools/puzzle-enrichment-lab/tests/fixtures/golden-calibration/labels.json` | — | [P] | not_started |
| T66 | Inventory all enrichment-lab initiatives in `TODO/initiatives/` | `TODO/initiatives/` | — | [P] | not_started |
| **PGR-0** | **Phase Gate: models + config + foundation ready** | Run VM-3 (config parsing) | T1-T5, T9 | — | not_started |

### Phase 1: Signal Wiring + Observability [UNLOCKED BY PGR-0]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T6 | Wire `policy_entropy` + `correct_move_rank` from stage context → `AiAnalysisResult.difficulty` | `analyzers/stages/difficulty_stage.py`, `analyzers/enrich_single.py` | PGR-0 (T2) | [P] | not_started |
| T7 | Extend `BatchSummaryAccumulator` with entropy/rank aggregates + `goal_agreement` metric | `analyzers/observability.py`, `models/solve_result.py` | PGR-0 (T2) | [P] | not_started |
| T8 | Implement `_compute_qk()` function with config-driven weights | `analyzers/sgf_enricher.py` or new `analyzers/quality.py` | PGR-0 (T1, T2) | no | not_started |
| T10 | Extend `_build_yq()` with `qk:` field | `analyzers/sgf_enricher.py` | T8 | no | not_started |
| T11 | Add `goal_agreement` diagnostic to `DisagreementSink` | `analyzers/observability.py` | T7 | no | not_started |
| T12 | Tests: `_build_yx()` with all 8 fields (AC-1) | `tests/` | PGR-0 (T9) | [P] | not_started |
| T13 | Tests: `_build_yq()` with `qk` calculation (AC-2) | `tests/` | T10 | [P] | not_started |
| T14 | Tests: Config parsing for `quality_weights` (AC-3) | `tests/` | PGR-0 (T1) | [P] | not_started |
| T15 | Tests: Visit-count gate degradation (AC-4) | `tests/` | T8 | [P] | not_started |
| T16 | Tests: Signal propagation end-to-end (AC-7) | `tests/` | T6, T7 | no | not_started |
| **PGR-1** | **Phase Gate: all signals wired + tested** | Run VM-1 (full non-slow suite) | T6-T16 | — | not_started |

### Phase 2: Per-Puzzle Diagnostics [UNLOCKED BY PGR-0]

Phase 2 runs **in parallel with Phase 1** — both depend only on PGR-0.

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T17 | Wire `PuzzleDiagnostic` into `enrich_single()` pipeline | `analyzers/enrich_single.py` | PGR-0 (T3), T6 | no | not_started |
| T18 | Write per-puzzle diagnostic JSON to `.lab-runtime/diagnostics/` | `cli.py` | T17 | no | not_started |
| T19 | Extend batch accumulator to aggregate per-puzzle diagnostics | `analyzers/observability.py` | T17 | no | not_started |
| T20 | Tests: Diagnostic model serialization (AC-15) | `tests/` | PGR-0 (T3) | [P] | not_started |
| T21 | Tests: Batch diagnostic output (AC-16) | `tests/` | T18, T19 | no | not_started |
| **PGR-2** | **Phase Gate: diagnostics wired + tested** | Run VM-1, verify diagnostic output | T17-T21 | — | not_started |

### Phase 3: Hinting Consolidation [UNLOCKED BY PGR-0]

Phase 3 runs **in parallel with Phase 1 and Phase 2** — only depends on T22 (already in PG-1).

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T23 | Copy atari relevance gating logic (reimplemented using KataGo position data) | `analyzers/hint_generator.py` | T22 | no | not_started |
| T24 | Copy depth-gated Tier 3 coordinate hints | `analyzers/hint_generator.py` | T22 | no | not_started |
| T25 | Copy solution-aware fallback (`InferenceConfidence` + `infer_technique_from_solution()`) | `analyzers/hint_generator.py` or new helper | T22 | no | not_started |
| T26 | Copy `HintOperationLog` structured logging per tier | `analyzers/hint_generator.py` | T22 | no | not_started |
| T27 | Copy liberty analysis for capture-race/ko hints | `analyzers/hint_generator.py` | T22 | no | not_started |
| T28 | Tests: All ported capabilities pass (AC-6 — green phase) | `tests/test_hint_generator.py` | T23-T27 | no | not_started |
| T29 | Verify golden-5 fixtures produce same-or-better hints | `tests/` | T28 | no | not_started |
| **PGR-3** | **Phase Gate: hinting consolidated + tested** | Run VM-1 + VM-4 (golden-5) | T22-T29 | — | not_started |

### Phase 4: Feature Activation [UNLOCKED BY PGR-1]

Sequential sub-phases with governance gates between Phase 1c→Phase 2.

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T30 | Phase 1a: Enable PI-1, PI-3, PI-12 flags | Config defaults | PGR-1 (T5) | no | not_started |
| T31 | Tests: Phase 1a activation + **attribution assertions** (AC-5 partial) | `tests/` | T30 | no | not_started |
| T32 | Phase 1b: Enable PI-5, PI-6, suboptimal_branches | Config | T31 | no | not_started |
| T33 | Tests: Phase 1b budget delta < 20% + attribution | `tests/` | T32 | no | not_started |
| T34 | Phase 1c: Enable PI-10, PI-11 | Config | T33 | no | not_started |
| T35 | Tests: Phase 1c opponent-response phrases visible + attribution | `tests/` | T34 | no | not_started |
| **PGR-4a** | **Governance Gate: Phase 1a-1c verified** | Invoke Governance-Panel (review mode) | T30-T35 | — | not_started |
| T36 | Phase 2: Enable PI-2, PI-7, PI-8, PI-9 with budget monitoring | Config + observability | PGR-4a | no | not_started |
| T37 | Tests: Phase 2 budget ≤4x verified (C7) | `tests/` | T36 | no | not_started |
| T37b | Tests: Phase 2 **pairwise interaction tests** (PI-2×PI-7, PI-7×PI-8, PI-9×PI-2) | `tests/` | T36 | [P] with T37 | not_started |
| T37c | **Budget distribution benchmark**: 20-puzzle fixed set, assert p95 < 3.5× | `tests/` + benchmark script | T36 | [P] with T37 | not_started |
| **PGR-4b** | **Governance Gate: Phase 2 budget verified** | Invoke Governance-Panel (review mode) | T37, T37b, T37c | — | not_started |

### Phase 5: Test Coverage + Debug Artifacts [UNLOCKED BY PGR-2]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T39 | Add multi-orientation tests for ≥12 detector families (AC-8) | `tests/test_detectors_*.py` | T38 (Phase 0) | no | not_started |
| T40 | Add `--debug-export` CLI flag | `cli.py` | PGR-2 (T17) | [P] | not_started |
| T41 | Implement debug artifact export (trap moves + detector matrix) | `analyzers/` or new module | T40 | no | not_started |
| T42 | Tests: Debug export CLI (AC-9) | `tests/` | T41 | no | not_started |
| **PGR-5** | **Phase Gate: tests + debug artifacts done** | Run VM-1 + VM-2 | T39-T42 | — | not_started |

### Phase 6: Calibration + Phase 3 Activation [UNLOCKED BY PGR-4b]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T44 | Run calibration on 95 fixtures × 3 visit counts (AC-10) | Scripts + `.lab-runtime/calibration-results/` | PGR-4b, T8, T43 | no | not_started |
| T44b | **Partial calibration milestone**: first 30 fixtures, preliminary qk distribution | Scripts | T8, T43 | no | not_started |
| T45 | Human spot-check top/bottom 10% qk scores | Manual + validation report | T44 | no | not_started |
| T46 | Adjust `quality_weights` if calibration shows misalignment | `config/katago-enrichment.json` | T45 | no | not_started |
| T47 | Phase 3 activation: `instinct_enabled`, `elo_anchor`, PI-4 (if gates met) | Config | T44, PGR-4b | no | not_started |
| T48 | Tests: Phase 3 instinct accuracy ≥ 70%, macro-F1 ≥ 0.85 | `tests/` | T47 | no | not_started |
| **PGR-6** | **Governance Gate: calibration + Phase 3 verified** | Invoke Governance-Panel (review mode) | T44-T48 | — | not_started |

### Phase 7: Comprehensive Documentation [UNLOCKED BY PGR-1 + PGR-3 + PGR-5 + PGR-6]

Documentation follows **three-tier pattern** (≤3 levels). Content distributed across existing structure:

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T49 | Expand `docs/architecture/tools/katago-enrichment.md` — add pipeline stages section (12 stages) | `docs/architecture/tools/katago-enrichment.md` | PGR-1 | [P] | not_started |
| T50 | Expand architecture doc — add signal formulas section (all formulas English + math) | `docs/architecture/tools/katago-enrichment.md` | PGR-1 (T8) | [P] | not_started |
| T51 | Expand architecture doc — add refutation analysis section (4 phases, KM optimizations) | `docs/architecture/tools/katago-enrichment.md` | PGR-1 | [P] | not_started |
| T52 | Expand architecture doc — add decisions log section (what we decided, what we dropped) | `docs/architecture/tools/katago-enrichment.md` | PGR-6 | [P] | not_started |
| T53 | Expand architecture doc — add future work section (all deferred items) | `docs/architecture/tools/katago-enrichment.md` | PGR-6 | [P] | not_started |
| T54 | Update `docs/concepts/hints.md` — consolidated 3-tier hint system with lab architecture | `docs/concepts/hints.md` | PGR-3 (T28) | [P] | not_started |
| T55 | Update `docs/concepts/quality.md` — add qk definition, panel algorithm, calibration | `docs/concepts/quality.md` | PGR-6 (T8) | [P] | not_started |
| T56 | Update `docs/concepts/teaching-comments.md` — enrichment teaching comment assembly | `docs/concepts/teaching-comments.md` | PGR-1 | [P] | not_started |
| T57 | Merge `docs/reference/enrichment-config.md` INTO `docs/reference/katago-enrichment-config.md` (single canonical config ref) | `docs/reference/katago-enrichment-config.md` | PGR-1 (T1) | [P] | not_started |
| T58 | Update `docs/how-to/tools/katago-enrichment-lab.md` — new CLI flags, diagnostics, debug export | `docs/how-to/tools/katago-enrichment-lab.md` | PGR-5 (T18, T41) | [P] | not_started |
| T59 | Add supersession note to `docs/architecture/backend/hint-architecture.md` | `docs/architecture/backend/hint-architecture.md` | PGR-3 | [P] | not_started |
| T60 | Update `tools/puzzle-enrichment-lab/AGENTS.md` | `tools/puzzle-enrichment-lab/AGENTS.md` | PGR-3, PGR-1 | no | not_started |
| **PGR-7** | **Phase Gate: all docs written** | Run VM-7 (doc existence + cross-refs) | T49-T60 | — | not_started |

### Phase 8: TODO Cleanup + Player Validation + Closeout [UNLOCKED BY PGR-6 + PGR-7]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T67 | Extract future work items from inventoried initiatives into architecture doc future work section | `docs/architecture/tools/katago-enrichment.md` | T53, T66 | no | not_started |
| T68 | Archive completed/superseded initiatives to `docs/archive/initiatives/enrichment-lab/` | `TODO/initiatives/`, `docs/archive/` | T67 | no | not_started |
| T69 | Player validation: 20+ puzzles per qk tier reviewed (AC-11) | Validation report | PGR-6 (T44) | [P] | not_started |
| T70 | Update `status.json` — set all phases to `approved`, `execute: "complete"` | `status.json` | T48, T60, T68, T69 | no | not_started |
| **PGR-8** | **Governance Gate: Final closeout review** | Invoke Governance-Panel (closeout mode) | T67-T70 | — | not_started |

---

## Parallel Execution Map

```
TIME →
──────────────────────────────────────────────────────────────────────

Phase 0 (PG-1):  T1  T2  T3  T4  T9  T22  T38  T43  T66
                  │   │   │   │   │   │    │    │    │
                  └───┴───┴───┴───┘   │    │    │    │ ← all parallel
                       PGR-0          │    │    │    │
                         │            │    │    │    │
Phase 1:    ┌────────────┤            │    │    │    │
            T6 T7 T8→T10 T11         │    │    │    │
            T12 T13 T14 T15 T16      │    │    │    │ ← Phase 1/2/3
                  PGR-1               │    │    │    │   run PARALLEL
                    │                 │    │    │    │
Phase 2:    ┌───────┤     Phase 3:    │    │    │    │
            T17→T18 │    T23-T27→T28→T29   │    │    │
            T19 T20 │         PGR-3        │    │    │
            T21     │           │          │    │    │
            PGR-2   │           │          │    │    │
              │     │           │          │    │    │
Phase 4:      │  ┌──┘           │          │    │    │
              │  T30→T31→T32→T33→T34→T35   │    │    │
              │       PGR-4a               │    │    │
              │         │                  │    │    │
              │  T36→T37+T37b+T37c         │    │    │
              │       PGR-4b               │    │    │
              │         │                  │    │    │
Phase 5:   ┌──┘         │   Phase 6:      │    │    │
           T39 T40→T41  │   T44b→T44→T45→T46   │    │
           T42    PGR-5 │   T47→T48             │    │
              │         │   PGR-6               │    │
              │         │     │                 │    │
Phase 7:      └─────────┴─────┤                 │    │
              T49-T53 T54-T59 T60               │    │
                    PGR-7                       │    │
                      │                         │    │
Phase 8:              └─────────────────────────┘    │
              T67→T68  T69                           │
              T70                                    │
              PGR-8 ← FINAL                          │
```

---

## Parallel Groups (Revised)

| PG-ID | Tasks | Rule | When |
|-------|-------|------|------|
| PG-1 | T1 + T2 + T3 + T4 + T9 + T22 + T38 + T43 + T66 | Foundation: zero dependencies | Immediate start |
| PG-2 | Phase 1 (T6-T16) ∥ Phase 2 (T17-T21) ∥ Phase 3 (T22-T29) | Three work streams run concurrently after PGR-0 | After PGR-0 |
| PG-3 | T37 + T37b + T37c | Phase 2 activation tests run in parallel | After T36 |
| PG-4 | T49-T59 | Doc pages can be written in parallel | After their PGR dependencies |
| PG-5 | T69 ∥ T67-T68 | Player validation runs parallel with cleanup | After PGR-6 |

---

## Score Recovery Tasks (NEW)

| T-ID | Purpose | Recovers | Effort |
|------|---------|----------|--------|
| T37b | Pairwise interaction tests for Phase 2 (PI-2×PI-7, PI-7×PI-8, PI-9×PI-2) | CRT-2: +2 regression risk points | Small (3-4 test cases) |
| T37c | Budget distribution benchmark: 20-puzzle fixed set, assert p95 < 3.5× | CRT-4: +1 budget predictability point | Small (1 fixture set + assertion) |
| T44b | Partial calibration milestone: first 30 fixtures before full 95 | CRT-5: +1 calibration confidence point | Small (script subset) |

---

## Documentation Alignment (Amended)

### Three-Tier Compliance

All documentation follows `docs/tier/component/file.md` (≤3 levels):

| Previous (violating) | Amended (compliant) |
|---------------------|---------------------|
| `docs/architecture/tools/katago-enrichment/README.md` (4 levels) | `docs/architecture/tools/katago-enrichment.md` (3 levels — expand existing) |
| `docs/architecture/tools/katago-enrichment/signal-formulas.md` | Section within `katago-enrichment.md` |
| `docs/architecture/tools/katago-enrichment/config-reference.md` | `docs/reference/katago-enrichment-config.md` (merge with existing) |
| `docs/architecture/tools/katago-enrichment/hinting.md` | `docs/concepts/hints.md` (update existing) |
| `docs/architecture/tools/katago-enrichment/teaching-comments.md` | `docs/concepts/teaching-comments.md` (update existing) |
| `docs/architecture/tools/katago-enrichment/quality-assessment.md` | `docs/concepts/quality.md` (update existing) |

### Config Reference Consolidation

| Before | After |
|--------|-------|
| `docs/reference/enrichment-config.md` (ai_solve section) | Merged INTO `docs/reference/katago-enrichment-config.md` |
| `docs/reference/katago-enrichment-config.md` (visit tiers, refutation) | **Canonical** — single source of truth |
| Proposed `config-reference.md` (D-12) | **Dropped** — content merged into canonical file |

---

## Validation Matrix (Updated)

| VM-ID | Check | Command/Method | Owner Tasks |
|-------|-------|----------------|-------------|
| VM-1 | Enrichment lab non-slow suite | `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short` | T12-T16, T20-T21, T28-T29, T31-T37, T37b, T37c, T42 |
| VM-2 | Detector rotation regression | `pytest tools/puzzle-enrichment-lab/tests/test_detectors_*.py -q --no-header --tb=short` | T39 |
| VM-3 | Config parsing sanity | `pytest tools/puzzle-enrichment-lab/tests/test_config*.py -q --no-header --tb=short` | T1, T14 |
| VM-4 | Golden-5 integration (with KataGo) | `pytest tools/puzzle-enrichment-lab/tests/test_golden5.py -q --no-header --tb=short` | T29 |
| VM-5 | Calibration run (with KataGo) | Calibration script execution | T44, T44b |
| VM-6 | Player validation | Structured review report | T69 |
| VM-7 | Documentation completeness | File existence + cross-ref checks | T49-T60 |
| VM-8 | TODO cleanup verification | No enrichment-lab initiatives remain in TODO (except this one) | T68 |
| VM-9 | Phase 2 budget distribution | p95 < 3.5× on 20-puzzle benchmark | T37c |

---

## Deliverables (Updated)

| DEL-ID | Artifact | Produced By |
|--------|----------|-------------|
| DEL-1 | Extended YX/YQ with all signals + `qk` quality score | T8-T10 |
| DEL-2 | Consolidated hint generator with best of backend + lab | T23-T28 |
| DEL-3 | Per-puzzle structured diagnostics system | T17-T21 |
| DEL-4 | All 16 features activated (phased) | T30-T37, T47-T48 |
| DEL-5 | ≥12 detector families with rotation tests | T38-T39 |
| DEL-6 | Debug artifact export (CLI + bridge) | T40-T42 |
| DEL-7 | Calibration baseline with qk distribution | T43-T46, T44b |
| DEL-8 | Comprehensive enrichment documentation (expanded architecture doc + updated concept/reference docs) | T49-T60 |
| DEL-9 | Clean TODO directory; archived initiatives; future work preserved | T66-T68 |
| DEL-10 | Player validation report | T69 |
| DEL-11 | 8 governance phase gate reviews documented | PGR-0 through PGR-8 |

---

## Hinting Unification Confirmation

**G4 (Hinting consolidation) is IN SCOPE.** Tasks T22-T29 implement TDD. Backend `hints.py` marked as superseded (T59 adds note to `docs/architecture/backend/hint-architecture.md`).

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture and implementation details
> - [Charter](./00-charter.md) — Goals G1-G11, constraints, acceptance criteria
> - [Options](./25-options.md) — OPT-1 selected
> - [Analysis](./20-analysis.md) — Ripple effects, coverage checks

### Phase 1: Signal Wiring + Observability (Work Streams A+B)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T6 | Wire `policy_entropy` + `correct_move_rank` from stage context → `AiAnalysisResult.difficulty` | `tools/puzzle-enrichment-lab/analyzers/stages/difficulty_stage.py`, `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` | T2 | no | not_started |
| T7 | Extend `BatchSummaryAccumulator` with entropy/rank aggregates + `goal_agreement` metric | `tools/puzzle-enrichment-lab/analyzers/observability.py`, `tools/puzzle-enrichment-lab/models/solve_result.py` | T2 | [P] yes | not_started |
| T8 | Implement `_compute_qk()` function with config-driven weights | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` or new `tools/puzzle-enrichment-lab/analyzers/quality.py` | T1, T2 | no | not_started |
| T9 | Extend `_build_yx()` with `a:`, `b:`, `t:` fields | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | — | [P] yes | not_started |
| T10 | Extend `_build_yq()` with `qk:` field | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | T8 | no | not_started |
| T11 | Add `goal_agreement` diagnostic to `DisagreementSink` | `tools/puzzle-enrichment-lab/analyzers/observability.py` | T7 | no | not_started |
| T12 | Tests: `_build_yx()` with all 8 fields (AC-1) | `tools/puzzle-enrichment-lab/tests/` | T9 | [P] yes | not_started |
| T13 | Tests: `_build_yq()` with `qk` calculation (AC-2) | `tools/puzzle-enrichment-lab/tests/` | T10 | [P] yes | not_started |
| T14 | Tests: Config parsing for `quality_weights` (AC-3) | `tools/puzzle-enrichment-lab/tests/` | T1 | [P] yes | not_started |
| T15 | Tests: Visit-count gate degradation (AC-4) | `tools/puzzle-enrichment-lab/tests/` | T8 | [P] yes | not_started |
| T16 | Tests: Signal propagation end-to-end (AC-7) | `tools/puzzle-enrichment-lab/tests/` | T6, T7 | no | not_started |

### Phase 2: Per-Puzzle Diagnostics (Work Stream E)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T17 | Wire `PuzzleDiagnostic` into `enrich_single()` pipeline | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` | T3, T6 | no | not_started |
| T18 | Write per-puzzle diagnostic JSON to `.lab-runtime/diagnostics/` | `tools/puzzle-enrichment-lab/cli.py` | T17 | no | not_started |
| T19 | Extend batch accumulator to aggregate per-puzzle diagnostics | `tools/puzzle-enrichment-lab/analyzers/observability.py` | T17 | no | not_started |
| T20 | Tests: Diagnostic model serialization (AC-15) | `tools/puzzle-enrichment-lab/tests/` | T3 | [P] yes | not_started |
| T21 | Tests: Batch diagnostic output (AC-16) | `tools/puzzle-enrichment-lab/tests/` | T18, T19 | no | not_started |

### Phase 3: Hinting Consolidation (Work Stream C)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T22 | Port backend hint test scenarios into lab test suite (TDD — red phase) | `tools/puzzle-enrichment-lab/tests/test_hint_generator.py` | — | [P] yes | not_started |
| T23 | Copy atari relevance gating logic (reimplemented using KataGo position data) | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | T22 | no | not_started |
| T24 | Copy depth-gated Tier 3 coordinate hints | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | T22 | no | not_started |
| T25 | Copy solution-aware fallback (`InferenceConfidence` + `infer_technique_from_solution()`) | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` or new helper | T22 | no | not_started |
| T26 | Copy `HintOperationLog` structured logging per tier | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | T22 | no | not_started |
| T27 | Copy liberty analysis for capture-race/ko hints | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | T22 | no | not_started |
| T28 | Tests: All ported capabilities pass (AC-6 — green phase) | `tools/puzzle-enrichment-lab/tests/test_hint_generator.py` | T23-T27 | no | not_started |
| T29 | Verify golden-5 fixtures produce same-or-better hints | `tools/puzzle-enrichment-lab/tests/` | T28 | no | not_started |

### Phase 4: Feature Activation (Work Stream D)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T30 | Phase 1a: Enable PI-1, PI-3, PI-12 flags in config | `config/katago-enrichment.json` or lab config defaults | T5 | no | not_started |
| T31 | Tests: Phase 1a activation verification (AC-5 partial) | `tools/puzzle-enrichment-lab/tests/` | T30 | no | not_started |
| T32 | Phase 1b: Enable PI-5 (noise_scaling), PI-6 (forced_min_visits), suboptimal_branches | Config | T31 | no | not_started |
| T33 | Tests: Phase 1b budget delta < 20% | `tools/puzzle-enrichment-lab/tests/` | T32 | no | not_started |
| T34 | Phase 1c: Enable PI-10, PI-11 | Config | T33 | no | not_started |
| T35 | Tests: Phase 1c opponent-response phrases visible | `tools/puzzle-enrichment-lab/tests/` | T34 | no | not_started |
| T36 | Phase 2: Enable PI-2, PI-7, PI-8, PI-9 with budget monitoring | Config + observability | T35 | no | not_started |
| T37 | Tests: Phase 2 budget ≤4x verified (C7) | `tools/puzzle-enrichment-lab/tests/` | T36 | no | not_started |

### Phase 5: Test Coverage + Debug Artifacts (Work Streams F+G)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T38 | Audit: which of 28 detector families have rotation tests | `tools/puzzle-enrichment-lab/tests/test_detectors_*.py` | — | [P] yes | not_started |
| T39 | Add multi-orientation tests for ≥12 detector families (AC-8) | `tools/puzzle-enrichment-lab/tests/test_detectors_*.py` | T38 | no | not_started |
| T40 | Add `--debug-export` CLI flag | `tools/puzzle-enrichment-lab/cli.py` | T17 | [P] yes | not_started |
| T41 | Implement debug artifact export (trap moves + detector matrix) | `tools/puzzle-enrichment-lab/analyzers/` or new module | T40 | no | not_started |
| T42 | Tests: Debug export CLI (AC-9) | `tools/puzzle-enrichment-lab/tests/` | T41 | no | not_started |

### Phase 6: Calibration (Work Stream H)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T43 | Populate `golden-calibration/labels.json` with Cho answer keys | `tools/puzzle-enrichment-lab/tests/fixtures/golden-calibration/labels.json` | — | [P] yes | not_started |
| T44 | Run calibration on 95 fixtures × 3 visit counts (AC-10) | Scripts + `.lab-runtime/calibration-results/` | T8, T43 | no | not_started |
| T45 | Human spot-check top/bottom 10% qk scores | Manual + validation report | T44 | no | not_started |
| T46 | Adjust `quality_weights` if calibration shows misalignment | `config/katago-enrichment.json` | T45 | no | not_started |
| T47 | Phase 3 activation: `instinct_enabled`, `elo_anchor`, PI-4 (if gates met) | Config | T44, T37 | no | not_started |
| T48 | Tests: Phase 3 instinct accuracy ≥ 70%, macro-F1 ≥ 0.85 | `tools/puzzle-enrichment-lab/tests/` | T47 | no | not_started |

### Phase 7: Comprehensive Documentation (Work Stream I)

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T49 | Create `docs/architecture/tools/katago-enrichment/` directory + README.md index | `docs/architecture/tools/katago-enrichment/README.md` | T10 | [P] yes | not_started |
| T50 | Write pipeline-stages.md (12 stages explained) | `docs/architecture/tools/katago-enrichment/pipeline-stages.md` | T49 | [P] yes | not_started |
| T51 | Write signal-formulas.md (all formulas in English + math) | `docs/architecture/tools/katago-enrichment/signal-formulas.md` | T8, T49 | [P] yes | not_started |
| T52 | Write hinting.md (consolidated 3-tier system) | `docs/architecture/tools/katago-enrichment/hinting.md` | T28, T49 | [P] yes | not_started |
| T53 | Write teaching-comments.md | `docs/architecture/tools/katago-enrichment/teaching-comments.md` | T49 | [P] yes | not_started |
| T54 | Write difficulty-scoring.md | `docs/architecture/tools/katago-enrichment/difficulty-scoring.md` | T49 | [P] yes | not_started |
| T55 | Write technique-detection.md (28 detectors) | `docs/architecture/tools/katago-enrichment/technique-detection.md` | T49 | [P] yes | not_started |
| T56 | Write quality-assessment.md (q vs qk) | `docs/architecture/tools/katago-enrichment/quality-assessment.md` | T8, T49 | [P] yes | not_started |
| T57 | Write refutation-analysis.md (phases, KM optimizations) | `docs/architecture/tools/katago-enrichment/refutation-analysis.md` | T49 | [P] yes | not_started |
| T58 | Write decisions-log.md (why decisions were made, what was dropped) | `docs/architecture/tools/katago-enrichment/decisions-log.md` | T49 | [P] yes | not_started |
| T59 | Write future-work.md (all deferred items from research) | `docs/architecture/tools/katago-enrichment/future-work.md` | T49 | [P] yes | not_started |
| T60 | Write config-reference.md (all config keys) | `docs/architecture/tools/katago-enrichment/config-reference.md` | T1, T49 | [P] yes | not_started |
| T61 | Update `docs/concepts/quality.md` with qk definition | `docs/concepts/quality.md` | T8 | [P] yes | not_started |
| T62 | Update `docs/concepts/hints.md` with consolidated architecture | `docs/concepts/hints.md` | T28 | [P] yes | not_started |
| T63 | Update `docs/how-to/tools/katago-enrichment-lab.md` with new CLI, diagnostics | `docs/how-to/tools/katago-enrichment-lab.md` | T18, T41 | [P] yes | not_started |
| T64 | Update `docs/reference/enrichment-config.md` with quality_weights | `docs/reference/enrichment-config.md` | T1 | [P] yes | not_started |
| T65 | Update `tools/puzzle-enrichment-lab/AGENTS.md` | `tools/puzzle-enrichment-lab/AGENTS.md` | T28, T10 | no | not_started |

### Phase 8: TODO Cleanup + Archive (Work Stream J) + Player Validation

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T66 | Inventory all enrichment-lab initiatives in `TODO/initiatives/` | `TODO/initiatives/` | — | [P] yes | not_started |
| T67 | Extract future work items from each into `future-work.md` | `docs/architecture/tools/katago-enrichment/future-work.md` | T59, T66 | no | not_started |
| T68 | Archive completed/superseded initiatives to `docs/archive/initiatives/enrichment-lab/` | `TODO/initiatives/`, `docs/archive/` | T67 | no | not_started |
| T69 | Player validation: 20+ puzzles per qk tier reviewed (AC-11) | Validation report | T44 | [P] yes | not_started |
| T70 | Final governance review (Gate 6: plan review) | `70-governance-decisions.md`, `status.json` | T48, T65, T68, T69 | no | not_started |

---

## Parallel Groups

| PG-ID | Tasks | Rule |
|-------|-------|------|
| PG-1 | T1 + T2 + T3 + T4 + T9 + T22 + T38 + T43 + T66 | Foundation: all can start simultaneously (no dependencies) |
| PG-2 | T7 + T12 + T14 + T20 | Tests that only depend on models/config (Phase 0 complete) |
| PG-3 | T50-T60 | Documentation pages can be written in parallel once index exists (T49) |
| PG-4 | T61-T64 | Doc updates can parallel after their source tasks complete |

---

## Validation Matrix

| VM-ID | Check | Command/Method | Owner Tasks |
|-------|-------|----------------|-------------|
| VM-1 | Enrichment lab non-slow suite | `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short` | T12-T16, T20-T21, T28-T29, T31-T37, T42 |
| VM-2 | Detector rotation regression | `pytest tools/puzzle-enrichment-lab/tests/test_detectors_*.py -q --no-header --tb=short` | T39 |
| VM-3 | Config parsing sanity | `pytest tools/puzzle-enrichment-lab/tests/test_config*.py -q --no-header --tb=short` | T1, T14 |
| VM-4 | Golden-5 integration (with KataGo) | `pytest tools/puzzle-enrichment-lab/tests/test_golden5.py -q --no-header --tb=short` | T29 |
| VM-5 | Calibration run (with KataGo) | Calibration script execution | T44 |
| VM-6 | Player validation | Structured review report | T69 |
| VM-7 | Documentation completeness | File existence + cross-ref checks | T49-T65 |
| VM-8 | TODO cleanup verification | No enrichment-lab initiatives remain in TODO (except this one) | T68 |

---

## Deliverables

| DEL-ID | Artifact | Produced By |
|--------|----------|-------------|
| DEL-1 | Extended YX/YQ with all signals + `qk` quality score | T8-T10 |
| DEL-2 | Consolidated hint generator with best of backend + lab | T23-T28 |
| DEL-3 | Per-puzzle structured diagnostics system | T17-T21 |
| DEL-4 | All 16 features activated (phased) | T30-T37, T47-T48 |
| DEL-5 | ≥12 detector families with rotation tests | T38-T39 |
| DEL-6 | Debug artifact export (CLI + bridge) | T40-T42 |
| DEL-7 | Calibration baseline with qk distribution | T43-T46 |
| DEL-8 | Comprehensive enrichment documentation directory (≥12 pages) | T49-T65 |
| DEL-9 | Clean TODO directory; archived initiatives; future work preserved | T66-T68 |
| DEL-10 | Player validation report | T69 |

---

## Hinting Unification Confirmation

**G4 (Hinting consolidation) is IN SCOPE.** Per user directive (D7/Q11): "Copy backend hints.py into the lab. Combine the backend wins. NOT a separate initiative." Tasks T22-T29 implement this as TDD (red-green-refactor): port test scenarios first (T22), copy each capability (T23-T27), verify all pass (T28), validate against golden fixtures (T29). Backend `hints.py` is marked as superseded in documentation (T52, AC-14).

---

## Addendum: Log-Report Tasks (Added 2026-03-20)

> Source: GOV-PLAN-REVISE handover. Phases PGR-LR-0 through PGR-LR-6.
> Dependencies: Independent of Phases 0-8. Can execute after PGR-8 or in parallel with deferred work.

### PGR-LR-0: Governance Addendum Gate [PREREQUISITE]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T71 | Record Q17:A + Q18:C decisions in clarifications and status.json | `10-clarifications.md`, `status.json` | — | [P] | ✅ completed |
| T72 | Add PGR-LR phase gates to plan + tasks | `30-plan.md`, `40-tasks.md` | — | [P] | ✅ completed |
| T73 | Add change-magnitude blocked condition to governance decisions | `70-governance-decisions.md` | — | [P] | ✅ completed |
| **PGR-LR-0** | **Governance Gate: addendum artifacts approved** | Governance-Panel (plan mode re-review) | T71-T73 | — | ✅ approved |

### PGR-LR-1: Global Toggle + Precedence Contract [UNLOCKED BY PGR-LR-0]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T74 | Add `report_generation` section to `config/katago-enrichment.json` | `config/katago-enrichment.json` | PGR-LR-0 | no | ✅ completed |
| T75 | Implement `ReportToggleResolver` — precedence: CLI > env > profile > config | `tools/puzzle-enrichment-lab/report/toggle.py` (new) | T74 | no | ✅ completed |
| T76 | Tests: Precedence resolution (all 4 levels, edge cases) | `tools/puzzle-enrichment-lab/tests/test_report_toggle.py` (new) | T75 | no | ✅ completed |
| T77 | Add `--log-report` CLI flag to `enrich` and `batch` commands | `tools/puzzle-enrichment-lab/cli.py` | T75 | no | ✅ completed |
| T78 | Tests: CLI flag parsing and default matrix (lab ON, prod OFF) | `tools/puzzle-enrichment-lab/tests/test_cli_report.py` (new) | T77 | no | ✅ completed |
| **PGR-LR-1** | **Phase Gate: toggle + precedence tested** | Run report toggle + CLI tests | T74-T78 | — | ✅ approved |

### PGR-LR-2: Auto-Trigger Wiring [UNLOCKED BY PGR-LR-1]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T79 | Wire report generation to end of `enrich_single()` pipeline (non-blocking) | `tools/puzzle-enrichment-lab/cli.py` | PGR-LR-1 | no | ✅ completed |
| T80 | Wire report generation to end of batch pipeline (non-blocking) | `tools/puzzle-enrichment-lab/cli.py` | PGR-LR-1 | no | ✅ completed |
| T81 | Tests: Auto-trigger ON/OFF for single run | `tools/puzzle-enrichment-lab/tests/` | T79 | [P] | ✅ completed |
| T82 | Tests: Auto-trigger ON/OFF for batch run | `tools/puzzle-enrichment-lab/tests/` | T80 | [P] | ✅ completed |
| T83 | Tests: Reporter failure does NOT fail enrichment run | `tools/puzzle-enrichment-lab/tests/` | T79 | no | ✅ completed |
| **PGR-LR-2** | **Phase Gate: auto-trigger wired + non-blocking verified** | Run trigger + failure mode tests | T79-T83 | — | ✅ approved |

### PGR-LR-3: Markdown Report Engine [UNLOCKED BY PGR-LR-2]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T84 | Implement `LogReportGenerator` — markdown report with S1-S9 sections | `tools/puzzle-enrichment-lab/report/generator.py` (new) | PGR-LR-2 | no | ✅ completed |
| T85 | Implement log-to-report token extraction (deterministic timestamp reuse) | `tools/puzzle-enrichment-lab/report/token.py` (new) | PGR-LR-2 | [P] | ✅ completed |
| T86 | Implement request/response correlator from structured JSON log events | `tools/puzzle-enrichment-lab/report/correlator.py` (new) | PGR-LR-2 | [P] | ✅ completed |
| T87 | Tests: Markdown section completeness (S1-S9 present, S10 placeholder) | `tools/puzzle-enrichment-lab/tests/test_report_generator.py` (new) | T84 | no | ✅ completed |
| T88 | Tests: Token reuse (log filename → report filename deterministic coupling) | `tools/puzzle-enrichment-lab/tests/test_report_token.py` (new) | T85 | no | ✅ completed |
| T89 | Tests: Request/response correlation + unmatched accounting (data quality S9) | `tools/puzzle-enrichment-lab/tests/test_report_correlator.py` (new) | T86 | no | ✅ completed |
| T90 | Add remaining CLI flags: `--log-report-output`, `--log-report-filter-status`, `--log-report-min-requests`, `--log-report-include-glossary` | `tools/puzzle-enrichment-lab/cli.py` | T84 | no | ✅ completed |
| **PGR-LR-3** | **Phase Gate: markdown engine validated** | All report tests pass; no ASCII rendering path | T84-T90 | — | ✅ approved |

### PGR-LR-4: Production Boundary Contract [UNLOCKED BY PGR-LR-1, PARALLEL WITH PGR-LR-2/3]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T91 | Document backend-to-lab invocation contract (default OFF, explicit flag) | `docs/architecture/tools/katago-enrichment.md` | PGR-LR-1 | [P] | ✅ completed |
| T92 | Tests: Production profile resolves to OFF unless explicit CLI override | `tools/puzzle-enrichment-lab/tests/test_report_toggle.py` | T75, T76 | no | ✅ completed |
| **PGR-LR-4** | **Phase Gate: production boundary tested** | Integration contract documented + tested | T91-T92 | — | ✅ approved |

### PGR-LR-5: Governance-Blocked Magnitude Section [BLOCKED — awaits glossary approval]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T93 | Implement S10 change-magnitude levels section with approved glossary text | `tools/puzzle-enrichment-lab/report/generator.py` | Governance glossary approval | no | blocked |
| T94 | Tests: S10 section renders correctly with approved level definitions | `tools/puzzle-enrichment-lab/tests/test_report_generator.py` | T93 | no | blocked |
| **PGR-LR-5** | **Governance Gate: magnitude glossary approved** | Glossary text finalized + embedded in report | T93-T94 | — | blocked |

### PGR-LR-6: Validation + Docs + Closeout [UNLOCKED BY PGR-LR-3 + PGR-LR-4]

| T-ID | Title | Scope Files | Depends On | Parallel | Status |
|------|-------|-------------|------------|----------|--------|
| T95 | Update `docs/how-to/tools/katago-enrichment-lab.md` — log-report CLI usage, defaults, operator examples | `docs/how-to/tools/katago-enrichment-lab.md` | PGR-LR-3 | [P] | ✅ completed |
| T96 | Update `docs/architecture/tools/katago-enrichment.md` — log-report architecture section | `docs/architecture/tools/katago-enrichment.md` | PGR-LR-3 | [P] | ✅ completed |
| T97 | Add glossary governance note to `docs/concepts/` or canonical location | `docs/concepts/` | PGR-LR-3 | [P] | ✅ completed |
| T98 | Update `tools/puzzle-enrichment-lab/AGENTS.md` with report module | `tools/puzzle-enrichment-lab/AGENTS.md` | PGR-LR-3 | [P] | ✅ completed |
| T99 | Regression: no ASCII rendering path remains; no CSV options in CLI help | `tools/puzzle-enrichment-lab/tests/` | PGR-LR-3 | no | ✅ completed |
| T100 | Integration test: malformed log events reflected in data-quality section S9 | `tools/puzzle-enrichment-lab/tests/` | PGR-LR-3 | no | ✅ completed |
| **PGR-LR-6** | **Phase Gate: log-report validated + documented** | All tests pass; docs updated; operator examples present | T95-T100 | — | ✅ approved |

### Log-Report Parallel Execution Map

```
PGR-LR-0 (T71-T73) ← Governance approval
    │
PGR-LR-1 (T74-T78) ← Toggle + CLI
    │
    ├──── PGR-LR-2 (T79-T83) ← Auto-trigger        PGR-LR-4 (T91-T92) ← Production boundary
    │           │                                         │
    │     PGR-LR-3 (T84-T90) ← Markdown engine          │
    │           │                                         │
    │           └────────────────┬─────────────────────── ┘
    │                            │
    │                      PGR-LR-6 (T95-T100) ← Validation + docs
    │
    ├──── PGR-LR-5 (T93-T94) ← BLOCKED until governance glossary
```

### Log-Report Validation Matrix

| VM-ID | Check | Command/Method | Owner Tasks |
|-------|-------|----------------|-------------|
| VM-LR-1 | Toggle precedence suite | `pytest tools/puzzle-enrichment-lab/tests/test_report_toggle.py` | T76, T78, T92 |
| VM-LR-2 | Auto-trigger ON/OFF suite | `pytest tools/puzzle-enrichment-lab/tests/test_cli_report.py` | T81, T82, T83 |
| VM-LR-3 | Markdown report completeness | `pytest tools/puzzle-enrichment-lab/tests/test_report_generator.py` | T87, T89 |
| VM-LR-4 | Token coupling suite | `pytest tools/puzzle-enrichment-lab/tests/test_report_token.py` | T88 |
| VM-LR-5 | Correlation quality | `pytest tools/puzzle-enrichment-lab/tests/test_report_correlator.py` | T89 |
| VM-LR-6 | Non-blocking failure mode | `pytest -k "reporter_failure"` | T83 |
| VM-LR-7 | No ASCII/CSV regression | `pytest -k "no_ascii and no_csv"` | T99 |

### Log-Report Deliverables

| DEL-ID | Artifact | Produced By |
|--------|----------|-------------|
| DEL-LR-1 | Global report toggle with 4-level precedence resolver | T74-T78 |
| DEL-LR-2 | Non-blocking auto-trigger for enrich + batch | T79-T83 |
| DEL-LR-3 | Markdown report engine (S1-S9 sections, S10 placeholder) | T84-T90 |
| DEL-LR-4 | Production boundary integration contract (default OFF) | T91-T92 |
| DEL-LR-5 | Change-magnitude section (governance-gated) | T93-T94 |
| DEL-LR-6 | Operator documentation and architecture docs | T95-T98 |

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture and implementation details (Work Stream K)
> - [Charter](./00-charter.md) — Goals G1-G11, constraints, acceptance criteria
> - [Options](./25-options.md) — OPT-1 selected
> - [Analysis](./20-analysis.md) — Ripple effects, coverage checks
