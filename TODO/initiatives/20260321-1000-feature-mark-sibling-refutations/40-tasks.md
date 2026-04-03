# Tasks — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Selected Option: OPT-1 (Backend Pipeline Fix)
> Last Updated: 2026-03-21

## Task Graph

Dependencies flow top-to-bottom. Tasks marked `[P]` can run in parallel with their siblings at the same dependency level.

### Phase 1: Core Implementation

- [ ] **T1** — Add `_has_correctness_signal()` helper to `core/correctness.py`
  - **File:** `backend/puzzle_manager/core/correctness.py`
  - **Scope:** ~15 lines. Private helper function that checks if a `SolutionNode` has any explicit Layer 1 (SGF markers) or Layer 2 (comment text) correctness signal.
  - **Dependencies:** None
  - **AC:** Returns `True` for nodes with BM/TR/TE/IT markers or Correct/Wrong/Right/Incorrect comment prefixes. Returns `False` for nodes with no signal.

- [ ] **T2** — Add `mark_sibling_refutations(root: SolutionNode) -> int` to `core/correctness.py`
  - **File:** `backend/puzzle_manager/core/correctness.py`
  - **Scope:** ~35 lines. Public function that walks the solution tree recursively, finds sibling sets where exactly 1 child is explicitly correct, and marks unmarked siblings as `is_correct=False`.
  - **Dependencies:** T1
  - **AC:** 
    - Traverses all depths recursively
    - Only marks player-move nodes (`move is not None`)
    - Miai guard: skips when ≥2 siblings are explicitly correct
    - Returns count of nodes marked
    - Handles edge cases: empty tree, single child, no children, no markers

- [ ] **T3** — Update module docstring in `core/correctness.py`
  - **File:** `backend/puzzle_manager/core/correctness.py`
  - **Scope:** ~2 lines. Add `mark_sibling_refutations` to the "Used by:" list in the module docstring.
  - **Dependencies:** T2
  - **AC:** Module docstring reflects the new function and its call site.

### Phase 2: Integration

- [ ] **T4** — Integrate `mark_sibling_refutations()` call in `stages/analyze.py`
  - **File:** `backend/puzzle_manager/stages/analyze.py`
  - **Scope:** ~8 lines. Import + call after `parse_sgf()`, before quality/complexity computation. Add debug logging for marked count.
  - **Dependencies:** T2
  - **AC:** Function is called for every puzzle with a solution tree. Debug log emitted when nodes are marked. Called BEFORE `compute_quality_metrics()` and `compute_complexity_metrics()`.

### Phase 3: Tests (can parallelize within phase)

- [ ] **T5** `[P]` — Unit tests for `_has_correctness_signal()`
  - **File:** `backend/puzzle_manager/tests/unit/test_correctness.py`
  - **Scope:** ~40 lines. Tests for BM/TE/IT/TR markers, Correct/Wrong comments, no-signal nodes, empty comments, comment-only nodes.
  - **Dependencies:** T1
  - **AC:** All signal types detected. No-signal nodes correctly return `False`.

- [ ] **T6** `[P]` — Unit tests for `mark_sibling_refutations()` — core cases
  - **File:** `backend/puzzle_manager/tests/unit/test_correctness.py`
  - **Scope:** ~80 lines. Tests:
    - `puzzle_14_net` topology: 3 unmarked wrong siblings → all marked
    - Single child (no siblings) → no change
    - All children marked → no change
    - No solution tree → returns 0
    - Empty children → returns 0
    - Opponent-only nodes (no `move`) → not marked
  - **Dependencies:** T2
  - **AC:** All topology variants tested. Return counts correct.

- [ ] **T7** `[P]` — Unit test for miai edge case
  - **File:** `backend/puzzle_manager/tests/unit/test_correctness.py`
  - **Scope:** ~25 lines. Test: 2+ siblings explicitly correct, 1 unmarked → unmarked sibling is NOT marked as wrong.
  - **Dependencies:** T2
  - **AC:** Miai guard works. `None` siblings left unchanged when ≥2 siblings are correct.

- [ ] **T8** `[P]` — Integration test: metrics improvement after marking
  - **File:** `backend/puzzle_manager/tests/unit/test_correctness.py`
  - **Scope:** ~20 lines. Build a tree with unmarked siblings, call `mark_sibling_refutations()`, then verify `count_refutation_moves()` returns higher count and `compute_avg_refutation_depth()` returns non-zero.
  - **Dependencies:** T2
  - **AC:** Metrics reflect the corrected data.

- [ ] **T9** `[P]` — Frontend regression test: `buildSolutionNodeFromSGF` with BM+C[Wrong]
  - **File:** `frontend/tests/unit/solution-tree.test.ts`
  - **Scope:** ~30 lines. Test that an SGF node with `BM: '1'` + `C: 'Wrong'` produces `isCorrect: false` in the output `SolutionNode`.
  - **Dependencies:** None (frontend test, independent of backend)
  - **AC:** Frontend correctly detects BM+C[Wrong] as wrong move.

### Phase 4: Documentation

- [ ] **T10** `[P]` — Update `backend/puzzle_manager/AGENTS.md`
  - **File:** `backend/puzzle_manager/AGENTS.md`
  - **Scope:** ~2 lines. Add `core/correctness.py` entry mentioning `mark_sibling_refutations()` in the core module table.
  - **Dependencies:** T2
  - **AC:** AGENTS.md reflects the new function.

### Phase 5: Regression

- [ ] **T11** — Run backend unit tests: `pytest backend/ -m unit -q --no-header --tb=short`
  - **Dependencies:** T4, T5, T6, T7, T8
  - **AC:** All tests pass, including new tests.

- [ ] **T12** — Run frontend tests: `npx vitest run --no-coverage`
  - **Dependencies:** T9
  - **AC:** All tests pass, including new test.

## Task Summary

| ID | Phase | Description | Files | Parallel? |
|----|-------|-------------|-------|-----------|
| T1 | 1 | `_has_correctness_signal()` helper | `core/correctness.py` | — |
| T2 | 1 | `mark_sibling_refutations()` function | `core/correctness.py` | — |
| T3 | 1 | Module docstring update | `core/correctness.py` | — |
| T4 | 2 | Analyze stage integration | `stages/analyze.py` | — |
| T5 | 3 | Unit tests: `_has_correctness_signal` | `tests/unit/test_correctness.py` | [P] |
| T6 | 3 | Unit tests: core marking cases | `tests/unit/test_correctness.py` | [P] |
| T7 | 3 | Unit test: miai edge case | `tests/unit/test_correctness.py` | [P] |
| T8 | 3 | Integration test: metrics improvement | `tests/unit/test_correctness.py` | [P] |
| T9 | 3 | Frontend regression test | `frontend/tests/unit/solution-tree.test.ts` | [P] |
| T10 | 4 | AGENTS.md update | `backend/puzzle_manager/AGENTS.md` | [P] |
| T11 | 5 | Backend regression run | — | — |
| T12 | 5 | Frontend regression run | — | — |

## Dependency Graph

```
T1 ──→ T2 ──→ T3
              ├──→ T4 ──→ T11
              ├──→ T5 ─────→ T11
              ├──→ T6 ─────→ T11
              ├──→ T7 ─────→ T11
              ├──→ T8 ─────→ T11
              └──→ T10

T9 (independent) ──→ T12
```
