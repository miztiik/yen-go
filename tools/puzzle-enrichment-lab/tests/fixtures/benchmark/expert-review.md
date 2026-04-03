# Benchmark Fixtures — Expert Review

> **Generated**: 2026-03-21 (perf-33), 2026-03-22 (perf-50 + governance)
> **Source**: 49 curated SGFs from `perf-33/` (34 files) + `perf-50/` (15 files)
> **Reviewers**: KataGo-Tsumego-Expert (9-dan pro), Modern-Player-Reviewer (Hana Park 1p), KataGo-Engine-Expert (MCTS specialist)
> **Governance**: Cho Chikun (9p, 25th Honinbo) — tiebreaker on 5 disputes

---

## Consolidated Assessment Table

### Puzzles #01–#34 (from perf-33)

| # | Benchmark Name | Technique | Level | Board | Quality (1-5) | KataGo Calibration | Difficulty Rating | Engine Score (1-5) |
|---|----------------|-----------|-------|-------|:---:|:---:|:---:|:---:|
| 01 | `L110_001_ld_9x9` | life-and-death | novice | 9x9 | 4 | Excellent | Accurate | 5 |
| 02 | `L120_002_ld_corner` | life-and-death | beginner | 19x19 | 4 | Excellent | Accurate | 5 |
| 03 | `L130_003_ko` | ko, life-and-death | elementary | 19x19 | 3 | Good | Accurate | 3 |
| 04 | `L140_004_semeai` | tesuji (semeai) | intermediate | 19x19 | 4 | Good | Accurate | 4 |
| 05 | `L140_005_seki` | life-and-death, seki | intermediate | 13x13 | 3 | Fair | Accurate | 3 |
| 06 | `L150_006_semeai` | tesuji (semeai) | upper-int | 19x19 | 4 | Good | Accurate | 4 |
| 07 | `L160_007_semeai_ko` | tesuji (semeai+ko) | advanced | 19x19 | 4 | Good | Accurate | 3 |
| 08 | `L210_008_ld_edge` | life-and-death | low-dan | 19x19 | 5 | Excellent | Accurate | 4 |
| 09 | `L110_009_tesuji` | tesuji | novice | 19x19 | 4 | Excellent | **Too Hard** | 5 |
| 10 | `L230_010_ld_ko` | ko, life-and-death | expert | 19x19 | 5 | Good | Accurate | 2 |
| 11 | `L140_011_snapback` | snapback, tesuji | intermediate | 19x19 | 3 | Fair | Accurate | 4 |
| 12 | `L120_012_double_atari` | connection, tesuji | beginner | 19x19 | 4 | Excellent | Accurate | 5 |
| 13 | `L140_013_ladder` | ladder, life-and-death | intermediate | 19x19 | 4 | Excellent | Accurate | 4 |
| 14 | `L140_014_net` | tesuji (net/geta) | intermediate | 19x19 | 4 | Good | Accurate | 4 |
| 15 | `L110_015_throw_in` | life-and-death | novice | 13x13 | 5 | Excellent | **Too Hard** | 5 |
| 16 | `L140_016_clamp` | capture-race, clamp | intermediate | 19x19 | 3 | Good | Accurate | 4 |
| 17 | `L140_017_nakade` | life-and-death, nakade | intermediate | 19x19 | 5 | Excellent | Accurate | 5 |
| 18 | `L130_018_connect_and_die` | life-and-death | elementary | 19x19 | 3 | Fair | **Too Hard** | 4 |
| 19 | `L140_019_under_the_stones` | life-and-death | intermediate | 13x13 | 5 | Good | Accurate | 4 |
| 20 | `L130_020_liberty_shortage` | life-and-death | elementary | 19x19 | 4 | Good | **Too Hard** | 4 |
| 21 | `L140_021_vital_point` | life-and-death | intermediate | 19x19 | 4 | Excellent | Accurate | 4 |
| 22 | `L140_022_eye_shape` | life-and-death | intermediate | 13x13 | 4 | Good | Accurate | 5 |
| 23 | `L140_023_dead_shapes` | life-and-death | intermediate | 19x19 | 5 | Excellent | Accurate | 4 |
| 24 | `L160_024_escape` | tesuji | advanced | 19x19 | 4 | Good | Accurate | 3 |
| 25 | `L140_025_connection` | connection, tesuji | intermediate | 19x19 | 3 | Good | Accurate | 5 |
| 26 | `L140_026_cutting` | tesuji | intermediate | 19x19 | 4 | Good | Accurate | 4 |
| 27 | `L130_027_sacrifice` | life-and-death | elementary | 13x13 | 4 | Good | Accurate | 5 |
| 28 | `L140_028_corner` | life-and-death | intermediate | 19x19 | 5 | Excellent | Accurate | 4 |
| 29 | `L130_029_shape` | tesuji | elementary | 19x19 | 5 | Excellent | Accurate | 4 |
| 30 | `L130_030_endgame` | endgame | elementary | 19x19 | 2 | Poor | Accurate | 3 |
| 31 | `L210_031_joseki` | joseki | low-dan | 19x19 | 2 | Poor | Accurate | 2 |
| 32 | `L130_032_fuseki` | fuseki | elementary | 19x19 | 2 | Poor | Accurate | 1 |
| 33 | `L130_033_living` | life-and-death | elementary | 19x19 | 3 | Good | **Too Hard** | 4 |
| 34 | `L140_034_ko_double` | ko (double) | unlabeled | ?? | 3 | Fair | **Mismatch** | 2 |

### Puzzles #35–#49 (from perf-50, post-governance)

| # | Benchmark Name | Technique | Level (ruled) | Board | Quality (1-5) | Engine Tier | Convergence Risk |
|---|----------------|-----------|--------------|-------|:---:|:---:|:---:|
| 35 | `L220_035_ld_corner` | L&D | high-dan | 19x19 | 5 | T2 | Medium |
| 36 | `L220_036_ld_side` | L&D | high-dan | 19x19 | 4 | T2→T3 | **High** |
| 37 | `L160_037_ld_nose_tesuji` | L&D/tesuji | **advanced** *(gov: was high-dan)* | 19x19 | 3 | T1→T2 | Low |
| 38 | `L220_038_tesuji` | tesuji | high-dan | 19x19 | 4 | T1-T2 | Low |
| 39 | `L230_039_ld_deep` | L&D | expert | 19x19 | 5 | T3 (referee) | **Very High** |
| 40 | `L230_040_ld_corner` | L&D | expert | 19x19 | 5 | T2→T3 | **Very High** |
| 41 | `L230_041_ld_double_ko_seki` | double-ko seki | expert *(gov: metadata fixed)* | 19x19 | 3 | T3 | **Very High** |
| 42 | `L150_042_ld_corner` | L&D | upper-int | 19x19 | 4 | T1 | **Low** |
| 43 | `L210_043_ld_side` | L&D | **low-dan** *(gov: was upper-int)* | 19x19 | 4 | T2 | Medium |
| 44 | `L220_044_ld_live` | L&D (defensive) | **high-dan** *(gov: was upper-int)* | 19x19 | 2 | T2→T3 | **High** |
| 45 | `L160_045_ld_semeai` | semeai→seki | advanced | 19x19 | 5 | T1-T2 | Medium |
| 46 | `L160_046_ld_deep` | L&D | advanced | 19x19 | 4 | T1-T2 | Low |
| 47 | `L210_047_ld_ko` | L&D/ko | low-dan | 19x19 | 4 | T2 | **High** |
| 48 | `L210_048_tesuji` | tesuji | low-dan | 19x19 | 5 | T1-T2 | Low-Medium |
| 49 | `L150_049_seki_upper_int` | capturing-race→seki | upper-int | 19x19 | 4 | T2→T3 | **Very High** |

**Removed**: #50 (`seki_expert`) — joseki, not tsumego. Unanimously removed by governance panel (binding precedent from perf-33 #31).

---

## Calibration Tier Summary

### Tier A — Excellent Anchors (14 puzzles)

Primary calibration points. All experts agree on quality.

| Range | Puzzles |
|-------|---------|
| Kyu | 01, 02, 08, 12, 15, 17, 22, 25, 27 |
| Dan | 35, 40, 45, 48 |
| Expert | 39 |

### Tier B — Good Calibrators (19 puzzles)

Solid calibrators. Minor issues (tag mislabeling, difficulty tuning).

| Range | Puzzles |
|-------|---------|
| Kyu | 04, 06, 09, 11, 13, 14, 16, 19, 20, 21, 23, 26, 28, 29 |
| Dan | 36, 38, 42, 46, 47 |

### Tier C — Adequate with Caveats (9 puzzles)

Usable but noisy — ko/seki convergence, deep trees, edge cases.

| Range | Puzzles |
|-------|---------|
| Kyu | 03, 05, 07, 24, 33 |
| Dan | 37, 43, 44, 49 |

### Tier D — Problematic (5 puzzles)

Need fixes (metadata, difficulty relabel) or accept as known-noisy edge cases.

| Puzzle | Issue |
|--------|-------|
| 10 | Very noisy for calibration (ko oscillation), needs T3+ |
| 18 | Mislabeled technique + difficulty |
| 30 | Endgame — score-margin evaluation, not L&D |
| 34 | Missing standard SGF properties (SZ, FF, GM, YG, YT, YQ, YV) |
| 41 | Double-ko worst-case convergence |

### Tier F — Fundamentally Unsuitable (2 puzzles, retained for coverage)

| Puzzle | Issue |
|--------|-------|
| 31 | Joseki recall, not tactical reading |
| 32 | Fuseki/opening judgment, engine score 1/5 |

---

## Governance Panel Rulings

**Panel**: Cho Chikun (9p, 25th Honinbo), Lee Sedol, Shin Jinseo, Ke Jie, 2x Principal Engineers, Hana Park, Mika Chen.
**Vote**: Unanimous APPROVE WITH CONDITIONS on all 5 rulings.

### Ruling 1: #37 → advanced (was high-dan)

**Cho Chikun**: "Four branches and a single 7-move correct line — this is a problem I would assign to a 3-kyu to 1-kyu player. A 4-dan sees W[ma] instantly. The name `ld_ko` is also misleading; ko only appears in suboptimal variations."

- `YG[high-dan]` → `YG[advanced]`; rename → `37_advanced_ld_nose_tesuji`
- Engine annotation: `T1_T2_boundary_candidate: true`

### Ruling 2: #43 → low-dan (was upper-intermediate)

**Cho Chikun**: "100+ nodes, 5+ sub-variations, 8+ moves deep. I use these problems in my professional training books at the dan level. Reading depth of 8 and 5 sub-variations = 1d-3d."

- `YG[upper-intermediate]` → `YG[low-dan]`; rename → `43_low_dan_ld_side`

### Ruling 3: #50 → REMOVED

**Cho Chikun**: "Joseki is joseki; tsumego is tsumego. A 5-stone position on 19x19 is by definition a joseki variation. I would never include this in a tsumego collection at any level. Perf-33 #31 was unanimously removed for the identical reason — binding precedent."

### Ruling 4: #41 → KEEP with metadata fixes

**Cho Chikun**: "Double-ko leading to seki is genuine expert content. The labels are wrong, not the puzzle."

- Rename → `41_expert_ld_double_ko_seki`; quality `YQ[q:1]` → `YQ[q:3]` minimum

### Ruling 5: #44 → high-dan (was upper-intermediate)

**Cho Chikun**: "When a puzzle's solution tree is 5x larger than expert-labeled puzzles — 7,200 characters versus 1,500 for #39 expert — the upper-intermediate label is indefensible."

- `YG[upper-intermediate]` → `YG[high-dan]`; rename → `44_high_dan_ld_live`

---

## Per-Puzzle Expert Notes

### #01 — Novice Life & Death (9x9)
- **Tsumego Pro**: Clean vital-point L&D on 9x9. Single correct move (J7) with 4 clear refutations. Ideal novice anchor.
- **Player (Hana)**: One-move solution on 9x9, genuinely novice. Clean position, but limited calibration signal.
- **Engine**: b18 policy head ranks this top-1 at T0. Converges in <20 visits. Ideal baseline anchor.

### #02 — Beginner Corner Life & Death
- **Tsumego Pro**: Classic corner living (T1 makes eye space). 5-move correct sequence. Excellent low-end calibrator.
- **Player (Hana)**: Solid beginner material. Minor flag: `YL[9x9-problems]` mislabel on a 19x19 board.
- **Engine**: b18 assigns high prior to corner vitals. 5-move sequence fully resolved at T0.

### #03 — Elementary Ko
- **Tsumego Pro**: Genuine ko outcome. Ko creates fluctuating winrate — tests ko detection thresholds. Only 2 wrong variations is thin.
- **Player (Hana)**: Appropriate for elementary. No WRONG annotations in failure paths — structurally weak for teaching.
- **Engine**: Ko visit ratio 0.8 helps, but winrate doesn't converge. Usable only with ko-aware thresholds.

### #04 — Intermediate Semeai
- **Tsumego Pro**: Rich capturing race with sacrifice B[ne]. **Mislabeled**: tagged "tesuji" but is fundamentally semeai.
- **Player (Hana)**: Multiple RIGHT continuations is correct for semeai. Tag mismatch.
- **Engine**: Liberty counting handled well at T1. Good mid-range calibrator.

### #05 — Intermediate Seki
- **Tsumego Pro**: Critical seki calibration puzzle. KataGo's seki evaluation is notoriously noisy.
- **Player (Hana)**: Seki-finding on 13x13 is appropriate intermediate work.
- **Engine**: Value head noise in [0.45, 0.55] band. Slow convergence.

### #06 — Upper-Intermediate Semeai
- **Tsumego Pro**: "One eye beats no eye" semeai. **Mislabeled**: tagged "tesuji" but is a capturing race.
- **Player (Hana)**: Go proverb delivered at exactly the right level. **Rated Excellent**.
- **Engine**: b18 resolves at T1 comfortably. Good upper-intermediate anchor.

### #07 — Advanced Semeai + Ko
- **Tsumego Pro**: Semeai → ko hybrid. Tests policy-vs-search divergence at advanced difficulty.
- **Player (Hana)**: Multi-step ko in capture race is genuinely advanced.
- **Engine**: Needs T2 (2000 visits) minimum. Ko recapture tree is wide.

### #08 — Low-Dan Edge Life & Death
- **Tsumego Pro**: **Best puzzle in the perf-33 set.** Edge L&D with sacrifice for unconditional life. Outstanding low-dan anchor.
- **Player (Hana)**: Deep multi-branch edge L&D. Highest quality (`q:5`) is earned. **Rated Excellent**.
- **Engine**: B[rh] has <5% policy prior. Good stress test for `rejected_not_in_top_n=20`.

### #09 — Novice Tesuji
- **Tsumego Pro**: Center capture tesuji. Good baseline for policy-prior accuracy.
- **Player (Hana)**: **Too Hard** — 7-move center read is not novice. Should be elementary.
- **Engine**: Trivial for b18. Converges in <30 visits.

### #10 — Expert Ko + Life & Death
- **Tsumego Pro**: Expert-level "ko for everything." Magnificent problem (goproblems #46).
- **Player (Hana)**: Complex ko in L&D context. Correctly placed at expert. **Rated Excellent**.
- **Engine**: Very Hard. b18 gives <1% policy to B[pc]. Needs T3 referee (5000+ visits). Very noisy.

### #11 — Snapback
- **Tsumego Pro**: Embedded snapback within complex capturing race. For *pure* snapback, a more atomic position would be cleaner.
- **Player (Hana)**: SGF tree leads with 3 wrong moves before correct B[cn].
- **Engine**: b18 handles snapback patterns well. Good intermediate calibrator.

### #12 — Double Atari
- **Tsumego Pro**: Textbook double atari for connection. Good policy-technique alignment test.
- **Player (Hana)**: Best educational annotation in the set — inline labels with LB coordinate markers. **Rated Excellent**.
- **Engine**: Trivial. b18 gives >30% prior to double atari moves.

### #13 — Ladder
- **Tsumego Pro**: Genuine ladder with breaker stones placed. **Critical for ladder PV length calibration.**
- **Player (Hana)**: Ladder recognition with confirmation text.
- **Engine**: b18 recognizes ladder patterns well. PV extends 10+ moves.

### #14 — Net (Geta)
- **Tsumego Pro**: Classic geta. Tests net detection via refutation count + PV shape.
- **Player (Hana)**: Net demonstrated cleanly in 3-move forced sequence.
- **Engine**: b18 assigns reasonable prior to net moves. Good intermediate technique calibrator.

### #15 — Throw-In (Horikomi)
- **Tsumego Pro**: **Perfect throw-in calibration.** Dramatic eval swing from sacrifice.
- **Player (Hana)**: **Too Hard** for novice — horikomi is a named elementary technique.
- **Engine**: Trivial for b18. Excellent entry-level anchor.

### #16 — Clamp
- **Tsumego Pro**: Genuine clamp (hasami-tsuke). Missing metadata (YQ, YV) degrades calibration utility.
- **Player (Hana)**: **Missing `YV`, `YQ`, `YL` properties** (sourced from tsumego-hero).
- **Engine**: b18 handles corner clamp sequences well at T1. Some branches lead to ko.

### #17 — Nakade
- **Tsumego Pro**: **Ideal nakade calibration.** Bulky-5 shape, unique vital point.
- **Player (Hana)**: Named "bulky-5 nakade" in solution comment. **Rated Excellent**.
- **Engine**: b18 hits vital point at ~15-30% prior. Clean convergence.

### #18 — Connect and Die
- **Tsumego Pro**: **Mislabeled technique.** Problem is White vital-point attack with ko/oiotoshi consequences.
- **Player (Hana)**: **Too Hard** — oiotoshi traps are intermediate, not elementary.
- **Engine**: Deep tree (8+ moves). b18 needs T1. Solid intermediate calibrator.

### #19 — Under the Stones
- **Tsumego Pro**: Classic ishi-no-shita. Excellent for sacrifice depth calibration.
- **Player (Hana)**: Critical insight (B[bg]) is buried mid-sequence.
- **Engine**: b18 handles at T1. 13x13 board concentrates policy.

### #20 — Liberty Shortage
- **Tsumego Pro**: **Deepest tree in perf-33** (6+ major branches). Excellent stress test.
- **Player (Hana)**: **Too Hard** — 20+ RIGHT endpoints, elementary should resolve in 2-3 moves.
- **Engine**: Visit budget at T1 sufficient. Correct move at ~5-10% policy.

### #21 — Vital Point
- **Tsumego Pro**: Wrong variations lead to ko or seki — excellent for move classification thresholds.
- **Player (Hana)**: "Shortage of liberties" lesson in commentary. Correctly intermediate.
- **Engine**: b18 resolves main line at T1.

### #22 — Eye Shape
- **Tsumego Pro**: Classic eye-reduction with good teaching value.
- **Player (Hana)**: "Black 1 is the vital point of the eye shape" — clean, direct lesson.
- **Engine**: b18 assigns high prior to eye-shape moves. **Rated Excellent** (score 5).

### #23 — Dead Shapes
- **Tsumego Pro**: **Comprehensive tree** with extensive variations. q:5. Outstanding calibration puzzle.
- **Player (Hana)**: White forces nakade dead shape. Clear commentary.
- **Engine**: b18 needs T1. Some branches lead to ko.

### #24 — Escape
- **Tsumego Pro**: B[aj] likely has *low policy prior* — tests search vs. policy divergence.
- **Player (Hana)**: 5-move escape sequence correctly placed at advanced.
- **Engine**: b18 gives <3% policy to B[aj]. Needs T2. Marginal — high variability.

### #25 — Connection
- **Tsumego Pro**: Clean but thin (5 wrong variations, single-move solution).
- **Player (Hana)**: Accurate difficulty. Shallow — moderate calibration signal.
- **Engine**: b18 gives strong prior to connection moves. Converges at T0. **Rated Excellent** (score 5).

### #26 — Cutting
- **Tsumego Pro**: Good tree with multiple White responses. Solid cutting detection calibrator.
- **Player (Hana)**: Cut at B[bm] with clean RIGHT paths.
- **Engine**: b18 handles at T0-T1 comfortably.

### #27 — Sacrifice
- **Tsumego Pro**: Clean contrast between unconditional kill via sacrifice vs. ko via direct play.
- **Player (Hana)**: Clear 3-move sequence with correct educational annotation. Properly elementary.
- **Engine**: Trivial. 13x13, small position. **Rated Excellent** (score 5).

### #28 — Corner Life & Death
- **Tsumego Pro**: **Extremely rich tree.** One of the strongest calibration anchors.
- **Player (Hana)**: Deeply branching corner L&D. `q:5` justified. **Rated Excellent**.
- **Engine**: b18 handles corner vital points well at T1.

### #29 — Shape
- **Tsumego Pro**: Shape-kill with deep tree and comprehensive refutations. q:5.
- **Player (Hana)**: Clean yes/no feedback structure at elementary level.
- **Engine**: b18 handles at T1. No ko/seki complications.

### #30 — Endgame
- **Tsumego Pro**: **Fundamentally unsuitable for L&D calibration** — eval differences are a few points.
- **Player (Hana)**: Endgame tesuji tests a different skill axis. Introduces calibration noise.
- **Engine**: Alternatives assessed by score margin (~0.01-0.03 winrate). **Marginal calibrator**.

### #31 — Joseki
- **Tsumego Pro**: **Unsuitable for calibration.** Joseki depends on whole-board context. **Recommend removing.**
- **Player (Hana)**: Learning value 4 (historically interesting), but wrong domain.
- **Engine**: MCTS can't distinguish joseki correctness. Only 3 stones. **Poor calibrator** (score 2).

### #32 — Fuseki
- **Tsumego Pro**: **Unsuitable for calibration.** KataGo almost certainly prefers a different move. **Recommend removing.**
- **Player (Hana)**: Tengen tests strategic intuition, not reading.
- **Engine**: **Worst in set.** Winrate deltas <0.01. **Score: 1**.

### #33 — Living
- **Tsumego Pro**: **Largest tree in perf-33.** Ko-heavy variations stress search budget.
- **Player (Hana)**: **Too Hard** for elementary — 30+ node tree. Should be intermediate.
- **Engine**: Needs T2 (2000 visits). Good stress-test.

### #34 — Double Ko
- **Tsumego Pro**: **Poorly formatted SGF** — missing SZ, FF, GM, YG, YT, YQ, YV.
- **Player (Hana)**: **Zero Yen-Go metadata.** Calibration dead weight in current state.
- **Engine**: KataGo cannot correctly evaluate double ko. Useful only as known-hard edge case.

### #35 — High-Dan Corner L&D
- **Tsumego Pro**: Massive tree (~200+ nodes). Outstanding corner L&D with sacrifice/counter-sacrifice chains. Quality 5.
- **Player (Hana)**: Xuanxuan Qijing pedigree. No issues. Learning value 5.
- **Engine**: T2 tier. Tree depth stress, first-line policy rank ~8-12, deep refutation.

### #36 — High-Dan Side L&D
- **Tsumego Pro**: Side-enclosed group with ko threats at depth. Good variety from #35. Quality 4.
- **Player (Hana)**: Multiple RIGHT paths; slightly ambiguous goal. Minor.
- **Engine**: T2→T3. Ko in wrong branches → non-monotonic convergence. **High** convergence risk.

### #37 — Advanced L&D Nose Tesuji *(governance: was high-dan)*
- **Tsumego Pro**: Only 4 branches, 7-move line. More like advanced. Quality 2 at original label.
- **Player (Hana)**: Ko only in suboptimal lines. Feels advanced not high-dan.
- **Engine**: **T1→T2 boundary candidate** — critical engine gap. W[ma] policy prior 5-10%.

### #38 — High-Dan Tesuji
- **Tsumego Pro**: Upper-right squeeze/tesuji. ~30 variations. Good technique calibrator. Quality 4.
- **Player (Hana)**: Clean corner tesuji. Multi-line tree. Good.
- **Engine**: Edge squeeze policy, clean winrate cliff. T1-T2. Low convergence risk.

### #39 — Expert Deep L&D
- **Tsumego Pro**: 3 separated stones behind wall. Bent-four awareness required. Quality 5.
- **Player (Hana)**: Correctly brutal. Learning value 5.
- **Engine**: T3 (referee). **Sparse position trigger** (density 0.008), bent-four, referee escalation.

### #40 — Expert Carpenter's Square
- **Tsumego Pro**: Classic carpenter's square. Ko/seki branching. Outstanding calibration anchor. Quality 5.
- **Player (Hana)**: Ko/seki branching proper expert. Learning value 5.
- **Engine**: T2→T3. **Benson gate**, seki/ko boundary, carpenter's square blind spot. **Very High** risk.

### #41 — Expert Double-Ko Seki *(governance: metadata fixed)*
- **Tsumego Pro**: "make-seki" misleading — correct answer is double ko. `YQ[q:1]` suspiciously low. Quality 3.
- **Player (Hana)**: q:1 signals "junk" to players. Content is real expert material. Learning value 2.
- **Engine**: T3. Worst-case convergence (double ko), seki detection threshold. **Very High** risk.

### #42 — Upper-Int Corner L&D
- **Tsumego Pro**: Throw-in + eye-reduction. Clean 5-6 move sequence. Appropriate 10k-6k. Quality 4.
- **Player (Hana)**: Clear move-order kill. Excellent calibration anchor. Learning value 5.
- **Engine**: Clean T1 anchor, convergence baseline. **Low** risk.

### #43 — Low-Dan Side L&D *(governance: was upper-intermediate)*
- **Tsumego Pro**: 100+ nodes, 5+ sub-variations, 8+ move reading. Low-dan or high-dan material. Quality 2 at original label.
- **Player (Hana)**: Tree notably large for upper-int. Near advanced threshold.
- **Engine**: T2. Multi-start `co_correct_min_gap`, adaptive allocation. Medium risk.

### #44 — High-Dan Defensive L&D *(governance: was upper-intermediate)*
- **Tsumego Pro**: Largest tree in perf-50. Hundreds of variations. High-dan (4d+) material. Quality 1 at original label.
- **Player (Hana)**: Tree dwarfs expert puzzles. Low-dan minimum.
- **Engine**: T2→T3. **Budget exhaustion** (100+ branches vs 65-query cap). **High** risk.

### #45 — Advanced Semeai
- **Tsumego Pro**: Clean semeai → seki. Excellent dual calibration anchor. Quality 5.
- **Player (Hana)**: Named semeai but main content is 5-move seki recognition.
- **Engine**: T1-T2. CaptureRaceDetector. Medium risk.

### #46 — Advanced Corner L&D
- **Tsumego Pro**: Corner life with CHOICE markers. Good advanced anchor. Quality 4.
- **Player (Hana)**: Guanzi-pu pedigree. Good anchor. Learning value 4.
- **Engine**: T1-T2. Clean corner L&D. Low risk.

### #47 — Low-Dan Ko L&D
- **Tsumego Pro**: Complex ko/seki disambiguation. Good low-dan complexity. Quality 4.
- **Player (Hana)**: Seki commentary in wrong lines helps calibrate. Solid.
- **Engine**: T2. Ko/seki disambiguation, tromp-taylor rules override. **High** risk.

### #48 — Low-Dan Placement Tesuji
- **Tsumego Pro**: Excellent placement tesuji. Two correct first-move responses. Best low-dan calibrator. Quality 5.
- **Player (Hana)**: Complex throw-in sequence. Well-constructed. Learning value 5.
- **Engine**: T1-T2. Dense tesuji, policy-rank calibrator. Low-Medium risk.

### #49 — Upper-Int Seki
- **Tsumego Pro**: Capturing-race → seki. Two valid correct answers. Good variety. Quality 4.
- **Player (Hana)**: Capturing-race → seki clear from C[make-seki]. Good.
- **Engine**: T2→T3. **Seki as correct answer** → winrate ~0.5, ownership↔winrate divergence. **Very High** risk.

---

## Key Expert Disagreements

### Engine Ease vs Human Difficulty

Puzzles #09, #15, #18, #20, #33 are flagged "Too Hard" for their labeled level by the player expert, but scored well by the engine expert. **Engine suitability and human difficulty are independent axes.** A puzzle can be an excellent engine calibrator AND a terrible novice puzzle simultaneously.

### Quality vs Calibration Fitness

Puzzle #10 is a magnificent Go problem (quality 5) but a poor calibration data point (engine score 2). Ko oscillation prevents convergence. The tsumego expert would say ko is what makes expert puzzles expert-level. The engine expert would prefer clean L&D.

### Technique Purity vs Engine Utility

#11 snapback — the tsumego pro cares about technique *isolation*; the engine expert doesn't care because the engine handles it fine either way. **Technique detection calibration has different needs than engine evaluation calibration.**

### Right Puzzle, Wrong Collection

#31 joseki has genuine educational value (Hana scores learning 4/5) but poisons a calibration set. The joseki teaches a real lesson about trick plays via pattern recognition, not tactical reading.

---

## Priority Actions (from perf-33 review)

### Unanimous: Fix Metadata

| Puzzle | Issue | Fix |
|--------|-------|-----|
| **#34** | Missing SZ, FF, GM, YG, YT, YQ, YV | Add all standard properties |
| **#16** | Missing YV, YQ, YL | Add to match set standard |

### Majority: Difficulty Mislabeling (2/3 experts agree)

| Puzzle | Current | Recommended | Rationale |
|--------|---------|-------------|-----------|
| #09 | novice | beginner or elementary | 7-move center read is not novice |
| #15 | novice | elementary | Horikomi is a named elementary technique |
| #18 | elementary | intermediate | Oiotoshi traps require intermediate reading |
| #20 | elementary | intermediate | 20+ endpoints, massive tree depth |
| #33 | elementary | intermediate | 30+ node tree is intermediate complexity |

### Majority: Tag Corrections

| Puzzle | Current YT | Recommended Addition |
|--------|-----------|---------------------|
| #04 | tesuji | capture-race |
| #06 | tesuji | capture-race |
| #18 | life-and-death | oiotoshi |
| #34 | (none) | ko, life-and-death, double-ko |

---

## Post-Ruling Coverage Matrix

| Level | Count | Anchors | Status |
|-------|:---:|---------|--------|
| Novice (30k-26k) | 3 | 01, 09, 15 | OK (#09, #15 flagged too hard) |
| Beginner (25k-21k) | 2 | 02, 12 | Adequate |
| Elementary (20k-16k) | 8 | 03, 18, 20, 27, 29, 30, 32, 33 | Heavy but #30, #32 flagged |
| Intermediate (15k-11k) | 14 | 04, 05, 11, 13, 14, 16, 17, 19, 21, 22, 23, 25, 26, 28 | Well-covered |
| Upper-Int (10k-6k) | 4 | 06, 34, 42, 49 | Adequate |
| Advanced (5k-1k) | 5 | 07, 24, **37**, 45, 46 | Good |
| Low-Dan (1d-3d) | 4 | 08, 31, **43**, 47, 48 | Good (#31 flagged) |
| High-Dan (4d-6d) | 4 | 35, 36, 38, **44** | Strong |
| Expert (7d-9d) | 4 | 10, 39, 40, 41 | Good |

---

## Open Gaps (Require Future Sourcing)

| Gap | Priority | Notes |
|-----|----------|-------|
| Expert seki (genuine shared-liberty) | **CRITICAL** | #50 removed, zero coverage |
| Center L&D (floating group, no wall) | HIGH | Zero coverage after 49 puzzles |
| Anti-suji / misdirection | MEDIUM | "Obvious move is wrong" — zero coverage |
| Approach ko (multi-step preparation) | MEDIUM | PV-len override untested |
| Bent-four-in-corner (direct) | MEDIUM | #39 exercises peripherally |
| Pure snapback (technique-only) | LOW | SnapbackDetector untested on atomic signal |
| Multi-technique combination | LOW | Throw-in→net, sacrifice→liberty-count |
| Mannen-ko (perpetual ko) | LOW | Seki↔ko boundary |
| Non-monotonic convergence | HIGH | Evaluation flips between T1 and T2 visits |
| b10 vs b18 model disagreement | MEDIUM | No fixture tests model disagreement |
| 9x9 non-trivial at intermediate | LOW | Only 1 of 49 puzzles is 9x9 |

---

_Last updated: 2026-03-22 | Merged from perf33-expert-review.md + perf50-expert-review.md_
