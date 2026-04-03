# Governance Decisions — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Gate 1: Charter/Research Preflight

**Decision:** `approve`
**Status Code:** `GOV-CHARTER-APPROVED`

### Member Reviews

| ID | Member | Domain | Vote | Supporting Comment | Evidence |
|----|--------|--------|------|-------------------|----------|
| GV-1 | Cho Chikun 9p | Go domain | approve | The sibling heuristic correctly models standard tsumego convention. The miai guard (≥2 correct siblings → skip) is essential and well-specified. | 50+ years of professional tsumego authoring experience |
| GV-2 | Lee Sedol 9p | Go domain | approve | The problem statement accurately describes the goproblems.com convention. All 3 unmarked moves in puzzle_14_net are definitively wrong. | Direct reading of the position |
| GV-3 | Shin Jinseo 9p | Go domain | approve | Recursive all-depth scope is correct — the pattern occurs at all depths, not just first-move. | Analysis of affected corpus |
| GV-4 | Ke Jie 9p | Go domain | approve | The miai edge case guard is critical. Exactly-1-correct-sibling threshold prevents false positives on multi-answer puzzles. | Professional judgment on puzzle design patterns |
| GV-5 | Staff Engineer A | Backend architecture | approve | `core/correctness.py` is the right location. SRP is maintained. The function operates on in-memory `SolutionNode` tree and lets `SGFBuilder` handle serialization — clean separation. | Codebase analysis of correctness.py, sgf_builder.py, analyze.py |
| GV-6 | Staff Engineer B | Pipeline/testing | approve | Test strategy is clear: unit tests for the function, integration assertion for metrics, frontend regression test. Level 3 is appropriate. | Review of test patterns in tests/unit/test_correctness.py |
| GV-7 | Hana Park 1p | Domain + UX | approve | Fixing data at source ensures consistent UX across all puzzle sources. The frontend already handles BM[1]+C[Wrong], so no frontend code change is needed. | Frontend sgf-solution.ts analysis |

### Support Summary

Unanimous approval (7/7). Charter scope, research findings, and clarification answers are all well-grounded. No blocking items.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Feature-Planner",
  "message": "Charter and research approved. Proceed to options evaluation.",
  "required_next_actions": ["Generate options comparison", "Submit for options election"],
  "artifacts_to_update": ["25-options.md", "status.json"],
  "blocking_items": []
}
```

---

## Gate 2: Option Election

**Decision:** `approve`
**Status Code:** `GOV-OPTIONS-APPROVED`
**Selected Option:** OPT-1 (Backend Pipeline Fix — Structural Sibling Heuristic)

### Member Reviews

| ID | Member | Domain | Vote | Supporting Comment | Evidence |
|----|--------|--------|------|-------------------|----------|
| GV-8 | Cho Chikun 9p | Go domain | approve OPT-1 | Data quality must be fixed at the source. The pipeline is the right place to enforce correctness conventions. | Decades of tsumego publication experience |
| GV-9 | Lee Sedol 9p | Go domain | approve OPT-1 | OPT-2 (frontend fix) would mask the real problem. Agree with pipeline-first approach. | Professional reading accuracy |
| GV-10 | Shin Jinseo 9p | Go domain | approve OPT-1 | Backend fix is cleaner. Frontend should not contain correctness inference logic. | Architecture principle alignment |
| GV-11 | Ke Jie 9p | Go domain | approve OPT-1 | Metrics improvement is an important secondary benefit that only OPT-1 provides. | Analysis of rc/refutation_depth dependency on is_correct |
| GV-12 | Staff Engineer A | Backend architecture | approve OPT-1 | OPT-1 maintains architecture compliance. OPT-2 violates the rule that services must be view-agnostic. | Architecture rules review |
| GV-13 | Staff Engineer B | Pipeline/testing | approve OPT-1 | OPT-1 is ~40 lines of core logic + tests. OPT-2 requires ongoing sync between backend and frontend correctness logic. | Complexity analysis |
| GV-14 | Hana Park 1p | Domain + UX | approve OPT-1 | OPT-1 ensures all downstream consumers see correct data. UX improvement is automatic once pipeline runs. | Frontend consumer analysis |

### Selected Option

```json
{
  "option_id": "OPT-1",
  "title": "Backend Pipeline Fix — Structural Sibling Heuristic",
  "selection_rationale": "Unanimous selection. Fixes data at source, all downstream consumers benefit automatically, architecture-compliant, lower complexity than frontend alternative.",
  "must_hold_constraints": [
    "Miai guard: skip when ≥2 siblings already marked correct",
    "Only mark player-move nodes (skip opponent response nodes)",
    "Recursive all-depth traversal",
    "Function in core/correctness.py, call from analyze stage",
    "No new dependencies, no new files"
  ]
}
```

### Support Summary

Unanimous approval (7/7) for OPT-1. No conditions, no blocking items.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Feature-Planner",
  "message": "OPT-1 selected unanimously. Proceed to plan draft and task decomposition.",
  "required_next_actions": ["Draft 30-plan.md", "Draft 40-tasks.md", "Draft 20-analysis.md", "Submit for plan review"],
  "artifacts_to_update": ["30-plan.md", "40-tasks.md", "20-analysis.md", "status.json"],
  "blocking_items": []
}
```

---

## Gate 3: Plan Review

**Decision:** `approve`
**Status Code:** `GOV-PLAN-APPROVED`

### Member Reviews

| ID | Member | Domain | Vote | Supporting Comment | Evidence |
|----|--------|--------|------|-------------------|----------|
| GV-15 | Cho Chikun 9p | Go domain | approve | Algorithm correctly models tsumego convention: unmarked siblings of explicitly-correct leaves are wrong. The exactly-1-correct guard is sound. | Domain expertise in tsumego publication |
| GV-16 | Lee Sedol 9p | Go domain | approve | Recursive all-depth traversal is necessary. The puzzle_14_net example is accurately analyzed. | Professional reading of example position |
| GV-17 | Shin Jinseo 9p | Go domain | approve | Player-move-only filter is correct — opponent response nodes don't carry correctness semantics in tsumego. | Go theory alignment |
| GV-18 | Ke Jie 9p | Go domain | approve | Miai guard threshold of exactly-1-correct is the right threshold. Prevents false positives while maximizing coverage. | Analysis of multi-answer puzzle patterns |
| GV-19 | Staff Engineer A | Backend architecture | approve | Architecture is clean: `_has_correctness_signal()` re-checks Layer 1+2 independently (doesn't rely on `is_correct` default). SGFBuilder handles serialization. Call site in analyze.py is correct. | Code review of correctness.py, sgf_builder.py, analyze.py |
| GV-20 | Staff Engineer B | Pipeline/testing | approve | Task decomposition is complete. 12 tasks, clear dependency graph. All AC from charter traced to tasks. Ripple effects table shows all downstream impacts addressed. Test strategy covers core, edge, miai, metrics, and frontend. | Review of 40-tasks.md and 20-analysis.md |
| GV-21 | Hana Park 1p | Domain + UX | approve | No frontend code changes needed — the fix is purely data-quality. Frontend regression test (T9) confirms existing BM+C[Wrong] handling works. | Frontend sgf-solution.ts analysis |

### Support Summary

Unanimous approval (7/7). Plan is architecture-compliant, well-tested, and covers all acceptance criteria. No conditions, no blocking items.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Plan-Executor",
  "message": "Plan approved unanimously. Execute tasks T1-T12 per dependency order. Start with T1 (helper function), then T2 (main function), then T3-T4 (integration), then T5-T10 (parallel tests/docs), then T11-T12 (regression).",
  "required_next_actions": [
    "Execute T1: Add _has_correctness_signal() to core/correctness.py",
    "Execute T2: Add mark_sibling_refutations() to core/correctness.py",
    "Execute T3: Update module docstring",
    "Execute T4: Integrate in stages/analyze.py",
    "Execute T5-T9: Add tests (parallelizable)",
    "Execute T10: Update AGENTS.md",
    "Execute T11-T12: Regression verification"
  ],
  "artifacts_to_update": ["status.json", "50-execution-log.md"],
  "blocking_items": []
}
```

---

## Gate 4: Implementation Review

**Decision:** `approve`
**Status Code:** `GOV-IMPL-APPROVED`

### Member Reviews

| ID | Member | Domain | Vote | Supporting Comment | Evidence |
|----|--------|--------|------|-------------------|----------|
| GV-22 | Cho Chikun 9p | Go domain | approve | Miai guard correctly implemented — `len(explicitly_correct) == 1` prevents false positives on multi-answer puzzles. | `correctness.py` L215; `TestMarkSiblingRefutationsMiai` |
| GV-23 | Lee Sedol 9p | Go domain | approve | `move is not None` guard correctly excludes setup/pass nodes from marking. Recursive deep marking tested. | `correctness.py` L219; `test_opponent_only_nodes_not_marked`, `test_recursive_deep_marking` |
| GV-24 | Shin Jinseo 9p | Frontend | approve | End-to-end flow verified: backend `is_correct=False` → `SGFBuilder` writes `BM[1]` → frontend detects `isCorrect: false`. | `sgf_builder.py` L636; `solution-tree.test.ts` L559 |
| GV-25 | Ke Jie 9p | Safety | approve | Function mutates in-memory `SolutionNode` only. Call site placed correctly before `compute_quality_metrics()`. | `analyze.py` L263 |
| GV-26 | Staff Engineer A | Architecture | approve | Clean scope: 2 prod files, `_has_correctness_signal` reuses `infer_correctness_from_comment` (DRY), `TYPE_CHECKING` import avoids circular deps. | Import structure review |
| GV-27 | Staff Engineer B | Testing | approve | 21 new backend tests + 1 frontend regression. 1624 backend passed, 1352 frontend passed. No regressions. | Test run evidence |
| GV-28 | Hana Park 1p | Documentation | approve | AGENTS.md updated in same commit. Module docstring updated. Debug logging at call site. | D1-D3 complete |

### Support Summary

Unanimous approval (7/7). Minimal scope, robust guards, comprehensive tests, architecture-compliant.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Plan-Executor",
  "message": "Implementation approved unanimously. Proceed to closeout.",
  "required_next_actions": ["Closeout audit"],
  "artifacts_to_update": ["status.json"],
  "blocking_items": []
}
```

---

## Gate 5: Closeout Audit

**Decision:** `approve`
**Status Code:** `GOV-CLOSEOUT-APPROVED`

### Member Reviews

| ID | Member | Domain | Vote | Supporting Comment | Evidence |
|----|--------|--------|------|-------------------|----------|
| GV-29 | Cho Chikun 9p | Go domain | approve | Algorithm correctly models tsumego convention. Test cases match real-world patterns. | `test_puzzle_14_net_topology` |
| GV-30 | Lee Sedol 9p | Go domain | approve | Edge case battery is complete: empty tree, single child, all marked, no markers, miai. | 7 edge case tests |
| GV-31 | Shin Jinseo 9p | Go domain | approve | Recursive all-depth traversal + player-move filter are sound. | Tests verified |
| GV-32 | Ke Jie 9p | Go domain | approve | No false positives from any edge case topology. | All 21 tests pass |
| GV-33 | Staff Engineer A | Architecture | approve | Architecture boundaries maintained. No `[DEBUG]` leakage. | Code review |
| GV-34 | Staff Engineer B | Testing | approve | All 8 AC traced to tests. All 6 ripple effects verified. Zero regressions. | `60-validation-report.md` |
| GV-35 | Hana Park 1p | Documentation | approve | Cross-references complete: module docstring, AGENTS.md, debug logging. | D1-D3 verified |

### Support Summary

Unanimous approval (7/7). All artifacts present, coherent, and complete. All gates passed. Zero open items. Initiative ready to close.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Plan-Executor",
  "message": "GOV-CLOSEOUT-APPROVED. Initiative cleared for closure.",
  "required_next_actions": ["Set status.json closeout=approved, current_phase=closeout"],
  "artifacts_to_update": ["status.json"],
  "blocking_items": []
}
```
