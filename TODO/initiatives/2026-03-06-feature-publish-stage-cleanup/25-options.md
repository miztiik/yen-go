# Options — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Planning Confidence

- **Score:** 78/100
  - -20: Two viable flush architecture approaches with different tradeoff profiles
  - -2: Minor uncertainty on optimal periodic flush interval for publish log
- **Risk Level:** medium (performance-sensitive change to core publish pipeline)
- **Research invoked:** No (sufficient internal evidence from codebase analysis)

---

## Option A: Snapshot-at-End with Lightweight Periodic Flush

**Approach:** Decouple snapshot build from periodic flush entirely. Periodic flush writes only publish log + batch state (both are append/overwrite operations, O(1) per flush). Snapshot is built once after the main loop completes. All six cleanup items addressed.

### Periodic Flush (every 100 files):

1. Append pending publish log entries to JSONL → `log_writer.write_batch()`
2. Save BatchState to disk → `batch_states["global"].save()`
3. **No snapshot rebuild**

### End-of-Run:

1. Build snapshot once (load existing + merge all new entries)
2. Update inventory
3. Write audit entry

### Benefits

- **Massive speedup**: Eliminates N full snapshot rebuilds (currently one per 100 files). For 2000-file run, goes from ~20 full rebuilds to 1.
- **Simplest code change**: Remove snapshot code from `_flush_incremental`, keep it only after the loop.
- **Crash recovery preserved**: Publish log + batch state flushed periodically. On crash, re-run processes only un-published files (content-hash duplicate detection). Snapshot rebuilt from scratch on re-run.
- **No new abstractions**: Uses existing APIs.

### Drawbacks

- If crash happens at file 1900 of 2000, snapshot doesn't reflect those 1900 files until re-run completes.
- Frontend sees stale snapshot until full run completes. (Acceptable: pipeline is not a live service.)

### Risks

- **Low:** Snapshot staleness during a run is not user-visible (pipeline runs are batch operations).
- **Low:** Re-run after crash re-scans published SGFs for duplicate detection — this is already the pattern.

### Test Impact

- Update flush tests to verify no snapshot build during periodic flush
- Add test: snapshot built once at end with correct entry count

### Architecture Compliance

- ✅ KISS: Simplest possible change.
- ✅ YAGNI: No incremental snapshot machinery.
- ✅ Deterministic: Same input → same output.

---

## Option B: Tiered Flush — Frequent Log Flush, Infrequent Snapshot Rebuild

**Approach:** Two-tier periodic flush strategy. Publish log + batch state flushed every 100 files (lightweight). Snapshot rebuilt every 500–2000 files (configurable, defaults to batch_size). All six cleanup items addressed.

### Tier 1 Flush (every 100 files):

1. Append pending publish log entries to JSONL
2. Save BatchState to disk
3. **No snapshot rebuild**

### Tier 2 Flush (every `batch_size` files, e.g., 500):

1. Full snapshot rebuild (load existing + merge)
2. Log message: `"Snapshot rebuild at %d files"`

### End-of-Run:

1. Final snapshot rebuild (if any entries since last Tier 2 flush)
2. Update inventory
3. Write audit entry

### Benefits

- **Good speedup**: For 2000-file run with batch_size=500, goes from ~20 rebuilds to ~4.
- **More current snapshot**: Frontend (or debugging) can see intermediate state every 500 files.
- **Configurable**: The `batch_size` or `flush_interval` config already exists (unused); could wire it.

### Drawbacks

- **More complex**: Two different flush cadences to reason about and test.
- **Still O(total_corpus) per snapshot rebuild**: Each Tier 2 flush is still a full rebuild.
- **Marginal benefit over Option A**: The snapshot is only useful at run completion for static deployment.

### Risks

- **Medium:** Additional configuration surface (what's the right Tier 2 interval?)
- **Low:** Still deterministic — same config → same output.

### Test Impact

- Tests for both flush tiers
- Configuration validation for flush interval

### Architecture Compliance

- ⚠️ KISS: More complex than necessary for a batch pipeline.
- ⚠️ YAGNI: Intermediate snapshot visibility serves no real use case.
- ✅ Deterministic.

---

## Option C: Incremental Snapshot Append (Shard-Level Delta Updates)

**Approach:** Instead of full snapshot rebuild, maintain in-memory shard state and only write _changed_ shard pages at each flush. Requires tracking which shards are dirty.

### Benefits

- O(delta) per flush instead of O(total_corpus)
- Could flush frequently without performance penalty

### Drawbacks

- **Significant complexity**: ShardWriter is designed for full builds (computes all 1D+2D keys, assigns collection sequence numbers). Making it incremental requires tracking dirty shards, partial page appends, sequence number management.
- **Architectural risk**: Changes core snapshot infrastructure (SnapshotBuilder + ShardWriter) — affects rollback, rebuild, daily challenge generation.
- **Level 4–5 change**: 4+ files, structural redesign of shard system.

### Risks

- **High:** Regression risk in core infrastructure.
- **High:** Complexity for marginal benefit (the static site doesn't need mid-run snapshots).

### Test Impact

- Major: new test infrastructure for incremental shard operations.

### Architecture Compliance

- ❌ KISS: Over-engineered for batch pipeline.
- ❌ YAGNI: No consumer needs mid-run snapshots.
- ✅ Deterministic (but harder to prove).

---

## Comparison Matrix

| Criterion            | Option A (Snapshot-at-End)             | Option B (Tiered Flush)           | Option C (Incremental)    |
| -------------------- | -------------------------------------- | --------------------------------- | ------------------------- |
| **Speedup**          | ~20x (eliminates all mid-run rebuilds) | ~5x (reduces rebuilds)            | ~20x (O(delta) flushes)   |
| **Code complexity**  | Low (remove code)                      | Medium (add tier logic)           | High (redesign shards)    |
| **Crash recovery**   | ✅ Publish log preserved               | ✅ Publish log + partial snapshot | ✅ Full incremental state |
| **Files changed**    | 2-3 + tests                            | 3-4 + tests                       | 5+ + tests                |
| **Correction level** | Level 3                                | Level 3                           | Level 4-5                 |
| **KISS/YAGNI**       | ✅                                     | ⚠️                                | ❌                        |
| **Risk**             | Low                                    | Medium                            | High                      |

## Recommendation

**Option A** is the clear winner. It provides the maximum speedup with the minimum complexity. The snapshot is only consumed by the frontend after deployment — there is zero value in having a current snapshot mid-pipeline. The publish log provides crash recovery. Option B adds complexity for no real benefit. Option C is over-engineering.
