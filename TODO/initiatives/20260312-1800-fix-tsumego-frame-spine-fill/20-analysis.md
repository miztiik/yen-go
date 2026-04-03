# Analysis

**Last Updated**: 2026-03-12

## Root Cause
V3.1 `_bfs_fill()` expands BFS frontier from ALL visited cells including skipped ones. The checkerboard skip (`x%2==0 and y%2==0`) removes stones but preserves expansion, causing placed stones on either side of holes to land in separate connected components.

## Key Findings

| id | finding | severity | resolution |
|----|---------|----------|------------|
| AN-1 | BFS expands past skipped cells → fragments | CRITICAL | Only expand from placed cells |
| AN-2 | `_near_boundary` Manhattan≤2 covers ~60% → too dense | HIGH | Reduce to Manhattan≤1 |
| AN-3 | Multi-seed fallback creates new components | HIGH | Remove fallback |
| AN-4 | Checkerboard pattern not connectivity-aware | CRITICAL | Replace with counter-based eye skip |

## Impact Surface
- `_bfs_fill()` — complete rewrite of skip logic
- `fill_territory()` — remove multi-seed fallback
- Tests — density threshold and eye test adjustments
