# Plan

**Last Updated**: 2026-03-12

## Approved Scope
Replace V3.1 checkerboard skip in `_bfs_fill()` with connectivity-preserving spine fill per governance RC-1 through RC-5 (P0/P1 items).

## Implementation Approach
1. **Connectivity guarantee**: Only expand BFS frontier from cells where a stone is placed (or pre-existing same-color). Skipped cells become dead ends.
2. **Counter-based eye holes**: Every `EYE_INTERVAL` (7) placed stones, skip next eligible cell. No coordinate-based pattern.
3. **Reduced near-boundary**: Manhattan distance ≤ 1 (from ≤ 2). Dense fill only immediately adjacent to border/puzzle.
4. **Remove multi-seed fallback**: Prevents creating disconnected components for unreached cells.
5. **Test updates**: Adjust density thresholds, fix eye guard test for reduced BFS reach.

## Documentation Plan

| id | action | file | why_updated |
|----|--------|------|-------------|
| DP-1 | Deferred | docs/concepts/tsumego-frame.md | Post-validation update |

## Files Changed
- `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`
- `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`
