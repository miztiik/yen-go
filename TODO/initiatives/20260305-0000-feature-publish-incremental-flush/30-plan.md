# Plan — Publish Stage Incremental Flush & Logging

> Last Updated: 2026-03-05  
> Selected Option: **A — Inline Periodic Flush in Publish Loop**

## Architecture

### Design Decision

The publish stage's `for sgf_path in sgf_files` loop will gain a periodic flush block at every 100th total processed file (processed + failed + skipped). This exactly mirrors the dual-level logging pattern proven in ingest.py (L158-176) and analyze.py (L151-171).

### Conceptual Diff: publish.py

The publish loop currently has this structure:

```
for sgf_path in sgf_files:
    try:
        ... per-file processing ...
        trace_logger.info("Published puzzle", ...)       # ← PROBLEM 1: INFO per file
        publish_log_entries.append(log_entry)              # ← PROBLEM 3: in-memory only
        new_entries.append(entry)                          # ← PROBLEM 2: in-memory only
    except:
        ... error handling ...

# All after loop:
batch_states["global"].save(sgf_root)                     # ← PROBLEM 5: once at end
builder.build_snapshot(merged_entries)                      # ← PROBLEM 2: once at end
log_writer.write_batch(publish_log_entries)                 # ← PROBLEM 3: once at end
```

After this change:

```
for sgf_path in sgf_files:
    try:
        ... per-file processing ...
        logger.log(DETAIL, "Published puzzle", ...)        # FIX 1: DETAIL per file
        pending_log_entries.append(log_entry)               # accumulate
        pending_entries.append(entry)                       # accumulate
    except:
        ... error handling ...

    # Streaming progress (matches ingest/analyze)
    total = processed + failed + skipped
    logger.debug("Progress: %d processed, %d failed, %d skipped (%d/%d)", ...)
    if total % 100 == 0:                                   # FIX 1: console every 100
        logger.info("[publish] %d/%d — %d ok, %d failed, %d skipped", ...)

        # FIX 2+3+4+5: Periodic flush
        if not context.dry_run and pending_entries:
            _flush_pending(...)                             # snapshot + log + state

# After loop: flush remaining
if not context.dry_run and pending_entries:
    _flush_pending(...)                                    # final flush for remainder
```

### Data Model Impact

None. No schema changes, no config changes, no new data structures.

### Contracts/Interfaces

**Modified**: `PublishStage.run()` internal behavior only. Public interface (`StageResult`) unchanged.

**New internal helper** (private method or local function):

```python
def _flush_pending(
    pending_entries, pending_log_entries, new_entries,
    builder, id_maps, output_root, sgf_root, batch_states,
    log_writer, processed, context
):
    # 1. Merge pending_entries into existing snapshot
    # 2. Write publish log entries
    # 3. Save batch state
    # 4. Clear pending buffers
```

This avoids duplication between the 100-file boundary flush and the end-of-loop flush.

### `flush_interval` Config Resolution

The existing `BatchConfig.flush_interval` (default 500) was designed for batch state flushing but was never wired. Since we're now using a fixed 100-file cadence for all periodic operations (matching ingest/analyze), the `flush_interval` config becomes the batch-state flush interval, distinct from the 100-file console progress/snapshot cadence.

**Decision**: Wire `flush_interval` for BatchState saves, but use hardcoded 100 for console progress and snapshot rebuilds. This means:

- Console progress: every 100 (hardcoded, matching siblings)
- Snapshot rebuild: every 100 (hardcoded, user requirement)
- Publish log flush: every 100 (hardcoded, for crash resilience)
- BatchState save: every 100 (at the same boundary, simplest approach)

Since all four operations happen at the same 100-file boundary, we don't need `flush_interval` separately. We'll document it as superseded by the 100-file cadence in the code comments.

### Duplicate Skip Logging

Current: `logger.info(f"Skipping already-published SGF {content_hash} ...")` at L214.
Change to: `logger.log(DETAIL, f"Skipping duplicate ...")` — matching test expectation in `test_duplicate_skip_is_detail_level`.

## Risks & Mitigations

| Risk                                                     | Probability | Impact                  | Mitigation                                                                                                                 |
| -------------------------------------------------------- | ----------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Performance: 20× snapshot builds per 2000-file run       | Certain     | Medium (slower publish) | User accepted. Each build is O(total_entries).                                                                             |
| Partial snapshot gap: files between last flush and crash | Low         | Low                     | Content-hash dedup on re-run picks them up. Next 100-boundary rebuilds snapshot.                                           |
| Test flakiness from snapshot timing                      | Low         | Low                     | Tests use small file counts (3-5), so flush boundary is predictable.                                                       |
| Existing tests fail due to logging level change          | Certain     | Low                     | Tests already expect DETAIL — they just currently fail against the code. We're fixing the code to match test expectations. |

## Rollout / Rollback

- **Rollout**: Single commit. No feature flags, no gradual rollout.
- **Rollback**: Revert single commit. No schema migration needed.
- **Validation**: `pytest -m "not (cli or slow)"` must pass.

## Files Changed

| File                                                                  | Change Type | Description                                   |
| --------------------------------------------------------------------- | ----------- | --------------------------------------------- |
| `backend/puzzle_manager/stages/publish.py`                            | Modify      | Add periodic flush block + fix logging levels |
| `backend/puzzle_manager/tests/integration/test_publish_robustness.py` | Modify      | Update existing tests + add new tests         |

## Constraints

- Must match ingest/analyze dual-level pattern exactly
- `DETAIL` (15) for per-file messages, `DEBUG` (10) for streaming counter
- `INFO` (20) for 100-file console summary
- No new files, no new classes, no new abstractions
- Remove old all-at-once behavior
