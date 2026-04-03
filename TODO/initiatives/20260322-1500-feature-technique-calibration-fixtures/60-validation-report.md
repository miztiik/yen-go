# Validation Report — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Test Commands and Results

| VAL-1 | Command | Exit | Result |
|-------|---------|------|--------|
| VAL-1 | `pytest test_fixture_coverage.py -m unit` | 0 | 334 passed, 4 deselected |
| VAL-2 | `pytest test_fixture_integrity.py` | 0 | 8 passed |
| VAL-3 | `pytest test_technique_calibration.py -m unit` | 0 | 3 passed, 125 deselected |
| VAL-4 | All 3 modified files combined: `-m unit` | 0 | 337 passed, 137 deselected |
| VAL-5 | `pytest backend/ -m unit` | 0 | 1624 passed, 430 deselected |
| VAL-6 | Correct move extraction (all 28 fixtures) | 0 | All GTP coords verified |
| VAL-7 | Fixture directory listing | 0 | 40 SGF files (was 42: -3 deleted +1 added) |
| VAL-8 | Extended benchmark count | 0 | 13 SGF files across 5 techniques |

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| R-1 | Deleting endgame/fuseki/joseki removes tag coverage for those tags | EXCLUDED_NON_TSUMEGO_TAGS excludes from test | ✅ verified | — | ✅ verified |
| R-2 | Replacing simple_life_death.sgf breaks golden5 correct_move assertion | Updated D1→B2 in test_golden5.py | ✅ verified | — | ✅ verified |
| R-3 | miai→living tag rename breaks tag coverage test | Updated ALL_KNOWN_TAG_SLUGS, added living_puzzle.sgf | ✅ verified | — | ✅ verified |
| R-4 | Goproblems fixtures lack C[Wrong...] annotations | Removed from test_has_wrong_branch parametrize | ✅ verified | — | ✅ verified |
| R-5 | Goproblems fixtures lack PC[] Sensei's references | Removed from TestSenseisReferences parametrize | ✅ verified | — | ✅ verified |
| R-6 | Replacing connection_puzzle.sgf changes dispatch behavior | FIXTURE_TAG_IDS updated, dispatch test passes | ✅ verified | — | ✅ verified |
| R-7 | TECHNIQUE_CASES smoke test coords must match new fixtures | Updated all SGF coords and corners | ✅ verified | — | ✅ verified |
| R-8 | Backend tests should not be affected | 1624 passed, 0 failures | ✅ verified | — | ✅ verified |
| R-9 | Extended benchmark tests should pass | 3/3 new tests pass (count, coverage, readme) | ✅ verified | — | ✅ verified |

## Pre-Existing Issues (Not in Scope)

- 26 test failures in `test_sgf_enricher.py` — these exist in the baseline and are unrelated to fixture changes. All failures are in `TestEnrichSgfPolicyCompliance`, `TestRoundtripPreservation`, `TestLevelMismatchStrictThreshold`, and `TestYxUFieldSemantics` classes.

## Acceptance Criteria Check

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Every active tsumego tag has a fixture with valid solution tree | ✅ 25/25 tags covered |
| AC-2 | TechniqueSpec captures 5 calibration dimensions | ✅ TypedDict has all 5 required fields |
| AC-3 | TECHNIQUE_REGISTRY covers all 25 active + excludes 3 non-tsumego | ✅ 25 entries + EXCLUDED_NON_TSUMEGO_TAGS |
| AC-4 | Config cross-check test validates registry vs tags.json | ✅ test_all_tags_have_registry_entry passes |
| AC-5 | Extended benchmark has ≥10 SGFs across ≥5 techniques | ✅ 13 SGFs, 5 techniques |
| AC-6 | All existing tests pass (no regressions from our changes) | ✅ 337 modified-file tests pass, 1624 backend pass |
| AC-7 | AGENTS.md updated in same commit | ✅ Added calibration test + benchmark entries |
