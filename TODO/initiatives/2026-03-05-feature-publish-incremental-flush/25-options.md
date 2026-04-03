# Options — Publish Stage Incremental Flush & Logging

> Last Updated: 2026-03-05

## Option A: Inline Periodic Flush in Publish Loop

**Approach**: Add a `% 100 == 0` check inside the existing publish loop. At every 100th file: flush publish log entries, save batch state, build incremental snapshot, and emit console progress.

### Architecture

- Single code path: the existing `for sgf_path in sgf_files` loop gains a periodic flush block
- No new classes or abstractions
- Reuses `SnapshotBuilder` as-is (load_existing → merge → build_snapshot)
- Publish log entries written in chunks: accumulate 100, flush, clear accumulator
- `trace_logger.info(...)` per-file → `logger.debug(...)` per-file

### Benefits

- **Minimal structural change** — all 5 fixes live in one code block added to the loop
- **Easy to read** — matches ingest/analyze pattern almost line-for-line
- **No new abstractions** — follows KISS/YAGNI
- **Flush boundary is explicit** — `if (processed + skipped + failed) % 100 == 0`

### Drawbacks

- Snapshot built multiple times per run (user accepted this cost)
- Each snapshot build loads existing entries from disk (O(total_entries) per rebuild)
- The publish loop becomes longer (but only ~15 lines added for the flush block)

### Risks

- **Performance**: For 2000-file batch, ~20 snapshot builds per run. Each loads existing entries + merges + writes all shards. Acceptable per user directive.
- **Partial snapshot on crash**: If crash at file 250, snapshot reflects first 200. Files 201-250 are on disk but not in snapshot. Re-run deduplicates via content hash, and next 100-boundary rebuilds snapshot.

### Complexity

Low. ~50 lines changed in publish.py, ~80 lines in test updates.

### Test Impact

- `test_per_file_log_is_detail_level` → update to check `logger.debug` (or DETAIL level)
- `test_batch_state_flushed_at_interval` → update expectations (flush at 100 boundaries)
- New test: `test_incremental_snapshot_every_100_files`
- New test: `test_publish_log_flushed_every_100_files`

### Rollback

Revert single commit. No schema changes, no config migration.

### Architecture Compliance

- ✅ No new files
- ✅ No new dependencies
- ✅ Matches existing ingest/analyze patterns
- ✅ KISS compliant

---

## Option B: Extract Flush Logic into FlushManager Helper

**Approach**: Create a `PublishFlushManager` class that encapsulates the periodic flush logic (snapshot build, log flush, state save, progress logging). The publish loop calls `flush_manager.on_file_processed()` after each file, and the manager handles the interval check internally.

### Architecture

- New class: `PublishFlushManager` in `stages/publish.py` (or `stages/publish_flush.py`)
- Encapsulates: snapshot builder reference, publish log writer, batch state, interval config
- `on_file_processed(entry, processed, failed, skipped)` → checks interval, triggers flush
- `finalize()` → flushes remaining entries at loop end

### Benefits

- **Separation of concerns** — flush logic separate from publish loop
- **Testable in isolation** — unit test the flush manager without running full publish
- **Reusable** — if other stages ever need periodic flush, pattern exists

### Drawbacks

- **New abstraction for single use** — YAGNI concern
- More files or classes to maintain
- Slightly more complex to understand the publish flow (indirection)
- Manager holds mutable state (entries buffer) — harder to reason about

### Risks

- **Over-engineering** — adds abstraction layer for something that's ~15 lines inline
- **Testing duplication** — need both unit tests for manager AND integration tests for publish

### Complexity

Medium. New class (~60 lines), publish.py changes (~30 lines), new test file (~100 lines).

### Test Impact

- New unit tests for `PublishFlushManager`
- Integration tests still needed for full publish flow
- Existing tests need updates

### Rollback

Revert commit + delete new file/class.

### Architecture Compliance

- ⚠️ New class/abstraction for single use (YAGNI tension)
- ✅ No new dependencies
- ⚠️ Creates indirection that doesn't exist in ingest/analyze

---

## Option C: Event-Driven Flush via Callback

**Approach**: Define a `on_progress` callback signature. The publish loop calls the callback after every file. The callback implementation checks the interval and triggers flushes. Default callback does the inline flush; tests can inject a mock callback.

### Architecture

- Callback type: `Callable[[int, int, int], None]` (processed, failed, skipped)
- Default implementation wired in `PublishStage.run()` as a closure
- No new files — callback defined as inner function

### Benefits

- **Testable** — inject mock callback to verify call frequency
- **Flexible** — different callbacks for different scenarios

### Drawbacks

- **Closure complexity** — callback captures snapshot builder, log writer, batch state
- **Unusual pattern** — ingest/analyze don't use callbacks for this
- **Harder to debug** — stack traces through closures are less readable

### Risks

- Pattern inconsistency across stages (ingest/analyze are inline)
- Over-engineering for the problem at hand

### Complexity

Medium. ~40 lines for callback + wiring, ~40 lines test updates.

### Test Impact

Similar to Option A but with callback injection in tests.

### Rollback

Revert single commit.

### Architecture Compliance

- ⚠️ Introduces pattern not used by sibling stages
- ✅ No new files or dependencies

---

## Comparison Matrix

| Criterion                       |   Option A (Inline)   |      Option B (FlushManager)       |   Option C (Callback)   |
| ------------------------------- | :-------------------: | :--------------------------------: | :---------------------: |
| Structural simplicity           |        ✅ Best        |            ⚠️ New class            |  ⚠️ Closure complexity  |
| Consistency with ingest/analyze |    ✅ Exact match     |        ❌ Different pattern        |  ❌ Different pattern   |
| KISS/YAGNI compliance           |      ✅ Minimal       |      ❌ Premature abstraction      |      ⚠️ Borderline      |
| Testability                     | ✅ Good (integration) |     ✅ Best (unit+integration)     | ✅ Good (mock callback) |
| Lines changed                   |      ~130 total       |             ~190 total             |       ~150 total        |
| Files changed                   | 2 (publish.py + test) | 2-3 (publish.py + manager + tests) |  2 (publish.py + test)  |
| Rollback complexity             |          Low          |                Low                 |           Low           |
| Risk                            |          Low          |                Low                 |           Low           |

## Recommendation

**Option A (Inline Periodic Flush)** — It directly mirrors the ingest/analyze pattern, adds no abstractions, and satisfies all 5 requirements with minimal code. KISS and YAGNI compliant.
