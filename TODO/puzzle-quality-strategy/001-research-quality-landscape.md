# Research: Puzzle Quality Landscape & Collection Strategy

**Created:** 2026-02-25  
**Status:** Research complete — ready for planning  
**Purpose:** Data-driven analysis of ~194K puzzle assets to inform quality control strategy

---

## 1. Data Landscape (Sampled from `external-sources/`)

### Source Inventory

| Source              |     Count | Format | Quality Tier                                    |  Pipeline-Ready  |
| ------------------- | --------: | ------ | ----------------------------------------------- | :--------------: |
| goproblems          |    51,822 | SGF    | **Best** — rich trees, 100+ branches, YQ scored |       Yes        |
| ogs                 |    51,996 | SGF    | **Good** — rich comments, deep teaching text    |       Yes        |
| gotools             |    23,462 | SGF    | **Medium** — has trees, no metadata             | Needs enrichment |
| kisvadim-goproblems |    18,276 | SGF    | **Mixed** — pro author books, encoding issues   | Needs enrichment |
| t-hero              |    12,990 | SGF    | **Good** — tagged, objective-style              |       Yes        |
| tsumegodragon       |    12,836 | SGF    | **Good** — 84% collection-tagged                |       Yes        |
| sanderland          |    12,640 | JSON   | **Needs conversion** — 1-move solution only     | Needs conversion |
| ambak-tsumego       |    10,035 | SGF    | **Minimal** — tiny files, 0-2 branches          | Needs enrichment |
| manual-imports      |        60 | SGF    | **Curated**                                     |       Yes        |
| **Total**           | **~194K** |        |                                                 |                  |

### Pipeline Readiness Tiers

| Tier                                           | Sources                                                | Count | Issues                                                                    |
| ---------------------------------------------- | ------------------------------------------------------ | ----: | ------------------------------------------------------------------------- |
| **Ready** (minimal work)                       | goproblems, ogs, t-hero, tsumegodragon, manual-imports | ~130K | Missing YQ on some; tsumegodragon has encoding issues                     |
| **Needs enrichment** (have SGF, need metadata) | gotools, ambak-tsumego, kisvadim-goproblems            |  ~52K | No YG/YT/YL/YQ; kisvadim has encoding issues; ambak lacks PL              |
| **Needs conversion** (not SGF)                 | sanderland                                             |  ~13K | JSON format, single-move solutions, needs SGF conversion + tree expansion |

---

## 2. Per-Source Deep Analysis

### 2.1 goproblems (51,822 SGF) — Highest Quality

- **Structure:** `sgf/batch-{001-052}/` (52 batches)
- **Pipeline metadata:** Already enriched with YV[10], YG, YT, YQ, YL
- **Rich solution trees:** Some puzzles have 100+ branches with deep correct/wrong paths
- **Comments:** Teaching text with "RIGHT"/"Wrong" markers and explanations
- **BM[1] markers:** 7.5% of samples — bad move annotations with TR[] triangles
- **Board sizes:** 19×19 (80%), 13×13 (16%), plus 5×5, 9×9, 7×7
- **Difficulty range:** novice through low-dan

**Example (batch-007/8770.sgf):** 125 branches, 159 nodes, 1760B — deeply annotated W-to-play life-and-death with emoticon feedback

```sgf
(;SZ[19]FF[4]GM[1]PL[B]YV[10]YG[low-dan]YT[life-and-death]YQ[q:2;rc:0;hc:0]
AB[sb][rc][qc][ra][pd][od][nd][of][og][oh][oj][qj][rj][sj][rh]
AW[ri][qh][rg][pf][pe][qd][rd][sd][sc]
(;B[rf];W[re](;B[sf];W[qf];B[sh]C[RIGHT])...))
```

### 2.2 ogs (51,996 SGF) — Good Quality, Best Narrative

- **Structure:** `sgf/batch-{001-052}/` (52 batches)
- **Teaching comments:** Best narrative quality — long explanatory text, strategic reasoning
- **Comment format:** Root has objective ("black-to-kill"), moves have `C[Correct!]` or `C[Wrong #Incorrect! **-> explanation**]`
- **Markdown formatting** in comments: `**bold**` for key points
- **Board size diversity:** 19 (72%), 9 (11%), 13 (6%), 11 (5.5%), 5 (3%) — most diverse
- **Collection attribution:** 75% have YL[] with named collections
- **File size range:** 74B–135KB (widest range)

**Example (batch-002/2216.sgf):**

```sgf
(;FF[4]GM[1]CA[UTF-8]SZ[13]YG[intermediate]YT[life-and-death]YL[fran-go-library]
PL[B]AB[ad][be][ce][de][dd][bg][db][eb]AW[cd][bd][ae][cb][ca][ab]
C[black-to-kill]
(;B[cc];W[bc];B[ba]C[Correct! #Correct! **-> White has formed only one eye and is dead.**])...)
```

### 2.3 gotools (23,462 SGF) — Needs Full Enrichment

- **Structure:** `{advanced,elementary,high-dan,intermediate,low-dan,upper-intermediate}/`
- **No pipeline properties.** Only GM, FF, SZ, HA, KM, empty GN[]
- **Consistent format:** All 19×19, standardized naming (`gotools_lv{1-6}_{08-14}_p{7-digit}.sgf`)
- **Level in comments:** `C[GoTools Lv5.9 → low-dan:2]`
- **Solution trees:** 2–52 nodes. WV[] + "Wrong."/"Correct." markers
- **No PL[]:** Player to move not set

**Example (low-dan/gotools_lv5_09_p1012116.sgf):**

```sgf
(;GM[1]FF[4]SZ[19]HA[0]KM[0]GN[]
AB[aa][ba][ca][da][ea][ab][gb][ac][ad][fd][ae][ee][af][bf][df][ag]
AW[bb][db][cc][ec][bd][dd]
C[GoTools Lv5.9 → low-dan:2]
(;B[ac];W[ba];B[da];W[ad];B[bc];W[ca];B[aa];W[dc];B[cb]C[Correct.])
(;B[ea]WV[];W[ac];B[cd]...C[Wrong.])...)
```

### 2.4 kisvadim-goproblems (18,276 SGF) — Mixed Quality, Professional Authors

- **Structure:** 64 book/author directories (Cho Chikun, Go Seigen, Hashimoto Utaro, Gokyo Shumyo, etc.)
- **No pipeline metadata.** Some GN[] with book names
- **Comment quality varies wildly:** 71% have C[], but some contain garbled Chinese encoding (GB2312/Big5 → mojibake), while others have clean labels like `C[Elementary]`
- **WV[] markers:** Wrong variations tagged in Cho Chikun books
- **SZ missing:** ~14% lack board size property
- **Encoding issues:** Go Seigen and classic collections have corrupted non-Latin comments
- **Collection breadth:** Novice through professional-level, tsumego + tesuji

**Example (Cho Elementary/prob0250.sgf):**

```sgf
(;GM[1]FF[4]SZ[19]HA[0]KM[0]GN[Cho L&D (abc)]
AB[fa][fb][hb][ac][bc][fc][cd][dd][ed][be]
AW[ca][ab][bb][eb][cc][dc]C[Elementary]
(;B[db];W[da](;B[ea];W[cb];B[ec]C[Correct.])(;B[ec];W[cb];B[ea]C[Correct.]))...)
```

### 2.5 t-hero (12,990 SGF) — Good Quality, Tagged

- **Structure:** `sgf/batch-{001-026}/` (26 batches), YS[th] source marker
- **YG (100%), YT (43%), YL (14%)**, no YQ
- **Good solution trees:** Up to 72 nodes, 20 branches
- **Tags when present:** Specific — dead-shapes, eye-shape, throw-in, vital-point
- **Root comments:** Objective-style (black-to-kill, white-to-play)
- **Correct marker:** `C[+]` (terse, consistent)

**Example (batch-023/th-13896.sgf):**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]C[white-to-kill]YG[elementary]
YT[dead-shapes,eye-shape,throw-in,vital-point]YS[th]
AB[ap][bp][cp][dp][aq][eq][fq][fr][fs]AW[bq][cq][dq][ar][er][cs][ds]
(;B[bs];W[br](;B[dr]C[+])(;B[es];W[dr]))...)
```

### 2.6 tsumegodragon (12,836 SGF) — Good Quality, Well-Categorized

- **Structure:** `sgf/batch-{001-026}/` (26 batches), YS[td] source marker
- **Highest collection coverage** (84% have YL[]): double-atari-problems, ko-problems, general-practice
- **Good trees:** Up to 100 nodes, 26 branches
- **Multilingual comments:** Chinese (黑先白死), English, some garbled encoding
- **BM[1] markers:** 16% — highest rate of bad-move annotations

**Example (batch-007/...725000.sgf):**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]C[Black to play double atari]YG[intermediate]YT[double-atari]
YS[td]YL[double-atari-problems]
AB[ac][bc][cc][cd][ce][da][db][dc][dd][ec][ed]
AW[bb][be][ca][cb][cf][df][ea][eb][fb][ff][gc][ge]
(;B[ba];W[aa];B[ab]C[Correct.])(;B[ab];W[ba]C[Wrong.]BM[1])...)
```

### 2.7 sanderland (12,640 JSON) — Needs Full Conversion

- **Format:** Custom JSON — NOT SGF. Fields: AB, AW, SZ, C, SOL
- **Solution depth: 1 move only.** SOL is always `[["B", "coord", "", ""]]`. No variations
- **All 19×19**, all "Black to play" or "White to play"
- **Professional book attributions:** Cho Chikun, Lee Chang-ho, Go Seigen, Hashimoto Utaro
- **Categories:** tsumego-beginner/intermediate/advanced, tesuji, etc.

**Example (Cho Elementary/Prob0593.json):**

```json
{
  "AB": ["ba", "da", "db", "bc", "dc", "bd", "cd"],
  "AW": ["ea", "ab", "eb", "ec", "ad", "dd", "ae", "be", "ce", "de"],
  "SZ": "19",
  "C": "Black to play: Elementary",
  "SOL": [["B", "bb", "", ""]]
}
```

### 2.8 ambak-tsumego (10,035 SGF) — Minimal Metadata

- **Structure:** `{elementary,intermediate,advanced}/batch-{001-009}/`
- **No pipeline metadata at all.** No YG, YT, YL, YQ, PL, or YS
- **Very small files** (median 207B, max 1.9KB): 0-2 branches
- **All 19×19**, comments terse: Just `C[+]` for correct
- **Difficulty from directory name only**

### 2.9 manual-imports (60 SGF) — Small Curated Set

- Small curated OGS batch with rich teaching comments. Too small to matter statistically.

---

## 3. Current Pipeline Quality Heuristics (Audit)

### 3.1 Quality Scoring (YQ) — `core/quality.py`

**Format:** `q:{level};rc:{refutation_count};hc:{comment_level}`

| Level          | Name  | Criteria                                         |
| -------------- | ----- | ------------------------------------------------ |
| 5 (Premium)    | Best  | solution tree + ≥3 refutations + comments (hc≥1) |
| 4 (High)       |       | solution tree + ≥2 refutations + comments (hc≥1) |
| 3 (Standard)   |       | solution tree + ≥1 refutation                    |
| 2 (Basic)      |       | solution tree present, zero refutations          |
| 1 (Unverified) | Worst | no solution tree                                 |

**Gap:** All thresholds hardcoded. Config `puzzle-quality.json` is documentation-only — code doesn't read it. Doesn't evaluate QUALITY of refutations (could be shallow/meaningless).

### 3.2 Validation (Ingest Stage) — `core/puzzle_validator.py`

| Check               | Default |        Configurable?         |
| ------------------- | ------- | :--------------------------: |
| Board width 5–19    | Yes     | Yes (puzzle-validation.json) |
| Stone count ≥ 2     | Yes     |             Yes              |
| Solution depth ≥ 1  | Yes     |             Yes              |
| Solution depth ≤ 30 | Yes     |             Yes              |

**Gap:** Centralized PuzzleValidator exists but ingest stage only checks `has_solution`. No semantic validation (puzzle vs game record vs training material).

### 3.3 Difficulty Classification (YG) — `core/classifier.py`

Additive scoring: solution_depth + variation_count + stone_count + board_size → mapped to 9 levels.

**Code comment:** _"This is a placeholder - real implementation would use more sophisticated analysis"_

**Gap:** Doesn't consider technique type, spatial complexity, liberty situations, or reading difficulty. A shallow puzzle with a subtle net is rated same as a shallow capture.

### 3.4 Tag Detection (YT) — `core/tagger.py`

- **Phase 1:** Comment keywords (English + Japanese word-boundary matching) → 14+ technique tags
- **Phase 2:** Board pattern detection for ko, snapback, capture-race, ladder

**Gap:** 12+ techniques detectable ONLY from comments, no board heuristic. If comments absent or CJK-only without matching keywords → untagged.

### 3.5 Complexity Metrics (YX) — `core/complexity.py`

**Format:** `d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness}`

**Gap:** `d` only follows first correct branch. `r` includes wrong-move subtrees. No measure of "reading density."

### 3.6 Hint Generation (YH) — `core/enrichment/hints.py`

Three progressive hints: technique → reasoning → coordinate. Tag-driven with atari detection fallback.

**Gap:** No hints for puzzles with zero tags AND non-captures.

### 3.7 Puzzle vs Training Material Detection

**Finding: NO code exists for this.** `is_teaching_comment()` in `text_cleaner.py` detects whether a comment has teaching content — but it's only used for the `hc` metric, not for content classification.

---

## 4. The Core Problem

**A "beginner puzzle" and "beginner training exercise" from the same source are structurally identical in SGF.** The pipeline cannot currently tell them apart.

Manifestations:

- Websites host training material (explaining concepts step-by-step) as "puzzles"
- Collections are force-mapped into difficulty slugs without content-type distinction
- When a user selects "beginner", they get a mix of genuine tsumego and teaching sequences
- Some "puzzles" are trivial captures (stone already in atari) — reflex drills, not reading exercises
- Single-path SGFs (no branching) might be teaching sequences rather than puzzles
- Same classical problems (Cho Chikun, etc.) appear in 3-4 sources with different metadata quality

---

## 5. Professional Go Player Consultation (Synthesized Advice)

### 5.1 Cho Chikun (9-dan, Tsumego Author)

**Key insight:** The single most important quality signal is **uniqueness of the first move.** A proper tsumego has exactly one vital point. If u:0 (miai first moves), it's likely an exercise, not a tsumego.

**Recommendations:**

1. Use YX `u` field as a filter: u:0 → flag as exercise, not tsumego
2. Solution depth `d:1` does NOT mean "novice" — many elementary problems are devastating 1-move kills requiring 10-move reading to verify
3. Root comment intent: "demonstrates/explains/shows" = training signal. "Play/kill/live" = puzzle signal
4. Trust source difficulty for known-authority collections (Cho, professional books in kisvadim)

### 5.2 Lee Chang-ho (9-dan, Precision Reading Specialist)

**Key insight:** Quality comes from the **refutation tree**, not the correct path.

**Recommendations:**

1. Compute **refutation coverage ratio** = wrong_first_moves_covered / total_plausible_first_moves
2. Compute **avg_refutation_depth** — mean depth of wrong-move subtrees. Shallow refutations → training. Deep → proper puzzle
3. Classify content into three types: `tsumego` / `tesuji-exercise` / `teaching-position` — don't reject, classify and let users filter
4. Don't sacrifice OGS teaching puzzles — comments make them pedagogically superior to well-branched but unexplained puzzles

### 5.3 Takemiya Masaki (9-dan, "Cosmic Style" — Big Picture)

**Key insight:** Over-optimizing for individual puzzle quality when the real problem is **collection coherence.**

**Recommendations:**

1. **Near-duplicate detection** is the #1 shift-left opportunity — same position in 4 sources × 4 metadata qualities → keep best version
2. **Trivial capture detection** — if any opponent stone is already in atari AND correct move captures it → reflex drill, not puzzle
3. **Don't sacrifice quantity — STRATIFY it** into curated/practice/exploration tracks
4. **Positional features** for classifier — stone density in action zone + groups with ≤3 liberties

---

## 6. Proposed Strategies (Tradeoff Analysis)

### Strategy A: Shift-Left — Enrich at Collection Time

| Signal                                                  | Cost                    | Catches                                |
| ------------------------------------------------------- | ----------------------- | -------------------------------------- |
| Board position hash (rotation-normalized, SHA256)       | O(n) per puzzle         | Duplicates across sources              |
| Trivial capture detection (opponent stone at 1 liberty) | O(stones)               | Reflex drills misclassified as puzzles |
| Solution tree completeness score                        | O(nodes + stones)       | Training material with thin trees      |
| First-move uniqueness                                   | Free (already computed) | Miai exercises vs tsumego              |
| Root comment intent (regex)                             | O(comment_len)          | Teaching positions                     |

**Tradeoffs:**

- (+) Catches problems before pipeline state, saving re-processing
- (+) Duplicate detection saves ~15-20% storage, avoids user-facing dupes
- (-) Requires re-running collection for existing 194K (one-time cost)
- (-) Doesn't solve classification accuracy for edge cases

**Effort:** ~2 weeks implementation, ~1 day re-run

### Strategy B: Post-Collection Content-Type Classification

Add `content_type` dimension in analyze stage:

| Content Type        | Detection Heuristics                                                  |
| ------------------- | --------------------------------------------------------------------- |
| `tsumego`           | unique first move (u:1) + refutations ≥ 1 + no teaching root comment  |
| `tesuji-drill`      | technique tag + may have miai moves + objective-only root             |
| `teaching-position` | hc:2 on root OR root explains technique OR depth ≤ 1 with explanation |
| `trivial`           | correct first move captures stones already in atari                   |
| `unclassifiable`    | None of the above                                                     |

**Tradeoffs:**

- (+) Directly solves puzzle-vs-training problem
- (+) Users can filter by content type, nothing rejected
- (-) Adds new dimension to shard/view system (structural change)
- (-) ~10-15% misclassification rate without human validation
- (-) Requires frontend UI changes

**Effort:** ~3 weeks

### Strategy C: Quality Floor with Conscious Sacrifice

Minimum quality thresholds per difficulty level:

| Level               | Min Quality | Min Refutations |  Projected Keep |
| ------------------- | :---------: | :-------------: | --------------: |
| novice-beginner     |     q≥1     |        0        |             92% |
| elementary          |     q≥2     |        0        |             92% |
| intermediate        |     q≥3     |        1        |             80% |
| upper-intermediate+ |     q≥3     |        2        |             71% |
| dan-level           |     q≥4     |        3        |             62% |
| **Total**           |             |                 | **~151K (78%)** |

**Tradeoffs:**

- (+) Guarantees minimum quality at every level
- (+) Simple to implement (config + validation gate)
- (-) Loses ~43K puzzles (22%), some may be good but data-poor
- (-) Dan-level scarcity worsens

**Effort:** ~1 week

### Strategy D: Hybrid (Recommended by Staff Engineer)

Combine best of A, B, and soft C:

| Phase       | Action                                                          | Timeline |
| ----------- | --------------------------------------------------------------- | -------- |
| **Phase 1** | Board-position dedup + trivial-capture detection                | 2 weeks  |
| **Phase 2** | Content-type classification in analyze stage                    | 3 weeks  |
| **Phase 3** | avg_refutation_depth metric + quality-weighted daily challenges | 2 weeks  |

User-facing quality tiers:

- **Curated** (q≥4, tsumego, professional collections): ~25K
- **Standard Practice** (q≥2, tsumego or drill): ~120K
- **All Puzzles** (everything after dedup): ~175K
- **Training Lab** (teaching + drill explicitly): ~30K

**Tradeoffs:**

- (+) No puzzle sacrificed, users self-select quality
- (+) Dedup eliminates ~15K duplicates
- (+) Durable — handles future sources automatically
- (-) Highest effort (~5 weeks total)
- (-) Content-type still ~10-15% error rate

### Strategy E: Statistical Outlier Detection

Composite "puzzle health score" from weighted signals:

| Signal                                | Weight |
| ------------------------------------- | ------ |
| Solution depth / stone count ratio    | 0.20   |
| Refutation coverage                   | 0.25   |
| First-move uniqueness                 | 0.15   |
| Comment presence (hc)                 | 0.10   |
| Source trust score                    | 0.15   |
| avg_refutation_depth / solution_depth | 0.15   |

Percentile-based cutoff per difficulty level (reject bottom 10th percentile).

**Tradeoffs:**

- (+) Data-driven, adapts to corpus distribution
- (+) Catches multi-dimensional issues
- (-) Requires calibration with spot-checks
- (-) Opaque to users; wrong weights = wrong ejections

**Effort:** ~3 weeks

---

## 7. Strategy Comparison Matrix

| Criterion                  | A (Shift-Left) | B (Content-Type) | C (Quality Floor) | D (Hybrid) | E (Statistical) |
| -------------------------- | :------------: | :--------------: | :---------------: | :--------: | :-------------: |
| Solves puzzle-vs-training  |   Partially    |     **Yes**      |        No         |  **Yes**   |    Partially    |
| Preserves quantity         |    **Yes**     |     **Yes**      |     No (78%)      |  **Yes**   |    No (90%)     |
| Implementation complexity  |      Low       |      Medium      |      **Low**      |    High    |     Medium      |
| User experience impact     |      Low       |     **High**     |      Medium       |  **High**  |     Medium      |
| Handles future sources     |   Partially    |     **Yes**      |      **Yes**      |  **Yes**   |     **Yes**     |
| No frontend changes needed |    **Yes**     |        No        |      **Yes**      |     No     |     **Yes**     |

---

## 8. Key Insight: The Problem Won't Go Away with Shift-Left Alone

Shift-left (Strategy A) catches known issues at collection time, but:

- Every new source brings new variations of the same problem
- Training-vs-puzzle distinction requires semantic analysis that runs on EVERY pipeline execution
- Content-type classification (Strategy B) in the analyze stage is the durable solution

**Recommended path:** Strategy D (Hybrid), phased over 3 sprints.

---

## 9. Open Questions for Planning Phase

1. Should content-type become a new SGF property (e.g., `YP[tsumego]`) or metadata-only in views?
2. Should dedup keep the highest-quality duplicate or merge metadata from all copies?
3. What's the acceptable misclassification rate before we'd consider human spot-check calibration?
4. Should "Training Lab" be a user-visible mode in v1, or deferred?
5. Should we implement avg_refutation_depth as a new YX sub-field or separate property?

---

_Next step: Create planning document with phased implementation plan, task breakdown, and acceptance criteria._
