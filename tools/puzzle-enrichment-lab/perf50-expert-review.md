# Perf-50 Expert Review & Governance Panel Rulings

> 16 calibration fixtures sourced from external-sources/goproblems to fill gaps identified in perf-33 expert review.
> Reviewed by 3 domain experts + Governance Panel (Cho Chikun tiebreaker).

---

## Round 1: Expert Assessments

### KataGo-Tsumego-Expert (Dr. Shin Jinseo 9p)

| # | Fixture | Difficulty Accurate? | Gap Filled? | Quality (1-5) | Issues |
|---|---------|:---:|:---:|:---:|--------|
| 35 | high_dan_ld_corner | **Yes** | **Yes** — HIGH-DAN L&D | **5** | Massive tree (~200+ nodes). Outstanding corner L&D with sacrifice/counter-sacrifice chains. |
| 36 | high_dan_ld_side | **Yes** | **Yes** — HIGH-DAN side L&D | **4** | Side-enclosed group with ko threats at depth. Good variety from #35. |
| 37 | high_dan_ld_ko | **Borderline — TOO EASY** | Partially | **2** | Only 4 branches, 7-move line. More like advanced. Recommend relabel. |
| 38 | high_dan_tesuji | **Yes** | **Yes** — HIGH-DAN tesuji | **4** | Upper-right squeeze/tesuji. ~30 variations. Good technique calibrator. |
| 39 | expert_ld_deep | **Yes** | **Yes** — EXPERT deep L&D | **5** | 3 separated stones behind wall. Bent-four awareness required. |
| 40 | expert_ld_corner | **Yes** | **Yes** — EXPERT carpenter's square | **5** | Classic carpenter's square. Ko/seki branching. Outstanding calibration anchor. |
| 41 | expert_ld_seki | **Yes, nuanced** | Partially — double-ko not pure seki | **3** | "make-seki" misleading — correct answer is double ko. YQ[q:1] suspiciously low. |
| 42 | upper_int_ld_corner | **Yes** | **Yes** — UPPER-INT corner kill | **4** | Throw-in + eye-reduction. Clean 5-6 move sequence. Appropriate 10k-6k. |
| 43 | upper_int_ld_side | **NO — TOO HARD** | **No** — difficulty mismatch | **2** | 100+ nodes, 5+ sub-variations, 8+ move reading. Low-dan or high-dan material. |
| 44 | upper_int_ld_live | **NO — FAR TOO HARD** | **No** — severe mismatch | **1** | Largest tree in perf-50. Hundreds of variations. High-dan (4d+) material. |
| 45 | advanced_ld_semeai | **Yes** | **Yes** — ADVANCED semeai | **5** | Clean semeai → seki. Excellent dual calibration anchor. |
| 46 | advanced_ld_deep | **Yes** | **Yes** — ADVANCED corner L&D | **4** | Corner life with CHOICE markers. Good advanced anchor. |
| 47 | low_dan_ld_ko | **Yes** | **Yes** — LOW-DAN L&D with ko | **4** | Complex ko/seki disambiguation. Good low-dan complexity. |
| 48 | low_dan_tesuji | **Yes** | **Yes** — LOW-DAN tesuji | **5** | Excellent placement tesuji. Two correct first-move responses. Best low-dan calibrator. |
| 49 | seki_upper_int | **Yes** | **Yes** — SEKI variety | **4** | Capturing-race → seki. Two valid correct answers. Good variety. |
| 50 | seki_expert | **NO — UNSUITABLE** | **No** — joseki, not tsumego | **1** | 5 stones on 19×19 = joseki. Identical to unanimously-removed perf-33 #31. REMOVE. |

**P0 Actions**: REMOVE #50. RELABEL #44 → high-dan. RELABEL #43 → low-dan+. RELABEL #37 → advanced.

### KataGo-Engine-Expert

| # | Expected Tier | Convergence | Engine Difficulty | Engine Gaps Exercised |
|---|:---:|:---:|:---:|---|
| 35 | T2 | Medium | Hard | Tree depth stress, first-line policy rank ~8-12, deep refutation |
| 36 | T2→T3 | **High** | Hard | Ko in wrong branches → non-monotonic convergence |
| 37 | T1→T2 | Low | Moderate-Hard | **T1→T2 boundary candidate** — critical engine gap |
| 38 | T1-T2 | Low | Moderate | Edge squeeze policy, clean winrate cliff |
| 39 | T3 (referee) | **Very High** | Very Hard | **Sparse position trigger** (density 0.008), bent-four, referee escalation |
| 40 | T2→T3 | **Very High** | Very Hard | **Benson gate**, seki/ko boundary, carpenter's square blind spot |
| 41 | T3 | **Very High** | Very Hard | Worst-case convergence (double ko), seki detection threshold |
| 42 | T1 | **Low** | Moderate | Clean T1 anchor, convergence baseline |
| 43 | T2 | Medium | Hard | Multi-start `co_correct_min_gap`, adaptive allocation |
| 44 | T2→T3 | **High** | Hard | **Budget exhaustion** (100+ branches vs 65-query cap), first defensive puzzle |
| 45 | T1-T2 | Medium | Moderate-Hard | Semeai→seki, CaptureRaceDetector |
| 46 | T1-T2 | Low | Moderate | Clean corner L&D, CHOICE markers |
| 47 | T2 | **High** | Hard | Ko/seki disambiguation, tromp-taylor rules override |
| 48 | T1-T2 | Low-Medium | Moderate | Dense tesuji, policy-rank calibrator |
| 49 | T2→T3 | **Very High** | Hard | **Seki as correct answer** → winrate ~0.5, ownership↔winrate divergence |
| 50 | T3 (referee) | **Very High** | Very Hard | Sparse position trigger (density 0.017) |

**Tier distribution**: T1 only: 1 | T1→T2 boundary: 5 | T2: 5 | T3/Referee: 5 — Well-shaped pyramid.

**Engine gaps NOW covered**: T1→T2 boundary flip (#37), non-monotonic convergence (#36, #47), policy rank 10-20 rescue (#44, #35), referee escalation trigger (#39, #50), budget exhaustion (#44), ownership↔winrate divergence (#49).

**Engine gaps STILL OPEN**: b10 vs b18 model disagreement, transposition caching, 9×9 noise amplification, forced-move chain >6 plies, seki with shared liberties.

### Modern-Player-Reviewer (Hana Park 1p)

| # | Difficulty Accurate? | Learning Value (1-5) | Technique Correct? | Player Issues |
|---|:---:|:---:|:---:|---------|
| 35 | ✅ | 5 | ✅ L&D | Xuanxuan Qijing pedigree. No issues. |
| 36 | ✅ | 4 | ✅ L&D | Multiple RIGHT paths; slightly ambiguous goal. Minor. |
| 37 | ⚠️ Questionable | 3 | ⚠️ Ko mislabel | Correct answer kills WITHOUT ko. Ko only in suboptimal lines. Feels advanced. |
| 38 | ✅ | 4 | ✅ Tesuji | Clean corner tesuji. Multi-line tree. Good. |
| 39 | ✅ | 5 | ✅ L&D | 3 sparse stones vs 10 white. Correctly brutal. |
| 40 | ✅ | 5 | ✅ L&D | Carpenter's square confirmed. Ko/seki branching proper expert. |
| 41 | ✅ but... | 2 | ✅ Double-ko seki | q:1 signals "junk" to players. Content is real expert material. |
| 42 | ✅ | 5 | ✅ L&D | Clear move-order kill. Excellent calibration anchor. |
| 43 | ✅ borderline | 4 | ✅ L&D | Tree notably large for upper-int. Near advanced threshold. |
| 44 | ❌ Over-labeled | 2 | ✅ L&D | Largest solution tree in entire set. Low-dan minimum. |
| 45 | ⚠️ Under-labeled | 3 | ⚠️ Seki, not semeai | Named semeai but main content is 5-move seki recognition. |
| 46 | ✅ | 4 | ✅ L&D | Guanzi-pu pedigree. Good anchor. |
| 47 | ✅ | 4 | ✅ L&D | Seki commentary in wrong lines helps calibrate. Solid. |
| 48 | ✅ | 5 | ✅ Tesuji | Complex throw-in sequence. Well-constructed. |
| 49 | ✅ | 4 | ✅ L&D | Capturing-race → seki clear from C[make-seki]. Good. |
| 50 | ❌ Over-labeled | 1 | ⚠️ Misleading | Expert with 5 stones — two tiers too high. Embarrasses calibration set. |

**Critical flags**: RC-1: #37 ko mislabel. RC-2: #44 off by 2 tiers. RC-3: #50 expert label absurd. RC-4: #41 q:1 harms trust.

---

## Round 2: Expert Disagreements

### Dispute 1: #37 — High-Dan or Advanced?
- **KataGo-Tsumego**: Too easy for high-dan. 4 branches, 7-move line. 3-dan solves in 30s. → Relabel advanced.
- **Modern-Player**: Ko only in suboptimal lines. Feels advanced not high-dan. → Borderline.
- **Engine Expert**: Best T1→T2 boundary candidate. W[ma] policy prior 5-10%. → Critical engine test, keep.
- **Tension**: Player accuracy vs engine calibration value.

### Dispute 2: #43 — What Difficulty Level?
- **KataGo-Tsumego**: 100+ nodes, 8+ move reading. Low-dan or high-dan. NOT upper-int. → Relabel.
- **Modern-Player**: Borderline. Acceptable at upper-int (outlier opinion).
- **Engine Expert**: Multi-start co-correct test. High engine value.
- **Tension**: 2 of 3 experts say too hard.

### Dispute 3: #50 — Remove or Relabel?
- **KataGo-Tsumego**: FUNDAMENTALLY UNSUITABLE. Joseki ≠ tsumego. → REMOVE.
- **Modern-Player**: Over-labeled by 2 tiers. → Relabel to low-dan.
- **Engine Expert**: Sparse-position trigger, but value from sparseness unrelated to seki gap.
- **Tension**: Go experts say remove; engine expert sees sparse-test value.

### Dispute 4: #41 — Quality Score and Labels
- **All agree**: Puzzle has legit expert content. Labels/metadata are wrong (seki→double-ko, q:1 too low).
- **Disagreement**: Priority and quality assessment (2/5 vs 3/5 vs "critical edge case").

### Dispute 5: #44 — How Far to Relabel?
- **KataGo-Tsumego**: High-dan (4d+). Hundreds of variations, 7 rows span.
- **Modern-Player**: Low-dan. Tree dwarfs expert puzzles.
- **Engine Expert**: T2→T3. Budget exhaustion test. Way beyond upper-int.
- **Tension**: All agree upper-int is wrong. Disagreement: low-dan vs high-dan.

---

## Round 3: Governance Panel Rulings

**Panel Chair**: Cho Chikun (9p, 25th Honinbo)
**Unanimous vote**: All 8 panel members (Cho Chikun, Lee Sedol, Shin Jinseo, Ke Jie, 2× Principal Engineers, Hana Park, Mika Chen) voted **APPROVE WITH CONDITIONS**.

### Ruling 1: #37 → RELABEL to `advanced`

**Cho Chikun**: "Four branches and a single 7-move correct line — this is a problem I would assign to a 3-kyu to 1-kyu player. A 4-dan sees W[ma] instantly. The name `ld_ko` is also misleading; ko only appears in suboptimal variations."

- `YG[high-dan]` → `YG[advanced]`
- Rename: `37_high_dan_ld_ko` → `37_advanced_ld_nose_tesuji`
- Engine test role: Annotate `T1_T2_boundary_candidate: true` (label-independent)

### Ruling 2: #43 → RELABEL to `low-dan`

**Cho Chikun**: "100+ nodes, 5+ sub-variations, 8+ moves deep. I use these problems in my professional training books at the dan level. Reading depth of 8 and 5 sub-variations = 1d-3d."

- `YG[upper-intermediate]` → `YG[low-dan]`
- Rename: `43_upper_int_ld_side` → `43_low_dan_ld_side`
- Engine test role: Retain `multi_start_co_correct: true`

### Ruling 3: #50 → REMOVE

**Cho Chikun**: "Joseki is joseki; tsumego is tsumego. A 5-stone position on 19×19 is by definition a joseki variation. I would never include this in a tsumego collection at any level. Perf-33 #31 was unanimously removed for the identical reason — binding precedent."

- Action: REMOVE `50_seki_expert.sgf` from perf-50
- Expert seki gap: Track as open, requires genuine replacement (shared liberties, ≥20 stones)

### Ruling 4: #41 → KEEP with metadata fixes

**Cho Chikun**: "Double-ko leading to seki is genuine expert content. The labels are wrong, not the puzzle. `q:1` for expert double-ko content is an insult to the problem."

- Rename: `41_expert_ld_seki` → `41_expert_ld_double_ko_seki`
- Quality: `YQ[q:1]` → `YQ[q:3]` minimum
- Engine annotation: `worst_case_convergence: true`

### Ruling 5: #44 → RELABEL to `high-dan`

**Cho Chikun**: "When a puzzle's solution tree is 5× larger than expert-labeled puzzles — 7,200 characters versus 1,500 for #39 expert — the upper-intermediate label is indefensible. This requires systematic reading that only a 4-dan or stronger can navigate."

- `YG[upper-intermediate]` → `YG[high-dan]`
- Rename: `44_upper_int_ld_live` → `44_high_dan_ld_live`
- Engine annotation: `budget_exhaustion_test: true`

---

## Post-Ruling Coverage Matrix

| Level | Anchors (post-ruling) | Status |
|-------|-----------------------|--------|
| Upper-intermediate (10k-6k) | #42, #49 | ⚠️ Thin — single kill + single seki |
| Advanced (5k-1k) | #45, #46, **+#37** | ✅ Adequate (3 anchors) |
| Low-dan (1d-3d) | #47, #48, **+#43** | ✅ Good (3 anchors) |
| High-dan (4d-6d) | #35, #36, #38, **+#44** | ✅ Strong (4 anchors) |
| Expert (7d-9d) | #39, #40, **#41** (fixed) | ✅ Good (3 anchors) |

### Open Gaps (Require Manual Construction or Future Sourcing)

| Gap | Priority | Notes |
|-----|----------|-------|
| Expert seki (genuine shared-liberty reciprocal life) | **CRITICAL** — #50 removed, zero coverage | Must be sourced before perf-50 complete |
| Center L&D (floating group, no wall contact) | HIGH | Zero coverage after 50 puzzles |
| Anti-suji / misdirection | MEDIUM | Zero coverage; "obvious move is wrong" |
| 9×9 non-trivial L&D at intermediate | LOW | Testing convenience |
| Bent-four-in-corner (Benson gate boundary) | MEDIUM | #39 exercises peripherally, not directly |
| Approach ko (multi-step preparation) | MEDIUM | KataGo PV-len override untested |
| Pure snapback (technique-only) | LOW | SnapbackDetector untested on atomic signal |
| Multi-technique combination | LOW | throw-in → net, sacrifice → liberty-count |
| Mannen-ko (perpetual ko) | LOW | Seki↔ko boundary, historical edge case |
| Upper-int defensive (to-live) fixtures | MEDIUM | #44 was meant for this but relabeled |

---

## Final Fixture Inventory (15 puzzles)

| # | Fixture Name (post-ruling) | Level | Technique | Quality | Engine Role |
|---|---------------------------|-------|-----------|:---:|---|
| 35 | high_dan_ld_corner | high-dan | L&D | 5 | Deep refutation, policy rank 8-12 |
| 36 | high_dan_ld_side | high-dan | L&D | 4 | Non-monotonic convergence |
| 37 | **advanced_ld_nose_tesuji** | **advanced** | L&D/tesuji | 3 | **T1→T2 boundary candidate** |
| 38 | high_dan_tesuji | high-dan | tesuji | 4 | Clean winrate cliff |
| 39 | expert_ld_deep | expert | L&D | 5 | Sparse trigger, referee escalation |
| 40 | expert_ld_corner | expert | L&D | 5 | Benson gate, carpenter's square |
| 41 | **expert_ld_double_ko_seki** | expert | **double-ko seki** | **3** | Worst-case convergence |
| 42 | upper_int_ld_corner | upper-int | L&D | 4 | Clean T1 anchor |
| 43 | **low_dan_ld_side** | **low-dan** | L&D | 4 | Multi-start co-correct |
| 44 | **high_dan_ld_live** | **high-dan** | L&D (defensive) | 2 | Budget exhaustion test |
| 45 | advanced_ld_semeai | advanced | semeai→seki | 5 | CaptureRaceDetector |
| 46 | advanced_ld_deep | advanced | L&D | 4 | CHOICE markers |
| 47 | low_dan_ld_ko | low-dan | L&D/ko | 4 | Ko/seki disambiguation |
| 48 | low_dan_tesuji | low-dan | tesuji | 5 | Placement tesuji calibrator |
| 49 | seki_upper_int | upper-int | capturing-race→seki | 4 | Seki as goal, ownership divergence |
| ~~50~~ | ~~seki_expert~~ | ~~REMOVED~~ | ~~joseki~~ | — | — |

---

_Last updated: 2026-03-22 | Trigger: Expert review + governance panel dispute resolution of perf-50 calibration fixtures_
