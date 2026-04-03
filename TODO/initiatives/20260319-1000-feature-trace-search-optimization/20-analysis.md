# Analysis

## Bottleneck

`PublishLogReader.search_by_run_id()`, `search_by_puzzle_id()`, `search_by_source()` all call `read_all()` which deserializes every JSONL line. At 500k entries, this means 500k `json.loads()` calls per search.

## Approach

- **String pre-filter**: O(1) substring check per line eliminates 99%+ of `json.loads()` calls
- **Write-time indexes**: JSON files mapping `puzzle_id`/`trace_id` → date, enabling O(1) date-targeted reads
- **Graceful fallback**: Missing/corrupt indexes trigger full pre-filtered scan (never raise)

## Risk

- **Low**: Changes are additive; existing API signatures preserved
- **Index staleness**: Writer updates indexes atomically; `rebuild_indexes()` available for recovery
- **Format agnostic**: Pre-filter uses value-only needles, works with both compact and pretty-printed JSON
