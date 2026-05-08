# perf-50: Gap-Filling Calibration Fixtures

Puzzles sourced from `external-sources/goproblems/sgf/` to fill gaps
identified by the expert review of perf-33 calibration fixtures.

**Status**: Reviewed by 3 domain experts + Governance Panel (Cho Chikun tiebreaker).
See `perf50-expert-review.md` in the enrichment lab root for full review.

## Purpose

The perf-33 calibration set had critical coverage gaps:
- **Zero** high-dan (4d-6d) puzzles
- **Only 1** upper-intermediate puzzle
- **Only 1** seki puzzle
- **No** carpenter's square or dead shape variety
- **No** defensive (to-live) puzzles at intermediate+ level
- **Limited** advanced/expert coverage (single anchor each)

## Fixture Inventory (15 puzzles, post-governance-review)

| # | Fixture | Level | Tags | Quality | Source | Engine Role |
|---|---------|-------|------|---------|--------|-------------|
| 35 | 35_high_dan_ld_corner | high-dan | life-and-death | q:5 | batch-004/5317.sgf | Deep refutation, policy rank 8-12 |
| 36 | 36_high_dan_ld_side | high-dan | life-and-death | q:5 | batch-004/5302.sgf | Non-monotonic convergence |
| 37 | **37_advanced_ld_nose_tesuji** | **advanced** | L&D/tesuji | q:5 | batch-001/1052.sgf | **T1-T2 boundary candidate** |
| 38 | 38_high_dan_tesuji | high-dan | tesuji | q:5 | batch-001/1010.sgf | Clean winrate cliff |
| 39 | 39_expert_ld_deep | expert | life-and-death | q:5 | batch-001/992.sgf | Sparse trigger, referee escalation |
| 40 | 40_expert_ld_corner | expert | life-and-death | q:5 | batch-002/1298.sgf | Benson gate, carpenter's square |
| 41 | **41_expert_ld_double_ko_seki** | expert | **double-ko seki** | **q:3** | batch-002/1282.sgf | Worst-case convergence |
| 42 | 42_upper_int_ld_corner | upper-int | life-and-death | q:5 | batch-006/6733.sgf | Clean T1 anchor |
| 43 | **43_low_dan_ld_side** | **low-dan** | life-and-death | q:5 | batch-006/6710.sgf | Multi-start co-correct |
| 44 | **44_high_dan_ld_live** | **high-dan** | L&D (defensive) | q:4 | batch-006/6685.sgf | Budget exhaustion test |
| 45 | 45_advanced_ld_semeai | advanced | semeai-to-seki | q:5 | batch-002/1258.sgf | CaptureRaceDetector |
| 46 | 46_advanced_ld_deep | advanced | life-and-death | q:5 | batch-002/1497.sgf | CHOICE markers |
| 47 | 47_low_dan_ld_ko | low-dan | L&D/ko | q:5 | batch-001/1024.sgf | Ko/seki disambiguation |
| 48 | 48_low_dan_tesuji | low-dan | tesuji | q:5 | batch-001/1065.sgf | Placement tesuji calibrator |
| 49 | 49_seki_upper_int | upper-int | capturing-race-to-seki | q:4 | batch-001/446.sgf | Seki as goal, ownership divergence |

**Bold** entries were relabeled or metadata-fixed per governance panel rulings.
`50_seki_expert` was **REMOVED** (joseki, not tsumego — same issue as perf-33 #31).

## Governance Panel Changes Applied

| RC | Change | Ruling By |
|----|--------|-----------|
| RC-1 | #37: `high-dan` -> `advanced`, renamed `ld_ko` -> `ld_nose_tesuji` | Cho Chikun: "4 branches, 7-move line = 3k-1k level" |
| RC-2 | #43: `upper-intermediate` -> `low-dan`, renamed | Cho Chikun: "100+ nodes, 8+ move depth = dan level" |
| RC-3 | #50: **REMOVED** (joseki != tsumego, binding precedent from perf-33 #31) | Unanimous |
| RC-4 | #41: renamed to `double_ko_seki`, q:1 -> q:3 | Cho Chikun: "Real expert content, not junk" |
| RC-5 | #44: `upper-intermediate` -> `high-dan`, renamed | Cho Chikun: "Tree 5x larger than expert puzzles" |

## Coverage Matrix (Post-Ruling)

| Level | Anchors | Status |
|-------|---------|--------|
| Upper-intermediate (10k-6k) | #42, #49 | Thin (2 anchors) |
| Advanced (5k-1k) | #37, #45, #46 | Adequate (3 anchors) |
| Low-dan (1d-3d) | #43, #47, #48 | Good (3 anchors) |
| High-dan (4d-6d) | #35, #36, #38, #44 | Strong (4 anchors) |
| Expert (7d-9d) | #39, #40, #41 | Good (3 anchors) |

## Open Gaps (Require Manual Construction or Future Sourcing)

| Gap | Priority | Notes |
|-----|----------|-------|
| Expert seki (genuine shared-liberty reciprocal life) | **CRITICAL** | #50 removed, zero coverage |
| Center L&D (floating group, no wall contact) | HIGH | Zero after 50 puzzles |
| Upper-int defensive (to-live) fixtures | MEDIUM | #44 was meant for this but relabeled |
| Anti-suji / misdirection (obvious move is wrong) | MEDIUM | Zero coverage |
| Bent-four-in-corner (Benson gate boundary) | MEDIUM | #39 exercises peripherally |
| Approach ko (multi-step preparation) | MEDIUM | PV-len override untested |
| Pure snapback (technique-only) | LOW | SnapbackDetector untested |
| Multi-technique combination (throw-in -> net) | LOW | No combos yet |
| Mannen-ko (perpetual ko, seki<->ko boundary) | LOW | Historical edge case |
| 9x9 non-trivial L&D at intermediate | LOW | Testing convenience |

_Source: perf-33 + perf-50 expert reviews + governance panel rulings, 2026-03-22_
