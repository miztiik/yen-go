# Analysis — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 90 |
| Risk Level | low |
| Research Invoked | No (internal code fully traced, no external patterns needed) |

**Score breakdown**: Start 100, -10 (test strategy needs scenario-level coverage matrix = minor uncertainty). No architecture seams unclear, no external precedent needed, no security impact.

## Cross-Artifact Consistency

| check_id | artifact | finding | severity |
|----------|----------|---------|----------|
| CA-1 | Charter ↔ Plan | All 3 problems (P1, P2, P3) mapped to specific plan sections (AD-1 through AD-4). ✅ | OK |
| CA-2 | Plan ↔ Tasks | Each AD maps to at least one task. AD-1→T1, AD-2→T2, AD-3→T3, AD-4→T4, AD-5→T6. ✅ | OK |
| CA-3 | Tasks ↔ Success Criteria | SC-1→T7, SC-2→T8, SC-3→T10, SC-4→T1, SC-5→T9, SC-6→T7-T11. ✅ | OK |
| CA-4 | Options ↔ Governance | Selected OPT-1 matches GOV-OPTIONS-APPROVED per-question selections. ✅ | OK |
| CA-5 | Predecessor charter | RC-1 through RC-4 from predecessor are NOT touched (in scope confirmation). ✅ | OK |

## Coverage Map

| Scenario | Covered by Task | Test Task | Status |
|----------|-----------------|-----------|--------|
| A (all-almost, zero-feedback) | T1 (remove all-skip) | T7 | ✅ mapped |
| B (mixed, works correctly) | — (no change) | T9 (regression) | ✅ mapped |
| C (all true wrong, works) | — (no change) | T9 (regression) | ✅ mapped |
| D (curated + AI coexist) | T2, T5 (gate removal, dedup) | T8, T11 | ✅ mapped |
| E (no wrongs found) | — (no change) | — (no behavioral change) | ✅ trivial |
| F (position-only, same as A) | T1 (all-skip removal applies to all paths) | T7 (can extend) | ✅ mapped |

## Unmapped Tasks

None. All tasks trace to charter scope items and success criteria.

## Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | `solve_position.py` → produces `result.refutations` | None — unchanged input | No change needed | — | ✅ addressed |
| RE-2 | upstream | `config/katago-enrichment.json` → `max_refutation_root_trees` | Config read added in enricher | Read-only, config is stable | T2 | ✅ addressed |
| RE-3 | downstream | `teaching_comments.py` → generates per-move comments | Template change propagates via config, coord change is code fix | T4 ensures no spoiler coord | T3, T4 | ✅ addressed |
| RE-4 | downstream | `infer_correctness_from_comment()` → frontend uses this | "Wrong." prefix preserved. No detection change. | T1 preserves "Wrong." prefix via `_build_refutation_branches()` | T1 | ✅ addressed |
| RE-5 | lateral | Existing tests checking `skipped_all_almost` or "Close —" text | Tests may fail if they assert old behavior | Grep for affected tests, update to new expected behavior | T7 | ❌ needs action |
| RE-6 | lateral | YR property derivation | `skipped_all_almost` guard on YR removed; YR now set for all-almost scenarios | Correct behavior — YR should reflect all wrongs | T1 | ✅ addressed |
| RE-7 | downstream | `_has_existing_refutation_branches` → called in sgf_enricher only? | If other callers exist, removal in T6 would break them | Grep before removing; keep if callers found | T6 | ❌ needs action |
| RE-8 | lateral | AI branch coord overlaps curated branch coord | Duplicate branches in SGF tree | T5 adds dedup filter | T5 | ✅ addressed |

## Findings

| finding_id | severity | finding | resolution |
|-----------|----------|---------|------------|
| F1 | Major | RE-5: Existing tests may assert old `skipped_all_almost` behavior or "Close —" template text | Grep for affected tests during T7; update expected values |
| F2 | Minor | RE-7: Must verify `_has_existing_refutation_branches` has no other callers before deleting | Grep in T6 before deletion |
| F3 | Info | Lee Sedol (GV-2) prefers template Option B ("there's a slightly better option"). Config-tunable post-implementation. | Document in charter as noted preference. No code impact. |
| F4 | Info | Re-enrichment campaign for affected puzzles tracked as follow-up per GV-7 (Hana Park). | Out of scope. Track separately. |

Last Updated: 2026-03-20
