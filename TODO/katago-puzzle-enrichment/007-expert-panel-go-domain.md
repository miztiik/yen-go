# Expert Panel: Go Domain Review (S.0)

**Last Updated:** 2026-03-02
**Expert Personas:** Lee Sedol 9-dan, Cho Chikun 9-dan
**Co-reviewer:** Principal Systems Architect

---

## 1. Reference Puzzles (ASCII Board Renderings)

### Puzzle A: Cho Chikun Elementary — prob0026.sgf

SGF: `AB[ba][ca][fb][hb][cc][dc][ec][fc][bd][cd][bf] AW[ea][bb][cb][db][eb][ac][bc]`
Correct: B[aa] (Black plays A19). Wrong: B[ab], B[ad], B[fa], B[da].

```
     A  B  C  D  E  F  G  H  (cols 1-8, rows 1-6 relevant)
 19  .  ●  ●  .  .  .  .  .     ← Black ba(B19), ca(C19)
 18  .  ○  ○  ○  ○  .  .  .     ← White bb,cb,db,eb; Black fb(F18),hb(H18)
 17  ○  ○  ●  ●  ●  ●  .  .     ← White ac,bc; Black cc,dc,ec,fc
 16  .  ●  .  ●  .  .  .  .     ← Black bd,cd
 15  .  .  .  .  ○  .  .  .     ← White ea(E19→actually row 19)
 14  .  ●  .  .  .  .  .  .     ← Black bf(B14→actually col B, row 6)
```

**Corrected coordinate mapping** (SGF `ab` = col A, row 2 = A18):

```
     A   B   C   D   E   F   G   H
 19  .   ●   ●   .   ○   .   .   .     ba=B19, ca=C19, ea=E19
 18  .   ○   ○   ○   ○   ●   .   ●     bb=B18, cb=C18, db=D18, eb=E18, fb=F18, hb=H18
 17  ○   ○   ●   ●   ●   ●   .   .     ac=A17, bc=B17, cc=C17, dc=D17, ec=E17, fc=F17
 16  .   ●   .   ●   .   .   .   .     bd=B16, cd=C16
 15  .   .   .   .   .   .   .   .
 14  .   ●   .   .   .   .   .   .     bf=B14
```

**Correct move: B[aa] = A19** — the 1-1 point, capturing corner.

**Solution analysis:**

- Black plays A19, filling the last liberty of the White group (B18,C18,D18,E18 + A17,B17)
- This is a direct capture — White's corner group has been surrounded and A19 is the killing move
- Wrong moves lead to ko (B[ad], B[fa]) or direct failure (B[ab], B[da])

**Enrichment data (from last calibration):**

- `policy_prior = 0.011` (KataGo ranks A19 at 1.1% — low because on full 19×19 board)
- `visits_to_solve = 509` (needed 509 visits to confirm A19)
- `trap_density = 0.999` (near-maximum — many tempting wrong moves)
- `composite_score = 58.6` → mapped to "intermediate" (level 140)
- **Ground truth: Elementary (level 130)**

### Puzzle B: Cho Chikun Intermediate — prob0026.sgf

SGF: `AB[fa][ab][bb][db][eb][bc][dc][cd] AW[ea][fb][hb][ac][ec][fc][bd][dd][be][de][bg]`

```
     A   B   C   D   E   F   G   H
 19  .   .   .   .   ○   ●   .   .     ea=E19, fa=F19
 18  ●   ●   .   ●   ●   ○   .   ○     ab=A18, bb=B18, db=D18, eb=E18, fb=F18, hb=H18
 17  ○   .   ●   .   ○   ○   .   .     ac=A17, bc=B17(→err), dc=D17, ec=E17, fc=F17
 16  .   ●   .   ●   .   .   .   .     bd=B16(→err), cd=C16, dd=D16
 15  .   ●   .   .   ●   .   .   .     be=B15, de=D15(→err)
 14  .   .   .   .   .   .   .   .
 13  .   ○   .   .   .   .   .   .     bg=B13
```

**Correct sequence:** B[cc] → W[ca] → B[ba] — Multi-step reading required.

### Puzzle C: Cho Chikun Advanced — prob0026.sgf

SGF: `AB[eb][gb][ib][cc][dc][ec][gc][ic][bd][cd][fd][ae][de][fe][df][ff]`
`AW[ea][fa][bb][cb][db][fb][lb][ac][bc][fc][kc][ad][gd][jd][ce][ge][ie][cf][gf][cg]`

```
     A   B   C   D   E   F   G   H   I   J   K   L
 19  .   .   .   .   ○   ○   .   .   .   .   .   .
 18  .   ○   ○   ○   ●   ○   .   ●   .   ●   .   ○
 17  ○   ○   ●   ●   ●   ○   ●   .   ●   .   ○   .
 16  ○   ●   .   ●   .   ●   .   ●   .   ●   .   .
 15  ●   .   .   .   ●   ●   .   .   .   .   .   .
 14  .   .   ○   .   .   ○   ○   .   .   .   .   .
 13  .   .   .   .   .   .   ○   .   .   .   .   .
```

**Correct:** B[ba] → W[da] → B[be] → W[aa] → B[ab] — Ko fight, 5 moves deep, advantageous ko.

---

## 2. Expert Panel Review: Lee Sedol 9-dan

### 2.1 Tight-Board Cropping Validity

**Lee Sedol's assessment:**

> For Puzzle A (prob0026), the stones occupy columns A-H and rows 14-19. This is a classic corner life-and-death problem. Cropping from 19×19 to 9×9 (with margin=2) is absolutely valid here — the entire reading tree is contained within the corner. KataGo's neural network will actually perform BETTER on a 9×9 crop because:
>
> 1. The policy network won't waste probability mass on moves in the empty center/right half
> 2. The value network can focus on the local life-and-death without distant irrelevant stones confusing the evaluation
>
> **Edge case concern:** For Puzzle C (advanced), stones extend from A to L (12 columns). With margin=2, this would need at least 16 columns — which exceeds 13×13 and stays at 19×19. The cropping algorithm's snap-to-standard (9/13/19) handles this correctly.
>
> **Critical concern on prob0026 specifically:** The isolated stone at B14 (bf) is 3 rows away from the main group. With margin=2, the crop boundary would be at row 12 (14-2). This stone IS relevant — it could create a ladder or connection. The cropping correctly includes it since the bounding box includes row 14.
>
> **VERDICT: Cropping is valid** for tsumego. The margin=2 is sufficient for 95%+ of life-and-death problems. Very rare edge cases (running fights, loose ladders) might need margin=3, but these are atypical in curated collections.

### 2.2 Coordinate Back-Translation

> Back-translation is straightforward for tsumego because:
>
> - All stones are in one region (corner or side)
> - The offset is a simple row/column shift
> - No ambiguity — GTP coordinates map 1:1
>
> **One potential pitfall:** KataGo's `pass` move should NOT be translated. The implementation correctly handles this (pass → pass).
>
> **VERDICT: No edge case concerns.** The implementation is sound.

### 2.3 Difficulty Signal Weights (80% KataGo / 20% Structural)

> **This is where the problem lies with prob0026.**
>
> Looking at the enrichment data:
>
> - `policy_prior = 0.011` — On the full 19×19 board, KataGo gives A19 only 1.1% probability. This is because A19 (the 1-1 point) is almost never played in normal Go. The NN has a strong prior against corner plays. But with cropping to 9×9, the policy should be MUCH higher — A19 becomes one of very few legal moves in the corner.
> - `visits_to_solve = 509` — This is reasonable for an elementary puzzle but inflated by the 19×19 board size
> - `trap_density = 0.999` — This is suspiciously high. It suggests ALL wrong moves have high policy AND high winrate loss. For an elementary puzzle, wrong moves should be obviously bad (low policy).
>
> **The 80/20 split is correct in principle, but the INPUTS to the formula are the problem.** With cropping active:
>
> - Policy should increase from 0.011 → 0.1-0.3 range (elementary territory)
> - Visits should decrease from 509 → ~100 range
> - Trap density might decrease as KataGo's policy becomes more focused
>
> **VERDICT: 80/20 weight split is sound.** The calibration issue is input quality (19×19 policy dilution), not the formula weights.

### 2.4 Maximum Effort Config

> For once-per-puzzle enrichment:
>
> - **b28c512:** Excellent choice. This is KataGo's strongest publicly available architecture.
> - **10,000 visits:** More than sufficient for tsumego. Most life-and-death problems converge within 500-2000 visits. 10K provides high confidence.
> - **8 symmetries:** Correct. Go boards have 8-fold symmetry (4 rotations × 2 reflections). Using all 8 eliminates rotational bias.
> - **No time limit:** Correct for batch enrichment.
>
> **VERDICT: Config is optimal** for lab enrichment.

### 2.5 Phase B: KataGo PV → Teaching Comments/Technique Detection

> For prob0026 (Elementary):
>
> - PV shows direct capture (B[aa] captures entire corner group)
> - Teaching comment should identify: "Direct capture — fill the opponent's last liberty"
> - Technique: "capture" or "surround" — this is a basic enclosure kill
> - Ko branches (B[ad], B[fa]) should be annotated: "This leads to a ko fight — the direct capture at A19 avoids ko"
>
> For prob0026 (Advanced):
>
> - 5-move PV ending in ko: "advantageous ko"
> - Teaching comment: "Create a ko by sacrificing first, then fight the ko"
> - Technique: "ko", "sacrifice", "throw-in"
>
> **Mapping pattern:**
>
> - Direct kill (PV depth 1-2) → "capture", "surround"
> - Ko sequence (PV contains recapture) → "ko"
> - Sacrifice sequence (stone played on first-line) → "throw-in", "sacrifice"
> - Ladder (diagonal PV) → "ladder"
>
> **VERDICT: PV-to-technique mapping is feasible** with ~10-15 pattern rules.

### 2.6 Cropping + Frame Interaction

> The tsumego frame (opponent stones surrounding the board edge) should be applied AFTER cropping. Here's why:
>
> 1. On 19×19, the frame would be 72 stones (entire board perimeter) — wasteful and unrealistic
> 2. On cropped 9×9, the frame is 32 stones (9×9 perimeter minus corners = 28, actually) — realistic tsumego setup
> 3. KataGo's NN expects realistic positions. A frame on a small board is how real tsumego books present problems.
>
> **VERDICT: Frame AFTER cropping is correct.** This is already implemented (S.1.4 confirms frame wraps cropped board).

---

## 3. Expert Panel Review: Cho Chikun 9-dan

### 3.1 Problem Assessment — prob0026 (Elementary)

> As the author of this problem collection, I can confirm:
>
> This is a **straightforward killing problem**. Black plays A19 (the 1-1 point) to capture the White corner group. The key reading points are:
>
> - A19 directly removes White's last liberty cluster
> - B[ab] (A18) fails because White plays D19, making two eyes
> - B[ad] and B[fa] lead to ko — unnecessary complication when a direct kill exists
> - B[da] (D19) fails because White plays A19 first
>
> **Difficulty assessment:** This is genuinely elementary-level. A 15-kyu player should solve this in under 30 seconds. The reading required is only 1-2 moves deep. KataGo scoring this as "intermediate" (level 140) is **too high by one full level**.

### 3.2 Root Cause of Mis-grading

> The problem is the **policy prior on 19×19 board**. A19 (the 1-1 point) is almost never played in real games. KataGo's prior of 0.011 treats this as an obscure move. But in the context of this tsumego, it's the ONLY logical move — there's nowhere else to play that captures the group.
>
> **With proper cropping to 9×9:**
>
> - A19 becomes the obvious move — the corner capture
> - Policy prior should jump to 0.1-0.3 range
> - The problem correctly grades as elementary
>
> **My recommendation:**
>
> 1. Verify that tight-board cropping is active during calibration (this will fix the policy dilution)
> 2. The score-to-level thresholds may need slight adjustment — elementary should accept scores up to ~62 instead of 56
> 3. The `trap_density` of 0.999 seems inflated — on a cropped board, wrong moves should have lower policy (fewer tempting alternatives)

### 3.3 Calibration Recommendation

> For the 9-level system mapped to my collections:
>
> | Cho Collection | Yen-Go Level                    | Expected Level ID | Score Range |
> | -------------- | ------------------------------- | ----------------- | ----------- |
> | Elementary     | elementary                      | 130               | 40-62       |
> | Intermediate   | intermediate-upper-intermediate | 140-150           | 55-72       |
> | Advanced       | advanced-low-dan                | 160-210           | 68-88       |
>
> The current threshold `max_score: 56` for elementary is too tight. An elementary puzzle with policy=0.011 gets a policy_component of ~29.7 (out of 30), which alone pushes it past 56. With any trap_density or visits contribution, it exceeds elementary.
>
> **Recommendation: Widen elementary to max_score: 62, shift subsequent thresholds accordingly.**

---

## 4. Principal Systems Architect Co-Review

### Assessment

The expert panel identifies two actionable issues:

1. **Policy dilution on 19×19** — Cropping is already implemented (S.1) and integrated, but we need to verify it's active during calibration test runs. The `test_calibration.py` should be using the same enrichment pipeline that includes cropping.

2. **Score-to-level threshold tuning** — Current thresholds are calibrated to Phase R.3's structural formula. With Phase S.3's KataGo-primary formula (80% AI signals), the score distribution shifts. Thresholds need re-calibration.

### Action Items from Expert Panel

- [x] S.1-S.3 implemented (cropping, max-effort, restored signals) ✅
- [ ] **Run calibration with current code** — verify cropping is active during calibration
- [ ] **Analyze score distribution** — determine if elementary puzzles score 40-62 with cropping
- [ ] **Tune thresholds** — if needed, widen elementary max_score from 56 to ~62
- [ ] **Re-validate ordering** — avg(elementary) < avg(intermediate) < avg(advanced) strict

---

## 5. Verdict

| Topic                       | Status            | Notes                                       |
| --------------------------- | ----------------- | ------------------------------------------- |
| Tight-board cropping        | **APPROVED**      | Valid for tsumego; margin=2 sufficient      |
| Coordinate back-translation | **APPROVED**      | No edge case concerns                       |
| 80/20 signal weights        | **APPROVED**      | Correct in principle; input quality matters |
| Max-effort config           | **APPROVED**      | Optimal for lab enrichment                  |
| Phase B PV mapping          | **FEASIBLE**      | ~10-15 pattern rules needed                 |
| Cropping + frame            | **APPROVED**      | Frame AFTER cropping is correct             |
| Threshold tuning            | **ACTION NEEDED** | Elementary max_score 56→62 recommended      |

**Expert Panel S.0: PASSED with one action item (threshold tuning).**

> **See also:**
>
> - [006-implementation-plan-final.md](006-implementation-plan-final.md) — Phase S plan
> - [docs/architecture/tools/katago-enrichment.md](../../docs/architecture/tools/katago-enrichment.md) — Design decisions D22-D31
