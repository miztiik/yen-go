# Tasks: Tsumego Frame Flood-Fill Rewrite (OPT-3)

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Selected Option**: OPT-3 — Full Rewrite + Validation Hardening
**Last Updated**: 2026-03-12

---

## Dependency Graph

```
T1 ──→ T3 ──→ T5 ──→ T7 ──→ T9 ──→ T11 ──→ T12 ──→ T13
T2 ─┘  T4 ─┘  T6 ─┘  T8 ─┘  T10 ─┘
```

T1+T2 parallel → T3+T4 parallel → T5+T6 parallel → T7+T8 parallel → T9+T10 parallel → T11 → T12 → T13

---

## Task Checklist

### Phase 1: Data Model + Normalization

- [ ] **T1** — Add `swap_xy` to `NormalizedPosition` dataclass [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (lines 60-66)
  - Add `swap_xy: bool` field to `NormalizedPosition` frozen dataclass
  - Default `False` for backward compat during implementation
  - **RC-4**: Also update `build_frame()` line 798: change `normalized=norm.flip_x or norm.flip_y` to `normalized=norm.flip_x or norm.flip_y or norm.swap_xy`
  - AC: Field exists, `NormalizedPosition(swap_xy=True)` constructs without error, `FrameResult.normalized` reflects swap
  - MH: RC-2, RC-4

- [ ] **T2** — Update `normalize_to_tl()` with axis-swap logic [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (lines 215-260)
  - After flip computation, detect edge puzzle: if `min(x_coords) > min(y_coords)` after flip → swap x↔y
  - Return `NormalizedPosition` with `swap_xy=True` when swap applied
  - AC: Edge puzzle normalized to corner position. `swap_xy` field correct.
  - MH: G5, contributes to MH-1

- [ ] **T3** — Update `denormalize()` to reverse axis-swap
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (lines 262-280)
  - If `norm.swap_xy`: swap x↔y for all stones BEFORE applying flip reversal
  - Swap ordering: undo swap first, then undo flips (reverse of normalize order)
  - AC: `denormalize(normalize(pos)) == pos` for all position types
  - MH: MH-1, G5
  - Depends: T1, T2

- [ ] **T4** — Write normalize/denormalize round-trip tests [P]
  - File: `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`
  - Add test cases: TL corner (no swap), BR corner (flip, no swap), left-edge (swap), right-edge (swap+flip), top-edge (no swap or swap), center (may swap)
  - Each test: `assert _coord_set(denormalize(normalize(pos)).stones) == _coord_set(pos.stones)`
  - AC: All round-trip tests pass. swap_xy path explicitly tested.
  - MH: MH-1
  - Depends: T1, T2

### Phase 2: Score-Neutral Territory + API Cleanup

- [ ] **T5** — Remove `offence_to_win` from `FrameConfig` and `compute_regions()` [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`
  - Delete `offence_to_win: int = 10` from `FrameConfig` dataclass
  - Replace territory formula in `compute_regions()`:
    ```python
    defense_area = max(0, frameable // 2)
    offense_area = max(0, frameable - defense_area)
    ```
  - Delete `_REF_AREA`, `scaled_otw` scaling logic
  - AC: `FrameConfig()` constructs without `offence_to_win`. `compute_regions()` returns 50/50 split (±1).
  - MH: MH-5, G3

- [ ] **T6** — Remove `offence_to_win` from `apply_tsumego_frame()` signature [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (lines 806-850)
  - Delete `offence_to_win: int = 10` parameter
  - Delete `offence_to_win=offence_to_win` from `FrameConfig()` construction
  - AC: `apply_tsumego_frame(pos)` works. Passing `offence_to_win` raises TypeError.
  - MH: MH-5
  - Depends: T5

### Phase 3: BFS Flood-Fill

- [ ] **T7** — Implement `_choose_flood_seeds()` and `_bfs_fill()` helper
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`
  - Add `_choose_flood_seeds(regions, board_size) → (defender_seed, attacker_far_seed)`
    - After normalize-to-TL: defender = `(bs-1, 0)`, attacker = `(bs-1, bs-1)`
  - Add `_bfs_fill(seed, frameable, quota, color, occupied, puzzle_coords, defender_color, bs) → list[Stone]`
    - BFS using `collections.deque`
    - Apply legality guards at each placement (reuse from `liberty.py`)
    - Track skip_stats counters
  - AC: `_bfs_fill` produces connected stones from seed. Legality guards fire correctly.
  - MH: G1, G2, MH-4
  - Depends: T3, T5

- [ ] **T8** — Replace `fill_territory()` with BFS flood-fill [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (lines 354-440)
  - Rewrite `fill_territory()` body:
    1. Compute frameable cells
    2. Call `_choose_flood_seeds()`
    3. BFS defender fill from defender_seed (quota = defense_area)
    4. BFS attacker fill from attacker_seeds (border coords + far corner)
    5. Multi-seed fallback: scan unreached frameable cells, BFS from secondary seeds if >5% unreached
    6. Return (stones, skip_stats) — same interface
  - Delete `_choose_scan_order()` function entirely
  - Update `fill_territory()` signature: add `border_coords` parameter
  - AC: `fill_territory()` returns connected stones. `_choose_scan_order` deleted.
  - MH: G1, G2, G6
  - Depends: T7

### Phase 4: Validation + Integration

- [ ] **T9** — Implement `validate_frame()` function
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`
  - Add `validate_frame(position, original_position, attacker_color, puzzle_stone_coords) → (bool, dict)`
  - Check 1: BFS connectivity for defender frame stones (component count must == 1) (MH-2)
  - Check 2: BFS connectivity for attacker frame stones + border (component count must == 1)
  - Check 3: No dead frame stone — each has ≥1 same-color orthogonal neighbor within bounds (MH-3)
  - Return `(is_valid, {"defender_components": n, "attacker_components": n, "dead_stones": n})`
  - AC: `validate_frame` correctly identifies disconnected and dead stone cases
  - MH: G4, MH-2, MH-3

- [ ] **T10** — Wire `validate_frame()` into `build_frame()` [P]
  - File: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` (build_frame, ~lines 682-790)
  - After framed position assembly, before denormalize:
    1. Call `validate_frame(framed_norm, norm.position, attacker, puzzle_stone_coords)`
    2. If invalid: log WARNING with diagnostics dict, log failed frame SGF (`framed_norm.to_sgf()`), return `FrameResult(position=original, frame_stones_added=0, ...)`
  - Update `build_frame()` to pass border_coords to `fill_territory()`
  - AC: Validation integrated. Invalid frames return original position.
  - MH: MH-6, G4
  - Depends: T8, T9

### Phase 5: Test Updates

- [ ] **T11** — Update existing tests + add connectivity tests
  - File: `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`
  - **Update**: `TestFillTerritory` density thresholds to match new fill
  - **Update**: `TestOffenceToWin` — remove or replace with score-neutral tests
  - **Update**: `TestStoneCountBalanced` — adjust balance expectations for 50/50 split
  - **Update**: `TestLeftRightEdgePuzzles` — remove `_choose_scan_order` references
  - **Update**: `TestNoSurroundedFrameStones` — tighten threshold (BFS should have ~0 surrounded)
  - **Add**: `TestBFSConnectivity` — verify defender/attacker fill are each single component
  - **Add**: `TestNoDead FrameStones` — verify all frame stones have ≥1 same-color neighbor
  - **Add**: `TestValidationFailureFallback` — force invalid frame, verify original position returned + warning logged
  - **Add**: `TestScoreNeutralSplit` — verify defense_area ≈ offense_area (±1)
  - **Add**: `TestNormalizeSwapEdgePuzzle` — verify edge puzzle normalized to corner with swap_xy=True
  - AC: All tests pass green. Both density AND connectivity invariants present.
  - MH: MH-1 (round-trip), MH-2 (connectivity), MH-3 (dead stones), MH-6 (fallback)
  - Depends: T3, T4, T8, T10

### Phase 6: Documentation + Cleanup

- [ ] **T12** — Update `docs/concepts/tsumego-frame.md`
  - Replace "Zone-Based Fill vs Checkerboard" section with "BFS Flood-Fill"
  - Update "Algorithm Overview" pipeline diagram
  - Update "Key Parameters" table — remove offence_to_win
  - Add "Post-Fill Validation" subsection under "Legality Validation"
  - Update visual example to show BFS-filled frame
  - AC: Docs reflect new algorithm. No references to offence_to_win or linear scan.
  - Depends: T11

- [ ] **T13** — Final grep verification + cleanup
  - Grep for `offence_to_win` — must return 0 results in `tsumego_frame.py`
  - Grep for `_choose_scan_order` — must return 0 results
  - Grep for `defense_area.*offence` — must return 0 results
  - Verify `_compute_synthetic_komi` still works (if referenced)
  - Run full test suite: `pytest tests/test_tsumego_frame.py -v`
  - AC: Clean codebase. All tests green.
  - Depends: T12

---

## Parallel Markers

| Phase | Tasks | Parallelizable |
|-------|-------|---------------|
| 1 | T1, T2, T4 | T1 + T2 [P], T4 after T1+T2 (T3 depends on both) |
| 2 | T5, T6 | T5 + T6 [P] (T6 depends on T5 for FrameConfig) |
| 3 | T7, T8 | T7 first, T8 [P] depends on T7 |
| 4 | T9, T10 | T9 + T10 [P] (T10 depends on T9) |
| 5 | T11 | Sequential — depends on T3, T4, T8, T10 |
| 6 | T12, T13 | T12 then T13 (sequential) |

---

## File Impact Summary

| File | Tasks | Change Type |
|------|-------|-------------|
| `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` | T1-T3, T5-T10 | Major rewrite (~120 lines changed/added) |
| `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py` | T4, T11 | Update + additions (~80 lines) |
| `docs/concepts/tsumego-frame.md` | T12 | Documentation update |

---

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture and algorithm design
> - [Charter](./00-charter.md) — Goals G1-G6, acceptance criteria AC1-AC10
> - [Governance](./70-governance-decisions.md) — MH-1 through MH-6
