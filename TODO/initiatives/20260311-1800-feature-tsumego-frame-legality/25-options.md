# Options: Tsumego Frame Legality & Correctness

**Last Updated**: 2026-03-11

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 90 |
| Risk Level | low |
| Research Invoked | No (score ≥ 70, risk low) |

---

## Option Comparison

| Dimension | OPT-1: Inline Validation | OPT-2: Liberty Module + Validation | OPT-3: Full Play Engine |
|-----------|--------------------------|-------------------------------------|------------------------|
| **Summary** | Add liberty-counting helpers directly in `tsumego_frame.py`. Each stone placement checks surrounding liberties before adding. Eye detection inline. | Extract a reusable `liberty.py` module (~100 lines) in `tools/puzzle-enrichment-lab/analyzers/`. Import into `tsumego_frame.py`. | Build a minimal Go rules engine with capture resolution (auto-remove dead groups). Frame stones are "played" with captures. |
| **Scope** | Single file edit (~80-100 new lines in tsumego_frame.py) | New file (~100 lines) + edits to tsumego_frame.py (~40 lines) | New module (~200-300 lines) + significant tsumego_frame.py refactor |
| **F1 (illegality)** | ✅ Liberty check before placement; skip if would create 0-liberty group | ✅ Same logic via imported `has_liberties()` | ✅ Full capture resolution removes dead groups automatically |
| **F2 (puzzle capture)** | ✅ Check puzzle stone liberties after candidate placement; skip if reduces any to 0 | ✅ Same via `check_puzzle_liberties()` | ✅ Captures auto-resolved but may REMOVE puzzle stones (dangerous) |
| **F3/F9 (turn parity)** | ✅ Document player_to_move as inviolate; add code comment | ✅ Same | ✅ Same |
| **F7 (ko fragility)** | ✅ Existing warning sufficient (Low severity) | ✅ Same | ✅ Ko detection built into engine |
| **F8 (legality-aware)** | ✅ validate-then-skip approach | ✅ Same approach, cleaner separation | ✅ play-then-resolve approach |
| **F10 (puzzle capture)** | ✅ Pre-check puzzle liberties | ✅ Same | ⚠️ Risk: captures may remove puzzle stones |
| **F11 (full board)** | ✅ Count frameable area, skip fill if < threshold | ✅ Same | ✅ Same |
| **F20 (eye space)** | ✅ Eye detection inline (~30 lines) | ✅ Eye detection in liberty module | ✅ Eye detection in engine |
| **F25 (PL attacker)** | ✅ PL tie-breaker in guess_attacker() (~5 lines) | ✅ Same | ✅ Same |
| **Complexity** | Low — single-file, no new abstractions | Low-Medium — new file, clean separation | High — full Go engine, scope creep risk |
| **Test impact** | Existing 46 tests + new validation tests | Same + liberty module unit tests | Major — need engine unit tests + integration |
| **Regression risk** | Low — validate-and-skip never changes existing behavior for legal placements | Low — same approach, just better organized | Medium — capture resolution changes stone set unpredictably |
| **YAGNI compliance** | ✅ Minimal — only what's needed | ⚠️ Module reusable but no current consumers | ❌ Builds far more than needed |
| **Architecture compliance** | ✅ No new deps, no backend import | ✅ Same | ✅ Same (but 2-3x code volume) |

---

## Detailed Option Descriptions

### OPT-1: Inline Validation (Recommended)

**Approach**: Add liberty-counting and eye-detection helpers as private functions directly in `tsumego_frame.py`. Modify `fill_territory()` and `place_border()` to call these validators before each stone placement.

**Key functions to add** (~80-100 lines total):

```python
def _count_liberties(coord, color, occupied, board_size) -> int:
    """Count liberties of the group containing coord after hypothetical placement."""

def _would_reduce_puzzle_liberties(coord, color, puzzle_stones, occupied, board_size) -> bool:
    """Check if placing a stone at coord would reduce any puzzle group to 0 liberties."""

def _is_eye_point(coord, color, occupied, board_size) -> bool:
    """Check if coord is a single-point eye of the given color."""

def _is_two_point_eye(coord, color, occupied, board_size) -> bool:
    """Check if coord is part of a two-point eye formation."""

def _has_frameable_space(regions, board_size, min_ratio=0.05) -> bool:
    """Check if board has enough frameable area (F11)."""
```

**Fill/border modification**: Wrap each `stones.append()` call with a guard:
```python
if _count_liberties(...) == 0:
    continue  # Skip illegal placement
if _would_reduce_puzzle_liberties(...):
    continue  # Protect puzzle stones
if _is_eye_point(...) or _is_two_point_eye(...):
    continue  # Respect eye space
```

**F25 fix**: Replace the `return Color.BLACK` tie-breaker at line 168 with:
```python
# PL tie-breaker: in tsumego, player_to_move is typically the defender
if position.player_to_move:
    return _opposite(position.player_to_move)
return Color.BLACK  # Ultimate fallback
```

**Benefits**: Minimal file count, no new abstractions, all changes localized, easiest to review.
**Drawbacks**: `tsumego_frame.py` grows from ~650 to ~750 lines. Liberty logic not reusable.

### OPT-2: Liberty Module + Validation

**Approach**: Create `tools/puzzle-enrichment-lab/analyzers/liberty.py` (~100 lines) containing liberty counting, eye detection, and puzzle-protection logic. Import into `tsumego_frame.py`.

**Module API**:
```python
# liberty.py
def count_group_liberties(stones, coord, board_size) -> int
def would_capture(stones, coord, color, board_size) -> bool
def is_single_eye(stones, coord, color, board_size) -> bool
def is_two_point_eye(stones, coord, color, board_size) -> bool
```

**Benefits**: Clean separation of concerns, testable in isolation, potentially reusable by other analyzers.
**Drawbacks**: New file (against minimal-files preference), need to import correctly for both direct and package execution modes (the `try/except ImportError` pattern), no current second consumer.

### OPT-3: Full Play Engine (Not Recommended)

**Approach**: Build a minimal Go rules engine that simulates stone placement with capture resolution. Frame stones are "played" rather than placed.

**Benefits**: Correct-by-construction — every stone placement is legal.
**Drawbacks**: 
- ~200-300 lines of new code (scope creep)
- Capture resolution could remove puzzle stones (F10 violation)
- Turn alternation changes the entire frame philosophy
- YAGNI — the validate-and-skip approach is sufficient

---

## Recommendation

**OPT-1 (Inline Validation)** is recommended:

1. **YAGNI**: No second consumer for a liberty module. If one emerges later, extraction is trivial.
2. **Minimal files**: Follows project preference for editing existing files over creating new ones.
3. **Lowest risk**: validate-and-skip never changes behavior for already-legal placements; only skips illegal ones.
4. **Fastest to implement**: Single file, ~80-100 new lines, ~10 lines of modification to existing functions.
5. **Easiest to test**: Data audit validates on real corpus; unit tests cover edge cases.
