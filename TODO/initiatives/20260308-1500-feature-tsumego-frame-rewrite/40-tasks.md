# Tasks: Tsumego Frame Rewrite (OPT-2)

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Selected Option**: OPT-2 (Merged KaTrain + ghostban)  
> **Last Updated**: 2026-03-08

---

## Legend

- `[P]` = Can run in parallel with other `[P]` tasks in this group
- `→ T{n}` = Depends on task T{n}
- Files in scope: `analyzers/tsumego_frame.py`, `analyzers/query_builder.py`, `tests/test_tsumego_frame.py`

---

## Phase 1: Data Types & Infrastructure

| ID  | Task                                                                                                                                              | File(s)                      | Depends | Parallel | Notes                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ------- | -------- | --------------------------------------------- |
| T1  | Delete entire body of `analyzers/tsumego_frame.py`. Keep file. Write new module docstring with MIT attribution (KaTrain + ghostban). Add imports. | `analyzers/tsumego_frame.py` | —       | —        | Clean slate. Old code: ~200 lines → deleted.  |
| T2  | Define `FrameConfig` dataclass (frozen): `margin`, `offence_to_win`, `ko_type`, `board_size`                                                      | `analyzers/tsumego_frame.py` | → T1    | [P]      | Default `offence_to_win=10`, `ko_type="none"` |
| T3  | Define `NormalizedPosition` dataclass (frozen): `position`, `flip_x`, `flip_y`, `original_board_size`                                             | `analyzers/tsumego_frame.py` | → T1    | [P]      | Transformation metadata for denormalize       |
| T4  | Define `FrameRegions` dataclass (frozen): `puzzle_bbox`, `puzzle_region`, `occupied`, `board_edge_sides`, `defense_area`, `offense_area`          | `analyzers/tsumego_frame.py` | → T1    | [P]      | Computed regions for placement                |
| T5  | Define `FrameResult` dataclass: `position`, `frame_stones_added`, `attacker_color`, `normalized`                                                  | `analyzers/tsumego_frame.py` | → T1    | [P]      | Output metadata                               |

## Phase 2: Core Functions

| ID  | Task                                                                                                                                                                           | File(s)                      | Depends  | Parallel          | Notes                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- | -------- | ----------------- | --------------------------------------------------- |
| T6  | Implement `guess_attacker(position) → Color`. Edge-proximity heuristic from KaTrain. Average min-edge-distance per color. Closer-to-edge = defender. Tie-break: Black attacks. | `analyzers/tsumego_frame.py` | → T2     | —                 | ~25 lines. KaTrain `guess_black_to_attack()` logic. |
| T7  | Implement `normalize_to_tl(position) → NormalizedPosition`. Flip X if center in right half, flip Y if center in bottom half.                                                   | `analyzers/tsumego_frame.py` | → T3     | [P] after T6      | ~20 lines. KaTrain `snap()` + `flip_stones()`.      |
| T8  | Implement `denormalize(position, norm_meta) → Position`. Reverse flip_x/flip_y.                                                                                                | `analyzers/tsumego_frame.py` | → T3     | [P] after T6      | ~20 lines. Inverse of T7.                           |
| T9  | Implement `detect_board_edge_sides(bbox, board_size, margin) → set[str]`. Returns which sides of puzzle bbox are within `margin` of board edge.                                | `analyzers/tsumego_frame.py` | → T4     | [P] after T6      | ~10 lines. ghostban border logic.                   |
| T10 | Implement `compute_regions(position, config) → FrameRegions`. Bounding box, puzzle region, occupied set, edge sides (via T9), defense/offense area (ghostban formula).         | `analyzers/tsumego_frame.py` | → T4, T9 | —                 | ~30 lines. Central computation.                     |
| T11 | Implement `fill_territory(position, regions, attacker_color) → list[Stone]`. Count-based half/half fill. Dense near seam, checkerboard holes far from seam.                    | `analyzers/tsumego_frame.py` | → T10    | —                 | ~30 lines. KaTrain `put_outside()` core logic.      |
| T12 | Implement `place_border(position, regions, attacker_color) → list[Stone]`. Attacker-colored wall on non-board-edge sides only.                                                 | `analyzers/tsumego_frame.py` | → T10    | [P] with T11      | ~25 lines. ghostban border logic.                   |
| T13 | Implement `place_ko_threats(position, regions, attacker_color, ko_type, player_to_move) → list[Stone]`. KaTrain's 2 fixed threat patterns. Gated on `ko_type != "none"`.       | `analyzers/tsumego_frame.py` | → T10    | [P] with T11, T12 | ~30 lines. KaTrain `put_ko_threat()`.               |

## Phase 3: Orchestration & Entry Point

| ID  | Task                                                                                                                                                                                                                                | File(s)                      | Depends  | Parallel     | Notes                         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------- | ------------ | ----------------------------- |
| T14 | Implement `build_frame(position, config) → FrameResult`. Orchestrates: guess_attacker → normalize → compute_regions → fill → border → ko_threats → denormalize → assemble Position.                                                 | `analyzers/tsumego_frame.py` | → T6-T13 | —            | ~25 lines. Core orchestrator. |
| T15 | Implement `apply_tsumego_frame(position, *, margin, offense_color, ko_type, offence_to_win) → Position`. Public entry point. Builds FrameConfig, calls build_frame, returns Position. Preserves V1 signature compatibility (MHC-1). | `analyzers/tsumego_frame.py` | → T14    | —            | ~20 lines. Facade.            |
| T16 | Implement `remove_tsumego_frame(framed, original) → Position`. Trivial — returns `original.model_copy(deep=True)`.                                                                                                                  | `analyzers/tsumego_frame.py` | → T1     | [P] with T14 | ~3 lines. MHC-4.              |

## Phase 4: Caller Update

| ID  | Task                                                                                                                                                               | File(s)                      | Depends | Parallel | Notes             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- | ------- | -------- | ----------------- |
| T17 | Update `query_builder.py` line 101: pass `ko_type=ko_type` to `apply_tsumego_frame()`. Use raw `ko_type` parameter (already available as function arg at line 75). | `analyzers/query_builder.py` | → T15   | —        | ~2 lines changed. |

## Phase 5: Tests

| ID  | Task                                                                                                                                                                                                                 | File(s)                       | Depends | Parallel     | Notes             |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ------- | ------------ | ----------------- |
| T18 | Delete entire body of `tests/test_tsumego_frame.py`. Keep file + imports. Write new test infrastructure: helper factories (`_make_corner_tl`, `_make_corner_br`, `_make_edge`, `_make_center`, `_make_ko_position`). | `tests/test_tsumego_frame.py` | → T15   | —            | Clean test slate. |
| T19 | Write `TestGuessAttacker` — TL corner, BR corner, center, explicit override.                                                                                                                                         | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC1               |
| T20 | Write `TestNormalizeTL` + `TestDenormalize` — all 4 corners, roundtrip identity.                                                                                                                                     | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC5               |
| T21 | Write `TestComputeRegions` + `TestDetectEdgeSides` — bbox, margin, edge detection, defense_area formula.                                                                                                             | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC4               |
| T22 | Write `TestFillTerritory` — density 65-75%, count balance, no stones in puzzle region.                                                                                                                               | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC2               |
| T23 | Write `TestPlaceBorder` — non-edge sides only, all attacker color.                                                                                                                                                   | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC3, AC4          |
| T24 | Write `TestPlaceKoThreats` — placed when ko_type != "none", not placed when "none", no overlap.                                                                                                                      | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC6               |
| T25 | Write `TestApplyTsumegoFrame` — full pipeline, original stones preserved, player_to_move preserved, substantial stones added. Parameterized across 9/13/19 board sizes.                                              | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC9               |
| T26 | Write `TestRemoveTsumegoFrame` — roundtrip preservation.                                                                                                                                                             | `tests/test_tsumego_frame.py` | → T18   | [P]          | MHC-4             |
| T27 | Write `TestOffenceToWin` — different values produce different territory splits.                                                                                                                                      | `tests/test_tsumego_frame.py` | → T18   | [P]          | AC7               |
| T28 | Write integration test `TestQueryBuilderKoType` — `prepare_tsumego_query()` with `ko_type="direct"` includes ko threats.                                                                                             | `tests/test_query_builder.py` | → T17   | —            | AC8               |
| T29 | Write integration test `TestQueryBuilderBackwardCompat` — `prepare_tsumego_query()` without `ko_type` works as before.                                                                                               | `tests/test_query_builder.py` | → T17   | [P] with T28 | MHC-1             |

## Phase 6: Validation & Documentation

| ID  | Task                                                                                                                                           | File(s)                       | Depends   | Parallel     | Notes                                                                                |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | --------- | ------------ | ------------------------------------------------------------------------------------ |
| T30 | Run full test suite: `pytest tests/test_tsumego_frame.py tests/test_query_builder.py -v`                                                       | —                             | → T19-T29 | —            | AC9: all tests pass.                                                                 |
| T31 | _(Recommended, MHC-5)_ Create regression comparison script: run V1 vs V2 frame on ≥5 sample SGFs, document density/attacker-color differences. | `tests/` or standalone script | → T15     | [P] with T30 | Inline V1 logic for comparison (do NOT use git stash — forbidden per project rules). |
| T32 | Verify `remove_tsumego_frame` is preserved and tested (MHC-4 gate).                                                                            | —                             | → T26     | [P] with T30 | Checklist item.                                                                      |
| T33 | Add MIT attribution header to `tsumego_frame.py` (KaTrain SHA + ghostban repo URL).                                                            | `analyzers/tsumego_frame.py`  | → T1      | [P]          | DOC-3.                                                                               |

## Phase 7: Legacy Cleanup

| ID  | Task                                                                                                               | File(s)                                     | Depends | Parallel     | Notes           |
| --- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------- | ------- | ------------ | --------------- |
| T34 | Verify no other files import V1-specific internals (`_PUZZLE_MARGIN`, `_add_stone`, etc.). Grep for removed names. | All files in `tools/puzzle-enrichment-lab/` | → T30   | —            | No BC decision. |
| T35 | Remove any V1-specific test fixtures or helpers that are no longer relevant.                                       | `tests/test_tsumego_frame.py`               | → T30   | [P] with T34 | Clean up.       |

---

## Dependency Graph (simplified)

```
T1 (clean slate)
├── T2, T3, T4, T5 [P] (data types)
│   └── T6 (guess_attacker)
│       ├── T7, T8 [P] (normalize/denormalize)
│       ├── T9 (detect edges)
│       │   └── T10 (compute regions)
│       │       ├── T11 (fill territory)
│       │       ├── T12 [P] (place border)
│       │       └── T13 [P] (place ko threats)
│       │           └── T14 (build_frame orchestrator)
│       │               └── T15 (apply_tsumego_frame entry)
│       │                   ├── T16 [P] (remove_tsumego_frame)
│       │                   ├── T17 (query_builder update)
│       │                   └── T18 (test infrastructure)
│       │                       ├── T19-T29 [P] (unit + integration tests)
│       │                       │   └── T30 (full test run)
│       │                       └── T31 [P] (regression comparison)
├── T33 [P] (attribution header)
└── T34, T35 (legacy cleanup, after T30)
```

## Summary

| Metric              | Value                                                               |
| ------------------- | ------------------------------------------------------------------- |
| Total tasks         | 35                                                                  |
| Files modified      | 3 (`tsumego_frame.py`, `query_builder.py`, `test_tsumego_frame.py`) |
| Files created       | 0                                                                   |
| Files deleted       | 0 (content replaced, not file deleted)                              |
| Estimated new lines | ~240-300 (tsumego_frame.py) + ~300-400 (tests) + ~2 (query_builder) |
| Parallel groups     | 6 groups of [P] tasks                                               |
| Critical path       | T1 → T2 → T6 → T10 → T11 → T14 → T15 → T17 → T18 → T30              |
