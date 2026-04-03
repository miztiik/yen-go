# Clarifications — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Last Updated:** 2026-03-10

---

## Q1: Should we replace BesoGo with a different board library?

**Answer:** No. BesoGo stays. Overlays are rendered as a separate SVG layer on top. This avoids the risk of another library migration (the project has already gone through multiple GUI failures). See Charter NG1.

## Q2: Do we need dark theme to match GoProblems?

**Answer:** Not in this initiative. Current light theme remains. Dark theme can be a follow-up if desired. See Charter NG2.

## Q3: Should the layout be responsive for mobile/tablet?

**Answer:** No. This is a desktop developer tool. Minimum viewport width is 1280px. See Charter NG5.

## Q4: What happens to the existing SGF textarea in the sidebar?

**Answer:** Stays as-is for now. A future polish task (m3) could collapse it after loading, but it's not blocking.

## Q5: Score overlays on board — do they show for ALL candidates or just top N?

**Answer:** Top 5-8 candidates only. Showing all would clutter the board. GoProblems shows ~4-5 on the board intersections (visible in screenshot: E5, D5, D2, F2 = 4 candidates).

## Q6: PV hover — should it also work on solution tree nodes?

**Answer:** Yes, hovering a tree node should preview that position on the board. This is in T15 scope. The tree branch hovering shows the board state at that node.

## Q7: What coordinate system do score overlays use?

**Answer:** GTP coordinates (A1-T19, skipping I). The analysis table already uses GTP via `gtpDisplay()`. The overlay module maps GTP → board pixel coordinates using BesoGo's SVG layout dimensions.
