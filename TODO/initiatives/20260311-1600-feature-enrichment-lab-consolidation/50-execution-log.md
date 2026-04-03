# Execution Log — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-11

## Phase A: Foundation Fixes

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-1 | T1: Per-component debug logging | ✅ done | Added `logger.debug()` after policy, visits, trap, structural component computation in `estimate_difficulty.py` |
| EX-2 | T2: Ko recurrence/adjacency logging | ✅ done | Added `logger.debug()` at recurrence detection, adjacency check, and verdict in `ko_validation.py` |
| EX-3 | T3: Conftest run_id format | ✅ done | Replaced inline run_id generation with `generate_run_id()` from `models.ai_analysis_result` in `conftest.py` |
| EX-4 | T4: Ko capture verification | ✅ done | Added board replay verification via `_verify_ko_capture_on_board()` in `ko_validation.py`. New optional params: `initial_stones`, `first_player_color`, `board_size`. Backward compatible — without initial_stones, falls back to adjacency-only |
| EX-5 | T5: Remove ai_solve_active | ✅ done | Removed all 6 references to `ai_solve_active` variable. Replaced with direct `ai_solve_config is not None` checks. Simplified conditional branches |
| EX-6 | T6: Remove level_mismatch config | ✅ done | Pre-step: grep confirmed only `sgf_enricher.py:83` and `config/katago-enrichment.json:160` reference `level_mismatch` (singular). Backend `level_mismatches` (plural) is unrelated. Removed JSON section. Replaced `_load_mismatch_threshold()` with `_MISMATCH_THRESHOLD = 3` constant (retains active overwrite behavior at ≥3 level steps). Existing test `test_overwrites_existing_yg_on_large_mismatch` continues to assert overwrite at distance=4 |
| EX-7 | T7: Doc stubs | ✅ done | Added placeholder sections in `docs/concepts/quality.md`, `docs/architecture/tools/katago-enrichment.md`, `docs/reference/enrichment-config.md` |
| EX-8 | T8: Phase A regression | ✅ done | 214 passed, 3 skipped. Pre-existing weight config test failure excluded |

## Phase B: Algorithms

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-9 | T9: Benson's unconditional life | ✅ done | Created `analyzers/benson_check.py` (~210 lines). `find_unconditionally_alive_groups()` implements Benson 1976 — iterative elimination of groups with < 2 vital regions. Returns `set[frozenset[tuple[int,int]]]` |
| EX-10 | T10: Interior-point death check | ✅ done | Added `check_interior_point_death()` to `benson_check.py`. Counts empty cells within `puzzle_region`, returns True when ≤ 2 non-adjacent |
| EX-11 | T11: Integration into solve_position | ✅ done | Added `puzzle_region` parameter to `_build_tree_recursive()` and `build_solution_tree()`. Pre-query check converts `_BoardState.grid` to dict, checks Benson alive (G1) and interior-point death (G2). Threaded `puzzle_region` through all 4 recursive call sites |
| EX-12 | T12-T13: Benson + interior-point tests | ✅ done | Created `tests/test_benson_check.py` with 13 tests: 5 Benson tests (empty board, two-eye alive, framework false-positive rejection, ko-dependent, seki) + 8 interior-point tests (empty region, 0/1/2/3 empty points, adjacency, opponent stones) |
| EX-13 | T14: Phase B regression | ✅ done | 164 passed, 3 skipped |

## Phase C: Individual Reviews

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-14 | T15: KM Config Extension | ✅ PASS | All JSON/Pydantic fields aligned. Value-gating design (visits=0 disables, not boolean flags) |
| EX-15 | T16: KM Transposition | ✅ PASS | _BoardState with Zobrist hashing, 20 tests |
| EX-16 | T17: KM Simulation | ✅ PASS | _try_simulation() called at opponent nodes, 8 tests |
| EX-17 | T18: KM Forced Move | ✅ PASS | Reduced visits when single candidate, safety net, 5 tests |
| EX-18 | T19: KM Proof-Depth | ✅ PASS | _compute_max_resolved_depth() post-build, 7 tests across 2 files |
| EX-19 | T20: KM Benchmarks+Docs | ✅ PASS | 5 perf test files, D52-D56 in architecture docs |
| EX-20 | T21: S1-G16 confirmation queries | ✅ PASS | engine parameter wired, 6 tests |
| EX-21 | T22: S1-G15 classify_move_quality | ✅ PASS | config parameter, not hardcoded, 8+ tests |
| EX-22 | T23: S1-G1 ownership convergence | ✅ PASS | _check_ownership_convergence(), 3 tests |
| EX-23 | T24: S1-G12 corner/ladder boosts | ✅ PASS | Config fields aligned, 3 tests |
| EX-24 | T25: S1-G14 co-correct score gap | ✅ PASS | Three-signal check, 2 tests |
| EX-25 | T26: S2-G2 multi-root tree | ✅ PASS | Priority A/B/C allocation, 2 tests |
| EX-26 | T27: S2-G3 has-solution path | ✅ PASS | validate + discover_alternatives, tests present |
| EX-27 | T28: S2-G5 human_solution_confidence | ✅ PASS | Wired from discover_alternatives to result, 2 tests |
| EX-28 | T29: S2-G6 ai_solution_validated | ✅ PASS | Boolean flag wired, tests present |
| EX-29 | T30: S2-G17 discover_alternatives async+tree | ✅ PASS | Builds alternative trees, tests present |
| EX-30 | T31: S2-G13 parallel tree building | ✅ PASS | ThreadPoolExecutor with split budgets |
| EX-31 | T32: S3-G4 AC level wiring | ✅ PASS | 4-level decision matrix, 4 tests |
| EX-32 | T33: S3-G7 roundtrip assertion | ✅ PASS | extract_correct_first_move assert non-None |
| EX-33 | T34: S3-G11 goal inference | ✅ PASS | infer_goal() with score deltas + ownership, 5 tests |
| EX-34 | T35: S4-G8 BatchSummary emitter | ✅ PASS | Accumulator wired in cli.py, 2+ tests |
| EX-35 | T36: S4-G9 DisagreementSink | ✅ PASS | JSONL writer in observability.py, 2 tests |
| EX-36 | T37: S4-G10 collection disagreement | ✅ PASS | Per-collection counters, warning threshold, 2 tests |
| EX-37 | T38: S5-G20 missing tests | ✅ PASS | All sprint test files exist, 57+ test files |
| EX-38 | T39: S5-G19 missing docs | ✅ PASS | README, GUI docs, module docstrings present |
| EX-39 | T40: S5-G18 calibration | ✅ PASS | Deferred per D3 |

### Phase C: Per-Review Structured Checklist (Reconstructed)

> Added 2026-03-10 per finding F-07 (remediation RT-7). Checklist criteria per RC-2 review template.

| review_id | task | code_present | tests_present | config_aligned | no_dead_code | logging_adequate | edge_cases |
|-----------|------|:---:|:---:|:---:|:---:|:---:|:---:|
| RC-15 | T15: KM Config Extension | ✅ | ✅ | ✅ JSON+Pydantic aligned | ✅ | ✅ value-gating logged | ✅ visits=0 disables |
| RC-16 | T16: KM Transposition | ✅ | ✅ 20 tests | ✅ | ✅ | ✅ Zobrist hash logged | ✅ hash collision, empty board |
| RC-17 | T17: KM Simulation | ✅ | ✅ 8 tests | ✅ | ✅ | ✅ simulation hit/miss logged | ✅ opponent-node-only gate |
| RC-18 | T18: KM Forced Move | ✅ | ✅ 5 tests | ✅ | ✅ | ✅ reduced visits logged | ✅ safety net when single candidate |
| RC-19 | T19: KM Proof-Depth | ✅ | ✅ 7 tests (2 files) | ✅ | ✅ | ✅ max_resolved_depth logged | ✅ single-node tree |
| RC-20 | T20: KM Benchmarks+Docs | ✅ | ✅ 5 perf test files | ✅ | ✅ | N/A (docs) | N/A |
| RC-21 | T21: S1-G16 confirmation | ✅ | ✅ 6 tests | ✅ | ✅ | ✅ | ✅ engine param wiring |
| RC-22 | T22: S1-G15 classify_move | ✅ | ✅ 8+ tests | ✅ config param | ✅ | ✅ | ✅ delta boundary |
| RC-23 | T23: S1-G1 ownership | ✅ | ✅ 3 tests | ✅ | ✅ | ✅ convergence logged | ✅ early convergence |
| RC-24 | T24: S1-G12 boosts | ✅ | ✅ 3 tests | ✅ config fields | ✅ | ✅ boost logged | ✅ corner+ladder |
| RC-25 | T25: S1-G14 co-correct | ✅ | ✅ 2 tests | ✅ | ✅ | ✅ | ✅ three-signal check |
| RC-26 | T26: S2-G2 multi-root | ✅ | ✅ 2 tests | ✅ | ✅ | ✅ | ✅ priority A/B/C allocation |
| RC-27 | T27: S2-G3 has-solution | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ validate+discover |
| RC-28 | T28: S2-G5 human_conf | ✅ | ✅ 2 tests | ✅ | ✅ | ✅ | ✅ |
| RC-29 | T29: S2-G6 ai_validated | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ boolean flag |
| RC-30 | T30: S2-G17 alternatives | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ async+tree |
| RC-31 | T31: S2-G13 parallel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ ThreadPoolExecutor |
| RC-32 | T32: S3-G4 AC levels | ✅ | ✅ 4 tests | ✅ | ✅ | ✅ | ✅ 4-level matrix |
| RC-33 | T33: S3-G7 roundtrip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ assert non-None |
| RC-34 | T34: S3-G11 goal infer | ✅ | ✅ 5 tests | ✅ | ✅ | ✅ | ✅ score delta+ownership |
| RC-35 | T35: S4-G8 BatchSummary | ✅ | ✅ 2+ tests | ✅ | ✅ | ✅ | ✅ accumulator wired |
| RC-36 | T36: S4-G9 Disagreement | ✅ | ✅ 2 tests | ✅ | ✅ | ✅ | ✅ JSONL writer |
| RC-37 | T37: S4-G10 collection | ✅ | ✅ 2 tests | ✅ | ✅ | ✅ warning threshold | ✅ per-collection |
| RC-38 | T38: S5-G20 tests | ✅ | ✅ 57+ files | N/A | ✅ | N/A | N/A (meta) |
| RC-39 | T39: S5-G19 docs | ✅ | N/A | N/A | ✅ | N/A | N/A (meta) |
| RC-40 | T40: S5-G18 calibration | ✅ deferred D3 | N/A | N/A | ✅ | N/A | N/A |

## Phase D: sgfmill Replacement — DROPPED

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-40 | T41-T44: sgfmill replacement | ❌ DROPPED | Complexity assessed as HIGH (3 production files, no mutate+serialize in tools/core, SgfNode type incompatibility, CJK encoding risk). Per MHC-3 drop criterion, Phase D is dropped. sgfmill remains as implicit dependency. |

## Phase E: Documentation

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-41 | T45: docs/concepts/quality.md | ✅ done | Filled Benson gate and interior-point exit sections with quality signal descriptions |
| EX-42 | T46: docs/architecture/tools/katago-enrichment.md | ✅ done | Added D69 (Benson gate), D70 (interior-point exit), D71 (ko capture verification) design decisions |
| EX-43 | T47: docs/how-to/tools/katago-enrichment-lab.md | ✅ done | Added pre-query terminal detection usage guide with Benson, interior-point, and ko capture sections |
| EX-44 | T48: docs/reference/enrichment-config.md | ✅ done | Filled Benson gate and interior-point config sections (no separate config params — integrated into existing transposition + frame config) |
| EX-45 | T49: Cross-reference verification | ✅ done | All 4 docs have See Also callouts linking to the other tiers |
| EX-46 | T50: Final regression | ✅ done | 384 passed, 3 skipped. 1 pre-existing failure unrelated to changes |

## Deviations from Plan

1. **Phase D dropped**: sgfmill replacement was assessed as HIGH complexity (drop criterion MHC-3 met). Key blocking issues: tools/core parser lacks mutate+serialize capability, SgfNode type mismatch requires ~20+ call site rewrites, CJK encoding risk.
2. **level_mismatch config section removed**: After removing the `level_mismatch` JSON section, threshold retained as `_MISMATCH_THRESHOLD = 3` code constant. Existing behavior preserved: YG is overwritten when KataGo-estimated level differs by ≥3 steps from existing value. Test `test_overwrites_existing_yg_on_large_mismatch` validates overwrite at distance=4 (beginner→advanced). Test `test_preserves_yg` validates preservation at distance=1 (beginner→elementary).
3. **Framework false-positive test fixture revised**: Original 5x5 fixture was geometrically incorrect (no Benson vital regions on full-perimeter group). Revised to 9x9 board with clear two-eye framework.

## Remediation Session 1 (2026-03-10): RT-1 through RT-9

Findings F-01 through F-09 identified during deep review. Governance-approved.

| ex_id | finding | fix | status | evidence |
|-------|---------|-----|--------|----------|
| EX-47 | F-01/RT-1: puzzle_region not threaded to build_solution_tree | Wired `puzzle_region` via `FrameConfig`/`compute_regions` in `enrich_single.py` position-only path. Passed to 3 `build_solution_tree()` calls (lines ~409, 440, 474) | ✅ done | Lines 325-332 compute, lines 409/440/474 pass through |
| EX-48 | F-04/RT-4: validate_ko missing position | Added `position` param to `validate_ko()`. Derives `initial_stones`, `first_player_color`, `board_size` from Position. Updated caller in `validate_correct_move.py` | ✅ done | ko_validation.py:373, validate_correct_move.py passes position |
| EX-49 | F-06/RT-6: Stale changelog entries | Annotated v1.6 and v1.11 sections in `katago-enrichment.json` with "(Section retired in v1.15…)" | ✅ done | config/katago-enrichment.json |
| EX-50 | F-08/RT-8: Stale Last Updated dates | Updated "Last Updated" to 2026-03-10 across 4 doc files | ✅ done | docs/concepts/quality.md, architecture, how-to, reference |
| EX-51 | F-09/RT-9: Missing sgfmill in requirements | Added `sgfmill>=2.1.1` to `requirements.txt` | ✅ done | tools/puzzle-enrichment-lab/requirements.txt |
| EX-52 | F-02,F-03,F-05/RT-2,3,5: Gate+ko integration tests | Created `tests/test_gate_integration.py` with 6 tests (Benson gate, interior-point gate, no-region bypass, ko recapture, ko false-positive rejection, position threading spy) | ✅ done | 6 tests pass |

## Remediation Session 2 (2026-03-10): NF-01, NF-02, R1/NF-03, R3, R5

Deeper review findings identified additional bugs and test quality gaps.

| ex_id | finding | fix | status | evidence |
|-------|---------|-----|--------|----------|
| EX-53 | NF-01: `_BoardState` hardcoded `board_size=19` | Replaced with `engine._raw_position.board_size` (fallback 19). ~line 947 in `solve_position.py` | ✅ done | 9x9 and 13x13 tests pass |
| EX-54 | NF-02: `_are_adjacent()` used `<= 1` (identical coords = adjacent) | Changed to `== 1` in `ko_validation.py` ~line 115 | ✅ done | `test_identical_coordinates_not_adjacent` passes |
| EX-55 | R1/NF-03: `discover_alternatives()` missing `puzzle_region` | Added `puzzle_region` param to `discover_alternatives()` sig + threaded to internal `build_solution_tree()`. Caller in `enrich_single.py` passes it through | ✅ done | `test_puzzle_region_forwarded_to_alt_tree_build` passes |
| EX-56 | Missing: `_run_has_solution_path` never computed `puzzle_region` | Added `compute_regions(position, FrameConfig(...))` in `_run_has_solution_path()` before `discover_alternatives()` call. Was causing NameError in 5 tests | ✅ done | `test_enrich_single.py` 29 passed |
| EX-57 | R3/R5: Gate tests weak — wrong query counts, wrong config | Rewrote `test_gate_integration.py`: 14 tests. Fixed `_make_config` to override `depth_profiles` (min/max depth was being ignored). Fixed puzzle_region coords to match GTP→(row,col) mapping. Added NF-01/NF-02/NF-03 coverage | ✅ done | 14/14 pass |

### Regression Results (Remediation Session 2)

- **Gate integration tests**: 14/14 passed
- **Core test files** (enrich_single, solve_position, gate, ko_validation, ai_solve_integration, sprint1, query_builder, sgf_enricher): 268 passed, 3 skipped, 1 pre-existing error
- **Extended files** (remediation_sprints, sprint2-5, benson, correct_move, tsumego_frame): 191 passed, 2 skipped, 2 pre-existing failures, 4 pre-existing errors
- **Pre-existing failures unrelated to changes**: `StructuralDifficultyWeights` validation error (weights sum=110, expected 100) and fixture setup errors in `TestCollectionDisagreementWarning`

## Post-Closeout Amendment: Audit Findings (2026-03-11)

### Finding Corrections

| ex_id | finding | fix | status | evidence |
|-------|---------|-----|--------|----------|
| EX-58 | F-01/G9: EX-6 claimed threshold=99 and test updated; actual code has `_MISMATCH_THRESHOLD = 3` (active overwrite) | Corrected EX-6 description, corrected katago-enrichment.json changelog annotations (v1.6, v1.11), corrected VAL-2 | ✅ done | `sgf_enricher.py:66` has `_MISMATCH_THRESHOLD = 3`; `test_overwrites_existing_yg_on_large_mismatch` asserts overwrite at distance=4 |
| EX-59 | F-01/G9: Missing test for preservation path (small gap < threshold) | Added `test_preserves_existing_yg_on_small_mismatch` to `TestEnrichSgfPolicyCompliance` | ✅ done | Tests beginner→elementary (distance=1 < threshold=3), asserts YG preserved as "beginner" |

### Design Amendment: Terminal Detection Config Decoupling

Governance Gate 8 approved (unanimous, `GOV-REVIEW-CONDITIONAL`, RC-1 naming: `terminal_detection_enabled`).

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-60 | Add `terminal_detection_enabled` field to `AiSolveSolutionTreeConfig` | ✅ done | `config.py`: `terminal_detection_enabled: bool = Field(default=True, ...)` |
| EX-61 | Decouple `board_state` init from `transposition_enabled` | ✅ done | `solve_position.py`: `if tree_config.transposition_enabled or tree_config.terminal_detection_enabled:` |
| EX-62 | Add explicit `terminal_detection_enabled` guard at gate check | ✅ done | `solve_position.py`: `if tree_config.terminal_detection_enabled and board_state is not None and puzzle_region is not None and depth >= min_depth:` |
| EX-63 | Add `terminal_detection_enabled: true` to `katago-enrichment.json` | ✅ done | `config/katago-enrichment.json` solution_tree section |
| EX-64 | Update reference docs (enrichment-config.md) | ✅ done | Benson Gate Config section rewritten with dedicated toggle; Interior-Point Config updated |
| EX-65 | Update architecture docs (katago-enrichment.md) — D72 | ✅ done | New design decision D72: Terminal Detection Config Decoupling |
| EX-66 | Update how-to docs (katago-enrichment-lab.md) | ✅ done | Added `terminal_detection_enabled` to knob table and "Disabling All Optimizations" example |
| EX-67 | Add config field tests (`test_ai_solve_config.py`) | ✅ done | Field presence, type check, backward compat default assertions |
| EX-68 | Add gate-disabled integration tests (`test_gate_integration.py`) | ✅ done | `TestTerminalDetectionConfigDecoupling`: 2 tests — gates disabled (queries not short-circuited), transposition off + gates on (gates still fire) |
| EX-69 | Update Last Updated dates | ✅ done | enrichment-config.md, katago-enrichment.md, katago-enrichment-lab.md → 2026-03-11 |
