# Tasks — Externalize TECHNIQUE_REGISTRY (OPT-1)

Last Updated: 2026-03-22

## Task List

### Phase 1: Data Export (T1–T2)

| task_id | task | file(s) | depends_on | parallel | definition_of_done |
|---------|------|---------|------------|----------|--------------------|
| T1 | Create JSON data file with metadata header and 25 technique entries | `tests/fixtures/technique-benchmark-reference.json` | — | — | JSON file exists, is valid JSON, has `version`, `last_updated`, `description`, and `techniques` object with 25 keys matching current TECHNIQUE_REGISTRY slug keys |
| T2 | Verify JSON content matches current hardcoded dict exactly | `tests/fixtures/technique-benchmark-reference.json` | T1 | — | Every field in every entry is identical to the current `TECHNIQUE_REGISTRY` values. Verify by running: `python -c "import json; ..."` comparison script or manual diff |

### Phase 2: Test File Refactor (T3–T5)

| task_id | task | file(s) | depends_on | parallel | definition_of_done |
|---------|------|---------|------------|----------|--------------------|
| T3 | Add `_load_registry()` function to test file | `tests/test_technique_calibration.py` | T1 | — | Function reads JSON, constructs `TechniqueSpec(**entry)` per technique, returns `dict[str, TechniqueSpec]`. Includes error handling for FileNotFoundError and JSON decode errors. |
| T4 | Replace hardcoded `TECHNIQUE_REGISTRY` with loader call | `tests/test_technique_calibration.py` | T3 | — | Delete ~250 lines of dict literal. Replace with `TECHNIQUE_REGISTRY = _load_registry()`. Module-level assignment. |
| T5 | Run all 8 tests and verify pass | `tests/test_technique_calibration.py` | T4 | — | 3 unit tests pass: `test_all_tags_have_registry_entry`, `test_registry_entries_reference_existing_fixtures`, `test_no_excluded_tags_in_registry`. 5 parametrized tests (×25 each) still discoverable (integration tests may skip if no KataGo). |

### Phase 3: Regeneration Script (T6–T8)

| task_id | task | file(s) | depends_on | parallel | definition_of_done |
|---------|------|---------|------------|----------|--------------------|
| T6 | Create `scripts/regenerate_benchmark_reference.py` | `scripts/regenerate_benchmark_reference.py` | T1 | [P] with T3 | Script exists, has `--dry-run` flag, reads current JSON for fixture→slug mapping, runs `enrich_single_puzzle()` per fixture, extracts 5 calibration dimensions |
| T7 | Add `--dry-run` diff output mode | `scripts/regenerate_benchmark_reference.py` | T6 | — | `--dry-run` prints per-technique diff (expected vs actual) without writing. Exit code 0 if no diffs, 1 if diffs found. |
| T8 | Add write mode with metadata update | `scripts/regenerate_benchmark_reference.py` | T7 | — | Without `--dry-run`, writes updated JSON with new `last_updated` timestamp. Preserves `notes` fields and optional fields not derived from pipeline. |

### Phase 4: Documentation & Cleanup (T9–T11)

| task_id | task | file(s) | depends_on | parallel | definition_of_done |
|---------|------|---------|------------|----------|--------------------|
| T9 | Update AGENTS.md with new files | `AGENTS.md` | T4, T8 | [P] | AGENTS.md mentions `technique-benchmark-reference.json` in fixtures section and `regenerate_benchmark_reference.py` in scripts section |
| T10 | Remove legacy code (hardcoded dict) | `tests/test_technique_calibration.py` | T5 | — | No `TechniqueSpec` dict entries remain in test file. Only `_load_registry()`, `TECHNIQUE_REGISTRY = _load_registry()`, and `EXCLUDED_NON_TSUMEGO_TAGS`. Confirm via grep: `grep -c "fixture.*sgf" test_technique_calibration.py` returns 0 for inline fixture references. |
| T11 | Final regression test | all | T9, T10 | — | Run: `pytest tests/test_technique_calibration.py -v --tb=short -m unit` passes (3/3 unit tests). Verify JSON is valid: `python -m json.tool tests/fixtures/technique-benchmark-reference.json > /dev/null`. Regen script `--dry-run` executes without errors (may skip if no KataGo). |

## Dependency Graph

```
T1 ──→ T2 ──→ T3 ──→ T4 ──→ T5 ──→ T10 ──→ T11
 │                                      ↑
 └──→ T6 [P] ──→ T7 ──→ T8 ──→ T9 [P] ─┘
```

- T1: Foundation (JSON file)
- T2: Verification gate
- T3–T5: Core refactor (sequential, test-driven)
- T6–T8: Regen script (parallel with T3–T5 after T1)
- T9: Documentation (parallel after T4 and T8 complete)
- T10: Legacy removal (after T5 confirms tests pass)
- T11: Final regression gate

## Notes

- T4 and T10 may merge into a single edit (remove dict, add loader in one step) but are listed separately for clarity and rollback granularity
- T6–T8 can be developed independently of T3–T5 since both only depend on T1 (the JSON file)
- Integration tests (5×25) require KataGo — they will be skipped in environments without the binary. Unit tests (T5) are the primary regression gate.
- Regen script (T6–T8) is a "nice to have" tool — if it blocks, T3–T5 and T9–T11 can ship independently
