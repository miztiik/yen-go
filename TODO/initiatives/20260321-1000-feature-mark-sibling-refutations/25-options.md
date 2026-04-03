# Options — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Options Comparison

| Field | OPT-1: Backend Pipeline Fix (Structural Sibling Heuristic) | OPT-2: Frontend Fallback Fix |
|-------|-------------------------------------------------------------|------------------------------|
| **Approach** | Add `mark_sibling_refutations()` to `core/correctness.py`. Walks entire solution tree post-parse, finds player-move siblings where exactly 1 is marked correct, marks `None` siblings as `is_correct=False`. SGFBuilder then emits `BM[1]` + `C[Wrong]` automatically. | Modify frontend `buildSolutionNodeFromSGF()` to infer sibling correctness at render time: if a node has no markers but a sibling does, mark it wrong. |
| **Benefits** | Fixes data at source. All downstream consumers (quality, complexity, search, frontend) automatically benefit. Single source of truth. No frontend complexity. | No pipeline re-run needed. Immediate effect for all existing puzzles. |
| **Drawbacks** | Requires pipeline re-run to apply to existing puzzles. | Adds correctness logic to frontend (violates SRP). Doesn't fix quality/complexity metrics. Other consumers still see wrong data. Duplicates backend logic. |
| **Risks** | False positive on miai puzzles → mitigated by "exactly 1 correct sibling" guard. | Frontend tree walk could impact render performance. Logic drift between backend and frontend correctness inference. |
| **Complexity** | Low — ~40 lines of Python tree walk + ~80 lines of tests. | Medium — TypeScript tree walk + test + ongoing sync with backend. |
| **Test Impact** | Unit tests for `mark_sibling_refutations()` + frontend regression test for BM+C[Wrong] detection (already works). | Frontend unit tests + integration tests for new inference logic. |
| **Rollback** | Remove function call from analyze stage. Re-run pipeline. | Revert frontend change. Instant. |
| **Architecture Compliance** | ✅ Correctness logic in `core/correctness.py` (SRP). Pipeline-first data quality. | ❌ Correctness logic in frontend (violates architecture rule: services must be view-agnostic). |
| **Downstream Impact** | `count_refutation_moves()`, `compute_avg_refutation_depth()` automatically improve. | No metric improvement. Backend still has wrong data. |
| **Recommendation** | ✅ **Recommended** | ❌ Not recommended |

## Prior Governance Decision

The governance panel (7 members: Cho Chikun 9p, Lee Sedol 9p, Shin Jinseo 9p, Ke Jie 9p, Staff Engineers A & B, Hana Park 1p) **unanimously selected OPT-1 (Backend Pipeline Fix)** in the first review round (`GOV-OPTIONS-REVISE`). The revision was procedural (create formal initiative artifacts), not substantive.

## Selection Rationale

OPT-1 is the clear winner:
1. **Data quality at source** — fixes the root cause, not a symptom.
2. **All consumers benefit** — frontend, quality metrics, complexity metrics, search index.
3. **Architecture compliance** — correctness logic belongs in `core/correctness.py`.
4. **Lower complexity** — simple tree walk, no frontend logic duplication.
5. **SOLID/SRP** — single responsibility, single source of truth.
