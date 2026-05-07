# Clarifications — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Q1: Backward compatibility?

**Answer:** No backward compatibility required. Old fields and code should be removed entirely.

## Q2: YM `f` field removal at publish?

**Answer:** Confirmed. Strip `f` (original_filename) from the YM JSON before writing the final published SGF. It remains during ingest/analyze for traceability but must not appear in published artifacts.

## Q3: Flush interval / performance approach?

**Answer:** The current every-100-file full-snapshot-rebuild approach is too slow. User is open to different approaches (not locked to "every N files"). The key insight: the snapshot rebuild is O(total_corpus) per flush, not O(delta). Need a fundamentally different flushing strategy.

## Q4: Idempotency?

**Answer:** Not useful in practice. User frequently edits hints, teaching comments, and metadata, which changes content hashes. Re-runs after crashes should work but idempotency guarantees are not a design goal.

## Q5: Trace registry in publish stage?

**Answer:** User asked "do we really need it?" — Assessment: **No.** The trace_id is already embedded in the YM property of every SGF (set at ingest). Publish can extract it directly from `game.yengo_props.pipeline_meta` via `parse_pipeline_meta()`. The trace registry lookup is redundant, the directory is always empty (cleaned), and the PUBLISHED/FAILED status updates add per-file write overhead for no consumer. Remove trace registry dependency from publish.

## Q6: Inventory update timing?

**Derived:** Inventory.json is only written at the very end of publish. A crash or interruption after flushing some puzzles leaves inventory at zero. Should be addressed.

## Q7: Audit entry for publish?

**Derived:** The audit.py module documents that it records "publish" operations, but the publish stage never calls `write_audit_entry()`. Historical entries exist from a now-removed code path. Should be wired up.
