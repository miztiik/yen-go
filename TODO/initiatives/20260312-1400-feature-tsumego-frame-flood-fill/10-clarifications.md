# Clarifications: Tsumego Frame Flood-Fill Rewrite

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Last Updated**: 2026-03-12

---

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Backward compatibility & old code removal?** Fill algorithm change produces different frame outputs for every puzzle. | A: No compat — re-enrich all, delete old fill / B: Keep old as fallback / C: Feature flag toggle | A | **A — No backward compat.** Old fill produces provably wrong results. | ✅ resolved |
| Q2 | **Scope: All five remediations (P0-P4)?** P0=flood-fill, P1=border/side, P2=scan order, P3=validation, P4=remove offence_to_win | A: All P0-P4 / B: P0+P2+P3 now / C: P0-P3 now, P4 deferred | A | **A — All five are critical.** Causally linked. | ✅ resolved |
| Q3 | **Score-neutral fill vs attacker advantage?** Panel recommends score-neutral. KaTrain uses 5, ghostban 10. | A: Fully score-neutral (50/50) / B: Minimal bias (2-3) / C: Configurable | A | **A — Fully score-neutral.** Puzzle outcome itself is variance source. | ✅ resolved |
| Q4 | **Flood-fill seed strategy?** | A: Farthest corner from puzzle / B: First free cell adjacent to border (defender side) / C: Nearest edge midpoint | Consult staff engineer | **Consult governance panel.** "No wall is better than bad wall." Reference GoProblems.com images. Also: should cropping be dropped? | ✅ resolved (see Q4-resolution) |
| Q5 | **Post-fill validation: hard fail or warning?** | A: Hard assertion — fail frame, return original position / B: Warning + continue / C: Auto-repair | A | **A — Hard fail.** Log strong warning + log failed frame for analysis/troubleshooting. | ✅ resolved |
| Q6 | **`offence_to_win` API removal — break or deprecate?** | A: Remove parameter entirely / B: Keep but ignore with warning / C: Rename to `territory_bias` | A | **A — Remove entirely.** Only 1 caller, doesn't pass it. Clean removal. | ✅ resolved |
| Q7 | **`_choose_scan_order()` — remove or keep?** | A: Remove (flood-fill makes it irrelevant) / B: Keep for seed corner preference | A | **A — Remove.** Same as Q4 decision — consult first. | ✅ resolved |
| Q8 | **Test calibration: density only, connectivity only, or both?** | A: Update density assertions / B: Replace with connectivity / C: Both | C | **C — Both.** Keep density checks + add connectivity invariants. | ✅ resolved |

---

## Q4-Resolution: Staff Engineer / Governance Consultation

### User Direction
- "No wall is better than bad wall/tsumego frame"
- Reference images: GoProblems.com research view showing clean zone-based fill with separated colors and eyes
- Question: Should board cropping be dropped?

### Research Findings (Feature-Researcher, 2026-03-12)

**Cropping Decision:** **KEEP cropping.** Dropping it violates D33 architectural decision, breaks tree-solver back-translation (28+ tests), and requires Level 5 governance review. Flood-fill achieves all stated goals without dropping crop. The GoProblems.com images show 19×19 because their tool operates on full boards; our pipeline crops to 9/13 first (D33), which is architecturally correct for KataGo's neural net.

**Root Cause Discovery:** The research found the **actual root cause** of disconnected zones is NOT the linear scan itself, but a **missing axis-swap in `normalize_to_tl()`**. KaTrain's normalization includes `if imin < jmin → swap(i,j)` which puts any puzzle into a true corner. Our implementation only flips, never swaps, so edge puzzles stay as edge puzzles and the linear scan bisects the frame.

**Border Wall Decision:** **KEEP border wall.** But seed attacker BFS from border cells (R-22) so attacker fill + border form one connected blob. The user's "no wall is better than bad wall" principle is respected: the wall is kept but the fill that surrounds it is guaranteed connected, eliminating the fragmentation issue.

**Seed Strategy:** After normalize-to-TL-corner (with axis swap fix):
- Defender seed: far corner (bs-1, 0) — top-right
- Attacker seed: border wall cells + far corner (bs-1, bs-1) — bottom-right
- BFS grows from seeds outward; quota-limited per zone

---

## Decision Summary

- Q1:A = No backward compat, delete old fill
- Q2:A = All P0-P4 in scope
- Q3:A = Fully score-neutral fill (50/50 split)
- Q4 = Keep cropping (D33), fix normalize axis-swap, BFS flood-fill with fixed seeds, keep border wall + seed from it
- Q5:A = Hard fail + strong warning + log failed frame
- Q6:A = Remove offence_to_win entirely
- Q7:A = Remove _choose_scan_order(), replace with _choose_flood_seeds()
- Q8:C = Keep density + add connectivity invariants

---

> **See also**:
>
> - [Research: Flood-Fill Strategy](../../initiatives/20260312-research-tsumego-frame-flood-fill/15-research.md) — Full research brief
> - [Concepts: Tsumego Frame](../../docs/concepts/tsumego-frame.md) — Current algorithm docs
