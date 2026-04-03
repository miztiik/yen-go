# Analysis: Refutation Tree Quality Improvements

> Initiative: `20260315-2000-feature-refutation-quality`
> Last Updated: 2026-03-16

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score — Phase A | 82/100 |
| Planning Confidence Score — Phase B/C/D | 85/100 |
| Risk Level — Phase B | low-medium |
| Risk Level — Phase C | medium |
| Risk Level — Phase D | medium |
| Research invoked | Yes (Feature-Researcher → 59 findings in 15-research.md + 16-codebase-audit.md) |
| Deductions (Phase B) | -10 (tree builder regression risk PI-2/PI-9), -5 (Phase B code in working tree without tests) |
| Deductions (Phase C) | -10 (PI-7 disagreement heuristic design), -5 (PI-12 compute cost estimation) |
| Deductions (Phase D) | -10 (calibration data sufficiency), -5 (surprise metric definition needs validation) |

---

## Consistency & Coverage Findings (All Phases)

| F-ID | Phase | Severity | Finding | Resolution |
|------|-------|----------|---------|------------|
| F1 | All | Info | Charter lists 12 PI items; tasks cover all 12 across 4 phases | ✅ Complete coverage (C-1 through C-18) |
| F2 | All | Info | OPT-3 selected unanimously; plan is derived from OPT-3 phasing | ✅ Consistent |
| F3 | A | Low | PI-4 model routing location unclear — `single_engine.py` vs stage | ✅ Resolved — implemented in `single_engine.py` |
| F4 | All | Info | All config defaults match current behavior per v1.14 pattern | ✅ Verified against status.json decisions |
| F5 | A | Low | Ownership delta computation needs puzzle_region scope | ✅ Resolved — `compute_ownership_delta()` implements region-aware computation |
| F6 | A | Info | Score delta already has foundation in `suboptimal_branches.score_delta_threshold=2.0` | ✅ PI-3 extends existing pattern |
| F7 | A | Info | `test_fast: b10c128` model already in config — PI-4 needs routing logic only | ✅ No new model definition needed |
| F8 | B | Medium | Phase B items have algorithm code + config models but NO JSON keys and NO tests | ❌ Must complete: T8a (JSON v1.19), T8b/T9a/T10a/T11a (tests), T16c (AGENTS.md) |
| F9 | B | Low | `status.json` says `phase_b_in_progress` but Phase B is only partially coded | ✅ Corrected — status reset to planning phase |
| F10 | A | Low | `opponent_response_emitted` observability counter missing from BatchSummary | ❌ Scoped into T16c (Phase B AGENTS.md + observability task) |
| F11 | B | Medium | PI-2 and PI-9 both touch `_build_tree_recursive()` — highest regression risk | ✅ Addressed — code injected at separate points (L946/L1211 vs L1320). Regression suite required. |
| F12 | C | Low | PI-7 disagreement threshold (0.10) is an untested heuristic | ✅ Addressed — feature-gated with disabled default. 0.10 is initial calibration value. |
| F13 | C | Medium | PI-7+PI-12 compound compute worst case: 6x per branch | ✅ Addressed — `max_total_tree_queries` cap (50). Both independently gated. |
| F14 | D | Medium | PI-11 surprise metric depends on T0/T2 winrate gap — may need different formulas for different puzzle types | ✅ Addressed — Phase D sequenced last with production data available. `surprise_weight_scale` is tunable. |
| F15 | B | Info | Phase B code already verified correct at injection points (audit R-18 through R-23) | ✅ Code review passed — needs formal test coverage |

---

## Coverage Map (All Phases)

| cov_id | Charter Item | Phase | Plan Section | Task IDs | Test IDs | Doc IDs | Status |
|--------|-------------|-------|-------------|----------|----------|---------|--------|
| C-1 | PI-1 (ownership delta) | A | Plan §PI-1 | T1, T2 | TS-1 | D-1, D-2 | ✅ Complete |
| C-2 | PI-3 (score delta) | A | Plan §PI-3 | T1, T3 | TS-2 | D-1, D-2 | ✅ Complete |
| C-3 | PI-4 (model routing) | A | Plan §PI-4 | T1, T4 | TS-3 | D-1, D-2 | ✅ Complete |
| C-4 | PI-10 (opponent policy) | A | Plan §PI-10 | T1, T4b | TS-5 | D-1, D-2 | ✅ Complete |
| C-5 | Config schema (Phase A) | A | Plan §all | T1, T5 | TS-4 | D-2 | ✅ Complete |
| C-6 | Phase A tests | A | Plan §Test Strategy | T6 | TS-1..6 | — | ✅ Complete (41 tests) |
| C-7 | Phase A docs | A | Plan §Doc Plan | T7 | — | D-1, D-2 | ✅ Complete |
| C-8 | PI-2 (adaptive visits) | B | Plan §PI-2 | T8a, T8b | TS-8b | D-4, D-5, D-6 | ⚠️ Partial (code+config, no JSON/tests) |
| C-9 | PI-5 (noise scaling) | B | Plan §PI-5 | T8a, T9a | TS-8 | D-4, D-5, D-6 | ⚠️ Partial (code+config, no JSON/tests) |
| C-10 | PI-6 (forced visits) | B | Plan §PI-6 | T8a, T10a | TS-9 | D-4, D-5, D-6 | ⚠️ Partial (code+config, no JSON/tests) |
| C-11 | PI-9 (player alternatives) | B | Plan §PI-9 | T8a, T11a | TS-7 | D-4, D-5, D-6 | ⚠️ Partial (code+config, no JSON/tests) |
| C-12 | Phase B tests+docs | B | Plan §Test+Doc | T16b, T16c | Regression | D-5, D-6 | ❌ Not started |
| C-13 | PI-7 (disagreement) | C | Plan §PI-7 | T12a, T12b, T12c | TS-11 | D-7, D-8, D-9 | ❌ Not started |
| C-14 | PI-8 (harvesting) | C | Plan §PI-8 | T13a, T13b, T13c | TS-12 | D-7, D-8, D-9 | ❌ Not started |
| C-15 | PI-12 (best resistance) | C | Plan §PI-12 | T14a, T14b, T14c | TS-10 | D-7, D-8, D-9 | ❌ Not started |
| C-16 | Phase C tests+docs | C | Plan §Test+Doc | T16d, T16e, T16f | Regression | D-8, D-9 | ❌ Not started |
| C-17 | PI-11 (calibration) | D | Plan §PI-11 | T15a, T15b, T15c | TS-13 | D-10, D-11, D-12 | ❌ Not started |
| C-18 | Phase D tests+docs | D | Plan §Test+Doc | T16g, T16h, T16i | Regression | D-11, D-12 | ❌ Not started |

---

## Unmapped Tasks

None — all tasks (T1-T7, T8a-T16i) map to charter PI items or documentation/regression obligations.

---

## Ripple-Effects Table (All Phases)

### Phase A Ripple Effects (Archived — all ✅ addressed)

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | `AnalysisResponse.move_infos[].ownership` — PI-1 depends on KataGo returning ownership data | Low — `include_ownership=True` already set in all queries | Already wired in `query_builder.py` | T2 | ✅ addressed |
| RE-2 | upstream | `AnalysisResponse.root_score` — PI-3 depends on score_lead being populated | Low — score data already returned and used elsewhere | `_enrich_curated_policy()` already reads `score_lead` | T3 | ✅ addressed |
| RE-3 | upstream | `get_level_category()` in `config/helpers.py` — PI-4 depends on level category being known at model selection time | Low — helper already exists with `LEVEL_CATEGORY_MAP` | Verify level is available when engine is initialized | T4 | ✅ addressed |
| RE-4 | downstream | `RefutationResult` — consumers of refutation data won't see format changes | None — output format unchanged. Only internal scoring changes. | No downstream impact | T2, T3 | ✅ addressed |
| RE-5 | downstream | `AiAnalysisResult` — model metadata may change if PI-4 routes to different model | Low — YM metadata already has model info. Add category routing flag. | Hana Park requirement: flag model used in YM | T4 | ✅ addressed |
| RE-6 | lateral | `tests/conftest.py` MockEngineManager — tests may need mock ownership data | Low — mock already returns ownership in some fixtures | Extend mock if needed | T6 | ✅ addressed |
| RE-7 | lateral | `observability.py` BatchSummary — new signals should be logged | Low — structured logging pattern exists | Emit ownership_delta and score_delta in batch summaries | T2, T3 | ✅ addressed |
| RE-8 | downstream | `config/katago-enrichment.json` version — consumers may read version | None — version bump is standard practice | Bump to v1.18 | T5 | ✅ addressed |
| RE-9 | upstream | `AnalysisResponse.move_infos[].pv` — PI-10 depends on PV being populated for refutation moves | None — PV always populated for analyzed moves | Already returned by KataGo | T4b | ✅ addressed |
| RE-10 | lateral | `comment_assembler.py` template system — PI-10 needs coordinate tokens in teaching comments | Low — `{!xy}` substitution already exists | Extend templates with opponent response token | T4b | ✅ addressed |

### Phase B Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-11 | lateral | `_build_tree_recursive()` — PI-2+PI-9 both modify tree builder inner loop | Medium — tree builder is most complex code path | Same modification window. PI-2 modifies visit allocation at L946/L1211. PI-9 adds branching at L1320. Different code sections. | T8b, T11a | ✅ addressed (code already injected at separate points) |
| RE-12 | upstream | `run_position_only_path()` — PI-9 auto-detect relies on solve path dispatch | None — dispatch already exists and is stable | Use existing dispatch signal | T11a | ✅ addressed (auto-detect at solve_paths.py L103) |
| RE-13 | downstream | `SolutionTree` output — PI-2 changes visit distribution, PI-9 adds alternative branches | Low — tree format unchanged, only internal quality changes | Feature gates default to current behavior | T8b, T11a | ✅ addressed |
| RE-14 | lateral | `override_settings` dict in `generate_refutations()` — PI-5 modifies noise value in same dict used by AI-1 FPU | Low — noise and FPU are independent override keys | `wide_root_noise` is separate from `root_fpu_reduction_max` | T9a | ✅ addressed |
| RE-15 | lateral | `generate_single_refutation()` — PI-6 adds forced visit logic before existing candidate evaluation | Low — additive code, doesn't modify existing evaluation | Only queries candidates that already passed filters | T10a | ✅ addressed |
| RE-16 | downstream | Phase B JSON config keys — existing deployments won't have v1.19 keys | None — Pydantic defaults handle absent keys (v1.14 pattern) | Absent key = current behavior | T8a | ✅ addressed |
| RE-17 | lateral | `opponent_response_emitted` observability gap — PI-10 missing counter in BatchSummary | Low — functional correctness unaffected, only monitoring gap | Add counter in T16c alongside AGENTS.md update | T16c | ❌ needs action |

### Phase C Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-18 | upstream | `branch_visits` from PI-2 — PI-7 escalation multiplies branch_visits | Medium — PI-7 depends on PI-2 being stable | Phase C sequenced after Phase B. Escalation is multiplicative on existing visits. | T12b | ✅ addressed (phasing) |
| RE-19 | upstream | `noise_scaling` from PI-5 — PI-8 secondary noise multiplies PI-5's output | Medium — PI-8 depends on PI-5 being stable | Phase C sequenced after Phase B. Multiplier applied on effective_noise. | T13b | ✅ addressed (phasing) |
| RE-20 | lateral | `identify_candidates()` — PI-8 adds second pass through same function | Low — second pass is additive, first pass untouched | Merge and deduplicate results after both passes | T13b | ✅ addressed |
| RE-21 | lateral | `generate_single_refutation()` — PI-12 adds multi-candidate evaluation after initial PV | Medium — modifies output selection (which PV to use) | Config cap `best_resistance_max_candidates=3`. Feature gate default disabled. | T14b | ✅ addressed |
| RE-22 | downstream | PI-7+PI-12 compound compute — escalated branches + multi-candidate resistance | Medium — worst case: 2x visits × 3 candidates = 6x per branch | `max_total_tree_queries` cap (50). Both features independently gated. | T12b, T14b | ✅ addressed |

### Phase D Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-23 | upstream | All prior signals (ownership, score, alternatives, resistance) — PI-11 needs diverse data | Medium — calibration only meaningful with all signals active | Phase D sequenced last. Requires production runs with B+C features enabled. | T15b | ✅ addressed (phasing) |
| RE-24 | lateral | `.lab-runtime/calibration-results/` — PI-11 reads/writes calibration data | Low — directory already exists, format additive | Add surprise_weight field to calibration records | T15b | ✅ addressed |
| RE-25 | upstream | Visit tiers T0/T1/T2 — surprise score depends on multi-tier analysis | None — visit tiers already exist and produce signals | Used as-is | T15b | ✅ addressed |

---

## Governance Conditions Verification

| RC-ID | Condition | Status | Evidence |
|-------|-----------|--------|----------|
| RC-7 | Seki detection behavioral verification | ✅ Addressed | Config+code wired (stopping condition #3). Informational only. |
| RC-8 | F-8 tracked as deferred-with-player-impact | ✅ Addressed | Listed in charter non-goals §3 with explicit note. |
| Must-hold 1 | ownership_delta_weight defaults to 0.0 | ✅ In plan | T1 adds field with default=0.0 |
| Must-hold 2 | PI-4 integration test | ✅ In plan | TS-3 in test strategy, T6 in tasks |
| Must-hold 3 | Absent key = current behavior | ✅ In plan | Pydantic defaults, v1.14 pattern |
| Must-hold 4 | AGENTS.md updated | ✅ In plan | T7 explicitly |
| Must-hold 5 | Metrics baselines | ✅ Resolved (Gate 8 EX-9) | `BatchSummaryAccumulator` extended with `ownership_delta_used` + `score_delta_rescues`. Outstanding: `opponent_response_emitted` → T16c. |

---

## PI-10 Composition Refinement Findings (Gate 5)

| F-ID | Severity | Finding | Resolution |
|------|----------|---------|------------|
| F9 | Low | Original 6 opponent-response templates mapped to 12 conditions by shared scenario key — lossy mapping | ✅ Replaced with 1:1 condition-keyed templates (12 conditions, 5 active + 7 suppressed) |
| F10 | Medium | `capturing_race_lost` WM at 9 words exceeded budget when opponent-response appended (16 total) | ✅ Reshaped to "Loses the race." (3w), combined total now 10w |
| F11 | Low | `default` opponent-response "punishes the mistake" violated VP-5 (sentiment on non-almost_correct) | ✅ Changed to "responds decisively." (RC-1) |
| F12 | Low | `assemble_wrong_comment()` missing `_count_words()` guard (only enforced on correct-move path) | ✅ Added to T4b scope |
| F13 | Info | 7 conditions already fully describe opponent action in wrong-move template — opponent-response would be redundant | ✅ Suppressed via `enabled_conditions` array in config |
| F14 | Info | Lee Sedol proposed WM reshaping for all opponent-action conditions — larger scope, deferred | ✅ Tracked as RC-2 follow-up |

### Additional Ripple-Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-15 | lateral | `config/teaching-comments.json` — 9 wrong-move templates need VP-3 cleanup (article removal) | Low — text-only changes | Same commit as opponent-response addition | T4b | ✅ addressed |
| RE-16 | lateral | `docs/concepts/teaching-comments.md` — wrong-move template table is now stale | Low — doc update | D73 ADR in katago-enrichment.md + concepts doc update | T7 | ✅ addressed |
| RE-17 | downstream | Frontend `C[]` display — longer combined comments (up to 12w) may affect UI text layout | Low — 15w cap enforced; frontend wraps text | Verify with screenshot tests if available | T6 (TS-5) | ✅ addressed |

> **See also**:
> - [Plan: 30-plan.md](30-plan.md) — Architecture details
> - [Tasks: 40-tasks.md](40-tasks.md) — Task breakdown
> - [Charter: 00-charter.md](00-charter.md) — Classification tables
