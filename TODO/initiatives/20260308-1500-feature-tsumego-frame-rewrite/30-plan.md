# Plan: Tsumego Frame Rewrite (OPT-2: Merged KaTrain + ghostban)

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Selected Option**: OPT-2 (GOV-OPTIONS-APPROVED, unanimous)  
> **Last Updated**: 2026-03-08

---

## 1. Architecture Overview

### 1.1 Module Design

Single file `analyzers/tsumego_frame.py` with clean function decomposition. Each function takes and returns a typed payload (dataclass). The pipeline is:

```
Position → FrameConfig → [guess_attacker] → [normalize_to_tl] → [compute_regions]
         → [fill_territory] → [place_border] → [place_ko_threats] → [denormalize] → Position
```

### 1.2 Data Types (all in `tsumego_frame.py`)

```python
@dataclass(frozen=True)
class FrameConfig:
    """Configuration for frame generation — all tunables."""
    margin: int = 2                  # Empty margin around puzzle stones
    offence_to_win: int = 10         # Territory advantage for attacker (ghostban=10, KaTrain=5)
    ko_type: str = "none"            # "none" | "direct" | "approach" — enables ko threats
    board_size: int = 19             # For defense_area calculation

@dataclass(frozen=True)
class NormalizedPosition:
    """Position normalized to top-left corner with transformation metadata."""
    position: Position               # TL-normalized position
    flip_x: bool                     # Was flipped horizontally
    flip_y: bool                     # Was flipped vertically
    original_board_size: int

@dataclass(frozen=True)
class FrameRegions:
    """Computed regions for frame placement."""
    puzzle_bbox: tuple[int, int, int, int]  # (min_x, min_y, max_x, max_y)
    puzzle_region: set[tuple[int, int]]      # Bbox + margin (no-place zone)
    occupied: set[tuple[int, int]]           # Existing stones
    board_edge_sides: set[str]               # {"top", "left"} etc. — sides where puzzle touches board edge
    defense_area: int                        # Number of defense stones to place
    offense_area: int                        # Number of offense stones to place

@dataclass
class FrameResult:
    """Result of frame generation — new stones + metadata."""
    position: Position               # Framed position
    frame_stones_added: int          # How many stones the frame added
    attacker_color: Color            # Which color is the attacker
    normalized: bool                 # Whether normalization was applied
```

### 1.3 Function Decomposition

| Function                                                                           | Input                                     | Output             | Lines | Source                                                     |
| ---------------------------------------------------------------------------------- | ----------------------------------------- | ------------------ | ----- | ---------------------------------------------------------- |
| `apply_tsumego_frame(position, *, margin, offense_color, ko_type, offence_to_win)` | Position + optional params                | Position           | ~20   | Entry point (facade)                                       |
| `build_frame(position, config)`                                                    | Position, FrameConfig                     | FrameResult        | ~25   | Orchestrator                                               |
| `guess_attacker(position)`                                                         | Position                                  | Color              | ~25   | KaTrain `guess_black_to_attack()`                          |
| `normalize_to_tl(position)`                                                        | Position                                  | NormalizedPosition | ~20   | KaTrain `snap()` + `flip_stones()`                         |
| `denormalize(position, normalized)`                                                | Position, NormalizedPosition              | Position           | ~20   | Reverse of normalize                                       |
| `compute_regions(position, config)`                                                | Position, FrameConfig                     | FrameRegions       | ~30   | KaTrain fill logic + ghostban bbox formula                 |
| `detect_board_edge_sides(bbox, board_size)`                                        | tuple, int                                | set[str]           | ~10   | ghostban border logic                                      |
| `fill_territory(position, regions, attacker)`                                      | Position, FrameRegions, Color             | list[Stone]        | ~30   | KaTrain count-based half/half + ghostban territory formula |
| `place_border(position, regions, attacker)`                                        | Position, FrameRegions, Color             | list[Stone]        | ~25   | ghostban: border only on non-edge sides                    |
| `place_ko_threats(position, regions, attacker, ko_type, player_to_move)`           | Position, FrameRegions, Color, str, Color | list[Stone]        | ~30   | KaTrain `put_ko_threat()`                                  |
| `remove_tsumego_frame(framed, original)`                                           | Position, Position                        | Position           | ~3    | Preserved (MHC-4)                                          |

**Total estimated**: ~240-300 lines (including dataclasses, docstrings, imports)

### 1.4 Algorithm Detail

**Step 1: Attacker Inference** (`guess_attacker`)

- KaTrain's edge-proximity heuristic: compute average distance of each color's stones from the nearest board edge
- Color closer to edges is the DEFENDER (living in the corner/edge)
- Opposite color is the ATTACKER (surrounding from outside)
- Tie-break: Black is attacker (convention)

**Step 2: Normalize to TL** (`normalize_to_tl`)

- Find bounding box center of all stones
- If center is in right half → flip X
- If center is in bottom half → flip Y
- Record transformations for denormalization

**Step 3: Compute Regions** (`compute_regions`)

- Bounding box of all stones + margin = puzzle region (no-place zone)
- Detect which sides of bbox touch the board edge (distance ≤ margin)
- ghostban formula: `defense_area = floor((board_size² - bbox_area) / 2) - komi - offence_to_win`
- `offense_area = total_frameable - defense_area`

**Step 4: Fill Territory** (`fill_territory`)

- KaTrain's count-based approach: iterate frameable cells in order
- Near puzzle region seam: prefer dense placement (no checkerboard holes)
- Far from puzzle region: checkerboard `(i+j)%2==0` holes for liberty safety
- Alternate offense/defense stones count-based (half/half adjusted by `offense_area`/`defense_area`)

**Step 5: Place Border** (`place_border`)

- ghostban approach: border ring of attacker-colored stones
- Only on sides where puzzle region does NOT touch the board edge
- TL corner puzzle → border on right side + bottom side only

**Step 6: Ko Threats** (`place_ko_threats`, optional)

- KaTrain's fixed patterns: two 4-stone threat groups placed near (but not in) puzzle region
- Offense ko threat vs defense ko threat selected by `for_offense_p = xor(ko_p, xor(black_to_attack_p, black_to_play_p))`
- Gated on `ko_type != "none"`

**Step 7: Denormalize** (`denormalize`)

- Reverse the flip_x/flip_y from Step 2 on all frame stones
- Return framed position in original orientation

### 1.5 Caller Changes (`query_builder.py`)

Current call site (line 101):

```python
framed_position = apply_tsumego_frame(tsumego_position, margin=puzzle_region_margin)
```

New call site:

```python
framed_position = apply_tsumego_frame(
    tsumego_position,
    margin=puzzle_region_margin,
    ko_type=ko_type,
)
```

This is a minimal change — `ko_type` is already available as a parameter of `prepare_tsumego_query()` (line 75). Note: `ko_type_key` is computed at line ~104 (AFTER the frame call), so we pass the raw `ko_type` parameter directly. The new `apply_tsumego_frame` validates internally via `FrameConfig`. The old call signature still works since `ko_type` defaults to `"none"` (MHC-1).

---

## 2. Risks and Mitigations

| Risk                                                                     | Likelihood | Impact | Mitigation                                                                                                                          |
| ------------------------------------------------------------------------ | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Edge-proximity heuristic misclassifies attacker for center-board puzzles | Low        | Medium | AC1 test covers this. Fallback: if no stones near edge, use `player_to_move` opponent as attacker (current V1 behavior as fallback) |
| `offence_to_win=10` too aggressive for some board sizes                  | Low        | Low    | Configurable (MHC-2). Can tune per-run via `FrameConfig`                                                                            |
| normalize/denormalize introduces off-by-one or coordinate error          | Low        | High   | Unit test: normalize→frame→denormalize roundtrip preserves puzzle stones exactly. Test all 4 corner positions.                      |
| Ko threat placement collides with puzzle stones                          | Low        | Medium | Check placement candidates against occupied set before placing                                                                      |
| `query_builder.py` integration regression                                | Very Low   | Medium | AC8 integration test. `ko_type` already in scope at call site.                                                                      |

---

## 3. Test Strategy

### 3.1 Unit Tests (per function)

| Test Class               | Target Function             | Key Assertions                                                                                                    |
| ------------------------ | --------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `TestGuessAttacker`      | `guess_attacker()`          | TL corner → Black defends, White attacks. BR corner → same. Center → fallback. Explicit `offense_color` override. |
| `TestNormalizeTL`        | `normalize_to_tl()`         | TL puzzle → no flip. BR puzzle → flip_x + flip_y. TR → flip_x only. BL → flip_y only.                             |
| `TestDenormalize`        | `denormalize()`             | Roundtrip: normalize→denormalize = identity for all 4 corners.                                                    |
| `TestComputeRegions`     | `compute_regions()`         | Correct bbox, margin, edge detection. defense_area formula matches ghostban.                                      |
| `TestDetectEdgeSides`    | `detect_board_edge_sides()` | TL corner → {"top", "left"}. Center → empty. Edge → {"top"}.                                                      |
| `TestFillTerritory`      | `fill_territory()`          | Density ~65-75%. Count-based balance. No stones in puzzle region.                                                 |
| `TestPlaceBorder`        | `place_border()`            | Border only on non-edge sides. All border stones are attacker color.                                              |
| `TestPlaceKoThreats`     | `place_ko_threats()`        | Ko threats placed when ko_type != "none". Not placed when "none". Patterns don't overlap puzzle.                  |
| `TestApplyTsumegoFrame`  | `apply_tsumego_frame()`     | Full pipeline: original stones preserved, player_to_move preserved, substantial stones added.                     |
| `TestRemoveTsumegoFrame` | `remove_tsumego_frame()`    | Roundtrip: framed→removed = original.                                                                             |

### 3.2 Integration Tests

| Test                             | Target                                            | Key Assertions                                                  |
| -------------------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| `TestQueryBuilderKoType`         | `prepare_tsumego_query()` with `ko_type="direct"` | Frame includes ko threats. Region moves computed. Bundle valid. |
| `TestQueryBuilderBackwardCompat` | `prepare_tsumego_query()` without ko_type         | Works identically to current behavior (no ko threats).          |

### 3.3 Board Size Coverage

All tests run across 9×9, 13×13, and 19×19 (parameterized).

### 3.4 Regression Comparison (MHC-5, recommended)

A separate test or script that:

1. Takes ≥5 sample SGF puzzles (TL corner, BR corner, edge, center, ko)
2. Runs V1 frame + V2 frame
3. Asserts V2 produces higher fill density and correct attacker color
4. Documents results in test output

---

## 4. Documentation Plan

| ID    | Action                                        | File                                       | Why                                   |
| ----- | --------------------------------------------- | ------------------------------------------ | ------------------------------------- |
| DOC-1 | Update enrichment lab architecture notes      | `docs/architecture/` (if exists for tools) | New algorithm description             |
| DOC-2 | Update module docstring in `tsumego_frame.py` | `analyzers/tsumego_frame.py`               | Algorithm references, MIT attribution |
| DOC-3 | Add attribution comment                       | `analyzers/tsumego_frame.py` header        | KaTrain MIT + ghostban MIT credit     |

### Files to Update

- `analyzers/tsumego_frame.py` — complete rewrite (DOC-2, DOC-3)
- `analyzers/query_builder.py` — add `ko_type` to `apply_tsumego_frame()` call
- `tests/test_tsumego_frame.py` — complete rewrite

### Files to Create

- None (single-file replacement)

### Cross-References

- Research: `TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/15-research.md`
- Charter: `TODO/initiatives/20260308-1500-feature-tsumego-frame-rewrite/00-charter.md`

---

## 5. Rollback Plan

If the V2 frame produces worse KataGo evaluations:

1. Git revert the commit (single commit, 3 files)
2. V1 code is restored from git history
3. No downstream data corruption — frame is ephemeral (applied per-query, never persisted)

> **See also**:
>
> - [Options: OPT-2 details](25-options.md) — Full algorithm comparison
> - [Charter: Acceptance criteria](00-charter.md) — AC1-AC11
> - [Research: Three-way comparison](../2026-03-08-research-goproblems-tsumego-frame/15-research.md) — Verbatim source analysis
