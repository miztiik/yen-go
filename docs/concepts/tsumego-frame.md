# Tsumego Frame

> **See also**:
>
> - [Architecture: KataGo Enrichment — D3, D33, D40](../architecture/tools/katago-enrichment.md) — Why the frame exists and key design decisions
> - [How-To: Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — Running enrichment with frame applied
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — Frame configuration options

**Last Updated**: 2026-03-13

---

## What Is a Tsumego Frame?

A **tsumego frame** is an artificial arrangement of stones placed around a Go puzzle before submitting it to KataGo for analysis. Without a frame, the puzzle sits alone on a 19×19 board surrounded by hundreds of empty intersections. KataGo's neural network interprets this as a whole-board game position, causing:

- **Policy leakage** — the network's move-probability distribution spreads across the entire board instead of concentrating on the puzzle
- **Ownership ambiguity** — the ownership head sees mostly "dame" (neutral) territory; it cannot tell which groups are alive or dead
- **Komi-driven bias** — with no surrounding stones, one side appears to be "winning" based solely on komi
- **Accuracy collapse** — empirical testing shows puzzle validation accuracy drops from ~95 % to ~60 % without a frame (see [D3](../architecture/tools/katago-enrichment.md))

The frame solves these problems by making the position look like a realistic mid-game board with clearly divided territory.

---

## Algorithm Overview

> **GP Frame Swap (2026-03-13):** The active frame implementation is now the **yengo-source count-based fill** algorithm in `analyzers/tsumego_frame_gp.py`, exposed via the thin adapter in `analyzers/frame_adapter.py`. The previous BFS flood-fill in `analyzers/tsumego_frame.py` is **archived** — kept for reference but no longer imported by any consumer code. Shared geometry utilities (bounding box, region computation) live in `analyzers/frame_utils.py`.

The implementation combines techniques from two open-source projects:

| Source                                                                            | License | What We Use                                                                        |
| --------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| **KaTrain** ([GitHub](https://github.com/sanderland/katrain), SHA `877684f`)      | MIT     | Zone-based fill algorithm, attacker inference, normalization, ko-threat placement  |
| **ghostban** ([GitHub](https://github.com/goproblems/ghostban), v3.0.0-alpha.155) | MIT     | Non-board-edge border placement, bbox-based territory formula, `offence_to_win=10` |

### Pipeline: Crop First, Then Frame

Per [D33](../architecture/tools/katago-enrichment.md), the puzzle is **cropped to a tight board** (9×9 or 13×13) before the frame is applied. The frame is never applied to the original 19×19 board — that would waste hundreds of stones on empty space.

```
Original 19×19  →  Crop to 9×9/13×13  →  Apply tsumego frame  →  Send to KataGo
```

### Step-by-Step Algorithm

```
1. Guess attacker    — edge-proximity heuristic: which colour's stones are closer
                       to the board edges?  That side is the DEFENDER; the opponent
                       is the ATTACKER (trying to kill the group)

2. Normalize         — flip the position so puzzle stones land in the top-left
                       quadrant (canonical orientation for consistent framing)

3. Compute regions   — bounding box of stones + margin = "puzzle region" (no-place zone)
                     — detect which sides of the bbox touch board edges
                     — calculate territory split:
                       defense_area = frameable // 2  (score-neutral 50/50)

4. Fill territory    — spine/chain growth with counter-based eye holes (V3.2):
                       • defender BFS from far corner (e.g., top-right)
                       • attacker BFS from border wall cells + far corner
                       • connectivity-preserving: only expand from placed stones
                       • periodic eye holes every ~7 placed stones

5. Place border      — single-stone-wide wall of ATTACKER stones around the puzzle
                       region, on non-board-edge sides only (ghostban approach)

6. Place ko threats  — (optional, when ko_type ≠ "none") fixed 4-stone patterns
                       at far corners for ko-fight material

7. Denormalize       — reverse the flips from step 2
```

### Visual Example

For a top-left corner puzzle (`X` = Black/Attacker, `O` = White/Defender):

```
OOOOOOOOOOOOO    ← Defence zone (solid White block)
OOOOOOOOOOOOO
OO.OO.OO.OO.    ← checkerboard holes far from seam
XXXXXXXXXXXXX    ← Transition seam (dense, both colours adjacent)
XXXXXXXXXXXXX    ← Offence zone (solid Black block)
XXXX.........
XXXX.XXXXXXXX    ← Attacker wall, empty margin, puzzle region
XXXX.X???????
XXXX.X???????    ← ? = original puzzle stones (untouched)
```

---

## BFS Flood-Fill (V3)

The fill algorithm uses **BFS flood-fill from seed points** to produce connected zones.

### Checkerboard (Rejected, V1)

An early implementation alternated attacker/defender stones cell-by-cell across the entire board. KataGo's ownership network sees alternating stones as contested territory, not clearly owned territory.

### Zone-Based Linear Scan (Replaced, V2)

V2 used row-major/column-major iteration to divide the board into two zones. This produced dead checker stones in sparse regions and disconnected islands when the puzzle split the frameable area.

### BFS Flood-Fill (Replaced, V3)

> **V3.2 Update**: V3 BFS flood-fill was replaced by spine/chain growth with counter-based eye holes. Multi-seed fallback was removed. See initiative `20260312-1800-fix-tsumego-frame-spine-fill` for rationale. Full doc rewrite tracked under RC-8.

V3 replaced the linear scan with BFS flood-fill from seed points:

1. **Defender BFS** from the far corner (top-right after normalize) — fills up to `defense_area` cells
2. **Attacker BFS** from border wall cells + opposite corner — fills remaining cells
3. ~~**Multi-seed fallback** — if >5% of frameable cells are unreached, add secondary seeds~~ *(removed in V3.2)*

**Why this works:**

| Property           | BFS Flood-Fill                                             | Linear Scan (V2)                                       |
| ------------------ | ---------------------------------------------------------- | ------------------------------------------------------ |
| Connectivity       | **Guaranteed** — BFS grows from seed = single component    | **Not guaranteed** — scan wraps around puzzle region    |
| Dead stones        | **None** — every stone placed is adjacent to prior stone   | **Common** — checkerboard holes produce isolated stones |
| Territory balance  | **Score-neutral** — 50/50 split, puzzle outcome decides    | **Attacker-biased** — offence_to_win gave artificial lead |
| Ownership signal   | **Strong** — connected blocks read as living territory     | **Mixed** — isolated stones read as dead/captured       |

### Zone-Based Fill (Active — KaTrain/GP Algorithm)

The **active implementation** (`tsumego_frame_gp.py`) uses KaTrain's count-based fill approach. It iterates cells in row-major order with a counter. The first `defense_area` cells become one colour; the rest become the other colour:

```
O O O O O O O O    ← solid defender zone (ownership near -1.0)
O O O O O O O O
X X X X X X X X    ← dense seam (100% fill)
X X . X . X . X    ← attacker zone with checkerboard holes far from seam
```

**Why this works:**

| Property           | Zone-Based                                                | Checkerboard                                          |
| ------------------ | --------------------------------------------------------- | ----------------------------------------------------- |
| Ownership signal   | Strong (~±1.0) — solid blocks read as territory           | Weak (~0.0) — alternating looks contested             |
| Policy containment | Strong — dense fill leaves few legal moves outside puzzle | Moderate — 50% empty frame has playable intersections |
| Stone density      | ~65–75% average (100% at seam, ~50% far)                  | ~50% everywhere                                       |
| Territory balance  | Count-based split with `offence_to_win` advantage         | Exact 50/50 alternation                               |

### The Dense Seam

Near the boundary between the two zones (`|count - defense_area| ≤ board_size`), **all** cells are filled regardless of the checkerboard pattern. This prevents either side from having stones with zero liberties at the transition point. Far from the boundary, the standard `(x + y) % 2 == 0` checkerboard holes provide liberty safety.

---

## 1-Pass vs 2-Pass Analysis

### Current: 1-Pass (Frame Applied, Then Analysed)

Yen-Go's enrichment pipeline applies the tsumego frame and sends the framed position to KataGo once:

```
Parse SGF  →  Crop  →  Apply frame  →  KataGo analysis (1 pass)  →  Extract results
```

This is sufficient for our current needs: correct-move validation, difficulty estimation, technique classification, and teaching comments.

### yengo-source: 2-Pass (Comparison Mode)

yengo-source uses a **2-pass mechanism** as a diagnostic/research feature:

```
Pass 1: Analyse raw position (NO frame)   → baseline winrate, policy, ownership
Pass 2: Analyse WITH frame                → constrained winrate, policy, ownership
Compare: delta between passes reveals frame impact
```

The delta measures how much the frame changes KataGo's evaluation. Large deltas suggest the frame significantly constrains the search — useful for calibrating frame parameters or detecting puzzles where the frame distorts results.

**Parameters observed on yengo-source:**

| Parameter | Value                       |
| --------- | --------------------------- |
| Model     | b10 (10-block, compact)     |
| Backend   | WebGL (GPU in browser)      |
| Visits    | 500                         |
| Frame     | Toggle on/off via UI button |

**Our position:** 2-pass is not needed for production enrichment. It could be added as an optional diagnostic mode in the lab tool if frame calibration work requires it in the future.

---

## Key Parameters

| Parameter        | Default  | Source   | Description                                                                                                      |
| ---------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------------------- |
| `margin`         | 2        | KaTrain  | Empty rows/columns around puzzle stones where no frame stones are placed                                         |
| `ko_type`        | `"none"` | KaTrain  | `"none"`, `"direct"`, or `"approach"` — adds ko-threat patterns when applicable                                  |
| `synthetic_komi` | `false`  | Lizzie   | Experimental: recompute komi from filled territory areas instead of preserving original. Not for production use.  |

> **Removed in V3:** `offence_to_win` (previously defaulted to 10). Territory split is now score-neutral (50/50). The puzzle outcome alone determines the winning margin.

---

## Legality Validation (V3)

Frame stone placement is guarded by three validation checks. Each candidate placement is tested before adding; illegal placements are silently skipped.

### Guard Ordering

1. **Eye detection** — skip if the point is a single-point or two-point eye of the defender. Filling eyes destroys the defender's living potential.
2. **Self-legality** — skip if the placed stone's group would have zero liberties (suicide). Uses BFS liberty counting.
3. **Puzzle stone protection** — skip if placement would reduce any adjacent puzzle-stone group to zero liberties.

These guards are implemented in `analyzers/liberty.py` (extracted per MH-1 governance constraint when helpers exceeded 120 lines).

### Attacker Inference: PL Tie-Breaker (F25)

`guess_attacker()` uses a three-heuristic cascade: stone-count ratio (≥3:1), average edge distance, and cover-side score. When all three fail to distinguish attacker from defender, the **player-to-move (PL)** property serves as a tie-breaker: in tsumego, the player to move is typically the defender, so `opposite(PL)` = attacker. This replaces the previous arbitrary `Color.BLACK` fallback. A `logger.info` message is emitted when the PL-based result differs from what the heuristic would have chosen.

### Fill Density Metric

Each frame records a `fill_density` value: `stones_added / frameable_area`. This metric is logged via `logger.debug` and stored in `FrameResult.fill_density` for observability.

### Skip Counters

`FrameResult` includes three skip counters for diagnostic purposes:
- `stones_skipped_illegal` — placements that would create zero-liberty groups
- `stones_skipped_puzzle_protect` — placements that would capture puzzle stones
- `stones_skipped_eye` — placements that would fill defender eyes

### Nearly-Full Board Handling (F11)

When the frameable area is less than 5% of the total board, `build_frame()` returns early with the original position unmodified and a warning log.

### Inviolate Rule: player_to_move

`player_to_move` from the original SGF PL property is **never altered** by the framing process. KataGo's policy head conditions on this value; changing it would alter move recommendations.

### Post-Fill Validation (V3)

After all frame stones are placed, `validate_frame()` checks:

1. **No truly isolated stones** — every frame stone must have at least one orthogonal neighbor (of any color). Stones at the zone boundary between defender and attacker fill may have only opposite-color neighbors (seam stones) — this is expected.
2. **Connectivity diagnostics** — component counts for defender and attacker fill zones are logged. Multiple components are allowed when puzzle geometry splits the frameable area.

If validation fails (truly isolated stones detected), the frame is rejected:
- `WARNING` log with full diagnostics (component counts, dead stone counts)
- Failed frame position logged as SGF for troubleshooting
- `FrameResult` returned with original position and `frame_stones_added=0`
- Callers handle "frame skipped" gracefully (same as F11 nearly-full board)

---

## Known Limitations

1. **BFS seed placement determines zone division.** The defender and attacker BFS seeds are placed at fixed far corners after normalization. On small boards (9×9) where the puzzle region geometrically splits the frameable area, the BFS may produce multiple disconnected components per color — this is logged as INFO and is an inherent geometry constraint, not a fill quality issue.

2. **Ko-threat placement degrades on small boards.** On a crowded 9×9 board, the 5 candidate positions for ko-threat patterns may all be blocked. A warning is logged (`"Ko threats requested ... but insufficient room"`), but the framed position is still returned without ko material. Callers should check logs if ko analysis quality matters. On 19×19 boards, ko threats are placed **before** territory fill to avoid placement conflicts.

3. **Synthetic komi is experimental.** When `synthetic_komi=True`, komi is recomputed from the territory fill areas. This can stabilize engine evaluations for some puzzles but may distort puzzle semantics for others. Not enabled by default.

---

## Alternative Implementations Considered

During development, we compared our algorithm against **Lizzie YZY** ([GitHub](https://github.com/yzyray/lizzieyzy), GPL-3.0), a Leela Zero/KataGo GUI that includes tsumego framing in `rules/Tsumego.java`. Key differences:

| Aspect               | Yen-Go (adopted)                                       | Lizzie (researched, not adopted)                          |
| -------------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| Fill strategy        | BFS flood-fill from seed points (V3)                   | Side-specific checkerboard with hard boundaries           |
| Orientation          | Normalize to TL (flip + axis-swap) → single code path   | 4 separate case branches (left/right/top/bottom)          |
| Territory split      | Score-neutral 50/50 split                              | Half-board area balancing with residual komi              |
| Ko threats           | Fixed 4-stone patterns in far corners                  | Same patterns with extensive no-room fallback diagnostics |
| Komi                 | Preserved (default) or synthetic (opt-in)              | Always recomputed from territory                          |
| Attacker inference   | Edge-distance + ratio + cover-side tie-break           | Cover-side scoring as primary heuristic                   |

**What we adopted from Lizzie:**
- Cover-side attacker tie-breaker as secondary heuristic (C3)
- Ko-room warning diagnostics (C1)
- Optional synthetic komi mode for experimentation (C4)

**What we rejected:**
- Side-specific branch explosion (4× duplicated logic) — normalization eliminates this need
- Checkerboard-dominant fill — produces weak ownership signal
- Zobrist hash integration during framing — unnecessary for our pipeline


---

## Diagnostic Tooling

The enrichment lab includes a diagnostic script for visualising the frame:

```bash
# Render before/after ASCII boards
python scripts/show_frame.py path/to/puzzle.sgf

# From stdin
echo "(;SZ[19]FF[4]GM[1]PL[B]AB[fb][bb][cb][db]AW[ea][dc][cc][eb][bc])" | python scripts/show_frame.py -

# With custom margin
python scripts/show_frame.py puzzle.sgf --margin 3
```

> **Note (GP Frame Swap):** The `--ko` and `--color` CLI flags were removed when `show_frame.py` was rewired to use the GP adapter. Ko detection and attacker colour are now determined automatically by the algorithm.

This renders the raw position and the framed position side by side using `X` (Black), `O` (White), `.` (empty) notation with GTP coordinate labels.

---

## Attribution

Both primary source projects are MIT-licensed and cited in the module header:

- **KaTrain** — https://github.com/sanderland/katrain (SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`)
- **ghostban** — https://github.com/goproblems/ghostban (v3.0.0-alpha.155)

Additionally researched (not adopted as source code):

- **Lizzie YZY** — https://github.com/yzyray/lizzieyzy (GPL-3.0) — `rules/Tsumego.java`. Cover-side scoring, synthetic komi, and ko-room diagnostics were reimplemented from scratch based on algorithmic concepts observed in this codebase. No code was copied.
