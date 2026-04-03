# Clarifications: Tsumego Frame Legality

**Last Updated**: 2026-03-11

---

## Clarification Rounds

### Round 1 — Pre-Charter (from Governance Panel)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should old frame output be preserved for puzzles already enriched? | A: Yes — existing enriched puzzles must not change / B: No — re-enrich all puzzles with new frame / C: Partial — only re-enrich if legality issue detected | B | B — No backward compatibility required. | ✅ resolved |
| Q2 | Should the data audit (RC-1) be a prerequisite for options, or can it run in parallel? | A: Prerequisite / B: Skip audit, fix legality regardless | A | A — Do the data audit using fixtures in `tests/fixtures/scale/` (scale-100, scale-1k, scale-10k) and `tests/fixtures/calibration/`. Run on 100% of available fixture puzzles. | ✅ resolved |
| Q3 | For F3 (turn/ko parity), what should `player_to_move` be set to after framing? | A: Always the original puzzle player (status quo) / B: The attacker (convention) / C: Configurable | A | A — Keep original puzzle player. This is an **inviolate rule**: `player_to_move` from the SGF's PL property must be preserved. The current code already does this correctly (verified: `player_to_move` is preserved at every stage in `tsumego_frame.py`). **Action**: Add explicit code comment documenting this as inviolate. | ✅ resolved |
| Q4 | Should the legality-aware placement actually *play* stones (with captures) or just *validate* before placing? | A: Play — simulate captures / B: Validate — skip illegal placements | B | B — Validate and skip. Start with validation approach. | ✅ resolved |
| Q5 | How much should fill density change? The current zone-based fill is ~65-75% dense. | A: Keep current density / B: Increase to 80-90% / C: Decrease to 50-60% / D: Make density configurable | A | A — **Governance unanimous (6/6): keep emergent density.** On cropped 9x9/13x13 boards, the difference between 65% and 80% is ~5-10 stones (noise, not signal). KataGo’s ownership head produces strong ±1.0 signals from the solid zone blocks regardless. Checkerboard holes serve a structural purpose (liberty safety). No third layer needed. **Condition**: Add density metric logging to the data audit (RC-Q5-1) — compute and report `stones_added / frameable_area` per puzzle to empirically validate. | ✅ resolved |
| Q6 | Should F20 (eye-space respect) be limited to single-point eyes or include more complex eye shapes? | A: Single-point eyes only / B: Two-point eyes as well / C: Full life-and-death eye analysis | A | B — Detect both single-point and two-point eyes. | ✅ resolved |
