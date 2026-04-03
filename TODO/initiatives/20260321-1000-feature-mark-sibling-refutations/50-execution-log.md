# Execution Log — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Executor: Plan-Executor
> Started: 2026-03-21
> Last Updated: 2026-03-21

## Parallel Lane Plan

All tasks in Phase 1-2 are sequential (dependency chain). Phase 3 tasks share a single file (`test_correctness.py`) so they were executed sequentially in a single lane. T9 and T10 are independent.

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T2, T3 | `core/correctness.py` | None → T1 → T2 → T3 | ✅ merged |
| L2 | T4 | `stages/analyze.py` | T2 | ✅ merged |
| L3 | T5, T6, T7, T8 | `tests/unit/test_correctness.py` | T1, T2 | ✅ merged |
| L4 | T9 | `frontend/tests/unit/solution-tree.test.ts` | None | ✅ merged |
| L5 | T10 | `backend/puzzle_manager/AGENTS.md` | T2 | ✅ merged |
| L6 | T11 | — (test run) | L1-L3, L5 | ✅ merged |
| L7 | T12 | — (test run) | L4 | ✅ merged |

## Per-Task Execution Log

### T1 — `_has_correctness_signal()` helper ✅

| ID | Detail |
|----|--------|
| EX-1 | Added `_has_correctness_signal(node: SolutionNode) -> bool` to `core/correctness.py` (~15 lines) |
| EX-2 | Added `from __future__ import annotations` and `TYPE_CHECKING` import for `SolutionNode` |
| EX-3 | Checks Layer 1 (BM/TR/TE/IT in `node.properties`) and Layer 2 (`infer_correctness_from_comment`) |

### T2 — `mark_sibling_refutations()` function ✅

| ID | Detail |
|----|--------|
| EX-4 | Added `mark_sibling_refutations(root: SolutionNode) -> int` (~45 lines) |
| EX-5 | Walks tree recursively, partitions children into explicitly_correct/unmarked |
| EX-6 | Marks unmarked siblings when exactly 1 sibling is correct |
| EX-7 | Miai guard: skips when ≥2 siblings are explicitly correct |
| EX-8 | Only marks player-move nodes (`child.move is not None`) |

### T3 — Module docstring update ✅

| ID | Detail |
|----|--------|
| EX-9 | Added `mark_sibling_refutations()` to "Used by:" list in module docstring |
| EX-10 | Added `stages/analyze.py` as call site |

### T4 — Analyze stage integration ✅

| ID | Detail |
|----|--------|
| EX-11 | Added import: `from backend.puzzle_manager.core.correctness import mark_sibling_refutations` |
| EX-12 | Call site: after `parse_sgf()`, before quality/complexity computation |
| EX-13 | Debug logging: `"Marked %d unmarked sibling refutations"` when count > 0 |
| EX-14 | Placed BEFORE `is_fully_enriched` skip check (ensures all puzzles get fix on re-analyze) |

### T5 — Unit tests: `_has_correctness_signal` ✅

| ID | Detail |
|----|--------|
| EX-15 | `TestHasCorrectnessSignal` class with 10 test methods |
| EX-16 | Tests: BM, TE, IT, TR markers; Correct/Wrong/RIGHT comments; no-signal; ambiguous comment; empty comment |

### T6 — Unit tests: core marking cases ✅

| ID | Detail |
|----|--------|
| EX-17 | `TestMarkSiblingRefutations` class with 7 test methods |
| EX-18 | Tests: puzzle_14_net topology, single child, all marked, empty tree, no markers, opponent-only nodes, recursive deep marking |

### T7 — Unit test: miai edge case ✅

| ID | Detail |
|----|--------|
| EX-19 | `TestMarkSiblingRefutationsMiai` class with 2 test methods |
| EX-20 | Tests: 2 correct siblings + unmarked → no change; 3 correct siblings → no change |

### T8 — Integration test: metrics improvement ✅

| ID | Detail |
|----|--------|
| EX-21 | `TestSiblingRefutationMetrics` class with 2 test methods |
| EX-22 | Tests: `count_refutation_moves()` returns higher count after marking; parsed SGF with RIGHT marker |
| EX-23 | Initial issue: `Point(row=0, col=0)` — `Point` uses positional args `(x, y)`. Fixed to `Point(0, 0)` |

### T9 — Frontend regression test ✅

| ID | Detail |
|----|--------|
| EX-24 | Added `SGF_PIPELINE_MARKED_REFUTATION` test fixture with BM[1] + C[Wrong] node |
| EX-25 | Test: `detects pipeline-marked sibling refutation (BM[1] + C[Wrong])` verifies `isCorrect: false` |

### T10 — AGENTS.md update ✅

| ID | Detail |
|----|--------|
| EX-26 | Added `core/correctness.py` entry to directory structure table in `backend/puzzle_manager/AGENTS.md` |
| EX-27 | Entry: `3-layer correctness inference; mark_sibling_refutations(root) fixes unmarked wrong siblings; _has_correctness_signal(node) helper` |

### T11 — Backend unit regression ✅

| ID | Detail |
|----|--------|
| EX-28 | Command: `pytest backend/ -m unit -q --no-header --tb=short` |
| EX-29 | Result: **1624 passed, 430 deselected, 0 failed** (9.14s) |
| EX-30 | First run had 8 failures due to `Point(row=0, col=0)` kwarg error — fixed in T8 |

### T12 — Frontend regression ✅

| ID | Detail |
|----|--------|
| EX-31 | Command: `npx vitest run tests/unit/solution-tree.test.ts --no-coverage --reporter=verbose` |
| EX-32 | Result: **26 passed (26)** including new T9 test |
| EX-33 | Full suite: `npx vitest run --no-coverage` → **88 test files, 1352 tests passed** (60.32s) |

## Deviations

| ID | Deviation | Resolution |
|----|-----------|------------|
| EX-34 | `Point` constructor uses `Point(x, y)` not `Point(row=0, col=0)` | Fixed test helpers in T6 and T7 classes to use `Point(0, 0)` |
| EX-35 | T8 `compute_avg_refutation_depth()` not used in final tests | Used `count_refutation_moves()` directly — simpler and sufficient to verify metrics improvement |
