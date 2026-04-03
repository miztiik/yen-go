# Execution Log — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T7, T8, T8.1, T9 | tests/fixtures/*.sgf | PH-A complete | ✅ merged |
| L2 | T10, T11, T13 | test_fixture_coverage.py, test_fixture_integrity.py, TECHNIQUE_FIXTURE_AUDIT.md | L1 | ✅ merged |
| L3 | T12 | — (verification) | L2 | ✅ merged |
| L4 | T14, T15 | tests/fixtures/extended-benchmark/ | PH-A complete | ✅ merged |
| L5 | T16 | test_fixture_integrity.py | L4 | ✅ merged |
| L6 | T17, T18, T19, T20, T21 | test_technique_calibration.py | L3 | ✅ merged |
| L7 | T23, T24 | AGENTS.md, _render_all_techniques.py | L6 | ✅ merged |
| L8 | T25 | — (verification) | L7 | ✅ merged |

## Per-Task Completion Log

### PH-A: Fixture Sourcing (completed in prior session)

| task_id | status | evidence |
|---------|--------|----------|
| T1 | ✅ | Grepped goproblems/ogs for YT-tagged SGFs, found 5+ candidates per technique |
| T2 | ✅ | Grepped goproblems_difficulty_based for stratified candidates |
| T3 | ✅ | Rendered + evaluated via Execution-Worker subagent |
| T4 | ✅ | Expert selection: 7 gap fixtures + 15 extended-benchmark candidates |
| T5 | ✅ | Replacement decisions: joseki/fuseki/endgame excluded as non-tsumego |
| T6 | ✅ | Cutting replacement: goproblems/129.sgf selected |

### PH-B: Fixture Swap (atomic)

| task_id | status | evidence |
|---------|--------|----------|
| T7 | ✅ | Deleted: endgame.sgf, fuseki.sgf, joseki.sgf via `Path.unlink()` |
| T8 | ✅ | Replaced: connection_puzzle.sgf←106.sgf, shape.sgf←108.sgf; Added: living_puzzle.sgf←1121.sgf |
| T8.1 | ✅ | Replace-in-place: simple_life_death.sgf←1042.sgf, tesuji.sgf←968.sgf. Updated golden5 correct_move_gtp D1→B2, board_size 9→19 |
| T9 | ✅ | Replaced: cutting.sgf←129.sgf. Normalized YT to include `cutting` |
| T10 | ✅ | Updated ALL_TAG_FIXTURES (30 entries), ALL_KNOWN_TAG_SLUGS (25 active), EXCLUDED_NON_TSUMEGO_TAGS, fixed miai→living, updated TECHNIQUE_CASES, FIXTURE_TAG_IDS, wrong-branch tests, Sensei's references |
| T11 | ✅ | Added EXTENDED_BENCHMARK_DIR + TestExtendedBenchmarkPopulation to test_fixture_integrity.py |
| T12 | ✅ | pytest: 334 passed, 4 deselected (test_fixture_coverage.py -m unit) |
| T13 | ✅ | Updated TECHNIQUE_FIXTURE_AUDIT.md Stage 2 + Stage 2b completion status |

### PH-C: Extended Benchmark

| task_id | status | evidence |
|---------|--------|----------|
| T14 | ✅ | Created tests/fixtures/extended-benchmark/README.md with inventory table |
| T15 | ✅ | Copied 13 SGFs (5 techniques × 2-3 difficulty levels) from goproblems |
| T16 | ✅ | Added TestExtendedBenchmarkPopulation (3 tests: min_count, technique_coverage, has_readme). 8 passed |

### PH-D: Live Test Suite

| task_id | status | evidence |
|---------|--------|----------|
| T17 | ✅ | Created test_technique_calibration.py with TechniqueSpec TypedDict + TECHNIQUE_REGISTRY (25 entries) + EXCLUDED_NON_TSUMEGO_TAGS |
| T18 | ✅ | Implemented class-scoped engine fixture (same pattern as golden5), @pytest.mark.slow + @pytest.mark.integration |
| T19 | ✅ | Implemented 5 parametrized tests: test_correct_move, test_technique_tags, test_difficulty_range, test_refutations, test_teaching_comments |
| T20 | ✅ | Implemented 3 unit tests: test_all_tags_have_registry_entry (config cross-check), test_registry_entries_reference_existing_fixtures, test_no_excluded_tags_in_registry. 3 passed |
| T21 | ✅ | Populated all 25 registry entries with correct_move_gtp, expected_tags, difficulty ranges, refutation counts from fixture analysis |
| T22 | ⏭️ SKIPPED | KataGo binary not available in workspace — integration tests auto-skip |

### PH-E: Documentation and Cleanup

| task_id | status | evidence |
|---------|--------|----------|
| T23 | ✅ | Updated AGENTS.md: added test_technique_calibration.py entry + extended-benchmark/ description |
| T24 | ✅ | Deleted _render_all_techniques.py via `Path.unlink()` |
| T25 | ✅ | Regression: 337 passed on modified files; 1624 passed backend unit; 26 pre-existing failures in unmodified test_sgf_enricher.py |

## Deviations

1. **T22 skipped**: KataGo binary not available in workspace. Integration tests have `@pytest.mark.skipif` guard. This is expected — live validation requires local KataGo setup.
2. **Naming convention**: Extended-benchmark uses `{technique}_{level}_{source_id}.sgf` (underscore-separated) instead of plan's `{technique}-{level}.sgf` (hyphen-separated). Reason: technique slugs already contain hyphens (e.g., `life-and-death`), making underscore the only unambiguous separator.
3. **26 pre-existing failures** in test_sgf_enricher.py: These exist in the baseline before our changes and are unrelated to fixture work.
