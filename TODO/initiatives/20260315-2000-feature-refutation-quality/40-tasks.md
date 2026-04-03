# Tasks: Refutation Tree Quality Improvements (All Phases)

> Initiative: `20260315-2000-feature-refutation-quality`
> Option: OPT-3 (Parallel Tracks) — Expanded with DF-2/3/4/5
> Last Updated: 2026-03-15

---

## Phase A Task Graph

```
T1 (config schema) ─┬─→ T2 (PI-1 ownership)   ─┬─→ T6 (integration tests)
                     ├─→ T3 (PI-3 score)        ─┤
                     ├─→ T4 (PI-4 model route)   ─┤
                     └─→ T4b (PI-10 opponent pol) ─┘
                                                   └─→ T7 (AGENTS.md + changelog)
T5 (config JSON) depends on T1
T2, T3, T4, T4b depend on T1 + T5
T6 depends on T2, T3, T4, T4b
T7 depends on T6
```

---

## Phase A Task Checklist (Signal Quality + Teaching + Compute)

| ID | Task | Files | Depends On | Parallel | Status |
|----|------|-------|------------|----------|--------|
| T1 | **Add config model fields** — Add `ownership_delta_weight`, `score_delta_enabled`, `score_delta_threshold` to `RefutationsConfig`. Add `model_by_category` to `AiSolveConfig`. Add `use_opponent_policy` to `TeachingConfig`. | `config/refutations.py`, `config/ai_solve.py`, `config/teaching.py` | — | [P] T1 is standalone | ✅ done |
| T2 | **PI-1: Ownership delta scoring in refutation candidates** — Add `compute_ownership_delta()` helper. Modify candidate scoring in `identify_candidates()` to use weighted composite: `wr_delta * (1-w) + ownership_delta * w`. Use initial analysis ownership data. Emit structured `ownership_delta` field in batch summary via `BatchSummaryAccumulator` pattern (~5 LOC). | `analyzers/generate_refutations.py`, `analyzers/observability.py` | T1, T5 | [P] T2/T3/T4/T4b are parallel | ✅ done (algorithm impl, observability pending RC-3) |
| T3 | **PI-3: Score-lead delta filter for refutations** — Add score delta as complementary candidate qualification filter in `identify_candidates()`. Candidate qualifies if winrate delta OR score delta exceeds threshold. Emit structured `score_delta` field in batch summary via `BatchSummaryAccumulator` (~5 LOC). | `analyzers/generate_refutations.py`, `analyzers/observability.py` | T1, T5 | [P] T2/T3/T4/T4b are parallel | ✅ done (rescue mechanism impl, observability pending RC-3) |
| T4 | **PI-4: Model routing by puzzle complexity** — Add model selection logic to `SingleEngineManager` to use category-mapped model when `model_by_category` is configured. Add YM metadata flag for model used. | `analyzers/single_engine.py` | T1, T5 | [P] T2/T3/T4/T4b are parallel | ✅ done |
| T4b | **PI-10: Opponent policy for teaching comments** — (a) Apply VP-3 wrong-move template fixes (9 of 12) in `config/teaching-comments.json`. (b) Reshape `capturing_race_lost` template from 9w→3w. (c) Add `voice_constraints` block to `config/teaching-comments.json`. (d) Add `opponent_response_templates` with 5 active + 7 suppressed conditions to `config/teaching-comments.json`. (e) In `comment_assembler.py`, add `_assemble_opponent_response()` helper: look up condition in `enabled_conditions`, substitute tokens `{opponent_color}` + `{!opponent_move}`, apply conditional dash rule (suppress dash when WM already has `—`). (f) Add `_count_words()` guard to `assemble_wrong_comment()`. (g) Emit opponent-response metrics in batch summary via `BatchSummaryAccumulator`. | `analyzers/comment_assembler.py`, `analyzers/teaching_comments.py`, `analyzers/observability.py`, `config/teaching-comments.json` | T1, T5 | [P] T2/T3/T4/T4b are parallel | ✅ done |
| T5 | **Update katago-enrichment.json** — Add all new config keys with defaults matching current behavior. Bump version to v1.18. | `config/katago-enrichment.json` | T1 | — | ✅ done |
| T6 | **Unit + integration tests (Phase A)** — TS-1: Ownership delta scoring tests. TS-2: Score delta filter tests. TS-3: Model routing tests. TS-4: Config parsing tests. TS-5: Opponent policy teaching comment tests. TS-6: Regression. | `tests/test_generate_refutations.py`, `tests/test_ai_solve_config.py`, `tests/test_comment_assembler.py` | T2, T3, T4, T4b | — | ✅ done (28 tests: TestOpponentResponseAssembly, TestModelRouting, TestOwnershipDeltaScoring, TestScoreDeltaRescue) |
| T7 | **Update AGENTS.md + changelog** — Add new config models. Add scoring logic. Add opponent policy teaching path. Bump config version in changelog. | `AGENTS.md`, `config/katago-enrichment.json` (changelog) | T6 | — | ✅ done (PI-1/PI-3/PI-4 bullets added to AGENTS.md §5) |

---

## Phase B Task Graph

```
T8a (JSON config v1.19) ──┬──→ T8b (PI-2 tests) ──────────┐
                           ├──→ T9a (PI-5 tests)  ─[P]─────┤
                           ├──→ T10a (PI-6 tests) ─[P]─────┤
                           └──→ T11a (PI-9 tests) ──────────┤
                                                             └──→ T16b (regression) → T16c (AGENTS.md)
```

**Note**: PI-2/PI-5/PI-6/PI-9 algorithm code is already injected in working tree. Config Pydantic models are committed. Phase B work is completing the remaining gaps: JSON keys, tests, AGENTS.md, and observability.

---

## Phase B Task Checklist (Tree Depth + Exploration + Alternatives)

| ID | Task | Files | Depends On | Parallel | Status |
|----|------|-------|------------|----------|--------|
| T8a | **Update katago-enrichment.json v1.19** — Add all Phase B config keys with disabled/current-behavior defaults. Keys: `solution_tree.visit_allocation_mode` ("fixed"), `solution_tree.branch_visits` (500), `solution_tree.continuation_visits` (125), `refutation_overrides.noise_scaling` ("fixed"), `refutation_overrides.noise_base` (0.03), `refutation_overrides.noise_reference_area` (361), `refutations.forced_min_visits_formula` (false), `refutations.forced_visits_k` (2.0), `solution_tree.player_alternative_rate` (0.0), `solution_tree.player_alternative_auto_detect` (true). Bump version v1.18→v1.19 with changelog entry. | `config/katago-enrichment.json` | — | — | ✅ done |
| T8b | **PI-2: Adaptive visits tests** (TS-8b) — (a) Feature gate: `visit_allocation_mode="fixed"` uses current `tree_visits`. (b) Adaptive mode: branch nodes get `branch_visits`, continuation nodes get `continuation_visits`. (c) Config parsing: new keys parse with correct defaults. (d) Absent key: behavior unchanged. | `tests/test_refutation_quality_phase_b.py` | T8a | [P] T8b/T9a/T10a/T11a parallel | ✅ done (8 tests) |
| T9a | **PI-5: Noise scaling tests** (TS-8) — (a) Feature gate: `noise_scaling="fixed"` uses current `wide_root_noise=0.08`. (b) Board-scaled: 9×9 → `~0.134`, 19×19 → `~0.030`. (c) Config defaults: noise_base=0.03, noise_reference_area=361. (d) Edge case: board_area=0 guard. | `tests/test_refutation_quality_phase_b.py` | T8a | [P] T8b/T9a/T10a/T11a parallel | ✅ done (9 tests) |
| T10a | **PI-6: Forced visits tests** (TS-9) — (a) Feature gate: `forced_min_visits_formula=false` → no forced visits. (b) Formula: `sqrt(k * P(c) * total)` for k=2.0, various P(c). (c) Config parsing. (d) Only candidates above policy threshold get forced visits. | `tests/test_refutation_quality_phase_b.py` | T8a | [P] T8b/T9a/T10a/T11a parallel | ✅ done (9 tests) |
| T11a | **PI-9: Player alternatives tests** (TS-7) — (a) Auto-detect: position-only → rate=0.05. (b) Auto-detect: curated single-answer → rate=0.0. (c) Must-hold #4 safeguard: zero alternatives explored when rate=0.0. (d) Manual override: `player_alternative_rate=0.1` → uses manual rate. (e) Config parsing and defaults. | `tests/test_refutation_quality_phase_b.py` | T8a | [P] T8b/T9a/T10a/T11a parallel | ✅ done (8 tests) |
| T16b | **Phase B regression** — Run `pytest -m "not (cli or slow)"` and confirm zero new failures. | — | T8b, T9a, T10a, T11a | — | ✅ done (546+1936 passed) |
| T16c | **Phase B AGENTS.md + observability** — (a) Update AGENTS.md §3 with PI-2/PI-5/PI-6/PI-9 method entries and injection points. (b) Update §5 with Phase B config keys. (c) Add `opponent_response_emitted` counter to BatchSummary/BatchSummaryAccumulator (PI-10 observability gap from audit). | `tools/puzzle-enrichment-lab/AGENTS.md`, `tools/puzzle-enrichment-lab/models/solve_result.py`, `tools/puzzle-enrichment-lab/analyzers/observability.py` | T16b | — | ✅ done |

---

## Phase C Task Graph

```
T12a (PI-7 config) ──→ T12b (PI-7 algorithm) ──→ T12c (PI-7 tests)  ──┐
T13a (PI-8 config) ──→ T13b (PI-8 algorithm) ──→ T13c (PI-8 tests)  ──┤ [P] T12/T13
T14a (PI-12 config) ─→ T14b (PI-12 algorithm) → T14c (PI-12 tests) ──┤ [P] T14
                                                                        └──→ T16d (JSON v1.20) → T16e (regression) → T16f (AGENTS.md)
```

---

## Phase C Task Checklist (Compute Allocation + Discovery + Resistance)

| ID | Task | Files | Depends On | Parallel | Status |
|----|------|-------|------------|----------|--------|
| T12a | **PI-7: Config model** — Add `branch_escalation_enabled: bool = False` and `branch_disagreement_threshold: float = 0.10` to `SolutionTreeConfig`. | `config/solution_tree.py` | Phase B complete | [P] T12a/T13a/T14a parallel | ✅ done |
| T12b | **PI-7: Branch-local escalation algorithm** — In `_build_tree_recursive()`, at opponent nodes, compare policy vs search outcome after evaluation. If disagreement > threshold, re-evaluate branch with escalated visits. Log escalation events. | `analyzers/solve_position.py` | T12a | — | ✅ done |
| T12c | **PI-7: Tests** (TS-11) — (a) Feature gate: disabled → no escalation. (b) Disagreement above threshold → escalated visits. (c) Disagreement below → standard visits. (d) Escalation capped by `max_total_tree_queries`. | `tests/test_refutation_quality_phase_c.py` | T12b | [P] T12c/T13c/T14c parallel | ✅ done (8 tests) |
| T13a | **PI-8: Config model** — Add `multi_pass_harvesting: bool = False` and `secondary_noise_multiplier: float = 2.0` to `RefutationsConfig`. | `config/refutations.py` | Phase B complete | [P] T12a/T13a/T14a parallel | ✅ done |
| T13b | **PI-8: Multi-pass harvesting algorithm** — In `identify_candidates()`, after initial scan, run secondary scan with `noise * secondary_noise_multiplier`. Merge and deduplicate candidates. Re-rank by composite score. | `analyzers/generate_refutations.py` | T13a | — | ✅ done |
| T13c | **PI-8: Tests** (TS-12) — (a) Feature gate: disabled → single pass. (b) Multi-pass: secondary scan finds candidates missed by first. (c) Deduplication: same candidate from both passes → single entry. (d) Compute: secondary pass bounded by maxMoves. | `tests/test_refutation_quality_phase_c.py` | T13b | [P] T12c/T13c/T14c parallel | ✅ done (9 tests) |
| T14a | **PI-12: Config model** — Add `best_resistance_enabled: bool = False` and `best_resistance_max_candidates: int = 3` to `RefutationsConfig`. | `config/refutations.py` | Phase B complete | [P] T12a/T13a/T14a parallel | ✅ done |
| T14b | **PI-12: Best-resistance algorithm** — In `generate_single_refutation()`, after initial PV, evaluate top N opponent responses and select strongest punishment (by score delta or ownership flip). For position-only puzzles, best-resistance is essential for solution discovery. | `analyzers/generate_refutations.py` | T14a | — | ✅ done |
| T14c | **PI-12: Tests** (TS-10) — (a) Feature gate: disabled → first PV used (current behavior). (b) Enabled: evaluate up to N candidates, pick max punishment. (c) Compute cap: `best_resistance_max_candidates` respected. (d) Position-only integration: correct move verified via best resistance. | `tests/test_refutation_quality_phase_c.py` | T14b | [P] T12c/T13c/T14c parallel | ✅ done (7 tests) |
| T16d | **Phase C JSON config v1.20** — Add PI-7/PI-8/PI-12 keys to katago-enrichment.json with disabled defaults. Bump v1.19→v1.20. | `config/katago-enrichment.json` | T12c, T13c, T14c | — | ✅ done |
| T16e | **Phase C regression** — Run `pytest -m "not (cli or slow)"`. | — | T16d | — | ✅ done (1936 passed) |
| T16f | **Phase C AGENTS.md** — Update §3 with PI-7/PI-8/PI-12 methods. Update §5 with Phase C config keys. | `tools/puzzle-enrichment-lab/AGENTS.md` | T16e | — | ✅ done |

---

## Phase D Task Graph

```
T15a (PI-11 config) → T15b (PI-11 algorithm) → T15c (PI-11 tests) → T16g (JSON v1.21) → T16h (regression) → T16i (AGENTS.md + final docs)
```

---

## Phase D Task Checklist (Calibration Infrastructure)

| ID | Task | Files | Depends On | Parallel | Status |
|----|------|-------|------------|----------|--------|
| T15a | **PI-11: Config model** — Add `surprise_weighting: bool = False` and `surprise_weight_scale: float = 2.0` to `CalibrationConfig` in `config/infrastructure.py`. | `config/infrastructure.py` | Phase C complete | — | ✅ done |
| T15b | **PI-11: Surprise-weighted calibration algorithm** — In calibration pipeline, compute per-puzzle surprise score = `|T0_winrate - T2_winrate|`. Weight = `1 + surprise_weight_scale * surprise_score`. Apply weighted contribution to threshold optimization. | Calibration pipeline scripts | T15a | — | ✅ done (`compute_surprise_weight()` in `config/infrastructure.py`) |
| T15c | **PI-11: Tests** (TS-13) — (a) Feature gate: disabled → uniform weighting. (b) Enabled: high-surprise positions get more weight. (c) Identical output when surprise_weight_scale=0. (d) Seed reproducibility. | `tests/test_refutation_quality_phase_d.py` (new) | T15b | — | ✅ done (17 tests) |
| T16g | **Phase D JSON config v1.21** — Add PI-11 keys to katago-enrichment.json. Bump v1.20→v1.21. | `config/katago-enrichment.json` | T15c | — | ✅ done |
| T16h | **Phase D regression** — Run full test suite `pytest -m "not (cli or slow)"`. | — | T16g | — | ✅ done (1941 backend passed, 2160 enrichment lab passed) |
| T16i | **Phase D AGENTS.md + final closeout** — Update §3 with PI-11 calibration method. Update §5 with final config key set. Final changelog summary (v1.18→v1.21 across 4 phases). | `tools/puzzle-enrichment-lab/AGENTS.md` | T16h | — | ✅ done |

---

## Compatibility Strategy

- **No legacy removal** — all changes are additive
- **Feature gates** — each PI item has its own config switch defaulting to disabled/current behavior
- **Absent key** — absent config key = current behavior (Pydantic defaults)
- **Version** — config version bumped v1.17 → v1.18
- **Auto-detect** — PI-9 (player alternatives) uses puzzle-type auto-detection, no per-collection config needed

> **See also**:
> - [Plan: 30-plan.md](30-plan.md) — Architecture and risk details
> - [Charter: 00-charter.md](00-charter.md) — Full scope and classification
