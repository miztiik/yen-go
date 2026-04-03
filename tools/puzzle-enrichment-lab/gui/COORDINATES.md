# Coordinate Contract — Enrichment Lab GUI

**Purpose:** Prevent the coordinate transposition bug that caused gui_deprecated to fail.

## The Bug (Root Cause)

gui_deprecated stored board state as `mat[row][col]` (via Preact Signals) but GhostBan expects `mat[col][row]` (column-major). The transposition in GoBoardPanel.tsx was fragile and caused persistent display bugs.

## The Contract (This GUI)

1. **Bridge `/api/analyze` response** delivers stones as `{x, y}` pairs where `x = column`, `y = row` (0-indexed)
2. **SSE `board_state` event** delivers `black_stones: [[x, y], ...]` — same format
3. **`board.js`** converts stone lists directly to GhostBan's Ki matrix: `mat[x][y] = Ki.Black`
4. **NO intermediate `mat[row][col]` representation** — stones go directly from API to GhostBan's coordinate system
5. **Analysis dots** use the same `{x, y}` coordinates, mapped to canvas pixels via `calcSpaceAndPadding()`
6. **BesoGo tree** uses its own internal SGF coordinates (`a`–`s`) — no translation needed

## Verification

If you see stones displayed in the wrong position (rotated 90° or mirrored), check:
1. Is there ANY point where `mat[y][x]` or `mat[row][col]` is used? → Remove it
2. Is there ANY transposition step between API data and GhostBan render? → Remove it
3. The ONLY mapping should be: `for (const [x, y] of stones) mat[x][y] = Ki.Black`
