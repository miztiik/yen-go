# Tasks — Publish Stage Cleanup (Option A)

> Last Updated: 2026-03-06

## Task Overview

| Task | File(s)                 | Parallel?    | Depends On |
| ---- | ----------------------- | ------------ | ---------- |
| T01  | `models/publish_log.py` | [P]          | —          |
| T02  | `stages/publish.py`     | [P]          | —          |
| T03  | `stages/publish.py`     |              | T02        |
| T04  | `stages/publish.py`     |              | T02        |
| T05  | `stages/publish.py`     |              | T03, T04   |
| T06  | `stages/publish.py`     |              | T05        |
| T07  | `stages/publish.py`     |              | T05        |
| T08  | tests                   |              | T01-T07    |
| T09  | tests                   | [P] with T08 | T01-T07    |

---

## Tasks

### T01: Remove dead fields from PublishLogEntry [P]

**File:** `backend/puzzle_manager/models/publish_log.py`

- [ ] Remove `source_file: str = ""` field from dataclass
- [ ] Remove `original_filename: str = ""` field from dataclass
- [ ] Remove `"source_file"` and `"original_filename"` from `to_jsonl()` dict
- [ ] Remove `.get("source_file", "")` and `.get("original_filename", "")` from `from_jsonl()`
- [ ] Update class docstring to remove references to these fields

### T02: Replace trace registry with YM-based trace_id extraction [P]

**File:** `backend/puzzle_manager/stages/publish.py`

- [ ] Remove imports: `TraceRegistryReader`, `TraceRegistryWriter` from `trace_registry`
- [ ] Remove imports: `TraceEntry`, `TraceStatus` from `models.trace`
- [ ] Add import: `parse_pipeline_meta` from `core.trace_utils`
- [ ] Remove trace registry initialization block (lines ~105-109: `trace_reader`/`trace_writer` setup)
- [ ] Move trace_id extraction inside the try block, after `parse_sgf()`:
  ```python
  trace_id, _, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)
  ```
- [ ] Remove `source_file` variable assignment above try block (move inside if still needed for logging)
- [ ] Remove trace status update for PUBLISHED (inside try, after successful write)
- [ ] Remove trace status update for FAILED (inside except block)
- [ ] Update trace_logger creation to use extracted trace_id (move after extraction)

### T03: Strip `f` field from YM at publish time

**File:** `backend/puzzle_manager/stages/publish.py`

**Depends on:** T02 (trace_id extraction refactored)

- [ ] Add helper function `_strip_ym_filename(game)` to module level:
  - Parse `game.yengo_props.pipeline_meta` as JSON
  - Remove `"f"` key if present
  - Re-serialize with compact separators
  - Set back on `game.yengo_props.pipeline_meta`
  - Defensive: no-op on malformed/missing YM
- [ ] Call `_strip_ym_filename(game)` after `parse_sgf()` and before `SGFBuilder.from_game(game).build()`

### T04: Decouple snapshot from periodic flush

**File:** `backend/puzzle_manager/stages/publish.py`

**Depends on:** T02 (imports cleaned up)

- [ ] Rename `_flush_incremental()` → `_flush_periodic()`
- [ ] Remove snapshot build code from `_flush_periodic()` (the `if new_entries:` block with `SnapshotBuilder` calls)
- [ ] `_flush_periodic()` now only:
  1. Writes pending publish log entries via `log_writer.write_batch()`
  2. Saves batch state via `batch_states["global"].save()`
- [ ] Update both call sites (periodic @100 and "final") to use `_flush_periodic()`
- [ ] Keep the `new_entries` list accumulating — it's consumed at end

### T05: Add `_build_final_snapshot()` method

**File:** `backend/puzzle_manager/stages/publish.py`

**Depends on:** T03, T04

- [ ] Create `_build_final_snapshot()` method that:
  1. Builds snapshot (load existing + merge new_entries + build_snapshot)
  2. Logs summary
- [ ] Call `_build_final_snapshot()` once after the main loop (after the final `_flush_periodic`)
- [ ] Guard with `if new_entries and not context.dry_run`

### T06: Wire audit entry at publish completion

**File:** `backend/puzzle_manager/stages/publish.py`

**Depends on:** T05

- [ ] Add import: `write_audit_entry` from `audit`
- [ ] After `_update_inventory()`, call `write_audit_entry()` with:
  - `audit_file`: `output_root / ".puzzle-inventory-state" / "audit.jsonl"`
  - `operation`: `"publish"`
  - `target`: `"puzzles-collection"`
  - `details`: `{"files_published": processed, "files_failed": failed, "files_skipped": skipped, "source": source_id, "run_id": run_id}`

### T07: Remove dead PublishLogEntry field references from publish stage

**File:** `backend/puzzle_manager/stages/publish.py`

**Depends on:** T01, T05

- [ ] Remove `source_file=""` and `original_filename=""` from `PublishLogEntry()` constructor call (if present)
- [ ] Ensure `trace_id=trace_id or ""` uses the YM-extracted value (from T02)

### T08: Update existing tests

**Files:** `tests/` (multiple)

**Depends on:** T01-T07

- [ ] Update `test_publish_log.py`: Remove assertions for `source_file`/`original_filename` fields
- [ ] Update `test_publish.py` / publish stage tests:
  - Remove trace registry setup/mocking
  - Update flush behavior assertions (no snapshot in periodic flush)
  - Update `PublishLogEntry` construction in test fixtures
- [ ] Update any `PublishLogEntry.from_jsonl()` test data to exclude removed fields
- [ ] Grep for `source_file` and `original_filename` across all test files — update or remove

### T09: Add new test coverage [P with T08]

**Files:** `tests/` (multiple)

**Depends on:** T01-T07

- [ ] Test: `_strip_ym_filename` strips `f` from YM JSON
- [ ] Test: `_strip_ym_filename` is no-op when YM has no `f`
- [ ] Test: `_strip_ym_filename` is no-op for malformed YM
- [ ] Test: trace_id extracted from YM appears in publish log entry
- [ ] Test: periodic flush does NOT call SnapshotBuilder
- [ ] Test: snapshot built once at end with correct entry count
- [ ] Test: audit entry written at end of successful publish
- [ ] Test: PublishLogEntry serialization/deserialization without removed fields
