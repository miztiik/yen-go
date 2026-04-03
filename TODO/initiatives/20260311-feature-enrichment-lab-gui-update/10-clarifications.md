# Clarifications — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Last Updated:** 2026-03-11

---

## Q1: Should we replace BesoGo with a different board library?

**Answer:** No. BesoGo stays. It was chosen after evaluating multiple libraries across prior initiatives (GhostBan, custom canvas). Overlays are rendered as a separate SVG layer on top. See Charter NG1.

## Q2: Do we need dark theme changes?

**Answer:** The GUI already uses a dark theme modeled after GoProblems.com. No theme changes needed. See Charter NG2.

## Q3: Should the layout be responsive for mobile/tablet?

**Answer:** No. This is a desktop developer tool for puzzle enrichment analysis. Minimum viewport width is 1280px. See Charter NG5.

## Q4: What happens to the existing SGF textarea in the sidebar?

**Answer:** Stays as-is. A future polish task could collapse it after loading, but it's low priority and not blocking.

## Q5: Score overlays on board — do they show for ALL candidates or just top N?

**Answer:** Top 5-8 candidates only. Showing all would clutter the board. GoProblems shows ~4-5 on the board intersections.

## Q6: PV hover — should it also work on solution tree nodes?

**Answer:** Yes. Hovering a tree node should preview that position on the board. This is secondary to the analysis table hover feature.

## Q7: What coordinate system do score overlays use?

**Answer:** GTP coordinates (A1-T19, skipping I). The analysis table already uses GTP via `gtpDisplay()`. The overlay module maps GTP to board pixel coordinates using BesoGo's SVG layout dimensions.

## Q8: How does the overlay SVG layer avoid blocking clicks on the board?

**Answer:** The overlay SVG uses `pointer-events: none` so all mouse/touch events pass through to BesoGo below. A ResizeObserver keeps the overlay dimensions synced with the board container.

## Q9: What about the policy priors panel — where does it go?

**Answer:** Policy priors bar chart moves to the right panel along with the tree and analysis table. Currently it's dynamically created inside `.besogo-panels` by `board.js`. After the restructure, `#policy-priors` will be pre-placed in the right panel HTML and `initPolicyPanel()` will resolve it by ID as it already does.

## Q10: Does the bridge.py API need changes?

**Answer:** No. The API remains unchanged. The GUI will consume existing SSE events (`board_state`, `analysis`, etc.) more completely. See Charter C4.
