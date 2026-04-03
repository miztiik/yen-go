# Codebase State Audit — All 12 PI Items

> Initiative: `20260315-2000-feature-refutation-quality`
> Date: 2026-03-16
> Scope: Read-only audit of `tools/puzzle-enrichment-lab/` + `config/katago-enrichment.json` + `config/teaching-comments.json`

---

## 1. Config JSON Version

**`config/katago-enrichment.json` version: `1.18`**

v1.18 changelog entry confirms Phase A scope:
> "Refutation tree quality improvements Phase A (PI-1/PI-3/PI-4/PI-10). Added: refutations.ownership_delta_weight, refutations.score_delta_enabled/score_delta_threshold, ai_solve.model_by_category, teaching.use_opponent_policy. All feature-gated with current-behavior defaults."

### Custom keys added for this initiative in katago-enrichment.json

| R-ID | JSON Path | Default | Phase |
|------|-----------|---------|-------|
| R-1 | `refutations.ownership_delta_weight` | `0.0` | A (PI-1) |
| R-2 | `refutations.score_delta_enabled` | `false` | A (PI-3) |
| R-3 | `refutations.score_delta_threshold` | `5.0` | A (PI-3) |
| R-4 | `ai_solve.model_by_category` | `{}` | A (PI-4) |
| R-5 | `teaching.use_opponent_policy` | `false` | A (PI-10) |

**Phase B keys**: NOT present in katago-enrichment.json. All Phase B config fields exist only in Pydantic models with defaults. Zero JSON keys for PI-2, PI-5, PI-6, PI-9.

---

## 2. Detailed PI-Item Status Table

| R-ID | PI-ID | Config Pydantic Model | Algorithm Code | JSON Config Key | Tests | AGENTS.md | Overall Status |
|------|-------|-----------------------|----------------|-----------------|-------|-----------|----------------|
| R-6 | **PI-1** | ✅ PRESENT — `RefutationsConfig.ownership_delta_weight` (refutations.py L157) | ✅ PRESENT — `compute_ownership_delta()` (generate_refutations.py L36), composite scoring in `identify_candidates()` (L200-228) | ✅ PRESENT — `refutations.ownership_delta_weight: 0.0` | ✅ PRESENT — 7 tests in `TestOwnershipDelta` | ✅ MENTIONED — L158-160, L232 | **COMPLETE** |
| R-7 | **PI-3** | ✅ PRESENT — `RefutationsConfig.score_delta_enabled` (L163), `.score_delta_threshold` (L168) | ✅ PRESENT — rescue logic in `identify_candidates()` (L240-248), per-candidate filter in `_generate_single_refutation()` (L390-428) | ✅ PRESENT — `refutations.score_delta_enabled: false`, `.score_delta_threshold: 5.0` | ✅ PRESENT — 5 tests in `TestScoreDeltaFilter` | ✅ MENTIONED — L233 | **COMPLETE** |
| R-8 | **PI-4** | ✅ PRESENT — `AiSolveConfig.model_by_category` (ai_solve.py L164) | ✅ PRESENT — `get_model_for_level()` (single_engine.py L76), `model_label_for_routing()` (L108) | ✅ PRESENT — `ai_solve.model_by_category: {}` | ✅ PRESENT — 6 tests in `TestModelRouting` | ✅ MENTIONED — L163-164, L167, L239 | **COMPLETE** |
| R-9 | **PI-10** | ✅ PRESENT — `TeachingConfig.use_opponent_policy` (teaching.py L39) | ✅ PRESENT — `_assemble_opponent_response()` (comment_assembler.py L159), gated in `assemble_wrong_comment()` (L253-254) | ✅ PRESENT — `teaching.use_opponent_policy: false` (L420) | ✅ PRESENT — 12 tests in `TestOpponentResponseComments` | ✅ MENTIONED — L170-171, L231 | **COMPLETE** |
| R-10 | **PI-2** | ✅ PRESENT — `SolutionTreeConfig.visit_allocation_mode` (solution_tree.py L138), `.branch_visits` (L144), `.continuation_visits` (L148) | ✅ PRESENT — adaptive mode check at solve_position.py L946-951 (branch nodes) and L1211-1215 (continuation nodes) | ❌ MISSING — no JSON keys | ❌ MISSING — no Phase B test file | Not specifically mentioned | **PARTIAL** |
| R-11 | **PI-5** | ✅ PRESENT — `RefutationOverridesConfig.noise_scaling` (refutations.py L42), `.noise_base` (L47), `.noise_reference_area` (L52) | ✅ PRESENT — board-scaled noise in generate_refutations.py L643-651 | ❌ MISSING — no JSON keys | ❌ MISSING — no Phase B test file | Not specifically mentioned | **PARTIAL** |
| R-12 | **PI-6** | ✅ PRESENT — `RefutationsConfig.forced_min_visits_formula` (refutations.py L171), `.forced_visits_k` (L177) | ✅ PRESENT — forced visits in generate_refutations.py L333-345 | ❌ MISSING — no JSON keys | ❌ MISSING — no Phase B test file | Not specifically mentioned | **PARTIAL** |
| R-13 | **PI-9** | ✅ PRESENT — `SolutionTreeConfig.player_alternative_rate` (solution_tree.py L152), `.player_alternative_auto_detect` (L158) | ✅ PRESENT — alternative exploration at solve_position.py L1320-1342, auto-detect in stages/solve_paths.py L103-110 | ❌ MISSING — no JSON keys | ❌ MISSING — no Phase B test file | Referenced at L164, L239 ("Phase B") | **PARTIAL** |
| R-14 | **PI-7** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING | NOT MENTIONED | **NOT STARTED** |
| R-15 | **PI-8** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING | NOT MENTIONED | **NOT STARTED** |
| R-16 | **PI-12** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING | NOT MENTIONED | **NOT STARTED** |
| R-17 | **PI-11** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING | NOT MENTIONED | **NOT STARTED** |

---

## 3. Phase A — Detailed Findings

### Tests: test_refutation_quality_phase_a.py — 41 tests collected

| Test Class | PI | Count | Coverage |
|------------|----|-------|----------|
| `TestOwnershipDelta` (TS-1) | PI-1 | 7 | computation, edge cases, candidate reranking |
| `TestScoreDeltaFilter` (TS-2) | PI-3 | 5 | config defaults, rescue logic, disabled state |
| `TestModelRouting` (TS-3) | PI-4 | 6 | empty routing, active routing, unmapped categories, labels |
| `TestPhaseAConfigParsing` (TS-4) | All | 7 | version, defaults, backward compat, changelog |
| `TestOpponentResponseComments` (TS-5) | PI-10 | 12 | gate on/off, 5 active, 7 suppressed, dash rule, word count, tokens |
| `TestVP3Compliance` | PI-10 | 4 | voice constraints, forbidden starts, warmth rule |

### Observability

- `BatchSummary` model (models/solve_result.py L409-417): Has `ownership_delta_used: int` and `score_delta_rescues: int`
- `BatchSummaryAccumulator` (analyzers/observability.py L130-188): Tracks both counters, wired into `record_puzzle()` and `emit()`
- **`opponent_response_emitted`**: ❌ NOT FOUND in BatchSummary or BatchSummaryAccumulator — PI-10 observability counter is missing

### AGENTS.md

Updated 2026-03-15. Contains entries for:
- `compute_ownership_delta()` (L158-160)
- `get_model_for_level()` (L163-164)
- `model_label_for_routing()` (L167)
- `_assemble_opponent_response()` (L170-171)
- Prose summaries for PI-1, PI-4, opponent-response composition (L231-239)

### Config: config/teaching-comments.json

- `opponent_response_templates` section (L334): 5 templates, 5 `enabled_conditions`
- `voice_constraints` section (L327): `max_words: 15`, `forbidden_starts`, `forbidden_phrases`
- Conditional dash rule documented

---

## 4. Phase B — Detailed Findings

All 4 Phase B items share: config models ✅, algorithm code ✅, JSON keys ❌, tests ❌

### Algorithm Injection Points

| R-ID | PI-ID | File | Lines | Description |
|------|-------|------|-------|-------------|
| R-18 | PI-2 | analyzers/solve_position.py | L946-951 | Adaptive visit allocation — branch nodes get `branch_visits` |
| R-19 | PI-2 | analyzers/solve_position.py | L1211-1215 | Continuation nodes get `continuation_visits` |
| R-20 | PI-5 | analyzers/generate_refutations.py | L643-651 | Board-scaled noise: `base * ref_area / legal_moves` |
| R-21 | PI-6 | analyzers/generate_refutations.py | L333-345 | Forced min visits: `sqrt(k * P(c) * total_visits)` |
| R-22 | PI-9 | analyzers/solve_position.py | L1320-1342 | Player-side alternative exploration |
| R-23 | PI-9 | analyzers/stages/solve_paths.py | L103-110 | Auto-detect position-only → rate=0.05 |

### Phase B Test File

❌ `test_refutation_quality_phase_b.py` does NOT exist.

---

## 5. Phase C (PI-7, PI-8, PI-12) and Phase D (PI-11)

All 4 items: zero config fields, zero algorithm code, zero JSON keys, zero tests, not mentioned in AGENTS.md. Completely **NOT STARTED**.

---

## 6. Discrepancies

| R-ID | Discrepancy | Severity |
|------|-------------|----------|
| R-24 | `status.json` says `execute: "phase_b_in_progress"` — but Phase B has no JSON keys and no test file. Algorithm code IS injected but untestable without JSON. | Medium |
| R-25 | `opponent_response_emitted` observability counter missing from BatchSummary for PI-10. PI-1 and PI-3 have counters. | Low |
| R-26 | Phase B Pydantic defaults all gated OFF. JSON absent means testable only via Pydantic overrides, not via config file. | Medium |
| R-27 | AGENTS.md mentions "Phase B" only for PI-4 engine switching (L164, L239). Does not document PI-2, PI-5, PI-6 as Phase B items. | Low |

---

## 7. Summary

| Phase | Items | Status |
|-------|-------|--------|
| **A** | PI-1, PI-3, PI-4, PI-10 | ✅ **COMPLETE** — config + code + JSON + 41 tests + AGENTS.md |
| **B** | PI-2, PI-5, PI-6, PI-9 | ⚠️ **PARTIAL** — config models + algorithm code, NO JSON keys, NO tests |
| **C** | PI-7, PI-8, PI-12 | ❌ **NOT STARTED** |
| **D** | PI-11 | ❌ **NOT STARTED** |

---

## 8. Planner Recommendations

1. **Phase B completion requires**: (a) add JSON config keys + v1.19 changelog to katago-enrichment.json, (b) create `test_refutation_quality_phase_b.py` with feature-gate and algorithm smoke tests.
2. **Add `opponent_response_emitted` counter** to BatchSummary/BatchSummaryAccumulator for PI-10 observability completeness.
3. **Update AGENTS.md** to document Phase B injection points (PI-2/PI-5/PI-6/PI-9 line numbers).
4. **Phase C/D** can wait — zero code exists, no dependency on Phase B completion.

---

## 9. Confidence and Risk

| Metric | Value |
|--------|-------|
| Post-research confidence score | 85 |
| Post-research risk level | low |
