# Tasks — KataGo Winrate Perspective Fix + Enrichment Reconciliation

Last Updated: 2026-03-08

## Phase 1: Perspective Fix + Tests (G1, G2, G3, G8, G9)

- [ ] **T1** — Change `reportAnalysisWinratesAs` to `SIDETOMOVE` in both KataGo config files [P]
  - `katago/tsumego_analysis.cfg` L41: `reportAnalysisWinratesAs = SIDETOMOVE`
  - `katago/analysis_example.cfg` L30: `reportAnalysisWinratesAs = SIDETOMOVE`
  - Files: `katago/tsumego_analysis.cfg`, `katago/analysis_example.cfg`
  - AC: AC1

- [ ] **T2** — Document `generate_refutations.py` L214 as correct under SIDETOMOVE
  - Under SIDETOMOVE: after opponent moves, KataGo reports winrate from opponent's perspective. `1.0 - opp_best.winrate` correctly flips to puzzle player's perspective. Research §2.3 confirms this is correct for BOTH Black and White puzzles.
  - Action: Add explanatory comment at L214 documenting why the flip is correct under SIDETOMOVE
  - Files: `analyzers/generate_refutations.py`
  - AC: AC2

- [ ] **T3** — Fix MockConfirmationEngine in tests
  - Remove the manual `1.0 - data["winrate"]` flip in MockConfirmationEngine. Under SIDETOMOVE, the mock should return winrate from the current player's (opponent's) perspective directly, which is what `normalize_winrate(opp_wr, opponent_color, puzzle_player)` at L242 expects.
  - Files: `tests/test_solve_position.py`
  - AC: AC9
  - Depends: T1

- [ ] **T4** — Add White-to-play parametrized test coverage [P]
  - Add at least 1 White-to-play test fixture SGF (small board, known answer)
  - Parametrize classification test: B and W puzzle through `analyze_position_candidates()` — verify TE/BM classification is correct for both
  - Parametrize validation test: B and W puzzle through `validate_correct_move()` — verify ACCEPTED for both
  - Parametrize difficulty test: B and W puzzle through `estimate_difficulty()` — verify scores are reasonable for both
  - Test `normalize_winrate()` under SIDETOMOVE: `(0.8, "B", "B") → 0.8`, `(0.8, "W", "B") → 0.2`, `(0.8, "B", "W") → 0.2`, `(0.8, "W", "W") → 0.8`
  - Files: `tests/test_solve_position.py`, `tests/test_validate_correct_move.py` (or new test file)
  - AC: AC3

- [ ] **T5** — Run baseline tests (regression check)
  - Run full test suite: `pytest` in `tools/puzzle-enrichment-lab/`
  - Document pass/fail count
  - AC: AC11
  - Depends: T1, T2, T3, T4

- [ ] **T6** — Re-run session evidence puzzle (MANUAL validation — requires live KataGo, does not gate Phase 2)
  - Re-enrich `(;SZ[19]FF[4]GM[1]PL[B]C[problem 1 ]AB[fb][bb][cb][db]AW[ea][dc][cc][eb][bc])`
  - Verify: correct_moves > 0, solution tree built, refutation branches present
  - AC: AC10
  - Depends: T5

## Phase 2: Comprehensive Logging (G4, G5)

- [ ] **T7** — Add decision logging to `solve_position.py` [P]
  - Log each move’s classification decision: move coord, quality (TE/BM/NEUTRAL), delta, root winrate, move winrate, policy, thresholds used
  - Log root winrate with perspective context (SIDETOMOVE)
  - Log each tree branch stopping condition when triggered (which condition, at what depth)
  - Log co-correct three-signal check detail for each alternative (both_te, wr_gap, score_gap)
  - Files: `analyzers/solve_position.py`
  - AC: AC4

- [ ] **T8** — Add decision logging to `validate_correct_move.py` [P]
  - Log validator dispatcher selection
  - Log `_classify_move` results: correct_move, is_top, in_top_n, winrate, policy, rank, visits
  - Log `_status_from_classification` threshold comparison and resulting status
  - Log ownership rescue trigger (status change)
  - Log final validation decision: status, reason, flags
  - Files: `analyzers/validate_correct_move.py`
  - AC: AC4

- [ ] **T9** — Add decision logging to `estimate_difficulty.py` [P]
  - Log all 4 component scores with their inputs and weights
  - Log structural sub-weights breakdown (each of the 5 sub-signals)
  - Log final raw_score, suggested_level, level_id, confidence with reasoning
  - Files: `analyzers/estimate_difficulty.py`
  - AC: AC4

- [ ] **T10** — Add decision logging to `technique_classifier.py` [P]
  - Log each detector invocation and result (fired/not-fired with key parameters)
  - Log fallback trigger when no technique detected
  - Log final sorted tag list
  - Files: `analyzers/technique_classifier.py`
  - AC: AC4

- [ ] **T11** — Add decision logging to `ko_validation.py` [P]
  - Log ko detection result: ko_detected, recurrence coordinates, capture verification result
  - Log ko type inference and reasoning
  - Log ko validation status decision with thresholds
  - Files: `analyzers/ko_validation.py`
  - AC: AC4

- [ ] **T12** — Add decision logging to `generate_refutations.py` [P]
  - Log initial winrate baseline for refutation delta computation
  - Log each candidate accept/reject decision with delta, threshold, policy
  - Log ko-aware threshold override when active
  - Files: `analyzers/generate_refutations.py`
  - AC: AC4

- [ ] **T13** — Add decision logging to `enrich_single.py` + `query_builder.py` [P]
  - Log goal inference reasoning: inferred goal, score_delta, ownership_variance
  - Log allowed_moves coordinate list in query_builder (not just count)
  - Files: `analyzers/enrich_single.py`, `analyzers/query_builder.py`
  - AC: AC4

- [ ] **T14** — Fix log naming: run_id for `enrich` CLI + conftest alignment
  - In `cli.py`: generate `run_id = generate_run_id()` and call `set_run_id(run_id)` before enrichment starts in the `enrich` subcommand path
  - In `conftest.py`: change format to `"test-" + generate_run_id()` (uses YYYYMMDD-HHMMSS-8HEXUPPER)
  - Files: `cli.py`, `conftest.py`
  - AC: AC5, AC6

- [ ] **T15** — Phase 2 regression test
  - Run full test suite
  - Verify logging additions don't break tests
  - Run ruff on all modified files
  - AC: AC11, AC12
  - Depends: T7-T14

## Phase 3: Quality Fixes + Cleanup (G6, G7, G10, G11, Config)

- [ ] **T16** — Fix ko detection false positives (capture verification)
  - In `detect_ko_in_pv()`: add capture verification — coordinate recurrence is ko ONLY if the recaptured intersection shows a stone being removed then placed. Check that between two occurrences of the same coordinate, the opponent captured the previous stone.
  - Add test cases: atari sequence (same coord, no ko) vs actual ko (capture-recapture cycle)
  - Files: `analyzers/ko_validation.py`, test file
  - AC: AC13
- [ ] **T17** — Fix difficulty collinearity (weight rebalancing)
  - Reduce policy_rank and visits_to_solve weights (PUCT-coupled: high-policy moves get more visits, so both signal the same thing). Increase structural weight (independent signal).
  - Constraint: policy_rank + visits_to_solve combined must be < 40%; structural must be > 35%. Determine exact split by comparing before/after level distribution on golden fixtures if available.
  - If no fixture comparison available, use: policy_rank=15, visits_to_solve=15, trap_density=25, structural=45
  - Update both JSON (`config/katago-enrichment.json`) and Pydantic defaults to match
  - Add test: verify weights sum to 100
  - Files: `config/katago-enrichment.json`, `config.py`, test file
  - AC: AC14
  - Note: Exact weights are provisional until calibration sweep (NG6)

- [ ] **T18** — Sync stale Pydantic defaults + seki field
  - `DifficultyWeights`: sync Pydantic defaults (currently 30/30/20/20) to match new weights from T17
  - `TeachingConfig`: sync `non_obvious_policy` 0.05→0.10, `ko_delta_threshold` 0.1→0.12
  - `QualityGatesConfig`: sync `acceptance_threshold` 0.85→0.95
  - Add `score_threshold: float = 5.0` to `SekiDetectionConfig` model
  - Add `"score_threshold": 5.0` to JSON `technique_detection.seki`
  - Files: `config.py`, `config/katago-enrichment.json`
  - Depends: T17

- [ ] **T19** — Remove dead code
  - Delete `models/difficulty_result.py` (backward-compat shim) — update any imports to use `difficulty_estimate.py` directly
  - Remove orphan `level_mismatch` section from `config/katago-enrichment.json`
  - Files: `models/difficulty_result.py`, `config/katago-enrichment.json`, any importing files

- [ ] **T20** — Remove `ai_solve.enabled` flag
  - Remove `enabled: bool` from `AiSolveConfig` in `config.py`
  - Remove `"enabled": false` from JSON `ai_solve` section
  - In `enrich_single.py`: remove `ai_solve_active = ... and ai_solve_config.enabled` gating — always-on
  - Simplify the has-solution path that checks `ai_solve_active`
  - Files: `config.py`, `config/katago-enrichment.json`, `analyzers/enrich_single.py`
  - AC: AC8

- [ ] **T21** — Phase 3 regression test + ruff
  - Run full test suite
  - Run ruff on all modified files
  - Re-run session evidence puzzle again to verify full pipeline with all fixes
  - AC: AC11, AC12
  - Depends: T16-T20

## Parallel Markers

Tasks marked `[P]` can run in parallel within their phase:

- Phase 1: T1+T4 parallel (config + tests); T2, T3 depend on T1
- Phase 2: T7-T13 all parallel (independent modules); T14 parallel; T15 depends on all
- Phase 3: T16, T17, T19, T20 can be parallel; T18 depends on T17; T21 depends on all

## Task → Goal → AC Traceability

| Task   | Goal   | AC         |
| ------ | ------ | ---------- |
| T1     | G1     | AC1        |
| T2     | G2     | AC2        |
| T3     | G8     | AC9        |
| T4     | G3     | AC3        |
| T5     | —      | AC11       |
| T6     | G9     | AC10       |
| T7-T13 | G4     | AC4        |
| T14    | G5     | AC5, AC6   |
| T15    | —      | AC11, AC12 |
| T16    | G10    | AC13       |
| T17    | G11    | AC14       |
| T18    | Config | —          |
| T19    | G6     | AC7        |
| T20    | G7     | AC8        |
| T21    | —      | AC11, AC12 |

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture, phases, risks
> - [Charter](./00-charter.md) — Goals G1-G11, AC1-AC14
