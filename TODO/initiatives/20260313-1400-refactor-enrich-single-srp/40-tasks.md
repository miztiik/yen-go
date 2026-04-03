# Tasks: enrich_single.py SRP Refactor — OPT-1 Stage Runner Pattern

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Selected Option:** OPT-1  
**Last Updated:** 2026-03-13

---

## Legend
- `[P]` = Parallelizable with other `[P]`-marked tasks in the same phase
- `depends:` = Must complete before this task starts
- `DoD:` = Definition of Done

---

## Phase 1: Foundation (Prerequisites)

| task_id | title | scope | depends | parallel | DoD |
|---------|-------|-------|---------|----------|-----|
| T1 | Create `analyzers/stages/` sub-package | Create `analyzers/stages/__init__.py` (empty) | — | [P] | Directory + `__init__.py` exist; imports resolve |
| T2 | Define protocols in `analyzers/stages/protocols.py` | Create `PipelineContext` dataclass, `StageResult`, `ErrorPolicy` enum, `EnrichmentStage` Protocol (~100 lines) | — | [P] | File passes lint; protocol is importable; field ownership matches plan §Field Ownership Table |
| T3 | Extract result builders to `analyzers/result_builders.py` | Move `_build_refutation_entries`, `_build_difficulty_snapshot`, `_compute_config_hash`, `_make_error_result`, `_build_partial_result` from enrich_single.py (lines 141–270) | T1 | [P] | Functions importable from new location; old private names removed from enrich_single.py; existing tests pass |
| T4 | Create stage runner in `analyzers/stages/stage_runner.py` | Implement `StageRunner` with auto-wrap for notify/timing/error policy (~70 lines) | T2 | — | `StageRunner.run_stage()` correctly wraps a mock stage with timing + notify + error policy; unit-testable by design |

---

## Phase 2: Extract Stage Modules

| task_id | title | scope | depends | parallel | DoD |
|---------|-------|-------|---------|----------|-----|
| T5 | Extract parse stage | Create `analyzers/stages/parse_stage.py` from enrich_single Steps 1-2 (lines 793–860). Class `ParseStage` implementing `EnrichmentStage`. Error policy: FAIL_FAST. | T2, T3 | [P] | Stage function runnable in isolation with mock context; enrich_single.py calls ParseStage instead of inline code; existing tests pass |
| T6 | Extract solve paths | Move `_run_position_only_path`, `_run_has_solution_path`, `_run_standard_path` to `analyzers/stages/solve_paths.py` (lines 276–720, ~445 lines). **Rename to `run_position_only_path`, `run_has_solution_path`, `run_standard_path`** (drop underscore prefix — these become the public API of solve_paths.py). Adapt to receive/return `PipelineContext`. | T2 | [P] | Three functions importable from new module by public names; enrich_single.py calls them from new location; existing AI-Solve tests pass |
| T7 | Extract query stage | Create `analyzers/stages/query_stage.py` from enrich_single Steps 3-4 (lines 935–1085). Class `QueryStage`. Error policy: FAIL_FAST. | T2 | [P] | Stage runnable; board state notifications preserved; existing query tests pass |
| T8 | Extract validation stage | Create `analyzers/stages/validation_stage.py` from enrich_single Steps 5-5.5 (lines 1086–1245). Class `ValidationStage`. Error policy: DEGRADE. | T2 | [P] | Stage runnable; tree validation + curated wrongs + nearby moves logic preserved; existing validation tests pass |
| T9 | Extract refutation stage | Create `analyzers/stages/refutation_stage.py` from enrich_single Step 6 (lines 1246–1392). Class `RefutationStage`. Error policy: DEGRADE. Includes escalation logic. | T2 | [P] | Stage runnable; escalation loop preserved; existing refutation tests pass |
| T10 | Extract difficulty stage | Create `analyzers/stages/difficulty_stage.py` from enrich_single Step 7 (lines 1393–1452). Class `DifficultyStage`. Error policy: DEGRADE (fallback to policy-only). | T2, T3 | [P] | Stage runnable; structural + policy-only fallback paths work; existing difficulty tests pass |
| T11 | Extract assembly stage | Create `analyzers/stages/assembly_stage.py` from enrich_single Step 8 (lines 1453–1600). Class `AssemblyStage`. Error policy: FAIL_FAST. Includes AC level matrix, goal inference, field wiring. | T2, T3 | [P] | Stage runnable; AC level logic matches original; goal inference preserved; existing assembly tests pass |
| T12 | Extract teaching stage | Create `analyzers/stages/teaching_stage.py` from enrich_single Steps 9-10 (lines 1601–1726). Class `TeachingStage`. Error policy: DEGRADE. Includes SGF writeback + final timings. | T2 | [P] | Stage runnable; technique tags, comments, hints, SGF writeback all produce same output; existing teaching tests pass |

---

## Phase 3: Rewrite Orchestrator

| task_id | title | scope | depends | parallel | DoD |
|---------|-------|-------|---------|----------|-----|
| T13 | Rewrite `enrich_single.py` as thin orchestrator | Replace 1,726-line body with ~120-150 lines: config init → PipelineContext → solve-path dispatch → StageRunner.run_pipeline() → return result. | T4, T5, T6, T7, T8, T9, T10, T11, T12 | — | File ≤ 150 lines; `enrich_single_puzzle()` delegates to stages; all existing tests pass |
| T14 | Update imports across lab | Update `cli.py`, `bridge.py`, `scripts/run_calibration.py`, **test files** (`tests/test_enrich_single.py` and any test importing internal helpers), and any other module that imports from `enrich_single.py`. Replace with imports from `result_builders.py` or `stages/`. **Update function names** in test files where solve path functions are referenced by old `_run_*` names (now `run_*`). | T13 | — | No import errors; `grep -r "from.*enrich_single import" tools/puzzle-enrichment-lab/` returns only `enrich_single_puzzle`; all test files updated to new import paths and function names |
| T15 | Delete dead code from enrich_single.py | Remove any functions that were extracted but accidentally left behind. Verify via grep. | T14 | — | No private helper functions remain in enrich_single.py; only orchestrator function + minimal imports |

---

## Phase 4: Documentation + Validation

| task_id | title | scope | depends | parallel | DoD |
|---------|-------|-------|---------|----------|-----|
| T16 | Update lab README | Add architecture section describing stage runner pattern, module map, and how to add new stages. | T15 | [P] | README has "Architecture" heading with module map diagram |
| T17 | Create stages README | Create `analyzers/stages/README.md` with brief description of pattern, stage interface, and extension guide. | T15 | [P] | File exists with stage protocol documentation |
| T18 | Run full test suite + lint | Execute `pytest tests/` and verify zero failures. Run linter. | T15 | — | All tests pass; zero lint warnings in modified files |
| T19 | Remove legacy enrich_single.py code | Final verification: confirm enrich_single.py ≤ 150 lines, no dead code, all imports clean. Delete any residual commented-out code. | T18 | — | File ≤ 150 lines; no `# TODO: remove` or commented-out blocks |

---

## Dependency Graph

```
Phase 1:  T1 ─┬─ T3 ──────────────────┐
          T2 ─┼─ T4                    │
              │                        │
Phase 2:      ├─ T5 [P] ──┐           │
              ├─ T6 [P] ──┤           │
              ├─ T7 [P] ──┤           │
              ├─ T8 [P] ──┤           │
              ├─ T9 [P] ──┤           │
              ├─ T10 [P] ─┤           │
              ├─ T11 [P] ─┤           │
              └─ T12 [P] ─┤           │
                           │           │
Phase 3:              T13 ←┘───────────┘
                       │
                      T14
                       │
                      T15
                       │
Phase 4:         T16 [P]  T17 [P]
                       │
                      T18
                       │
                      T19
```

---

## Task Summary

| Phase | Tasks | Parallel? | Estimated Files Touched |
|-------|-------|-----------|------------------------|
| 1: Foundation | T1-T4 | T1,T2,T3 parallel; T4 after T2 | 4 new files created |
| 2: Extract Stages | T5-T12 | All 8 parallelizable after T2 | 8 new files + 1 modified (enrich_single.py shrinks) |
| 3: Rewrite Orchestrator | T13-T15 | Sequential | 3+ files modified (enrich_single.py + imports) |
| 4: Documentation | T16-T19 | T16,T17 parallel | 2 docs + validation |
| **Total** | **19 tasks** | | **12 new files, ~5 modified files** |
