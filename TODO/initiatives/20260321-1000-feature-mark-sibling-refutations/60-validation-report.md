# Validation Report — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Test Results

### Backend Unit Tests

| VAL-1 | Command | `pytest backend/ -m unit -q --no-header --tb=short` |
|-------|---------|------------------------------------------------------|
| | Exit Code | 0 |
| | Result | **1624 passed, 430 deselected, 0 failed** |
| | Duration | 9.14s |
| | New Tests | 21 tests in 4 new classes (TestHasCorrectnessSignal: 10, TestMarkSiblingRefutations: 7, TestMarkSiblingRefutationsMiai: 2, TestSiblingRefutationMetrics: 2) |

### Frontend Tests

| VAL-2 | Command | `npx vitest run tests/unit/solution-tree.test.ts --no-coverage` |
|-------|---------|------------------------------------------------------------------|
| | Exit Code | 0 |
| | Result | **26 passed (26)** |
| | New Tests | 1 test: `detects pipeline-marked sibling refutation (BM[1] + C[Wrong])` |

| VAL-3 | Command | `npx vitest run --no-coverage` (full suite) |
|-------|---------|----------------------------------------------|
| | Exit Code | 0 |
| | Result | **88 test files, 1352 tests passed** |
| | Duration | 60.32s |

## Ripple Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| RE-1 | `count_refutation_moves()` returns higher count for puzzles with newly-marked siblings | `TestSiblingRefutationMetrics.test_refutation_count_increases` verifies `rc == 2` after marking 2 siblings | Match | — | ✅ verified |
| RE-2 | `SGFBuilder` emits `BM[1]` + `C[Wrong]` for `is_correct=False` nodes | Existing `SGFBuilder._build_node()` already handles this — no code change needed, confirmed by code review | Match | — | ✅ verified |
| RE-3 | Frontend `buildSolutionNodeFromSGF()` detects BM+C[Wrong] as `isCorrect: false` | T9 test verifies this explicitly | Match | — | ✅ verified |
| RE-4 | No interference with existing correctness tests (Layer 1/2/3) | All 42 pre-existing tests in `test_correctness.py` still pass | Match | — | ✅ verified |
| RE-5 | analyze stage call site doesn't break pipeline flow for puzzles without solution tree | Guard: `if game.solution_tree:` — null-safe | Match | — | ✅ verified |
| RE-6 | AGENTS.md reflects new function | Entry added to core module table | Match | — | ✅ verified |

## Documentation Validation

| VAL-4 | D1: Module docstring | Updated in `core/correctness.py` — mentions `mark_sibling_refutations()` and `stages/analyze.py` call site | ✅ |
|-------|---------------------|--------------------------------------------------------------------------------------------------------------|------|
| VAL-5 | D2: Inline comment at call site | Debug logging in `stages/analyze.py` explains purpose | ✅ |
| VAL-6 | D3: AGENTS.md | `core/correctness.py` entry added to directory structure table | ✅ |

## Acceptance Criteria Trace

| AC | From Charter | Verified By | Status |
|----|-------------|-------------|--------|
| AC-1 | Unmarked siblings of exactly-1-correct sibling are marked `is_correct=False` | T6: `test_puzzle_14_net_topology` | ✅ |
| AC-2 | Miai guard: skip when ≥2 siblings correct | T7: `test_two_correct_siblings_leaves_unmarked` | ✅ |
| AC-3 | Player-move filter: only mark nodes with `move is not None` | T6: `test_opponent_only_nodes_not_marked` | ✅ |
| AC-4 | Recursive all-depth traversal | T6: `test_recursive_deep_marking` | ✅ |
| AC-5 | Returns count of nodes marked | T6: all tests verify return count | ✅ |
| AC-6 | Metrics improve after marking | T8: `test_refutation_count_increases` | ✅ |
| AC-7 | Frontend detects BM+C[Wrong] correctly | T9: `detects pipeline-marked sibling refutation` | ✅ |
| AC-8 | No regressions in existing tests | T11: 1624 passed; T12: 1352 passed | ✅ |
