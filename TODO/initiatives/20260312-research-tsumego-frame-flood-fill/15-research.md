# Research: Tsumego Frame Flood-Fill Strategy

**Initiative:** `20260312-research-tsumego-frame-flood-fill`
**Last Updated:** 2026-03-12
**Researcher:** Feature-Researcher mode

---

## 1. Research Question and Boundaries

**Primary Question:** Should the zone-based linear scan in `tsumego_frame.py:fill_territory()` be replaced with a BFS flood-fill, and if so, what seed strategy, border treatment, and cropping decisions follow?

**Sub-questions resolved by this brief:**

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should board cropping be dropped when adopting flood-fill? | A: Drop cropping entirely / B: Keep crop-to-standard-size / C: Increase minimum crop size threshold | B | pending | ❌ pending |
| Q2 | Where should defender/attacker BFS seeds originate? | A: Fixed far corners (top-right / bottom-right) / B: Adaptive from detect_board_edge_sides / C: Border-wall cells as attacker seed / Other | A+C hybrid | pending | ❌ pending |
| Q3 | Should the explicit border wall (`place_border`) be kept? | A: Keep unchanged / B: Drop and derive from attacker BFS / C: Keep but make attacker BFS start from border cells | C | pending | ❌ pending |
| Q4 | What should replace `_choose_scan_order()`? | A: Delete it; seed placement is geometry-aware implicitly / B: Rename to `_choose_flood_seeds()` / Other | B (rename/replace) | pending | ❌ pending |

**In-scope:** `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`, `analyzers/liberty.py`, `models/position.py` (crop), `analyzers/query_builder.py` (pipeline flow).
**Out-of-scope:** Frontend rendering, backend pipeline stages, KataGo config, visit counts, evaluation results.

---

## 2. Internal Code Evidence

### 2.1 Root Cause: Why Linear Scan Creates Disconnected Zones

| R-id | File | Symbol | Finding |
|------|------|--------|---------|
| R-1 | [analyzers/tsumego_frame.py L354–L430](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `fill_territory()` | Iterates cells in row-major or column-major scan order. Skips `puzzle_region` cells and increments a counter. First `defense_area` counted cells → defender stones; remainder → attacker stones. No connectivity guarantee. |
| R-2 | [analyzers/tsumego_frame.py L312–L330](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `_choose_scan_order()` | Returns `"column-major"` when puzzle touches left/right-only edges; `"row-major"` otherwise. Directly controls which axis the zone-split happens on. This is the only geometry-awareness in the current fill. |
| R-3 | [analyzers/tsumego_frame.py L354–L395](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `fill_territory()` | For a top-edge (non-corner) puzzle occupying columns 4–11 of a 9×9 crop: row-major scan at y=0 counts cells `x=0,1,2,3` as early-defense AND `x=12…` (if any) as also early-defense — producing two disconnected defender islands flanking the puzzle, with no defender stones connecting them. This is the structural root cause of "disconnected islands." |
| R-4 | [analyzers/tsumego_frame.py L452–L520](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `place_border()` | Places a line of attacker stones around the puzzle_region perimeter on non-board-edge sides. Called **before** `fill_territory()` in `build_frame()`. The border stones are added to the `occupied` dict before the fill runs, so the fill must navigate around them. For a top-edge puzzle, the border's vertical segment down the right side of the puzzle region acts as an additional barrier that can isolate defender fill into three distinct pools (left, right, and above-puzzle). |
| R-5 | [analyzers/tsumego_frame.py L395–L430](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `fill_territory()` | Checkerboard holes (`(x+y)%2==0 AND abs(count-defense_area)>bs`) produce isolated single stones far from the seam. Each has at most 2 or 3 empty orthogonal neighbors (2 diagonal neighbors are always empty = 2 liberties minimum). The legality guard accepts these; KataGo sees them as in-atari stones requiring capture/save responses, polluting policy output near those cells. |
| R-6 | [analyzers/tsumego_frame.py L215–L280](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `normalize_to_tl()` | Flips x/y axes so puzzle centroid is in TL quadrant. Uses **only flip** (no axis swap). A top-center puzzle with cx≈mid, cy≈0 produces `flip_x=False, flip_y=False` — puzzle stays at top-center, not normalized to any corner. This is the essential gap: normalization does not guarantee the puzzle is in a **corner** before the zone-split. |
| R-7 | [models/position.py L211–L320](../../../tools/puzzle-enrichment-lab/models/position.py) | `crop_to_tight_board()` | Crops 19×19 to bounding box + margin, snapped to nearest standard board size (9, 13, 19). Produces `CroppedPosition` with translation offset for back-translation. Cropping reduces the board to exactly the standard size that fits the puzzle with margin=2. A 4×4 corner puzzle crops to 9×9 (81 cells), leaving ~65 frameable cells. |
| R-8 | [analyzers/query_builder.py L155–L240](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py) | `build_query_from_sgf()` | Calls `crop_to_tight_board()` when `crop=True` (default). `build_query_from_position()` explicitly **does not crop** (noted in docstring: "no cropping — tree builder uses original board coordinates"). Two distinct pipeline paths already exist with and without crop. |
| R-9 | [models/position.py L14–L18](../../../tools/puzzle-enrichment-lab/models/position.py) | `STANDARD_BOARD_SIZES` | `(9, 13, 19)` — KataGo neural net trained on exactly these sizes. Cropping to a non-standard size would be undefined; crop-to-standard-size is architecturally correct. |
| R-10 | [analyzers/liberty.py L22–L60](../../../tools/puzzle-enrichment-lab/analyzers/liberty.py) | `count_group_liberties()` | Already uses BFS to count liberties of a stone group. The **same BFS primitive** needed for flood-fill zone growth. Reusing it is natural and reduces complexity. |
| R-11 | [tests/test_tight_board_crop.py L60–L100](../../../tools/puzzle-enrichment-lab/tests/test_tight_board_crop.py) | `TestCropToTightBoard` | 28 tests covering crop snapping, offset computation, back-translation. These tests do not test frame quality — they test coordinate mechanics only. Dropping crop would break these tests and the `uncrop_gtp`/`uncrop_move` back-translation logic used throughout the tree solver. High cost to remove. |
| R-12 | [analyzers/tsumego_frame.py L658–L760](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py) | `build_frame()` | Orchestration order: `normalize → regions → border → ko → fill → denormalize`. Fill receives `pre_fill_occupied` that includes border and ko stones. Changing fill algorithm requires only modifying `fill_territory()` — the orchestration stays the same. |

### 2.2 Cropping vs. Framing: Tension Analysis

The crop-first design (D33 in [katago-enrichment.md](../../../docs/architecture/tools/katago-enrichment.md)) was chosen because:
- 19×19 boards with a corner puzzle leave ~340 empty cells → most frame stones would fill empty space far from the puzzle, wasting them
- KataGo analysis on 9×9 is ~4.4× faster than on 19×19 (cells ratio)
- Crop snaps to KataGo-supported sizes (9, 13, 19)

Neither KaTrain nor ghostban crop, because they operate on the original game board (always 19×19). The framing was designed FOR 19×19 boards.

**Critical finding:** The disconnected-zone failure only manifests when:
1. The puzzle region spans a significant fraction of the smaller (cropped) board, AND
2. The puzzle is not in a corner (an edge or center puzzle), AND
3. Linear scan cannot route around the puzzle region without splitting zones

The crop itself is not the cause; the combination of crop + linear scan + non-corner puzzle is. Flood-fill on the same cropped board resolves this.

---

## 3. External References

### 3.1 KaTrain `tsumego_frame.py` — Zone-Split Algorithm (Authoritative Source)

Fetched live (SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`, MIT license) and already fully documented in `TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/15-research.md` §3.2.

Key finding for this brief: KaTrain uses **count-based zone split with row-major scan**, NOT flood-fill. The canonical diagram is:
```
OOOOOOOOOOOOO    ← Defence zone (solid White block)
XXXXXXXXXXXXX    ← Transition seam
XXXX.........
XXXX.X???????   ← puzzle in TL corner after normalization
```

KaTrain's normalization handles the TL-corner-placement problem via `flip_spec` with axis **swap** (`[False, False, True]` when `imin < jmin`). This is more powerful than our `normalize_to_tl()` which only flips, never swaps axes. **This normalization gap is the real root cause of edge-puzzle disconnection in our implementation.**

| R-id | Finding | Source |
|------|---------|--------|
| R-13 | KaTrain normalizes via flip+swap hybrid: `if imin < jmin → swap(i,j)`. This reliably puts the puzzle in a corner, not just a quadrant. | KaTrain verbatim, §3.2 of prior research |
| R-14 | KaTrain's `put_outside` is row-major iteration, same as ours — but it works because after its normalization, the puzzle is ALWAYS in a corner, so the scan never needs to route around both sides of the puzzle. | KaTrain verbatim `put_outside()` |
| R-15 | KaTrain's `put_border` places **attacker** wall at `frame_range` perimeter before the fill. The fill iterates all cells and skips `inside_p(i,j,frame_range)`. This means fill flows AROUND the border+puzzle region as a single exclusion block, not in two disjoint scanning passes. | KaTrain verbatim `tsumego_frame_stones()` call order |

### 3.2 ghostban `e.FO` — Count-Based Zone Fill (goproblems.com)

Also count-based scan, not flood-fill. Full verbatim in prior research §3.5. Same conclusion: ghostban relies on corner-normalization to avoid zone splits.

### 3.3 BFS Flood-Fill in Territory Estimation Context

BFS flood-fill for territory is well-established in Go engine code:

| R-id | Source | Usage | Applicability |
|------|--------|-------|---------------|
| R-16 | `TODO/puzzle-quality-scorer/reference/gogamev4-territory.md` | `flood_fill_territory(board, start_x, start_y, visited)` — BFS from a seed point to identify enclosed empty regions | Direct adaptation: replace scan-order iteration with BFS for zone growth |
| R-17 | `TODO/lab-web-katrain/005-learnings-and-review-browser-engine.md` | blacktoplay.com `estimator.js`: "territory filling (flood fill areas surrounded by one color)" — real-world JS implementation | Confirms BFS territory fill is a known good pattern for Go boards |
| R-18 | `TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md` KM-05 | "Relevance Zone Refinement (flood-fill)" noted as valid but deferred because current crop+frame is sufficient | Shows BFS was considered and deferred, not rejected |
| R-19 | `analyzers/liberty.py:count_group_liberties()` | BFS traversal of same-color connected stones — already in the codebase | The BFS primitive for flood-fill zone growth is already present. Implementation cost is low — it's adapting the existing pattern, not writing new infrastructure. |

### 3.4 Python stdlib BFS — No New Dependency

Standard BFS using `collections.deque` is the canonical Python approach:
```python
from collections import deque
def _bfs_fill(seed, frameable, quota, color, occupied):
    """BFS from seed; fills up to quota cells with color. Returns placed stones."""
    queue = deque([seed])
    visited = {seed}
    stones = []
    while queue and len(stones) < quota:
        x, y = queue.popleft()
        if (x, y) not in frameable or (x, y) in occupied:
            continue
        stones.append(Stone(color=color, x=x, y=y))
        occupied[coord] = color
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            neighbor = (x+dx, y+dy)
            if neighbor not in visited and neighbor in frameable:
                visited.add(neighbor)
                queue.append(neighbor)
    return stones
```
No external dependency. `collections.deque` is stdlib.

**License/compliance:** BFS is a standard algorithm with no IP concerns. No external library needed. `pyproject.toml` unchanged.

---

## 4. Candidate Adaptations for Yen-Go

| R-id | Adaptation | Description | Effort | Risk |
|------|-----------|-------------|--------|------|
| R-20 | **Fix normalize_to_tl to include axis swap (KaTrain parity)** | Add `swap_xy` logic: `if puzzle_min_row < puzzle_min_col → swap x↔y`. This puts the puzzle in a corner (not just a quadrant). Solves the root cause of disconnected zones **without** any flood-fill changes. | ~20 lines, 1 day | Medium: swap changes test expectations for edge-puzzle normalization |
| R-21 | **Replace `fill_territory` with BFS flood-fill** | Delete `_choose_scan_order()`. Add `_choose_flood_seeds()`. In `fill_territory()`, replace scan loop with BFS from defender seed (quota=defense_area) then BFS from attacker seed (remaining cells). Legality guards preserved. | ~60 lines changed, 2 days | Low-Medium: changes fill output; calibration tests need refresh |
| R-22 | **Attacker BFS seeds from border wall cells** | After `place_border()`, pass border stone coords as attacker BFS seeds. Attacker zone then grows OUT from the border = one connected attacker blob (border + fill). Eliminates attacker disconnection entirely. | +10 lines in `build_frame()` | Low: purely additive, natural extension of existing border logic |
| R-23 | **Delete `_choose_scan_order()`; replace with `_choose_flood_seeds()`** | Geometry-aware seed placement based on `regions.board_edge_sides`. After normalize_to_tl, fixed: defender=(bs-1, 0), attacker=(bs-1, bs-1). Without normalize, infer from edge_sides. | ~15 lines | Low: internals only, no public API change |
| R-24 | **Multi-seed fallback for edge (non-corner) puzzles** | After primary BFS, scan frameable cells unreachable by first BFS; add secondary seeds. Ensures both left and right of an edge puzzle get filled. Minor complexity increase. | ~30 lines | Low: purely additive |
| R-25 | **Drop cropping** | Remove `crop_to_tight_board()` call; always use 19×19. Removes coordinate back-translation overhead. | High: touches query_builder, tree solver, 28+ crop tests | High: breaks back-translation for tree solver, violates D33; full test suite impact |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

### Flood-Fill Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| BFS cannot reach some cells (puzzle region as barrier) | Medium (edge puzzles) | Medium | R-24 multi-seed fallback; unreachable cells get default fill pass |
| Flood-fill changes `fill_density` metric; calibration tests fail | High | Low | Recalibrate; density should improve (more connected groups) |
| Seam formation: BFS zones grow toward each other and may interleave at boundary | Low | Low | BFS with strict quota stops cleanly; seam width = 1 cell naturally |
| `place_border` + BFS interaction: border occupies cells before BFS, changing reachability | Low | Low | Beneficial: attacker BFS seeded at border cells naturally includes them |
| `ko_stones` placed before fill (in `build_frame`) create corridors in BFS | Low | Low | Ko stones are already in `pre_fill_occupied`; BFS respects occupied dict |

### Cropping Drop — Rejected

**R-25 (Drop cropping) is rejected** for the following reasons:
- `build_query_from_sgf()` returns a `QueryResult.cropped` object used by callers for back-translation of KataGo move coordinates to original SGF coordinates
- `build_query_from_position()` (tree solver) already skips crop; introducing full-board into the SGF path would desynch coordinate spaces
- D33 architectural decision is documented: crop-then-frame was validated. Reversing it requires a governance panel decision (Level 5 change)
- 28+ crop tests (`test_tight_board_crop.py`) + tree solver integration tests would need complete rework
- Flood-fill achieves the stated goals (connected groups, better signal) without dropping crop

### normalize_to_tl Swap Fix vs. Flood-Fill

**R-20 (normalize swap)** is the **simpler fix** that addresses the root cause:
- The root cause is that `normalize_to_tl()` doesn't match KaTrain's full normalization
- KaTrain's `tsumego_frame_stones()` uses `[False, False, True] if imin < jmin` → axis swap puts puzzle in corner
- Our `normalize_to_tl()` skips the swap, leaving edge puzzles as edge puzzles
- Adding axis swap to `normalize_to_tl()` means linear scan works correctly (like KaTrain) — no flood-fill needed for the disconnected-zone bug

**However**, flood-fill is **additionally** valuable because:
1. Connected groups have better ownership signal even for corner puzzles (fewer isolated 2-liberty stones)
2. BFS naturally respects legality constraints as it grows, more elegant than post-hoc guards
3. BFS produces zones that look more like natural game positions (solid blobs, not scan-order bands)

### License

- BFS is public domain algorithm, stdlib `deque`
- `liberty.py:count_group_liberties()` BFS pattern is original Yen-Go code (MIT, in-repo)
- No external reference code copied verbatim

---

## 6. Planner Recommendations

**R-A (Highest priority, low risk):** Fix `normalize_to_tl()` to include axis swap (R-20). This is a single-function fix that aligns our normalization with KaTrain's verbatim behavior. It eliminates the root cause of disconnected zones for edge puzzles with 1/4 the effort of full flood-fill. Can be deployed independently. Expected impact: eliminates "disconnected islands" class of failures. Test changes: `TestNormalizeTL.test_tl_no_flip` may need adjustment for edge-puzzle cases.

**R-B (Medium priority, medium risk):** Replace `fill_territory()` with BFS flood-fill (R-21 + R-22 + R-23). Delete `_choose_scan_order()`, add `_choose_flood_seeds()`, rewrite the iteration loop with `collections.deque` BFS seeded at top-right (defender) and bottom-right (attacker), using border wall cells as additional attacker seeds. This produces fully connected zones with organic zone boundaries. Reuse `count_group_liberties`-style BFS from `liberty.py`. Legality guards (eye, suicide, puzzle-protect) are preserved as-is — they apply during BFS placement identically to linear scan. Estimated scope: ~80 lines changed in `tsumego_frame.py`, ~10 lines in `build_frame()`, calibration reset for `fill_density` tests.

**R-C (Conditionally, based on R-A/R-B results):** Add multi-seed fallback for unreachable cells (R-24) only if empirical testing shows BFS leaves >5% of frameable area unfilled for edge-puzzle cases. This is an additive fallback, not a structural change.

**R-D (Do NOT pursue):** Drop cropping (R-25). This violates D33, breaks the tree solver's back-translation, and requires a governance panel decision. The benefits of flood-fill are achievable without changing board size. If full-board framing is ever desired, it must go through D-level ADR review as a Phase-S architectural change.

---

## 7. Confidence and Risk

| Metric | Value | Notes |
|--------|-------|-------|
| `post_research_confidence_score` | 88 | High confidence on all four questions; R-20 (swap) is fully proven from KaTrain verbatim; flood-fill implementation pattern is established in-codebase. -12 for not having empirical failure corpus to quantify how often edge-puzzle disconnection occurs in production. |
| `post_research_risk_level` | `low` | All changes are isolated to `tsumego_frame.py`. No public API surface changes. Legality guards are preserved. Calibration tests require refresh but that's expected. R-20 alone can be done at Correction Level 1; R-B is Level 2. |

---

## Handoff Summary

```
research_completed: true
initiative_path: TODO/initiatives/20260312-research-tsumego-frame-flood-fill/
artifact: 15-research.md
top_recommendations:
  1. Fix normalize_to_tl() axis-swap (R-20) — root cause fix, 1 day, Level 1
  2. Replace fill_territory() with BFS flood-fill (R-21+R-22+R-23) — algorithmic improvement, 2 days, Level 2
  3. Keep border wall; seed attacker BFS from border cells (R-22) — integrates naturally
  4. Delete _choose_scan_order(); add _choose_flood_seeds() with fixed post-norm seeds (R-23)
open_questions:
  - Q1: Confirm planner accepts keeping crop-to-standard-size (D33 preserved) — RECOMMENDED: yes
  - Q2: Should R-20 (normalize swap) be shipped independently before R-B (flood-fill rewrite)?
  - Q3: Is there empirical data on how often edge-puzzle disconnection has caused KataGo signal degradation?
post_research_confidence_score: 88
post_research_risk_level: low
```

---

> **See also:**
>
> - [Prior Research: goproblems.com frame](../2026-03-08-research-goproblems-tsumego-frame/15-research.md) — KaTrain + ghostban verbatim sources, R-1 through R-63
> - [Feature Rewrite: Tsumego Frame](../20260308-1500-feature-tsumego-frame-rewrite/15-research.md) — merged design summary
> - [Legality Initiative](../20260311-1800-feature-tsumego-frame-legality/00-charter.md) — F1-F25 correctness findings (already implemented)
> - [Architecture: KataGo Enrichment D33](../../../docs/architecture/tools/katago-enrichment.md) — crop-then-frame decision
> - [Concept: Tsumego Frame](../../../docs/concepts/tsumego-frame.md) — algorithm overview
