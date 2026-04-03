# Validation Report: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Last Updated**: 2026-03-05

## Test Results

### Sanderland Adapter Tests (42 tests)

- **Command**: `pytest backend/puzzle_manager/tests/adapters/test_sanderland.py -v --tb=short`
- **Exit code**: 0
- **Result**: 42 passed in 2.33s
- **New tests**: 9 (all in `TestPassMoveHandling`)
- **Existing tests**: 33 (all still passing)

### Broader Backend Tests (2039 collected)

- **Command**: `pytest backend/puzzle_manager/tests/ -m "not (cli or slow)" -q`
- **Exit code**: 1 (pre-existing failures)
- **Result**: 2026 passed, 13 failed, 44 deselected
- **New failures introduced**: 0
- **Pre-existing failures** (all unrelated):
  - `test_inventory_publish` (1 failure)
  - `test_publish_log_integration` (4 failures)
  - `test_publish_robustness` (5 failures)
  - `test_publish_snapshot_wiring` (1 failure)
  - `test_adapter_registry` (2 failures — discovery logging)
  - `test_tag_taxonomy` (1 failure — version check)

## Acceptance Criteria Verification

| #   | Criterion                                                             | Status | Evidence                             |
| --- | --------------------------------------------------------------------- | ------ | ------------------------------------ |
| 1   | `_build_solution_tree([["W", "zz", "", ""]])` → `;W[]C[White passes]` | PASS   | `test_single_white_pass`             |
| 2   | `_build_solution_tree([["B", "zz", "", ""]])` → `;B[]C[Black passes]` | PASS   | `test_single_black_pass`             |
| 3   | Multi-move with embedded pass preserves full sequence                 | PASS   | `test_multi_move_with_embedded_pass` |
| 4   | Comment append with em-dash for non-empty existing comments           | PASS   | `test_pass_with_existing_comment`    |
| 5   | Existing tests still pass                                             | PASS   | 33 pre-existing tests unchanged      |
| 6   | New unit tests cover sequential and miai paths                        | PASS   | 9 tests in `TestPassMoveHandling`    |
| 7   | Normal moves unaffected                                               | PASS   | `test_normal_moves_unchanged`        |

## Files Changed

| File                                                       | Type | Lines Changed                       |
| ---------------------------------------------------------- | ---- | ----------------------------------- |
| `backend/puzzle_manager/adapters/sanderland/adapter.py`    | Code | +23 lines (helper + two path fixes) |
| `backend/puzzle_manager/tests/adapters/test_sanderland.py` | Test | +60 lines (9 new tests)             |
