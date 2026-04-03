# Research Brief: External-Sources Puzzle Inventory for Calibration Fixture Sourcing

> Last Updated: 2026-03-22
> Initiative ID: 20260322-research-external-sources-fixture-sourcing
> Research scope: Systematic inventory of `external-sources/` for finding replacement puzzles for enrichment-lab calibration fixtures

---

## 1. Research Question & Boundaries

**Question**: Which collections in `external-sources/` can provide high-quality replacement SGF puzzles for the 8 technique gaps identified in the fixture audit — and what is the most efficient sourcing strategy?

**Target techniques** (the 8 fixture gaps needing replacement):

| R-1 | Tag slug | Tag name | Category | Fixture file |
|-----|----------|----------|----------|--------------|
| R-1 | `capture-race` | Capture Race (semeai) | technique | `capture_race.sgf` |
| R-2 | `cutting` | Cutting | technique | `cutting.sgf` |
| R-3 | `snapback` | Snapback | tesuji | `snapback_puzzle.sgf` |
| R-4 | `throw-in` | Throw-in | tesuji | `throw_in.sgf` |
| R-5 | `ko` | Ko (variants) | objective | `ko_direct.sgf`, `ko_approach.sgf`, `ko_double.sgf`, `ko_multistep.sgf`, `ko_10000year.sgf`, `ko_double_seki.sgf` |
| R-6 | `living` / `eye-shape` | Living / Eye Shape | objective/technique | `eye_shape.sgf`, `simple_life_death.sgf` |
| R-7 | `liberty-shortage` | Squeeze (shibori/damezumari) | tesuji | `liberty_shortage.sgf` |
| R-8 | `dead-shapes` | Dead Shapes (carpenter's square) | technique | `dead_shapes.sgf` |

**Boundaries**:
- Only `external-sources/` collections (not new crawling)
- Sample-based assessment (2-3 SGFs per collection) — not exhaustive reads
- Focus on SGF format quality: solution trees, technique tags, difficulty labels
- Must have branching solution tree (correct + wrong paths) to serve as calibration fixture

**Success criteria**: Identify at least 2 candidate sources per technique gap with format-quality grading.

---

## 2. Internal Code Evidence

### 2.1 Existing Fixture Format Requirements

Current fixtures in `tools/puzzle-enrichment-lab/tests/fixtures/` (42 root-level SGFs) follow this format:
- `FF[4]GM[1]SZ[19]PL[B|W]` header
- `YT[tag-slug]` technique tag
- `AB[..] AW[..]` initial stones
- `C[description]` root comment
- Branching solution tree with `C[Correct...]` / `C[Wrong...]` markers
- Some have `PC[senseis-url]` source attribution

**Critical quality**: Enrichment-lab calibration **requires** solution trees with both correct AND wrong paths. Collections with only first-move solutions or linear sequences are unsuitable.

### 2.2 Tag System Mapping

From `config/tags.json` v8.3, the 28 standard tags map technique keywords as follows:
- `capture-race` aliases: semeai, liberty race, liberty counting
- `snapback` aliases: snap back, uttegaeshi, pounce, backward
- `throw-in` aliases: horikomi, sacrifice throw, flutter
- `liberty-shortage` aliases: squeeze, damezumari
- `dead-shapes` aliases: carpenter's square (golden cabinet corner), bent-four, bulky-five, L-group
- `cutting` aliases: cut, disconnect, crosscut, peep, nozoki

### 2.3 Pipeline Pre-Processing

The `goproblems/` flat collection already has pipeline-applied tags: `YV[10]`, `YG[level]`, `YT[tag]`, `YQ[quality]`, `YL[collection]`. These puzzles can be used **directly** without re-tagging.

---

## 3. Collection Inventory

### 3.1 Master Inventory Table

| R-1 | Collection | Est. Puzzles | File Format | Organization | Solution Trees | Technique Tags | Difficulty Labels | Quality Grade |
|-----|-----------|-------------|-------------|--------------|----------------|---------------|-------------------|---------------|
| R-1 | `goproblems/` (flat) | 51,822 | SGF (pipeline-enriched) | batch dirs | Yes (branching) | Yes (`YT[...]`) | Yes (`YG[...]`) | **A** |
| R-2 | `goproblems_difficulty_based/` | ~9,000+ | SGF (rich metadata) | technique × difficulty | Yes (RIGHT markers) | Yes (`GE[tesuji]`) | Yes (`DI[4k]`) | **A+** |
| R-3 | `ogs/` | 51,996 | SGF (pipeline-enriched) | batch + collection | Yes (Correct!/Wrong) | Yes (`YT[...]`) | Yes (`YG[...]`) | **A** |
| R-4 | `gotools/` | ~18,000 | SGF (GoTools) | difficulty level dirs | Yes (Correct./Wrong.) | No | Yes (by dir) | **B+** |
| R-5 | `kisvadim-goproblems/` | ~10,000+ | SGF (curated books) | book dirs (~65 books) | Yes (Correct./Wrong.) | No (by book name) | No | **B** |
| R-6 | `tsumegodragon/` | 12,836 | SGF | batch dirs | Unknown | Unknown | Unknown | **C** (unsampled) |
| R-7 | `t-hero/` | 12,990 | SGF | batch dirs | Unknown | Unknown | Unknown | **C** (unsampled) |
| R-8 | `blacktoplay/` | 3,780 | SGF | batch dirs | Unknown | Unknown | Unknown | **C** (unsampled) |
| R-9 | `ambak-tsumego/` | 10,035 | SGF (CGoban) | difficulty level × batch | Minimal (1 correct path) | No | Yes (by dir) | **B-** |
| R-10 | `tasuki/` | ~2,700+ | SGF (bare-bones) | book dirs | **No** (position only) | No | No | **D** |
| R-11 | `sanderland/` (2a-tesuji) | ~3,200 JSON | JSON (OGS format) | book dirs | **No** (first move only) | No | No | **D** |
| R-12 | `sanderland/` (2c-encyclopedia) | 2,636 JSON | JSON (OGS format) | batch dirs | **No** (first move only) | No | No | **D** |
| R-13 | `eidogo_puzzles/` | ~1,000 | SGF (FF[3]) | collection dirs | **No** (linear) | No | No | **D** |
| R-14 | `Xuan Xuan Qi Jing/` | 347 | SGF | flat | Unknown | No | No | **C** |
| R-15 | `Kanzufu/` | ~400+ | SGF | volume dirs | Unknown | No | No | **C** |
| R-16 | `101weiqi/` | 4 (181K catalogued) | SGF | book-based | Unknown | Unknown | Yes (catalog) | **C** (barely downloaded) |

### 3.2 goproblems_difficulty_based — Technique × Difficulty Breakdown

This is the **highest-value collection** for fixture sourcing due to pre-categorized technique directories AND rich SGF metadata.

| R-1 | Technique Dir | Easy | Medium | Hard | Total |
|-----|--------------|------|--------|------|-------|
| R-1 | `tesuji/` | 707 | 398 | 131 | 1,236 |
| R-2 | `life_and_death/` | 2,928 | 2,141 | 624 | 5,693 |
| R-3 | `best_move/` | 350 | 202 | 93 | 645 |
| R-4 | `elementary/` | 627 | 74 | 14 | 715 |
| R-5 | `endgame/` | ? | ? | ? | ? |
| R-6 | `fuseki/` | ? | ? | ? | ? |
| R-7 | `joseki/` | ? | ? | ? | ? |

**SGF metadata format** (sampled from `easy/tesuji/10019.sgf`):
```
GE[tesuji]     — technique genre (VERY valuable for filtering)
DI[4k]         — difficulty rank
DP[29]         — solution depth
SO[Dudzik]     — original author
CO[5]          — comment count
```
Full solution trees with RIGHT markers and multiple branching variations.

### 3.3 kisvadim-goproblems — Tesuji Book Counts

| R-1 | Book Name | SGF Count | Relevance |
|-----|-----------|-----------|-----------|
| R-1 | TESUJI GREAT DICTIONARY | 2,636 | Broad tesuji coverage: snapback, throw-in, cutting, squeeze |
| R-2 | LEE CHANGHO TESUJI | 735 | Dan-level tesuji |
| R-3 | GO SEIGEN - SEGOE TESUJI DICTIONARY | 505 | Classic tesuji reference |
| R-4 | SAKATA EIO TESUJI | 110 | Master-level tesuji |
| R-5 | KOBAYASHI SATORU 105 BASIC TESUJI | 105 | 1-3 dan basic tesuji |
| R-6 | MAKING SHAPE TESUJI | 31 | Shape-focused tesuji |
| R-7 | CHO CHIKUN L&D — Elementary | 900 | Life & death (has solution trees) |
| R-8 | CHO CHIKUN L&D — Intermediate | 861 | Life & death |
| R-9 | CHO CHIKUN L&D — Advanced | 792 | Life & death |

**SGF format** (sampled from Cho Chikun Elementary `prob0001.sgf`):
```
GM[1]FF[4]SZ[19]GN[Cho L&D (abc)]
AB[...] AW[...]
C[Elementary]
(;B[ba]C[Correct.])
(;B[ca]WV[];W[ba]C[Wrong.])
```
Good: has branching solution trees with `C[Correct.]`/`C[Wrong.]` markers. No technique tags though — discovery requires domain knowledge of book content.

### 3.4 Collection Format Samples

| R-1 | Collection | Sample | Solution Tree? | Markers | Metadata |
|-----|-----------|--------|----------------|---------|----------|
| R-1 | goproblems (flat) | `batch-001/100.sgf` | Yes (linear, some branching) | None (C[] text) | YV, YG, YT, YQ, YL |
| R-2 | goproblems (flat) | `batch-001/1000.sgf` | Yes (deep branching) | RIGHT / Wrong Wrong | YV, YG, YT, YQ, YL |
| R-3 | goproblems_difficulty_based | `easy/tesuji/10019.sgf` | Yes (deep branching) | RIGHT | GE, DI, DP, SO, CO |
| R-4 | ogs | `batch-001/10.sgf` | Yes (deep branching) | Correct! / Wrong | YG, YT, YL |
| R-5 | gotools | `elementary/gotools_lv1_...` | Yes (branching) | Correct. / Wrong. | GN (level info) |
| R-6 | kisvadim (Cho L&D) | `prob0001.sgf` | Yes (branching) | Correct. / Wrong. | GN, C[level] |
| R-7 | kisvadim (Tesuji Dict) | `problem (1).sgf` | Yes (branching) | None | FF, SZ only |
| R-8 | ambak-tsumego | `1623.sgf` | Minimal (1 correct path) | +/C[] | CGoban headers |
| R-9 | sanderland (2a-tesuji) | `Problem 1.json` | **No** (first move only) | None | JSON format, not SGF |
| R-10 | tasuki | `problem_0001_p1.sgf` | **No** (position only) | None | C[source] only |
| R-11 | eidogo (xxqj) | `xxqj_problem0001.sgf` | **No** (linear) | None | FF[3] |

---

## 4. Candidate Adaptations for Yen-Go

### 4.1 Per-Technique Sourcing Candidates

#### R-1: Capture Race (semeai)

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | `sgf/batch-*/*.sgf` where `YT[capture-race]` | Pre-tagged, just grep | Low |
| R-2 | goproblems_difficulty_based | `*/life_and_death/*.sgf` where `GE` matches | Many semeai within L&D | Medium |
| R-3 | ogs | `sgf/batch-*/*.sgf` where `YT[capture-race]` | Pre-tagged | Low |

#### R-2: Cutting

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | `sgf/batch-*/*.sgf` where `YT` includes cutting-related | Pre-tagged | Low |
| R-2 | kisvadim TESUJI GREAT DICTIONARY | 2,636 problems (some are cutting) | Needs manual technique ID | High |
| R-3 | goproblems_difficulty_based | `*/tesuji/*.sgf` | GE[tesuji] broad category | Medium |

#### R-3: Snapback

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | `sgf/batch-*` where `YT[snapback]` | Pre-tagged, direct grep | Low |
| R-2 | ogs | `sgf/batch-*` where `YT[snapback]` | Pre-tagged | Low |
| R-3 | kisvadim (105 BASIC TESUJI) | 105 problems include snapback examples | Needs manual ID | Medium |

#### R-4: Throw-in

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | `sgf/batch-*` where `YT[throw-in]` | Pre-tagged | Low |
| R-2 | ogs | `sgf/batch-*` where `YT[throw-in]` | Pre-tagged | Low |
| R-3 | kisvadim (TESUJI GREAT DICT) | Various throw-in problems | Needs manual ID | High |

#### R-5: Ko (variants: direct, approach, double, multistep, 10000-year, double-seki)

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | `sgf/batch-*` where `YT[ko]` | Pre-tagged, rich ko pool | Low |
| R-2 | ogs | `sgf/batch-*` where `YT[ko]` | Pre-tagged | Low |
| R-3 | goproblems_difficulty_based | `*/life_and_death/*.sgf` | Ko often embedded in L&D | Medium |
| R-4 | kisvadim (Cho Chikun L&D series) | 2,553 L&D problems | Classic ko positions | High |

#### R-6: Living / Two Eyes

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | where `YT[living]` or `YT[life-and-death]` | Pre-tagged | Low |
| R-2 | goproblems_difficulty_based | `*/life_and_death/*.sgf` (5,693 total!) | Massive pool | Low |
| R-3 | kisvadim (Cho Chikun L&D Elementary) | 900 problems | Curated by master | Medium |
| R-4 | ogs | where `YT[living]` | Pre-tagged | Low |

#### R-7: Squeeze (liberty-shortage / shibori / damezumari)

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | where `YT[liberty-shortage]` | Pre-tagged (if alias matched) | Low |
| R-2 | goproblems_difficulty_based | `*/tesuji/*.sgf` | Squeeze is a tesuji sub-type | Medium |
| R-3 | kisvadim (TESUJI GREAT DICT) | Domain knowledge needed | Needs manual ID | High |

#### R-8: Carpenter's Square (dead-shapes)

| R-1 | Source | Path | Why | Effort |
|-----|--------|------|-----|--------|
| R-1 | goproblems (flat) | where `YT[dead-shapes]` | Pre-tagged | Low |
| R-2 | kisvadim (Cho Chikun L&D series) | Classic carpenter's square problems | Needs manual ID | Medium |
| R-3 | goproblems_difficulty_based | `*/life_and_death/*.sgf` | Carpenter's square is L&D | Medium |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

### 5.1 Rejected Sources

| R-1 | Collection | Rejection Reason |
|-----|-----------|------------------|
| R-1 | `tasuki/` | No solution trees — position-only SGFs, useless for calibration |
| R-2 | `sanderland/` (2a-tesuji, 2c-encyclopedia) | JSON format with first-move-only solutions, no branching |
| R-3 | `eidogo_puzzles/` | FF[3] linear sequences, no branching solution trees |
| R-4 | `101weiqi/` | Only 4 puzzles downloaded — catalog exists but data unavailable |

### 5.2 Risks

| R-1 | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| R-1 | goproblems flat collection already pipeline-enriched (YV[10]) — selecting from them may bias toward easier puzzles | Medium | Cross-reference with goproblems_difficulty_based to get multiple difficulty tiers |
| R-2 | kisvadim books have no explicit technique tags — identifying specific techniques (snapback vs throw-in) requires Go domain expert review | Medium | Use domain expert review or run through enrichment-lab classifier first |
| R-3 | goproblems_difficulty_based `GE[tesuji]` is too broad — doesn't distinguish snapback from throw-in | Medium | Use enrichment-lab's existing technique tagger to sub-classify |
| R-4 | Duplicate puzzles across collections (e.g., Cho Chikun in kisvadim AND tasuki AND goproblems) — fixture may already exist in pipeline | Low | Content hash dedup will catch this |
| R-5 | ambak-tsumego has minimal solution trees (1 correct path, no wrong paths) — insufficient for calibration | Medium | Use only as fallback; prefer goproblems/OGS with full branching |

### 5.3 License Context

All external-sources are pre-existing in the repository — licensing decisions were made at crawl time. This research does not introduce new external data. Fixture usage is internal testing only (not redistribution).

---

## 6. Planner Recommendations

### Recommendation 1 (HIGHEST PRIORITY): Grep goproblems/ogs pre-tagged collections

The `goproblems/` (51K) and `ogs/` (52K) flat collections already have `YT[tag-slug]` tags from pipeline processing. A simple grep for `YT[snapback]`, `YT[throw-in]`, `YT[capture-race]`, etc. will immediately yield technique-specific candidates with full solution trees. **This is the lowest-effort, highest-yield approach** — likely covers 6 of 8 technique gaps in minutes.

**Action**: Run `grep -rl "YT\[snapback\]" external-sources/goproblems/sgf/` (and similar for each technique) to get candidate lists, then manually select 2-3 best per technique.

### Recommendation 2: Use goproblems_difficulty_based for multi-tier fixtures

For techniques requiring easy/medium/hard variants, `goproblems_difficulty_based/` provides pre-stratified difficulty tiers with rich SGF metadata (`GE[]`, `DI[]`, `DP[]`). Particularly valuable for life-and-death (5,693 puzzles) and tesuji (1,236 puzzles) gaps. However, the `GE[tesuji]` tag is broad — sub-technique identification still requires either domain expert review or running the enrichment-lab classifier.

### Recommendation 3: Use kisvadim Cho Chikun L&D for curated-quality fixtures

kisvadim's Cho Chikun Encyclopedia of Life & Death (2,553 problems across 3 difficulty tiers) has excellent solution trees with `C[Correct.]`/`C[Wrong.]` markers. These are domain-expert-curated by one of Go's greatest players. Ideal for **ko variants**, **carpenter's square**, and **living/eye shape** fixtures where technique nuance matters. Higher effort (no pre-existing technique tags) but highest domain authority.

### Recommendation 4: Skip sanderland, tasuki, eidogo entirely

These collections lack solution trees and are structurally unsuitable for calibration fixture sourcing. `sanderland/` uses JSON (not SGF) with first-move-only solutions. `tasuki/` has position-only SGFs with no solution data. `eidogo/` uses FF[3] linear sequences. None can serve as calibration fixtures.

---

## 7. Confidence & Risk Update for Planner

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260322-research-external-sources-fixture-sourcing/` |
| `artifact` | `15-research.md` |
| `post_research_confidence_score` | 85 |
| `post_research_risk_level` | low |

**Top recommendations** (ordered):
1. Grep `goproblems/` + `ogs/` for pre-tagged technique SGFs (covers ~6/8 gaps, minutes)
2. Use `goproblems_difficulty_based/` for difficulty-stratified fixtures
3. Use kisvadim Cho Chikun L&D for ko/carpenter's-square/living fixtures
4. Skip sanderland, tasuki, eidogo

**Open questions**:

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | For kisvadim-sourced fixtures (no technique tags), should we (A) manually identify technique by reading SGF board position, (B) run through enrichment-lab classifier first, or (C) skip kisvadim and rely solely on pre-tagged collections? | A / B / C | B | | ❌ pending |
| Q2 | Should the sourcing script produce a ranked shortlist of N candidates per technique, or should it auto-select the single best? What is N? | N=3 / N=5 / N=10 / auto-select-1 | N=3 | | ❌ pending |
| Q3 | For ko variant fixtures (direct, approach, double, multistep, 10000-year, double-seki), are all 6 needed or is a subset sufficient for calibration? | All 6 / Top 3 / Just direct+approach | All 6 | | ❌ pending |
