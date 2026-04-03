# Execution Log — Refutation Tree Quality Phase A + Phase B + Phase C + Phase D

**Initiative**: `20260315-2000-feature-refutation-quality`
**Executor**: Plan-Executor (via Governance-Panel dispatch)
**Started**: 2026-03-15
**Last Updated**: 2026-03-16

## Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-1 | T1 | Config model fields: `ownership_delta_weight`, `score_delta_enabled`, `score_delta_threshold` in `RefutationsConfig`; `model_by_category` in `AiSolveConfig`; `use_opponent_policy` in `TeachingConfig` | `config/refutations.py`, `config/ai_solve.py`, `config/teaching.py` | ✅ (pre-existing) |
| EX-2 | T5 | `katago-enrichment.json` updated to v1.18 with all Phase A keys and changelog | `config/katago-enrichment.json` | ✅ (pre-existing) |
| EX-3 | T4 | PI-4: `get_model_for_level()` and `model_label_for_routing()` in `SingleEngineManager` | `analyzers/single_engine.py` | ✅ (pre-existing) |
| EX-4 | T4b | PI-10: `_assemble_opponent_response()`, `assemble_wrong_comment()` opponent params, `voice_constraints`, `opponent_response_templates` in JSON | `analyzers/comment_assembler.py`, `config/teaching-comments.json` | ✅ (pre-existing) |
| EX-5 | T2 | PI-1: `compute_ownership_delta()` helper + composite scoring in `identify_candidates()` | `analyzers/generate_refutations.py` | ✅ (pre-existing) |
| EX-6 | T3 | PI-3: Score delta rescue mechanism in `identify_candidates()` | `analyzers/generate_refutations.py` | ✅ (pre-existing) |
| EX-7 | T6 | Phase A tests: 39 tests in `test_refutation_quality_phase_a.py` (TS-1 ownership delta 8, TS-2 score delta 3, TS-3 model routing 6, TS-4 config parsing 6, TS-5 opponent-response 12, VP-3 compliance 4). Version assertion updates in `test_ai_solve_config.py`, `test_enrichment_config.py`. | `tests/test_refutation_quality_phase_a.py` (new), `tests/test_ai_solve_config.py`, `tests/test_enrichment_config.py` | ✅ |
| EX-8 | T7 | AGENTS.md updated: PI-1/PI-3/PI-4/PI-10 methods added to §3 Key Methods. Config keys documented in §5 Gotchas. Last-updated trigger line. | `AGENTS.md` | ✅ |
| EX-9 | RC-3 | Observability extension: Added `ownership_delta_used` (int) and `score_delta_rescues` (int) to `BatchSummary` model and `BatchSummaryAccumulator.record_puzzle()` with accumulation in `__init__`, wired into `emit()`. | `models/solve_result.py`, `analyzers/observability.py` | ✅ |
| EX-10 | RC-4 | Teaching comments test fix: Updated `test_pv_truncated_falls_back_to_default` assertion from `"wrong"` to `"opponent"` to match new default template "Opponent has a strong response." (T5 config change). | `tests/test_teaching_comments.py` | ✅ |

## Deviations

| dev_id | deviation | resolution |
|---|---|---|
| D-1 | T1-T5 and T2/T3 production code were already implemented before formal execution started | Codebase audit confirmed all implementations match plan spec. Task status updated from `not-started` to `✅ done`. |
| D-2 | RC-3 (observability extension) initially deferred to Phase B | Implemented in execution turn 2 (EX-9). All 8 observability/BatchSummary tests pass. |
| D-3 | Pre-existing test `test_pv_truncated_falls_back_to_default` broken by T5 default template change | Fixed in EX-10 — assertion updated to match new template. |

## Open Items

None — all Phase A items resolved.

---

## Phase B Execution Log

### Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---|---|---|---|---|
| L0 | T8a | `config/katago-enrichment.json` | None | ✅ merged |
| L1 | T8b, T9a, T10a, T11a | `tests/test_refutation_quality_phase_b.py` | L0 | ✅ merged |
| L2 | T16b | — (regression) | L1 | ✅ merged |
| L3 | T16c | `AGENTS.md`, `models/solve_result.py`, `analyzers/observability.py` | L2 | ✅ merged |

**Note**: L1-L4 all target the same test file → serialized into single lane L1.

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-11 | T8a | Update katago-enrichment.json to v1.19: 10 Phase B keys added (PI-2: visit_allocation_mode/branch_visits/continuation_visits, PI-5: noise_scaling/noise_base/noise_reference_area, PI-6: forced_min_visits_formula/forced_visits_k, PI-9: player_alternative_rate/player_alternative_auto_detect), changelog entry, version bump | `config/katago-enrichment.json` | ✅ |
| EX-12 | T8b | PI-2 adaptive visits tests (TS-8b): 8 tests — feature gate (fixed), adaptive mode, config parsing, absent-key backward compat | `tests/test_refutation_quality_phase_b.py` | ✅ |
| EX-13 | T9a | PI-5 noise scaling tests (TS-8): 9 tests — fixed mode, board-scaled (9×9/13×13/19×19), config parsing, absent-key | `tests/test_refutation_quality_phase_b.py` | ✅ |
| EX-14 | T10a | PI-6 forced visits tests (TS-9): 9 tests — formula verification, disabled/enabled, never-decreases invariant, config parsing, absent-key | `tests/test_refutation_quality_phase_b.py` | ✅ |
| EX-15 | T11a | PI-9 player alternatives tests (TS-7): 8 tests — must-hold #4 safeguard (rate=0.0), auto-detect position-only, manual override, config parsing, absent-key | `tests/test_refutation_quality_phase_b.py` | ✅ |
| EX-16 | — | Version assertion updates: 3 test files updated from "1.18" to "1.19" | `tests/test_refutation_quality_phase_a.py`, `tests/test_ai_solve_config.py`, `tests/test_enrichment_config.py` | ✅ |
| EX-17 | T16b | Phase B regression: enrichment lab 546 passed, 1 failed (pre-existing test_timeout_handling — requires live KataGo), 1 skipped. Backend 1936 passed, 0 failed, 44 deselected | — | ✅ |
| EX-18 | T16c | AGENTS.md Phase B update: trigger line, PI-2/PI-5/PI-6/PI-9 injection points and config keys in §5. opponent_response_emitted counter added to BatchSummary + BatchSummaryAccumulator. | `AGENTS.md`, `models/solve_result.py`, `analyzers/observability.py` | ✅ |

### Phase B Config Version

| Item | Before | After |
|---|---|---|
| Config version | 1.18 | 1.19 |
| New JSON keys | 0 | 10 |
| New tests | 0 | 37 |
| Total Phase B files modified | 0 | 7 |

### Deviations

| dev_id | deviation | resolution |
|---|---|---|
| D-4 | PI-2/PI-5/PI-6/PI-9 algorithm code was injected before formal Phase B execution | Verified by 16-codebase-audit.md. Feature gates ensure zero behavior change with current defaults. Phase B adds JSON keys + tests + docs. |

### Open Items

None — all Phase B tasks resolved.

---

## Phase C Execution Log

### Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---|---|---|---|---|
| L0 | T12a, T13a, T14a | `config/solution_tree.py`, `config/refutations.py` | None | ✅ merged |
| L1 | T12b, T13b, T14b | `analyzers/solve_position.py`, `analyzers/generate_refutations.py` | L0 | ✅ merged |
| L2 | T16d | `config/katago-enrichment.json` | L1 | ✅ merged |
| L3 | T12c, T13c, T14c | `tests/test_refutation_quality_phase_c.py` | L2 | ✅ merged |
| L4 | T16e | — (regression) | L3 | ✅ merged |
| L5 | T16f | `AGENTS.md` | L4 | ✅ merged |

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-19 | T12a | PI-7 config: `branch_escalation_enabled: bool = False`, `branch_disagreement_threshold: float = 0.10` in `SolutionTreeConfig` | `config/solution_tree.py` | ✅ |
| EX-20 | T13a | PI-8 config: `multi_pass_harvesting: bool = False`, `secondary_noise_multiplier: float = 2.0` in `RefutationsConfig` | `config/refutations.py` | ✅ |
| EX-21 | T14a | PI-12 config: `best_resistance_enabled: bool = False`, `best_resistance_max_candidates: int = 3` in `RefutationsConfig` | `config/refutations.py` | ✅ |
| EX-22 | T12b | PI-7 algorithm: branch-local disagreement escalation in `_build_tree_recursive()` opponent node loop. Compares policy prior vs search winrate, re-evaluates with 2x visits if disagreement > threshold. Gated by `query_budget.can_query()`. | `analyzers/solve_position.py` | ✅ |
| EX-23 | T13b | PI-8 algorithm: multi-pass harvesting in `generate_refutations()`. After initial `identify_candidates()`, runs secondary analysis with noise × `secondary_noise_multiplier`. Merges, deduplicates, caps at `candidate_max_count`. | `analyzers/generate_refutations.py` | ✅ |
| EX-24 | T14b | PI-12 algorithm: best-resistance in `generate_single_refutation()`. After getting opponent response, evaluates top N alternative responses by punishment signal `abs(1 - opp_wr - initial_wr)`, selects maximum. Zero additional KataGo queries — uses existing `move_infos`. | `analyzers/generate_refutations.py` | ✅ |
| EX-25 | T16d | JSON config v1.20: 6 Phase C keys added, version bump 1.19→1.20, changelog entry. | `config/katago-enrichment.json` | ✅ |
| EX-26 | T12c/T13c/T14c | Phase C tests: 28 tests in `test_refutation_quality_phase_c.py` — TestBranchEscalation (8), TestMultiPassHarvesting (9), TestBestResistance (7), TestPhaseCConfigParsing (4). | `tests/test_refutation_quality_phase_c.py` (new) | ✅ |
| EX-27 | — | Version assertion updates: 4 test files updated from "1.19" to "1.20" | `test_refutation_quality_phase_a.py`, `test_refutation_quality_phase_b.py`, `test_ai_solve_config.py`, `test_enrichment_config.py` | ✅ |
| EX-28 | T16e | Phase C regression: 182 passed (A+B+C combined), backend 1936 passed, 0 failed | — | ✅ |
| EX-29 | T16f | AGENTS.md: trigger line updated, PI-7/PI-8/PI-12 injection points and config keys in §5 | `AGENTS.md` | ✅ |

### Open Items

None — all Phase C tasks resolved.

---

## Phase D Execution Log

### Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---|---|---|---|---|
| L0 | T15a, T15b | `config/infrastructure.py` | None | ✅ merged |
| L1 | T16g | `config/katago-enrichment.json` | L0 | ✅ merged |
| L2 | T15c | `tests/test_refutation_quality_phase_d.py` | L0+L1 | ✅ merged |
| L3 | T16h | — (regression) | L2 | ✅ merged |
| L4 | T16i | `AGENTS.md` | L3 | ✅ merged |

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-30 | T15a | PI-11 config model: `surprise_weighting: bool = False` and `surprise_weight_scale: float = 2.0` added to `CalibrationConfig` in `config/infrastructure.py`. | `config/infrastructure.py` | ✅ |
| EX-31 | T15b | PI-11 algorithm: `compute_surprise_weight()` pure function in `config/infrastructure.py`. Computes `weight = 1 + scale * |T0_winrate - T2_winrate|`. Returns 1.0 when disabled (uniform weighting). | `config/infrastructure.py` | ✅ |
| EX-32 | T15c | PI-11 tests (TS-13): 17 tests in `test_refutation_quality_phase_d.py` — TestSurpriseWeightedCalibration (11 tests: disabled uniform, enabled high/zero/moderate surprise, scale=0 uniform, symmetry, min-weight-1.0 invariant, custom scale), TestPhaseDConfigParsing (6 tests: version 1.21, changelog, JSON keys, absent-key backward compat). | `tests/test_refutation_quality_phase_d.py` (new) | ✅ |
| EX-33 | T16g | JSON config v1.21: 2 Phase D keys added (`surprise_weighting`, `surprise_weight_scale`), version bump 1.20→1.21, changelog entry. | `config/katago-enrichment.json` | ✅ |
| EX-34 | — | Version assertion updates: 5 test files updated from "1.20" to "1.21" | `test_refutation_quality_phase_a.py`, `test_refutation_quality_phase_b.py`, `test_refutation_quality_phase_c.py`, `test_ai_solve_config.py`, `test_enrichment_config.py` | ✅ |
| EX-35 | T16h | Phase D regression: 17 Phase D tests passed, 199 combined phase tests passed, enrichment lab 2160 passed (15 pre-existing failures), backend 1941 passed (0 new failures) | — | ✅ |
| EX-36 | T16i | AGENTS.md: trigger line updated to Phase D, CalibrationConfig description expanded, `compute_surprise_weight()` documented, Phase D config keys (v1.21) added, PI-11 method description added. | `AGENTS.md` | ✅ |

### Phase D Config Version

| Item | Before | After |
|---|---|---|
| Config version | 1.20 | 1.21 |
| New JSON keys | 0 | 2 |
| New tests | 0 | 17 |
| Total Phase D files modified | 0 | 8 |

### Deviations

None — Phase D executed according to task graph.

### Open Items

None — all Phase D tasks resolved.

---

## Governance RC Fix Execution Log

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-37 | RC-1 | Refactored `_cached_raw_config` global mutable from `comment_assembler.py` to `config/teaching.py`. New `load_raw_teaching_config()` public function + `_cached_raw_teaching_config` module variable. Cache cleared by existing `clear_teaching_cache()`. Removed `_PROJECT_ROOT`, `json` import, `_load_raw_teaching_config()` from comment_assembler.py. Updated import to use `load_raw_teaching_config` from `config.teaching`. | `config/teaching.py`, `analyzers/comment_assembler.py` | ✅ |
| EX-38 | RC-1 | Test fixture cleanup: removed `ca._cached_raw_config = None` from Phase A test `_clear_caches` fixture — no longer needed since `clear_teaching_cache()` now clears the raw config cache. Fixed `test_vp3_no_forbidden_starts` in `test_comment_assembler.py` to import `load_raw_teaching_config` from `config.teaching` instead of old private `_load_raw_teaching_config`. | `tests/test_refutation_quality_phase_a.py`, `tests/test_comment_assembler.py` | ✅ |
| EX-39 | CRA-1 | Added `board_size: int = 19` parameter to `identify_candidates()` in `generate_refutations.py`. Updated both callers in `generate_refutations()` to pass `board_size=position.board_size`. This enables ownership delta to work correctly on 9×9 and 13×13 boards. | `analyzers/generate_refutations.py` | ✅ |
| EX-40 | MH-5 | AGENTS.md updated: PI-1 entry documents `board_size` parameter and position-derived size. Opponent-response composition documents `load_raw_teaching_config()` cache location in `config/teaching.py`. | `AGENTS.md` | ✅ |

### Deviations

None — RC fixes executed as specified by governance review.

---

## Phase B Governance RC Fix Execution Log

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-41 | RC-1 | Replaced tautological MH-4 safeguard test (`assert not (0.0 > 0)`) with behavioral test. New test calls `build_solution_tree()` via MockEngine with 3 high-policy candidates. Walks tree and asserts every player node has at most 1 child when `player_alternative_rate=0.0`. Test will fail if the `if alt_rate > 0` guard is weakened/removed. | `tests/test_refutation_quality_phase_b.py` | ✅ |
| EX-42 | RC-2 | Added adaptive mode + boost interaction note to AGENTS.md PI-2 entry. Documents that `visit_allocation_mode="adaptive"` overrides edge-case boosts (corner_visit_boost, ladder_visit_boost) by design. | `AGENTS.md` | ✅ |

### Deviations

None — RC fixes executed as specified by governance review.

---

## Phase C Governance RC Fix Execution Log

### Per-Task Completion Log

| ex_id | task_id | description | files_changed | status |
|---|---|---|---|---|
| EX-43 | RC-1 | **PI-7 disagreement metric fix (CRA-1)**: Replaced `abs(m_policy - child.winrate)` (policy prior vs search winrate — different scales, always triggers) with `abs(child.winrate - first_child_winrate)` (sibling winrate comparison — same unit, same scale). The first child has the highest policy prior; divergence from its search result is genuine disagreement. | `analyzers/solve_position.py` | ✅ |
| EX-44 | RC-2 | **PI-8 merge re-ranking fix (CRA-2)**: After merge+dedup of secondary candidates, added `candidates.sort(key=lambda m: m.policy_prior, reverse=True)` before `candidates[:candidate_max_count]` cap. Policy prior is analysis-independent (same model, same position), so it's a fair cross-analysis ranking criterion. Prevents systematic drop of high-policy secondary candidates. | `analyzers/generate_refutations.py` | ✅ |
| EX-45 | RC-4 | **DRY noise helper (CRB-2)**: Extracted `_calculate_effective_noise(overrides_cfg, board_size)` shared helper. Used by both PI-5 refutation query noise (main injection point) and PI-8 multi-pass secondary noise. Eliminated duplicate board-scaled noise calculation. Also fixed CRB-1: removed redundant `refutation_cfg = config.refutations if config else None` at PI-12 injection. | `analyzers/generate_refutations.py` | ✅ |
| EX-46 | RC-5 | **Per-puzzle query counter (MH-7)**: Added `max_queries_per_puzzle: int` field to `BatchSummary` model. Added `_max_queries_per_puzzle` tracking to `BatchSummaryAccumulator.__init__()`, `record_puzzle()`, and `emit()`. Provides compute monitoring before PI-7/PI-12 activation. | `models/solve_result.py`, `analyzers/observability.py` | ✅ |
| EX-47 | RC-3 | **Algorithm integration tests**: Added 13 tests to `test_refutation_quality_phase_c.py`: TestPI7DisagreementMetric (3), TestPI8MergeReRanking (2), TestPI12BestResistance (2), TestNoiseHelper (3), TestMaxQueriesPerPuzzle (3). Total: 41 tests (28 original + 13 new). | `tests/test_refutation_quality_phase_c.py` | ✅ |
| EX-48 | — | **AGENTS.md update**: PI-7 entry updated (sibling winrate comparison), PI-8 entry updated (re-sort + shared noise helper), MH-7 `max_queries_per_puzzle` observability documented. | `AGENTS.md` | ✅ |
| EX-49 | — | **Regression**: Phase C: 41 passed. Full enrichment lab: 2173 passed, 15 pre-existing failures. Backend unit: 1555 passed, 0 failed. No new failures. | — | ✅ |

### Deviations

None — all 5 RCs from Phase C governance review resolved as specified.
