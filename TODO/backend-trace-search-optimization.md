# Backend Trace Search Optimization

**Created:** 2026-02-24
**Status:** Not Started
**Origin:** Extracted from archived `plan-backend-performance-at-scale.md` Phase 4

---

## Problem

At 300-500k puzzles, trace searches take 8-25 seconds because every JSONL line is deserialized via `json.loads()` even when it doesn't match. No indexing exists.

## Proposed Solution

### Step 1: String pre-filter before JSON deserialization

- **File:** `backend/puzzle_manager/trace_registry.py` (or equivalent publish-log search)
- Construct `needle = f'"puzzle_id":"{puzzle_id}"'`, check `if needle in line:` before `json.loads(line)`
- Same pattern for `trace_id` and `source_file` searches
- Eliminates ~99.99% of JSON parsing

### Step 2: Write-time JSON index for puzzle_id

- Maintain `.index-puzzle-id.json` mapping `{puzzle_id: [run_id1, run_id2, ...]}`
- Called from trace write path
- `search_by_puzzle_id()` reads index first → only scans matched run files

### Step 3: Write-time JSON index for trace_id

- Maintain `.index-trace-id.json` mapping `{trace_id: run_id}`
- Called from trace write path
- `find_by_trace_id()` reads index → O(1) lookup

### Step 4: `rebuild_indexes()` recovery method

- Single-pass over all JSONL files → rebuilds both index files
- Missing index → graceful fallback to full scan

## Target Performance

- Trace search at 200k entries: < 200ms (currently 8-25s)
- No new dependencies (stdlib only)
