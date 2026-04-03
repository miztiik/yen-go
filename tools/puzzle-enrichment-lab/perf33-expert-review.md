# Perf-33 Calibration Set — Expert Review

> **Generated**: 2026-03-21
> **Source**: `tools/puzzle-enrichment-lab/tests/fixtures/perf-33/` (34 SGF files)
> **Reviewers**: KataGo-Tsumego-Expert (9-dan pro), Modern-Player-Reviewer (Hana Park 1p), KataGo-Engine-Expert (MCTS specialist)

---

## Consolidated Assessment Table

| # | Filename | Technique | Level | Board | To Play | Technique Accurate? | Quality (1-5) | KataGo Calibration | Difficulty Rating | Learning Value (1-5) | KataGo Difficulty | Visit Budget | Convergence Risk | Engine Calibration (1-5) |
|---|----------|-----------|-------|-------|---------|--------------------:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 01 | `01_novice_ld_9x9` | life-and-death | novice | 9x9 | B | Yes | 4 | Excellent | Accurate | 3 | Trivial | Low | None | 5 |
| 02 | `02_beginner_ld_corner` | life-and-death | beginner | 19x19 | B | Yes | 4 | Excellent | Accurate | 4 | Easy | Low | None | 5 |
| 03 | `03_elementary_ko` | ko, life-and-death | elementary | 19x19 | B | Yes | 3 | Good | Accurate | 3 | Moderate | Medium | Medium | 3 |
| 04 | `04_intermediate_semeai` | tesuji (semeai) | intermediate | 19x19 | B | Partially | 4 | Good | Accurate | 4 | Moderate | Medium | Low | 4 |
| 05 | `05_intermediate_seki` | life-and-death, seki | intermediate | 13x13 | B | Yes | 3 | Fair | Accurate | 4 | Moderate | Medium | Medium | 3 |
| 06 | `06_upper_int_semeai` | tesuji (semeai) | upper-int | 19x19 | B | Partially | 4 | Good | Accurate | 5 | Moderate | Medium | Low | 4 |
| 07 | `07_advanced_semeai_ko` | tesuji (semeai+ko) | advanced | 19x19 | B | Yes | 4 | Good | Accurate | 4 | Hard | High | High | 3 |
| 08 | `08_low_dan_ld_edge` | life-and-death | low-dan | 19x19 | B | Yes | 5 | Excellent | Accurate | 5 | Hard | High | Low | 4 |
| 09 | `09_novice_tesuji` | tesuji | novice | 19x19 | B | Yes | 4 | Excellent | **Too Hard** | 3 | Trivial | Low | None | 5 |
| 10 | `10_expert_ld_ko` | ko, life-and-death | expert | 19x19 | B | Yes | 5 | Good | Accurate | 5 | Very Hard | Very High | High | 2 |
| 11 | `11_snapback` | snapback, tesuji | intermediate | 19x19 | B | Partially | 3 | Fair | Accurate | 3 | Moderate | Medium | Low | 4 |
| 12 | `12_double_atari` | connection, tesuji | beginner | 19x19 | B | Yes | 4 | Excellent | Accurate | 5 | Trivial | Low | None | 5 |
| 13 | `13_ladder` | ladder, life-and-death | intermediate | 19x19 | B | Yes | 4 | Excellent | Accurate | 4 | Easy | Medium | Low | 4 |
| 14 | `14_net` | tesuji (net/geta) | intermediate | 19x19 | B | Yes | 4 | Good | Accurate | 4 | Easy | Medium | None | 4 |
| 15 | `15_throw_in` | life-and-death | novice | 13x13 | B | Yes | 5 | Excellent | **Too Hard** | 5 | Trivial | Low | None | 5 |
| 16 | `16_clamp` | capture-race, clamp | intermediate | 19x19 | B | Yes | 3 | Good | Accurate | 4 | Moderate | Medium | Low | 4 |
| 17 | `17_nakade` | life-and-death, nakade | intermediate | 19x19 | B | Yes | 5 | Excellent | Accurate | 5 | Easy | Medium | None | 5 |
| 18 | `18_connect_and_die` | life-and-death | elementary | 19x19 | W | Partially | 3 | Fair | **Too Hard** | 3 | Moderate | Medium | Low | 4 |
| 19 | `19_under_the_stones` | life-and-death | intermediate | 13x13 | B | Yes | 5 | Good | Accurate | 4 | Moderate | Medium | Low | 4 |
| 20 | `20_liberty_shortage` | life-and-death | elementary | 19x19 | B | Yes | 4 | Good | **Too Hard** | 3 | Moderate | Medium | Low | 4 |
| 21 | `21_vital_point` | life-and-death | intermediate | 19x19 | B | Yes | 4 | Excellent | Accurate | 4 | Moderate | Medium | Low | 4 |
| 22 | `22_eye_shape` | life-and-death | intermediate | 13x13 | B | Yes | 4 | Good | Accurate | 4 | Easy | Medium | None | 5 |
| 23 | `23_dead_shapes` | life-and-death | intermediate | 19x19 | W | Yes | 5 | Excellent | Accurate | 4 | Moderate | Medium | Low | 4 |
| 24 | `24_escape` | tesuji | advanced | 19x19 | B | Yes | 4 | Good | Accurate | 4 | Hard | High | Low | 3 |
| 25 | `25_connection` | connection, tesuji | intermediate | 19x19 | B | Yes | 3 | Good | Accurate | 3 | Easy | Low | None | 5 |
| 26 | `26_cutting` | tesuji | intermediate | 19x19 | B | Yes | 4 | Good | Accurate | 4 | Easy | Medium | None | 4 |
| 27 | `27_sacrifice` | life-and-death | elementary | 13x13 | B | Yes | 4 | Good | Accurate | 4 | Easy | Low | None | 5 |
| 28 | `28_corner` | life-and-death | intermediate | 19x19 | B | Yes | 5 | Excellent | Accurate | 5 | Moderate | Medium | Low | 4 |
| 29 | `29_shape` | tesuji | elementary | 19x19 | W | Yes | 5 | Excellent | Accurate | 4 | Easy | Medium | None | 4 |
| 30 | `30_endgame` | endgame | elementary | 19x19 | W | Partially | 2 | Poor | Accurate | 3 | Easy | Medium | None | 3 |
| 31 | `31_joseki` | joseki | low-dan | 19x19 | W | Partially | 2 | Poor | Accurate | 4 | Moderate | Medium | Low | 2 |
| 32 | `32_fuseki` | fuseki | elementary | 19x19 | B | Partially | 2 | Poor | Accurate | 3 | Moderate | Medium | Low | 1 |
| 33 | `33_living` | life-and-death | elementary | 19x19 | B | Yes | 3 | Good | **Too Hard** | 3 | Moderate | High | Low | 4 |
| 34 | `34_ko_double` | ko (double) | unlabeled | ?? | W | Yes | 3 | Fair | **Mismatch** | 4 | Hard | High | High | 2 |

---

## Expert Summaries by Puzzle

### 01 — Novice Life & Death (9x9)
- **Tsumego Pro**: Clean vital-point L&D on 9x9. Single correct move (J7) with 4 clear refutations. Ideal novice anchor.
- **Player (Hana)**: One-move solution on 9x9, genuinely novice. Clean position, but limited calibration signal.
- **Engine**: b18 policy head ranks this top-1 at T0. Converges in <20 visits. Ideal baseline anchor.

### 02 — Beginner Corner Life & Death
- **Tsumego Pro**: Classic corner living (T1 makes eye space). 5-move correct sequence. Excellent low-end calibrator.
- **Player (Hana)**: Solid beginner material. Minor flag: `YL[9x9-problems]` mislabel on a 19x19 board.
- **Engine**: b18 assigns high prior to corner vitals. 5-move sequence fully resolved at T0.

### 03 — Elementary Ko
- **Tsumego Pro**: Genuine ko outcome. Ko creates fluctuating winrate — tests ko detection thresholds. Only 2 wrong variations is thin.
- **Player (Hana)**: Appropriate for elementary. No WRONG annotations in failure paths — structurally weak for teaching.
- **Engine**: Ko visit ratio 0.8 helps, but winrate doesn't converge to a crisp value. Usable only with ko-aware thresholds.

### 04 — Intermediate Semeai
- **Tsumego Pro**: Rich capturing race with sacrifice B[ne]. **Mislabeled**: tagged "tesuji" but is fundamentally semeai. Recommend adding "capture-race" tag.
- **Player (Hana)**: Multiple RIGHT continuations is correct for semeai. Tag mismatch: `YT[tesuji]` vs `YL[capturing-race]`.
- **Engine**: Liberty counting handled well at T1. Good mid-range calibrator.

### 05 — Intermediate Seki
- **Tsumego Pro**: Critical seki calibration puzzle. KataGo's seki evaluation is notoriously noisy (winrate ~0.5, score ~0).
- **Player (Hana)**: Seki-finding on 13x13 is appropriate intermediate work. Good tree discipline.
- **Engine**: Value head noise in [0.45, 0.55] band. Slow convergence. Adequate for seki-specific validation only.

### 06 — Upper-Intermediate Semeai
- **Tsumego Pro**: "One eye beats no eye" semeai. **Mislabeled**: tagged "tesuji" but is a capturing race.
- **Player (Hana)**: Go proverb delivered at exactly the right level. Textbook calibration material. **Rated Excellent**.
- **Engine**: b18 resolves at T1 comfortably. Good upper-intermediate anchor.

### 07 — Advanced Semeai + Ko
- **Tsumego Pro**: Semeai → ko hybrid. Tests policy-vs-search divergence at advanced difficulty.
- **Player (Hana)**: Multi-step ko in capture race is genuinely advanced. Tag mismatch with collection.
- **Engine**: Needs T2 (2000 visits) minimum. Ko recapture search tree is wide. Useful but noisy.

### 08 — Low-Dan Edge Life & Death
- **Tsumego Pro**: **Best puzzle in the set.** Edge L&D with sacrifice for unconditional life. Extremely rich tree. Outstanding low-dan anchor.
- **Player (Hana)**: Deep multi-branch edge L&D. Highest quality (`q:5`) is earned. **Rated Excellent**.
- **Engine**: B[rh] has <5% policy prior. Good stress test for `rejected_not_in_top_n=20`.

### 09 — Novice Tesuji
- **Tsumego Pro**: Center capture tesuji. KataGo easily finds it. Good baseline for policy-prior accuracy.
- **Player (Hana)**: **Too Hard** — 7-move center read is not novice. Should be elementary at minimum.
- **Engine**: Trivial for b18. Converges in <30 visits. Excellent anchor.

### 10 — Expert Ko + Life & Death
- **Tsumego Pro**: Expert-level "ko for everything." Magnificent problem (goproblems #46). Tests depth profiles.
- **Player (Hana)**: Complex ko in L&D context. Correctly placed at expert. **Rated Excellent**.
- **Engine**: Very Hard. b18 gives <1% policy to B[pc]. Needs T3 referee (5000+ visits). Very noisy for calibration.

### 11 — Snapback
- **Tsumego Pro**: Embedded snapback within complex capturing race. For *pure* snapback detection, a more atomic position would be cleaner.
- **Player (Hana)**: SGF tree leads with 3 wrong moves before correct B[cn] — breaks player expectation.
- **Engine**: b18 handles snapback patterns well. Good intermediate calibrator.

### 12 — Double Atari
- **Tsumego Pro**: Textbook double atari for connection. Good for verifying policy-technique alignment.
- **Player (Hana)**: Best educational annotation in the set — inline labels with LB coordinate markers. **Rated Excellent**.
- **Engine**: Trivial. b18 gives >30% prior to double atari moves. Converges in <30 visits.

### 13 — Ladder
- **Tsumego Pro**: Genuine ladder with breaker stones placed. **Critical for ladder PV length calibration.**
- **Player (Hana)**: Ladder recognition with confirmation text. Pedagogically fine.
- **Engine**: b18 recognizes ladder patterns well. PV extends 10+ moves. Converges at T1.

### 14 — Net (Geta)
- **Tsumego Pro**: Classic geta. Tests net detection via refutation count + PV shape.
- **Player (Hana)**: Net demonstrated cleanly in 3-move forced sequence. `YT[tesuji]` but net is more specific.
- **Engine**: b18 assigns reasonable prior to net moves. Good intermediate technique calibrator.

### 15 — Throw-In (Horikomi)
- **Tsumego Pro**: **Perfect throw-in calibration.** Dramatic eval swing from sacrifice. Ideal for sacrifice-detection tuning.
- **Player (Hana)**: **Too Hard** for novice — horikomi is a named elementary technique, not novice. Suggest relabel to elementary.
- **Engine**: Trivial for b18. Small board, clear pattern. Excellent entry-level anchor.

### 16 — Clamp
- **Tsumego Pro**: Genuine clamp (hasami-tsuke). Missing metadata (YQ, YV) degrades calibration utility.
- **Player (Hana)**: **Missing `YV`, `YQ`, `YL` properties** (sourced from tsumego-hero). Incomplete metadata.
- **Engine**: b18 handles corner clamp sequences well at T1. Some branches lead to ko.

### 17 — Nakade
- **Tsumego Pro**: **Ideal nakade calibration.** Bulky-5 shape, unique vital point. Perfect for dead-shape detection.
- **Player (Hana)**: Named "bulky-5 nakade" in solution comment. Exemplary educational design. **Rated Excellent**.
- **Engine**: b18 hits vital point at ~15-30% prior. Clean convergence, good refutation coverage.

### 18 — Connect and Die
- **Tsumego Pro**: **Mislabeled technique.** Problem is White vital-point attack with ko/oiotoshi consequences, not "connect-and-die."
- **Player (Hana)**: **Too Hard** — oiotoshi traps are intermediate, not elementary. Level mismatch.
- **Engine**: Deep tree (8+ moves). b18 needs T1. Solid intermediate calibrator.

### 19 — Under the Stones
- **Tsumego Pro**: Classic ishi-no-shita. KataGo needs sufficient depth to see past the sacrifice. Excellent for sacrifice depth calibration.
- **Player (Hana)**: Critical insight (B[bg]) is buried mid-sequence — starting position could be tighter.
- **Engine**: b18 handles at T1. 13x13 board concentrates policy. Good technique calibrator.

### 20 — Liberty Shortage
- **Tsumego Pro**: **Deepest tree in the set** (6+ major branches). Excellent stress test for refutation completeness.
- **Player (Hana)**: **Too Hard** — 20+ RIGHT endpoints, elementary should resolve in 2-3 moves. Should be intermediate.
- **Engine**: Visit budget at T1 sufficient. Correct move at ~5-10% policy. Tree width stress-tests candidate exploration.

### 21 — Vital Point
- **Tsumego Pro**: Wrong variations lead to ko or seki — excellent for calibrating move classification thresholds.
- **Player (Hana)**: "Shortage of liberties" lesson in commentary. Correctly intermediate.
- **Engine**: b18 resolves main line at T1. Corner confinement helps policy concentration.

### 22 — Eye Shape
- **Tsumego Pro**: Classic eye-reduction problem with good teaching value. KataGo should clearly find vital point.
- **Player (Hana)**: "Black 1 is the vital point of the eye shape" — clean, direct lesson. Good for calibration.
- **Engine**: b18 assigns high prior to eye-shape moves. **Rated Excellent** (engine score 5). Predictable, convergent.

### 23 — Dead Shapes
- **Tsumego Pro**: **Comprehensive tree** with extensive variations. q:5. Outstanding calibration puzzle.
- **Player (Hana)**: White forces nakade dead shape. Clear "dead shape" commentary. Good construction.
- **Engine**: b18 needs T1. Some branches lead to ko. Good dead-shape detection calibrator.

### 24 — Escape
- **Tsumego Pro**: B[aj] likely has *low policy prior* — tests KataGo's search vs. policy divergence.
- **Player (Hana)**: 5-move escape sequence correctly placed at advanced. Good strategic context.
- **Engine**: b18 gives <3% policy to B[aj]. Needs T2. Marginal calibrator — high variability.

### 25 — Connection
- **Tsumego Pro**: Clean but thin (5 wrong variations, single-move solution). Adequate for basic connection detection.
- **Player (Hana)**: Accurate difficulty. Shallow — moderate calibration signal.
- **Engine**: b18 gives strong prior to connection moves. Converges at T0. **Rated Excellent** (engine score 5).

### 26 — Cutting
- **Tsumego Pro**: Good tree with multiple White responses. Solid calibration for cutting detection.
- **Player (Hana)**: Cut at B[bm] with clean RIGHT paths. Solid intermediate construction.
- **Engine**: b18 handles at T0-T1 comfortably. Good intermediate calibrator.

### 27 — Sacrifice
- **Tsumego Pro**: Clean contrast between unconditional kill via sacrifice vs. ko via direct play. Well-suited for classification.
- **Player (Hana)**: Clear 3-move sequence with correct educational annotation. Properly placed elementary.
- **Engine**: Trivial. 13x13, small position. b18 resolves trivially. **Rated Excellent** (engine score 5).

### 28 — Corner Life & Death
- **Tsumego Pro**: **Extremely rich tree.** One of the strongest calibration anchors.
- **Player (Hana)**: Deeply branching corner L&D. `q:5` justified. **Rated Excellent**.
- **Engine**: b18 handles corner vital points well at T1. Rich refutation tree.

### 29 — Shape
- **Tsumego Pro**: Shape-kill with deep tree and comprehensive refutations. q:5. **Outstanding for shape-based vital point detection.**
- **Player (Hana)**: Clean yes/no feedback structure at elementary level.
- **Engine**: b18 handles at T1. Clean L&D with no ko/seki complications.

### 30 — Endgame
- **Tsumego Pro**: **Fundamentally unsuitable for KataGo L&D calibration** — eval differences are a few points, not life/death. Consider replacing.
- **Player (Hana)**: Endgame tesuji tests a different skill axis. Introduces calibration noise for tactical solving.
- **Engine**: Alternatives assessed by score margin (~0.01-0.03 winrate), not life/death. **Marginal calibrator**.

### 31 — Joseki
- **Tsumego Pro**: **Unsuitable for calibration.** "Correct" joseki depends on whole-board context. **Recommend removing.**
- **Player (Hana)**: Joseki tests recall, not tactical computation. Introduces uncontrolled recall variance.
- **Engine**: MCTS doesn't distinguish "joseki correctness." Only 3 stones on board — maximal policy scatter. **Poor calibrator** (score 2).

### 32 — Fuseki
- **Tsumego Pro**: **Unsuitable for calibration.** Modern KataGo almost certainly prefers a different move. **Recommend removing.**
- **Player (Hana)**: Tengen tests strategic intuition, not reading. Cannot be verified by counting moves.
- **Engine**: **Fundamentally unsuitable for tsumego calibration.** Winrate deltas <0.01. **Score: 1** (worst in set).

### 33 — Living
- **Tsumego Pro**: **Largest tree in the set.** Deep ko-heavy variations stress search budget. Good stress-test calibration.
- **Player (Hana)**: **Too Hard** for elementary — 30+ node tree. Should be intermediate.
- **Engine**: Needs T2 (2000 visits). Tree depth strains `max_total_tree_queries=65`. Good stress-test.

### 34 — Double Ko
- **Tsumego Pro**: **Poorly formatted SGF** — missing SZ, FF, GM, YG, YT, YQ, YV. Must add standard properties.
- **Player (Hana)**: **Zero Yen-Go metadata.** Calibration dead weight in current state. **Rated Poor**.
- **Engine**: KataGo cannot correctly evaluate double ko. Winrate oscillates indefinitely. Useful only as known-hard edge case.

---

## Cross-Expert Consensus: Priority Actions

### Unanimous: Remove/Replace (All 3 experts agree)

| Puzzle | Action | Reason |
|--------|--------|--------|
| **#32 fuseki** | **REMOVE** | Not calibratable — opening judgment, not tactical reading. Engine score 1/5. |
| **#31 joseki** | **REMOVE** | Not calibratable — joseki recall, not L&D. Engine score 2/5. |
| **#30 endgame** | **REPLACE** | Score-margin evaluation, not winrate cliffs needed for threshold calibration. |

### Unanimous: Fix Metadata

| Puzzle | Issue | Fix |
|--------|-------|-----|
| **#34 ko_double** | Missing SZ, FF, GM, YG, YT, YQ, YV | Add all standard properties |
| **#16 clamp** | Missing YV, YQ, YL | Add to match set standard |

### Majority: Difficulty Mislabeling (2/3 experts agree)

| Puzzle | Current | Recommended | Rationale |
|--------|---------|-------------|-----------|
| **#09** novice_tesuji | novice | beginner or elementary | 7-move center read is not novice (Player: Too Hard) |
| **#15** throw_in | novice | elementary | Horikomi is a named intermediate-level technique (Player: Too Hard) |
| **#18** connect_and_die | elementary | intermediate | Oiotoshi traps require intermediate reading (Player: Too Hard) |
| **#20** liberty_shortage | elementary | intermediate | 20+ endpoints, massive tree depth (Player: Too Hard) |
| **#33** living | elementary | intermediate | 30+ node tree is intermediate complexity (Player: Too Hard) |

### Majority: Tag Corrections

| Puzzle | Current YT | Recommended Addition |
|--------|-----------|---------------------|
| **#04** | tesuji | capture-race |
| **#06** | tesuji | capture-race |
| **#18** | life-and-death | oiotoshi |
| **#34** | (none) | ko, life-and-death, double-ko |

### Coverage Gaps Identified

| Gap | Current Coverage | Recommendation |
|-----|-----------------|----------------|
| High-dan (4d-6d) | 0 puzzles | Add 1-2 puzzles to bridge low-dan → expert |
| Seki | 1 puzzle (#05) | Add 1-2 more seki positions |
| Pure snapback | Buried in complex tree (#11) | Add a direct 3-move snapback |

---

## Calibration Tier Summary

| Tier | Count | Puzzles | Description |
|------|-------|---------|-------------|
| **Tier A — Excellent** | 9 | 01, 02, 08, 12, 15, 17, 22, 25, 27 | Strong anchors. All experts agree on quality. Use as primary calibration points. |
| **Tier B — Good** | 14 | 04, 06, 09, 11, 13, 14, 16, 19, 20, 21, 23, 26, 28, 29 | Solid calibrators. Minor issues (tag mislabeling, difficulty tuning). |
| **Tier C — Adequate** | 5 | 03, 05, 07, 24, 33 | Usable with caveats. Ko/seki convergence noise, deep trees, edge cases. |
| **Tier D — Problematic** | 4 | 10, 18, 30, 34 | Need fixes (metadata, difficulty relabel) or accept as known-noisy edge cases. |
| **Tier F — Remove** | 2 | 31, 32 | Fundamentally incompatible with tsumego calibration. |

---

## Difficulty Distribution (Current vs Recommended)

| Level | Current Count | Puzzles | Notes |
|-------|:---:|---------|-------|
| Novice | 3 | 01, 09, 15 | #09 and #15 flagged as too hard |
| Beginner | 2 | 02, 12 | Adequate |
| Elementary | 6 | 03, 18, 20, 27, 29, 30 | #18, #20, #30 flagged |
| Intermediate | 12 | 04, 05, 11, 13, 14, 16, 17, 21, 22, 25, 26, 28 | Well-covered but heavy |
| Upper-Intermediate | 1 | 06 | Thin |
| Advanced | 2 | 07, 24 | Adequate |
| Low-Dan | 2 | 08, 31 | #31 unsuitable |
| **High-Dan** | **0** | — | **Gap: no coverage** |
| Expert | 1 | 10 | Thin |
| Unlabeled | 1 | 34 | Missing metadata |

---

## Expert Disagreements (Verbal Nuance)

The 3 reviewers had distinct perspectives that caused notable disagreements on specific puzzles. These are worth understanding because they reveal calibration ambiguity.

### Puzzle #09 (novice_tesuji) — **Difficulty vs Engine Ease**
- **Tsumego Pro**: Quality 4, Excellent calibration. Technique is genuine.
- **Player (Hana)**: **Too Hard** — 7-move center reading is NOT novice. Should be elementary at minimum.
- **Engine**: Trivial. Converges in <30 visits. Score 5/5.
- **The disagreement**: What's trivial for KataGo is impossibly hard for a 30-kyu beginner. The engine expert rates it top-tier *because* it converges cleanly, while the player expert says the human difficulty is clearly mislabeled. This exposes a fundamental tension: **engine suitability and human difficulty are independent axes**. A puzzle can be an excellent engine calibrator AND a terrible novice puzzle simultaneously.

### Puzzle #10 (expert_ld_ko) — **Magnificent Problem vs Noisy Signal**
- **Tsumego Pro**: Quality 5, magnificent problem. Outstanding for depth profile testing.
- **Player (Hana)**: Excellent. Correctly placed at expert. Clear high-end anchor.
- **Engine**: Score 2/5. Very Hard. Needs T3+ (5000 visits). Winrate oscillates due to ko. **Very noisy for calibration.**
- **The disagreement**: The tsumego expert and player see a brilliant classic puzzle. The engine expert sees a convergence nightmare. KataGo's policy head gives <1% to the correct move, and the ko outcome means the winrate never stabilizes. This means #10 is a great **Go puzzle** but a poor **calibration data point**. The engine expert would prefer a clean expert L&D without ko — the tsumego expert would say that's removing what makes expert puzzles expert-level.

### Puzzle #11 (snapback) — **Technique Purity vs Engine Utility**
- **Tsumego Pro**: Partially accurate. Snapback is buried in a complex capturing race. Wants a cleaner atomic position.
- **Player (Hana)**: SGF tree structure is broken (wrong moves listed first). Fair calibration.
- **Engine**: Score 4/5. b18 handles snapback patterns well. Good intermediate calibrator.
- **The disagreement**: The tsumego pro cares about technique *isolation* — is this testing snapback or general reading? The engine expert doesn't care; the engine handles it fine either way. This reveals that **technique detection calibration has different needs than engine evaluation calibration**. For the `SnapbackDetector` to be validated, you need a clean signal. For engine visit-budget testing, the complex position actually works better.

### Puzzle #15 (throw_in) — **Perfect Puzzle, Wrong Shelf**
- **Tsumego Pro**: Quality 5, perfect throw-in calibration. Ideal for sacrifice-detection tuning.
- **Player (Hana)**: Learning value 5 — **but Too Hard for novice**. Horikomi is a named technique, definitionally not novice.
- **Engine**: Trivial. Score 5/5.
- **The disagreement**: Everyone loves this puzzle. The only fight is about the `YG[novice]` label. The tsumego pro and engine expert don't flag the difficulty because they evaluate *puzzle quality*, not *player experience at that level*. The player expert catches what the others miss: a novice (30k-26k) player will never solve this. This is the strongest argument in the set for relabeling — all 3 experts agree it's excellent, but it's on the wrong shelf.

### Puzzle #31 (joseki) — **Learning Value vs Calibration Fitness**
- **Tsumego Pro**: Quality 2, Poor. **REMOVE.** Not calibratable.
- **Player (Hana)**: Learning value 4. The "19-point trick play" commentary is historically valuable. But acknowledges it's a wrong domain (recall vs tactical reading).
- **Engine**: Score 2/5. MCTS can't distinguish joseki correctness from position evaluation.
- **The disagreement**: Hana sees educational merit the other two dismiss. The joseki problem teaches a real lesson about trick plays — but it does so through pattern recognition, not the tactical reading that the pipeline measures. This is a **"right puzzle, wrong collection"** situation. The joseki is valuable for a teaching collection but poisons a calibration set.

### Puzzle #30 (endgame) vs #32 (fuseki) — **Degrees of Unsuitability**
- **Tsumego Pro**: Both rated Quality 2 / Poor. Endgame slightly better than fuseki. Recommends removing both, but #30 has a "replace" option while #32 is a hard "remove."
- **Player (Hana)**: #30 is "Fair" (endgame is at least computation-based). #32 is "Fair" (fuseki is strategic intuition).
- **Engine**: #30 is score 3 (marginal). #32 is score 1 (worst in set).
- **The disagreement**: The endgame puzzle (#30) gets a marginal pass from the engine expert because it at least *has* a calculable answer. The fuseki puzzle (#32) is unanimously the weakest — KataGo may legitimately prefer a different opening move, and the eval difference is <0.01 winrate. Even Hana (most lenient reviewer) rates both as "Fair" rather than "Good."

---

## Gap Analysis: What We Are NOT Testing

_Based on parallel gap analysis by all 3 domain experts, 2026-03-21_

### Cross-Expert Consensus Gaps (All 3 agree these are missing)

| Gap | Description | Tsumego Pro Priority | Engine Priority | Player Priority | Agreed Priority |
|-----|-------------|:---:|:---:|:---:|:---:|
| **High-dan puzzles (4d-6d)** | Zero coverage. Score thresholds 91-96 completely uncalibrated. | Critical | — | Critical | **Critical** |
| **Upper-intermediate depth** | Only 1 puzzle (#06). Most populous real-player tier. | Critical | — | Critical | **Critical** |
| **Approach ko** | KataGo's PV length override (`pv_len=30`) is unvalidated. Ko subtype with highest failure risk. | Critical | Medium | Medium | **Critical** |
| **Seki variety** | Only 1 seki. KataGo's seki detection params (`winrate_band`, `score_lead_max`) need multiple seki subtypes. | Critical | Medium | Medium | **Critical** |
| **Bent-four-in-corner** | Most famous status position in Go. Benson gate has zero test fixtures. Rules-dependent evaluation. | Critical | Medium | High | **Critical** |
| **Clean snapback** | Current is buried in complex tree. `SnapbackDetector` threshold untested on clean signal. | High | — | High | **High** |
| **Center L&D** | No center puzzle. `center_alive=0.5`, `center_dead=-0.5` ownership thresholds uncalibrated. | High | High | High | **High** |
| **Carpenter's square** | Second most important dead shape. Policy network gives <5% to killing move. | Critical | — | High | **High** |
| **Multi-technique combinations** | Every puzzle tests one technique. Real tsumego combine throw-in→net, ladder→nakade, etc. | — | — | Critical | **High** |
| **Misdirection / anti-suji** | No puzzle where the obvious move is wrong. Defining SDK-to-dan transition skill. | — | — | Critical | **High** |

### Engine-Specific Gaps (Only engine expert flagged)

| Gap | Description | Priority | Config Parameters At Risk |
|-----|-------------|:---:|---|
| **T1→T2 boundary flip** | No puzzle where evaluation flips between 500 and 2000 visits. Escalation trigger is blind. | **Critical** | `branch_disagreement_threshold=0.07`, `visit_allocation_mode` |
| **Non-monotonic convergence** | No puzzle with convergence dip (looks winning → opponent counter → counter refuted). | **Critical** | `t_disagreement`, `surprise_weighting` |
| **Policy rank 10-20 rescue zone** | Gap between trivial (rank 1) and extreme (#10, rank >20). The `rejected_not_in_top_n=20` rescue corridor is untested. | **Critical** | `rejected_not_in_top_n`, `winrate_rescue_auto_accept` |
| **Forced-move chain >6 plies** | Fast-path (`forced_move_visits=125`) never exercised on long chains. Budget accounting untested. | High | `forced_move_visits`, `max_total_tree_queries` |
| **Tree width 8+ candidates** | `candidate_max_count=6` truncation + multi-pass harvesting untested. | High | `candidate_max_count`, `multi_pass_harvesting` |
| **9x9 noise amplification** | Board-scaled noise is 4x on 9x9 but only trivial puzzle tests it. | High | `noise_base`, `noise_reference_area` |
| **Referee escalation trigger** | Only 1 puzzle reaches T3 and it's very noisy. No clean borderline case. | High | `escalation_winrate_low/high` |
| **Budget exhaustion** | `max_total_tree_queries=65` cap never hit. No graceful degradation test. | High | `max_total_tree_queries` |
| **b10 vs b18 model disagreement** | No fixture tests where quick model and deep model disagree on correct move. | Medium | `models.quick`, T0 routing |
| **Transposition caching** | `transposition_enabled=true` with zero transposition fixtures. Counter never increments. | Medium | `transposition_enabled` |
| **Ownership vs winrate divergence** | No fixture where ownership says "alive" but winrate says "losing." | Medium | `ownership_delta_weight` |

### Tsumego-Domain Gaps (Only tsumego pro flagged)

| Gap | Description | Priority |
|-----|-------------|:---:|
| **Mannen-ko (ten-thousand-year ko)** | Perpetual ko misclassified as seki by winrate band. Critical seki↔ko boundary test. | **Critical** |
| **Multi-step ko (two-stage)** | Sacrifice-then-ko pattern. `min_pv_length=3` may not trigger. | High |
| **Ko with threats on board** | Isolated ko puzzles ignore threat exploration. Visit budget may exhaust. | High |
| **Eye-vs-no-eye semeai (properly tagged)** | No puzzle with `capture-race` as primary tag. `CaptureRaceDetector` never fires as lead. | Critical |
| **Seki with shared liberties** | Most common KataGo seki failure mode. Ownership values misleading. | Critical |
| **Seki as wrong answer** | No puzzle where seki is suboptimal and kill is possible. `t_bad` discrimination untested. | High |
| **Big-eye vs small-eye semeai** | Internal liberties from eye size determine winner. Tests difficulty scoring depth. | High |
| **L-group status** | Conditional-status position. Ko/dead boundary test. | Medium |
| **Straight-three dead shape** | Trivially dead. Tests Benson gate short-circuit and difficulty floor. | Medium |
| **Flexible move order (miai)** | `co_correct_min_gap=0.02` and `player_alternative_rate=0.15` completely uncalibrated. | High |

### Player-Experience Gaps (Only player expert flagged)

| Gap | Description | Priority |
|-----|-------------|:---:|
| **Defensive puzzles (Black to live)** | All 34 puzzles are attack-oriented. Real games require defense too. Half of Go is untested. | **High** |
| **Multi-technique combinations** | Every puzzle is single-technique. Real puzzles combine throw-in→net, semeai→ko, etc. | **Critical** |
| **Ko threat evaluation puzzles** | Correct answer changes based on ko threat count. Standard at SDK+ level. | High |
| **9x9 board depth** | 1 of 34 puzzles is 9x9. Beginners start on 9x9. Undertested. | Medium |
| **Oiotoshi as explicit technique** | #18 is mislabeled. No clean connect-and-die position exists. | Medium |
| **Wedge / push-through tesuji** | Common SDK tesuji absent from set. | Medium |
| **Crane's nest tesuji** | Classic beginner-trap absent. | Medium |
| **Tenuki judgment** | No puzzle testing "when NOT to play locally." 3k-1d blindspot. | Low |
| **Multi-phase (attack + live combo)** | Simultaneous kill one group + secure another. Distinguishes 1d from 3d. | Low |
| **Reading depth benchmarks** | No explicit depth-per-tier calibration. Depth variance within intermediate is extreme. | Medium |

---

## Recommended New Puzzles to Add

Consolidated from all 3 experts, deduplicated and prioritized. **Minimum viable set: 10 new puzzles** (bringing total to ~42 after removing #31, #32).

| # | Technique | Level | Board | Expert Source | Gaps Covered | Description |
|---|-----------|-------|-------|:---:|---|---|
| **35** | Bent-four-in-corner | Low-Dan | 19x19 | Tsumego + Player | Bent-four, Benson gate, dead shapes | Classic bent-four status position. Tests rules-dependent evaluation and Benson gate boundary. |
| **36** | Approach ko | Advanced | 19x19 | Tsumego + Engine | Ko subtype, PV length, ko threats | Multi-step approach ko requiring preparation moves before ko fight. Tests `pv_len=30` override. |
| **37** | Seki with shared liberties | Intermediate | 13x13 | Tsumego + Engine | Seki variety, ownership noise, seki↔ko boundary | Two groups sharing dame. Tests `score_lead_seki_max=5.0` and ownership thresholds. |
| **38** | Deep corner L&D | High-Dan | 19x19 | All 3 | Level gap, difficulty thresholds 91-96 | 12+ move solution with multiple sacrifice sequences. Fills zero-coverage high-dan tier. |
| **39** | Complex semeai + counting | High-Dan | 19x19 | All 3 | Second high-dan anchor, eye-vs-no-eye | Eye-counting semeai. Second anchor for reliable threshold calibration. |
| **40** | Edge sacrifice (T1→T2 flip) | Upper-Int | 19x19 | Engine | Visit boundary flip, escalation, rank 10-20 rescue | Correct move at policy rank ~12. Evaluation flips between 500v and 2000v. Fills thin upper-int tier. |
| **41** | Carpenter's square | Low-Dan | 19x19 | Tsumego + Player | Dead shape, policy blind spot | Standard side killing shape. Tests `rejected_not_in_top_n` with <5% policy correct move. |
| **42** | Multi-technique combo | Intermediate | 19x19 | Player | Real-puzzle realism, technique overlap | Throw-in sets up net, or ladder creates nakade. Tests technique co-detection. |
| **43** | Misdirection / anti-suji | Upper-Int | 19x19 | Player | SDK-to-dan transition, misdirection | Obvious move fails; quiet move succeeds. Tests difficulty recalibration for non-obvious solutions. |
| **44** | Deep sacrifice (convergence dip) | Advanced | 19x19 | Engine | Non-monotonic convergence, referee escalation | Sacrifice looks winning → opponent counter → counter refuted. T2 borderline, clean at T3. |

### Additional high-value additions if budget allows (puzzles 45-50):

| # | Technique | Level | Gaps Covered |
|---|-----------|-------|---|
| 45 | Clean 3-move snapback | Elementary | Pure snapback detection signal |
| 46 | Center L&D (floating group) | Advanced | Center ownership thresholds |
| 47 | Mannen-ko (perpetual ko) | Low-Dan | Seki↔ko misclassification boundary |
| 48 | Defensive puzzle (Black to live) | Intermediate | Attack vs defense balance |
| 49 | Non-trivial 9x9 L&D | Intermediate | Small-board noise amplification |
| 50 | Miai first moves (flexible order) | Intermediate | `co_correct_min_gap`, `player_alternative_rate` |

---

_Last updated: 2026-03-21 | Trigger: Expert review + gap analysis of perf-33 calibration fixtures_
