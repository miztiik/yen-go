# Plan: Inventory Reset Safety (3-Bug Fix)

**Last Updated**: 2026-03-10  
**Selected Option**: OPT-A expanded — Fix test leak + audit-before-reset + safe default

## Three Bugs, One Initiative

### Bug #1: Test Isolation Leak (ROOT CAUSE of 2026-03-09 incident)

`test_inventory_protection.py` line 170 patches `get_output_dir` but not `_reset_inventory`. Every pytest run zeros real inventory.

**Fix**: Add `patch("backend.puzzle_manager.pipeline.cleanup._reset_inventory")` to the test.

### Bug #2: Audit-Before-Reset Ordering (defense-in-depth)

`_reset_inventory()` is called before `write_cleanup_audit_entry()`. Reorder so journal is written before destructive mutation.

**Fix**: Merge two `if not dry_run:` blocks, put audit write first.

### Bug #3: Unsafe `dry_run` Default (defense-in-depth)

`cleanup_target(target, dry_run=False)` means any direct caller (tests, scripts) bypasses the CLI's dry-run safety. The CLI adds its own safety layer, but the function itself is unsafe.

**Fix**: Add defensive logic inside `cleanup_target()` so that `puzzles-collection` target defaults to `dry_run=True` at the function level, unless explicitly overridden. CLI callers already pass explicit `dry_run=False` via `_parse_dry_run_flag`, so their behavior is unchanged.

## File Impact

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `backend/puzzle_manager/tests/integration/test_inventory_protection.py` | Test fix | ~5 lines |
| `backend/puzzle_manager/pipeline/cleanup.py` | Logic reorder + safe default | ~30 lines |
| `backend/puzzle_manager/tests/integration/test_cleanup.py` | New regression test | ~30 lines |
| `docs/how-to/backend/troubleshoot.md` | Doc update | ~5 lines |

## Risks and Mitigations

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Changing `dry_run` default breaks callers that expect deletion | Low | Only affects `puzzles-collection` target; all existing callers pass explicit `dry_run=False` |
| Reorder introduces subtle behavior change | None | Both operations already exist; only order changes |
| Test fix masks a real bug | None | Test was already asserting correct behavior — it just wasn't isolated |

## Documentation Plan

| Action | File | Why |
|--------|------|-----|
| files_to_update | `docs/how-to/backend/troubleshoot.md` | Update "Inventory Shows Zero" known issue with root cause and fix |

> **See also**:
> - [Charter](./00-charter.md) — Problem statement and 3 bugs
> - [Analysis](./20-analysis.md) — Impact and ripple analysis
> - [Governance](./70-governance-decisions.md) — Panel approval
