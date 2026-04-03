# Charter — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Summary

The publish stage has accumulated several behavioral gaps and performance problems since the incremental-flush initiative (2026-03-05). This initiative addresses six issues:

1. **Dead fields in publish log**: `source_file` and `original_filename` are declared but never populated (always `""`)
2. **YM `f` field leaks to published SGFs**: Original source filenames remain in published artifacts
3. **Snapshot flush is O(total_corpus) per flush**: Every 100-file flush rebuilds the ENTIRE snapshot, making batch publishes extremely slow at scale
4. **Trace registry dependency is redundant**: Publish looks up trace_id from an always-empty trace registry instead of reading it from the already-parsed YM property
5. **Inventory only updated at end**: A crash mid-run leaves inventory.json at zero
6. **Audit entry never written by publish**: The audit module promises publish records but the stage never calls it

## Goals

- **G1**: Remove `source_file` and `original_filename` from `PublishLogEntry` model and serialization
- **G2**: Strip `f` field from YM property before writing published SGFs
- **G3**: Decouple snapshot build from periodic flush — build snapshot only at end, flush lightweight data (publish log + batch state) periodically
- **G4**: Extract trace_id from parsed YM property instead of trace registry; remove trace registry reader/writer from publish
- **G5**: Write inventory incrementally during periodic flushes (or at snapshot build time)
- **G6**: Write audit entry at publish completion

## Non-Goals

- Changing SnapshotBuilder internals (load_existing_entries, build_snapshot)
- Making snapshot builds incremental/append-only (that's a separate architectural change)
- Modifying ingest or analyze stages
- Changing the trace registry for other stages (ingest still uses it)
- Adding new CLI flags or config fields

## Constraints

- Correction Level: **Level 3** (2-3 core files + test files)
- No backward compatibility required — remove dead code, don't deprecate
- Must pass existing tests (with updates) and add new coverage
- Published SGFs must not contain `f` in YM

## Acceptance Criteria

- [ ] `PublishLogEntry` has no `source_file` or `original_filename` fields
- [ ] Published SGFs have YM without `f` key (only `t`, `i`, and any other active fields)
- [ ] Periodic flush (every N files) only writes publish log + batch state (lightweight)
- [ ] Snapshot built once at end of run, not per-flush
- [ ] trace_id populated in publish log from YM property (not trace registry)
- [ ] No trace registry imports in publish.py
- [ ] Inventory updated at end of run after snapshot build
- [ ] Audit entry written at end of successful publish run
- [ ] All existing tests updated; new tests for YM stripping and trace_id extraction
