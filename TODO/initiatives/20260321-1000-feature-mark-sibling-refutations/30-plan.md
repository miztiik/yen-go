# Plan — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Selected Option: OPT-1 (Backend Pipeline Fix — Structural Sibling Heuristic)
> Last Updated: 2026-03-21

## Architecture

### New Function: `mark_sibling_refutations(root: SolutionNode) -> int`

**Location:** `backend/puzzle_manager/core/correctness.py`

**Algorithm:**
```
def mark_sibling_refutations(root: SolutionNode) -> int:
    """Walk solution tree; mark unmarked siblings as wrong when exactly 1 sibling is correct.
    
    Returns: count of nodes marked as wrong.
    """
    marked = 0
    
    def _walk(node: SolutionNode) -> None:
        nonlocal marked
        if not node.children:
            return
        
        # Partition children by correctness status
        # "explicitly correct" = is_correct was set to True by Layer 1/2
        #   (i.e., has BM/TE/IT marker or Correct/Wrong comment — infer_correctness returned non-None)
        # "explicitly wrong" = is_correct was set to False by Layer 1/2
        # "unmarked" = is_correct is True (default) but has no signal (infer_correctness returned None)
        
        explicitly_correct = []
        explicitly_wrong = []
        unmarked = []
        
        for child in node.children:
            # A child is "explicitly correct" if it has correctness markers/comments
            # A child is "unmarked" if is_correct=True AND no signal exists
            if not child.is_correct:
                explicitly_wrong.append(child)
            elif _has_correctness_signal(child):
                explicitly_correct.append(child)
            else:
                unmarked.append(child)
        
        # Only mark unmarked siblings when EXACTLY 1 sibling is explicitly correct
        # Miai guard: if 2+ are explicitly correct, leave unmarked siblings alone
        if len(explicitly_correct) == 1 and unmarked:
            for child in unmarked:
                # Only mark player-move nodes (nodes with a move)
                if child.move is not None:
                    child.is_correct = False
                    marked += 1
        
        # Recurse into all children (including correct ones — they may have inner branches)
        for child in node.children:
            _walk(child)
    
    _walk(root)
    return marked

def _has_correctness_signal(node: SolutionNode) -> bool:
    """Check if a node has any explicit correctness signal (marker or comment)."""
    # Layer 1: SGF markers
    if any(k in node.properties for k in ("BM", "TR", "TE", "IT")):
        return True
    # Layer 2: Comment with correctness prefix
    if node.comment:
        result = infer_correctness_from_comment(node.comment)
        if result is not None:
            return True
    return False
```

**Key Design Decisions:**

1. **"Unmarked" detection**: A node is "unmarked" when `is_correct=True` (the default) AND it has no explicit correctness signal (no BM/TE/IT/TR markers, no Correct/Wrong/Right/Incorrect comment text). The helper `_has_correctness_signal()` re-checks Layer 1 and Layer 2 signals.

2. **Exactly-1-correct guard (miai protection)**: When ≥2 siblings are explicitly correct, this is a miai/multi-answer puzzle. The heuristic skips these nodes to prevent false positives.

3. **Player-move filter**: Only marks nodes with `move is not None`. Root/pass/setup nodes are skipped.

4. **Recursive all-depth traversal**: The `_walk()` recurses into ALL children (including correct ones) because sub-variations at deeper levels may also have the pattern.

5. **SGFBuilder handles serialization**: The function only mutates `is_correct` on `SolutionNode`. `SGFBuilder._build_node()` already emits `BM[1]` when `is_correct=False` and calls `standardize_move_comment()` to generate `C[Wrong]`.

### Call Site: `stages/analyze.py`

In `_analyze_puzzle()`, after `game = parse_sgf(content)` and before `compute_quality_metrics(game)`:

```python
from backend.puzzle_manager.core.correctness import mark_sibling_refutations

# After parse_sgf():
if game.has_solution:
    marked_count = mark_sibling_refutations(game.solution_tree)
    if marked_count > 0:
        trace_logger.debug(
            "Marked %d unmarked sibling refutations for %s",
            marked_count, puzzle_id,
        )
```

**Insertion point:** After `game = parse_sgf(content)` (line ~270) and the trace_id extraction block, before the "Skip if already has ALL required YenGo properties" check — OR after that check but before quality/complexity computation. The key constraint is: **before `compute_quality_metrics()` and `compute_complexity_metrics()`** so metrics reflect the corrected data.

Best insertion point: **immediately after `game = parse_sgf(content)`** and the trace_id/logger setup, before the `is_fully_enriched` skip check. This ensures even already-enriched puzzles get the sibling fix on re-analyze (which is correct — we want to fix all puzzles).

### Data Model Impact

No data model changes. The function mutates existing `SolutionNode.is_correct` field in-place.

### Frontend Impact

**None.** The frontend `buildSolutionNodeFromSGF()` already detects `BM[1]` and `C[Wrong]` correctly:
```ts
const hasBadMoveProperty = props.BM !== undefined;
const hasWrongComment = isWrongMoveComment(comment);
const isCorrect = !hasBadMoveProperty && !hasWrongComment;
```

A **regression test** (vitest) will be added to verify this behavior explicitly with BM+C[Wrong] markers.

## Risks and Mitigations

| Risk ID | Risk | Probability | Impact | Mitigation |
|---------|------|-------------|--------|------------|
| R1 | False positive: marking a correct move as wrong in miai puzzle | Low | High | Exactly-1-correct guard: only mark when exactly 1 sibling is explicitly correct. Unit test with miai topology. |
| R2 | Unmarked detection inaccuracy: node has is_correct=True from default, not from explicit signal | Low | Medium | `_has_correctness_signal()` re-checks Layer 1 and Layer 2 independently of `is_correct` value. |
| R3 | Performance: large solution trees | Very Low | Low | Tree walk is O(n) where n = nodes. Typical puzzles have <100 nodes. No I/O. |
| R4 | Existing tests break | Low | Medium | Run full backend unit + frontend test suites before and after. |

## Rollback Plan

1. Remove the `mark_sibling_refutations()` call from `stages/analyze.py`.
2. Re-run the pipeline for affected sources.
3. Previously-processed puzzles will revert to their original unmarked state.

## Documentation Plan

| ID | Action | File | Why |
|----|--------|------|-----|
| D1 | Update module docstring | `core/correctness.py` | Add `mark_sibling_refutations` to "Used by:" list in module docstring |
| D2 | Add inline comment at call site | `stages/analyze.py` | Explain why the function is called at this point in the pipeline |
| D3 | Update AGENTS.md | `backend/puzzle_manager/AGENTS.md` | Mention new function in correctness module section (structural change rule) |

No user-facing documentation changes needed — this is an internal pipeline improvement that fixes data quality transparently.
