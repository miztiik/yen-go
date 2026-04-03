# Execution Log: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Executor**: Plan-Executor  
> **Last Updated**: 2026-03-08

---

## Intake Validation

| EX-1 | Check                           | Result                                     |
| ---- | ------------------------------- | ------------------------------------------ |
| EX-1 | Charter approved                | ✅ GOV-CHARTER-APPROVED                    |
| EX-2 | Options approved                | ✅ GOV-OPTIONS-APPROVED (OPT-2 unanimous)  |
| EX-3 | Plan approved                   | ✅ GOV-PLAN-CONDITIONAL → all RCs resolved |
| EX-4 | Tasks approved                  | ✅ 35 tasks in dependency order            |
| EX-5 | Analysis findings resolved      | ✅ No unresolved CRITICAL findings         |
| EX-6 | Backward compatibility decision | ✅ Not required (explicit)                 |
| EX-7 | Documentation plan present      | ✅ DOC-1 (N/A), DOC-2 ✅, DOC-3 ✅         |
| EX-8 | Governance handover consumed    | ✅ RC-1, RC-2, RC-3 all resolved           |

---

## Task Execution

### Phase 1: Data Types & Infrastructure (T1-T5)

| EX-ID | Task                                               | Status | Evidence                                                                                   |
| ----- | -------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------ |
| EX-9  | T1: Clean slate + imports + MIT attribution header | ✅     | `tsumego_frame.py` header: KaTrain SHA 877684f9 + ghostban v3.0.0-alpha.155                |
| EX-10 | T2: `FrameConfig` dataclass                        | ✅     | Frozen, defaults: margin=2, offence_to_win=10, ko_type="none", board_size=19               |
| EX-11 | T3: `NormalizedPosition` dataclass                 | ✅     | Frozen: position, flip_x, flip_y, original_board_size                                      |
| EX-12 | T4: `FrameRegions` dataclass                       | ✅     | Frozen: puzzle_bbox, puzzle_region, occupied, board_edge_sides, defense_area, offense_area |
| EX-13 | T5: `FrameResult` dataclass                        | ✅     | Mutable: position, frame_stones_added, attacker_color, normalized                          |

### Phase 2: Core Functions (T6-T13)

| EX-ID | Task                            | Status | Evidence                                                                                        |
| ----- | ------------------------------- | ------ | ----------------------------------------------------------------------------------------------- |
| EX-14 | T6: `guess_attacker()`          | ✅     | Stone-count + edge-proximity heuristic (≥3:1 ratio → majority is attacker, else edge-proximity) |
| EX-15 | T7: `normalize_to_tl()`         | ✅     | Flip X/Y based on center-of-mass vs midpoint                                                    |
| EX-16 | T8: `denormalize()`             | ✅     | Reverse flip_x/flip_y                                                                           |
| EX-17 | T9: `detect_board_edge_sides()` | ✅     | Returns frozenset of {"top","left","right","bottom"}                                            |
| EX-18 | T10: `compute_regions()`        | ✅     | Board-size-proportional offence_to_win scaling (reference: 19x19)                               |
| EX-19 | T11: `fill_territory()`         | ✅     | Count-based interleaved fill, dense near seam, checkerboard holes far                           |
| EX-20 | T12: `place_border()`           | ✅     | Attacker-colored wall on non-edge sides only                                                    |
| EX-21 | T13: `place_ko_threats()`       | ✅     | KaTrain 2-pattern threats, gated on ko_type != "none"                                           |

### Phase 3: Orchestration (T14-T16)

| EX-ID | Task                          | Status | Evidence                                                               |
| ----- | ----------------------------- | ------ | ---------------------------------------------------------------------- |
| EX-22 | T14: `build_frame()`          | ✅     | Orchestrator with fill→border→ko occupied tracking to prevent overlaps |
| EX-23 | T15: `apply_tsumego_frame()`  | ✅     | Public entry, keyword-only args, offense_color wired through           |
| EX-24 | T16: `remove_tsumego_frame()` | ✅     | Trivial restoration (MHC-4)                                            |

### Phase 4: Caller Update (T17)

| EX-ID | Task                                   | Status | Evidence                           |
| ----- | -------------------------------------- | ------ | ---------------------------------- |
| EX-25 | T17: `query_builder.py` ko_type wiring | ✅     | Line ~101: `ko_type=ko_type` added |

### Phase 5: Tests (T18-T29)

| EX-ID | Task                                          | Status | Evidence                                                         |
| ----- | --------------------------------------------- | ------ | ---------------------------------------------------------------- |
| EX-26 | T18: Test infrastructure                      | ✅     | 6 factory functions, helper utilities                            |
| EX-27 | T19: TestGuessAttacker                        | ✅     | 6 tests (4 original + 2 new: heavy imbalance, moderate fallback) |
| EX-28 | T20: TestNormalizeTL + TestDenormalize        | ✅     | 3 + 4 parametrized tests                                         |
| EX-29 | T21: TestComputeRegions + TestDetectEdgeSides | ✅     | 2 + 4 tests                                                      |
| EX-30 | T22: TestFillTerritory                        | ✅     | 3 tests (density, no-region, balance)                            |
| EX-31 | T23: TestPlaceBorder                          | ✅     | 2 tests (TL corner, center)                                      |
| EX-32 | T24: TestPlaceKoThreats                       | ✅     | 3 tests (placed, not placed, no overlap)                         |
| EX-33 | T25: TestApplyTsumegoFrame                    | ✅     | 8 tests, parametrized 9/13/19                                    |
| EX-34 | T26: TestRemoveTsumegoFrame                   | ✅     | 1 roundtrip test                                                 |
| EX-35 | T27: TestOffenceToWin                         | ✅     | 2 tests (different values, default)                              |
| EX-36 | T28: TestKoTypeWiring (ko_type="direct")      | ✅     | Integration test in test_query_builder.py                        |
| EX-37 | T29: TestKoTypeWiring (default)               | ✅     | Default ko_type="none" compatibility                             |

### Phase 6: Validation (T30-T33)

| EX-ID | Task                                            | Status     | Evidence                                                                            |
| ----- | ----------------------------------------------- | ---------- | ----------------------------------------------------------------------------------- |
| EX-38 | T30: Full test suite                            | ✅         | 46 tsumego_frame + 20 query_builder + 205 dependent = 271 passed, 0 failed          |
| EX-39 | T31: Regression comparison (MHC-5, recommended) | ⏭ Skipped | Recommended, not required. KataGo integration test validates real evaluation works. |
| EX-40 | T32: remove_tsumego_frame preserved             | ✅         | Function exists, tested, MHC-4 verified                                             |
| EX-41 | T33: MIT attribution header                     | ✅         | Done as part of T1                                                                  |

### Phase 7: Legacy Cleanup (T34-T35)

| EX-ID | Task                         | Status | Evidence                                                                |
| ----- | ---------------------------- | ------ | ----------------------------------------------------------------------- |
| EX-42 | T34: Grep for V1 internals   | ✅     | `findstr` for `_PUZZLE_MARGIN`, `_add_stone`, `_fill_board`: no matches |
| EX-43 | T35: Remove V1 test fixtures | ✅     | Done as part of T18 (complete test rewrite)                             |

---

## Deviations from Plan

| DEV-ID | Description                                                                    | Justification                                                                                                                                                                           | Impact                                                                                                           |
| ------ | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| DEV-1  | Added stone-count heuristic (≥3:1) to `guess_attacker`                         | Edge-proximity alone misidentifies attacker in enclosure puzzles (nakade.sgf: 16B vs 2W). KaTrain heuristic assumes balanced stone counts typical of 19x19 corner problems.             | Fixes `test_real_puzzle_enrichment` rejection. No regression in balanced puzzles (falls back to edge-proximity). |
| DEV-2  | Added board-size-proportional scaling of `offence_to_win` in `compute_regions` | `offence_to_win=10` creates 62% territory imbalance on 9x9 (vs 6.7% on 19x19). Unscaled, small-board frames overwhelm KataGo evaluation. Ghostban formula designed for 19x19 reference. | Scaling: `max(1, round(otw * bs² / 361))`. 9x9→2, 13x13→5, 19x19→10 (unchanged).                                 |
| DEV-3  | Fixed fill/border stone overlap in `build_frame`                               | `place_border` was not aware of fill stones — could place duplicates at same position. Build_frame now passes fill-occupied set to border, and fill+border-occupied set to ko.          | Prevents duplicate stones in KataGo query.                                                                       |
| DEV-4  | Wired `offense_color` parameter through to `build_frame`                       | Parameter was declared in `apply_tsumego_frame` but never passed to internal logic. Now `build_frame` accepts optional `offense_color` and uses it to override `guess_attacker`.        | API contract fulfilled. No external callers currently pass `offense_color`.                                      |
| DEV-5  | Skipped T31 (regression comparison script)                                     | MHC-5 is "recommended, not blocking". Real KataGo validation via `test_real_puzzle_enrichment` provides stronger evidence.                                                              | No risk — KataGo integration test validates end-to-end.                                                          |

---

## MHC Compliance

| MHC-ID | Constraint                                | Status     | Evidence                                                                                                                    |
| ------ | ----------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| MHC-1  | Entry point compatible                    | ✅         | `apply_tsumego_frame(position, *, margin, offense_color, ko_type, offence_to_win)` — keyword-only args, backward compatible |
| MHC-2  | `offence_to_win` configurable, default 10 | ✅         | FrameConfig default + TestOffenceToWin                                                                                      |
| MHC-3  | No new external dependencies              | ✅         | Only stdlib imports (logging, dataclasses)                                                                                  |
| MHC-4  | `remove_tsumego_frame()` preserved        | ✅         | Function exists + TestRemoveTsumegoFrame                                                                                    |
| MHC-5  | Regression comparison (recommended)       | ⏭ Skipped | KataGo integration test provides equivalent validation                                                                      |
