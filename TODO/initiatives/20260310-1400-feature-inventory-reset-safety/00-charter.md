# Charter: Inventory Reset Safety (3-Bug Fix)

**Initiative ID**: 20260310-1400-feature-inventory-reset-safety  
**Last Updated**: 2026-03-10

## Problem Statement

On 2026-03-09, `inventory.json` was found zeroed (`clean-20260309215708`, all counts 0), no audit entry for that date, yet 2000+ SGF files remain on disk. Investigation revealed **three independent bugs**, one of which is the direct root cause and two are defense-in-depth gaps.

## Bug #1: Test Isolation Leak (ROOT CAUSE)

`test_cleanup_target_puzzles_collection_preserves_inventory` in `test_inventory_protection.py` (line 170) calls `cleanup_target("puzzles-collection")` with:
- `get_output_dir` patched to `tmp_path` (file deletion goes to temp folder — safe)
- `_reset_inventory()` **NOT patched** — it creates `InventoryManager()` with no args, which resolves to the **REAL** `yengo-puzzle-collections/.puzzle-inventory-state/inventory.json`

Result: **Every time `pytest` runs, real inventory.json gets zeroed.** The test SGFs are deleted from tmp, `remaining == 0`, so `_reset_inventory()` fires against the real path. Audit entry also writes to tmp (gone after test).

## Bug #2: Audit-Before-Reset Ordering

In `cleanup.py` `cleanup_target()` for `puzzles-collection`:
1. `_reset_inventory()` is called at line 433 (inventory zeroed)
2. `write_cleanup_audit_entry()` is called later at line 459

If audit write fails, inventory is already zeroed — no audit trail. The operations should be reordered: audit first, then reset.

## Bug #3: Unsafe `dry_run` Default

`cleanup_target()` function signature: `dry_run: bool = False`. The CLI layer adds a safety default via `_parse_dry_run_flag` (defaults to `True` for `puzzles-collection`), but any direct caller of the function (including tests) gets the **unsafe** `dry_run=False` default. This is why the test at Bug #1 actually performs real deletions instead of being a no-op.

## Goals

1. Fix test isolation: `_reset_inventory()` must be mocked in any test that calls `cleanup_target("puzzles-collection")` without full path isolation
2. Reorder audit-before-reset: journal before destructive mutation  
3. Make `cleanup_target` safe by default for `puzzles-collection`: default `dry_run=True` when target is `puzzles-collection`

## Non-Goals

- Adding a new CLI confirmation flag — existing `--dry-run false` sufficient
- Provenance metadata — separate initiative
- Auto-heal on startup — separate initiative

## Constraints

- Level 2 change: 3 files (cleanup.py, test_inventory_protection.py, troubleshoot.md), ~50 lines
- Must not change the CLI interface behavior (CLI already defaults to dry-run for puzzles-collection)
- Must not change the inventory schema
- Must preserve and improve test coverage

## Acceptance Criteria

1. Test `test_cleanup_target_puzzles_collection_preserves_inventory` mocks `_reset_inventory` (no real inventory mutation)
2. `_reset_inventory()` is only called after audit entry is successfully written
3. `cleanup_target("puzzles-collection")` without explicit `dry_run=False` does NOT delete files (safe default)
4. All existing tests continue to pass
5. New regression test covers audit-failure → inventory-preserved scenario

> **See also**:
> - [Troubleshoot guide](../../../docs/how-to/backend/troubleshoot.md) — Documents this known issue
> - [cleanup.py](../../../backend/puzzle_manager/pipeline/cleanup.py) — Target file
> - [test_inventory_protection.py](../../../backend/puzzle_manager/tests/integration/test_inventory_protection.py) — Leaking test
