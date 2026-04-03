# Tasks: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Last Updated:** 2026-03-07 (design review revision)

---

## Phase I Task Breakdown (REVISED)

| T-ID | Title                                            | File(s)                                                                    | DD             | Depends On | [P] | Definition of Done                                                                                                                                     |
| ---- | ------------------------------------------------ | -------------------------------------------------------------------------- | -------------- | ---------- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T1   | Fix root_winrate derivation (CA-1)               | `analyzers/solve_position.py`                                              | DD-1           | —          | [P] | `root_winrate = analysis.root_winrate` replaces `_get_winrate(best_move_info)`. All existing tests pass.                                               |
| T2   | ~~Add position_scan_visits config~~              | ~~WITHDRAWN~~                                                              | ~~DD-4~~       | —          | —   | **WITHDRAWN** — DD-4 withdrawn. Position-only uses existing `tree_visits: 500`.                                                                        |
| T3   | Update `enrichment_tier` docstring               | `models/ai_analysis_result.py`                                             | DD-5, RC-9     | —          | [P] | Docstring clarifies tier-2 semantics.                                                                                                                  |
| T4   | Create `_build_partial_result()` helper          | `analyzers/enrich_single.py`                                               | DD-6           | T3         | —   | Fallback-only helper: assembles tier-1/2 result with policy-only difficulty + techniques + hints. Used ONLY when AI-Solve fails or engine unavailable. |
| T5   | Bug A: Enable full AI-Solve for position-only    | `analyzers/enrich_single.py`                                               | DD-2 rev, DD-9 | T1, T4     | —   | Remove `not ai_solve_active` guard at line 546. Position-only SGFs ALWAYS enter AI-Solve path. Wrap in try/except → tier-2 fallback (T4) on failure.   |
| T6   | Bug B: AI-Solve fails → tier-2 fallback          | `analyzers/enrich_single.py`                                               | DD-3           | T1, T4     | —   | Lines 595-604: replace hard-exit with fallback using `pre_analysis` data.                                                                              |
| T7   | Test: CA-1 root_winrate fix                      | `tests/test_solve_position.py`                                             | DD-1           | T1         | [P] | Mock verifying `analysis.root_winrate` used.                                                                                                           |
| T8   | Test: Position-only full AI-Solve success        | `tests/test_enrich_single.py`                                              | DD-2 rev       | T5         | —   | Mock engine → AI-Solve succeeds → tier=3, ac=2, solution tree present.                                                                                 |
| T9   | Test: Position-only AI-Solve fails → fallback    | `tests/test_enrich_single.py`                                              | DD-3, DD-7     | T5, T6     | —   | Mock AI-Solve returns no correct moves → tier=2, ac=0, no tree. Engine exception → tier=1, ac=0.                                                       |
| T10  | Test: Correct-moves-only SGF (no wrong branches) | `tests/test_enrich_single.py`                                              | —              | —          | [P] | Verify existing path works: KataGo generates refutations.                                                                                              |
| T11  | Audit test mocks for root_winrate consistency    | `tests/test_solve_position.py`                                             | DD-1           | T1         | —   | Ensure mocks have consistent `root_winrate`.                                                                                                           |
| T12  | Merge design decisions into global docs          | `docs/architecture/tools/katago-enrichment.md`, `docs/concepts/quality.md` | RC-16          | T5, T6     | [P] | DD-1..DD-9 as D32-D40. Tier↔ac mapping table. Determinism scope. FPU/KM-01 equivalence documented.                                                     |

---

## Dependency Graph (REVISED)

```
T1 (CA-1 fix) ──────────────────┐
T3 (docstring) ── T4 (helper) ──┼── T5 (Bug A: full AI-Solve) ── T8, T9
                                 └── T6 (Bug B: fallback)
T7 (CA-1 test)   [P] parallel
T10 (verify)     [P] parallel
T11 (audit)      depends on T1
T12 (docs)       depends on T5, T6
```

## Execution Order

1. **Phase 1** [P]: T1, T3, T7, T10 — independent
2. **Phase 2**: T4 (depends on T3)
3. **Phase 3** [P]: T5, T6 (depend on T1, T4)
4. **Phase 4** [P]: T8, T9, T11, T12 — tests + docs

## Compatibility Strategy

- **Backward compatibility:** Not required — `enrichment_tier` already exists
- **Legacy code removal:** Hard-exit blocks at lines 546-555 and 595-604 are removed
- **Config migration:** None — no new config keys (DD-4 withdrawn)

### Additional Phase I Task

| T-ID | Title                                               | File(s)                                                       | DD  | Depends On | [P] | Definition of Done                                                                                                                                                                                                                                                                                                                                                                      |
| ---- | --------------------------------------------------- | ------------------------------------------------------------- | --- | ---------- | --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T13a | Remove hardcoded `500` visits in `enrich_single.py` | `analyzers/enrich_single.py`, `config/katago-enrichment.json` | —   | —          | [P] | Lines 897, 901: replace hardcoded `500` with `get_effective_visits(config, mode_override=engine_manager.mode)`. Update `analysis_defaults.default_max_visits` from `200` to `500` in config JSON to match the intended quick-mode value (per changelog v1.1). The existing helper `get_effective_visits()` already handles the decision tree — `enrich_single.py` just wasn't using it. |

---

## Phase II Tasks (Tree Builder Improvements)

Approved by governance charter revision (2026-03-07). Execute after Phase I (T1-T12) is complete.

| T-ID | Title                                         | File(s)                                                                    | Depends On      | [P] | Definition of Done                                                                                                                                                                                                        |
| ---- | --------------------------------------------- | -------------------------------------------------------------------------- | --------------- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T13  | Merge design decisions into global docs       | `docs/architecture/tools/katago-enrichment.md`, `docs/concepts/quality.md` | T5, T6          | [P] | DD-1..DD-8 written as D32-D39 in katago-enrichment.md. Enrichment tier ↔ ac mapping table with examples added to quality.md. Determinism scope (RC-13) documented. Cross-references added.                                |
| T14  | Baseline branching metrics instrumentation    | `analyzers/solve_position.py`                                              | T1-T12 complete | —   | Add `BranchingMetrics` to `_build_tree_recursive`: per-depth branch count, per-depth winrate stdev of candidates, count of pruned moves that would pass at relaxed threshold.                                             |
| T15  | Collect baseline data on fixture set          | —                                                                          | T14             | —   | Run enrichment on 100+ representative puzzles. Record branching metrics. Establish baseline statistics.                                                                                                                   |
| T16  | Implement uncertainty-modulated branching     | `analyzers/solve_position.py`, `config.py`                                 | T15             | —   | In opponent-node loop: compute σ_w from moveInfos winrates. Adjust effective_min_policy _= (1 - uncertainty_dampening _ clamp(σ_w / σ_prior, 0, 1)). Two new config keys: uncertainty_dampening, uncertainty_stdev_prior. |
| T17  | A/B comparison on fixture set                 | —                                                                          | T15, T16        | —   | Run enrichment with and without uncertainty modulation. Compare: branch count, tree depth, compute cost, solution quality.                                                                                                |
| T18  | Edge case validation                          | `tests/`                                                                   | T16             | —   | Test that modulation does NOT suppress: distant refutations (throw-ins), ko threats, ladder escapes. Use targeted fixtures.                                                                                               |
| T19  | Configuration, calibration, and documentation | `config/katago-enrichment.json`, docs                                      | T16, T17, T18   | —   | Calibrate σ defaults per puzzle category. Update enrichment architecture docs.                                                                                                                                            |
