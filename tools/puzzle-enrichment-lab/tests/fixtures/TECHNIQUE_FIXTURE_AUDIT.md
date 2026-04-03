# Technique Fixture Audit — Consolidated Expert Assessment

> **Generated**: 2026-03-22
> **Scope**: 35 technique fixture SGFs in `tests/fixtures/` (top-level, excluding test artifacts)
> **Reviewers**: KataGo-Tsumego-Expert (9-dan pro), Modern-Player-Reviewer (Hana Park 1p), KataGo-Engine-Expert (MCTS specialist)
> **Related**: `benchmark/expert-review.md` (49 benchmark puzzles, reviewed 2026-03-21/22)

---

## Consolidated Assessment Table

| # | Filename | Technique | Tech Match | Pro Q (1-5) | Player Q (1-5) | Engine Q (1-5) | Difficulty | Consensus | Issues |
|---|----------|-----------|:---:|:---:|:---:|:---:|:---:|:---:|--------|
| 1 | `capture_race.sgf` | capture-race | YES | 3 | 3 | 2 | beginner-int | **KEEP** | Shallow (1C/0W); needs more refutation branches |
| 2 | `center_puzzle.sgf` | life-and-death | YES | 3 | 4 | 3 | beginner-elem | **KEEP** | Rare center L&D — valuable for diversity. Tests `center_reduction` path |
| 3 | `clamp.sgf` | clamp | YES | 4 | 4 | 2 | elem-int | **KEEP** | Clean Sensei's source. Engine signal weak (structural detection) |
| 4 | `connect_and_die.sgf` | connect-and-die | YES | 4 | 4 | 2 | elem-int | **KEEP** | Classic oiotoshi. Well-commented. Good rare-technique anchor |
| 5 | `connection_puzzle.sgf` | connection | PARTIAL | 2 | 2 | 1 | novice | **REMOVE** | Trivially obvious (8 stones). 0 wrong branches. Zero calibration value |
| 6 | `corner.sgf` | corner (L&D) | PARTIAL | 3 | 2 | 3 | elementary | **FIX** | "Corner" is position, not technique. Retag as `life-and-death,corner-shape` |
| 7 | `cutting.sgf` | cutting | **SPLIT** | 4/P | 1 | 2 | novice-elem | **REPLACE** | Pro: clean concept. Player: "4 parallel rows — no human has ever seen this." Lab construct; zero game-context transfer |
| 8 | `dead_shapes.sgf` | dead-shapes | YES | 4 | **5** | 2 | novice-beg | **MERGE→BM** | Canonical straight-three. Engine-identical to nakade#25. Merge into benchmark |
| 9 | `double_atari.sgf` | double-atari | YES | 3 | 3 | 4 | novice-beg | **KEEP** | Sparse but correct. Clean "two captures" engine signal |
| 10 | `endgame.sgf` | endgame | PARTIAL | 2 | 2 | 3 | elementary | **REMOVE** | Yose is strategic, not tsumego. Score-margin eval. Conflates categories |
| 11 | `escape.sgf` | escape | **SPLIT** | 3/NO | 2 | 2 | beginner-elem | **FIX** | Pro: borderline L&D. Player: "completely enclosed — no escape." Retag as `life-and-death` |
| 12 | `eye_shape.sgf` | eye-shape | PARTIAL | **BUG** | 3 | 2 | beginner | **FIX** | Pro found structural SGF error (stone at `cc` in both AB and AW). Also retag as `false-eye` |
| 13 | `fuseki.sgf` | fuseki | NO | 1 | 1 | 1 | N/A | **REMOVE** | Not tsumego. 4 stones. Governance precedent (Cho Chikun): remove |
| 14 | `joseki.sgf` | joseki | NO | 1 | 1 | 1 | N/A | **REMOVE** | Not tsumego. 2 stones. Binding governance precedent from benchmark #31 |
| 15 | `ko_10000year.sgf` | ko (eternal) | YES | 2 | N/A | 4 | intermediate | **FIX** | Missing SZ property. Numeric tags `10,12`. Add SZ[9], FF[4], GM[1]; rename tags |
| 16 | `ko_approach.sgf` | ko (approach) | YES | 3 | 3 | 3 | advanced | **FIX** | Numeric tags `10,12` → `ko,approach-ko`. Good approach-ko anchor |
| 17 | `ko_direct.sgf` | ko (direct) | YES | 2 | N/A | 4 | beginner | **FIX** | 0 correct paths — broken solution tree. Strong engine signal though |
| 18 | `ko_double.sgf` | ko (double) | PARTIAL | 2 | N/A | 3 | intermediate | **FIX** | Missing SZ, no Yengo metadata, goproblems format. Standardize |
| 19 | `ko_double_seki.sgf` | ko+seki | YES | 3 | 3 | 4 | advanced-dan | **KEEP** | Dual technique. Highest-complexity fixture. Tests escalation path |
| 20 | `ko_multistep.sgf` | ko (multistep) | **SPLIT** | 2/YES | 3 | **5** | intermediate | **SPLIT** | Pro: degenerate solution. Engine: "best ko fixture." Keep for engine; may need better Go-correct variant |
| 21 | `ladder_puzzle.sgf` | ladder | YES | 4 | 4 | **5** | beginner | **KEEP** | All experts agree: strong anchor. PV diagonal ratio calibration. Breaker stones test failure case |
| 22 | `liberty_shortage.sgf` | liberty-shortage | YES | 3 | 3 | 2 | elementary | **KEEP** | Valid damezumari. Structural detection only |
| 23 | `life_death_tagged.sgf` | life-and-death | **SPLIT** | **BUG**/4 | 4 | 2 | beginner-elem | **FIX** | Pro found SGF error (`ds` in both AB and solution). Player: clean corner. Fix stone conflict |
| 24 | `miai_puzzle.sgf` | miai / L&D | **SPLIT** | **5**/P | 2 | 4 | elementary | **KEEP** | Pro: best in set (full metadata, 12C/1W). Player: "12 correct ≠ miai." Engine: unique stress test |
| 25 | `nakade.sgf` | nakade | YES | 4 | **5** | 3 | beginner | **MERGE→BM** | Textbook nakade. All agree: top-tier teaching. Merge into benchmark |
| 26 | `net_puzzle.sgf` | net (geta) | YES | 4 | 4 | 4 | elementary-int | **KEEP** | Clean geta. Strong engine signal (policy+winrate+refutations). Good calibrator |
| 27 | `sacrifice.sgf` | sacrifice | PARTIAL | **BUG** | 3 | **5** | elementary-int | **FIX** | Pro found coordinate errors. Engine: "strongest distinctive signal in entire set." Fix then keep |
| 28 | `seki_puzzle.sgf` | seki | YES | 3 | 4 | 4 | intermediate | **KEEP** | Valuable seki anchor. Engine: tests winrate [0.40-0.60] band. Verify correct move doesn't destroy seki |
| 29 | `shape.sgf` | shape | PARTIAL | 3 | 3 | 1 | beginner | **REMOVE** | No engine signal. "Good shape" is human aesthetic concept. Low calibration value |
| 30 | `simple_life_death.sgf` | life-and-death | PARTIAL | 1 | 2 | 2 | beginner-elem | **REMOVE** | No tags, no markers, no metadata. Redundant with #6 and #23 |
| 31 | `snapback_puzzle.sgf` | snapback | YES | **BUG** | 3 | **5** | intermediate | **FIX** | Pro found SGF error (W plays on existing stone). Engine: "excellent triple-signal." Fix urgently |
| 32 | `tesuji.sgf` | tesuji (generic) | NO | 1 | 1 | 2 | intermediate | **REMOVE** | No tags, no markers. "Tesuji" = everything. Zero discrimination for calibration |
| 33 | `throw_in.sgf` | throw-in | **SPLIT** | **NO**/YES | **5** | 3 | novice-beg | **VERIFY** | Pro: "mislabeled — NOT a throw-in, it's liberty filling." Player: "classic throw-in." Need expert tiebreak |
| 34 | `under_the_stones.sgf` | under-the-stones | YES | 4 | 4 | 3 | int-dan | **KEEP** | Unanimous keep. Classic ishi-no-shita. PV analysis needed for detection |
| 35 | `vital_point.sgf` | vital-point | YES | **BUG** | 4 | 2 | elementary | **FIX** | Pro found SGF error (`bc` in both AB and AW). Engine: redundant with nakade#25 |

---

## Consensus Breakdown

| Recommendation | Count | Puzzles |
|:---:|:---:|---|
| **KEEP** | 12 | 1, 2, 3, 4, 9, 19, 21, 22, 24, 26, 28, 34 |
| **FIX** | 10 | 6, 11, 12, 15, 16, 17, 18, 23, 27, 31, 35 |
| **REMOVE** | 7 | 5, 10, 13, 14, 29, 30, 32 |
| **MERGE→BM** | 2 | 8, 25 |
| **REPLACE** | 1 | 7 |
| **VERIFY** | 1 | 33 |
| **SPLIT decision** | 2 | 20, 24 (experts disagree on interpretation) |

---

## Structural SGF Bugs Requiring Immediate Fix

These puzzles have stone placement conflicts that corrupt calibration:

| # | File | Bug | Fix |
|---|------|-----|-----|
| 12 | `eye_shape.sgf` | `cc` (C7) in both AB[] and AW[] | Remove `cc` from AB |
| 23 | `life_death_tagged.sgf` | `ds` (D1) in AB[] AND solution move B[ds] | Remove `ds` from AB |
| 27 | `sacrifice.sgf` | W[da] plays on existing White stone | Verify and correct coordinates |
| 31 | `snapback_puzzle.sgf` | `jj` (J10) in AW[] AND solution move W[jj] | Remove `jj` from AW |
| 35 | `vital_point.sgf` | `bc` (B7) in both AB[] and AW[] | Remove `bc` from AB |

---

## Top 5 Strongest Calibration Anchors (All Experts Agree)

| Rank | Puzzle | Pro | Player | Engine | Consensus |
|:---:|---|:---:|:---:|:---:|---|
| 1 | **#24 miai_puzzle** | 5 | 2 | 4 | Only full-metadata fixture; 12 correct paths; unique multi-PV stress test |
| 2 | **#21 ladder_puzzle** | 4 | 4 | 5 | PV diagonal ratio, breaker stones, 19x19. Irreplaceable ladder anchor |
| 3 | **#25 nakade** | 4 | 5 | 3 | Textbook vital point. Clean. Best teaching example |
| 4 | **#27 sacrifice** (after fix) | 4* | 3 | 5 | Strongest engine signal (low policy + large winrate swing). Fix SGF first |
| 5 | **#31 snapback** (after fix) | 4* | 3 | 5 | Triple-signal (policy+winrate+delta). Fix SGF first |

## Top 5 Most Problematic

| Rank | Puzzle | Issue |
|:---:|---|---|
| 1 | **#14 joseki** | Not tsumego. 2 stones. Governance precedent: remove |
| 2 | **#13 fuseki** | Not tsumego. 4 stones. Wrong domain entirely |
| 3 | **#33 throw_in** | Pro: "MISLABELED — actually liberty filling, NOT horikomi." DANGEROUS for calibration |
| 4 | **#32 tesuji** | No tags, no markers, no specificity. Zero signal |
| 5 | **#7 cutting** | Player: "4 parallel rows — no human has ever reached this position" |

---

## Missing Techniques for Complete Coverage

| Technique | Importance | Who Flagged | Where to Source |
|-----------|:---:|---|---|
| **Semeai** (pure capture race, not ko) | HIGH | All 3 | goproblems.com "capturing race" tag |
| **Living / Making two eyes** | HIGH | Pro | Cho Chikun Elementary collection |
| **Squeeze (shibori)** | MEDIUM | Pro | goproblems.com or Cho Chikun tesuji |
| **Carpenter's square** | MEDIUM | Pro | Known KataGo blind spot — goproblems has canonical positions |
| **Attach / Hane tesuji** | LOW | Pro | Cho Chikun Dictionary of Basic Tesuji |
| **Bent-four in corner** | LOW | Pro | Classic position — senseis.xmp.net |
| **Clean cutting-point** | LOW | Player | OGS problem library (3-3 invasion cutting) |

---

## Overlap with Benchmark Set

The benchmark set (49 puzzles) already covers all technique categories. The fixtures set serves a DIFFERENT purpose:

| Fixture Set Purpose | Benchmark Purpose |
|---|---|
| Unit test anchors — fast, isolated technique signal | Full enrichment calibration — deep, multi-expert reviewed |
| Parser/structural detector validation | Engine threshold calibration with governance panel corrections |
| CI regression safety net | Production quality gates |

**Action**: After cleanup, fixtures should be **complementary**, not duplicative. Keep fixtures that test unique code paths, not puzzles already well-represented in benchmark.

---

## Multi-Stage Remediation Plan

### Stage 1: Triage (Immediate — same session)
1. ~~**Fix 5 structural SGF bugs** (#12, #23, #27, #31, #35)~~
2. ~~**Remove 7 unsuitable puzzles** (#5, #10, #13, #14, #29, #30, #32)~~
3. **Fix metadata on 5 ko puzzles** (#15, #16, #17, #18)
4. **Retag 2 mislabeled puzzles** (#6 → `life-and-death,corner-shape`, #11 → `life-and-death`)

### Stage 2: Merge & Replace — ✅ COMPLETED (initiative 20260322-1500)
1. ~~**Merge** #8 (dead_shapes), #25 (nakade) into benchmark set~~ — deferred to extended-benchmark
2. ~~**Replace** #7 (cutting) with game-realistic position~~ — ✅ Replaced with goproblems/129.sgf
3. **Verify** #33 (throw_in) — convene tiebreak expert review on technique label
4. ~~**Source** fixtures for missing techniques~~ — ✅ Added living_puzzle.sgf (1121.sgf)

### Stage 2b: Fixture Swap — ✅ COMPLETED (initiative 20260322-1500)
- ✅ Deleted non-tsumego: endgame.sgf, fuseki.sgf, joseki.sgf
- ✅ Replaced connection_puzzle.sgf with goproblems/106.sgf (real connection puzzle)
- ✅ Replaced shape.sgf with goproblems/108.sgf (real shape/L&D puzzle)
- ✅ Replaced cutting.sgf with goproblems/129.sgf (game-realistic cutting position)
- ✅ Replaced simple_life_death.sgf with goproblems/1042.sgf (advanced L&D)
- ✅ Replaced tesuji.sgf with goproblems/968.sgf (elementary tesuji)
- ✅ Added living_puzzle.sgf from goproblems/1121.sgf (covers living tag ID 14)
- ✅ Fixed miai→living tag mapping in test_fixture_coverage.py
- ✅ Excluded joseki/fuseki/endgame from tag coverage (EXCLUDED_NON_TSUMEGO_TAGS)

### Stage 3: External Sourcing (Future session)
1. Search `external-sources/goproblems/` and `external-sources/ogs/` for:
   - Pure semeai (no ko)
   - Defensive L&D (making two eyes)
   - Squeeze (shibori) tesuji
   - Carpenter's square
2. Process through enrichment pipeline, validate with experts
3. Add as calibration fixtures with full metadata

### Stage 4: Test Infrastructure (Future session)
1. Create technique-specific unit tests that load fixtures and assert:
   - Correct technique tag detected
   - Difficulty in expected range
   - Engine convergence at expected tier
2. Replace mock-heavy golden5 tests with real fixture-based assertions where possible
3. Document "what makes a good calibration test" in calibration README

---

## What Makes a Good Calibration Test?

Based on this audit, the criteria for a good technique calibration fixture are:

| Criterion | Weight | Description |
|-----------|:---:|---|
| **Technique purity** | HIGH | One clear technique, not a mix. Filename must match actual technique |
| **Solution tree** | HIGH | ≥1 correct + ≥1 wrong branch. Both RIGHT and WRONG markers present |
| **Yengo metadata** | HIGH | YT (tags), YG (level), YQ (quality), YV (version) present |
| **Structural correctness** | CRITICAL | No stone conflicts, no missing SZ, valid FF/GM |
| **Engine signal** | MEDIUM | Produces a distinctive KataGo output pattern for the technique |
| **Game realism** | MEDIUM | Position could arise in a real game (not lab construct) |
| **Difficulty calibration** | MEDIUM | Difficulty is in the expected range for the technique |
| **Non-redundancy** | LOW | Doesn't duplicate coverage already in benchmark set |

**Current fixture set vs criteria:**
- 12/35 (34%) pass all criteria → **KEEP**
- 10/35 (29%) fail on structural correctness → **FIX**
- 7/35 (20%) fail on technique purity → **REMOVE**
- 6/35 (17%) need other actions → **MERGE/REPLACE/VERIFY**

---

_Last updated: 2026-03-22 | Trigger: Initial technique fixture audit with 3-expert panel_
