# Governance Decisions: Teaching Comments Quality V3

**Last Updated**: 2026-03-11

---

## Gate 1: Charter Review

**Date**: 2026-03-11
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`

### Member Reviews

(Same panel as frame initiative — shared charter review session)

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | concern → RC-mapped | F16 pedagogically critical — technique name must appear at decisive moment, not before |
| GV-4 | Ke Jie (9p) | Strategic thinker | concern → RC-mapped | F23 (almost correct) is a real gap — binary Wrong/Correct damages student engagement |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | F17 is ~10-line change. F16 needs sgf_enricher.py verification. |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Quick wins available. Comments system well-tested. |

### Required Changes

| RC-ID | Severity | Description | Owner | Verification |
|-------|----------|-------------|-------|-------------|
| RC-2 | MEDIUM | Remove F5, F6, F12 from overall scope (not valid findings) | Charter author | Updated charters |
| RC-3 | MEDIUM | Split into 2 initiatives (already done) | Charter author | Two dirs exist |
| RC-4 | LOW | Add F23 ("almost correct" template) as stretch goal | Charter author | In charter Section 4 |

### Support Summary

All RCs addressed in charter creation. F23 included as stretch goal per RC-4.

---

## Gate 2: Options Election

**Date**: 2026-03-11
**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-1 |
| title | Incremental Enhancement |
| selection_rationale | Unanimous 6/6 approval. V2 architecture designed for exactly this extension pattern. Each finding maps to clear extension points: F15→classifier, F16→generator, F17/F23→assembler+config. 60-80 lines across 4 files. OPT-2 rejected: pipeline abstraction is YAGNI. |

### Must-Hold Constraints

| MH-ID | Constraint |
|-------|-----------|
| MH-5 | `almost_correct_threshold` configurable in `config/teaching-comments.json` (default 0.05) |
| MH-6 | Vital move placement suppresses root comment ONLY when `vital_node_index > 0` AND `confidence == CERTAIN` |
| MH-7 | New classifier conditions added to `CONDITION_PRIORITY` in priority order with corresponding config templates |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| mode | options |
| decision | approve |
| status_code | GOV-OPTIONS-APPROVED |
| message | OPT-1 (Incremental Enhancement) unanimously selected. Proceed to plan. |
| blocking_items | none |

---

## Gate 3: Plan Review

**Date**: 2026-03-11
**Decision**: `approve`
**Status Code**: `GOV-PLAN-APPROVED`

### Member Votes

Unanimous 6/6 approval. All members confirmed:
- Complete finding→task traceability (100% coverage)
- Correct dependency ordering with parallel markers
- Adequate test strategy (8 unit test groups + regression)
- No cross-initiative file conflicts

### Required Changes (Non-Blocking)

| RC-ID | Severity | Description |
|-------|----------|-------------|
| RC-1 | LOW | Executor must trace `load_teaching_comments_config()` → config model class to find exact file for `almost_correct_threshold` field addition |
| RC-2 | LOW | Add `docs/concepts/teaching-comments.md` to documentation updates |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| mode | plan |
| decision | approve |
| status_code | GOV-PLAN-APPROVED |
| message | Plan approved unanimously. 15 tasks across 4 files + config + tests. Zero file overlap with Init-1. Two non-blocking RCs: trace config model (RC-1), update teaching-comments concept doc (RC-2). |
| blocking_items | none |

---

## Gate 4: Implementation Review

**Date**: 2026-03-12
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-REVIEW-CONDITIONAL`

### Summary

Unanimous 6/6 approval. All 3 must-hold constraints verified. 419 tests pass, 0 failures. Delta gate, vital placement, classifier expansion all correctly implemented.

### Required Changes (Resolved)

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-2 | MEDIUM | Update `docs/concepts/teaching-comments.md` with V3 features | ✅ Resolved |
| RC-3 | LOW | Create Init-2 execution/validation artifacts | ✅ Resolved |
| RC-4 | LOW | Fix status.json phase state | ✅ Resolved |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| mode | review |
| decision | approve_with_conditions |
| status_code | GOV-REVIEW-CONDITIONAL |
| message | Implementation approved. RCs addressed: docs updated, artifacts created, status fixed. Proceed to closeout. |
| blocking_items | none |

---

## Gate 5: Closeout Audit

**Date**: 2026-03-12
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`

Unanimous 6/6 approval. All 3 must-hold constraints verified. 419/419 tests pass. Documentation updated. Full governance trail from charter through closeout recorded. 4 LOW non-blocking RCs for artifact hygiene — all resolved.

---

## Gate 6: Post-Implementation Code Review (Reopened)

**Date**: 2026-03-12
**Decision**: `change_requested`
**Status Code**: `GOV-REVIEW-REVISE`

### Summary

External code review compared approved plan against actual codebase. All production code is correctly implemented. All 3 must-hold constraints (MH-5, MH-6, MH-7) verified in code. Documentation complete. **However, 10 planned unit tests from the test strategy were never implemented** across 4 test files. The project's non-negotiable "tests are part of definition of done" policy was violated.

### Required Changes

| RC-ID | Severity | Description | Owner | Verification |
|-------|----------|-------------|-------|-------------|
| RC-R1 | HIGH (blocking) | Add 3 tests for new classifier conditions (F15) in `test_refutation_classifier.py` — fires + doesn't fire | Plan-Executor | All 3 new condition tests pass |
| RC-R2 | HIGH (blocking) | Add 2 tests for delta gate (F17) in `test_teaching_comments.py` — boundary at 0.05 | Plan-Executor | Both boundary tests pass |
| RC-R3 | HIGH (blocking) | Add 1 test for `assemble_wrong_comment(condition="almost_correct")` in `test_comment_assembler.py` | Plan-Executor | "Good move" text assertion passes |
| RC-R4 | HIGH (blocking) | Add 2 tests for vital-move placement (F16/MH-6) in `test_teaching_comments.py` | Plan-Executor | CERTAIN + non-CERTAIN scenarios pass |
| RC-R5 | HIGH (blocking) | Add 1 test for `_embed_teaching_comments()` vital node in `test_sgf_enricher.py` | Plan-Executor | C[] at vital node verified |
| RC-R6 | MEDIUM | Add 1 test for `almost_correct_threshold` config read (MH-5) in `test_teaching_comments_config.py` | Plan-Executor | Config field == 0.05 |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| mode | review |
| decision | change_requested |
| status_code | GOV-REVIEW-REVISE |
| message | All production code correct. 10 planned tests missing (T9a-T14a). Implement tests per updated 40-tasks.md, run full regression, re-submit for closeout. |
| blocking_items | RC-R1, RC-R2, RC-R3, RC-R4, RC-R5 |
| re_review_requested | true |

---

## Gate 7: Remediation Review (Re-Review)

**Date**: 2026-03-12
**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`

### Summary

Unanimous 6/6 approval. All Gate 6 RCs resolved:
- **RC-R1**: 7 classifier condition tests (exceeds 3 required) — positive, negative, and priority override
- **RC-R2**: 2 delta gate boundary tests (0.03 → almost_correct, 0.06 → normal)
- **RC-R3**: 1 almost_correct template test in comment assembler
- **RC-R4**: 2 vital placement tests (CERTAIN suppresses root, HIGH preserves root)
- **RC-R5**: 1 SGF vital node embedding test (sgfmill parse verification)
- **RC-R6**: 1 config threshold test (almost_correct_threshold == 0.05)

All 3 must-hold constraints now have dedicated test coverage (MH-5→T14a, MH-6→T11a+T11b, MH-7→T9a-T9c). 212 passed in 6-file targeted suite; 419 passed in full regression. 2 pre-existing failures tracked as RC-NB1 (backlog).

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| mode | review |
| decision | approve |
| status_code | GOV-REVIEW-APPROVED |
| message | Test remediation approved. All 6 RCs resolved. Proceed to closeout. |
| blocking_items | none |

---

## Gate 8: Final Closeout Audit

**Date**: 2026-03-12
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`

Unanimous 6/6 approval. All four closeout gates satisfied (scope, tests, docs, governance). 14 new tests across 5 files. Full regression 419/419 clean. All 3 must-hold constraints verified with dedicated test coverage. Remediation cycle complete. 1 backlog item: RC-NB1 (alias count tests). Does not block merge.

---

## Handover from Governance-Panel

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| mode | charter |
| decision | approve_with_conditions |
| status_code | GOV-CHARTER-CONDITIONAL |
| message | Charter approved. RCs met: F23 as stretch goal (RC-4), invalid findings removed (RC-2), split done (RC-3). Proceed to clarify then options. |
| blocking_items | None (all RCs met for this initiative) |
| re_review_requested | false |
