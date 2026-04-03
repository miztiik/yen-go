# Plan

## Implementation Steps

1. Add `_scan_lines_with_needle()` private helper to PublishLogReader
2. Rewrite `search_by_run_id()`, `search_by_puzzle_id()`, `search_by_source()` to use pre-filter
3. Add `_index_path()`, `_load_index()` to PublishLogReader
4. Add `rebuild_indexes()` to PublishLogReader
5. Add `find_by_trace_id()` to PublishLogReader
6. Add `_update_indexes()` to PublishLogWriter
7. Update `write()` and `write_batch()` to call `_update_indexes()`
8. Write tests covering all new paths

## Documentation Plan

| files_to_update | files_to_create | why_updated |
|----------------|----------------|-------------|
| — | — | No user-facing doc changes; internal optimization only |
