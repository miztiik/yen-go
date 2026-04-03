# Tasks: Inventory Reset Safety (3-Bug Fix)

**Last Updated**: 2026-03-10

## Task Checklist

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T1 | Fix test isolation leak: mock `_reset_inventory` in `test_inventory_protection.py` | `test_inventory_protection.py` | — | — | ✅ completed |
| T2 | Reorder audit-write before inventory-reset in `cleanup_target()` | `cleanup.py` | — | [P] with T1 | ✅ completed |
| T3 | Make `cleanup_target` default `dry_run=True` for `puzzles-collection` | `cleanup.py` | T2 | — | ✅ completed |
| T4 | Add regression test: audit-failure preserves inventory | `test_cleanup.py` | T2 | [P] with T5 | ✅ completed |
| T5 | Update troubleshoot.md to note the fix | `troubleshoot.md` | T1 | [P] with T4 | ✅ completed |
| T6 | Run existing tests, verify no regressions | — | T1-T5 | — | ✅ completed |

## Task Details

### T1: Fix test isolation leak (ROOT CAUSE)

**File**: `backend/puzzle_manager/tests/integration/test_inventory_protection.py`  
**Location**: `test_cleanup_target_puzzles_collection_preserves_inventory` (~line 170)

**Problem**: Test patches `get_output_dir` but NOT `_reset_inventory`. This causes `_reset_inventory()` to zero the REAL `inventory.json` every time pytest runs.

**Fix**: Mock `_reset_inventory` the same way the other cleanup tests do:
```python
with patch("backend.puzzle_manager.pipeline.cleanup.get_output_dir", ...),\
     patch("backend.puzzle_manager.pipeline.cleanup._reset_inventory"):
    cleanup_target("puzzles-collection")
```

### T2: Reorder audit-write before inventory-reset

**File**: `backend/puzzle_manager/pipeline/cleanup.py`  
**Location**: `cleanup_target()` function, lines ~429-467

Merge the two `if not dry_run:` blocks into one. Move `write_cleanup_audit_entry()` BEFORE `_reset_inventory()`. If audit write raises, inventory is never touched.

### T3: Safe `dry_run` default for `puzzles-collection`

**File**: `backend/puzzle_manager/pipeline/cleanup.py`  
**Location**: `cleanup_target()` function signature or body

Add safety logic: when `target == "puzzles-collection"` and `dry_run` is not explicitly passed as `False`, default to dry-run. This mirrors the CLI behavior at the function level so direct callers (tests, scripts) get the same safety net.

**Note**: The CLI already handles this via `_parse_dry_run_flag`, so CLI behavior is unchanged. This only protects direct callers.

### T4: Add regression test for audit-failure path

**File**: `backend/puzzle_manager/tests/integration/test_cleanup.py`

Add test: `test_inventory_preserved_when_audit_write_fails` — mock audit write to raise, verify `_reset_inventory` was NOT called.

### T5: Update troubleshoot.md

**File**: `docs/how-to/backend/troubleshoot.md`

At the "Inventory Shows Zero But Files Exist" section, note the root cause (test isolation leak) and the fix.

### T6: Regression verification

Run: `pytest -m "not (cli or slow)"` — verify all tests pass.
