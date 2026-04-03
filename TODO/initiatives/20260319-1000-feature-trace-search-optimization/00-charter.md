# Charter: Backend Trace Search Optimization

**Initiative ID**: 20260319-1000-feature-trace-search-optimization
**Type**: Feature (Performance)
**Source**: `TODO/backend-trace-search-optimization.md`

## Problem

At 300-500k puzzles, publish log trace searches take 8-25 seconds because every JSONL line is deserialized via `json.loads()` even when it doesn't match the search target. Target: <200ms for single-ID lookups.

## Solution

4-step optimization of `PublishLogReader` search methods:

1. **String pre-filter**: Check `needle in raw_line` before `json.loads()` to skip ~99% of deserialization
2. **puzzle_id write-time index**: JSON index maintained by writer for O(1) puzzle lookups
3. **trace_id write-time index**: Same pattern for trace_id lookups, plus new `find_by_trace_id()` method
4. **rebuild_indexes()**: Recovery method to rebuild indexes from JSONL files

## Scope

- `backend/puzzle_manager/publish_log.py` — Reader and Writer classes
- `backend/puzzle_manager/tests/unit/test_publish_log.py` — New test class

## Exclusions

- CLI wiring for `find_by_trace_id` (separate task)
- Migration of existing deployments (indexes are optional accelerators)
