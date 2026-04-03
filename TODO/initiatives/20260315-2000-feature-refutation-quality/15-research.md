# Research Brief: Phase A Completeness Audit + Phase B/C/D Codebase Readiness

> Initiative: `20260315-2000-feature-refutation-quality`
> Last Updated: 2026-03-15
> Research Scope: `tools/puzzle-enrichment-lab/` + `config/katago-enrichment.json`

---

## 1. Research Question and Boundaries

**Primary questions:**
1. Is Phase A (PI-1, PI-3, PI-4, PI-10) charter-complete with correct defaults, tests, docs, and observability?
2. What uncommitted Phase B code exists in the working tree? Is it correct, premature, or incomplete?
3. Where exactly would Phase C/D items land in the codebase?
4. What is the current test infrastructure state?

**Boundaries:** `tools/puzzle-enrichment-lab/` only. No frontend, no backend pipeline.

---

## 2. Part 1: Phase A Charter Compliance Audit

### 2.1 PI-1 Ownership Delta — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-1 | `compute_ownership_delta()` exists | ✅ | [generate_refutations.py](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L36) — 44-line function, handles None, flat/nested arrays, board_size bounds |
| R-2 | Composite scoring in `identify_candidates()` | ✅ | [generate_refutations.py](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L197) — Temperature path: `base_score *= (1 + composite)`. Policy-only path: same formula. Both gated by `ownership_weight > 0`. |
| R-3 | Config field `ownership_delta_weight` in `RefutationsConfig` | ✅ | [config/refutations.py](../../tools/puzzle-enrichment-lab/config/refutations.py#L155) — `Field(default=0.0, ge=0.0, le=1.0)` with PI-1 docstring |
| R-4 | Default = 0.0 (disabled) | ✅ | Pydantic default `0.0`, JSON has `"ownership_delta_weight": 0.0` |
| R-5 | Observability: `ownership_delta_used` in BatchSummary | ✅ | [solve_result.py](../../tools/puzzle-enrichment-lab/models/solve_result.py#L409) — `ownership_delta_used: int = Field(default=0)`. [observability.py](../../tools/puzzle-enrichment-lab/analyzers/observability.py#L130) — `self._ownership_delta_used` counter, `record_puzzle(ownership_delta_used=...)` |

### 2.2 PI-3 Score Delta — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-6 | `score_delta_enabled` and `score_delta_threshold` in config | ✅ | [config/refutations.py](../../tools/puzzle-enrichment-lab/config/refutations.py#L161) — Both fields with PI-3 docstrings, defaults False/5.0 |
| R-7 | Rescue mechanism in `identify_candidates()` | ✅ | [generate_refutations.py](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L239) — Score-delta rescue loop re-includes moves excluded by min_policy when `abs(root_score - score_lead) >= threshold`. With explanatory comment noting rescue is dormant when `candidate_min_policy=0.0`. |
| R-8 | Score delta in `generate_single_refutation()` | ✅ | [generate_refutations.py](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L387) — PI-3 complementary filter: when winrate delta < threshold but score delta ≥ threshold, generates score-based refutation. Falls through to suboptimal_branches as secondary. |
| R-9 | Observability: `score_delta_rescues` in BatchSummary | ✅ | [solve_result.py](../../tools/puzzle-enrichment-lab/models/solve_result.py#L413) — `score_delta_rescues: int`. [observability.py](../../tools/puzzle-enrichment-lab/analyzers/observability.py#L131) — Counter + accumulator wired. |
| R-10 | Defaults: enabled=False, threshold=5.0 | ✅ | Pydantic defaults match. JSON has `"score_delta_enabled": false, "score_delta_threshold": 5.0` |

### 2.3 PI-4 Model Routing — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-11 | `get_model_for_level()` in SingleEngineManager | ✅ | [single_engine.py](../../tools/puzzle-enrichment-lab/analyzers/single_engine.py#L76) — Resolves level→category→model via `model_by_category` routing table. Returns None when routing inactive/unmapped. |
| R-12 | `model_label_for_routing()` in SingleEngineManager | ✅ | [single_engine.py](../../tools/puzzle-enrichment-lab/analyzers/single_engine.py#L101) — Returns arch label for observability. Falls back to default model label. |
| R-13 | `model_by_category` in `AiSolveConfig` | ✅ | [config/ai_solve.py](../../tools/puzzle-enrichment-lab/config/ai_solve.py#L188) — `Field(default_factory=dict)` with PI-4 docstring |
| R-14 | Default: empty dict = no routing | ✅ | Pydantic default `dict()`. JSON has `"model_by_category": {}` |

### 2.4 PI-10 Opponent Policy Teaching — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-15 | `_assemble_opponent_response()` in comment_assembler.py | ✅ | [comment_assembler.py](../../tools/puzzle-enrichment-lab/analyzers/comment_assembler.py#L159) — Condition-keyed, 5 active conditions, 7 suppressed. Token substitution (`{opponent_color}`, `{!opponent_move}`), conditional dash rule (suppress when WM has `—`). |
| R-16 | `assemble_wrong_comment()` accepts opponent params | ✅ | [comment_assembler.py](../../tools/puzzle-enrichment-lab/analyzers/comment_assembler.py#L218) — Params: `opponent_move`, `opponent_color`, `use_opponent_policy`. Calls `_assemble_opponent_response()` when gated on, applies 15-word guard. |
| R-17 | `use_opponent_policy` in TeachingConfig | ✅ | [config/teaching.py](../../tools/puzzle-enrichment-lab/config/teaching.py#L33) — `Field(default=False)` with PI-10 docstring |
| R-18 | Voice constraints in teaching-comments.json | ✅ | `voice_constraints` block: `forbidden_starts`, `forbidden_phrases`, `allowed_warmth_conditions`, `max_words: 15` |
| R-19 | Opponent response templates in teaching-comments.json | ✅ | `opponent_response_templates`: 5 `enabled_conditions` (`immediate_capture`, `capturing_race_lost`, `self_atari`, `wrong_direction`, `default`), 5 templates |
| R-20 | Default: use_opponent_policy=False | ✅ | Pydantic default `False`. JSON has `"use_opponent_policy": false` |

### 2.5 Phase A Tests — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-21 | test_refutation_quality_phase_a.py exists | ✅ | [test_refutation_quality_phase_a.py](../../tools/puzzle-enrichment-lab/tests/test_refutation_quality_phase_a.py) |
| R-22 | TS-1 (PI-1 ownership): TestOwnershipDelta | ✅ | 8 tests covering: no data, identical, max flip, single flip, nested, short arrays, weight=0 baseline, weight≠0 boost |
| R-23 | TS-2 (PI-3 score): TestScoreDeltaFilter | ✅ | 5 tests: disabled default, config fields, JSON presence, rescue includes low-policy move, rescue skips when disabled |
| R-24 | TS-3 (PI-4 model): TestModelRouting | ✅ | 6 tests: default empty, JSON presence, empty routing returns None, active routing resolves, unmapped category, label routing default/active |
| R-25 | TS-4 (config): TestPhaseAConfigParsing | ✅ | 6 tests: version 1.18, all defaults correct, absent keys give defaults, v1.18 changelog presence |
| R-26 | TS-5 (PI-10 opponent): TestOpponentResponseComments | ✅ | 12 tests: gate off, gate on, suppressed, all 5 active, all 7 suppressed, dash rule (has/no dash), word count, all 12 pairings, token substitution |
| R-27 | VP-3 compliance: TestVP3Compliance | ✅ | 4 tests: forbidden starts, voice constraints, opponent templates, warmth conditions |
| R-28 | Total Phase A test count | ✅ | **41 tests** collected (pytest --co) |

### 2.6 Phase A AGENTS.md — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-29 | Header references Phase A | ✅ | Line 4: `Last updated: 2026-03-15 | Trigger: Refutation quality Phase A — PI-1 ownership delta, PI-3 score delta, PI-4 model routing, PI-10 opponent-response teaching comments` |
| R-30 | PI-1 documented | ✅ | Lines 159, 232, 237 — `compute_ownership_delta()`, composite scoring formula, weight=0.0 default |
| R-31 | PI-3 documented | ✅ | Lines 233, 238 — Score-delta rescue mechanism, complementary filter |
| R-32 | PI-4 documented | ✅ | Lines 163, 167, 234, 239 — `get_model_for_level()`, `model_label_for_routing()`, routing table |
| R-33 | PI-10 documented | ✅ | Line 170 — `_assemble_opponent_response()`, 5 active/7 suppressed conditions |
| R-34 | Phase A config summary | ✅ | Line 236 — All 5 config keys listed with PI IDs and defaults |

### 2.7 Phase A Config JSON — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-35 | Version is v1.18 | ✅ | `"version": "1.18"` |
| R-36 | Phase A keys present with correct defaults | ✅ | `ownership_delta_weight: 0.0`, `score_delta_enabled: false`, `score_delta_threshold: 5.0`, `model_by_category: {}`, `use_opponent_policy: false` |
| R-37 | v1.18 changelog entry | ✅ | Mentions PI-1, PI-3, PI-4, PI-10 with full descriptions |
| R-38 | Phase B keys NOT in JSON yet | ✅ | `forced_min_visits_formula: MISSING`, `forced_visits_k: MISSING`, `visit_allocation_mode: MISSING`, `branch_visits: MISSING`, `continuation_visits: MISSING`, `player_alternative_rate: MISSING`, `player_alternative_auto_detect: MISSING`, `noise_scaling: MISSING`, `noise_base: MISSING`, `noise_reference_area: MISSING` |

### 2.8 Phase A Observability — ✅ COMPLETE

| ID | Check | Status | Evidence |
|----|-------|--------|----------|
| R-39 | `ownership_delta_used` in BatchSummary model | ✅ | [solve_result.py L409](../../tools/puzzle-enrichment-lab/models/solve_result.py#L409) — `int`, default 0, PI-1 docstring |
| R-40 | `score_delta_rescues` in BatchSummary model | ✅ | [solve_result.py L413](../../tools/puzzle-enrichment-lab/models/solve_result.py#L413) — `int`, default 0, PI-3 docstring |
| R-41 | `record_puzzle()` accepts kwargs | ✅ | [observability.py L147-148](../../tools/puzzle-enrichment-lab/analyzers/observability.py#L147) — `ownership_delta_used: bool = False`, `score_delta_rescues: int = 0` |
| R-42 | Accumulator wiring | ✅ | [observability.py L186-188](../../tools/puzzle-enrichment-lab/analyzers/observability.py#L186) — Counter increments, summary emission at L241-242 |

### Phase A Verdict: **✅ ALL 42 CHECKS PASS — Phase A is charter-complete.**

---

## 3. Part 2: Uncommitted Phase B Code Assessment

### 3.1 Working Tree Diff Summary

`git diff --name-only -- tools/puzzle-enrichment-lab/` returns **~80 modified files**. However, for Phase B specifically:

| File | Diff Size | Phase B Content? |
|------|-----------|-----------------|
| `analyzers/generate_refutations.py` | +294/-33 lines | Yes — PI-1, PI-3, PI-5, PI-6, T18 (tenuki, overrides, score enrichment) |
| `analyzers/solve_position.py` | +184/-33 lines | Yes — PI-2, PI-9, Benson gate, SgfNode→SGFNode refactor |
| `config/refutations.py` | 0 diff (clean) | Phase B fields **already committed**: PI-5 (noise_scaling/noise_base/noise_reference_area), PI-6 (forced_min_visits_formula/forced_visits_k) |
| `config/solution_tree.py` | 0 diff (clean) | Phase B fields **already committed**: PI-2 (visit_allocation_mode/branch_visits/continuation_visits), PI-9 (player_alternative_rate/player_alternative_auto_detect) |
| `analyzers/stages/solve_paths.py` | 0 diff (clean) | PI-9 auto-detect logic **already committed** |

### 3.2 Detailed Uncommitted Change Assessment

#### In `generate_refutations.py` (uncommitted, +294 lines):

| ID | Change | Phase | Correct? | Notes |
|----|--------|-------|----------|-------|
| R-43 | `compute_ownership_delta()` function added | A (PI-1) | ✅ Correct | Handles flat/nested, bounds checking, returns max absolute delta |
| R-44 | `import math` added | A | ✅ Correct | Needed for temperature scoring |
| R-45 | Temperature-weighted scoring (T16B) in `identify_candidates()` | A (existing feature) | ✅ Correct | KaTrain-style `exp(-temp * points_lost) * policy`, replaces simple sort |
| R-46 | PI-1 ownership composite in candidate scoring | A (PI-1) | ✅ Correct | Both temperature and policy_only paths handle ownership_weight > 0 |
| R-47 | PI-3 score-delta rescue in `identify_candidates()` | A (PI-3) | ✅ Correct | Re-includes low-policy moves when score delta exceeds threshold. Dormancy comment is accurate. |
| R-48 | Score delta enrichment in `_enrich_curated_policy()` | A (PI-3) | ✅ Correct | `score_lookup` + `ref.score_delta` enrichment for curated refutations |
| R-49 | `initial_score`, `allowed_moves`, `override_settings` params | Mixed (A+B) | ✅ Correct | `initial_score` needed for PI-3, `allowed_moves` + `override_settings` for T17/T18 |
| R-50 | PI-6 forced minimum visits in `generate_single_refutation()` | **B (PI-6)** | ✅ Correct | `nforced(c) = sqrt(k * P(c) * visits)`. Gated by `forced_min_visits_formula=False`. Only boosts, never reduces. |
| R-51 | PI-3 in `generate_single_refutation()` score-based fallback | A (PI-3) | ✅ Correct | Score delta as complementary gate before suboptimal_branches |
| R-52 | T18B tenuki detection | Pre-existing feature | ✅ Correct | Manhattan distance check, flagging only (not rejection) |
| R-53 | `score_delta` and `tenuki_flagged` in Refutation result | Pre-existing | ✅ Correct | New output fields |
| R-54 | PI-5 board-size-scaled noise in `generate_refutations()` | **B (PI-5)** | ✅ Correct | `effective_noise = base * ref_area / legal_moves`. Gated by `noise_scaling == "board_scaled"`. Default "fixed" = no change. |
| R-55 | T17 puzzle-region allowMoves | Pre-existing | ✅ Correct | Uses entropy_roi or fallback to puzzle_region_moves |
| R-56 | `entropy_roi` param added to `generate_refutations()` | Pre-existing | ✅ Correct | Frame adapter integration |

#### In `solve_position.py` (uncommitted, +184 lines):

| ID | Change | Phase | Correct? | Notes |
|----|--------|-------|----------|-------|
| R-57 | `import time` added | B (Benson gate timing) | ✅ Correct | For gate elapsed_ms logging |
| R-58 | Import refactor: `config.AiSolveConfig` → `config.ai_solve.AiSolveConfig` | Cleanup | ✅ Correct | Proper module-level import |
| R-59 | `SgfNode` → `SGFNode` rename + import from `core.sgf_parser` | Refactor | ✅ Correct | Aligns with core parser module migration |
| R-60 | `SyncEngineAdapter` async/loop fix | Bug fix | ✅ Correct | Uses `get_running_loop()` with proper ThreadPoolExecutor fallback |
| R-61 | `puzzle_region` param threaded through `build_solution_tree()` and `_build_tree_recursive()` | B (Benson gate) | ✅ Correct | Needed for terminal detection |
| R-62 | PI-2 adaptive visit allocation in `build_solution_tree()` | **B (PI-2)** | ✅ Correct | Uses `tree_config.branch_visits` for decision points when mode="adaptive". Logs change. |
| R-63 | PI-2 continuation visits at player nodes | **B (PI-2)** | ✅ Correct | `child_effective_visits = tree_config.continuation_visits` for player continuation moves in adaptive mode |
| R-64 | Benson gate G1 + Interior-point G2 in `_build_tree_recursive()` | Pre-existing (RC-3) | ✅ Correct | Pre-query terminal detection with timing. Correctly checks after depth guard but before engine query. |
| R-65 | Board state tracker expansion | Cleanup | ✅ Correct | Also needed when `terminal_detection_enabled` true (not just transposition) |
| R-66 | PI-9 player alternative exploration at player nodes | **B (PI-9)** | ✅ Correct | Rate-based random exploration of top-2 alternatives at player nodes. Gated by `player_alternative_rate > 0`. Children marked `is_correct=False`. |
| R-67 | `puzzle_region` threaded through all recursive calls | B | ✅ Correct | All 5 `_build_tree_recursive()` call sites pass `puzzle_region` |
| R-68 | `discover_alternatives()` gets `puzzle_region` param | B | ✅ Correct | Passed through to `build_solution_tree()` |

### 3.3 Committed Phase B Config State

These are **already committed** and clean — no diff:

| File | Phase B Fields Present | Defaults Correct |
|------|----------------------|-----------------|
| `config/refutations.py` | PI-5: `noise_scaling="fixed"`, `noise_base=0.03`, `noise_reference_area=361` | ✅ |
| `config/refutations.py` | PI-6: `forced_min_visits_formula=False`, `forced_visits_k=2.0` | ✅ |
| `config/solution_tree.py` | PI-2: `visit_allocation_mode="fixed"`, `branch_visits=500`, `continuation_visits=125` | ✅ |
| `config/solution_tree.py` | PI-9: `player_alternative_rate=0.0`, `player_alternative_auto_detect=True` | ✅ |
| `analyzers/stages/solve_paths.py` | PI-9: Auto-detect logic sets rate=0.05 for position-only puzzles | ✅ |

### 3.4 Phase B JSON Config — ❌ NOT YET ADDED

`config/katago-enrichment.json` does **NOT** have Phase B keys. They are MISSING from the JSON:

- `refutation_overrides.noise_scaling`, `noise_base`, `noise_reference_area` (PI-5)
- `refutations.forced_min_visits_formula`, `forced_visits_k` (PI-6)
- `solution_tree.visit_allocation_mode`, `branch_visits`, `continuation_visits` (PI-2)
- `solution_tree.player_alternative_rate`, `player_alternative_auto_detect` (PI-9)

**This is acceptable** — Pydantic defaults handle absent keys. But for consistency with Phase A pattern (where all keys were added to JSON), Phase B should add them during its T5-equivalent task.

### 3.5 Phase B Uncommitted Code Verdict

| Aspect | Assessment |
|--------|-----------|
| **PI-2 (adaptive visits)** | ✅ Config committed, runtime code uncommitted in solve_position.py. Logic correct: branch nodes get `branch_visits`, player continuations get `continuation_visits`. Gated by `visit_allocation_mode="fixed"` default. |
| **PI-5 (noise scaling)** | ✅ Config committed, runtime code uncommitted in generate_refutations.py. Logic correct: `base * ref_area / legal_moves`. Gated by `noise_scaling="fixed"` default. |
| **PI-6 (forced visits)** | ✅ Config committed, runtime code uncommitted in generate_refutations.py. Logic correct: `sqrt(k * policy * base_visits)`. Only boosts, never reduces. Gated by `forced_min_visits_formula=False`. |
| **PI-9 (player alternatives)** | ✅ Config committed, auto-detect committed in solve_paths.py, tree exploration uncommitted in solve_position.py. Logic correct: explores top-2 player alternatives at rate with `is_correct=False` tagging. Gated by `player_alternative_rate=0.0`. |
| **Missing tests** | ❌ No Phase B test file exists (e.g., `test_refutation_quality_phase_b.py`). Must be created. |
| **Missing JSON keys** | ❌ Phase B keys not yet in `katago-enrichment.json`. Must be added with v1.19 bump. |
| **Missing AGENTS.md update** | ❌ AGENTS.md has Phase A references but not Phase B PI-2/PI-5/PI-6/PI-9 entries. |
| **Missing changelog** | ❌ No v1.19 changelog entry in `katago-enrichment.json` |

---

## 4. Part 3: Phase C/D Extension Points

### 4.1 PI-7: Branch Disagreement Escalation (Phase C)

| ID | Extension Point | Location | Description |
|----|----------------|----------|-------------|
| R-69 | Opponent node branch loop | [solve_position.py L1380-L1450](../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1380) | After opponent branch child is built, compare child's winrate vs parent to detect disagreement. If `abs(child_wr - parent_wr) > branch_disagreement_threshold`, re-query child with escalated visits. Existing `effective_visits` variable is the injection point. |
| R-70 | Config location | `config/solution_tree.py: SolutionTreeConfig` | Add `branch_escalation_enabled: bool = False`, `branch_disagreement_threshold: float = 0.10` |

### 4.2 PI-8: Diversified Harvesting (Phase C)

| ID | Extension Point | Location | Description |
|----|----------------|----------|-------------|
| R-71 | After first-pass candidates | [generate_refutations.py L660-L670](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L660) | After Step 3 (generate refutations loop), add second-pass: re-analyze with `secondary_noise_multiplier * effective_noise`, re-run `identify_candidates()` excluding already-found candidates, generate additional refutations. |
| R-72 | Config location | `config/refutations.py: RefutationsConfig` | Add `multi_pass_harvesting: bool = False`, `secondary_noise_multiplier: float = 2.0` |

### 4.3 PI-12: Best Resistance (Phase C)

| ID | Extension Point | Location | Description |
|----|----------------|----------|-------------|
| R-73 | Single refutation generation | [generate_refutations.py L357-L365](../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L357) | After `after_wrong = await engine.analyze(request)`, instead of taking `after_wrong.top_move`, evaluate top `best_resistance_max_candidates` opponent responses. For each, compute punishment depth. Select the one that maximizes `abs(winrate_delta)`. |
| R-74 | Config location | `config/refutations.py: RefutationsConfig` | Add `best_resistance_enabled: bool = False`, `best_resistance_max_candidates: int = 3` |

### 4.4 PI-11: Surprise Calibration (Phase D)

| ID | Extension Point | Location | Description |
|----|----------------|----------|-------------|
| R-75 | `CalibrationConfig` exists | [config/infrastructure.py L42](../../tools/puzzle-enrichment-lab/config/infrastructure.py#L42) | Currently has `sample_size`, `seed`, `batch_timeout`, `level_tolerance`, `fixture_dirs`, `randomize_fixtures`. Add `surprise_weighting: bool = False`, `surprise_weight_scale: float = 2.0`. |
| R-76 | Calibration pipeline | Test files: `test_calibration.py`, `test_ai_solve_calibration.py` | Calibration already exists as test infrastructure. Surprise weighting would modify the sampling/weighting during threshold optimization. `.lab-runtime/calibration-results/` directory exists. |

---

## 5. Part 4: Test Infrastructure State

| ID | Metric | Value |
|----|--------|-------|
| R-77 | Total tests (excluding golden5/calibration/ai_solve_calibration, not slow) | **2097 collected** (19 deselected) |
| R-78 | Phase A dedicated tests | **41 tests** in `test_refutation_quality_phase_a.py` |
| R-79 | Phase B dedicated tests | **0** — No `test_refutation_quality_phase_b.py` exists |

### Test Files Affected by Phase B Changes

| File | Likely Impact | Reason |
|------|--------------|--------|
| `test_solve_position.py` | HIGH | PI-2 modifies `_build_tree_recursive()` visit allocation; PI-9 adds player alternative branches |
| `test_refutations.py` | HIGH | PI-5 changes noise computation; PI-6 changes visit allocation in `generate_single_refutation()` |
| `test_single_engine.py` | LOW | PI-4 model routing already tested in Phase A tests |
| `test_enrich_single.py` | MEDIUM | Integration: may call `generate_refutations()` with new params |
| `test_sgf_enricher.py` | LOW | Orchestrator; passes through config |
| `test_ai_solve_integration.py` | MEDIUM | Solution tree integration tests may need adaptive visit awareness |
| `test_sprint2_fixes.py`–`test_sprint5_fixes.py` | LOW | Sprint regression tests should remain stable (feature-gated) |

---

## 6. Planner Recommendations

1. **Phase A is charter-complete** — all 42 audit checks pass. No remediation needed. Proceed to commit the working tree changes that belong to Phase A (generate_refutations.py and solve_position.py contain Phase A + Phase B mixed). Consider a clean Phase A-only commit if Git hygiene matters.

2. **Phase B code is correct but incomplete** — All 4 PI items (PI-2, PI-5, PI-6, PI-9) have correct runtime logic in the working tree diff. Before merging Phase B: (a) add Phase B keys to `katago-enrichment.json` with v1.19 bump, (b) create `test_refutation_quality_phase_b.py` with TS-6..TS-9 test classes, (c) update AGENTS.md with Phase B entries.

3. **Phase C extension points are well-defined** — PI-7 injects at opponent-node branch loop in `_build_tree_recursive()`, PI-8 adds a second-pass after refutation generation, PI-12 evaluates multiple opponent responses in `generate_single_refutation()`. All have clear config homes and gating patterns.

4. **Phase D calibration infrastructure exists** — `CalibrationConfig` is ready for extension. Surprise weighting is a 2-field addition + sampling modification.

---

## 7. Confidence and Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | **95** |
| `post_research_risk_level` | **low** |

Risk notes:
- The uncommitted diff is large (~480 lines across 2 files) and mixes Phase A + Phase B + pre-existing feature work. A clean separation before commit would reduce review complexity.
- Phase B JSON keys missing from `katago-enrichment.json` — low risk since Pydantic defaults handle it, but inconsistent with Phase A pattern.
- No Phase B tests yet — medium risk if code is committed before tests exist.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should the working tree diff be split into a clean Phase A commit and a separate Phase B commit? | A: Split / B: Single commit / C: Other | A: Split — cleaner history, Phase A is already charter-complete | | ❌ pending |
| Q2 | Should Phase B JSON keys be added before or during Phase B code commit? | A: Before (prep commit) / B: Same commit / C: Other | B: Same commit — matches Phase A pattern | | ❌ pending |
| Q3 | The `SgfNode → SGFNode` rename and `config.ai_solve` import refactor in solve_position.py — is this a separate cleanup tracked elsewhere? | A: Part of Phase B / B: Separate cleanup commit / C: Other | B: Separate — reduces Phase B diff noise | | ❌ pending |
