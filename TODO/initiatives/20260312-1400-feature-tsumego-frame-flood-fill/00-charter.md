# Charter: Tsumego Frame Flood-Fill Rewrite

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Last Updated**: 2026-03-12

---

## 1. Problem Statement

The tsumego frame's `fill_territory()` algorithm uses a linear zone-based scan (row-major/column-major) that produces **dead checker stones**, **disconnected islands**, and **border-fragmented defender fill**. Expert analysis (KataGo architecture expert, 1P+ tsumego composer, correctness governance panel) identified five causally linked issues:

| ID | Issue | Severity | Root Cause |
|----|-------|----------|------------|
| ISSUE-1 | Dead checker stones in sparse regions — ~50 White stones with 2 liberties, zero eye-space | **Critical** | `abs(count - defense_area) > board_size` generates isolated single stones; KataGo ownership assigns them as dead → inflates attacker territory |
| ISSUE-2 | Border wall fragments defender fill | **High** | Border placed between defender stones and main defender territory; defender isolated on attacker-side |
| ISSUE-3 | Row-major scan creates disconnected islands | **High** | Linear scan distributes fill across spatially distant cells; `normalize_to_tl()` missing axis-swap (KaTrain uses flip+swap) |
| ISSUE-4 | Post-fill validation absent | **Medium** | No check detects disconnected islands; silent correctness failures |
| ISSUE-5 | `offence_to_win` formula creates asymmetric territory | **High** | Score-biased fill violates global neutrality; KataGo may accept locally suboptimal moves because of artificial global advantage |

**Causal chain:** Isolated checker stone → no connectivity → no eye formation → KataGo reads as dead → assigns cells to attacker → global ownership corrupted → puzzle evaluation contaminated.

**Research finding (R-6, R-13, R-14):** The root cause of disconnected zones is a missing axis-swap in `normalize_to_tl()`. KaTrain normalizes via `flip+swap` which always puts the puzzle in a true corner; our implementation only flips, leaving edge puzzles as edge puzzles where the linear scan cannot route around both sides.

## 2. Goals

| ID | Goal | Acceptance Criteria |
|----|------|-------------------|
| G1 | **Connected fill zones** | All defender fill stones form a single connected component. All attacker fill stones form a single connected component (including border). Verified by post-fill BFS connectivity check. |
| G2 | **No dead frame stones** | No frame stone has zero same-color orthogonal neighbors AND is not adjacent to puzzle region. Every frame stone is part of a group with ≥2 liberties. |
| G3 | **Score-neutral territory** | Defender fill cells ≈ Attacker fill cells (±5%) outside puzzle zone. `offence_to_win` removed. Puzzle outcome alone determines the winning margin. |
| G4 | **Post-fill validation** | Hard assertion: fail frame and return original position + warning log when validation detects disconnected islands, dead stones, or zone fragmentation. Failed frame position logged for analysis. |
| G5 | **Correct normalization** | `normalize_to_tl()` includes axis-swap (KaTrain parity) so puzzles are reliably placed in a corner before framing. |
| G6 | **Clean API surface** | `offence_to_win` parameter removed from `apply_tsumego_frame()` and `FrameConfig`. `_choose_scan_order()` deleted. `_choose_flood_seeds()` added. |

## 3. Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Drop board cropping | D33 architectural decision; preserved per research R-25 rejection |
| NG2 | Full Go rules engine | Only BFS connectivity + legality guards needed |
| NG3 | Stochastic/augmented frame | Research interest, not production need |
| NG4 | Influence-based gradient fill | Algorithmic improvement beyond scope |
| NG5 | 2-pass analysis (with/without frame) | GoProblems.com diagnostic feature, not needed for production |
| NG6 | Synthetic komi changes | Off by default, experimental only |

## 4. Constraints

| ID | Constraint |
|----|-----------|
| C1 | Tools must NOT import from `backend/` (project rule) |
| C2 | All frame code lives in `tools/puzzle-enrichment-lab/analyzers/` |
| C3 | Existing legality guards (eye, suicide, puzzle-protect from F1/F2/F8/F10/F20) preserved unchanged |
| C4 | `player_to_move` inviolate rule preserved — never altered by framing |
| C5 | No new external dependencies |
| C6 | Board cropping pipeline (D33) preserved |
| C7 | Prior legality initiative work (20260311-1800-feature-tsumego-frame-legality) preserved |

## 5. Acceptance Criteria (Detailed)

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | `fill_territory()` replaced with BFS flood-fill from seed points | Code review (no linear scan loop) |
| AC2 | Defender fill is a single connected component | Post-fill BFS validation assertion |
| AC3 | Attacker fill + border is a single connected component | Post-fill BFS validation assertion |
| AC4 | No frame stone is isolated (all have ≥1 same-color neighbor) | Post-fill validation assertion |
| AC5 | `offence_to_win` parameter and scaling logic removed | `FrameConfig.offence_to_win` field deleted, `compute_regions()` uses 50/50 split |
| AC6 | `_choose_scan_order()` deleted, `_choose_flood_seeds()` added | Code review |
| AC7 | `normalize_to_tl()` includes axis-swap for edge puzzles | Unit test: edge puzzle normalized to corner |
| AC8 | Validation failure returns original position + WARNING log + diagnostic dump | Integration test with forced failure |
| AC9 | All existing frame tests pass (updated thresholds) + new connectivity tests | pytest green |
| AC10 | `fill_density` metric updated to reflect new algorithm | FrameResult.fill_density still computed |

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Normalize axis-swap changes edge-puzzle test expectations | High | Low | Update affected test assertions — edge puzzles now normalize differently |
| BFS cannot reach all frameable cells (puzzle region as barrier) | Medium | Medium | Multi-seed fallback: scan unreachable cells after primary BFS, add secondary seeds |
| Calibration tests fail due to different fill density | High | Low | Expected; recalibrate density thresholds per AC9 |
| BFS zones grow toward each other and interleave at boundary | Low | Low | Quota-limited BFS stops cleanly; seam width ≈ 1 cell |
| Score-neutral fill changes KataGo evaluation quality | Low | Medium | Post-change calibration run with golden puzzles; A/B comparison |

---

> **See also**:
>
> - [Clarifications](./10-clarifications.md) — User decisions Q1-Q8
> - [Research: Flood-Fill Strategy](../20260312-research-tsumego-frame-flood-fill/15-research.md) — Technical research brief
> - [Prior Initiative: Frame Legality](../20260311-1800-feature-tsumego-frame-legality/) — Closed out correctness fixes
> - [Concepts: Tsumego Frame](../../docs/concepts/tsumego-frame.md) — Current algorithm docs
> - [Architecture: KataGo Enrichment D33](../../docs/architecture/tools/katago-enrichment.md) — Crop-then-frame decision
