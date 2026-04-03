# Plan — Publish Stage Cleanup (Option A)

> Last Updated: 2026-03-06

## Architecture Design

### Core Change: Decouple Snapshot from Periodic Flush

**Current flow:**

```
Every 100 files → _flush_incremental():
  1. Load ALL existing entries from snapshot    ← O(total_corpus)
  2. Merge with new entries                     ← O(total_corpus)
  3. Build entire snapshot from scratch          ← O(total_corpus)
  4. Write publish log batch                     ← O(batch)
  5. Save batch state                            ← O(1)
```

**New flow:**

```
Every 100 files → _flush_periodic():
  1. Write publish log batch                     ← O(batch)
  2. Save batch state                            ← O(1)

After loop → _build_final_snapshot():
  1. Load ALL existing entries from snapshot      ← O(total_corpus)  ×1
  2. Merge with all new entries                   ← O(total_corpus)  ×1
  3. Build entire snapshot from scratch            ← O(total_corpus)  ×1
  4. Update inventory
  5. Write audit entry
```

**Performance impact:** For a 2000-puzzle run with 5000 existing entries, eliminates ~19 full snapshot rebuilds. Only 1 rebuild remains.

### Component Changes

#### 1. `stages/publish.py` — Primary changes

**Import changes:**

- REMOVE: `TraceRegistryReader`, `TraceRegistryWriter`, `TraceEntry`, `TraceStatus`
- ADD: `parse_pipeline_meta` from `core.trace_utils`
- ADD: `write_audit_entry` from `audit`

**trace_id extraction (replace trace registry):**

```python
# BEFORE: trace registry lookup (lines ~155-165)
if trace_reader:
    trace_entry = trace_reader.find_by_source_file(source_file, context.run_id)
    if trace_entry:
        trace_id = trace_entry.trace_id

# AFTER: extract from parsed YM
trace_id, _, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)
```

**YM `f` stripping (before re-serialization):**

```python
# After parse_sgf(), before SGFBuilder.from_game():
if game.yengo_props.pipeline_meta:
    _strip_ym_filename(game)  # Remove `f` key from YM JSON
```

Helper function in publish.py:

```python
def _strip_ym_filename(game: SGFGame) -> None:
    """Strip the `f` (original_filename) field from YM pipeline metadata."""
    import json
    try:
        meta = json.loads(game.yengo_props.pipeline_meta)
        if isinstance(meta, dict) and "f" in meta:
            del meta["f"]
            game.yengo_props.pipeline_meta = json.dumps(meta, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        pass  # Defensive: leave YM unchanged if malformed
```

**PublishLogEntry construction (remove dead fields):**

- Remove `source_file=...` and `original_filename=...` from constructor call
- trace_id now comes from YM, not trace registry

**Flush restructure:**

- Rename `_flush_incremental` → `_flush_periodic`
- Remove snapshot build code from periodic flush
- Add `_build_final_snapshot()` method called once after loop
- Move inventory update and audit write into `_build_final_snapshot()`

**Remove trace registry initialization/usage:**

- Delete `trace_reader`/`trace_writer` initialization block
- Delete PUBLISHED/FAILED trace status update calls
- Remove `context.trace_registry_dir` checks

#### 2. `models/publish_log.py` — Field removal

- Remove `source_file: str = ""` field from `PublishLogEntry`
- Remove `original_filename: str = ""` field from `PublishLogEntry`
- Remove from `to_jsonl()` serialization
- Remove from `from_jsonl()` deserialization
- Update docstring

#### 3. `audit.py` — No changes (existing `write_audit_entry` is sufficient)

#### 4. Test files — Update and add coverage

---

## Data Model Impact

### PublishLogEntry (BREAKING — no backward compat needed)

| Field               | Before                 | After                     |
| ------------------- | ---------------------- | ------------------------- |
| `source_file`       | `str = ""` (never set) | REMOVED                   |
| `original_filename` | `str = ""` (never set) | REMOVED                   |
| `trace_id`          | `str` (always `""`)    | `str` (populated from YM) |

### Published SGF YM property

| Before                                           | After                       |
| ------------------------------------------------ | --------------------------- |
| `YM[{"t":"abc...","f":"Problem 1.json","ct":3}]` | `YM[{"t":"abc...","ct":3}]` |

### Publish log JSONL

| Before                                                                | After                                      |
| --------------------------------------------------------------------- | ------------------------------------------ |
| `{..., "source_file":"", "original_filename":"", "trace_id":"", ...}` | `{..., "trace_id":"abc123def456...", ...}` |

---

## Risks and Mitigations

| Risk                                               | Severity | Mitigation                                                                          |
| -------------------------------------------------- | -------- | ----------------------------------------------------------------------------------- |
| Crash mid-run: snapshot stale                      | Low      | Publish log + batch state flushed periodically. Re-run rebuilds snapshot.           |
| `parse_pipeline_meta` returns empty trace_id       | Low      | Defensive parsing — empty string is acceptable (same as current behavior).          |
| YM `f` stripping changes content hash              | Medium   | This is intentional. New hash = new puzzle_id. Existing published files unaffected. |
| Test breakage from field removal                   | Low      | Update tests to remove dead field assertions.                                       |
| Rollback code reads `source_file` from publish log | None     | Grep confirmed: zero read-site consumers.                                           |

---

## Rollback Plan

If issues discovered after merge:

1. Revert the commit (single feature branch)
2. No data migration needed — publish log format change is forward-only
3. Existing published SGFs with `f` in YM remain valid (just have extra field)
