# Plan: Tsumego Frame Flood-Fill Rewrite (OPT-3)

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Selected Option**: OPT-3 — Full Rewrite + Validation Hardening
**Last Updated**: 2026-03-12

---

## 1. Architecture Overview

### Current Flow
```
Position → normalize_to_tl(flip only) → compute_regions(offence_to_win) 
         → place_border → place_ko_threats → fill_territory(linear scan) 
         → denormalize → FrameResult
```

### New Flow (OPT-3)
```
Position → normalize_to_tl(flip + axis-swap) → compute_regions(score-neutral)
         → place_border → place_ko_threats 
         → fill_territory_bfs(BFS flood-fill from seeds)
         → validate_frame(connectivity + dead-stone check)
         → denormalize → FrameResult
```

### Key Differences
1. `normalize_to_tl()` adds axis-swap → puzzle always in corner
2. `compute_regions()` uses 50/50 territory split (no offence_to_win)
3. `fill_territory()` replaced with BFS flood-fill from seed points
4. `validate_frame()` added as post-fill assertion
5. `_choose_scan_order()` deleted, `_choose_flood_seeds()` added
6. `offence_to_win` removed from `FrameConfig`, `compute_regions`, `apply_tsumego_frame`

---

## 2. Data Model Changes

### NormalizedPosition (RC-2)
```python
@dataclass(frozen=True)
class NormalizedPosition:
    """Position normalized to top-left corner with transformation metadata."""
    position: Position
    flip_x: bool
    flip_y: bool
    swap_xy: bool  # NEW: axis swap for edge puzzles
    original_board_size: int
```

### FrameConfig
```python
@dataclass(frozen=True)
class FrameConfig:
    """Configuration for frame generation — all tunables."""
    margin: int = 2
    # offence_to_win: REMOVED (MH-5)
    ko_type: str = "none"
    board_size: int = 19
    synthetic_komi: bool = False
```

### FrameResult (unchanged fields, new validation)
- `fill_density` preserved (AC10)
- All skip counters preserved
- Validation failure → `frame_stones_added=0`, original position returned (MH-6)

---

## 3. Algorithm Design

### 3.1 Normalize with Axis-Swap (G5)

After computing centroid flips (existing logic), check if puzzle stones span a wider range on one axis than the other. If `min_row < min_col` (puzzle is more horizontal than vertical), swap x↔y to move it into a corner.

```
normalize_to_tl(position):
  1. Compute centroid → flip_x, flip_y (existing)
  2. After flip, compute stone bounding box
  3. If min(x_coords) > min(y_coords):  # puzzle on edge, not corner
       swap x↔y for all stones
       swap_xy = True
  4. Return NormalizedPosition(position, flip_x, flip_y, swap_xy, bs)
```

Round-trip property: `denormalize(normalize(pos)) == pos` (MH-1)

### 3.2 Score-Neutral Territory Split (G3, MH-5)

Replace `offence_to_win` formula in `compute_regions()`:
```python
frameable = total_area - len(puzzle_region)
defense_area = frameable // 2
offense_area = frameable - defense_area
```

Exact 50/50 split (±1 cell for odd frameable count). No scaling, no bias.

### 3.3 BFS Flood-Fill (G1, G2)

Replace `fill_territory()` linear scan with:

```python
def fill_territory_bfs(position, regions, attacker_color, 
                        puzzle_stone_coords, border_coords):
    """BFS flood-fill from seed points.
    
    1. Compute frameable cells = all board cells - puzzle_region - occupied
    2. _choose_flood_seeds(regions, board_size) → defender_seed, attacker_seeds
    3. BFS from defender_seed: fill up to defense_area cells with defender color
       - Each placement applies legality guards (eye, suicide, puzzle-protect)
       - BFS grows outward from seed = guaranteed connected component
    4. BFS from attacker_seeds (border cells + far corner): fill remaining cells
    5. Multi-seed fallback: scan unreached frameable cells, add secondary seeds
    6. Return (stones, skip_stats)
    """
```

**Seed Selection (`_choose_flood_seeds`):**
After normalize-to-TL-corner:
- Defender seed: `(bs-1, 0)` — top-right corner (farthest from TL puzzle)
- Attacker seeds: border wall cell coords + `(bs-1, bs-1)` — grow from border outward

**BFS Implementation:**
```python
from collections import deque

def _bfs_fill(seed, frameable, quota, color, occupied, 
              puzzle_stone_coords, defender_color, board_size):
    queue = deque([seed])
    visited = {seed}
    stones = []
    while queue and len(stones) < quota:
        x, y = queue.popleft()
        if (x, y) not in frameable or (x, y) in occupied:
            continue
        # Apply legality guards (MH-4)
        if is_eye((x, y), defender_color, occupied, board_size):
            continue
        test_occ = dict(occupied)
        test_occ[(x, y)] = color
        if count_group_liberties((x, y), color, test_occ, board_size) == 0:
            continue
        if puzzle_stone_coords and would_harm_puzzle_stones(
            (x, y), color, puzzle_stone_coords, occupied, board_size):
            continue
        stones.append(Stone(color=color, x=x, y=y))
        occupied[(x, y)] = color
        # Enqueue neighbors (4-directional)
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                neighbor = (nx, ny)
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
    return stones
```

### 3.4 Multi-Seed Fallback

After primary BFS, check for unreached frameable cells:
```python
unreached = frameable - placed_coords - occupied
if len(unreached) > 0.05 * len(frameable):  # >5% unreached
    # Add secondary seeds from unreached cells
    secondary_seed = next(iter(unreached))
    _bfs_fill(secondary_seed, ...)
```

### 3.5 Post-Fill Validation (G4, MH-2, MH-3, MH-6)

```python
def validate_frame(position, original_position, attacker_color, 
                   puzzle_stone_coords):
    """Validate frame correctness after assembly.
    
    Checks (all must pass):
    1. Defender connectivity: BFS from any defender frame stone reaches 
       ALL defender frame stones (MH-2: component count == 1)
    2. Attacker connectivity: BFS from any attacker frame stone reaches
       ALL attacker frame stones (including border)
    3. No dead stones: every frame stone has ≥1 same-color orthogonal 
       neighbor within board bounds (MH-3)
    
    Returns:
        (is_valid, diagnostics_dict)
    
    On failure:
        - Log WARNING with diagnostics
        - Log failed frame as SGF (position.to_sgf())
        - Caller returns original position (MH-6)
    """
```

---

## 4. Build Frame Orchestration Changes

Current order: `normalize → regions → border → ko → fill → denormalize`

New order: `normalize → regions → border → ko → fill_bfs → validate → denormalize`

Key change in `build_frame()`:
- Pass border stone coords to `fill_territory_bfs()` as attacker seeds
- After assembling framed position, call `validate_frame()`
- If validation fails, log warning + SGF dump, return `FrameResult(position=original, frame_stones_added=0)`

---

## 5. API Surface Changes

### Removed
- `FrameConfig.offence_to_win` field (MH-5)
- `apply_tsumego_frame(offence_to_win=...)` parameter (MH-5)
- `_choose_scan_order()` function
- `offence_to_win` scaling logic in `compute_regions()`

### Added
- `NormalizedPosition.swap_xy` field (RC-2)
- `_choose_flood_seeds(regions, board_size)` function
- `validate_frame(position, original, attacker, puzzle_coords)` function
- `fill_territory_bfs()` replaces `fill_territory()`

### Preserved (MH-4)
- All legality guards in `liberty.py` (eye, suicide, puzzle-protect)
- `player_to_move` inviolate rule
- `FrameResult` structure and `fill_density` metric
- `place_border()`, `place_ko_threats()` (unchanged)
- `remove_tsumego_frame()` (unchanged)
- `guess_attacker()` (unchanged)

---

## 6. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Axis-swap introduces coordinate bugs in denormalize | Medium | High | MH-1: denormalize round-trip test with swap_xy=True. Explicit test for each position type. |
| BFS cannot reach all frameable cells | Medium | Medium | Multi-seed fallback after primary BFS. Warning logged. |
| Calibration tests fail | High | Low | Expected and planned — update thresholds to match new fill |
| Validation too strict, rejects valid frames | Low | Medium | MH-6: fallback = original position (safe). Monitor rejection rate in logs. |
| Score-neutral fill changes KataGo evaluation | Low | Medium | Post-change calibration with golden puzzles. Compare against prior results. |

---

## 7. Documentation Plan

| doc_id | File | Action | Change Description |
|--------|------|--------|--------------------|
| DOC-1 | `docs/concepts/tsumego-frame.md` | Update | Replace "Zone-Based Fill" section with "BFS Flood-Fill". Update algorithm overview, visual example, key parameters (remove offence_to_win). Update "Known Limitations" section. |
| DOC-2 | `docs/concepts/tsumego-frame.md` | Update | Update "Legality Validation (V3)" section with validation assertions (G4). Add "Post-Fill Validation" subsection. |
| DOC-3 | `docs/concepts/tsumego-frame.md` | Update | Update "Key Parameters" table — remove offence_to_win row, note score-neutral split. |

### Cross-references
- [Architecture: KataGo Enrichment](../../docs/architecture/tools/katago-enrichment.md) — D33 preserved, no changes needed
- [How-To: Enrichment Lab](../../docs/how-to/tools/katago-enrichment-lab.md) — May need parameter update if offence_to_win was documented

---

## 8. Must-Hold Constraints (from Governance)

| ID | Constraint | Verification |
|----|-----------|-------------|
| MH-1 | `denormalize(normalize(pos)) == pos` round-trip with `swap_xy=True` | Unit test: edge puzzle normalize→denormalize identity |
| MH-2 | Disconnected = BFS component count > 1 | `validate_frame()` implementation |
| MH-3 | Dead stone = zero same-color orthogonal neighbors | `validate_frame()` implementation |
| MH-4 | Legality guards (F1/F2/F8/F10/F20) preserved unchanged | No modifications to `liberty.py` |
| MH-5 | `offence_to_win` fully deleted from FrameConfig, apply_tsumego_frame, compute_regions | Code review + grep verification |
| MH-6 | Validation failure returns original position (no frame) | Integration test: forced validation failure |

---

> **See also**:
>
> - [Charter](./00-charter.md) — Goals G1-G6, constraints C1-C7
> - [Options](./25-options.md) — OPT-3 selected
> - [Research](../20260312-research-tsumego-frame-flood-fill/15-research.md) — R-20 through R-24
> - [Governance](./70-governance-decisions.md) — MH-1 through MH-6
