# Clarifications — Publish Incremental Flush

> Last Updated: 2026-03-05

## Questions & Answers

### Q1: Is backward compatibility required, and should old code be removed?

**Answer**: No backward compatibility required. Old code and old behavior should be removed.
**Impact**: We can directly replace the current publish loop behavior. No need for feature flags, fallback paths, or gradual migration.

### Q2: What flush/progress interval should the publish stage use?

**Answer**: Every 100 files — matching ingest and analyze stages.
**Impact**: All three stages will use the same `% 100 == 0` console progress pattern. The existing `flush_interval` config (default 500) will be replaced by a hardcoded 100-file progress cadence for logging, but periodic flush of batch state, publish log entries, and incremental snapshot building will all happen at the same 100-file boundary.

### Q3: Should all five identified problems be addressed?

**Answer**: Yes, all five:

1. Per-file INFO logging → batched every 100 files
2. Snapshot all-or-nothing → incremental every 100 files
3. Publish log all-at-once → flush every 100 files
4. `flush_interval` not wired → wire it (or use 100 directly)
5. `BatchState` saved only at end → save every 100 files

### Q4: Should incremental snapshot building be used even if slower?

**Answer**: Yes. User explicitly wants incremental snapshot building "to build that muscle." Performance trade-off is accepted.
**Impact**: `SnapshotBuilder` will be invoked every 100 files during the publish loop, not just at the end. Each invocation loads existing entries, merges new entries, and writes a fresh snapshot — the full `build_snapshot()` flow including validation and activation.

### Q5: Scope confirmation — any additional constraints?

**Answer**: Address exactly the five problems identified. Changes are scoped to the publish stage and its tests.

## Resolved Ambiguities

| Topic                   | Resolution                                       |
| ----------------------- | ------------------------------------------------ |
| Backward compat         | Not required                                     |
| Old code removal        | Yes, remove old behavior                         |
| Progress interval       | Every 100 files                                  |
| Snapshot strategy       | Incremental every 100 files                      |
| Scope                   | All 5 problems                                   |
| `flush_interval` config | Wire it or align to 100 — implementation decides |
