# Tasks

| task_id | title | status | parallel | depends_on |
|---------|-------|--------|----------|------------|
| T1 | Add _scan_lines_with_needle() to PublishLogReader | ✅ done | [P] | — |
| T2 | Rewrite search_by_run_id/puzzle_id/source with pre-filter | ✅ done | [P] | T1 |
| T3 | Add index infrastructure (_index_path, _load_index, rebuild_indexes) | ✅ done | [P] | — |
| T4 | Add find_by_trace_id() with index + fallback | ✅ done | — | T3 |
| T5 | Add _update_indexes() to PublishLogWriter | ✅ done | — | T3 |
| T6 | Update write()/write_batch() to maintain indexes | ✅ done | — | T5 |
| T7 | Write TestPublishLogSearchOptimization tests | ✅ done | — | T1-T6 |
| T8 | Run regression tests (1975 backend tests) | ✅ done | — | T7 |
