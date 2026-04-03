# Charter — Publish Stage Incremental Flush & Logging

> Last Updated: 2026-03-05

## Summary

The publish stage has five behavioral gaps compared to ingest/analyze stages:

1. Logs every single file at INFO level (floods console)
2. Builds snapshot only once at end of loop (all entries lost on crash)
3. Writes publish log all-at-once at end (all records lost on crash)
4. `flush_interval` config exists but is never wired in publish
5. `BatchState` persisted only at end of loop (stale on crash)

This initiative aligns publish with the dual-level batched logging pattern used by ingest/analyze, and adds incremental snapshot building every 100 files for crash resilience.

## Goals

- **G1**: Align publish stage console logging to `debug` per-file + `info` every 100 files (matching ingest/analyze)
- **G2**: Build snapshots incrementally every 100 published files (not just at end)
- **G3**: Flush publish log entries every 100 files (not all-at-once at end)
- **G4**: Wire `flush_interval` config or use 100-file boundary to save `BatchState` periodically
- **G5**: Remove old all-at-once behavior — no fallback paths

## Non-Goals

- Changing ingest or analyze stage behavior
- Modifying `SnapshotBuilder` internals (it already supports incremental via load + merge)
- Adding new CLI flags or config fields beyond wiring existing ones
- Optimizing `SnapshotBuilder` performance (user accepted the cost)
- Changing snapshot validation logic
- Modifying the `flush_interval` default in `BatchConfig` (keep 500, but the publish loop uses 100 for progress)

## Constraints

- Correction Level: **Level 3** (2-3 files: publish.py + test files)
- No backward compatibility required
- Remove old behavior, not deprecate
- Must pass existing tests (with updates) and add new coverage
- Must follow dual-level logging pattern exactly as ingest/analyze
- Must use existing `SnapshotBuilder.build_snapshot()` flow (load existing → merge → build)

## Acceptance Criteria

- [ ] `trace_logger.info("Published puzzle", ...)` replaced with `logger.debug(...)` per-file
- [ ] `logger.info("[publish] %d/%d — ...")` emitted every 100 files
- [ ] Snapshot rebuilt every 100 successfully published files
- [ ] Publish log entries flushed to disk every 100 files
- [ ] `BatchState.save()` called every 100 files (not just at loop end)
- [ ] Existing robustness tests updated to match new behavior
- [ ] New test: crash at file 150 preserves snapshot for first 100 files
- [ ] No `trace_logger.info("Published puzzle")` at INFO level in production path
- [ ] `flush_interval` config respected or documented as superseded
