# Analysis — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 100 |
| Risk Level | low |
| Research Invoked | No (score ≥ 70, risk low) |

## Consistency & Coverage Check

### Charter ↔ Clarifications

| ID | Check | Status |
|----|-------|--------|
| F1 | All 6 clarification questions resolved with user-confirmed answers | ✅ |
| F2 | Backward compatibility explicitly addressed (Q6: not required, additive fix) | ✅ |
| F3 | Charter goals G1-G5 trace to clarification decisions (Q1→G1 scope, Q2→G1 miai, Q5→G1 location) | ✅ |
| F4 | Charter constraints C1-C8 consistent with clarification answers | ✅ |

### Charter ↔ Options

| ID | Check | Status |
|----|-------|--------|
| F5 | OPT-1 addresses all 5 charter goals | ✅ |
| F6 | OPT-2 included for meaningful comparison (not straw-man) | ✅ |
| F7 | Architecture compliance assessed for both options | ✅ |

### Options ↔ Plan

| ID | Check | Status |
|----|-------|--------|
| F8 | Plan derived from governance-selected OPT-1 | ✅ |
| F9 | Plan algorithm matches charter scope (recursive all-depth, Q1=C) | ✅ |
| F10 | Plan includes miai guard per Q2=B and must_hold_constraints | ✅ |
| F11 | Plan places function in `core/correctness.py` per Q5=B | ✅ |
| F12 | Plan call site is in `stages/analyze.py` after parse, before quality/complexity | ✅ |

### Plan ↔ Tasks

| ID | Check | Status |
|----|-------|--------|
| F13 | Every plan component maps to at least one task | ✅ |
| F14 | Task dependencies are acyclic and correctly ordered | ✅ |
| F15 | No task references a file outside the changed set | ✅ |
| F16 | All acceptance criteria (AC1-AC9) from charter are covered by tasks | ✅ |

### AC ↔ Task Traceability

| Charter AC | Task(s) | Status |
|-----------|---------|--------|
| AC1: mark_sibling_refutations marks wrong siblings | T2, T6 | ✅ |
| AC2: Miai edge case | T7 | ✅ |
| AC3: Edge cases (empty, single, none, opponent) | T6 | ✅ |
| AC4: count_refutation_moves increases | T8 | ✅ |
| AC5: compute_avg_refutation_depth non-zero | T8 | ✅ |
| AC6: Frontend BM+C[Wrong] detection | T9 | ✅ |
| AC7: Backend tests pass | T11 | ✅ |
| AC8: Frontend tests pass | T12 | ✅ |
| AC9: Called after parse, before quality | T4 | ✅ |

## Ripple-Effects Analysis

| ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|----|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | `sgf_parser.parse_sgf()` produces the `SolutionNode` tree | None — read-only dependency, no changes to parser | N/A | T2 | ✅ addressed |
| RE-2 | upstream | `infer_correctness()` returns `None` for unmarked nodes | None — this is the root cause we're fixing. No changes to infer_correctness. | N/A | T1 | ✅ addressed |
| RE-3 | downstream | `SGFBuilder._build_node()` reads `is_correct` to emit `BM[1]` | Positive impact — nodes marked `is_correct=False` will automatically get `BM[1]` + standardized `C[Wrong]` comment | Verified in research: builder already handles this | T2 | ✅ addressed |
| RE-4 | downstream | `count_refutation_moves()` counts `is_correct=False` nodes | Positive impact — refutation count increases for affected puzzles | T8 integration test verifies | T8 | ✅ addressed |
| RE-5 | downstream | `compute_avg_refutation_depth()` measures wrong-move subtree depths | Positive impact — avg depth becomes non-zero for affected puzzles | T8 integration test verifies | T8 | ✅ addressed |
| RE-6 | downstream | `extract_refutations()` in enrichment reads `is_correct` | Positive impact — refutation coordinates (YR) more accurate | No test needed — same is_correct dependency | T2 | ✅ addressed |
| RE-7 | downstream | Frontend `buildSolutionNodeFromSGF()` reads `BM` + comment | Positive impact — frontend now correctly shows "Wrong" for these moves | T9 regression test verifies | T9 | ✅ addressed |
| RE-8 | lateral | `yengo-search.db` (DB-1) `cx_refutations` field | Positive impact — publish stage re-computes metrics from corrected tree | No additional task — publish reads from analyzed SGF | T4 | ✅ addressed |
| RE-9 | lateral | Existing backend tests in `test_correctness.py` | No impact — new function tests are additive. Existing tests unchanged. | T11 regression run verifies | T11 | ✅ addressed |
| RE-10 | lateral | Existing frontend tests in `solution-tree.test.ts` | No impact — new test is additive. Existing tests unchanged. | T12 regression run verifies | T12 | ✅ addressed |
| RE-11 | lateral | `is_fully_enriched` skip check in analyze.py | Consideration — already-enriched puzzles re-analyzed with new heuristic | Call site placed before skip check so all puzzles get the fix | T4 | ✅ addressed |

## Coverage Map

| Area | Covered By | Gap? |
|------|-----------|------|
| Core heuristic logic | T1, T2 | No |
| Miai edge case | T7 | No |
| Edge cases (empty/single/none/opponent) | T6 | No |
| Pipeline integration | T4 | No |
| Downstream metrics | T8 | No |
| Frontend detection | T9 | No |
| Documentation | T3, T10 | No |
| Backend regression | T11 | No |
| Frontend regression | T12 | No |

## Unmapped Tasks

None. All tasks trace to charter goals, acceptance criteria, or documentation requirements.

## Findings Summary

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| F-1 | Info | Planning confidence 100, risk low — no research needed | Documented in 15-research.md |
| F-2 | Info | SGFBuilder already handles BM[1] + C[Wrong] serialization from is_correct | Confirmed in research; no builder changes needed |
| F-3 | Info | Call site placement matters: must be before quality/complexity AND before is_fully_enriched skip | T4 specifies insertion after parse_sgf, before skip check |
| F-4 | Info | `_has_correctness_signal()` re-checks Layer 1+2 independently — does not rely on `is_correct` field | Prevents false positive from default `is_correct=True` |
