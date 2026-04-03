# Plan: GP Frame Swap (OPT-1 — Thin Adapter Module)

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Selected Option**: OPT-1 (Thin Adapter Module)
> **Last Updated**: 2026-03-13

---

## 1. Architecture Overview

```
analyzers/
  frame_utils.py        ← NEW: compute_regions(), FrameRegions (shared geometry)
  frame_adapter.py      ← NEW: apply_frame(), remove_frame(), validate_frame()
  tsumego_frame_gp.py   ← MODIFY: add GPFrameConfig dataclass (GP-internal)
  query_builder.py      ← MODIFY: import from frame_adapter instead of tsumego_frame
  enrich_single.py      ← MODIFY: import from frame_utils instead of tsumego_frame
  liberty.py            ← MODIFY: remove dead TYPE_CHECKING import
  tsumego_frame.py      ← UNTOUCHED (archived, still importable for rollback)

tests/
  test_frame_utils.py   ← NEW
  test_frame_adapter.py ← NEW
  test_tsumego_frame.py ← MODIFY: add pytest.mark.skip
  test_frames_gp.py     ← MODIFY: fix broken import path
```

### Call Flow (After Change)

```
query_builder.py
  └─ from analyzers.frame_adapter import apply_frame
       └─ apply_frame(position, margin=..., ko=...) 
            └─ apply_gp_frame(position, margin=..., ko=...) → GPFrameResult
            └─ returns FrameResult(position=gp_result.position, ...)

enrich_single.py
  └─ from analyzers.frame_utils import compute_regions, FrameRegions
       └─ compute_regions(position, margin=2, board_size=19) → FrameRegions
            └─ fr.puzzle_region → frozenset[tuple[int,int]]  (Benson/interior gates)
```

---

## 2. Type Definitions (RC-1 / RC-2 Resolution)

### `frame_utils.py` — Shared Types

```python
@dataclass(frozen=True)
class FrameRegions:
    """Computed regions for frame placement — shared geometry."""
    puzzle_bbox: tuple[int, int, int, int]       # (min_x, min_y, max_x, max_y)
    puzzle_region: frozenset[tuple[int, int]]     # RC-2: MUST be frozenset (C4)
    occupied: frozenset[tuple[int, int]]
    board_edge_sides: frozenset[str]
    # NOTE: defense_area/offense_area EXCLUDED per Q6 governance decision

def compute_regions(
    position: Position,
    *,
    margin: int = 2,
    board_size: int | None = None,
) -> FrameRegions:
    """Compute puzzle bbox and region — pure geometry, no frame algorithm dependency.
    
    If board_size is None, uses position.board_size.
    """
```

**RC-1 resolution**: There is NO shared `FrameConfig` dataclass. The rationale:
- `compute_regions()` only needs `margin` and `board_size` — 2 plain args, not worth a dataclass
- GP has its own internal `GPFrameConfig` for its algorithm parameters (`margin`, `ko`, `komi`, `offence_to_win`)
- BFS has its own `FrameConfig` with BFS-specific fields (`ko_type` as str, `synthetic_komi`)
- A shared `FrameConfig` would be a lowest-common-denominator type that serves neither well
- The adapter's `apply_frame()` takes keyword args matching GP's parameters — clean, explicit

### `tsumego_frame_gp.py` — GP Internal Config (FrameConfig → GPFrameConfig)

```python
@dataclass(frozen=True)
class GPFrameConfig:
    """Configuration for GP frame generation — internal to GP module."""
    margin: int = 2
    komi: float = 0.0
    ko: bool = False
    offence_to_win: int = 5
```

This dataclass wraps the keyword arguments that `apply_gp_frame()` already accepts. It is used internally by `apply_gp_frame()` and is NOT part of the shared interface. Callers use the adapter.

### `frame_adapter.py` — Adapter Types

```python
@dataclass
class FrameResult:
    """Adapter result — same shape as BFS's FrameResult for consumer compatibility."""
    position: Position
    frame_stones_added: int
    attacker_color: Color

def apply_frame(
    position: Position,
    *,
    margin: int = 2,
    ko: bool = False,
    komi: float = 0.0,
    offence_to_win: int = 5,
) -> FrameResult:
    """Apply GP frame via adapter. Returns FrameResult for consumer compatibility."""

def remove_frame(
    framed_position: Position,
    original_position: Position,
) -> Position:
    """Remove frame — returns deep copy of original (same as BFS)."""
    return original_position.model_copy(deep=True)

def validate_frame(
    framed_position: Position,
    original_position: Position,
    attacker_color: Color,
    puzzle_stone_coords: frozenset[tuple[int, int]],
) -> tuple[bool, dict]:
    """Post-fill validation — same checks as BFS, algorithm-agnostic."""
```

---

## 3. File-by-File Change Map

### 3a. NEW: `analyzers/frame_utils.py` (~50-60 lines)

Extract from `tsumego_frame.py`:
- `FrameRegions` dataclass (without `defense_area`/`offense_area`)
- `compute_regions()` function (bbox calculation + puzzle_region computation)
- `detect_board_edge_sides()` helper (used by `compute_regions`)

Dependencies: Only `models.position` (Position, Stone, Color). Zero frame algorithm dependency.

### 3b. NEW: `analyzers/frame_adapter.py` (~100-120 lines)

Contains:
- `FrameResult` dataclass (consumer-compatible)
- `apply_frame()` — calls `apply_gp_frame()`, maps `GPFrameResult` → `FrameResult`
- `remove_frame()` — trivial one-liner (deep copy original)
- `validate_frame()` — extracted connectivity + dead stone checks (algorithm-agnostic geometry)

Dependencies: `tsumego_frame_gp.apply_gp_frame`, `models.position`. No BFS dependency.

### 3c. MODIFY: `analyzers/tsumego_frame_gp.py` (~15 lines added)

Add `GPFrameConfig` dataclass. Wire into `apply_gp_frame()` as optional alternative to keyword args.

### 3d. MODIFY: `analyzers/query_builder.py` (~3 lines changed)

```python
# Before:
from analyzers.tsumego_frame import apply_tsumego_frame
# After:
from analyzers.frame_adapter import apply_frame
```

Call site change:
```python
# Before:
framed_position = apply_tsumego_frame(tsumego_position, margin=..., ko_type=ko_type)
# After:
result = apply_frame(tsumego_position, margin=..., ko=(ko_type != "none"))
framed_position = result.position
```

Note: `ko_type` (str: "none"/"direct"/"approach") → `ko` (bool). The adapter does NOT need the distinction between direct/approach ko — the GP fill algorithm only cares whether ko material should be placed.

### 3e. MODIFY: `analyzers/enrich_single.py` (~4 lines changed, 2 callsites)

```python
# Before (line 331 and 606):
from analyzers.tsumego_frame import compute_regions, FrameConfig
_frame_cfg = FrameConfig(board_size=position.board_size, margin=config.analysis_defaults.puzzle_region_margin)
_frame_regions = compute_regions(position, _frame_cfg)

# After:
from analyzers.frame_utils import compute_regions
_frame_regions = compute_regions(position, margin=config.analysis_defaults.puzzle_region_margin)
```

### 3f. MODIFY: `analyzers/liberty.py` (~2 lines removed)

```python
# Remove:
if TYPE_CHECKING:
    from analyzers.tsumego_frame import FrameRegions
```

Also remove the `from typing import TYPE_CHECKING` import if nothing else uses it.

### 3g. MODIFY: `tests/test_tsumego_frame.py` (~1 line added)

```python
import pytest
pytestmark = pytest.mark.skip(reason="BFS frame archived — GP frame is active (20260313-1000-feature-gp-frame-swap)")
```

### 3h. MODIFY: `scripts/show_frame.py` (~15 lines changed)

Simplify the ASCII diagnostic script:
- Remove `--ko` CLI flag (GP doesn't need ko_type distinction)
- Remove `--color` CLI flag (GP uses `player_to_move` for attacker, no manual override)
- Rewire import: `tsumego_frame.apply_tsumego_frame` → `frame_adapter.apply_frame`
- Drop `Color` import (no longer needed without `--color`)
- Simplify call to `result = apply_frame(position, margin=args.margin)`
- Use `result.frame_stones_added` instead of counting stone difference

`scripts/probe_frame.py` is left as-is — already covered by `scripts/probe_frame_gp.py`.

### 3i. MODIFY: `tests/test_frames_gp.py` (~1 line fixed)

```python
# Before:
from analyzers.frames_gp import ...
# After:
from analyzers.tsumego_frame_gp import ...
```

### 3i. NEW: `tests/test_frame_utils.py` (~60-80 lines)

Tests for:
- `compute_regions()` — bbox computation, puzzle_region type is `frozenset[tuple[int,int]]`
- `FrameRegions` — frozen dataclass, fields correct, no `defense_area`
- Edge detection

### 3j. NEW: `tests/test_frame_adapter.py` (~80-100 lines)

Tests for:
- `apply_frame()` — returns `FrameResult`, position has frame stones, attacker_color set
- `remove_frame()` — returns original position
- `validate_frame()` — catches dead stones, allows multi-component
- `player_to_move` preservation (C2)
- Roundtrip: apply → validate → remove

---

## 4. Attacker Detection (Q7 → Governance-Resolved)

The adapter uses `player_to_move` directly (from GP's approach):
- GP already does: `black_to_play = position.player_to_move == Color.BLACK`
- The adapter just passes through `GPFrameResult.attacker_color`
- No need for `guess_attacker()` heuristic — our pipeline guarantees PL is set

---

## 5. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GP frame quality differs from BFS | Low | Medium | `validate_frame()` catches structural issues. BFS preserved for rollback (C5). |
| `ko_type` str→bool lossy conversion | Low | Low | GP doesn't distinguish direct/approach ko. Both produce ko material. Log the original `ko_type` for observability. |
| `compute_regions` extraction misses edge case | Low | Low | Tests verify type (`frozenset`), bbox accuracy, and board_edge_sides. Same algorithm, just moved. |
| `FrameConfig` naming confusion (BFS's vs GP's) | Low | Low | GP uses `GPFrameConfig` (distinct name). BFS's `FrameConfig` stays in BFS module (unused by active code). |

---

## 6. Documentation Plan

| doc_action | file | why |
|------|------|-----|
| Update | `docs/concepts/tsumego-frame.md` | Document GP as active implementation, BFS as archived. Update architecture diagram. |
| No change | `docs/architecture/*` | No structural architecture change (tools/ isolation preserved) |
| No change | `docs/reference/*` | No config changes |

---

## 7. Rollback Plan

To rollback to BFS:
1. In `frame_adapter.py`: change `from analyzers.tsumego_frame_gp import apply_gp_frame` → `from analyzers.tsumego_frame import apply_tsumego_frame`
2. Update `apply_frame()` body to call `apply_tsumego_frame()` instead
3. Un-skip `test_tsumego_frame.py`
4. One file change + one test file change = bounded rollback
